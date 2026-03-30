from __future__ import annotations

from typing import Any

from voucher_generator.profile_catalog import load_profiles_map


PROFILES_MAP = load_profiles_map()


BASE_CLIENTS = {
    "globalevents2": {
        "site_key": "globalevents2",
        "source_site_key": "globalevents2",
        "destination_site_key": "globalevents2",
        "default_folder_path": "/General",
    },
    "mastercard": {
        "site_key": "mastercard",
        "source_site_key": "mastercard",
        "destination_site_key": "mastercard",
        "default_folder_path": "/",
    },
    "banco_guayaquil": {
        "site_key": "globalevents2",
        "source_site_key": "globalevents2",
        "destination_site_key": "globalevents2",
        "default_folder_path": "/General",
    },
}


def build_clients() -> dict[str, dict[str, Any]]:
    clients: dict[str, dict[str, Any]] = {}

    for key, base in BASE_CLIENTS.items():
        profile = PROFILES_MAP.get(key, {})

        clients[key] = {
            "key": key,
            "label": profile.get("label", key),
            "default_profile": key,
            "brand_logo": (
                profile.get("branding", {}).get("brand_logo")
            ),
            **base,
        }

    return clients


CLIENTS = build_clients()