"""Realistic PBR spheres -> 1080p MP4.

Pure-NumPy renderer: analytic ray/sphere+plane hits, Cook-Torrance GGX
specular, Fresnel-Schlick, procedural HDR studio env, temp;ally-jittered
soft shadows, floor reflections, ACES tonemap, 2x2 supersampling.
"""
import math
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image
from imageio_ffmpeg import get_ffmpeg_exe

W, H = 1920, 1080
RENDER_W, RENDER_H = 2560, 1440
SS = 1
FPS = 24
DUR = 5.0
N_FRAMES = int(FPS * DUR)

R = 0.55
SPH_Y = R + 0.02
XS = np.array([-2.4, -1.2, 0.0, 1.2, 2.4], dtype=np.float32)
CENTERS = np.stack([XS, np.full(5, SPH_Y, np.float32), np.zeros(5, np.float32)], axis=1)

F0_GOLD = np.array([1.000, 0.766, 0.336], np.float32)
F0_COPPER = np.array([0.955, 0.637, 0.538], np.float32)
F0_STEEL = np.array([0.560, 0.570, 0.580], np.float32)
ALB_RED = np.array([0.72, 0.035, 0.035], np.float32)
ALB_SLATE = np.array([0.30, 0.33, 0.37], np.float32)
F0_DIE = 0.04
ROUGH = np.array([0.08, 0.12, 0.35, 0.15, 0.75], np.float32)
METAL = np.array([1, 1, 1, 0, 0], bool)

UP = np.array([0.0, 1.0, 0.0], np.float32)
SKY_UP = np.array([0.030, 0.045, 0.070], np.float32)
SKY_LO = np.array([0.012, 0.014, 0.020], np.float32)
BOXES = np.stack([
    [0.0, 0.9, 0.6], [0.0, 0.9, -0.7], [0.8, 0.6, 0.0],
    [-0.8, 0.6, 0.0], [0.0, 0.2, 1.0],
]).astype(np.float32)
BOXES = BOXES / np.linalg.norm(BOXES, axis=1, keepdims=True)
BOX_I = np.array([2.0, 2.0, 1.3, 1.3, 0.8], np.float32)
BOX_W = np.array([6.0, 6.0, 8.0, 8.0, 10.0], np.float32)

FLOOR_ALB = np.array([0.045, 0.047, 0.050], np.float32)


def norm(v):
    return v / np.sqrt((v * v).sum(-1, keepdims=True) + 1e-12)


