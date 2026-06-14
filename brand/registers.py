#!/usr/bin/env python3
"""
Daily Derja brand registers — palettes, layout geometry, and per-register
visual + prompt specs.

The "template" the pipeline applies is a constant branding layer (cream paper,
a thin geometric tile border along the top and bottom edges, the Daily Derja
logo, the Arabic title, and the dailyderja.com footer) plus a window in the
middle that holds either a supplied photo or AI-generated art. Both modes use
the SAME layer, so output stays consistent across the series.

Two registers, following the Daily Derja brand book:

  LEVANTINE (default, "Shami")  — the standard register for Levantine/Shami
      posts: gouache + ink on cream, Ablaq (alternating stone) border, jasmine
      and olive, olive/limestone/terracotta/pomegranate/teal palette.

  MAGHREBI ("Tunisian")         — for Tunisian/Maghrebi-dialect posts: harder
      Mediterranean light, Sidi Bou Said cobalt, whitewash, eight-pointed-star
      (khatam) zellige border, bougainvillea. NO pomegranate red, NO soft teal.

The register follows the DIALECT of the post, not the geography of the events.

Title sepia (70,45,30) and footer warm sepia-brown (130,80,50) are constant
across both registers (brand rule) — only the tile palette, the logo accent,
and the generation prompt change.
"""
from __future__ import annotations  # py3.9: allow "str | None" style hints
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

RGB = Tuple[int, int, int]

# --------------------------------------------------------------------- shared
# Title + footer colours are constant across the brand (matches nesma_nagma).
TITLE_COLOR: RGB  = (70, 45, 30)      # deep sepia
FOOTER_COLOR: RGB = (130, 80, 50)     # warm sepia-brown
FOOTER_TEXT = "dailyderja.com"

# Default output canvas. 16:9 at 2K is the Daily Derja blog-cover spec
# (true 16:9 — Nano Banana 2 territory; see brand/imagegen.py for the 3:2 caveat
# on GPT Image 2). Override per run with --size / --aspect.
DEFAULT_W, DEFAULT_H = 2752, 1536

# --------------------------------------------------------------------- layout
# Full-bleed model: the photo/art fills the whole canvas (the hero), and the
# brand layer is OVERLAID — a thin geometric tile border hugging the top and
# bottom edges (brand rule: border on top+bottom edges only), the Arabic title
# in the upper area, the dailyderja.com footer at the bottom, and the logo in a
# corner. A soft cream scrim/halo is laid behind the title, footer and logo
# only when the underlying pixels would hurt legibility, so sepia text always
# reads without resorting to a hard plate. All values are fractions of H or W.
@dataclass(frozen=True)
class Layout:
    tile_h_f: float      = 0.040      # tile-border strip height (top + bottom edges)
    art_keyline_f: float = 0.006      # thin cream rule between the tile strip and the art
    title_size_f: float  = 0.145      # TARGET title size (fraction of H, ~223px @1536); shrinks only on overflow
    title_cy_f: float    = 0.125      # title vertical centre (upper area, over the art)
    title_max_w_f: float = 0.74       # max title width before it auto-shrinks
    title_band_f: Tuple[float, float] = (0.055, 0.30)  # vertical window the title stays in / is scanned in
    footer_baseline_f: float = 0.952  # footer text baseline
    footer_size_f: float = 0.040      # footer cap height (≈ size 61 @1536 → reads as a brand mark)
    logo_h_f: float      = 0.110      # logo height
    logo_pos: str        = "tr"       # tl|tr|bl|br — default top-right (keeps the centred title clear)
    logo_margin_f: float = 0.030      # logo inset from the canvas corner
    logo_halo: bool      = True       # soft cream halo behind the logo (legible over any photo)
    scrim_lum_min: int   = 170        # title/footer band must be at least this bright for sepia to read

LAYOUT = Layout()

# --------------------------------------------------------------------- register
@dataclass(frozen=True)
class Register:
    key: str
    label: str
    paper: RGB                    # cream paper ground for the bands/margins
    tile_palette: List[RGB]       # colours used by the tile-border motif
    tile_style: str               # "ablaq" | "khatam"
    logo_color: RGB               # default recolour for the logo line-art
    keyline: RGB                  # thin separating line under each tile strip
    # ---- generation prompt fragments (prompt mode) ----
    medium: str
    atmosphere: str
    architecture: str
    botanical: str
    palette_words: str
    framing_note: str
    negative: str

    def prompt_palette(self) -> str:
        return self.palette_words


