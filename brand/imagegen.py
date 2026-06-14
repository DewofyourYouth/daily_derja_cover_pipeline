#!/usr/bin/env python3
"""
Image-generation backends for prompt mode.

Mirrors the nesma_nagma pipeline's dual-backend approach:

  - Gemini (Nano Banana family) is the DEFAULT. It does true 16:9 at 2K and is
    the right tool for Daily Derja blog covers. Set GEMINI_IMAGE_MODEL to your
    current 3.x image model for 2K / true 16:9.
  - OpenAI (GPT Image 2 / gpt-image-1) is OPTIONAL and useful for crisp lettering.
    CAVEAT: GPT Image 2 only emits preset sizes; its landscape preset is 1536x1024
    (3:2), NOT true 16:9. For a 16:9 cover the frame layer crops it; for square
    (1:1) covers it is fine. Prefer Gemini for 16:9.

Both backends are lazy-imported so the title-only and photo modes run on
pillow + numpy alone, with no API key and no SDK installed.

Keys (env): GEMINI_API_KEY and/or OPENAI_API_KEY.
"""
from __future__ import annotations
import base64, io, os, sys
from typing import List, Optional
from PIL import Image

GEMINI_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
OPENAI_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")  # set to gpt-image-2 when exposed


def log(*a):
    print(*a, file=sys.stderr)


def _png_buf(img: Image.Image, name: str):
    b = io.BytesIO()
    img.save(b, "PNG")
    b.seek(0)
    b.name = name
    return b


# ---------------------------------------------------------------- OpenAI
def _openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("openai not installed — run: pip install openai")
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set")
    return OpenAI()


def openai_generate(prompt: str, size: str = "1536x1024", quality: str = "high") -> Image.Image:
    """Text -> image (no reference photo)."""
    client = _openai_client()
    resp = client.images.generate(model=OPENAI_MODEL, prompt=prompt, size=size, quality=quality)
    return Image.open(io.BytesIO(base64.b64decode(resp.data[0].b64_json))).convert("RGB")


def openai_edit(prompt: str, images: List[Image.Image], size: str = "1536x1024",
                quality: str = "high") -> Image.Image:
    """Image(s) + prompt -> image. Use to place a reference photo of the figure."""
    client = _openai_client()
    files = [_png_buf(im, f"img{i}.png") for i, im in enumerate(images)]
    img_arg = files[0] if len(files) == 1 else files
    resp = client.images.edit(model=OPENAI_MODEL, image=img_arg, prompt=prompt,
                              size=size, quality=quality)
    return Image.open(io.BytesIO(base64.b64decode(resp.data[0].b64_json))).convert("RGB")


# ---------------------------------------------------------------- Gemini
def _gemini_client():
    try:
        from google import genai
    except ImportError:
        sys.exit("google-genai not installed — run: pip install google-genai")
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set")
    return genai.Client()


def gemini_image(prompt: str, images: Optional[List[Image.Image]] = None,
                 aspect_ratio: Optional[str] = None) -> Image.Image:
    """Text (+ optional reference images) -> image. Handles true 16:9 at 2K."""
    from google.genai import types
    client = _gemini_client()
    contents = [prompt] + list(images or [])      # google-genai accepts PIL.Image objects
    configs = []
    try:
        ic = types.ImageConfig(aspect_ratio=aspect_ratio) if aspect_ratio else None
        configs.append(types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=ic))
        if ic:
            configs.append(types.GenerateContentConfig(image_config=ic))
    except Exception:
        pass
    configs.append(None)
    last = None
    for cfg in configs:
        try:
            kw = {"model": GEMINI_MODEL, "contents": contents}
            if cfg is not None:
                kw["config"] = cfg
            resp = client.models.generate_content(**kw)
            cand = (resp.candidates or [None])[0]
            if cand and cand.content:
                for part in cand.content.parts:
                    inl = getattr(part, "inline_data", None)
                    if inl and inl.data:
                        data = inl.data
                        if isinstance(data, str):
                            data = base64.b64decode(data)
                        return Image.open(io.BytesIO(data)).convert("RGB")
            last = "no image part in response"
        except Exception as e:
            last = e
    raise RuntimeError(f"Gemini image generation failed: {last}")


# ---------------------------------------------------------------- dispatch
def _openai_size_for(aspect: str) -> str:
    return {"1:1": "1024x1024", "16:9": "1536x1024", "9:16": "1024x1536"}.get(aspect, "1536x1024")


def generate_scene(prompt: str, provider: str, aspect: str,
                   references: Optional[List[Image.Image]] = None) -> Image.Image:
    """
    Generate the inner scene for prompt mode.

    provider: "gemini" (default, true 16:9 / 2K) or "openai" (preset sizes; 16:9
              is approximated by the 3:2 landscape preset and cropped by the frame).
    references: optional reference photo(s) of the figure (Jacob). When present,
                the figure should read as him; you still pick which photo.
    """
    refs = references or []
    if provider == "openai":
        if refs:
            return openai_edit(prompt, refs, size=_openai_size_for(aspect))
        return openai_generate(prompt, size=_openai_size_for(aspect))
    return gemini_image(prompt, images=refs or None, aspect_ratio=aspect)
