# Daily Derja cover pipeline

Headless, template-driven cover generator for **dailyderja.com**. Pick a reusable
Daily Derja **frame** (ornate border + logo + `dailyderja.com` baked in once), drop
an image into its window, and overlay the post's Arabic title. The branding is never
regenerated — only the image and the title change.

Two ways to fill the window:

| Mode       | You give                     | What happens                                                                                                                                                  |
| ---------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **photo**  | a photo (`--photo`)          | smart-cropped (face-aware) into the window, then framed. No API key. Add `--gouache` to AI-repaint it into the Daily Derja gouache look (needs an image key). |
| **prompt** | a scene (`--prompt`)         | art is AI-generated in the chosen Daily Derja register, then framed. Optional reference photo of you.                                                         |
| **title**  | an existing cover (`--base`) | re-stamps just the Arabic title. No API key.                                                                                                                  |

## The template library

Six frames, two families — consistent branding (cream ground, ornate border on all
edges, the logo + `dailyderja.com` in the bottom cartouche). The **register follows
the dialect of the post, not the geography of its events.**

| Template                  | Family                  | Design                                                                     |
| ------------------------- | ----------------------- | -------------------------------------------------------------------------- |
| `levantine_gold_A`        | Levantine (Shami)       | restrained illuminated border, gold + pomegranate                          |
| `levantine_gold_B`        | Levantine (Shami)       | lush gilded pomegranate corners                                            |
| `levantine_ablaq_jasmine` | Levantine (Shami)       | Ablaq stone, jasmine, teal medallions                                      |
| `levantine_damascus_tile` | Levantine (Shami)       | geometric wood-inlay, mashrabiya, Liwan arch                               |
| `maghrebi_zellige`        | Tunisian (Maghrebi)     | Sidi Bou Saïd cobalt stars, whitewash, saffron                             |
| `maghrebi_bougainvillea`  | Tunisian (Maghrebi)     | cascading bougainvillea, cobalt zellige                                    |
| `levantine_word_square`   | Levantine — Word series | 1:1 image well + word & `نسمة كلمة` cartouches (gold)                      |
| `maghrebi_word_sbs`       | Tunisian — Word series  | Sidi Bou Saïd: top-oval `نسمة كلمة`, square well, word box, logo medallion |

`python cover.py templates` lists them.

## Install

```bash
python -m venv .venv && source .venv/bin/activate     # optional
pip install -r requirements.txt
python -c "from PIL import features; print('raqm:', features.check_feature('raqm'))"   # must print True
```

Python 3.9+. Photo mode and title mode need only `pillow` + `numpy`. Prompt mode also
needs a backend SDK + key (see `.env.example`). `opencv-python-headless` is optional —
it enables face-aware centring in photo mode (otherwise an upper-centre fallback is used).

## Usage

```bash
# list frames
python cover.py templates

# PHOTO — drop a photo in (no API key). Face-aware crop to the window.
python cover.py photo --photo photos/photo_10.jpg --title "نَسمة بحر" \
    --template levantine_gold_A --out sea.png

# PHOTO + --gouache — AI-repaint the photo into the Daily Derja gouache look
# (Gemini repaints the cropped photo in the template's register; needs an image key).
python cover.py photo --photo photos/photo_10.jpg --title "نَسمة بحر" --gouache \
    --template levantine_gold_A --out sea.png

# PROMPT — generate art in the register, then frame it (Gemini / Nano Banana, true 16:9)
python cover.py prompt --prompt "a glass of mint tea cooling on a windowsill, jasmine outside" \
    --title "شويّة هدوء" --template levantine_gold_B --out calm.png

# PROMPT with you in the scene. This defaults to three OpenRouter options using
# Nano Banana Pro, GPT Image 2, and FLUX.2 Pro, with the reference treated as identity-authoritative.
python cover.py prompt --prompt "a man at a desk before dawn, one lamp lit" \
    --figure-photo photos/photo_05.jpg --title "قبل الفجر" --template levantine_damascus_tile --out predawn.png

# Choose the count or models explicitly (one output per model/candidate).
python cover.py prompt --prompt "a man reading beside an open window" \
    --figure-photo photos/photo_05.jpg --title "قراية" --variants 2 \
    --models google/gemini-3-pro-image,openai/gpt-image-2 --out reading.png

# PROMPT offline — frame a pre-generated image instead of calling the API
python cover.py prompt --art examples/base_levantine_minttea.jpg --title "شويّة هدوء" \
    --template maghrebi_zellige --out calm.png

# WORD SERIES (نسمة كلمة) — word + a mnemonic graphic on a dedicated word frame
python cover.py word --word "كفاية" --prompt "a woman draped in too many keffiyehs, exasperated" \
    --template levantine_word_square --out kafiya.png
python cover.py word --word "كفاية" --art mnemonic.png --template maghrebi_word_sbs --out kafiya_sbs.png

# TITLE — restamp just the title on an existing cover
python cover.py title --base covers/calm.png --title "هدوء" --template maghrebi_zellige --out calm2.png
```

### Word series (نسمة كلمة)

The Word series teaches one Arabic word with a **mnemonic graphic**. Two dedicated 16:9
frames carry the series — `نسمة كلمة` and `dailyderja.com` are baked into each frame, and
each has a square **image well** plus a **word** cartouche:

