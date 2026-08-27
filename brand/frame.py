#!/usr/bin/env python3
"""
The Daily Derja template layer (full-bleed model).

The photo / generated art fills the whole canvas as the hero. The brand layer is
OVERLAID:

  * a thin geometric tile border hugging the TOP and BOTTOM edges only
    (Ablaq for Levantine, eight-pointed-star khatam for Maghrebi),
  * the Arabic episode title in the upper area,
  * the dailyderja.com footer at the bottom,
  * the Daily Derja logo in a corner (recoloured to fit; soft cream halo so it
    reads over any background).

A soft, feathered cream scrim is laid behind the title / footer only when the
pixels underneath would hurt legibility for the dark sepia type — never a hard
plate (brand rule: no multi-line plate).

Arabic rendering follows the standing rules (identical to nesma_nagma): raw
Unicode, layout_engine=RAQM, direction='rtl', language='ar'; width is measured on
the consonant skeleton (tashkeel stripped). Title sepia (70,45,30); footer warm
sepia-brown (130,80,50).
"""
from __future__ import annotations
import math, os, re, urllib.request
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, features

from .registers import (Register, Layout, LAYOUT, TITLE_COLOR, FOOTER_COLOR, FOOTER_TEXT,
                        DEFAULT_W, DEFAULT_H)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(HERE, "fonts")
DEFAULT_LOGO = os.path.join(HERE, "assets", "logo", "daily_derja_logo.png")
CREAM = (249, 245, 236)

# Title typefaces, keyed by the name a template declares in its title.font spec.
# Each entry is (local filename, Google-Fonts OFL download URL) — fetched on first
# use, exactly like Amiri was. DEFAULT_FONT (Amiri) is used when a template omits
# title.font, so existing frames render unchanged.
FONTS = {
    "Amiri":    ("Amiri-Regular.ttf",  "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"),
    "ReemKufi": ("ReemKufi.ttf",        "https://github.com/google/fonts/raw/main/ofl/reemkufi/ReemKufi%5Bwght%5D.ttf"),
    "Lalezar":  ("Lalezar-Regular.ttf", "https://github.com/google/fonts/raw/main/ofl/lalezar/Lalezar-Regular.ttf"),
}
DEFAULT_FONT = "Amiri"

# Arabic diacritics / marks + tatweel ONLY (must NOT include the letter block 0620–064A).
_TASHKEEL = re.compile("[ؐ-ؚـً-ٰٟۖ-ۜ۟-۪ۨ-ۭ]")


# --------------------------------------------------------------------- fonts
def ensure_font(name: str = DEFAULT_FONT) -> str:
    """Ensure the named title font is on disk (download on first use) and return
    its path. Unknown names fall back to Amiri so a bad title.font never crashes."""
    fname, url = FONTS.get(name) or FONTS[DEFAULT_FONT]
    path = os.path.join(FONT_DIR, fname)
    if not os.path.exists(path):
        os.makedirs(FONT_DIR, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    assert features.check_feature("raqm"), (
        "PIL raqm/HarfBuzz unavailable — reinstall Pillow from the official wheels")
    return path


def _font(size: int, name: str = DEFAULT_FONT) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(ensure_font(name), size, layout_engine=ImageFont.Layout.RAQM)


# --------------------------------------------------------------------- tiles
def _ablaq_strip(w: int, h: int, reg: Register) -> Image.Image:
    """Alternating light/dark stones — the Levantine Ablaq band."""
    light, dark = reg.tile_palette[0], reg.tile_palette[1]
    strip = Image.new("RGB", (w, h), light)
    d = ImageDraw.Draw(strip)
    bw = max(h, 28)
    for i, x in enumerate(range(0, w, bw)):
        if i % 2 == 1:
            d.rectangle([x, 0, x + bw - 1, h - 1], fill=dark)
        d.line([(x, 0), (x, h)], fill=reg.keyline, width=2)
    d.rectangle([0, 0, w - 1, h - 1], outline=reg.keyline, width=3)
    return strip


def _star8(d: ImageDraw.ImageDraw, cx: float, cy: float, R: float, fill, outline):
    """Eight-pointed khatam star = two overlapping squares."""
    for rot in (0.0, math.pi / 4):
        pts = [(cx + R * math.cos(rot + k * math.pi / 2), cy + R * math.sin(rot + k * math.pi / 2))
               for k in range(4)]
        d.polygon(pts, fill=fill, outline=outline)


def _khatam_strip(w: int, h: int, reg: Register) -> Image.Image:
    """Eight-pointed-star zellige band — the Maghrebi / Sidi Bou Said register."""
    cobalt, white, saffron = reg.tile_palette[0], reg.tile_palette[1], reg.tile_palette[2]
    strip = Image.new("RGB", (w, h), white)
    d = ImageDraw.Draw(strip)
    cell = max(h, 30)
    R, rc = h * 0.46, h * 0.13
    for x in range(0, w + cell, cell):
        cx, cy = x + cell / 2, h / 2
        _star8(d, cx, cy, R, fill=cobalt, outline=reg.keyline)
        d.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], fill=saffron)
    d.rectangle([0, 0, w - 1, h - 1], outline=reg.keyline, width=3)
    return strip


