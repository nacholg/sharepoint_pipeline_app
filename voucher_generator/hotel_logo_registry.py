from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional


BASE_DIR = Path(__file__).resolve().parent


def default_registry_path() -> Path:
    return BASE_DIR / "config" / "hotel_logo_registry.json"


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_hotel_logo_registry(path: str | Path | None = None) -> Dict[str, str]:
    registry_path = Path(path) if path else default_registry_path()

    if not registry_path.exists():
        return {}

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    normalized: Dict[str, str] = {}
    for hotel_name, logo_path in data.items():
        key = clean_text(str(hotel_name))
        value = str(logo_path).strip()
        if key and value:
            normalized[key] = value

    return normalized


def find_manual_logo(
    hotel_name: str | None,
    registry: Dict[str, str] | None = None,
    path: str | Path | None = None,
) -> Optional[str]:
    key = clean_text(hotel_name)
    if not key:
        return None

    registry_data = registry if registry is not None else load_hotel_logo_registry(path)
    return registry_data.get(key)