from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List

from voucher_generator.profiles.json_loader import load_json_profiles
from voucher_generator.profiles.profile_loader import load_profile

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_python_profile(profile_key: str) -> Dict[str, Any] | None:
    module_name = f"voucher_generator.profiles.{profile_key}_profile"
    try:
        module = import_module(module_name)
        return getattr(module, "PROFILE_CONFIG", None)
    except ModuleNotFoundError:
        return None


def get_profile_config(profile_key: str | None = None) -> Dict[str, Any]:
    return load_profile(profile_key or "default", BASE_DIR)


def list_profile_configs() -> List[Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}

    # JSON primero
    json_profiles = load_json_profiles(BASE_DIR)
    for key, profile in json_profiles.items():
        profiles[key] = profile

    # fallback Python legacy
    for key in ["default", "mastercard", "banco_guayaquil"]:
        if key not in profiles:
            py_profile = _load_python_profile(key)
            if py_profile:
                profiles[key] = py_profile

    return sorted(
        profiles.values(),
        key=lambda p: p.get("label", p.get("key", ""))
    )