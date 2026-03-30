from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Dict

from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG
from voucher_generator.profiles.json_loader import load_json_profiles
from voucher_generator.profiles.profile_validator import assert_valid_profile_config
from voucher_generator.profiles.utils import deep_merge_dict


def load_python_profile(profile_key: str) -> Dict[str, Any]:
    profile_key = (profile_key or "default").strip().lower()
    module_name = f"voucher_generator.profiles.{profile_key}_profile"

    try:
        module = import_module(module_name)
        return getattr(module, "PROFILE_CONFIG")
    except ModuleNotFoundError:
        if profile_key != "default":
            return load_python_profile("default")
        raise


def load_profile(profile_key: str | None, base_dir: Path) -> Dict[str, Any]:
    profile_key = (profile_key or "default").strip().lower()

    json_profiles = load_json_profiles(base_dir)
    json_profile = json_profiles.get(profile_key)

    if json_profile:
        profile = json_profile
    else:
        profile = load_python_profile(profile_key)

    if profile_key != "default":
        default_json = json_profiles.get("default")
        default_profile = default_json or DEFAULT_PROFILE_CONFIG
        profile = deep_merge_dict(default_profile, profile)

    assert_valid_profile_config(profile, base_dir=base_dir)

    return profile