LEVANTINE = Register(
    key="levantine",
    label="Levantine (Shami)",
    paper=(244, 238, 224),
    tile_palette=[(224, 210, 180), (188, 96, 64), (107, 110, 68), (150, 44, 42), (74, 128, 124)],
    tile_style="ablaq",
    logo_color=(70, 45, 30),
    keyline=(150, 120, 86),
    medium=(
        "vintage mid-century Levant travel illustration, hand-painted gouache and ink "
        "on cream-toned paper; visible gouache brushstrokes, confident fine ink contour "
        "lines, soft stippling for depth, hand-drawn organic feel"
    ),
    atmosphere=(
        "warm, sophisticated, poetic, Mediterranean-Levantine heritage; soft hazy morning "
        "light, quiet and contemplative"
    ),
    architecture=(
        "Levantine Ablaq stonework (alternating light and dark stone), arched Liwan windows, "
        "geometric wood-inlay, mashrabiya screens, Damascus courtyard detail"
    ),
    botanical="jasmine vines (primary), olive branches, pomegranate, climbing greenery",
    palette_words=(
        "olive green, warm limestone beige, terracotta, pomegranate red, soft teal, dusty gold"
    ),
    framing_note=(
        "leave the extreme top and bottom edges and a calm upper area uncluttered for the "
        "brand border and title that are added afterward"
    ),
    negative=(
        "no 3D render, no photorealism, no glossy or shiny finish, no modern UI, no vector art, "
        "no flat minimalism, no blur, no bokeh, no distorted or fake Arabic text, no watermark, "
        "no lens flare, no cobalt-blue Sidi-Bou-Said palette"
    ),
)

MAGHREBI = Register(
    key="maghrebi",
    label="Maghrebi (Tunisian)",
    paper=(243, 236, 220),
    tile_palette=[(38, 78, 140), (248, 248, 244), (224, 170, 70), (190, 100, 66), (110, 116, 70)],
    tile_style="khatam",
    logo_color=(38, 78, 140),
    keyline=(38, 78, 140),
    medium=(
        "vintage mid-century Maghrebi travel illustration, hand-painted gouache and ink on "
        "cream-toned paper; fine architectural ink lines, soft stippling, hand-drawn "
        "Tunisian travel-poster sensibility"
    ),
    atmosphere=(
        "warm, sophisticated, sun-soaked Maghreb; harder more directional Mediterranean light "
        "(bright noon or raking dawn), Sidi Bou Said clarity"
    ),
    architecture=(
        "whitewashed limestone walls, cobalt-blue iron-studded arched wooden doors, wrought-iron "
        "grille windows in Tunisian floral patterns, mashrabiya lattice, eight-pointed-star "
        "(khatam) zellige tile"
    ),
    botanical="cascading bougainvillea (magenta and coral, primary), olive trees, jasmine, citrus, prickly pear",
    palette_words=(
        "Sidi Bou Said cobalt blue, whitewash, warm sand and limestone beige, terracotta, "
        "saffron and dusty gold, olive green, with bougainvillea magenta and coral as the only "
        "saturated accent"
    ),
    framing_note=(
        "leave the extreme top and bottom edges and a calm upper area uncluttered for the "
        "brand border and title that are added afterward"
    ),
    negative=(
        "no 3D render, no photorealism, no glossy or shiny finish, no modern UI, no vector art, "
        "no flat minimalism, no blur, no bokeh, no distorted or fake Arabic text, no watermark, "
        "no Greek or Santorini look, no pomegranate red, no soft teal"
    ),
)

REGISTERS: Dict[str, Register] = {LEVANTINE.key: LEVANTINE, MAGHREBI.key: MAGHREBI}


def get_register(key: str) -> Register:
    k = (key or "levantine").strip().lower()
    if k not in REGISTERS:
        raise SystemExit(f"unknown register '{key}' — choose from: {', '.join(REGISTERS)}")
    return REGISTERS[k]