def tile_strip(w: int, h: int, reg: Register) -> Image.Image:
    return _khatam_strip(w, h, reg) if reg.tile_style == "khatam" else _ablaq_strip(w, h, reg)


# --------------------------------------------------------------------- logo
def recolor_logo(logo: Image.Image, color: Tuple[int, int, int], opacity: float = 1.0) -> Image.Image:
    """Tint the black line-art logo to `color`, keeping its alpha — so the logo
    can be recoloured per register / per background ('colours could change to fit')."""
    logo = logo.convert("RGBA")
    alpha = logo.split()[3]
    if opacity < 1.0:
        alpha = alpha.point(lambda a: int(a * opacity))
    solid = Image.new("RGBA", logo.size, color + (0,))
    solid.putalpha(alpha)
    return solid


def place_logo(canvas: Image.Image, reg: Register, lay: Layout = LAYOUT,
               logo_path: str = DEFAULT_LOGO,
               color: Optional[Tuple[int, int, int]] = None,
               pos: Optional[str] = None, height_f: Optional[float] = None,
               opacity: float = 1.0, halo: Optional[bool] = None) -> Image.Image:
    if not logo_path or not os.path.exists(logo_path):
        return canvas
    W, H = canvas.size
    pos = pos or lay.logo_pos
    lh = int((height_f or lay.logo_h_f) * H)
    logo = Image.open(logo_path).convert("RGBA")
    lw = int(logo.width * lh / logo.height)
    logo = recolor_logo(logo.resize((lw, lh), Image.LANCZOS), color or reg.logo_color, opacity)
    m = int(lay.logo_margin_f * H)
    x = m if pos in ("tl", "bl") else W - lw - m
    y = m if pos in ("tl", "tr") else H - lh - m
    if (lay.logo_halo if halo is None else halo):
        pad = int(lh * 0.16)
        halo_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo_layer).ellipse(
            [x - pad, y - pad, x + lw + pad, y + lh + pad], fill=CREAM + (150,))
        halo_layer = halo_layer.filter(ImageFilter.GaussianBlur(int(lh * 0.10)))
        canvas.alpha_composite(halo_layer)
    canvas.alpha_composite(logo, (x, y))
    return canvas


# --------------------------------------------------------------------- legibility
def _legible(im: Image.Image, box, lay: Layout = LAYOUT) -> bool:
    """True if `box` is bright/clear enough for dark sepia text to read."""
    import numpy as np
    W, H = im.size
    x0, y0, x1, y1 = (max(0, int(box[0])), max(0, int(box[1])),
                      min(W, int(box[2])), min(H, int(box[3])))
    a = np.asarray(im.convert("RGB")).astype(int)[y0:y1, x0:x1]
    if a.size == 0:
        return True
    lum = a.mean(axis=2)
    return (lum.mean() >= lay.scrim_lum_min) and (float((lum < 150).mean()) < 0.10)


def _scrim(im: Image.Image, box, W: int) -> Image.Image:
    """Lay a soft feathered cream scrim behind text (legibility safety net)."""
    scrim = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(scrim).rounded_rectangle(box, radius=int(0.018 * W), fill=CREAM + (232,))
    scrim = scrim.filter(ImageFilter.GaussianBlur(int(0.012 * W)))
    return Image.alpha_composite(im.convert("RGBA"), scrim)


# --------------------------------------------------------------------- title + footer
def _fit_title_size(text_bare: str, max_w: int, max_h: int, lo: int = 48, hi: int = 640,
                    font: str = DEFAULT_FONT) -> int:
    tmp = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        b = tmp.textbbox((0, 0), text_bare, font=_font(mid, font), direction="rtl", language="ar")
        if (b[2] - b[0]) <= max_w and (b[3] - b[1]) <= max_h:
            best = mid; lo = mid + 1
        else:
            hi = mid - 1
    return best