def env(d, rough):
    d = d.astype(np.float32)
    d = norm(d)
    y = np.clip(d[..., 1], -1.0, 1.0)
    g = SKY_LO + (SKY_UP - SKY_LO) * ((y + 1) * 0.5)[..., None]
    col = np.repeat(g.astype(np.float32), d.shape[-1] // 3 if d.ndim == 3 else 1, axis=-1)
    col = SKY_LO + (SKY_UP - SKY_LO) * ((y + 1)[..., None] * 0.5).astype(np.float32)
    for b, inten, wdt in zip(BOXES, BOX_I, BOX_W):
        dot = np.clip((d * b).sum(-1), 0.0, 1.0)
        rgh = np.asarray(rough, dtype=np.float32)
        if rgh.ndim == d.ndim:
            rgh = rgh[..., 0]
        rgh = rgh + np.zeros_like(dot)
        expo = np.maximum(np.float32(1.0), np.float32(wdt) / (np.float32(0.35) + rgh * np.float32(2.5)))
        lobe = (dot ** expo) * np.float32(inten)
        col = col + lobe[..., None] * np.float32([1.0, 0.98, 0.94])
    return col


def sun_dir(t):
    az = 0.9 + 0.7 * math.sin(2 * math.pi * t / DUR)
    return norm(np.float32([math.cos(az) * 0.8, 0.8, math.sin(az) * 0.8 + 0.3]))


def ggx_shadow(n, v, suns, rough):
    """Direct sun: GGX spec + Lambert * soft shadow from 3 jittered dirs."""
    col = np.zeros(n.shape[:-1] + (3,), np.float32)
    for sd in suns:
        h = norm(n + sd[None, None, :])
        ndh = np.clip((n * h).sum(-1), 0.0, 1.0)
        ndv = np.clip((n * v).sum(-1), 1e-4, 1.0)
        ndl = np.clip((n * sd[None, None, :]).sum(-1), 0.0, 1.0)
        a = float(rough) * float(rough)
        dnm = ndh * ndh * (a * a - 1.0) + 1.0
        D = a * a / (math.pi * dnm * dnm + 1e-9)
        k = a * 0.5
        G = (ndv / (ndv * (1 - k) + k)) * (ndl / (ndl * (1 - k) + k))
        spec = (D * G / (4 * np.maximum(ndv * ndl, 1e-4))).astype(np.float32) * ndl
        col += spec[..., None]
    return col


def sphere_mask_hit(o, d):
    """Nearest analytic sphere hit for arbitrary leading dims: (idx, t, hit)."""
    oc = o[..., None, :] - CENTERS
    b = -(oc * d[..., None, :]).sum(-1)
    c = (oc * oc).sum(-1) - R * R
    disc = b * b - c
    ok = disc > 0
    sq = np.sqrt(np.maximum(disc, np.float32(0)))
    t0 = np.where(ok, b - sq, np.float32(1e9))
    t1 = np.where(ok, b + sq, np.float32(1e9))
    t0 = np.where(t0 > 1e-4, t0, t1)
    j = np.argmin(t0, axis=-1)
    tbest = np.take_along_axis(t0, j[..., None], -1)[..., 0]
    return j, tbest, tbest < np.float32(1e8)


def aces(x):
    x = np.clip(x, 0.0, 4.0)
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0)


def to_srgb(x):
    x = aces(x)
    return (np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055) * 255).astype(np.uint8)


