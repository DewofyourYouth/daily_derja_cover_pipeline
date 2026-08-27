#!/usr/bin/env python3
"""
Image-generation backends for prompt mode.

Mirrors the nesma_nagma pipeline's dual-backend approach:

  - Gemini (Nano Banana family) is the DEFAULT. It does true 16:9 at 2K and is
    the right tool for Daily Derja blog covers. Set GEMINI_IMAGE_MODEL to your
    current 3.x image model for 2K / true 16:9.
  - OpenRouter is the default for reference-image work. It can compare several
    high-fidelity editing models and return multiple candidates.
  - OpenAI (GPT Image 2 / gpt-image-1) is OPTIONAL and useful for crisp lettering.
    CAVEAT: GPT Image 2 only emits preset sizes; its landscape preset is 1536x1024
    (3:2), NOT true 16:9. For a 16:9 cover the frame layer crops it; for square
    (1:1) covers it is fine. Prefer Gemini for 16:9.

The direct SDK backends are lazy-imported, and OpenRouter uses the standard library, so
title-only and ordinary photo modes run on
pillow + numpy alone, with no API key and no SDK installed.

Keys (env): OPENROUTER_API_KEY (OPEN_ROUTER_API_KEY is also accepted),
GEMINI_API_KEY and/or OPENAI_API_KEY. A project-root .env is loaded automatically.
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image


def _load_project_env() -> None:
    """Load simple KEY=VALUE entries without overriding the shell environment."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if value and value[:1] == value[-1:] and value[0] in "\"'":
                    value = value[1:-1]
                if key and value:
                    os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


_load_project_env()

GEMINI_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
OPENAI_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")  # set to gpt-image-2 when exposed
OPENROUTER_IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image"
)
OPENROUTER_REFERENCE_MODELS = tuple(
    m.strip() for m in os.environ.get(
        "OPENROUTER_REFERENCE_MODELS",
        "google/gemini-3-pro-image,openai/gpt-image-2,black-forest-labs/flux.2-pro",
    ).split(",") if m.strip()
)
# Strongest known face/identity fidelity for edits of a reference photo (Nano Banana
# Pro) — used instead of the quality-comparison slate when identity match matters more
# than seeing several stylistic options.
OPENROUTER_IDENTITY_MODEL = os.environ.get(
    "OPENROUTER_IDENTITY_MODEL", "google/gemini-3-pro-image"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/images"
OPENROUTER_TIMEOUT = int(os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "180"))
OPENROUTER_MAX_WORKERS = int(os.environ.get("OPENROUTER_MAX_WORKERS", "3"))
API_COST_INFO_KEY = "daily_derja_api_cost_usd"


def log(*a):
    print(*a, file=sys.stderr)


def api_cost_usd(image: Image.Image) -> Optional[float]:
    """Return exact per-request USD cost when the backend supplied one."""
    value = image.info.get(API_COST_INFO_KEY)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _png_buf(img: Image.Image, name: str):
    b = io.BytesIO()
    img.save(b, "PNG")
    b.seek(0)
    b.name = name
    return b


def _data_url(img: Image.Image) -> str:
    buf = _png_buf(img.convert("RGB"), "reference.png")
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


# -------------------------------------------------------------- OpenRouter
def _openrouter_key() -> str:
    # Accept the spelling already used by this project as well as OpenRouter's standard.
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPEN_ROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY (or OPEN_ROUTER_API_KEY) not set")
    return key


def choose_openrouter_models(count: int, has_references: bool,
                             requested: Optional[Sequence[str]] = None,
                             identity: bool = False) -> List[str]:
    """
    Choose a model slate; cycle it if more candidates are requested.

    identity=True skips the quality-comparison slate (and any explicit `requested`
    list) and pins every candidate to OPENROUTER_IDENTITY_MODEL — use it when
    faithfulness to a specific reference face matters more than seeing a spread
    of stylistic options.
    """
    if count < 1:
        raise ValueError("variants must be at least 1")
    if identity:
        return [OPENROUTER_IDENTITY_MODEL] * count
    slate = [m.strip() for m in (requested or []) if m.strip()]
    if not slate:
        slate = list(OPENROUTER_REFERENCE_MODELS if has_references
                     else (OPENROUTER_IMAGE_MODEL,))
    if not slate:
        raise RuntimeError("No OpenRouter image models configured")
    return [slate[i % len(slate)] for i in range(count)]


def openrouter_image(prompt: str, images: Optional[List[Image.Image]] = None,
                     aspect_ratio: str = "16:9", model: Optional[str] = None,
                     quality: str = "high") -> Image.Image:
    """Generate/edit one image through OpenRouter's dedicated Images API."""
    payload = {
        "model": model or OPENROUTER_IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "aspect_ratio": aspect_ratio,
        "quality": quality,
        "output_format": "png",
    }
    # OpenAI's image endpoint sizes from aspect + quality; the other selected
    # providers expose a resolution tier and can render the reference at 2K.
    if not payload["model"].startswith("openai/"):
        payload["resolution"] = "2K"
    if images:
        payload["input_references"] = [
            {"type": "image_url", "image_url": {"url": _data_url(im)}}
            for im in images
        ]
    selected_model = payload["model"]
    started = time.monotonic()
    log(f"[openrouter] starting {selected_model} ...")
    req = Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_openrouter_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://dailyderja.com",
            "X-Title": "Daily Derja cover pipeline",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=OPENROUTER_TIMEOUT) as resp:
            body = json.load(resp)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError(f"OpenRouter image request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenRouter image request failed: {exc.reason}") from exc
    data = body.get("data") or []
    if not data or not data[0].get("b64_json"):
        raise RuntimeError(f"OpenRouter returned no image: {body}")
    image = Image.open(io.BytesIO(base64.b64decode(data[0]["b64_json"]))).convert("RGB")
    # The dedicated OpenRouter Images API reports the exact billed amount in USD.
    # Keep it on the PIL object so existing image-returning APIs stay compatible.
    usage = body.get("usage") or {}
    cost = usage.get("cost")
    if cost is not None:
        try:
            image.info[API_COST_INFO_KEY] = float(cost)
        except (TypeError, ValueError):
            log(f"[openrouter] warning: invalid usage.cost value {cost!r}")
    log(f"[openrouter] finished {selected_model} in {time.monotonic() - started:.1f}s")
    return image


