from __future__ import annotations

from voucher_generator.i18n.translations import TRANSLATIONS


DEFAULT_LANGUAGE = "es"


def normalize_language(language: str | None) -> str:
    key = (language or DEFAULT_LANGUAGE).strip().lower()
    if key not in TRANSLATIONS:
        return DEFAULT_LANGUAGE
    return key


def get_translations(language: str | None) -> dict[str, str]:
    key = normalize_language(language)
    return TRANSLATIONS[key]