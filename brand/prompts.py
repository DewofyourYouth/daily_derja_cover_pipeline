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

NO_TEXT_RULE = (
    "Render NO text, NO letters, NO Arabic or Latin writing anywhere in the image, and NO "
    "decorative border or frame — leave the four outer edges as clean scene and keep the upper "
    "fifth calm and uncluttered. The title, footer, logo and tile border are added afterward."
)


def build_prompt(register: Register, scene: str, with_figure: bool = False,
                 figure_note: str = "", extra: str = "") -> str:
    """
    Compose the full Daily Derja brand prompt.

    scene       : the concrete, post-specific scene — ideally one or two objects
                  (e.g. "a packed suitcase by a door, dust on the lid").
    with_figure : include Jacob in the scene (default False — objects only).
    figure_note : optional extra figure direction (pose, what he's doing).
    extra       : optional freeform additions appended near the end.
    """
    scene = (scene or "").strip().rstrip(".")
    parts = [
        f"{register.medium}.",
        f"Subject: {scene}." if scene else "",
        # brand scene-construction discipline
        "Build the composition around one or two concrete objects from the scene; keep it quiet, "
        "concrete and intimate rather than literal or busy; never depict violence or graphic "
        "hardship directly — show its quiet aftermath instead.",
        f"Setting and decor: {register.architecture}.",
        f"Living accents: {register.botanical}.",
        f"Atmosphere: {register.atmosphere}.",
        f"Colour palette: {register.prompt_palette()}.",
    ]
    if with_figure:
        parts.append(FIGURE_RULE + (f" {figure_note.strip()}" if figure_note.strip() else "") + ".")
    else:
        parts.append("No human figures in the scene.")
    parts.append(register.framing_note + ".")
    parts.append(NO_TEXT_RULE)
    if extra.strip():
        parts.append(extra.strip().rstrip(".") + ".")
    neg = register.negative
    if with_figure:
        neg = neg + ", " + FIGURE_NEG
    parts.append("Avoid: " + neg + ".")
    return " ".join(p for p in parts if p)
