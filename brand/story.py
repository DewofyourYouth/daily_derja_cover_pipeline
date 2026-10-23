"""
Instagram story card (1080x1920) for a dailyderja post bundle.

The site's "Share to Instagram story" button hands this file to the phone's
share sheet, so it lives in the bundle as `story.jpg` beside `featured.*`.

Layout, top to bottom on the register's paper:

  * the register's tile band (Ablaq / khatam) along the top and bottom edges,
  * the post's cover, whole: covers are finished frames with the title, logo
    and URL baked in, so they are contain-fit, never cropped,
  * the series name (e.g. «نسمة كلمة») as a small kicker in the register accent,
  * the post's `pullquote` large in Amiri: a line of real Shami is the hook,
  * the post title, smaller, in sepia,
  * dailyderja.com.

Text is kept between y≈200 and y≈1740, clear of Instagram's profile bar and
reply field. Arabic follows the brand rule: raw Unicode through RAQM with
direction/language set, never reshaped by hand. The pullquote is wrapped here
(greedy, by measured width) because RAQM lays out one line at a time.
"""

from __future__ import annotations
import os, re
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw

from .frame import _font, ensure_font, tile_strip, _TASHKEEL
from .registers import Register, LEVANTINE, MAGHREBI, TITLE_COLOR, FOOTER_COLOR, FOOTER_TEXT

W, H = 1080, 1920
BAND = 34  # tile band height
SAFE_TOP, SAFE_BOTTOM = 200, 1740  # Instagram overlays above / below these
MARGIN = 60
_ARABIC = re.compile("[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")


