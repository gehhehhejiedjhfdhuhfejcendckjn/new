import math
import os

os.environ["FONTCONFIG_FILE"] = "/workspace/.cairo-root/etc/fonts-local/fonts.conf"

import cairosvg

W, H, FPS, DUR = 854, 480, 30, 6.0
N = int(FPS * DUR)
GROUND = H - 90


def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def cloud(x, y, s=1.0):
    parts = []
    for dx, dy, r in [(-40, 10, 26), (0, 0, 34), (42, 12, 24), (18, -14, 22)]:
        parts.append(f'<circle cx="{x+dx*s:.1f}" cy="{y+dy*s:.1f}" r="{r*s:.1f}" fill="#ffffff"/>')
    return "\n".join(parts)


def banana(x, y, spin=0.0):
    pts = []
    for i in range(13):
        a = math.pi * 0.25 + math.pi * 0.5 * (i / 12)
        r = 34
        pts.append((x - r * 0.5 + r * math.cos(a - math.pi / 4) * 1.2,
                    y + 8 - r * math.sin(a - math.pi / 4) * 0.9))
    if spin:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        ca, sa = math.cos(spin), math.sin(spin)
        pts = [((px - cx) * ca - (py - cy) * sa + cx,
                (px - cx) * sa + (py - cy) * ca + cy) for px, py in pts]
    line = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return (
        f'<polyline points="{line}" fill="none" stroke="#f0c828" stroke-width="13"'
        f' stroke-linecap="round" stroke-linejoin="round"/>'
        f'<polyline points="{line}" fill="none" stroke="#ffe65a" stroke-width="6"'
        f' stroke-linecap="round" stroke-linejoin="round"/>'
    )


def star(cx, cy, r, rot=0.0):
    pts = []
    for i in range(10):
        a = rot + math.pi * i / 5 - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{cx+rr*math.cos(a):.1f},{cy+rr*math.sin(a):.1f}")
    return (f'<polygon points="{" ".join(pts)}" fill="#ffdc3c" stroke="#c8960a"'
            f' stroke-width="2"/>')


def blob(x, y, squash=1.0, rot=0.0, blink=False, wide=False, mouth="smile",
         legphase=0.0, legs_out=False):
    RX = 52 * squash
    RY = 60 / squash
    deg = math.degrees(rot)
    body = [f'<g transform="translate({x:.1f} {y:.1f}) rotate({deg:.1f})">']
    body.append(
        f'<ellipse rx="{RX:.1f}" ry="{RY:.1f}" fill="#ff7896" stroke="#962846" stroke-width="4"/>'
    )
    ew = 11 if wide else 8
    eh = 2 if blink else (15 if wide else 12)
    for sx in (-24, 24):
        body.append(f'<ellipse cx="{sx}" cy="-8" rx="{ew}" ry="{eh}" fill="#1e1e1e"/>')
    if mouth == "oof":
        body.append('<ellipse cy="33" rx="16" ry="13" fill="#5a1428"/>')
        body.append('<ellipse cy="27" rx="16" ry="7" fill="#ffbe5a"/>')
    elif mouth == "oh":
        body.append('<ellipse cy="32" rx="10" ry="8" fill="#5a1428"/>')
    else:
        body.append('<path d="M -20 10 A 20 20 0 0 0 20 10" fill="none"'
                    ' stroke="#781e32" stroke-width="5" stroke-linecap="round"/>')
    lw = 'stroke="#962846" stroke-width="9" stroke-linecap="round"'
    if legs_out:
        body.append(f'<line x1="-20" y1="{RY-6:.1f}" x2="-70" y2="{RY+34:.1f}" {lw}/>')
        body.append(f'<line x1="20" y1="{RY-6:.1f}" x2="70" y2="{RY+30:.1f}" {lw}/>')
        body.append(f'<ellipse cx="-70" cy="{RY+38:.1f}" rx="13" ry="8" fill="#ff7896"'
                    f' stroke="#962846" stroke-width="3"/>')
        body.append(f'<ellipse cx="70" cy="{RY+34:.1f}" rx="13" ry="8" fill="#ff7896"'
                    f' stroke="#962846" stroke-width="3"/>')
    else:
        for sx, off in ((-20, 0.0), (20, math.pi)):
            ang = math.sin(legphase + off) * 0.6
            fx = sx + math.sin(ang) * 26
            fy = RY + 22
            body.append(f'<line x1="{sx}" y1="{RY-10:.1f}" x2="{fx:.1f}" y2="{fy:.1f}" {lw}/>')
            body.append(f'<ellipse cx="{fx:.1f}" cy="{fy+2:.1f}" rx="12" ry="7" fill="#ff7896"'
                        f' stroke="#962846" stroke-width="3"/>')
    body.append("</g>")
    return "\n".join(body)


