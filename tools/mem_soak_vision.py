"""Repeated recognition memory soak using synthetic faces (no camera needed)."""
import gc
import sys

import numpy as np
import psutil

from vision.detect import detect_face_grid

PROC = psutil.Process()

STICKER_RGB = {
    "W": (240, 240, 240), "Y": (250, 210, 40), "R": (200, 30, 40),
    "O": (240, 130, 30), "G": (30, 180, 70), "B": (30, 80, 220),
}


def render_face(colors, n=3, cell=48, border=6, bg=(30, 30, 30)):
    side = n * cell
    face = np.full((side, side, 3), bg, dtype=np.uint8)
    for r in range(n):
        for c in range(n):
            face[r * cell + border:(r + 1) * cell - border,
                 c * cell + border:(c + 1) * cell - border] = STICKER_RGB[colors[r][c]]
    pad = 40
    out = np.full((side + 2 * pad, side + 2 * pad, 3), bg, dtype=np.uint8)
    out[pad:pad + side, pad:pad + side] = face
    return out


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    patterns = [
        [["W", "R", "G"], ["Y", "W", "B"], ["O", "G", "R"]],
        [["Y", "O", "B"], ["G", "W", "R"], ["W", "B", "Y"]],
        [["R", "G", "W"], ["B", "Y", "O"], ["G", "R", "W"]],
    ]
    images = [render_face(p) for p in patterns]
    gc.collect()
    base = PROC.memory_info().rss / (1024 * 1024)
    print(f"baseline {base:.1f} MB")
    for i in range(1, count + 1):
        img = images[i % len(images)]
        detect_face_grid(img, 3)
        if i % 50 == 0:
            gc.collect()
            now = PROC.memory_info().rss / (1024 * 1024)
            print(f"{i:4d}: rss={now:7.1f} MB (+{now-base:5.1f})", flush=True)


if __name__ == "__main__":
    main()
