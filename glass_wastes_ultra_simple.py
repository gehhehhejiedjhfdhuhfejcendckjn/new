"""
Ultra-simple Glass-Wastes animation
Creates a 2048x2048 MP4 animation entirely with code
Uses very basic drawing to avoid memory issues
"""

import numpy as np
from moviepy import ImageSequenceClip
import random
import math

# ============================================================
# CONFIGURATION - Reduced for sandbox
# ============================================================
WIDTH, HEIGHT = 2048, 2048
FPS = 8  # Very low FPS
DURATION = 8  # 8 seconds
TOTAL_FRAMES = FPS * DURATION

print("=" * 60)
print("GLASS-WASTES ANIMATION (Ultra-Simple)")
print(f"Resolution: {WIDTH}x{HEIGHT}, FPS: {FPS}, Duration: {DURATION}s")
print(f"Total frames: {TOTAL_FRAMES}")
print("=" * 60)

CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2


def make_frame_title(frame_idx):
    """Title frame"""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:, :] = [10, 15, 20]
    
    # Add some stars
    for i in range(30):
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)
        frame[y, x] = [255, 255, 255]
    
    # Draw title
    for x in range(CENTER_X - 200, CENTER_X + 200):
        frame[CENTER_Y - 50, x] = [200, 150, 100]
    
    return frame


