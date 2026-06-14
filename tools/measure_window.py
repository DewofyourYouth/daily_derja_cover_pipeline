#!/usr/bin/env python3
"""
Detect a template's content-window box by flat-cream cross-expansion from the centre.
Prints a [left, top, right, bottom] box to seed a templates.json entry.

  python tools/measure_window.py levantine_gold_A
  python tools/measure_window.py my_frame --seed 0.5,0.42 --debug
"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TDIR = os.path.join(HERE, "templates")


def measure(path, seed=(0.5, 0.42), tol=46):
    im = Image.open(path).convert("RGB"); W, H = im.size
    a = np.asarray(im).astype(int)
    cx, cy = int(W * seed[0]), int(H * seed[1])
    ref = np.median(a[cy - 8:cy + 8, cx - 8:cx + 8].reshape(-1, 3), axis=0)
    flat = lambda x, y: np.abs(a[y, x] - ref).sum() < tol
    l = cx
    while l > 1 and flat(l - 1, cy): l -= 1
    r = cx
    while r < W - 2 and flat(r + 1, cy): r += 1
    t = cy
    while t > 1 and flat(cx, t - 1): t -= 1
    b = cy
    while b < H - 2 and flat(cx, b + 1): b += 1
    return (W, H), [l, t, r, b]


def main():
    ap = argparse.ArgumentParser(description="Detect a template content window")
    ap.add_argument("name", help="template name (uses <name>_blank.jpg if present, else <name>.png)")
    ap.add_argument("--seed", default="0.5,0.42", help="seed point fx,fy in 0..1")
    ap.add_argument("--debug", action="store_true", help="write _measure_<name>.png with the box drawn")
    a = ap.parse_args()
    path = os.path.join(TDIR, f"{a.name}_blank.jpg")
    if not os.path.exists(path):
        path = os.path.join(TDIR, f"{a.name}.jpg")
    seed = tuple(float(x) for x in a.seed.split(","))
    (W, H), box = measure(path, seed)
    print(f"{a.name}: canvas {W}x{H}")
    print(f'  "window": {box},   # {box[2]-box[0]}x{box[3]-box[1]}')
    if a.debug:
        im = Image.open(path).convert("RGB"); ImageDraw.Draw(im).rectangle(box, outline=(0, 150, 255), width=6)
        out = os.path.join(TDIR, f"_measure_{a.name}.jpg"); im.save(out)
        print(f"  debug -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
