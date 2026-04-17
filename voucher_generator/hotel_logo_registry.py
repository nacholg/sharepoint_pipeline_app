from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional


BASE_DIR = Path(__file__).resolve().parent

STOPWORDS = {
    "hotel",
    "the",
    "and",
    "resort",
    "spa",
    "by",
    "at",
}


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


def tokenize_text(value: str | None) -> list[str]:
    normalized = clean_text(value)
    if not normalized:
        return []

    return [token for token in normalized.split() if token and token not in STOPWORDS]


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


def score_registry_match(hotel_name: str, registry_key: str) -> int:
    hotel_norm = clean_text(hotel_name)
    key_norm = clean_text(registry_key)

    if not hotel_norm or not key_norm:
        return -1

    if hotel_norm == key_norm:
        return 1000

    score = 0

    if key_norm in hotel_norm:
        score += 300

    if hotel_norm in key_norm:
        score += 200

    hotel_tokens = set(tokenize_text(hotel_name))
    key_tokens = set(tokenize_text(registry_key))

    if not hotel_tokens or not key_tokens:
        return score

    overlap = hotel_tokens & key_tokens
    if overlap:
        score += len(overlap) * 25

    if key_tokens and key_tokens.issubset(hotel_tokens):
        score += 150

    if hotel_tokens and hotel_tokens.issubset(key_tokens):
        score += 100

    return score


def find_manual_logo(
    hotel_name: str | None,
    registry: Dict[str, str] | None = None,
    path: str | Path | None = None,
) -> Optional[str]:
    key = clean_text(hotel_name)
    if not key:
        return None

    registry_data = registry if registry is not None else load_hotel_logo_registry(path)
    if not registry_data:
        return None

    best_key: Optional[str] = None
    best_path: Optional[str] = None
    best_score = -1

    for registry_key, logo_path in registry_data.items():
        score = score_registry_match(key, registry_key)
        if score > best_score:
            best_score = score
            best_key = registry_key
            best_path = logo_path

    if best_score < 50:
        return None

    print(
        f"[MANUAL_LOGO_MATCH] hotel='{hotel_name}' | "
        f"registry_key='{best_key}' | "
        f"score={best_score} | "
        f"path='{best_path}'"
    )
    return best_path