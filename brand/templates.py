#!/usr/bin/env python3
"""
Template registry — the reusable Daily Derja frames.

A template is a FINISHED branded frame asset (ornate border + Daily Derja logo +
dailyderja.com URL, all baked in once) plus a small spec describing where the
content window is and how the per-post Arabic title is placed. Generating a cover
is just: drop an image into the window + overlay the title. The border, logo and
URL are never regenerated.

Templates live in templates/ as <name>.png alongside templates.json. Add a new
frame by dropping its PNG in and adding a registry entry (window box + title spec)
— as long as it stays in the Daily Derja family, the branding stays consistent.

Registry entry:
  file       PNG filename in templates/
  register   levantine | maghrebi  (informs prompt-mode generation, not the frame)
  canvas     [W, H] of the frame
  window     [left, top, right, bottom] content box (inside the gold keyline)
  title      {top_f, max_w_f, max_h_f, size_f, color}  — fractions of the WINDOW
             (top_f, max_w_f, max_h_f) and of canvas H (size_f); color is the
             title RGB (Daily Derja covers use deep pomegranate, not sepia)
"""
from __future__ import annotations
import json, os
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw

from .frame import cover_fit, draw_title_at

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(HERE, "templates")
REGISTRY_PATH = os.path.join(TEMPLATES_DIR, "templates.json")
GOLD_KEYLINE = (176, 141, 87)

with open(REGISTRY_PATH, encoding="utf-8") as _f:
    REGISTRY: Dict[str, dict] = json.load(_f)


def list_templates() -> List[str]:
    return sorted(REGISTRY)


def get_template(name: str) -> dict:
    if name not in REGISTRY:
        raise SystemExit(f"unknown template '{name}' — choose from: {', '.join(list_templates())}")
    return REGISTRY[name]


def _title_geom(spec: dict):
    l, t, r, b = spec["window"]
    ww, wh = r - l, b - t
    ts = spec["title"]
    cx = (l + r) // 2
    cy = int(t + ts["top_f"] * wh)
    max_w = int(ts["max_w_f"] * ww)
    max_h = int(ts.get("max_h_f", 0.24) * wh)
    return cx, cy, max_w, max_h, ts


def compose_on_template(content: Image.Image, name: str, title: str = "",
                        title_color: Optional[Tuple[int, int, int]] = None,
                        keyline: bool = True) -> Tuple[Image.Image, int]:
    """Drop `content` into the template's window and overlay the title. The border,
    logo and URL come from the baked frame asset."""
    spec = get_template(name)
    frame = Image.open(os.path.join(TEMPLATES_DIR, spec["file"])).convert("RGBA")
    l, t, r, b = spec["window"]
    ww, wh = r - l, b - t
    base = frame.copy()
    base.paste(cover_fit(content, ww, wh).convert("RGB"), (l, t))
    if keyline:                                   # crisp the content/border seam
        ImageDraw.Draw(base).rectangle([l, t, r - 1, b - 1], outline=GOLD_KEYLINE, width=3)
    cx, cy, max_w, max_h, ts = _title_geom(spec)
    H = base.size[1]
    target = int(ts.get("size_f", 0.115) * H)
    color = title_color or tuple(ts["color"])
    base, size = draw_title_at(base, title, cx, cy, max_w, max_h, color=color, target_size=target)
    return base.convert("RGB"), size


def title_only_on_template(base_img: Image.Image, name: str, title: str,
                           title_color: Optional[Tuple[int, int, int]] = None) -> Tuple[Image.Image, int]:
    """Re-stamp just the title on an existing cover built from `name` (fix a typo
    without re-dropping content)."""
    spec = get_template(name)
    cx, cy, max_w, max_h, ts = _title_geom(spec)
    H = base_img.size[1]
    target = int(ts.get("size_f", 0.115) * H)
    color = title_color or tuple(ts["color"])
    return draw_title_at(base_img.convert("RGBA"), title, cx, cy, max_w, max_h,
                         color=color, target_size=target)
