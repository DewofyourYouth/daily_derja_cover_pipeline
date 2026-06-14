#!/usr/bin/env python3
"""
Smart crop / fit for photo mode.

Fits a supplied photo into the template window "in the best way possible":

  1. honours EXIF orientation,
  2. finds a focus point — a detected face if OpenCV is installed, otherwise an
     upper-centre point that flatters portraits,
  3. crops to the window's aspect ratio around that focus (with gentle headroom),
  4. scales to the exact window size.

OpenCV is OPTIONAL. Without it, the upper-centre fallback is used — good enough
for the head-and-shoulders selfies in photos/. Install opencv-python-headless to
enable face-aware centring. A manual --focus FX,FY (each 0..1) always overrides.
"""
from __future__ import annotations
from typing import Optional, Tuple
from PIL import Image, ImageOps


def load_photo(path: str) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def detect_face_box(im: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """Return the largest frontal-face box (x, y, w, h), or None if unavailable."""
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None
    try:
        arr = np.asarray(im.convert("RGB"))[:, :, ::-1]  # RGB -> BGR
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6,
                                         minSize=(int(im.width * 0.08), int(im.height * 0.08)))
        if len(faces) == 0:
            return None
        return tuple(max(faces, key=lambda f: f[2] * f[3]))  # largest by area
    except Exception:
        return None


def focus_point(im: Image.Image, manual: Optional[Tuple[float, float]] = None) -> Tuple[float, float]:
    """Normalised (fx, fy) focus point in [0,1]."""
    if manual is not None:
        fx, fy = manual
        return (min(max(fx, 0.0), 1.0), min(max(fy, 0.0), 1.0))
    box = detect_face_box(im)
    if box is not None:
        x, y, w, h = box
        return ((x + w / 2) / im.width, (y + h * 0.45) / im.height)  # eyes a touch above box centre
    # fallback: portraits read best with the subject in the upper-middle
    return (0.5, 0.40 if im.height >= im.width else 0.5)


def fit_to_window(im: Image.Image, win_w: int, win_h: int,
                  manual_focus: Optional[Tuple[float, float]] = None,
                  place: Tuple[float, float] = None) -> Image.Image:
    """
    Crop `im` to the window aspect around its focus point, then resize to (win_w, win_h).

    place: where the focus should land inside the window, as (px, py) fractions.
           Defaults to (0.5, 0.42) — centred horizontally, slightly above centre,
           so faces sit on the upper third with a little headroom.
    """
    im = ImageOps.exif_transpose(im).convert("RGB")
    W, H = im.size
    fx, fy = focus_point(im, manual_focus)
    px, py = place if place else (0.5, 0.42)
    target_ar = win_w / win_h
    src_ar = W / H

    if src_ar > target_ar:                 # too wide -> crop width
        new_w, new_h = int(round(H * target_ar)), H
    else:                                  # too tall -> crop height
        new_w, new_h = W, int(round(W / target_ar))

    x0 = int(round(fx * W - px * new_w))
    y0 = int(round(fy * H - py * new_h))
    x0 = max(0, min(x0, W - new_w))
    y0 = max(0, min(y0, H - new_h))
    crop = im.crop((x0, y0, x0 + new_w, y0 + new_h))
    return crop.resize((win_w, win_h), Image.LANCZOS)