def _run_openrouter_options(models: Sequence[str], generate) -> List[Tuple[Image.Image, str]]:
    """Run independent model candidates concurrently while preserving slate order."""
    results = {}
    errors = []
    workers = max(1, min(len(models), OPENROUTER_MAX_WORKERS))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(generate, model): (i, model)
                   for i, model in enumerate(models)}
        for future in as_completed(pending):
            index, model = pending[future]
            try:
                results[index] = (future.result(), model)
            except Exception as exc:
                errors.append(f"{model}: {exc}")
                log(f"[openrouter] failed {model}: {exc}")
    if not results:
        raise RuntimeError("All OpenRouter image models failed: " + " | ".join(errors))
    return [results[i] for i in sorted(results)]


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


def repaint_photo(prompt: str, photI o: Image.Image, provider: str, aspect: str,
                  identity: bool = False) -> Image.Image:
    """
    Gouache filter: restyle a supplied PHOTO into the Daily Derja hand-painted look by
    passing it to the image backend as the reference and asking for a stylistic repaint
    (composition and faces preserved — see brand.prompts.build_repaint_prompt).

    Gemini (default) edits the photo directly at the requested aspect. OpenAI uses its
    edit endpoint at the nearest preset size (cropped by the frame layer for 16:9).
    identity=True (openrouter only) pins the model to OPENROUTER_IDENTITY_MODEL.
    """
    photo = photo.convert("RGB")
    if provider == "openrouter":
        model = choose_openrouter_models(1, has_references=True, identity=identity)[0]
        return openrouter_image(prompt, [photo], aspect_ratio=aspect, model=model)
    if provider == "openai":
        return openai_edit(prompt, [photo], size=_openai_size_for(aspect))
    return gemini_image(prompt, images=[photo], aspect_ratio=aspect)


def repaint_photo_options(prompt: str, photo: Image.Image, provider: str, aspect: str,
                          variants: int = 1, models: Optional[Sequence[str]] = None,
                          identity: bool = False) -> List[Tuple[Image.Image, str]]:
    """Return repaint candidates paired with the model/backend that made each one."""
    photo = photo.convert("RGB")
    if provider == "openrouter":
        chosen = choose_openrouter_models(variants, has_references=True, requested=models,
                                          identity=identity)
        return _run_openrouter_options(
            chosen, lambda model: openrouter_image(prompt, [photo.copy()], aspect, model)
        )
    return [(repaint_photo(prompt, photo, provider, aspect, identity=identity), provider)
            for _ in range(variants)]


def generate_scene(prompt: str, provider: str, aspect: str,
                   references: Optional[List[Image.Image]] = None,
                   model: Optional[str] = None, identity: bool = False) -> Image.Image:
    """
    Generate the inner scene for prompt mode.

    provider: "gemini" (default, true 16:9 / 2K) or "openai" (preset sizes; 16:9
              is approximated by the 3:2 landscape preset and cropped by the frame).
    references: optional reference photo(s) of the figure (Jacob). When present,
                the figure should read as him; you still pick which photo.
    identity: (openrouter only, ignored if `model` is given explicitly) pin the
              model to OPENROUTER_IDENTITY_MODEL instead of the default slate.
    """
    refs = references or []
    if provider == "openrouter":
        chosen = model or choose_openrouter_models(1, has_references=bool(refs), identity=identity)[0]
        return openrouter_image(prompt, refs or None, aspect_ratio=aspect, model=chosen)
    if provider == "openai":
        if refs:
            return openai_edit(prompt, refs, size=_openai_size_for(aspect))
        return openai_generate(prompt, size=_openai_size_for(aspect))
    return gemini_image(prompt, images=refs or None, aspect_ratio=aspect)


def generate_scene_options(prompt: str, provider: str, aspect: str,
                           references: Optional[List[Image.Image]] = None,
                           variants: int = 1, models: Optional[Sequence[str]] = None,
                           identity: bool = False) -> List[Tuple[Image.Image, str]]:
    """Return scene candidates paired with the model/backend that made each one."""
    refs = references or []
    if provider == "openrouter":
        chosen = choose_openrouter_models(variants, has_references=bool(refs), requested=models,
                                          identity=identity)
        return _run_openrouter_options(
            chosen,
            lambda model: generate_scene(
                prompt, provider, aspect, [ref.copy() for ref in refs], model
            ),
        )
    return [(generate_scene(prompt, provider, aspect, refs, identity=identity), provider)
            for _ in range(variants)]
