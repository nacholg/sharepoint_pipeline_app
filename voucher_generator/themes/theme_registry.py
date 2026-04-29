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

    "banco_guayaquil": deepcopy(BASE_THEME),

    "santander": deepcopy(BASE_THEME),
}


# =============================================================================
# Banco Guayaquil
# =============================================================================

THEME_REGISTRY["banco_guayaquil"]["colors"].update({
    "navy": "#D2006E",
    "navy_2": "#A31A61",
    "paper": "#ffffff",
    "panel": "#fff7fb",
    "page_bg": "#f7f3f6",
    "border": "#ead9e3",
    "line": "#edd0df",
    "text": "#160F41",
    "muted": "#7a4a67",
    "section_title": "#A31A61",
    "hotel_address": "#4a3a5f",
    "header_gradient_end": "#A31A61",
    "table_head": "#fceaf3",
    "table_row": "#f4d7e5",
    "footer_bg": "#fdf2f8",
    "placeholder": "#d9a8c4",
    "overlay": "rgba(255,255,255,0.16)",
    "overlay_border": "rgba(255,255,255,0.28)",
    "shadow": "rgba(22, 15, 65, 0.12)",
})

THEME_REGISTRY["banco_guayaquil"]["fonts"].update({
    "family": "Inter, Arial, Helvetica, sans-serif",
})

THEME_REGISTRY["banco_guayaquil"]["layout"].update({
    "logo_box_width": 220,
    "logo_box_min_height": 108,
    "brand_logo_height": 82,
    "brand_logo_height_print": 72,
    "print_logo_box_width": 200,
    "print_logo_box_min_height": 98,
    "header_title_size": "30px",
    "header_title_size_print": "27px",
    "header_subtitle_size": "13px",
    "header_subtitle_size_print": "12px",
})


# =============================================================================
# Santander México
# =============================================================================

THEME_REGISTRY["santander"]["colors"].update({
    "navy": "#EC0000",
    "navy_2": "#990000",
    "paper": "#ffffff",
    "panel": "#ffffff",
    "page_bg": "#f7f7f7",
    "border": "#ead6d6",
    "line": "#ead6d6",
    "text": "#000000",
    "muted": "#666666",
    "section_title": "#EC0000",
    "hotel_address": "#333333",
    "header_gradient_end": "#990000",
    "table_head": "#FBF1EA",
    "table_row": "#FCE8E4",
    "footer_bg": "#FBF1EA",
    "placeholder": "#F0B998",
    "overlay": "rgba(255,255,255,0.16)",
    "overlay_border": "rgba(255,255,255,0.28)",
    "shadow": "rgba(0, 0, 0, 0.10)",
})

THEME_REGISTRY["santander"]["fonts"].update({
    "family": "Inter, Arial, Helvetica, sans-serif",
})

THEME_REGISTRY["santander"]["layout"].update({
    "logo_box_width": 210,
    "logo_box_min_height": 100,
    "brand_logo_height": 58,
    "brand_logo_height_print": 50,
    "print_logo_box_width": 190,
    "print_logo_box_min_height": 90,
    "header_title_size": "30px",
    "header_title_size_print": "27px",
    "header_subtitle_size": "13px",
    "header_subtitle_size_print": "12px",
})


def get_theme_config(theme_key: str | None) -> Dict[str, Any]:
    key = (theme_key or "default").strip().lower()
    return deepcopy(THEME_REGISTRY.get(key, THEME_REGISTRY["default"]))