def draw_title(canvas: Image.Image, reg: Register, title: str, lay: Layout = LAYOUT,
               color: Optional[Tuple[int, int, int]] = None,
               font: str = DEFAULT_FONT) -> Tuple[Image.Image, int]:
    """Overlay the Arabic title in the upper area; returns (canvas, size)."""
    if not title:
        return canvas, 0
    ensure_font(font)
    W, H = canvas.size
    cx, cy = W // 2, int(lay.title_cy_f * H)
    max_w = int(W * lay.title_max_w_f)
    bt, bb_ = lay.title_band_f
    max_h = int((bb_ - bt) * H * 0.80)
    bare = _TASHKEEL.sub("", title) or title
    # Fixed target size for series consistency; shrink ONLY if the title would
    # overflow the width or the safe vertical band (nesma behaviour).
    size = min(int(lay.title_size_f * H), _fit_title_size(bare, max_w, max_h, font=font))
    d = ImageDraw.Draw(canvas)
    bb = d.textbbox((cx, cy), title, font=_font(size, font), anchor="mm", direction="rtl", language="ar")
    padx, pady = int(0.028 * W), int(0.022 * H)
    box = (bb[0] - padx, bb[1] - pady, bb[2] + padx, bb[3] + pady)
    if not _legible(canvas, box, lay):
        canvas = _scrim(canvas, box, W).convert("RGBA")
        d = ImageDraw.Draw(canvas)
    d.text((cx, cy), title, font=_font(size, font), fill=color or TITLE_COLOR,
           anchor="mm", direction="rtl", language="ar")
    return canvas, size


def draw_title_at(canvas: Image.Image, title: str, cx: int, cy: int, max_w: int, max_h: int,
                  color: Tuple[int, int, int] = TITLE_COLOR, target_size: Optional[int] = None,
                  kicker: Optional[str] = None, kicker_color: Optional[Tuple[int, int, int]] = None,
                  lay: Layout = LAYOUT, font: str = DEFAULT_FONT) -> Tuple[Image.Image, int]:
    """Overlay an Arabic title centred at (cx, cy), fit within (max_w, max_h); cream
    scrim safety net if the area isn't legible. `font` is the title typeface name
    (see FONTS) the template declares, so the type matches the frame.

    If `kicker` is given (e.g. a series name like 'نسمة كلمة'), it is rendered small
    ABOVE the main word — the Daily Derja "word series" layout (series kicker + word)."""
    if not title:
        return canvas, 0
    ensure_font(font)
    W, H = canvas.size
    bare = _TASHKEEL.sub("", title) or title

    if not kicker:
        fit = _fit_title_size(bare, max_w, max_h, font=font)
        size = min(target_size, fit) if target_size else fit
        d = ImageDraw.Draw(canvas)
        bb = d.textbbox((cx, cy), title, font=_font(size, font), anchor="mm", direction="rtl", language="ar")
        padx, pady = int(0.026 * W), int(0.020 * H)
        box = (bb[0] - padx, bb[1] - pady, bb[2] + padx, bb[3] + pady)
        if not _legible(canvas, box, lay):
            canvas = _scrim(canvas, box, W).convert("RGBA")
            d = ImageDraw.Draw(canvas)
        d.text((cx, cy), title, font=_font(size, font), fill=color, anchor="mm", direction="rtl", language="ar")
        return canvas, size

    # --- word-series layout: small kicker line + large word, stacked & centred on cy ---
    word_fit = _fit_title_size(bare, max_w, int(max_h * 0.62), font=font)
    size = min(target_size, word_fit) if target_size else word_fit
    kbare = _TASHKEEL.sub("", kicker) or kicker
    ksize = max(26, int(size * 0.46))
    while ksize > 22:
        kb = _fit_title_size(kbare, int(max_w * 0.9), int(size * 0.6), font=font)
        ksize = min(ksize, kb); break
    d = ImageDraw.Draw(canvas)
    wbb = d.textbbox((cx, cy), title, font=_font(size, font), anchor="mm", direction="rtl", language="ar")
    kbb = d.textbbox((cx, cy), kicker, font=_font(ksize, font), anchor="mm", direction="rtl", language="ar")
    word_h, kick_h = wbb[3] - wbb[1], kbb[3] - kbb[1]
    gap = int(size * 0.16)
    total = kick_h + gap + word_h
    top = cy - total // 2
    kick_cy = top + kick_h // 2
    word_cy = top + kick_h + gap + word_h // 2
    # union legibility box across both lines
    x0 = min(wbb[0], kbb[0]) - int(0.026 * W)
    x1 = max(wbb[2], kbb[2]) + int(0.026 * W)
    box = (x0, top - int(0.012 * H), x1, top + total + int(0.012 * H))
    if not _legible(canvas, box, lay):
        canvas = _scrim(canvas, box, W).convert("RGBA")
        d = ImageDraw.Draw(canvas)
    d.text((cx, kick_cy), kicker, font=_font(ksize, font), fill=kicker_color or color,
           anchor="mm", direction="rtl", language="ar")
    d.text((cx, word_cy), title, font=_font(size, font), fill=color,
           anchor="mm", direction="rtl", language="ar")
    return canvas, size