- `levantine_word_square` — gold + pomegranate; word cartouche left, square well right.
- `maghrebi_word_sbs` — Sidi Bou Saïd cobalt/whitewash; square well left, word box right,
  logo medallion lower-right (matches the Word-Breeze layout).

```bash
python cover.py word --word "كفاية" --prompt "a woman in too many keffiyehs, exasperated"   # generate the mnemonic
python cover.py word --word "كفاية" --art mnemonic.png      # supply the mnemonic graphic
python cover.py word --word "كفاية" --photo photos/photo_05.jpg
```

The mnemonic graphic is **background-cut automatically** (`brand/cutout.py`): the border ring
and the flat background are keyed out (edge-connected only, so a keffiyeh's white survives;
any teal is removed globally) and the figure is composited onto the frame's cream well — no
illustration block, no border. Pass `--no-cutout` to drop a full-bleed scene into the well
instead. `--word` also works on any general template (renders a `نسمة كلمة` kicker + word
overlaid in the title area).

Output is written to `covers/`. `--register levantine|maghrebi` overrides the generation
register in prompt mode (defaults to the template's register). `--title-color "r,g,b"`
overrides the title colour (default: pomegranate on Levantine, cobalt on Maghrebi).
Every cover-generation run also prints its total API cost. OpenRouter totals use the exact billed
`usage.cost` returned by the API; offline runs report `$0.00 USD`. Direct Gemini and
OpenAI runs say that the cost is unavailable because those image responses do not expose
an exact per-request USD charge.

## The photos folder

`photos/` holds reference photos of Jacob for when you want to be in the cover. In
**photo mode** the photo is the window content; in **prompt mode** pass one with
`--figure-photo` and it guides the generated figure. Reference-image jobs default to
OpenRouter and produce three separately named options (use `--variants 1` for one).
The default quality slate is configurable with `OPENROUTER_REFERENCE_MODELS`; `--models`
overrides it for one run. Both `OPENROUTER_API_KEY` and `OPEN_ROUTER_API_KEY` are accepted
from the project `.env`. Options run concurrently and print start/finish timing for each
model; `OPENROUTER_TIMEOUT_SECONDS` and `OPENROUTER_MAX_WORKERS` tune waiting/concurrency.
You pick which photo for now —
`photos/manifest.json` tags each one (frontal / sunglasses / study / outdoor …) to make
that easy and to support automatic selection later.

## Adding a template

1. Generate (or paint) an ornate Daily Derja border on a 2752×1536 cream canvas with a
   **blank rectangular centre window** (a crisp keyline helps) and a **small blank
   cartouche centred at the bottom** for the URL. No text, no figures.
2. Drop it in `templates/<name>_blank.jpg`.
3. Bake the logo + URL in:  `python tools/bake_template_footer.py <name> --register levantine`
   (auto-detects the cartouche and chooses a horizontal or stacked logo/URL lockup).
4. Add a registry entry to `templates/templates.json` — the content `window`
   `[left,top,right,bottom]` and a `title` spec. `tools/measure_window.py <name>`
   prints a detected window box to start from.

As long as a new frame keeps the Daily Derja DNA (cream ground, ornate border, the
baked logo + URL), the library stays consistent.

## Standing brand rules (baked into the pipeline)

- Minimal text: Arabic title + `dailyderja.com` only. **No English subtitle, no genre
  kicker, no multi-line plate.**
- RTL Arabic in PIL: raw Unicode with `layout_engine=RAQM`, `direction='rtl'`,
  `language='ar'`. **Never** pre-process with python-bidi / arabic-reshaper.
- Title font follows the template's `title.font` so the type matches the frame: Amiri
  (Naskh) on Levantine, Reem Kufi (geometric) on Maghrebi, Lalezar (display) on word
  frames; tashkeel preserved. Footer stays Amiri (a constant brand mark).
- Prompt-mode art never renders text or its own border (the template owns those); when a
  figure is requested it's Jacob, always with a **black kippah**, slim build, engaged in
  the scene — never posed.

## Files

```
cover.py                    # CLI: photo | prompt | title | word | templates
daily_derja_cover.py        # no-API helper: overlay-title, recolor-logo
brand/
  registers.py              # Levantine + Maghrebi palettes, layout, prompt fragments
  templates.py              # template registry + compose_on_template (RGBA-aware)
  frame.py                  # logo, tile motifs, per-template raqm title + footer + kicker (FONTS registry)
  photo_fit.py              # face-aware crop to the window
  prompts.py                # register-aware Daily Derja prompt builder
  imagegen.py               # OpenRouter multi-model + direct Gemini/OpenAI backends
  cutout.py                 # mnemonic figure cutout: trim border + background→transparent
templates/                  # the frames: <name>.jpg (baked) + <name>_blank.jpg + templates.json
assets/logo/                # the Daily Derja logo (transparent line-art)
fonts/                      # title typefaces (Amiri / ReemKufi / Lalezar) — auto-download on first use
photos/                     # your reference photos + manifest.json
examples/                   # sample generated scenes (for --art demos)
tools/                      # bake_template_footer.py, measure_window.py
covers/                     # output (gitignored)
```
