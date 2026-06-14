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
                        keyline: bool = True, kicker: Optional[str] = None) -> Tuple[Image.Image, int]:
    """Drop `content` into the template's window and overlay the title. The border,
    logo and URL come from the baked frame asset.

    `kicker` (e.g. 'نسمة كلمة') switches on the word-series layout: a small series line
    above the large word, given extra vertical room in the window."""
    spec = get_template(name)
    frame = Image.open(os.path.join(TEMPLATES_DIR, spec["file"])).convert("RGBA")
    l, t, r, b = spec["window"]
    ww, wh = r - l, b - t
    base = frame.copy()
    if content is not None:                       # leave the frame's cream window if no content
        if content.mode == "RGBA" and content.getextrema()[3][0] < 250:
            # transparent figure cutout — contain-fit, bottom-align, composite onto the cream window
            cw, ch = content.size
            s = min(ww / cw, wh / ch) * 0.97
            fig = content.resize((max(1, int(cw * s)), max(1, int(ch * s))), Image.LANCZOS)
            px = l + (ww - fig.width) // 2
            py = t + (wh - fig.height) - int(wh * 0.02)
            base.alpha_composite(fig, (px, py))
        else:                                     # opaque content fills the window
            base.paste(cover_fit(content, ww, wh).convert("RGB"), (l, t))
            if keyline:                           # crisp the content/border seam
                ImageDraw.Draw(base).rectangle([l, t, r - 1, b - 1], outline=GOLD_KEYLINE, width=3)
    H = base.size[1]
    ts = spec["title"]
    color = title_color or tuple(ts["color"])

    word_panel = spec.get("word_panel")
    if word_panel:                                # dedicated word-series frame: series header is
        wl, wt, wr, wb = word_panel               # baked in; render the WORD large, no kicker
        target = int(ts.get("size_f", 0.20) * H)
        base, size = draw_title_at(
            base, title, (wl + wr) // 2, (wt + wb) // 2,
            int((wr - wl) * ts.get("max_w_f", 0.84)), int((wb - wt) * ts.get("max_h_f", 0.74)),
            color=color, target_size=target)
        return base.convert("RGB"), size

    cx, cy, max_w, max_h, _ = _title_geom(spec)
    if kicker:                                     # word series on a general template: kicker + word
        cy = int(t + 0.25 * wh)
        max_h = int(0.50 * wh)
    target = int(ts.get("size_f", 0.115) * H)
    base, size = draw_title_at(base, title, cx, cy, max_w, max_h, color=color,
                               target_size=target, kicker=kicker, kicker_color=color)
    return base.convert("RGB"), size


def title_only_on_template(base_img: Image.Image, name: str, title: str,
                           title_color: Optional[Tuple[int, int, int]] = None,
                           kicker: Optional[str] = None) -> Tuple[Image.Image, int]:
    """Re-stamp just the title on an existing cover built from `name` (fix a typo
    without re-dropping content). `kicker` enables the word-series layout."""
    spec = get_template(name)
    cx, cy, max_w, max_h, ts = _title_geom(spec)
    if kicker:
        l, t, r, b = spec["window"]
        wh = b - t
        cy = int(t + 0.25 * wh)
        max_h = int(0.50 * wh)
    H = base_img.size[1]
    target = int(ts.get("size_f", 0.115) * H)
    color = title_color or tuple(ts["color"])
    return draw_title_at(base_img.convert("RGBA"), title, cx, cy, max_w, max_h,
                         color=color, target_size=target, kicker=kicker, kicker_color=color)
