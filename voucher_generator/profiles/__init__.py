from __future__ import annotations

from copy import deepcopy
from pathlib import Path


from voucher_generator.profiles.utils import deep_merge_dict
from voucher_generator.profiles.profile_validator import assert_valid_profile_config

from voucher_generator.profiles.client_demo_profile import PROFILE_CONFIG as CLIENT_DEMO_PROFILE_CONFIG
from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG
from voucher_generator.profiles.json_loader import load_json_profiles
from voucher_generator.profiles.mastercard_profile import PROFILE_CONFIG as MASTERCARD_PROFILE_CONFIG
from voucher_generator.profiles.banco_guayaquil_profile import PROFILE_CONFIG as BANCO_GUAYAQUIL_PROFILE_CONFIG


BASE_DIR = Path(__file__).resolve().parent.parent

PYTHON_PROFILES = {
    "default": deepcopy(DEFAULT_PROFILE_CONFIG),
    "mastercard": deepcopy(MASTERCARD_PROFILE_CONFIG),
    "banco_guayaquil": deepcopy(BANCO_GUAYAQUIL_PROFILE_CONFIG),
    "client_demo": deepcopy(CLIENT_DEMO_PROFILE_CONFIG),
}

JSON_PROFILES = load_json_profiles(BASE_DIR)

PROFILE_REGISTRY = {}

# primero cargar python profiles
for key, base_profile in PYTHON_PROFILES.items():
    PROFILE_REGISTRY[key] = deepcopy(base_profile)

# luego aplicar overrides JSON
for key, json_profile in JSON_PROFILES.items():
    base_profile = PROFILE_REGISTRY.get(key, deepcopy(DEFAULT_PROFILE_CONFIG))

    merged_profile = deep_merge_dict(base_profile, json_profile)

    # 🔥 VALIDAR EL RESULTADO FINAL
    assert_valid_profile_config(merged_profile, base_dir=BASE_DIR)

    PROFILE_REGISTRY[key] = merged_profile


def get_profile_config(profile_name: str | None) -> dict:
    key = (profile_name or "default").strip().lower()
    return deepcopy(PROFILE_REGISTRY.get(key, PROFILE_REGISTRY["default"]))


def list_profile_configs() -> list[dict]:
    return [deepcopy(config) for config in PROFILE_REGISTRY.values()]