from voucher_generator.profiles.default_profile import PROFILE_CONFIG as DEFAULT_PROFILE_CONFIG
from voucher_generator.profiles.mastercard_profile import PROFILE_CONFIG as MASTERCARD_PROFILE_CONFIG

PROFILE_REGISTRY = {
    "default": DEFAULT_PROFILE_CONFIG,
    "mastercard": MASTERCARD_PROFILE_CONFIG,
}


def get_profile_config(profile_name: str | None) -> dict:
    key = (profile_name or "default").strip().lower()
    return PROFILE_REGISTRY.get(key, DEFAULT_PROFILE_CONFIG)


def list_profile_configs() -> list[dict]:
    return list(PROFILE_REGISTRY.values())