#!/usr/bin/env python3
"""
Daily Derja cover helper — the no-API path (parallels nesma_nagma_cover.py).

  overlay-title  composite the Arabic title (+ optional footer) onto an existing
                 cover (Amiri + raqm; cream scrim safety net if the band isn't clear).
  recolor-logo   export the Daily Derja logo recoloured to any colour, keeping its
                 alpha — handy when a cover wants the logo tinted to fit ("colours
                 could be changed to fit").

Both run on pillow alone (no API key).

  python daily_derja_cover.py overlay-title --base COVER.png --text "إشي مختلف" --out OUT.png [--restamp-footer] [--register maghrebi]
  python daily_derja_cover.py recolor-logo  --color "#264e8c" --out logo_cobalt.png
"""
from __future__ import annotations
import argparse, os, sys
from PIL import Image

from brand import get_register, overlay_only_title, DEFAULT_LOGO
from brand.frame import recolor_logo

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS_DIR = os.path.join(HERE, "covers")
ASSET_DIR = os.path.join(HERE, "assets", "logo")


def _color(s):
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]; return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(p) for p in s.replace(" ", "").split(","))


def cmd_overlay_title(a):
    reg = get_register(a.register)
    base = Image.open(a.base).convert("RGB")
    img, size = overlay_only_title(base, reg, a.text, footer=a.restamp_footer,
                                   footer_text=a.footer_text)
    os.makedirs(COVERS_DIR, exist_ok=True)
    out = a.out if os.path.isabs(a.out) else os.path.join(COVERS_DIR, a.out)
    img.save(out)
    print(f"wrote {out}  (title size {size})", file=sys.stderr)


def cmd_recolor_logo(a):
    logo = Image.open(a.logo or DEFAULT_LOGO)
    out_img = recolor_logo(logo, _color(a.color), opacity=a.opacity)
    os.makedirs(ASSET_DIR, exist_ok=True)
    out = a.out if os.path.isabs(a.out) else os.path.join(ASSET_DIR, a.out)
    out_img.save(out)
    print(f"wrote {out}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Daily Derja cover helper (no API)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("overlay-title")
    t.add_argument("--base", required=True)
    t.add_argument("--text", required=True)
    t.add_argument("--out", default="cover_out.png")
    t.add_argument("--register", default="levantine")
    t.add_argument("--restamp-footer", action="store_true")
    t.add_argument("--footer-text", default="dailyderja.com")
    t.set_defaults(func=cmd_overlay_title)

    r = sub.add_parser("recolor-logo")
    r.add_argument("--color", required=True, help="'r,g,b' or '#rrggbb'")
    r.add_argument("--logo", help="source logo (default assets/logo/daily_derja_logo.png)")
    r.add_argument("--opacity", type=float, default=1.0)
    r.add_argument("--out", default="daily_derja_logo_recolored.png")
    r.set_defaults(func=cmd_recolor_logo)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