def render_strip(t, ys, ye, sw, sh):
    sun = sun_dir(t)
    suns = [sun,
            norm(sun + np.float32([0.035, 0.0, 0.0])),
            norm(sun + np.float32([0.0, 0.025, 0.035]))]
    cam_r = 6.2
    ang = 0.5 * math.sin(2 * math.pi * t / 6.0)
    cam = np.float32([cam_r * math.sin(ang), 1.7 + 0.3 * math.sin(2 * math.pi * t / DUR),
                      cam_r * math.cos(ang)])
    fwd = norm(-cam + np.float32([0, SPH_Y + 0.3, 0]))
    right = norm(np.cross(fwd, UP))
    up = np.cross(right, fwd)

    aspect = W / H
    u = ((np.arange(sw) + 0.5) / sw * 2 - 1) * aspect
    v = 1 - ((np.arange(ys, ye) + 0.5) / sh * 2)
    uu, vv = np.meshgrid(u, v)
    dirs = (fwd * 1.35 + right[None, None, :] * uu[..., None]
            + up[None, None, :] * vv[..., None]).astype(np.float32)
    dirs = norm(dirs)
    G = dirs.shape[0] * dirs.shape[1]

    d3 = dirs.reshape(G, 3)
    o3 = np.broadcast_to(cam, (G, 3))
    j, tb, _ = sphere_mask_hit(o3, d3)
    # plane hit
    with np.errstate(divide="ignore", invalid="ignore"):
        tp = -(cam[1]) / d3[:, 1]
    tp = np.where((d3[:, 1] < -1e-6) & (tp > 1e-4), tp, np.float32(1e9))
    plane = (tp < tb) & np.isfinite(tp) & (tp < 1e8)

    col = env(d3, 0.15).astype(np.float32)  # background
    col[plane] = 0

    # --- spheres ---
    hs = j >= 0
    if hs.any():
        idx = np.nonzero(hs)[0]
        jj = j[idx]
        p = o3[idx] + d3[idx] * tb[idx, None]
        n = norm(p - CENTERS[jj])
        v = norm(cam[None, :] - p)
        rough = ROUGH[jj]
        direct = np.zeros((len(idx), 3), np.float32)
        for sd in suns:
            hvec = norm(n + sd[None, :])
            ndh = np.clip((n * hvec).sum(-1), 0, 1)
            ndv = np.clip((n * v).sum(-1), 1e-4, 1)
            ndl = np.clip((n * sd[None, :]).sum(-1), 0, 1)
            a2 = (rough ** 2)[:, None].astype(np.float32) ** 2
            D = a2 / (math.pi * (ndh[:, None] ** 2 * (a2 - 1) + 1) ** 2 + 1e-9)
            k = (rough * 0.5)[:, None]
            Gt = (ndv[:, None] / (ndv[:, None] * (1 - k) + k)) * \
                 (ndl[:, None] / (ndl[:, None] * (1 - k) + k))
            spec = (D * Gt / (4 * np.maximum(ndv[:, None] * ndl[:, None], 1e-4))) * ndl[:, None]
            direct += spec.astype(np.float32)
        direct *= 2.5
        rd = norm(2 * (n * v).sum(-1, keepdims=True) * n - v)
        es = env(rd, rough[:, None]) * np.float32(1.0)
        ndv = np.clip((n * v).sum(-1), 1e-4, 1)
        fres = 0.04 + 0.96 * (1 - ndv)[:, None] ** 5
        f0s = {0: F0_GOLD, 1: F0_COPPER, 2: F0_STEEL}
        metal_arr = np.stack([f0s[0], f0s[1], f0s[2],
                              np.full(3, F0_DIE, np.float32), np.full(3, F0_DIE, np.float32)])
        f0 = metal_arr[jj]
        f0m = np.where(METAL[jj, None], f0, np.where(fres < F0_DIE, F0_DIE, fres).astype(np.float32))
        spec_env = f0m * es
        alb = np.stack([np.zeros(3), np.zeros(3), np.zeros(3), ALB_RED, ALB_SLATE])[jj].astype(np.float32)
        amb = alb * env(n, 1.0) * np.float32(1.0)
        direct_alb = alb * 0
        for sd in suns:
            ndl = np.clip((n * sd[None, :]).sum(-1), 0, 1)
            direct_alb += (alb * ndl[:, None]).astype(np.float32)
        diff = np.where(METAL[jj, None], 0, 1) * direct_alb * np.float32(1.2)
        col[idx] = spec_env + direct * f0m + diff + amb

    # --- floor ---
    fid = np.nonzero(plane)[0]
    if len(fid):
        p = o3[fid] + d3[fid] * tb[fid, None]
        n = np.float32([0, 1, 0])[None, :]
        v = norm(cam[None, :] - p)
        ndl_list = [np.clip((n * sd[None, :]).sum(-1), 0, 1) for sd in suns]
        ndv = np.clip((n * v).sum(-1), 1e-4, 1)
        # soft shadow
        vis = np.ones(len(fid), np.float32)
        for sd in suns:
            oo = p + sd[None, :] * np.float32(2e-3)
            jj2, tb2, _ = sphere_mask_hit(oo, np.broadcast_to(sd, oo.shape))
            vis *= np.where(tb2 < 40, np.float32(0.0), np.float32(1.0))
        visf = vis * 0.8 + 0.2
        diff = FLOOR_ALB * (sum(ndl_list) / 3) * visf[:, None] * 1.6
        # sun spec on floor
        spec = np.zeros((len(fid), 3), np.float32)
        rh = 0.25
        for sd in suns:
            hvec = norm(n + sd[None, :])
            ndh = np.clip((n * hvec).sum(-1), 0, 1)
            a2 = rh * rh
            D = a2 / (math.pi * (ndh ** 2 * (a2 - 1) + 1) ** 2 + 1e-9)
            k = rh * 0.5
            Gt = (ndv / (ndv * (1 - k) + k)) * (sum(ndl_list) / 3 / (sum(ndl_list) / 3 * (1 - k) + k))
            spec += (D * Gt).astype(np.float32)[:, None] * 0.5
        # mirror reflections of spheres
        rd = norm(d3[fid] - 2 * (d3[fid] * n).sum(-1, keepdims=True) * n)
        jj3, tb3, hitmask = sphere_mask_hit(p + n * 2e-3, rd)
        refl = env(rd, 0.2).astype(np.float32) * np.float32(0.9)
        hm = hitmask & (tb3 < 50)
        for q in np.unique(jj3[hm]):
            qm = hm & (jj3 == q)
            pq = p[qm] + n * np.float32(2e-3) + rd[qm] * tb3[qm, None]
            nq = norm(pq - CENTERS[q])
            vq = norm(cam[None, :] - pq)
            rdq = norm(2 * (nq * vq).sum(-1, keepdims=True) * nq - vq)
            envq = env(rdq, float(ROUGH[q])) * np.float32(1.2)
            base = np.where(METAL[q], f0s.get(q, np.full(3, F0_DIE, np.float32)),
                            np.full(3, F0_DIE, np.float32)) if q < 3 else np.full(3, F0_DIE, np.float32)
            if q >= 3:
                base = np.full(3, F0_DIE, np.float32)
                base = base * 1
                base = base + ALB_RED * 0.05 if q == 3 else base + ALB_SLATE * 0.05
            fade = 1.0 / (1.0 + tb3[qm] * tb3[qm] * 0.25)
            refl[qm] = (base[None, :] * envq).astype(np.float32) * (0.4 + 0.6 * fade[:, None])
        fres = (np.float32(0.05) + np.float32(0.85) * (1 - ndv)[:, None] ** 4).astype(np.float32)
        col[fid] = diff + spec + refl * fres

    return col.reshape(ye - ys, sw, 3), sw, sh


