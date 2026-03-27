from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG
from voucher_generator.profiles.mastercard_profile import PROFILE_CONFIG as MASTERCARD_PROFILE_CONFIG


def deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


PROFILE_REGISTRY = {
    "default": deepcopy(DEFAULT_PROFILE_CONFIG),
    "mastercard": deepcopy(MASTERCARD_PROFILE_CONFIG),
}


def get_profile_config(profile_name: str | None) -> dict:
    key = (profile_name or "default").strip().lower()
    return deepcopy(PROFILE_REGISTRY.get(key, PROFILE_REGISTRY["default"]))


def list_profile_configs() -> list[dict]:
    return [deepcopy(config) for config in PROFILE_REGISTRY.values()]
