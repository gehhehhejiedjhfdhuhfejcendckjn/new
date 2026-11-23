# Glass-Wastes Animation: Rhea and the Clock-Beast

A 2048×2048 MP4 animation created entirely with Python code, based on the story of Rhea tracking a clock-beast (Heavy Reclaimer) in the Glass-Wastes.

---

# 🫧 Funny Spheres — LiquidFun-Style Animation (NEW)

A **45-second, vertical 9:16 (720×1280)** MP4 of googly-eyed spheres playing in a physics-simulated liquid pool — splashes, geysers, a wrecking ball, a superball and a confetti finale.

- **File:** `liquidfun_spheres_45s.mp4`
- **Resolution:** 720×1280 (vertical 9:16)
- **Duration:** 45 seconds
- **FPS:** 30 (simulated at 120 Hz)
- **Format:** MP4 (H.264 + AAC stereo soundtrack)
- **Size:** ~12.1 MB

**Scenes:** 0:01 Chunky cannonballs in · 0:04 Lemon & Pistachio bounce · 0:08 Chubby Rain · 0:14 Bruiser the wrecking ball · 0:19 Bobby the floater · 0:25 Geyser O'Clock · 0:31 Superball Zoom · 0:37 Group Hug + confetti + THE END.

**How it's made:** a LiquidFun-style particle fluid (700 particles, damped spring solver at 120 Hz with surface tension and buoyancy), a cast of shaded vector spheres with blink/squash/googly-eye animation, and a soundtrack synthesized from the physics collision events (boings, splashes, geysers). Regenerate:

```bash
pip install numpy pillow imageio-ffmpeg matplotlib
python3 liquidfun_render.py
```

**Player:** open `liquidfun_player.html` in a browser to watch it with playback controls.

---

# 🪜 TOO MUCH TALL — the sequel (NEW)

The slide-tower sequel in the same 9:16 format: spheres sky-dive down a mega slide (rails → pinball pegs → trampoline) into the pool below.

- **File:** `too_much_tall_spheres.mp4`
- **Resolution:** 720×1280 (vertical 9:16)
- **Duration:** 45 seconds · 30 fps
- **Size:** ~11.1 MB

**Scenes:** 0:02 Chunky sky-dives · 0:06 STEP 1: JUMP · 0:14 HEAVY CARGO · 0:18 Bobby regrets it · 0:22 EVERYBODY JUMPS!! · 0:27 SUPERBALL!! · 0:30 GEYSER O'CLOCK · 0:34 SPLASHDOWN · 0:38 trampoline group hug + confetti.

Regenerate: `python3 too_tall_slide_render.py` (same dependencies as above).

---

## 📹 Video

- **File:** `glass_wastes_animation.mp4`
- **Resolution:** 2048×2048 pixels
- **Duration:** 7.5 seconds
- **FPS:** 8 frames per second
- **Format:** MP4 (H.264 codec)
- **Size:** ~706 KB

## 📜 The Story

The Glass-Wastes stretched from the copper foot-hills of Kar-Sheer to the northern scar where the sun had died during the Second Conjunction. It was not sand that made up the dunes, but billions of pale green vitrified shards—the leftover slag of an ancient war fought with mirrors and concentrated light.

Rhea, sixteen years old with skin cured like dark walnut by the silica wind, steered her dune-skiff, the *Bitter Tern*, tracking a drift-wake. She hunted **clock-beasts**—the self-winding automations abandoned when the high cities cracked.

The Heavy Reclaimer she found was colossal—an iron beetle eighty feet long, circling a jagged fracture in the Caldera of the Lens. Its mainspring was running away with itself, about to tear the beast apart.

Rhea climbed the vibrating iron frame and, with her copper-headed maul, sheared through the jammed safety pin. The trip-lever snapped forward, the balance wheel seized, and the beast stopped three paces from the abyss.

She inscribed her mother's seal: **Claimed for the Wells.**

## 🎬 Animation Scenes

1. **Title Frame** - "GLASS-WASTES" with starry night sky
2. **Glass-Wastes Landscape** - Copper mountains with billions of pale green vitrified shards
3. **Dune-Skiff Approaching** - The *Bitter Tern* sailing across the crystalline wastes
4. **Clock-Beast Revealed** - The iron beetle automaton with spinning mainspring housing
5. **Rhea Climbing** - Rhea scaling the beast with her copper-headed maul
6. **Brake Explosion** - The moment the trip-lever snaps forward with orange sparks
7. **Final Scene** - Rhea victorious, with "Claimed for the Wells" inscribed on the beast

## 💻 Code

The animation was created entirely with Python using:
- `numpy` for frame generation
- `moviepy` for video encoding
- Pure procedural generation (no external images or assets)

**Source code:** `glass_wastes_ultra_simple.py`

To generate the video yourself:

```bash
pip install numpy moviepy
python3 glass_wastes_ultra_simple.py
```

This will create `glass_wastes_animation.mp4` in the current directory.

## 🎨 HTML Player

A simple HTML video player is included: `video_player.html`

You can open this in a browser to play the video with controls.

## 📦 Files

- `glass_wastes_animation.mp4` - The main video file
- `glass_wastes_ultra_simple.py` - Python source code to generate the animation
- `liquidfun_spheres_45s.mp4` - Funny Spheres vertical animation (45 s)
- `too_much_tall_spheres.mp4` - TOO MUCH TALL ultra-tall sequel (45 s)
- `liquidfun_render.py` - Physics + renderer for the Funny Spheres animation
- `too_tall_slide_render.py` - Physics + renderer for the TOO MUCH TALL sequel
- `liquidfun_player.html` - HTML player for both Funny Spheres videos
- `video_player.html` - HTML player for the video
- `README.md` - This file

## 🔧 Requirements

- Python 3.7+
- numpy
- moviepy
- ffmpeg (for video encoding)

## 📝 License

This project is provided as-is for educational and entertainment purposes.

---

*Created entirely with code. No AI-generated images were used in the making of this animation.*