def render_frame(t):
    suns = [
        sun_dir(t),
        norm(sun_dir(t) + np.float32([0.035, 0, 0])),
        norm(sun_dir(t) + np.float32([0, 0.025, 0.035])),
    ]
    full = np.zeros((RENDER_H, RENDER_W, 3), np.float32)
    strip = 140
    sw, sh = RENDER_W * SS, RENDER_H * SS
    for ys in range(0, RENDER_H * SS, strip):
        ye = min(ys + strip, RENDER_H * SS)
        c, _, _ = render_strip(t, ys, ye, sw, sh)
        full[ys:ye] = c
    if SS > 1:
        full = full.reshape(RENDER_H, SS, RENDER_W, SS, 3).mean(axis=(1, 3))
    img = Image.fromarray(to_srgb(full), "RGB")
    if (RENDER_W, RENDER_H) != (W, H):
        img = img.resize((W, H), Image.LANCZOS)
    return img


def worker(args):
    i, t, path = args
    render_frame(t).save(path)
    return path


def main():
    limit = int(os.environ.get("PBR_TEST", "0"))
    nf = max(1, limit) if limit else N_FRAMES
    tmp = tempfile.mkdtemp()
    jobs = [(i, min(i / FPS, DUR - 1e-4), os.path.join(tmp, f"f{i:04d}.png")) for i in range(nf)]
    from concurrent.futures import ProcessPoolExecutor
    nworkers = max(1, min(4, nf))
    with ProcessPoolExecutor(max_workers=nworkers) as ex:
        for n, path in enumerate(ex.map(worker, jobs, chunksize=1), 1):
            if n == 1:
                Image.open(path).save("/workspace/.vibe/tool-results/pbr_preview.png")
            if n % 12 == 0 or n == nf:
                print(f"frame {n}/{nf}", flush=True)
    if limit:
        return
    out = "/workspace/pbr_spheres.mp4"
    subprocess.run([
        get_ffmpeg_exe(), "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out,
    ], check=True, capture_output=True)
    print("done", out, os.path.getsize(out), "bytes,", N_FRAMES, "frames at", W, "x", H)


if __name__ == "__main__":
    main()
