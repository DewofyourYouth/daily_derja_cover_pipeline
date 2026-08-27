#!/usr/bin/env python3
"""
Register-aware Daily Derja generation prompt builder (prompt mode).

Encodes the Daily Derja brand book into the Stage-1 prompt so generated art is
on-brand and ready for the template layer:

  * medium / atmosphere / architecture / botanical / palette per register
  * scene-construction rule: anchor the image on ONE or TWO concrete objects
    drawn from the post; quiet and concrete, never literal about heavy themes
    (e.g. show the cost of war, never the violence)
  * NO human figure by default (the brand default is objects, no people). A
    figure is added only when you opt in — and then it is Jacob, with the
    standing likeness rules (BLACK kippah always; slim build to his current,
    thinner appearance; conversational, contemplative, never posed-for-camera)
  * NO text / lettering and NO decorative border in the generated art — the
    Arabic title, footer, logo and tile border are composited afterward by the
    template layer, so the model must leave the edges and an upper area clean

Each `build_*` function assembles the prompt from named context blocks (one
per brand rule) and joins them one-per-line — easier to read/trace in code
than a run-on paragraph, and it also gives the image model a clearer,
section-by-section instruction list rather than one dense sentence.
"""
from __future__ import annotations
from typing import Optional
from .registers import Register

# Standing figure rule for Jacob (only used when a figure is requested).
FIGURE_RULE = (
    "If a person appears, it is the same man throughout: a Modern Orthodox Jewish man, "
    "late 30s to early 40s, trimmed dark beard with a little grey, light Mediterranean skin, "
    "ALWAYS wearing a BLACK kippah (never coloured — not burgundy, navy, tan or brown), "
    "a slim build, engaged in what he is doing (reading, writing, listening, walking) and "
    "never posed for the camera"
)
FIGURE_NEG = "no coloured kippah, no burgundy/navy/tan/brown kippah, no velvet kippah, no heavy or overweight build"

# Identity-match rule for a supplied reference photo. Applies whenever a reference photo
# is passed, regardless of which model renders it — see brand.imagegen's `identity` option
# for choosing the strongest-identity-fidelity model to go with this instruction.
REFERENCE_LIKENESS_RULE = (
    "The supplied reference photograph is the authoritative identity reference. Preserve the "
    "same facial geometry, eye shape and spacing, nose, smile, beard pattern, hairline, skin "
    "tone and apparent age. Keep him recognizably the same individual even in the painted "
    "style; do not beautify, genericize, caricature or substitute a lookalike"
)

NO_TEXT_RULE = (
    "Render NO text, NO letters, NO Arabic or Latin writing anywhere in the image, and NO "
    "decorative border or frame — leave the four outer edges as clean scene and keep the upper "
    "fifth calm and uncluttered. The title, footer, logo and tile border are added afterward."
)

# Photo-repaint rule (gouache filter): restyle a supplied photo, never reinvent it.
REPAINT_RULE = (
    "Repaint the SUPPLIED photograph in exactly the medium described above. Keep the original "
    "composition, framing, poses and the likeness of any people — faithfully preserve every "
    "face, expression and identifying feature; this is a stylistic repaint of the same picture, "
    "NOT a new scene and NOT a different person. Replace photographic texture and lighting with "
    "hand-painted gouache: visible brushstrokes, confident fine ink contour lines and soft "
    "stippling, on cream-toned paper, in the palette below. Do not add, remove or rearrange "
    "any subject or object."
)


def _figure_block(with_figure: bool, figure_note: str, reference_photo: bool) -> str:
    """
    Figure instruction. Brand default is NO people (objects only) — opting in via
    with_figure pulls in the standing likeness rules for Jacob, and reference_photo
    additionally pins the render to the supplied photo's actual face.
    """
    if not with_figure:
        return "No human figures in the scene."
    note = f" {figure_note.strip()}" if figure_note.strip() else ""
    block = FIGURE_RULE + note + "."
    if reference_photo:
        block += " " + REFERENCE_LIKENESS_RULE + "."
    return block


def _negative_block(register: Register, with_figure: bool) -> str:
    negatives = register.negative
    if with_figure:
        negatives += ", " + FIGURE_NEG
    return "Avoid: " + negatives + "."


def build_repaint_prompt(register: Register, extra: str = "") -> str:
    """
    Prompt for the gouache photo filter: restyle a supplied photo into the register's
    hand-painted gouache medium while preserving its composition and the likeness of any
    people. Unlike `build_prompt` this deliberately omits architecture/botanical fragments
    so the model restyles what is already in the photo rather than inventing new elements.
    """
    medium = f"{register.medium}."
    repaint_rule = REPAINT_RULE
    atmosphere = f"Atmosphere and light: {register.atmosphere}."
    palette = f"Colour palette: {register.prompt_palette()}."
    no_text = NO_TEXT_RULE
    extra_block = extra.strip().rstrip(".") + "." if extra.strip() else ""
    negative = ("Avoid: " + register.negative + ", no photographic look, no photorealism, "
                "no glossy sheen, no changed faces or identities.")

    sections = [medium, repaint_rule, atmosphere, palette, no_text, extra_block, negative]
    return "\n".join(s for s in sections if s)


def build_prompt(register: Register, scene: str, with_figure: bool = False,
                 figure_note: str = "", extra: str = "",
                 reference_photo: bool = False) -> str:
    """
    Compose the full Daily Derja brand prompt.

    scene       : the concrete, post-specific scene — ideally one or two objects
                  (e.g. "a packed suitcase by a door, dust on the lid").
    with_figure : include Jacob in the scene (default False — objects only).
    figure_note : optional extra figure direction (pose, what he's doing).
    extra       : optional freeform additions appended near the end.
    reference_photo : a reference photo of Jacob was supplied — adds the identity
                       likeness rule (only meaningful together with with_figure).
    """
    scene = (scene or "").strip().rstrip(".")

    medium = f"{register.medium}."
    subject = f"Subject: {scene}." if scene else ""
    composition_rule = (
        "Build the composition around one or two concrete objects from the scene; keep it "
        "quiet, concrete and intimate rather than literal or busy; never depict violence or "
        "graphic hardship directly — show its quiet aftermath instead."
    )
    setting = f"Setting and decor: {register.architecture}."
    accents = f"Living accents: {register.botanical}."
    atmosphere = f"Atmosphere: {register.atmosphere}."
    palette = f"Colour palette: {register.prompt_palette()}."
    figure = _figure_block(with_figure, figure_note, reference_photo)
    framing = register.framing_note + "."
    no_text = NO_TEXT_RULE
    extra_block = extra.strip().rstrip(".") + "." if extra.strip() else ""
    negative = _negative_block(register, with_figure)

    sections = [medium, subject, composition_rule, setting, accents, atmosphere, palette,
                figure, framing, no_text, extra_block, negative]
    return "\n".join(s for s in sections if s)