def draw_footer(canvas: Image.Image, reg: Register, lay: Layout = LAYOUT,
                text: str = FOOTER_TEXT, color: Optional[Tuple[int, int, int]] = None) -> Image.Image:
    ensure_font()
    W, H = canvas.size
    fsize = int(lay.footer_size_f * H)
    d = ImageDraw.Draw(canvas)
    # footer stays Amiri — it is a constant brand mark, not the per-template title
    bb = d.textbbox((W // 2, int(lay.footer_baseline_f * H)), text, font=_font(fsize),
                    anchor="ms", direction="ltr", language="en")
    padx, pady = int(0.02 * W), int(0.014 * H)
    box = (bb[0] - padx, bb[1] - pady, bb[2] + padx, bb[3] + pady)
    if not _legible(canvas, box, lay):
        canvas = _scrim(canvas, box, W).convert("RGBA")
        d = ImageDraw.Draw(canvas)
    d.text((W // 2, int(lay.footer_baseline_f * H)), text, font=_font(fsize),
           fill=color or FOOTER_COLOR, anchor="ms", direction="ltr", language="en")
    return canvas


# --------------------------------------------------------------------- fit + compose
def cover_fit(im: Image.Image, w: int, h: int, centering=(0.5, 0.45)) -> Image.Image:
    """Resize + centre-crop `im` to exactly (w, h)."""
    return ImageOps.fit(im.convert("RGB"), (w, h), Image.LANCZOS, centering=centering)


def _overlay_border(canvas: Image.Image, reg: Register, lay: Layout) -> Image.Image:
    W, H = canvas.size
    th = int(lay.tile_h_f * H)
    kl = int(lay.art_keyline_f * H)
    canvas.alpha_composite(tile_strip(W, th, reg).convert("RGBA"), (0, 0))
    canvas.alpha_composite(tile_strip(W, th, reg).convert("RGBA"), (0, H - th))
    if kl > 0:                                              # thin cream rule between strip and art
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, th, W, th + kl], fill=CREAM + (255,))
        d.rectangle([0, H - th - kl, W, H - th], fill=CREAM + (255,))
    return canvas


def compose(content: Image.Image, reg: Register, title: str = "", *,
            canvas: Tuple[int, int] = (DEFAULT_W, DEFAULT_H),
            lay: Layout = LAYOUT, logo_path: str = DEFAULT_LOGO,
            footer: bool = True, footer_text: str = FOOTER_TEXT,
            logo_pos: Optional[str] = None, logo_color: Optional[Tuple[int, int, int]] = None,
            logo_height_f: Optional[float] = None, logo_halo: Optional[bool] = None,
            title_color: Optional[Tuple[int, int, int]] = None,
            footer_color: Optional[Tuple[int, int, int]] = None) -> Tuple[Image.Image, int]:
    """
    Assemble the full-bleed cover at `canvas` (W, H). `content` is fit to the
    canvas (used as-is if already exactly canvas-sized — e.g. a face-aware photo
    fit), then the tile border, title, footer and logo are overlaid.
    Returns (RGB image, title_size).
    """
    W, H = canvas
    art = content if content.size == (W, H) else cover_fit(content, W, H)
    cv = art.convert("RGBA")
    cv = _overlay_border(cv, reg, lay)
    cv, size = draw_title(cv, reg, title, lay, title_color)
    if footer:
        cv = draw_footer(cv, reg, lay, footer_text, footer_color)
    place_logo(cv, reg, lay, logo_path, logo_color, logo_pos, logo_height_f, halo=logo_halo)
    return cv.convert("RGB"), size


def overlay_only_title(base: Image.Image, reg: Register, title: str, lay: Layout = LAYOUT,
                       footer: bool = False, footer_text: str = FOOTER_TEXT,
                       title_color: Optional[Tuple[int, int, int]] = None,
                       footer_color: Optional[Tuple[int, int, int]] = None) -> Tuple[Image.Image, int]:
    """Stamp the title (and optional footer) onto an EXISTING cover without rebuilding
    the border/logo — the title-only path (no API key needed)."""
    cv = base.convert("RGBA")
    cv, size = draw_title(cv, reg, title, lay, title_color)
    if footer:
        cv = draw_footer(cv, reg, lay, footer_text, footer_color)
    return cv.convert("RGB"), size