def frame_svg(i):
    t = i / FPS
    WALK = 2.4
    parts = [
        f'<rect width="{W}" height="{H}" fill="#87ceeb"/>',
        f'<rect y="{GROUND}" width="{W}" height="{H-GROUND}" fill="#6abe5a"/>',
        f'<circle cx="{W-95}" cy="75" r="35" fill="#ffeb78"/>',
        cloud(140 + t * 8, 80),
        cloud(520 + t * 5, 130, 0.7),
        f'<ellipse cx="600" cy="{GROUND+1}" rx="26" ry="9" fill="#5faf50"/>',
    ]
    if t < WALK:
        p = t / WALK
        x = lerp(120, 590, ease(min(1, p / 0.95)))
        y = GROUND - 60 - abs(math.sin(t * 7)) * 8
        scared = t > 1.9
        parts.append(blob(x, y, blink=(t * 2) % 1 < 0.09, wide=scared,
                          mouth="oh" if scared else "smile", legphase=t * 14))
        parts.append(banana(600, GROUND - 2))
        if scared:
            parts.append(f'<text x="{x+70}" y="{y-90}" font-family="DejaVu Sans"'
                         f' font-size="42" font-weight="bold" fill="#ff3c3c">!</text>')
    elif t < WALK + 0.7:
        p = (t - WALK) / 0.7
        y = GROUND - 60 - 150 * math.sin(p * math.pi * 0.8)
        x = 600 - 40 * math.sin(p * math.pi)
        parts.append(blob(x, y, squash=1.1,
                          rot=lerp(0, math.pi * 0.25, math.sin(p * math.pi)),
                          wide=True, mouth="oof", legs_out=True))
        parts.append(f'<text x="{x+60}" y="{y-40}" font-family="DejaVu Sans"'
                     f' font-size="42" font-weight="bold" fill="#ff3c3c">WHOA!</text>')
        parts.append(banana(600, GROUND - 2 + 40 * p, spin=p * 6))
    else:
        k = t - WALK - 0.7
        land = 1 + 0.25 * math.exp(-6 * k) * abs(math.sin(k * 14))
        y = GROUND - 46 * land + 30
        parts.append(blob(560, y, squash=1.9, blink=True, mouth="oof"))
        for s in range(3):
            a = t * 4 + s * 2 * math.pi / 3
            parts.append(star(560 + 40 * math.cos(a), y - 78 + 14 * math.sin(a) - 6, 12, a))
        parts.append(f'<text x="560" y="{y-160}" font-family="DejaVu Sans" font-size="42"'
                     f' font-weight="bold" fill="#c81e1e" text-anchor="middle">OOF!</text>')
        q = min(1, k * 3)
        parts.append(banana(600, GROUND - 2 + 40 * q, spin=q * 6))
        if t > 4.6:
            parts.append(f'<text x="{W/2}" y="100" font-family="DejaVu Sans" font-size="64"'
                         f' font-weight="bold" fill="#ffffff" text-anchor="middle">LOL</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
            f' viewBox="0 0 {W} {H}">' + "\n".join(parts) + "</svg>")


if __name__ == "__main__":
    import tempfile
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe

    tmp = tempfile.mkdtemp()
    for i in range(N):
        png = cairosvg.svg2png(bytestring=frame_svg(i).encode())
        with open(os.path.join(tmp, f"f{i:04d}.png"), "wb") as f:
            f.write(png)
    out = "/workspace/funny_svg.mp4"
    subprocess.run([
        get_ffmpeg_exe(), "-y", "-framerate", str(FPS),
        "-i", os.path.join(tmp, "f%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out,
    ], check=True, capture_output=True)
    print("done", out, os.path.getsize(out), "bytes,", N, "SVG frames")
