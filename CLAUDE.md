# CLAUDE.md — working notes for this repo

Headless Daily Derja cover generator. Sibling to `nesma_nagma_pipeline` (the
نسمة نغمة music-diary covers) and shares its conventions: a thin CLI over a small
package, Amiri + raqm for Arabic, Gemini-default / OpenAI-optional image backends.

## Core idea: templates are baked assets, not regenerated

A **template** is a finished branded frame (`templates/<name>.png`) — ornate border +
Daily Derja logo + `dailyderja.com`, all baked in **once**. Generating a cover only:

1. drops content (a photo or generated art) into the template's content **window**, and
2. overlays the per-post **Arabic title**.

The border / logo / URL are never re-drawn. This was a deliberate decision (don't
"reinvent the wheel" each render). `templates/templates.json` is the registry: each
entry has the `window` box `[l,t,r,b]` and a `title` spec; `compose_on_template` in
`brand/templates.py` does the drop + title.

## Two visual families, register == dialect

- **levantine** (Shami): cream + gold/pomegranate/olive/teal, Ablaq, jasmine, Damascus
  tile. Title in pomegranate.
- **maghrebi** (Tunisian): Sidi Bou Saïd cobalt + whitewash + saffron, khatam zellige,
  bougainvillea. Title in cobalt. NO pomegranate, NO soft teal.

The register follows the **dialect** of the post, not where the events happened.
`brand/registers.py` holds palettes, layout constants, and the per-register prompt
fragments used by `brand/prompts.py`.

## Title overlay (the one piece of per-cover text)

`brand/frame.draw_title_at` — RAQM `layout_engine`, `direction='rtl'`, `language='ar'`,
raw Unicode (NEVER python-bidi / arabic-reshaper — that double-shapes and mangles vowels).
Width is measured on the consonant skeleton (tashkeel stripped) so vowel-marked titles
aren't penalised. A feathered cream scrim is laid behind the title only when the pixels
under it would hurt legibility (`_legible`), never a hard plate.

**Typography matches the template.** The title typeface comes from the template's
`title.font` (a name in `brand/frame.FONTS`), so the type automatically suits the frame:
`Amiri` (classical Naskh) for the Levantine illuminated frames, `ReemKufi` (geometric Kufi,
echoes the khatam zellige) for Maghrebi, `Lalezar` (bold display) for the word frames.
Fonts are fetched from Google Fonts (OFL) on first use, like Amiri always was; omit
`title.font` and it falls back to Amiri. Title colour comes from `title.color` (sepia
fallback). The footer stays Amiri always — it's a constant brand mark, not per-template type.

## Word series (نسمة كلمة) + cutout

The Word series ("Word Breeze") teaches one word with a **mnemonic graphic**. Its two
16:9 frames — `levantine_word_square` (gold) and `maghrebi_word_sbs` (Sidi Bou Saïd) — bake
`نسمة كلمة` + `dailyderja.com` (and, on the SBS frame, the logo medallion) into the frame,
and declare BOTH a square `window` (the image well) and a `word_panel` (where the per-post
word renders). When a template has `word_panel`, `compose_on_template` renders the word there
and does NOT draw a kicker (the series name is baked).

`cover.py word` supplies the mnemonic via `--prompt` (generated), `--art`, or `--photo`, then
`brand/cutout.prepare_mnemonic` **trims any border ring and keys the background transparent**
(flood-fill from the edges so interior whites survive; teal removed globally) so the figure
composites onto the cream well with no block/border. RGBA content is contain-fit + bottom-
aligned by `compose_on_template`; opaque content cover-fits. `--no-cutout` keeps a full scene.
(`--word` on a *general* template instead overlays a `نسمة كلمة` kicker + word in the title band.)

## Adding / re-baking templates

- New frame: paint/generate an ornate border on 2752×1536 cream with a blank centre
  window + a blank bottom cartouche → `templates/<name>_blank.png`.
- `tools/measure_window.py <name>` → detected window box (flat-cream cross-expansion).
- `tools/bake_template_footer.py <name> --register <fam>` → composites logo + URL into
  the auto-detected cartouche. It auto-chooses a **horizontal** lockup (logo beside URL)
  for wide cartouches and a **stacked** one (logo above URL) for narrow/tall ones. Keep
  `<name>_blank.png` so the footer can be re-baked (e.g. recoloured).
- Register the entry in `templates.json` (window + title).

## Gouache filter (photo mode)

`cover.py photo --gouache` AI-repaints a supplied photo into the Daily Derja gouache look
instead of placing it straight. The photo is face-cropped to the window first, then
`brand/imagegen.repaint_photo_options` passes that crop to the image backend (OpenRouter
multi-model by default) with
`brand/prompts.build_repaint_prompt` — which reuses the register's `medium`/`atmosphere`/
`palette` but **omits** the architecture/botanical fragments, so the model restyles the
existing picture (composition + faces preserved) rather than inventing a new scene. The
result is resized back to the exact window. Reference jobs default to three options from
Nano Banana Pro, GPT Image 2, and FLUX.2 Pro; `--variants` and `--models` control the slate.
Needs an image key; `--register`/`--provider`/`--extra` mirror prompt mode,
`--save-intermediates` dumps the raw repaint.

## Image backends (prompt mode only)

`brand/imagegen.generate_scene_options` → **OpenRouter for reference photos**, with
identity-authoritative prompting and three quality-model candidates. Plain prompt jobs still
use Gemini / Nano Banana by default (true 16:9 at 2K; set `GEMINI_IMAGE_MODEL` to the current
3.x model). Direct OpenAI / GPT Image 2 is optional
(`--provider openai`) and emits 3:2, not true 16:9 — fine for square work, cropped for
16:9. Photo / title / `--art` paths need no key. The generated art deliberately contains
**no text and no border** (the template owns those) and leaves the upper area calm for
the title.

## Gotchas

- raqm must be present: `python -c "from PIL import features; print(features.check_feature('raqm'))"`.
- Python 3.9: modules use `from __future__ import annotations` for `str | None` hints.
- Node's `fetch`/`http` ignore the proxy in some sandboxes — irrelevant here (pure Python),
  but the font auto-download uses `urllib`, which honours `HTTPS_PROXY`.
- Output covers are large PNGs in `covers/` (gitignored).
