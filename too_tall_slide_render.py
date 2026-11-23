#!/usr/bin/env python3
""""TOO MUCH TALL" funny sphere slide animation.

Ultra-tall vertical MP4 (608x2560, 45 s): googly spheres sky-dive down a
mega slide (rails, pinball pegs, trampoline) into a liquid pool.
Same LiquidFun-style particle solver as liquidfun_render.py.
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

import matplotlib
FONT_PATH = os.path.join(os.path.dirname(matplotlib.__file__),
                         "mpl-data/fonts/ttf/DejaVuSans-Bold.ttf")

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
W, H = 720, 1280
FLOOR = 1150.0
WALL_L, WALL_R = 40.0, 680.0
FPS_SIM, FPS_OUT, DUR = 120, 30, 45.0
STEPS_PER_FRAME = FPS_SIM // FPS_OUT
N_FRAMES = int(DUR * FPS_OUT)
G = 2300.0

# fluid
N_COLS, N_ROWS = 58, 13
N = N_COLS * N_ROWS
R0 = 11.0
CUT = 20.0
K_REP = 2600.0
CD = 26.0
SAT = 35.0
PR = 6.5
VMAX = 1900.0

random.seed(11)
np.random.seed(11)

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT_MP4 = "/workspace/too_much_tall_spheres.mp4"
RAW_AUDIO = "/tmp/_audio_tall.wav"

# rails: (x0, y0, x1, y1, rest_mult)   trampoline flagged by rest_mult > 1.2
RAILS = [
    (60.0, 250.0, 440.0, 410.0, 1.0),       # slide 1, down-right
    (680.0, 700.0, 250.0, 860.0, 1.0),      # slide 2, down-left
    (160.0, 950.0, 530.0, 968.0, 1.6),      # TRAMPOLINE
]
TRAMP = 2
TRAMP_Y = 1799.0

PEGS = [
    (200.0, 470.0, 14.0), (430.0, 485.0, 14.0), (315.0, 545.0, 16.0),
    (200.0, 600.0, 13.0), (430.0, 615.0, 13.0), (315.0, 672.0, 15.0),
]

# ----------------------------------------------------------------------------
# Scene background
# ----------------------------------------------------------------------------
def build_bg():
    yy = np.linspace(0.0, 1.0, H)[:, None]
    top = np.array([10.0, 12.0, 44.0])
    mid = np.array([24.0, 34.0, 84.0])
    low = np.array([16.0, 52.0, 96.0])
    bot = np.array([8.0, 12.0, 34.0])
    grad = np.where(yy < 0.55,
                    top + (mid - top) * (yy / 0.55),
                    np.where(yy < 0.85,
                             mid + (low - mid) * ((yy - 0.55) / 0.30),
                             low + (bot - low) * ((yy - 0.85) / 0.15)))
    bg = np.repeat(grad[:, None, :], W, axis=1)

    r = np.random.default_rng(3)
    for _ in range(90):                       # stars up top
        sx = r.integers(10, W - 10)
        sy = r.integers(10, int(H * 0.30))
        b = r.uniform(0.25, 0.9)
        bg[sy, sx] += np.array([180.0, 190.0, 255.0]) * b
    for (ccx, ccy, crx, cry) in [(140, 320, 150, 42), (430, 260, 130, 36),
                                 (300, 470, 170, 40)]:   # soft clouds
        gx, gy = np.meshgrid(np.arange(W), np.arange(H))
        e = 1.0 - ((gx - ccx) / crx) ** 2 - ((gy - ccy) / cry) ** 2
        m = e > 0
        bg[m] += (e[m] * 0.5)[:, None] * np.array([70.0, 90.0, 130.0])

    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    f_tick = ImageFont.truetype(FONT_PATH, 26)
    for alt, y in [("1000 m", 260), ("500 m", 480), ("250 m", 700),
                   ("50 m", 920), ("0 m", 1110)]:
        d.line([(WALL_L, y), (WALL_L + 26, y)], fill=(120, 140, 200), width=2)
        d.text((WALL_L + 34, y - 14), alt, font=f_tick, fill=(110, 130, 190))
    d.text((WALL_L + 34, 2350 - 14), "0 m", font=f_tick, fill=(110, 130, 190))

    # rails & trampoline
    for i, (x0, y0, x1, y1, _) in enumerate(RAILS):
        col = (255, 170, 70) if i == TRAMP else (96, 116, 176)
        d.line([(x0, y0), (x1, y1)], fill=col, width=9)
        d.line([(x0, y0), (x1, y1)], fill=(230, 240, 255), width=2)
    for (cx, cy, cr) in PEGS:                  # pinball pegs
        d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr],
                  fill=(120, 140, 205), outline=(210, 225, 255), width=3)
    # walls + floor
    d.rectangle([WALL_L - 8, 60, WALL_L, FLOOR], fill=(60, 74, 120))
    d.rectangle([WALL_R, 60, WALL_R + 8, FLOOR], fill=(60, 74, 120))
    d.rectangle([WALL_L, FLOOR, WALL_R, H], fill=(24, 31, 62))
    d.rectangle([WALL_L - 8, FLOOR - 4, WALL_R + 8, FLOOR], fill=(100, 120, 180))
    BG = np.asarray(img).astype(np.float32)
    return BG

def build_vignette():
    gx, gy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    dd = np.sqrt(gx ** 2 + (gy * 0.55) ** 2)
    a = np.clip((dd - 0.55) / 0.6, 0, 1) ** 1.7 * 140.0
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")

def build_water_tint():
    t = np.zeros((H, 3), np.float32)
    shallow = np.array([64.0, 190.0, 255.0])
    deep = np.array([14.0, 70.0, 185.0])
    for y in range(H):
        f = np.clip((y - 980.0) / 320.0, 0.0, 1.0)
        t[y] = shallow + (deep - shallow) * f
    return t

BG = build_bg()
VIGN = build_vignette()
TINT = build_water_tint()

WATER_K = 23
SIG = 5.2
_k1 = np.arange(WATER_K) - WATER_K // 2
KERN = np.exp(-(_k1[None, :] ** 2 + _k1[:, None] ** 2) / (2 * SIG * SIG)).astype(np.float32)
KK = WATER_K // 2

HL_K = 11
SIG2 = 2.3
_k2 = np.arange(HL_K) - HL_K // 2
KERN2 = np.exp(-(_k2[None, :] ** 2 + _k2[:, None] ** 2) / (2 * SIG2 * SIG2)).astype(np.float32)
HK = HL_K // 2

# ----------------------------------------------------------------------------
# Physics state
# ----------------------------------------------------------------------------
px = np.empty(N); py = np.empty(N)
vx = np.zeros(N); vy = np.zeros(N)
idx = 0
spacing = 10.2
x0 = WALL_L + 22
for r in range(N_ROWS):
    for c in range(N_COLS):
        px[idx] = x0 + c * spacing + random.uniform(-0.6, 0.6)
        py[idx] = FLOOR - 8 - r * spacing - random.uniform(-0.5, 0.5)
        idx += 1

IU, IV = np.triu_indices(N, 1)

BALLS = []

BALL_META = [
    # name, t0, (x, y), vx, vy, R, rest, density, style, rgb
    ("Chunky",    2.00, (W*0.40, -90),   60,   0, 54.0, 0.50, 0.55, "normal", (255, 138, 43)),
    ("Lemon",     6.00, (W*0.62, -90),   30,   0, 44.0, 0.55, 0.70, "normal", (255, 214, 64)),
    ("Pistachio", 9.00, (W*0.30, -90),   70,   0, 38.0, 0.55, 0.62, "normal", (140, 224, 90)),
    ("Pinky",    10.30, (W*0.50, -90),   30,   0, 24.0, 0.55, 0.60, "normal", (255, 92, 145)),
    ("Bruiser",  14.00, (W*0.35, -90),   60,   0, 60.0, 0.40, 3.00, "angry",  (128, 96, 220)),
    ("Bobby",    18.50, (W*0.55, -90),   30,   0, 50.0, 0.50, 0.25, "googly", (64, 220, 230)),
    ("Sky",      22.60, (W*0.30, -90),   60,   0, 26.0, 0.58, 0.60, "normal", (86, 196, 255)),
    ("Limey",    22.90, (W*0.45, -90),   30,   0, 24.0, 0.58, 0.60, "normal", (176, 255, 92)),
    ("Mango",    23.20, (W*0.60, -90),   60,   0, 28.0, 0.58, 0.60, "normal", (255, 170, 40)),
    ("Berry",    23.50, (W*0.22, -90),   30,   0, 22.0, 0.58, 0.60, "normal", (205, 110, 255)),
    ("Zoom",     27.00, (W*0.20, -90),  380,   0, 24.0, 0.93, 1.30, "cool",   (255, 64, 64)),
]

def spawn_ball(meta, t):
    name, t0, (sx, sy), svx, svy, R, rest, density, style, rgb = meta
    BALLS.append(dict(
        name=name, t0=t0, R=R, rest=rest, density=density, style=style,
        x=sx, y=sy, vx=svx, vy=svy, rot=0.0, vr=0.0, sq=0.0,
        blink=random.uniform(1.0, 3.0), dizzy=0.0, scream=False,
        prevy=sy, was_above=True, wind_done=False,
        rgb=rgb,
    ))

CONF_N = 96
conf_active = False
cx_ = np.zeros(CONF_N); cy_ = np.zeros(CONF_N)
cvx_ = np.zeros(CONF_N); cvy_ = np.zeros(CONF_N)
crot_ = np.zeros(CONF_N); cvr_ = np.zeros(CONF_N)
ccol_ = np.zeros(CONF_N, int)
CONF_COLORS = [(255, 90, 126), (255, 210, 63), (63, 210, 255),
               (123, 255, 123), (192, 132, 255), (255, 159, 67)]

EVENTS = []
def boing_ev(t, s): EVENTS.append((t, "boing", float(min(1.0, s))))
def splash_ev(t, s): EVENTS.append((t, "splash", float(min(1.0, s))))

GEYSER_TIMES = [30.5, 34.0]
_g_done = set()
tramp_dent = 0.0

def ball_look(b):
    best, bd = None, 1e9
    for o in BALLS:
        if o is b: continue
        dd = (o["x"] - b["x"]) ** 2 + (o["y"] - b["y"]) ** 2
        if dd < bd:
            bd, best = dd, o
    if best is None: return 0.0, -1.0
    ddx, ddy = best["x"] - b["x"], best["y"] - b["y"]
    n = math.hypot(ddx, ddy) + 1e-6
    return ddx / n, ddy / n

SURF_BINS = 12
surf = np.full(SURF_BINS, FLOOR - 60.0)

def compute_surface():
    b = np.clip(((px - WALL_L) / (WALL_R - WALL_L) * SURF_BINS).astype(int), 0, SURF_BINS - 1)
    for k in range(SURF_BINS):
        m = b == k
        surf[k] = np.percentile(py[m], 12) if m.sum() > 3 else FLOOR - 40.0

def fluid_pair_forces(dt):
    global vx, vy
    dx = px[IV] - px[IU]
    dy = py[IV] - py[IU]
    d = np.sqrt(dx * dx + dy * dy) + 1e-6
    nx = dx / d
    ny = dy / d

    m = d < R0
    vn = (vx[IV][m] - vx[IU][m]) * nx[m] + (vy[IV][m] - vy[IU][m]) * ny[m]
    spring = K_REP * (R0 - d[m])
    f = spring - CD * vn
    f = np.maximum(f, -0.35 * spring)
    fx = f * nx[m]
    fy = f * ny[m]
    vx += (np.bincount(IV[m], fx, N) - np.bincount(IU[m], fx, N)) * dt
    vy += (np.bincount(IV[m], fy, N) - np.bincount(IU[m], fy, N)) * dt

    am = (d >= R0) & (d < CUT)
    fa = SAT * (d[am] / R0 - 1.0)
    ax_ = fa * nx[am]
    ay_ = fa * ny[am]
    vx += (np.bincount(IV[am], ax_, N) - np.bincount(IU[am], ax_, N)) * dt
    vy += (np.bincount(IV[am], ay_, N) - np.bincount(IU[am], ay_, N)) * dt

def rail_collision_particle(rail):
    global px, py, vx, vy
    x0, y0, x1, y1, _ = rail
    dxr, dyr = x1 - x0, y1 - y0
    L2 = dxr * dxr + dyr * dyr
    tt = np.clip(((px - x0) * dxr + (py - y0) * dyr) / L2, 0.0, 1.0)
    cxp = x0 + tt * dxr
    cyp = y0 + tt * dyr
    ddx = px - cxp
    ddy = py - cyp
    d2 = ddx * ddx + ddy * ddy
    Rr = 4.5 + PR
    m = (d2 < Rr * Rr) & (ddy < 0)
    if not m.any():
        return
    dist = np.sqrt(d2[m]) + 1e-6
    nxn = (ddx[m]) / dist
    nyn = (ddy[m]) / dist
    px[m] = cxp[m] + nxn * Rr
    py[m] = cyp[m] + nyn * Rr
    vn = vx[m] * nxn + vy[m] * nyn
    hit = vn < 0
    vx[m] -= np.where(hit, vn * nxn * 1.05, 0.0)
    vy[m] -= np.where(hit, vn * nyn * 1.05, 0.0)

def fluid_s():
    global px, py
    global vx, vy
    global tramp_dent
    px += vx / FPS_SIM
    py += vy / FPS_SIM

    for rail in RAILS:
        rail_collision_particle(rail)

    for b in BALLS:
        Rb = b["R"] + PR
        dxb = px - b["x"]; dyb = py - b["y"]
        m2 = (dxb * dxb + dyb * dyb) < Rb * Rb
        if m2.any():
            dsm = np.sqrt(dxb[m2] ** 2 + dyb[m2] ** 2) + 1e-6
            nxn = dxb[m2] / dsm; nyn = dyb[m2] / dsm
            px[m2] = b["x"] + nxn * Rb
            py[m2] = b["y"] + nyn * Rb
            vn_b = b["vx"] * nxn + b["vy"] * nyn
            pv_n = vx[m2] * nxn + vy[m2] * nyn
            delta = np.maximum(vn_b - pv_n, 0.0) * 0.95
            vx[m2] += nxn * delta
            vy[m2] += nyn * delta
            kick = 2.5 * 30.0 / max(1.0, b["R"])
            b["vx"] -= float(np.sum(nxn)) * kick / FPS_SIM
            b["vy"] -= float(np.sum(nyn)) * kick / FPS_SIM

    fl = py > FLOOR - PR
    py[fl] = FLOOR - PR
    vy[fl] = np.where(vy[fl] > 0, 0.0, vy[fl])
    vx[fl] *= 0.97
    ll = px < WALL_L + PR
    px[ll] = WALL_L + PR
    vx[ll] = np.where(vx[ll] < 0, 0.0, vx[ll])
    rr = px > WALL_R - PR
    px[rr] = WALL_R - PR
    vx[rr] = np.where(vx[rr] > 0, 0.0, vx[rr])
    np.clip(py, 200 + PR, None, out=py)

    sp2 = vx * vx + vy * vy
    over = sp2 > VMAX * VMAX
    if over.any():
        s = VMAX / np.sqrt(sp2[over])
        vx[over] *= s
        vy[over] *= s
    vx *= 0.9990
    vy *= 0.9990
    tramp_dent *= math.exp(-4.0 / FPS_OUT * (FPS_OUT / FPS_SIM))

def rail_collision_ball(b, t):
    for (x0, y0, x1, y1, rmult) in RAILS:
        dxr, dyr = x1 - x0, y1 - y0
        L2 = dxr * dxr + dyr * dyr
        tt = ((b["x"] - x0) * dxr + (b["y"] - y0) * dyr) / L2
        tt = min(1.0, max(0.0, tt))
        cxp = x0 + tt * dxr
        cyp = y0 + tt * dyr
        ddx = b["x"] - cxp
        ddy = b["y"] - cyp
        dist = math.hypot(ddx, ddy)
        Rr = b["R"] + 4.5
        if dist < Rr and dist > 1e-6 and ddy < 0:
            nxn, nyn = ddx / dist, ddy / dist
            b["x"] = cxp + nxn * Rr
            b["y"] = cyp + nyn * Rr
            vn = b["vx"] * nxn + b["vy"] * nyn
            if vn < 0:
                if abs(vn) > 90:
                    if rmult > 1.2:
                        rest = 0.85 if abs(vn) > 1200.0 else 1.5
                    else:
                        rest = 0.55
                    vn_out = -rest * vn
                    if vn_out > 1500.0:
                        vn_out = 1500.0
                    b["vx"] += (vn_out - vn) * nxn
                    b["vy"] += (vn_out - vn) * nyn
                    if abs(vn) > 260:
                        boing_ev(t, abs(vn) / 2000.0 * (1.4 if rmult > 1.2 else 0.8))
                    b["sq"] = max(b["sq"], min(0.45, abs(vn) / 2400.0))
                if rmult > 1.2:
                    global tramp_dent
                    tramp_dent = max(tramp_dent, min(26.0, abs(vn) / 60.0))

def peg_collision_ball(b, t):
    for (pcx, pcy, pcr) in PEGS:
        ddx = b["x"] - pcx
        ddy = b["y"] - pcy
        dist = math.hypot(ddx, ddy)
        Rr = b["R"] + pcr
        if dist < Rr and dist > 1e-6:
            nxn, nyn = ddx / dist, ddy / dist
            b["x"] = pcx + nxn * Rr
            b["y"] = pcy + nyn * Rr
            vn = b["vx"] * nxn + b["vy"] * nyn
            if vn < 0:
                b["vx"] -= 1.75 * vn * nxn
                b["vy"] -= 1.75 * vn * nyn
                b["vr"] += random.uniform(-4, 4)
                if abs(vn) > 260:
                    boing_ev(t, abs(vn) / 2400.0 * 0.7)
                b["sq"] = max(b["sq"], min(0.4, abs(vn) / 2600.0))

def balls_step(t):
    group = t >= 38.5
    calm = t > 39.0
    e_pair = 0.3 if calm else 0.8
    for b in BALLS:
        if t < b["t0"]:
            continue
        R = b["R"]
        bx = int(np.clip((b["x"] - WALL_L) / (WALL_R - WALL_L) * SURF_BINS, 0, SURF_BINS - 1))
        s = surf[bx]
        sub = np.clip(((b["y"] + R) - s) / (2 * R), 0.0, 1.0)
        if sub > 0:
            b["vy"] -= G * 1.22 * sub / b["density"] / FPS_SIM
            b["vx"] *= (1.0 - 2.6 * sub / FPS_SIM)
            b["vy"] *= (1.0 - 1.6 * sub / FPS_SIM)
        b["vy"] += G / FPS_SIM
        if calm:
            f_calm = 1.0 - 1.5 / FPS_SIM
            b["vx"] *= f_calm
            b["vy"] *= f_calm
        rest_eff = min(b["rest"], 0.45) if calm else b["rest"]
        if group:
            b["vx"] += (W / 2 - b["x"]) * 1.1 / FPS_SIM
        b["prevy"] = b["y"]
        b["x"] += b["vx"] / FPS_SIM
        b["y"] += b["vy"] / FPS_SIM

        was_above = b["y"] - R * 0.3 < s
        if b["was_above"] and not was_above and b["vy"] > 380:
            splash_ev(t, (b["vy"] - 350.0) / 1700.0)
        b["was_above"] = was_above
        if not b["wind_done"] and b["vy"] > 1400:
            b["wind_done"] = True
            EVENTS.append((t, "whoosh", 0.55))

        rail_collision_ball(b, t)
        peg_collision_ball(b, t)

        if b["y"] + R > FLOOR:
            imp = b["vy"]
            b["y"] = FLOOR - R
            b["vy"] = -b["vy"] * rest_eff
            b["vx"] *= 0.93
            b["vr"] = b["vx"] / R
            if imp > 320:
                b["sq"] = max(b["sq"], min(0.5, imp / 2300.0))
                boing_ev(t, imp / 2300.0)
        if b["x"] - R < WALL_L + 8:
            b["x"] = WALL_L + 8 + R
            if b["vx"] < 0:
                if abs(b["vx"]) > 350: boing_ev(t, abs(b["vx"]) / 2400.0 * 0.6)
                b["vx"] = -b["vx"] * rest_eff
        if b["x"] + R > WALL_R - 8:
            b["x"] = WALL_R - 8 - R
            if b["vx"] > 0:
                if abs(b["vx"]) > 350: boing_ev(t, abs(b["vx"]) / 2400.0 * 0.6)
                b["vx"] = -b["vx"] * rest_eff
        if b["y"] - R < 60:
            b["y"] = 60 + R
            b["vy"] = abs(b["vy"]) * 0.25

        sp = math.hypot(b["vx"], b["vy"])
        if sp > 2000.0:
            b["vx"] *= 2000.0 / sp
            b["vy"] *= 2000.0 / sp
        b["scream"] = b["vy"] > 1400 and sub < 0.2
        b["rot"] += b["vr"] / FPS_SIM
        b["sq"] *= math.exp(-7.0 / FPS_OUT)
        b["blink"] -= 1.0 / FPS_SIM
        b["dizzy"] = max(0.0, b["dizzy"] - 1.0 / FPS_SIM)
        if b["blink"] < -0.13:
            b["blink"] = random.uniform(2.0, 4.2)

    for i in range(len(BALLS)):
        ai = BALLS[i]
        if t < ai["t0"]: continue
        for j in range(i + 1, len(BALLS)):
            bj = BALLS[j]
            if t < bj["t0"]: continue
            dx = bj["x"] - ai["x"]; dy = bj["y"] - ai["y"]
            dd = math.hypot(dx, dy)
            rsum = ai["R"] + bj["R"]
            if dd < rsum and dd > 1e-6:
                nxn, nyn = dx / dd, dy / dd
                ma, mb = ai["R"] ** 2, bj["R"] ** 2
                tot = ma + mb
                ov = rsum - dd
                ai["x"] -= nxn * ov * (mb / tot)
                ai["y"] -= nyn * ov * (mb / tot)
                bj["x"] += nxn * ov * (ma / tot)
                bj["y"] += nyn * ov * (ma / tot)
                rvn = (bj["vx"] - ai["vx"]) * nxn + (bj["vy"] - ai["vy"]) * nyn
                if rvn < 0:
                    imp = -(1 + e_pair) * rvn / (1 / ma + 1 / mb)
                    ai["vx"] -= imp * nxn / ma
                    ai["vy"] -= imp * nyn / ma
                    bj["vx"] += imp * nxn / mb
                    bj["vy"] += imp * nyn / mb
                    if abs(rvn) > 380:
                        boing_ev(t, abs(rvn) / 2200.0)
                    ai["sq"] = max(ai["sq"], min(0.4, abs(rvn) / 2600.0))
                    bj["sq"] = max(bj["sq"], min(0.4, abs(rvn) / 2600.0))

def geyser(t, power):
    deep = py > FLOOR - 300
    vy[deep] -= power * (0.8 + np.random.random(deep.sum()) * 0.5)
    for b in BALLS:
        if b["y"] > surf[max(0, min(SURF_BINS - 1, int((b["x"] - WALL_L) / (WALL_R - WALL_L) * SURF_BINS)))] - b["R"]:
            b["vy"] -= power / max(0.4, b["density"]) * 0.25
            b["vr"] = random.uniform(-9, 9)
            b["sq"] = 0.35
            b["dizzy"] = 1.4
            b["wind_done"] = False

def confetti_burst(t):
    global conf_active
    conf_active = True
    for side in (0, 1):
        for k in range(CONF_N // 2):
            i = side * (CONF_N // 2) + k
            bx = WALL_L + 24 if side == 0 else WALL_R - 24
            ang = math.radians(random.uniform(55, 80))
            sp = random.uniform(1000, 1650)
            cvx_[i] = math.cos(ang) * sp * (1 if side == 0 else -1)
            cvy_[i] = -math.sin(ang) * sp
            cx_[i], cy_[i] = bx, FLOOR - 6
            crot_[i] = random.uniform(0, 6.28)
            cvr_[i] = random.uniform(-9, 9)
            ccol_[i] = random.randrange(len(CONF_COLORS))

def conf_step(dt):
    if not conf_active: return
    global cvx_, cvy_, cx_, cy_, crot_
    cvy_ += 1500.0 * dt
    cx_ += cvx_ * dt
    cy_ += cvy_ * dt
    cvx_ *= (1 - 0.8 * dt)
    crot_ += cvr_ * dt
    hit = cy_ > FLOOR - 4
    cy_[hit] = FLOOR - 4
    cvy_[hit] = -cvy_[hit] * 0.25
    cvx_[hit] *= 0.7

def simulate(record_every, warmup_steps=300, frames=N_FRAMES):
    global vy
    states, ball_states, conf_states = [], [], []
    for s in range(warmup_steps):
        vy += G * (1.0 / FPS_SIM)
        fluid_pair_forces(1.0 / FPS_SIM)
        fluid_s()
    for f in range(frames * STEPS_PER_FRAME):
        t = f / FPS_SIM
        for meta in BALL_META:
            if f == int(round(meta[1] * FPS_SIM)):
                spawn_ball(meta, t)
        for gt in GEYSER_TIMES:
            if t >= gt and gt not in _g_done:
                _g_done.add(gt)
                geyser(t, 2300.0 if gt == 30.5 else 1500.0)
                EVENTS.append((t, "whoosh", 1.0 if gt == 30.5 else 0.7))
        if t >= 41.5 and not conf_active:
            confetti_burst(t)
            EVENTS.append((t, "pop", 0.9))
        vy += G * (1.0 / FPS_SIM)
        fluid_pair_forces(1.0 / FPS_SIM)
        balls_step(t)
        fluid_s()
        conf_step(1.0 / FPS_SIM)
        if f % STEPS_PER_FRAME == 0:
            compute_surface()
            bs = []
            for b in BALLS:
                ld = ball_look(b)
                sp = math.hypot(b["vx"], b["vy"])
                if b["dizzy"] > 0: expr = 3
                elif b["sq"] > 0.22: expr = 2
                elif b["blink"] < 0.0 or b["scream"]: expr = 1
                else: expr = 0
                bs.append((b["x"], b["y"], b["rot"], b["sq"], expr,
                           sp > 900 or b["scream"], b["scream"], ld[0], ld[1],
                           b["R"], b["rgb"], b["style"], b["vx"], b["vy"]))
            states.append(np.stack([px, py], 1).astype(np.float32))
            ball_states.append(bs)
            conf_states.append((cx_.copy(), cy_.copy(), crot_.copy(), ccol_.copy(),
                                conf_active))
    return states, ball_states, conf_states

# ----------------------------------------------------------------------------
# Sprites & faces
# ----------------------------------------------------------------------------
BALL_SPRITES = {}
BALL_REFL = {}

def make_ball_sprite(rgb, R):
    S = int(math.ceil(R * 2.15))
    yy, xx = np.mgrid[0:S, 0:S]
    c = (S - 1) / 2.0
    nx = (xx - c) / R
    ny = (yy - c) / R
    r2 = nx * nx + ny * ny
    r = np.sqrt(r2)
    mid = np.array(rgb, np.float32)
    r2c = np.clip(r2, 0, 1)
    col = np.ones((S, S, 3), np.float32) * mid[None, None, :]
    col *= (1.0 - 0.34 * r2c)[..., None]
    hl = np.exp(-(((nx + 0.42) ** 2 + (ny + 0.48) ** 2) * 3.4))
    col += hl[..., None] * np.array([230.0, 240.0, 255.0]) * 0.75
    rim = np.clip((r - 0.55) / 0.45, 0, 1)
    col *= (1.0 - 0.38 * rim ** 2)[..., None]
    ring = (r > 0.94) & (r <= 1.0)
    col[ring] = mid[None, :] * 0.42
    alpha = np.clip((1.0 - r) / 0.045, 0.0, 1.0)
    alpha[ring] = 1.0
    arr = np.zeros((S, S, 4), np.uint8)
    arr[..., :3] = np.clip(col, 0, 255)
    arr[..., 3] = (alpha * 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA")
    refl = img.transpose(Image.FLIP_TOP_BOTTOM)
    ra = np.array(refl, np.uint8)
    ra[..., 3] = (ra[..., 3].astype(np.float32) * 0.13).astype(np.uint8)
    refl = Image.fromarray(ra, "RGBA")
    return img, refl

for (name, _, _, _, _, R, _, _, _, rgb) in BALL_META:
    BALL_SPRITES[(rgb, R)], BALL_REFL[(rgb, R)] = make_ball_sprite(rgb, R)

def draw_face(d, R, style, expr, mouth_o, scream, ldx, ldy, ox=0.0, oy=0.0):
    X = lambda a: a + ox
    Y = lambda a: a + oy
    ink = (28, 26, 46, 255)
    ew = R * 0.30
    ex = R * 0.36
    ey = -R * 0.25
    if style == "cool":
        d.rounded_rectangle([(X(-ex - ew/2), Y(ey - R*0.16)), (X(ex + ew/2), Y(ey + R*0.16))],
                            radius=R*0.10, fill=(20, 20, 34, 255))
        mw = R * 0.5
        d.arc([X(-mw), Y(R*0.05), X(mw), Y(R*0.55)], 15, 165, fill=ink, width=max(3, int(R*0.08)))
        return
    for sgn in (-1, 1):
        cx = sgn * ex
        if expr == 3:
            dd = R * 0.13
            d.line([(X(cx - dd), Y(ey - dd)), (X(cx + dd), Y(ey + dd))], fill=ink, width=max(3, int(R * 0.09)))
            d.line([(X(cx - dd), Y(ey + dd)), (X(cx + dd), Y(ey - dd))], fill=ink, width=max(3, int(R * 0.09)))
        elif expr == 2:
            d.line([(X(cx - R*0.16), Y(ey - R*0.12)), (X(cx), Y(ey + R*0.04)), (X(cx + R*0.16), Y(ey - R*0.12))],
                   fill=ink, width=max(3, int(R * 0.09)), joint="curve")
        elif scream:
            dd = R * 0.13
            d.line([(X(cx - dd), Y(ey - dd)), (X(cx + dd), Y(ey + dd)), (X(cx + dd), Y(ey + dd))],
                   fill=ink, width=max(3, int(R * 0.09)))
            d.line([(X(cx - dd), Y(ey + dd)), (X(cx + dd), Y(ey - dd))], fill=ink, width=max(3, int(R * 0.09)))
        elif expr == 1:
            d.line([(X(cx - R*0.16), Y(ey)), (X(cx + R*0.16), Y(ey))], fill=ink, width=max(3, int(R * 0.07)))
        else:
            d.ellipse([X(cx - ew/2), Y(ey - ew/2), X(cx + ew/2), Y(ey + ew/2)],
                      fill=(255, 255, 255, 255), outline=ink, width=max(2, int(R * 0.045)))
            pr = R * (0.13 if style == "googly" else 0.085)
            pxo = cx + ldx * R * 0.07
            pyo = ey + ldy * R * 0.07
            d.ellipse([X(pxo - pr), Y(pyo - pr), X(pxo + pr), Y(pyo + pr)], fill=ink)
            gr = pr * 0.4
            d.ellipse([X(pxo - pr*0.35 - gr), Y(pyo - pr*0.35 - gr), X(pxo - pr*0.35 + gr), Y(pyo - pr*0.35 + gr)],
                      fill=(255, 255, 255, 235))
    if style == "angry":
        for sgn in (-1, 1):
            d.line([(X(sgn * R*0.58), Y(ey - R*0.42)), (X(sgn * R*0.14), Y(ey - R*0.26))],
                   fill=ink, width=max(4, int(R * 0.11)))
        mw = R * 0.42
        d.arc([X(-mw), Y(R*0.02), X(mw), Y(R*0.42)], 200, 340, fill=ink, width=max(3, int(R*0.08)))
    elif scream:
        mr = R * 0.22
        d.ellipse([X(-mr), Y(R*0.10), X(mr), Y(R*0.10 + 2*mr)], fill=ink)
    elif mouth_o:
        mr = R * 0.16
        d.ellipse([X(-mr), Y(R*0.18), X(mr), Y(R*0.18 + 2*mr)], fill=ink)
    else:
        mw = R * 0.5
        d.arc([X(-mw), Y(R*0.02), X(mw), Y(R*0.55)], 20, 160, fill=ink, width=max(3, int(R*0.08)))

def face_layer(R, style, expr, mouth_o, scream, ldx, ldy, rot, sx, sy):
    S = int(math.ceil(R * 2.15))
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    draw_face(d, R, style, expr, mouth_o, scream, ldx, ldy, ox=S / 2.0, oy=S / 2.0)
    tw, th = max(2, int(S * sx)), max(2, int(S * sy))
    lay = lay.resize((tw, th), Image.BILINEAR)
    if abs(rot) > 0.02:
        lay = lay.rotate(math.degrees(rot), resample=Image.BILINEAR, expand=True)
    return lay

# ----------------------------------------------------------------------------
# Captions
# ----------------------------------------------------------------------------
CAPTIONS = [
    (1.20, 5.60, "TOO MUCH TALL"),
    (6.00, 9.00, "STEP 1: JUMP"),
    (10.20, 13.50, "DON'T LOOK DOWN"),
    (14.00, 17.50, "HEAVY CARGO"),
    (18.80, 22.10, "BOBBY REGRETS IT"),
    (22.40, 26.30, "EVERYBODY JUMPS!!"),
    (27.00, 30.30, "SUPERBALL!!"),
    (30.60, 34.20, "GEYSER O'CLOCK"),
    (34.40, 37.60, "SPLASHDOWN"),
    (38.00, 41.30, "GROUP HUG"),
]
FCACHE = {}
def get_font(size):
    if size not in FCACHE:
        FCACHE[size] = ImageFont.truetype(FONT_PATH, size)
    return FCACHE[size]

def text_layer(txt, size, y, alpha, center_x=W // 2, rot=0.0, stroke=4):
    f = get_font(size)
    bbox = f.getbbox(txt)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = stroke * 3 + 8
    lay = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((pad - bbox[0], pad - bbox[1]), txt, font=f,
           fill=(255, 255, 255, alpha), stroke_width=stroke,
           stroke_fill=(22, 20, 44, min(255, alpha + 40)))
    if rot:
        lay = lay.rotate(math.degrees(rot), resample=Image.BILINEAR, expand=True)
    return lay, (center_x - lay.width // 2, y - lay.height // 2)

def fade(t, t0, t1, fin=0.35, fout=0.35):
    if t < t0 or t > t1: return 0.0
    return min(1.0, (t - t0) / fin, (t1 - t) / fout)

# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
def render_frame(k, states, ball_states, conf_states):
    t = k / FPS_OUT
    acc = np.zeros((H, W), np.float32)
    hl = np.zeros((H, W), np.float32)
    P = states[k]
    xs = P[:, 0].astype(np.int32)
    ys = P[:, 1].astype(np.int32)
    for i in range(N):
        ix, iy = xs[i], ys[i]
        if ix < KK or ix >= W - KK or iy < KK or iy >= H - KK:
            continue
        acc[iy - KK:iy + KK + 1, ix - KK:ix + KK + 1] += KERN
        jx, jy = xs[i] - 3, ys[i] - 4
        if HK <= jx < W - HK and HK <= jy < H - HK:
            hl[jy - HK:jy + HK + 1, jx - HK:jx + HK + 1] += KERN2
    cov = 1.0 - np.exp(-2.1 * acc)
    hlc = 1.0 - np.exp(-5.0 * hl)

    canvas = BG * (1.0 - cov[..., None]) + cov[..., None] * TINT[:, None, :]
    canvas += hlc[..., None] * np.array([185.0, 235.0, 255.0]) * 0.75
    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(img)

    # trampoline sag
    if tramp_dent > 1.0:
        x0t, y0t, x1t, _, _ = RAILS[TRAMP]
        my = y0t + 18 + tramp_dent
        d.line([(x0t, y0t), (x0t + 20, my), ((x0t + x1t) / 2, my + 6), (x1t - 20, my), (x1t, y0t)],
               fill=(255, 150, 60), width=8, joint="curve")

    conf_x, conf_y, conf_r, conf_c, conf_on = conf_states[k]
    if conf_on:
        for i in range(CONF_N):
            col = CONF_COLORS[ccol_[i]]
            l, wdt = 13.0, 8.0
            ca, sa = math.cos(conf_r[i]), math.sin(conf_r[i])
            pts = [(conf_x[i] + ca * ax - sa * ay, conf_y[i] + sa * ax + ca * ay)
                   for ax, ay in ((-l, -wdt), (l, -wdt), (l, wdt), (-l, wdt))]
            d.polygon(pts, fill=col + (255,))

    for bi, bs in enumerate(ball_states[k]):
        (x, y, rot, sq, expr, mo, scream, ldx, ldy, R, rgb, style, bvx, bvy) = bs
        if t < BALL_META[bi][1]:
            continue
        sprite, refl = BALL_SPRITES[(tuple(rgb), R)], BALL_REFL[(tuple(rgb), R)]
        sp = math.hypot(bvx, bvy)
        stretch = min(0.22, sp / 6500.0)
        sx = (1.0 + sq * 0.55) * (1.0 + stretch * 0.25)
        sy = (1.0 - sq) * (1.0 - stretch * 0.25)

        # wind streaks in free fall
        if bvy > 1400:
            ln = min(360.0, (bvy - 1400.0) / 5.0)
            for ox_ in (-R * 0.55, -R * 0.2, R * 0.2, R * 0.55):
                yy0 = y - R - 8
                d.line([(x + ox_, yy0), (x + ox_, yy0 - ln)],
                       fill=(200, 220, 255, 46), width=2)

        hf = max(0.0, 1.0 - (FLOOR - y - R) / 900.0)
        if hf > 0.02 and y < FLOOR:
            sw = R * (0.6 + 0.9 * hf)
            d.ellipse([x - sw, FLOOR - 10, x + sw, FLOOR + 12], fill=(4, 6, 18, int(110 * hf)))

        ry = FLOOR + (FLOOR - y)
        if ry < H + 200:
            img.alpha_composite(refl.resize((max(2, int(sprite.width * sx)), max(2, int(sprite.height * sy))),
                                            Image.BILINEAR),
                                (int(x - sprite.width * sx / 2), int(ry - sprite.height * sy * 0.5)))

        if sp > 1200:
            gx = x - bvx * 0.014
            gy = y - bvy * 0.014
            ga = np.array(sprite, np.uint8).copy()
            ga[..., 3] = (ga[..., 3] * 0.25).astype(np.uint8)
            ghost = Image.fromarray(ga, "RGBA")
            img.alpha_composite(ghost.resize((max(2, int(sprite.width * sx)), max(2, int(sprite.height * sy))),
                                             Image.BILINEAR),
                                (int(gx - sprite.width * sx / 2), int(gy - sprite.height * sy / 2)))

        sp_img = sprite.resize((max(2, int(sprite.width * sx)), max(2, int(sprite.height * sy))),
                               Image.BILINEAR)
        img.alpha_composite(sp_img, (int(x - sp_img.width / 2), int(y - sp_img.height / 2)))

        fl = face_layer(R, style, expr, mo, scream, ldx, ldy, rot, sx, sy)
        img.alpha_composite(fl, (int(x - fl.width / 2), int(y - fl.height / 2)))

    for (t0, t1, txt) in CAPTIONS:
        a = fade(t, t0, t1)
        if a > 0.01:
            bounce = math.sin((t - t0) * 9.0) * 6.0 * math.exp(-(t - t0) * 3.0)
            lay, pos = text_layer(txt, 42, int(150 + bounce), int(235 * a), stroke=5)
            img.alpha_composite(lay, pos)

    a = fade(t, 0.30, 5.60, 0.3, 0.4)
    if a > 0.01:
        pop = 1.0 + 0.42 * math.exp(-3.4 * max(0.0, t - 0.34))
        sz = int(56 * pop)
        lay, pos = text_layer("TOO MUCH", sz, int(H * 0.075), int(245 * a), stroke=6)
        img.alpha_composite(lay, pos)
        lay, pos = text_layer("TALL", sz, int(H * 0.075) + int(62 * pop), int(245 * a), stroke=6)
        img.alpha_composite(lay, pos)

    a = fade(t, 41.60, 44.95, 0.4, 0.5)
    if a > 0.01:
        wob = math.sin(t * 2.6) * 0.05
        lay, pos = text_layer("THE END", int(80), int(H * 0.25), int(250 * a), rot=wob, stroke=7)
        img.alpha_composite(lay, pos)
        lay, pos = text_layer("starring: Chunky Lemon Pistachio Pinky", 24, int(H * 0.25) + 96, int(220 * a), stroke=3)
        img.alpha_composite(lay, pos)
        lay, pos = text_layer("Bruiser Bobby Sky Limey Mango", 24, int(H * 0.25) + 138, int(220 * a), stroke=3)
        img.alpha_composite(lay, pos)
        lay, pos = text_layer("Berry Zoom", 24, int(H * 0.25) + 180, int(220 * a), stroke=3)
        img.alpha_composite(lay, pos)

    out = Image.alpha_composite(img, VIGN)
    return out.convert("RGB").tobytes()

# ----------------------------------------------------------------------------
# Audio
# ----------------------------------------------------------------------------
SR = 44100

def synth_audio(events):
    n = int(DUR * SR)
    mono = np.zeros(n + SR, np.float64)

    def add(sig, t0):
        i0 = int(t0 * SR)
        i1 = min(n + SR, i0 + len(sig))
        if i1 > i0:
            mono[i0:i1] += sig[:i1 - i0]

    rng = np.random.default_rng(11)

    def noise(dur):
        return rng.standard_normal(int(dur * SR))

    def bandpass(x, lo, hi):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / SR)
        mask = ((f > lo) & (f < hi)).astype(np.float64)
        mask = mask / (1.0 + np.abs(f - 1100) / 2500)
        return np.fft.irfft(X * mask, len(x))

    def boing(t0, s):
        dur = 0.5
        tt = np.arange(int(dur * SR)) / SR
        f0 = 150 + 300 * s
        f = f0 * np.exp(-tt * 2.4) * (1 + 0.30 * np.sin(2 * np.pi * (15 + 30 * s) * tt) * (1 + 3 * tt))
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sin(ph) * np.exp(-tt * 7.0) * (0.18 + 0.42 * s)
        sig += noise(dur) * np.exp(-tt * 90) * 0.25 * (0.2 + s)
        add(sig, t0)

    def splash(t0, s):
        dur = 0.7
        tt = np.arange(int(dur * SR)) / SR
        nz = bandpass(noise(dur), 380, 4600)
        env = np.minimum(tt / 0.012, 1.0) * np.exp(-tt * 6.5)
        sig = nz * env * (0.30 + 0.42 * s)
        ff = 420 * np.exp(-tt * 5.0) + 140
        ph = 2 * np.pi * np.cumsum(ff) / SR
        sig += np.sin(ph) * np.exp(-tt * 9.0) * 0.30
        add(sig, t0)

    def whoosh(t0, s):
        dur = 1.1
        tt = np.arange(int(dur * SR)) / SR
        nz = bandpass(noise(dur), 200, 1500)
        env = np.sin(np.pi * np.minimum(tt / dur, 1.0)) ** 1.6
        rise = (tt / dur) ** 2
        sig = nz * env * (0.30 * s) * (0.5 + rise)
        add(sig, t0)

    def pop(t0, s):
        dur = 0.14
        tt = np.arange(int(dur * SR)) / SR
        f = 500 + 1100 * tt / dur
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sin(ph) * np.exp(-tt * 26) * 0.30
        sig += noise(dur) * np.exp(-tt * 120) * 0.18
        add(sig, t0)

    def marimba(freq, t0, dur=0.5, amp=0.1):
        tt = np.arange(int(dur * SR)) / SR
        sig = (np.sin(2 * np.pi * freq * tt) + 0.42 * np.sin(2 * np.pi * freq * 2.0 * tt)
               + 0.14 * np.sin(2 * np.pi * freq * 3.02 * tt))
        sig *= np.exp(-tt * 6.5) * amp
        add(sig, t0)

    def tada(t0):
        for k, m in enumerate([72, 76, 79, 84]):
            marimba(440.0 * 2 ** ((m - 69) / 12), t0 + k * 0.11, 0.6, 0.16)

    events = sorted(events)
    filtered, last = [], {"boing": -10.0, "splash": -10.0}
    for (t0, kind, s) in events:
        if kind == "boing":
            if t0 - last["boing"] < 0.14:
                continue
            if s < 0.40 and t0 - last["boing"] < 0.55:
                continue
        elif kind == "splash":
            if t0 - last["splash"] < 0.10:
                continue
            if s < 0.35 and t0 - last["splash"] < 0.55:
                continue
        filtered.append((t0, kind, s))
        last[kind] = t0

    for (t0, kind, s) in filtered:
        s = max(0.05, min(1.0, s))
        if kind == "boing": boing(t0, s)
        elif kind == "splash": splash(t0, s)
        elif kind == "whoosh": whoosh(t0, s)
        elif kind == "pop":
            pop(t0, s); pop(t0 + 0.08, s * 0.7)
    tada(41.45)

    BPM = 100.0
    e8 = 60.0 / BPM / 2.0
    t_start, t_end = 3.0, 44.2
    pent = [60, 62, 64, 67, 69, 72, 74, 76, 79]
    roots = [36, 33, 29, 31]
    rngm = np.random.default_rng(5)
    cur = 3
    steps = int((t_end - t_start) / e8)
    for i in range(steps):
        tt = t_start + i * e8
        bar = i // 8
        if i % 8 == 0:
            marimba(440.0 * 2 ** ((roots[bar % 4] - 69) / 12), tt, 0.9, 0.11)
            marimba(440.0 * 2 ** ((roots[bar % 4] + 12 - 69) / 12), tt, 0.9, 0.05)
        if rngm.random() < 0.55:
            cur = int(np.clip(cur + rngm.integers(-2, 3), 0, len(pent) - 1))
            marimba(440.0 * 2 ** ((pent[cur] - 69) / 12), tt, 0.34, 0.055)
        if i % 2 == 1:
            nz = noise(0.03) * np.exp(-np.arange(int(0.03 * SR)) / SR * 160) * 0.05
            add(nz, tt)

    mono = np.tanh(mono[:n] * 1.15) * 0.92
    st = np.zeros((n, 2))
    st[:, 0] = mono * 0.97
    st[8:, 1] = mono[:-8]
    st = np.clip(st, -1, 1)
    pcm = (st * 32767).astype(np.int16)
    with wave.open(RAW_AUDIO, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())

# ----------------------------------------------------------------------------
def main():
    print("simulating...", flush=True)
    states, ball_states, conf_states = simulate(STEPS_PER_FRAME)
    print(f"sim done: {len(states)} frames, {len(EVENTS)} audio events", flush=True)
    synth_audio(EVENTS)

    if "--test" in sys.argv:
        os.makedirs("/workspace/previews_tall", exist_ok=True)
        for k in [30, 75, 230, 320, 460, 560, 700, 920, 1000, 1060, 1180, 1300, 1340]:
            frame = render_frame(k, states, ball_states, conf_states)
            Image.frombytes("RGB", (W, H), frame).save(f"/workspace/previews_tall/f{k:04d}.jpg", quality=88)
        print("previews written", flush=True)
        return

    print("encoding video...", flush=True)
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-framerate", str(FPS_OUT), "-i", "pipe:0", "-i", RAW_AUDIO,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", OUT_MP4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for k in range(N_FRAMES):
        proc.stdin.write(render_frame(k, states, ball_states, conf_states))
        if k % 150 == 0:
            print(f"  frame {k}/{N_FRAMES}", flush=True)
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    proc.wait()
    if proc.returncode != 0:
        print("FFMPEG ERROR:\n", err[-3000:])
        sys.exit(1)
    sz = os.path.getsize(OUT_MP4) / 1e6
    print(f"DONE -> {OUT_MP4} ({sz:.1f} MB)", flush=True)

if __name__ == "__main__":
    main()
