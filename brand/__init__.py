"""Daily Derja cover-pipeline brand package."""
from .registers import (
    Register, Layout, LAYOUT, REGISTERS, get_register,
    LEVANTINE, MAGHREBI, TITLE_COLOR, FOOTER_COLOR, FOOTER_TEXT,
    DEFAULT_W, DEFAULT_H,
)
from .frame import cover_fit, draw_title_at, ensure_font, DEFAULT_LOGO
from .templates import (compose_on_template, title_only_on_template,
                        list_templates, get_template, REGISTRY, TEMPLATES_DIR)
from .photo_fit import load_photo, fit_to_window, detect_face_box, focus_point
from .prompts import build_prompt
from .imagegen import generate_scene
from .cutout import prepare_mnemonic, cutout_figure, trim_border

__all__ = [
    "Register", "Layout", "LAYOUT", "REGISTERS", "get_register",
    "LEVANTINE", "MAGHREBI", "TITLE_COLOR", "FOOTER_COLOR", "FOOTER_TEXT",
    "DEFAULT_W", "DEFAULT_H",
    "cover_fit", "draw_title_at", "ensure_font", "DEFAULT_LOGO",
    "compose_on_template", "title_only_on_template", "list_templates", "get_template",
    "REGISTRY", "TEMPLATES_DIR",
    "load_photo", "fit_to_window", "detect_face_box", "focus_point",
    "build_prompt", "generate_scene",
    "prepare_mnemonic", "cutout_figure", "trim_border",
]
