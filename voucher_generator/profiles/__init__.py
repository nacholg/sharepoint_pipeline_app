from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from voucher_generator.profiles.client_demo_profile import PROFILE_CONFIG as CLIENT_DEMO_PROFILE_CONFIG
from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG
from voucher_generator.profiles.json_loader import load_json_profiles
from voucher_generator.profiles.mastercard_profile import PROFILE_CONFIG as MASTERCARD_PROFILE_CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent

PYTHON_PROFILES = {
    "default": deepcopy(DEFAULT_PROFILE_CONFIG),
    "mastercard": deepcopy(MASTERCARD_PROFILE_CONFIG),
    "client_demo": deepcopy(CLIENT_DEMO_PROFILE_CONFIG),
}

JSON_PROFILES = load_json_profiles(BASE_DIR)

PROFILE_REGISTRY = {
    **PYTHON_PROFILES,
    **JSON_PROFILES,  # JSON pisa Python si comparte key
}


def get_profile_config(profile_name: str | None) -> dict:
    key = (profile_name or "default").strip().lower()
    return deepcopy(PROFILE_REGISTRY.get(key, PROFILE_REGISTRY["default"]))


def list_profile_configs() -> list[dict]:
    return [deepcopy(config) for config in PROFILE_REGISTRY.values()]