# --------------------------------------------------------------------- frontmatter
def read_frontmatter(index_md: str) -> Dict[str, object]:
    """The handful of fields the card needs, without a YAML dependency: top-level
    scalars (quotes stripped) and simple `- item` lists."""
    with open(index_md, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    data: Dict[str, object] = {}
    key: Optional[str] = None
    for line in m.group(1).splitlines():
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if top:
            key, val = top.group(1), top.group(2).strip()
            data[key] = val.strip("\"'") if val else []
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key and isinstance(data.get(key), list):
            data[key].append(item.group(1).strip().strip("\"'"))
    return data


def register_for(fm: Dict[str, object]) -> Register:
    dialects = fm.get("dialects") or []
    if isinstance(dialects, str):
        dialects = [dialects]
    return MAGHREBI if "tunisian" in dialects and "shami" not in dialects else LEVANTINE


def find_cover(post_dir: str) -> Optional[str]:
    for name in sorted(os.listdir(post_dir)):
        if re.match(r"featured\.(jpe?g|png|webp)$", name, re.I):
            return os.path.join(post_dir, name)
    return None


# --------------------------------------------------------------------- text
def _dir(text: str) -> Tuple[str, str]:
    return ("rtl", "ar") if _ARABIC.search(text) else ("ltr", "en")


def _width(d: ImageDraw.ImageDraw, text: str, size: int) -> float:
    direction, lang = _dir(text)
    bare = _TASHKEEL.sub("", text) or text
    return d.textlength(bare, font=_font(size), direction=direction, language=lang)


def _wrap(d: ImageDraw.ImageDraw, text: str, size: int, max_w: int) -> List[str]:
    lines: List[str] = []
    for word in text.split():
        trial = f"{lines[-1]} {word}" if lines else word
        if lines and _width(d, trial, size) <= max_w:
            lines[-1] = trial
        else:
            lines.append(word)
    return lines


def _balance(d: ImageDraw.ImageDraw, text: str, size: int, max_w: int) -> List[str]:
    """Wrap into as few lines as fit, then narrow the measure as far as it goes
    without adding a line, so a quote never ends on one stranded word."""
    lines = _wrap(d, text, size, max_w)
    lo, hi = max_w // 3, max_w
    while lo < hi:
        mid = (lo + hi) // 2
        if len(_wrap(d, text, size, mid)) <= len(lines):
            hi = mid
        else:
            lo = mid + 1
    return _wrap(d, text, size, hi)


def _fit_block(
    d: ImageDraw.ImageDraw, text: str, start: int, max_w: int, max_h: int,
    max_lines: int, min_size: int = 40, leading: float = 1.55,
) -> Tuple[int, List[str]]:
    """Largest size (stepping down from `start`) whose balanced lines fit."""
    size = start
    while True:
        lines = _balance(d, text, size, max_w)
        if (len(lines) <= max_lines and len(lines) * size * leading <= max_h) or size <= min_size:
            return size, lines
        size -= 4


def _draw_lines(
    d: ImageDraw.ImageDraw, lines: List[str], size: int, top: int, color,
    leading: float = 1.55,
) -> int:
    """Draw centred lines from `top`; return the y below the block."""
    step = int(size * leading)
    y = top + step // 2
    for line in lines:
        direction, lang = _dir(line)
        d.text((W // 2, y), line, font=_font(size), fill=color, anchor="mm",
               direction=direction, language=lang)
        y += step
    return top + step * len(lines)


# --------------------------------------------------------------------- card
def make_story(post_dir: str, out: Optional[str] = None) -> str:
    index_md = os.path.join(post_dir, "index.md")
    fm = read_frontmatter(index_md)
    reg = register_for(fm)
    cover_path = find_cover(post_dir)
    if not cover_path:
        raise FileNotFoundError(f"no featured.* image in {post_dir}")
    ensure_font()

    canvas = Image.new("RGB", (W, H), reg.paper)
    band = tile_strip(W, BAND, reg)
    canvas.paste(band, (0, 0))
    canvas.paste(band, (0, H - BAND))
    d = ImageDraw.Draw(canvas)

    # cover, whole, with a keyline
    cover = Image.open(cover_path).convert("RGB")
    cw = W - 2 * 40
    ch = round(cover.height * cw / cover.width)
    ch = min(ch, 760)
    cw = round(cover.width * ch / cover.height)
    cover = cover.resize((cw, ch), Image.LANCZOS)
    cx, cy = (W - cw) // 2, SAFE_TOP + 30
    canvas.paste(cover, (cx, cy))
    d.rectangle([cx - 3, cy - 3, cx + cw + 2, cy + ch + 2], outline=reg.keyline, width=2)
    y = cy + ch + 70

    accent = reg.tile_palette[3] if reg is LEVANTINE else reg.tile_palette[0]
    series = fm.get("series") or []
    series = series[0] if isinstance(series, list) and series else (series or "")

    title = str(fm.get("title") or "")
    quote = str(fm.get("pullquote") or "")
    footer_y = SAFE_BOTTOM - 20
    space = footer_y - 90 - y  # between the cover and the footer
    room = space  # what's left for quote + title

    # Size everything first, then centre the block in the space below the cover.
    blocks = []  # (size, lines, color, leading, gap_after)
    if series:
        blocks.append((40, [series], accent, 1.4, 28))
        room -= int(40 * 1.4) + 28
    if quote:
        q = f"«{quote}»" if _dir(quote)[0] == "rtl" else f"“{quote}”"
        size, lines = _fit_block(d, q, 84, W - 2 * MARGIN, int(room * 0.72), max_lines=4)
        blocks.append((size, lines, TITLE_COLOR, 1.55, 24))
        if title:
            used = int(len(lines) * size * 1.55) + 24
            tsize, tlines = _fit_block(d, title, 46, W - 2 * MARGIN, room - used,
                                       max_lines=2, min_size=30, leading=1.4)
            blocks.append((tsize, tlines, FOOTER_COLOR, 1.4, 0))
    elif title:
        size, lines = _fit_block(d, title, 80, W - 2 * MARGIN, room, max_lines=3)
        blocks.append((size, lines, TITLE_COLOR, 1.55, 0))

    total = sum(int(sz * ld) * len(ls) + gap for sz, ls, _, ld, gap in blocks)
    y += max(0, (space - total) // 2)
    for sz, ls, color, ld, gap in blocks:
        y = _draw_lines(d, ls, sz, y, color, leading=ld) + gap

    d.text((W // 2, footer_y), FOOTER_TEXT, font=_font(36), fill=FOOTER_COLOR,
           anchor="ms", direction="ltr", language="en")

    out = out or os.path.join(post_dir, "story.jpg")
    canvas.save(out, "JPEG", quality=88, optimize=True)
    return out
