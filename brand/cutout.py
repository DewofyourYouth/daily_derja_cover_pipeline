#!/usr/bin/env python3
"""
Turn a mnemonic illustration (figure on a flat background, optionally inside a
coloured border like the teal Word-Breeze ring) into a clean transparent cutout
of just the figure — so it can be composited onto a template's cream window with
no illustration "block" or border showing.

Two steps:
  1. trim a uniform coloured border ring (e.g. the teal frame) if present
  2. flood-fill the flat background from the edges to transparent — edge-connected
     only, so light areas INSIDE the figure (e.g. the white of a keffiyeh) survive

Pure pillow + numpy (no heavy deps). Used by `word` mode before compositing.
"""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def trim_border(img: Image.Image) -> Image.Image:
    """Crop a saturated teal/cyan border ring (the Word-Breeze frame) if present."""
    a = np.asarray(img.convert("RGB")).astype(int)
    h, w = a.shape[:2]
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    teal = (B > R + 18) & (G > R + 12) & (R < 150)
    def first_clear(is_border, n):
        for i in range(n):
            if not is_border(i):
                return i
        return 0
    cl = first_clear(lambda i: teal[:, i].mean() > 0.25, w // 5)
    cr = first_clear(lambda i: teal[:, w - 1 - i].mean() > 0.25, w // 5)
    ct = first_clear(lambda i: teal[i, :].mean() > 0.25, h // 5)
    cb = first_clear(lambda i: teal[h - 1 - i, :].mean() > 0.25, h // 5)
    if max(cl, cr, ct, cb) == 0:
        return img
    pad = 6
    return img.crop((cl + pad, ct + pad, w - cr - pad, h - cb - pad))


def cutout_figure(img: Image.Image, thresh: int = 60, feather: float = 1.4) -> Image.Image:
    """Flood-fill the flat background (connected to the edges) to transparent and
    crop to the figure. Returns an RGBA image."""
    img = img.convert("RGB")
    W, H = img.size
    work = img.copy()
    SENT = (255, 0, 255)
    seeds = [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1),
             (W // 2, 0), (W // 2, H - 1), (0, H // 2), (W - 1, H // 2)]
    for s in seeds:
        try:
            ImageDraw.floodfill(work, s, SENT, thresh=thresh)
        except Exception:
            pass
    arr = np.asarray(work)
    bg = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 255)
    # also key out ANY teal/cyan pixel (the Word-Breeze border) — the figure has none,
    # so this clears border remnants the flood-fill / rectangle trim leaves behind
    o = np.asarray(img).astype(int)
    R, G, B = o[:, :, 0], o[:, :, 1], o[:, :, 2]
    teal = (B > R + 18) & (G > R + 12) & (R < 150)
    alpha = np.where(bg | teal, 0, 255).astype("uint8")
    A = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(feather))
    out = img.convert("RGBA")
    out.putalpha(A)
    ys, xs = np.where(alpha > 10)
    if len(xs):
        out = out.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return out


def prepare_mnemonic(img: Image.Image) -> Image.Image:
    """Border-trim then background-cut a mnemonic illustration into a clean RGBA figure."""
    return cutout_figure(trim_border(img))
