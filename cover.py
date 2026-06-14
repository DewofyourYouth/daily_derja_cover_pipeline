#!/usr/bin/env python3
"""
Daily Derja cover generator — headless, template-driven.

Pick a reusable Daily Derja FRAME (border + logo + dailyderja.com URL baked in
once), drop content into its window, and overlay the per-post Arabic title. The
branding is never regenerated — only the image and the title change.

Modes:
  photo   you supply a photo; it is smart-cropped (face-aware) to the template
          window, then placed. No API key needed.
  prompt  you supply a text prompt; the art is AI-generated in the chosen Daily
          Derja register, placed in the window. Optionally a reference photo of
          you is passed so you appear in the scene (you pick which one). Use --art
          to place a pre-generated image (offline / re-frame).
  title   overlay/replace just the Arabic title on an existing cover.
  templates   list the available frames.

Examples:
  python cover.py templates
  python cover.py photo  --photo photos/photo_10.jpeg --title "نَسمة بحر" --template levantine_gold_A --out sea.png
  python cover.py prompt --prompt "a glass of mint tea on a windowsill, jasmine outside" \
                         --title "شويّة هدوء" --template levantine_gold_B --out calm.png
  python cover.py prompt --art examples/base_minttea.png --title "شويّة هدوء" --template levantine_gold_A --out calm.png
  python cover.py title  --base covers/calm.png --title "هدوء" --template levantine_gold_A --out calm2.png
"""
from __future__ import annotations
import argparse, os, sys
from PIL import Image

from brand import (get_register, get_template, list_templates, REGISTRY,
                   compose_on_template, title_only_on_template,
                   load_photo, fit_to_window, build_prompt, generate_scene)

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS_DIR = os.path.join(HERE, "covers")
DEFAULT_TEMPLATE = "levantine_gold_A"


def log(*a):
    print(*a, file=sys.stderr)


def parse_color(s):
    if not s:
        return None
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(p) for p in s.replace(" ", "").split(","))


def parse_focus(s):
    return tuple(float(p) for p in s.split(",")) if s else None


def _ref_for_model(path, max_side=1024):
    im = load_photo(path)
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    return im


def _save(img, out_name):
    os.makedirs(COVERS_DIR, exist_ok=True)
    out = out_name if os.path.isabs(out_name) else os.path.join(COVERS_DIR, out_name)
    img.save(out)
    return out


def _aspect_of(spec):
    w, h = spec["canvas"]
    r = w / h
    return min(["16:9", "3:2", "4:5", "1:1", "9:16"],
               key=lambda k: abs({"16:9": 16/9, "3:2": 3/2, "4:5": 4/5, "1:1": 1, "9:16": 9/16}[k] - r))


# ------------------------------------------------------------------- modes
def run_photo(args):
    spec = get_template(args.template)
    l, t, r, b = spec["window"]
    ww, wh = r - l, b - t
    im = load_photo(args.photo)
    art = fit_to_window(im, ww, wh, manual_focus=parse_focus(args.focus), place=(0.5, 0.5))
    cover, size = compose_on_template(art, args.template, args.title,
                                      title_color=parse_color(args.title_color))
    out = _save(cover, args.out)
    log(f"[photo] {args.template} · title size {size} -> {out}")


def run_prompt(args):
    spec = get_template(args.template)
    if args.art:
        art = Image.open(args.art).convert("RGB")
    else:
        reg = get_register(args.register or spec.get("register", "levantine"))
        refs = []
        with_figure = args.with_figure
        if args.figure_photo:
            refs = [_ref_for_model(args.figure_photo)]
            with_figure = True
        scene = args.prompt or args.scene
        full = build_prompt(reg, scene, with_figure=with_figure,
                            figure_note=args.figure_note, extra=args.extra)
        if args.print_prompt:
            print(full)
        aspect = _aspect_of(spec)
        log(f"[prompt] generating via {args.provider} ({aspect}, {reg.label}) ...")
        art = generate_scene(full, provider=args.provider, aspect=aspect, references=refs)
        if args.save_intermediates:
            _save(art, "_stage1_" + args.out)
    cover, size = compose_on_template(art, args.template, args.title,
                                      title_color=parse_color(args.title_color))
    out = _save(cover, args.out)
    log(f"[prompt] {args.template} · title size {size} -> {out}  (REVIEW before publishing)")


def run_title(args):
    base = Image.open(args.base).convert("RGB")
    cover, size = title_only_on_template(base, args.template, args.title,
                                         title_color=parse_color(args.title_color))
    out = _save(cover, args.out)
    log(f"[title] {args.template} · title size {size} -> {out}")


def run_templates(args):
    print("Available templates:")
    for name in list_templates():
        print(f"  {name:22s} {REGISTRY[name].get('label', '')}")


# ------------------------------------------------------------------- cli
def add_common(p, need_title=True):
    p.add_argument("--title", required=need_title, default="", help="Arabic title (raw Unicode; tashkeel ok)")
    p.add_argument("--template", default=DEFAULT_TEMPLATE, help=f"frame name (default {DEFAULT_TEMPLATE}; see `templates`)")
    p.add_argument("--out", default="cover_out.png", help="output filename (written to covers/)")
    p.add_argument("--title-color", help="override title colour 'r,g,b' or '#hex'")


def main():
    ap = argparse.ArgumentParser(description="Daily Derja headless cover generator (template-driven)")
    sub = ap.add_subparsers(dest="mode", required=True)

    sub.add_parser("templates", help="list available frames").set_defaults(func=run_templates)

    p = sub.add_parser("photo", help="drop a supplied photo into a template (no API key)")
    add_common(p)
    p.add_argument("--photo", required=True, help="path to the photo")
    p.add_argument("--focus", help="manual focus 'fx,fy' in 0..1 (overrides face detect)")
    p.set_defaults(func=run_photo)

    p = sub.add_parser("prompt", help="generate art from a prompt, then place it in a template")
    add_common(p)
    p.add_argument("--prompt", help="the concrete scene to generate")
    p.add_argument("--scene", help="alias for --prompt")
    p.add_argument("--art", help="place this pre-generated image instead of calling the API")
    p.add_argument("--register", help="levantine | maghrebi (defaults to the template's register)")
    p.add_argument("--provider", choices=["gemini", "openai"], default="gemini")
    p.add_argument("--with-figure", action="store_true", help="include Jacob in the scene (figure rules apply)")
    p.add_argument("--figure-photo", help="reference photo of Jacob (implies --with-figure)")
    p.add_argument("--figure-note", default="", help="extra figure direction")
    p.add_argument("--extra", default="", help="freeform additions to the prompt")
    p.add_argument("--print-prompt", action="store_true")
    p.add_argument("--save-intermediates", action="store_true")
    p.set_defaults(func=run_prompt)

    p = sub.add_parser("title", help="overlay just the title on an existing cover")
    add_common(p)
    p.add_argument("--base", required=True, help="existing cover to restamp")
    p.set_defaults(func=run_title)

    args = ap.parse_args()
    if args.mode == "prompt" and not (args.prompt or args.scene or args.art):
        ap.error("prompt mode requires --prompt (or --scene), or --art to place an existing image")
    args.func(args)


if __name__ == "__main__":
    main()
