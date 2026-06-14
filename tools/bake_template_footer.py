#!/usr/bin/env python3
"""
Bake the Daily Derja logo + dailyderja.com into a template's bottom cartouche.

Reads templates/<name>_blank.jpg (the ornate frame with an empty cartouche), auto-
detects the cartouche, and composites a logo+URL lockup into it — HORIZONTAL (logo
beside URL) when the cartouche is wide, STACKED (logo above URL) when it's narrow/tall.
Writes templates/<name>.jpg. Keep the _blank so you can re-bake (e.g. recolour).

  python tools/bake_template_footer.py maghrebi_bougainvillea --register maghrebi
  python tools/bake_template_footer.py levantine_gold_A --register levantine
  python tools/bake_template_footer.py my_frame --logo-color "#264e8c" --url-color "#264e8c"
"""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TDIR = os.path.join(HERE, "templates")
AMIRI = os.path.join(HERE, "fonts", "Amiri-Regular.ttf")
LOGO = os.path.join(HERE, "assets", "logo", "daily_derja_logo.png")
URL = "dailyderja.com"
COLORS = {"levantine": ((150, 50, 45), (95, 55, 38)), "maghrebi": ((38, 78, 140), (38, 78, 140))}


def _color(s):
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]; return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(p) for p in s.replace(" ", "").split(","))


def amiri(s):
    return ImageFont.truetype(AMIRI, s, layout_engine=ImageFont.Layout.RAQM)


def recolor(logo, color):
    logo = logo.convert("RGBA"); a = logo.split()[3]
    s = Image.new("RGBA", logo.size, color + (0,)); s.putalpha(a); return s


def text_dims(size):
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    bb = d.textbbox((0, 0), URL, font=amiri(size), direction="ltr", language="en")
    return bb[2] - bb[0], bb[3] - bb[1]


def detect_cartouche(a, W, H, win_bottom):
    """Largest flat-cream box in the bottom band, below the content window."""
    for fy in [0.84, 0.85, 0.86, 0.87, 0.88, 0.83, 0.89, 0.82]:
        cx, cy = int(W * 0.5), int(H * fy)
        ref = np.median(a[cy - 6:cy + 6, cx - 6:cx + 6].reshape(-1, 3), axis=0)
        flat = lambda x, y: np.abs(a[y, x] - ref).sum() < 46
        if not flat(cx, cy):
            continue
        l = cx
        while l > 1 and flat(l - 1, cy): l -= 1
        r = cx
        while r < W - 2 and flat(r + 1, cy): r += 1
        t = cy
        while t > 1 and flat(cx, t - 1): t -= 1
        b = cy
        while b < H - 2 and flat(cx, b + 1): b += 1
        if (r - l) > 200 and (b - t) > 45 and t > win_bottom - 40:
            return [l, t, r, b]
    return [int(W * 0.36), int(H * 0.83), int(W * 0.64), int(H * 0.90)]


def bake(name, logo_color, url_color, win_bottom):
    fr = Image.open(os.path.join(TDIR, f"{name}_blank.jpg")).convert("RGBA")
    W, H = fr.size
    a = np.asarray(fr.convert("RGB")).astype(int)
    l, t, r, b = detect_cartouche(a, W, H, win_bottom)
    cw, chh, ccx, ccy = r - l, b - t, (l + r) // 2, (t + b) // 2
    logo_im = Image.open(LOGO).convert("RGBA")
    d = ImageDraw.Draw(fr)
    gap = 18
    tw54, _ = text_dims(54)
    horizontal = cw >= 0.92 * (int(54 * 1.5) + gap + tw54)
    if horizontal:
        us = min(int(chh * 0.50), 60)
        while us > 40:
            lh = int(us * 1.5); tw, th = text_dims(us)
            if lh + gap + tw <= cw * 0.90 and lh <= chh * 0.86:
                break
            us -= 2
        lh = int(us * 1.5); tw, th = text_dims(us)
        lw = int(logo_im.width * lh / logo_im.height)
        lg = recolor(logo_im.resize((lw, lh), Image.LANCZOS), logo_color)
        gw = lw + gap + tw; gx = ccx - gw // 2
        fr.alpha_composite(lg, (gx, ccy - lh // 2))
        d.text((gx + lw + gap + tw // 2, ccy), URL, font=amiri(us), fill=url_color,
               anchor="mm", direction="ltr", language="en")
        mode = "horizontal"
    else:
        us = min(int(chh * 0.34), 52)
        while us > 30:
            tw, th = text_dims(us); lh = int(us * 1.35); vgap = int(us * 0.22)
            if tw <= cw * 0.86 and (lh + vgap + th) <= chh * 0.90 and lh <= cw * 0.70:
                break
            us -= 2
        tw, th = text_dims(us); lh = int(us * 1.35); vgap = int(us * 0.22)
        lw = int(logo_im.width * lh / logo_im.height)
        lg = recolor(logo_im.resize((lw, lh), Image.LANCZOS), logo_color)
        total = lh + vgap + th; ytop = ccy - total // 2
        fr.alpha_composite(lg, (ccx - lw // 2, ytop))
        d.text((ccx, ytop + lh + vgap + th // 2), URL, font=amiri(us), fill=url_color,
               anchor="mm", direction="ltr", language="en")
        mode = "stacked"
    out = os.path.join(TDIR, f"{name}.jpg")
    fr.convert("RGB").save(out)
    print(f"{name}: cartouche {cw}x{chh} -> {mode} footer (url size {us}) -> {out}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Bake logo + URL into a template cartouche")
    ap.add_argument("name", help="template name (expects templates/<name>_blank.jpg)")
    ap.add_argument("--register", choices=["levantine", "maghrebi"], default="levantine")
    ap.add_argument("--logo-color", help="override 'r,g,b' or '#hex'")
    ap.add_argument("--url-color", help="override 'r,g,b' or '#hex'")
    ap.add_argument("--win-bottom", type=int, help="content window bottom Y (helps place the cartouche below it)")
    a = ap.parse_args()
    lc, uc = COLORS[a.register]
    if a.logo_color: lc = _color(a.logo_color)
    if a.url_color: uc = _color(a.url_color)
    win_bottom = a.win_bottom
    if win_bottom is None:
        reg = json.load(open(os.path.join(TDIR, "templates.json"), encoding="utf-8"))
        win_bottom = reg.get(a.name, {}).get("window", [0, 0, 0, int(0.73 * 1536)])[3]
    bake(a.name, lc, uc, win_bottom)


if __name__ == "__main__":
    main()