def make_frame_glass_wastes(frame_idx):
    """Glass wastes landscape"""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    
    # Sky
    for y in range(HEIGHT):
        intensity = min(210, 200 + int((y / HEIGHT) * 40))
        frame[y, :] = [intensity, min(intensity + 20, 255), min(intensity + 40, 255)]
    
    # Mountains
    for i in range(3):
        mx = int(WIDTH * (0.1 + i * 0.3))
        my = HEIGHT - int(HEIGHT * 0.2)
        mw = int(WIDTH * 0.2)
        mh = int(HEIGHT * 0.2)
        
        for y in range(max(0, my - mh), min(HEIGHT, my)):
            line_width = int(mw * (1 - abs(y - my) / mh))
            for x in range(max(0, mx - line_width // 2), min(WIDTH, mx + line_width // 2)):
                frame[y, x] = [180, 120, 80]
    
    # Glass shards
    for i in range(100):
        x = random.randint(0, WIDTH - 1)
        y = random.randint(HEIGHT // 2, HEIGHT - 1)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = x + dx, y + dy
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                    frame[ny, nx] = [random.randint(100, 150), random.randint(180, 220), random.randint(140, 180)]
    
    return frame


def make_frame_skiff(frame_idx):
    """Dune-skiff"""
    frame = make_frame_glass_wastes(frame_idx)
    
    progress = frame_idx / TOTAL_FRAMES
    skiff_x = int(WIDTH * (0.1 + progress * 0.7))
    skiff_y = int(HEIGHT * 0.7)
    
    skiff_w = int(WIDTH * 0.2)
    skiff_h = int(HEIGHT * 0.05)
    
    # Hull
    for y in range(max(0, skiff_y - skiff_h), min(HEIGHT, skiff_y + skiff_h)):
        for x in range(max(0, skiff_x - skiff_w // 2), min(WIDTH, skiff_x + skiff_w // 2)):
            frame[y, x] = [200, 180, 150]
    
    # Sail
    sail_top = skiff_y - int(skiff_h * 3)
    for y in range(max(0, sail_top), min(HEIGHT, skiff_y)):
        sail_w = int(skiff_w * 0.6 * (1 - (y - sail_top) / (skiff_y - sail_top)))
        for x in range(max(0, skiff_x - sail_w // 2), min(WIDTH, skiff_x + sail_w // 2)):
            frame[y, x] = [180, 120, 80]
    
    return frame


def make_frame_beast(frame_idx):
    """Clock-beast"""
    frame = make_frame_glass_wastes(frame_idx)
    
    progress = frame_idx / TOTAL_FRAMES
    scale = 0.5 + progress * 0.5
    
    beast_w = int(WIDTH * 0.4 * scale)
    beast_h = int(HEIGHT * 0.3 * scale)
    
    # Body ellipse
    a = beast_w // 2
    b = beast_h // 2
    
    for y in range(max(0, CENTER_Y - b), min(HEIGHT, CENTER_Y + b)):
        for x in range(max(0, CENTER_X - a), min(WIDTH, CENTER_X + a)):
            dx = (x - CENTER_X) / a if a > 0 else 0
            dy = (y - CENTER_Y) / b if b > 0 else 0
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [80, 100, 80]
    
    # Legs
    for leg_idx in range(6):
        angle = math.pi * 2 * leg_idx / 6
        leg_x = CENTER_X + int(math.cos(angle) * beast_w * 0.4)
        leg_y = CENTER_Y + int(math.sin(angle) * beast_h * 0.3)
        
        for y in range(leg_y, min(HEIGHT, leg_y + int(beast_h * 0.2))):
            frame[y, leg_x] = [100, 100, 100]
    
    # Spinning wheel
    if frame_idx < TOTAL_FRAMES * 0.8:
        wheel_r = int(beast_w * 0.05)
        for angle in range(0, 360, 20):
            rad = math.radians(angle + frame_idx * 10)
            px = CENTER_X + int(math.cos(rad) * wheel_r)
            py = CENTER_Y - int(beast_h * 0.2) + int(math.sin(rad) * wheel_r)
            if 0 <= py < HEIGHT and 0 <= px < WIDTH:
                frame[py, px] = [255, 200, 150]
    
    return frame


def make_frame_climbing(frame_idx):
    """Rhea climbing"""
    frame = make_frame_glass_wastes(frame_idx)
    
    beast_w = int(WIDTH * 0.4)
    beast_h = int(HEIGHT * 0.3)
    
    # Beast
    a = beast_w // 2
    b = beast_h // 2
    for y in range(max(0, CENTER_Y - b), min(HEIGHT, CENTER_Y + b)):
        for x in range(max(0, CENTER_X - a), min(WIDTH, CENTER_X + a)):
            dx = (x - CENTER_X) / a if a > 0 else 0
            dy = (y - CENTER_Y) / b if b > 0 else 0
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [50, 50, 50]
    
    # Rhea
    climb_progress = frame_idx / TOTAL_FRAMES
    rhea_x = CENTER_X - int(beast_w * 0.3) + int(beast_w * 0.6 * climb_progress)
    rhea_y = CENTER_Y + int(beast_h * 0.1) - int(beast_h * 0.3 * climb_progress)
    
    # Body ellipse
    for y in range(max(0, rhea_y - 15), min(HEIGHT, rhea_y + 15)):
        for x in range(max(0, rhea_x - 10), min(WIDTH, rhea_x + 10)):
            dx = (x - rhea_x) / 10
            dy = (y - rhea_y) / 15
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [80, 50, 30]
    
    # Head
    for y in range(max(0, rhea_y - 25), min(HEIGHT, rhea_y - 15)):
        for x in range(max(0, rhea_x - 8), min(WIDTH, rhea_x + 8)):
            dx = (x - rhea_x) / 8
            dy = (y - (rhea_y - 20)) / 10
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [80, 50, 30]
    
    # Goggles
    for y in range(max(0, rhea_y - 27), min(HEIGHT, rhea_y - 25)):
        for x in range(max(0, rhea_x - 6), min(WIDTH, rhea_x + 6)):
            frame[y, x] = [200, 200, 200]
    
    return frame


def make_frame_explosion(frame_idx):
    """Explosion"""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:, :] = [20, 20, 30]
    
    progress = frame_idx / TOTAL_FRAMES * 2
    
    for i in range(50):
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(0, WIDTH * 0.4 * progress)
        
        x = CENTER_X + int(math.cos(angle) * dist)
        y = CENTER_Y + int(math.sin(angle) * dist)
        
        size = random.randint(2, 4)
        life = 1.0 - (dist / (WIDTH * 0.4 * progress)) if progress > 0 else 1.0
        
        if life > 0:
            color_val = int(200 + 55 * life)
            color = [min(color_val, 255), min(int(color_val * 0.7), 255), min(int(color_val * 0.4), 255)]
            
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                        frame[ny, nx] = color
    
    # Rhea
    if progress > 0.5:
        rhea_x = CENTER_X - int(WIDTH * 0.2)
        rhea_y = CENTER_Y + int(HEIGHT * 0.1)
        for y in range(max(0, rhea_y - 15), min(HEIGHT, rhea_y + 15)):
            for x in range(max(0, rhea_x - 10), min(WIDTH, rhea_x + 10)):
                dx = (x - rhea_x) / 10
                dy = (y - rhea_y) / 15
                if dx*dx + dy*dy <= 1.0:
                    frame[y, x] = [80, 50, 30]
    
    return frame


def make_frame_final(frame_idx):
    """Final scene"""
    frame = make_frame_glass_wastes(frame_idx)
    
    beast_w = int(WIDTH * 0.4)
    beast_h = int(HEIGHT * 0.3)
    
    # Beast
    a = beast_w // 2
    b = beast_h // 2
    for y in range(max(0, CENTER_Y - b), min(HEIGHT, CENTER_Y + b)):
        for x in range(max(0, CENTER_X - a), min(WIDTH, CENTER_X + a)):
            dx = (x - CENTER_X) / a if a > 0 else 0
            dy = (y - CENTER_Y) / b if b > 0 else 0
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [80, 100, 80]
    
    # Rhea
    rhea_x = CENTER_X + int(beast_w * 0.1)
    rhea_y = CENTER_Y - int(beast_h * 0.25)
    
    for y in range(max(0, rhea_y - 15), min(HEIGHT, rhea_y + 15)):
        for x in range(max(0, rhea_x - 10), min(WIDTH, rhea_x + 10)):
            dx = (x - rhea_x) / 10
            dy = (y - rhea_y) / 15
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [80, 50, 30]
    
    # Head
    for y in range(max(0, rhea_y - 25), min(HEIGHT, rhea_y - 15)):
        for x in range(max(0, rhea_x - 8), min(WIDTH, rhea_x + 8)):
            dx = (x - rhea_x) / 8
            dy = (y - (rhea_y - 20)) / 10
            if dx*dx + dy*dy <= 1.0:
                frame[y, x] = [80, 50, 30]
    
    # Goggles
    for y in range(max(0, rhea_y - 27), min(HEIGHT, rhea_y - 25)):
        for x in range(max(0, rhea_x - 6), min(WIDTH, rhea_x + 6)):
            frame[y, x] = [200, 200, 200]
    
    # Lance
    for y in range(max(0, rhea_y - 10), min(HEIGHT, rhea_y - 5)):
        for x in range(max(0, rhea_x + 10), min(WIDTH, rhea_x + 60)):
            frame[y, x] = [150, 100, 60]
    
    # Maul
    for y in range(max(0, rhea_y - 15 - 5), min(HEIGHT, rhea_y - 15 + 10)):
        for x in range(max(0, rhea_x + 25 - 5), min(WIDTH, rhea_x + 25 + 5)):
            frame[y, x] = [180, 120, 80]
    
    return frame


# ============================================================
# MAIN
# ============================================================

def main():
    scenes = [
        (make_frame_title, 8, "Title"),
        (make_frame_glass_wastes, 8, "Glass-Wastes"),
        (make_frame_skiff, 8, "Dune-Skiff"),
        (make_frame_beast, 8, "Clock-Beast"),
        (make_frame_climbing, 12, "Rhea Climbing"),
        (make_frame_explosion, 8, "Explosion"),
        (make_frame_final, 8, "Final"),
    ]
    
    all_frames = []
    
    for scene_func, num_frames, scene_name in scenes:
        print(f"\nGenerating {scene_name} ({num_frames} frames)...")
        for i in range(num_frames):
            frame = scene_func(i)
            all_frames.append(frame)
            print(f"  Frame {i + 1}/{num_frames}")
    
    print(f"\nTotal frames: {len(all_frames)}")
    print("Creating video clip...")
    
    clip = ImageSequenceClip(all_frames, fps=FPS)
    
    output_path = "/workspace/glass_wastes_animation.mp4"
    print(f"Writing to {output_path}...")
    
    clip.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        bitrate='3000k',
        threads=1,
        preset='ultrafast',
        ffmpeg_params=['-pix_fmt', 'yuv420p', '-crf', '23']
    )
    
    print(f"\n✓ Animation complete!")
    print(f"  File: {output_path}")
    print(f"  Resolution: {WIDTH}x{HEIGHT}")
    print(f"  Duration: {DURATION} seconds")
    
    return output_path


if __name__ == "__main__":
    main()
