from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

BASE_THEME: Dict[str, Any] = {
    "colors": {
        "navy": "#223a69",
        "navy_2": "#314b7b",
        "paper": "#f5f7fb",
        "panel": "#eef2f8",
        "line": "#cfd7e6",
        "text": "#0e1b3d",
        "muted": "#6c7894",
        "white": "#ffffff",
        "page_bg": "#e9edf4",
        "border": "#d7deeb",
        "header_gradient_end": "#263f70",
        "hotel_address": "#233356",
        "table_head": "#f8faff",
        "table_row": "#e3e8f1",
        "placeholder": "#cad2e2",
        "overlay": "rgba(255,255,255,0.10)",
        "overlay_border": "rgba(255,255,255,0.18)",
        "shadow": "rgba(21, 36, 70, 0.10)",
        "section_title": "#6c7894",
        "footer_bg": "#eef2f8",
    },
    "fonts": {
        "family": "Inter, Arial, Helvetica, sans-serif",
    },
    "radius": {
        "page": "28px",
        "xl": "22px",
        "lg": "20px",
        "md": "18px",
        "sm": "16px",
        "xs": "14px",
    },
    "layout": {
        "page_width_px": 794,
        "page_min_height_px": 1123,
        "body_padding": "18px",
        "header_padding": "22px 24px",
        "header_gap": "16px",
        "header_meta_width": 246,
        "logo_box_width": 170,
        "logo_box_min_height": 98,
        "brand_logo_height": 64,
        "brand_logo_height_print": 54,
        "header_title_size": "31px",
        "header_title_size_print": "28px",
        "header_subtitle_size": "13px",
        "header_subtitle_size_print": "12px",
        "top_grid_left": "1.45fr",
        "top_grid_right": "1fr",
        "panel_gap": "14px",
        "print_page_margin": "8mm",
        "print_header_padding": "18px 20px",
        "print_header_gap": "12px",
        "print_header_meta_width": 234,
        "print_logo_box_width": 156,
        "print_logo_box_min_height": 90,
        "meta_box_min_height": 98,
        "meta_box_min_height_print": 90,
    },
}

THEME_REGISTRY: Dict[str, Dict[str, Any]] = {
    "default": deepcopy(BASE_THEME),
    "mastercard": {
        **deepcopy(BASE_THEME),
        "colors": {
            **deepcopy(BASE_THEME["colors"]),
            "navy": "#eb001b",
            "navy_2": "#f79e1b",
            "paper": "#f7f5f3",
            "panel": "#ffffff",
            "line": "#e3d5cc",
            "text": "#1b1718",
            "muted": "#8a756d",
            "page_bg": "#f3f1ef",
            "border": "#e3d5cc",
            "header_gradient_end": "#f79e1b",
            "hotel_address": "#6b5a54",
            "table_head": "#f3e7dd",
            "table_row": "#efe6de",
            "placeholder": "#d8c7bd",
            "overlay": "rgba(255,255,255,0.10)",
            "overlay_border": "rgba(255,255,255,0.24)",
            "shadow": "rgba(80, 45, 20, 0.08)",
            "section_title": "#d3122f",
            "footer_bg": "#f4e6dc",
        },
        "layout": {
            **deepcopy(BASE_THEME["layout"]),
            "header_title_size": "30px",
            "header_title_size_print": "27px",
        },
    },
     "banco_guayaquil": {
        **deepcopy(BASE_THEME),
        "colors": {
            **deepcopy(BASE_THEME["colors"]),
            "navy": "#160F41",                  # Magno
            "navy_2": "#D2006E",               # Roma
            "paper": "#f7f6fb",
            "panel": "#ffffff",
            "line": "#ddd8ea",
            "text": "#160F41",                 # Magno
            "muted": "#6d6488",
            "page_bg": "#f2eff7",
            "border": "#ddd8ea",
            "header_gradient_end": "#A31A61", # Malbec
            "hotel_address": "#4a3f74",
            "table_head": "#f4eff8",
            "table_row": "#eee7f4",
            "placeholder": "#d7cfe4",
            "overlay": "rgba(255,255,255,0.12)",
            "overlay_border": "rgba(255,255,255,0.24)",
            "shadow": "rgba(22, 15, 65, 0.10)",
            "section_title": "#A31A61",       # Malbec
            "footer_bg": "#ece6f4",
        },
        "layout": {
            **deepcopy(BASE_THEME["layout"]),
            "header_title_size": "30px",
            "header_title_size_print": "27px",
        },
    },
}


def get_theme_config(theme_key: str | None) -> Dict[str, Any]:
    key = (theme_key or "default").strip().lower()
    return deepcopy(THEME_REGISTRY.get(key, THEME_REGISTRY["default"]))