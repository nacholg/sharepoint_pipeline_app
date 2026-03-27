from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class ProfileValidationError(Exception):
    pass


def validate_profile_config(profile: Dict[str, Any], base_dir: Path | None = None) -> List[str]:
    errors: List[str] = []

    key = profile.get("key")
    if not isinstance(key, str) or not key.strip():
        errors.append("Profile 'key' must be a non-empty string.")

    label = profile.get("label")
    if not isinstance(label, str) or not label.strip():
        errors.append("Profile 'label' must be a non-empty string.")

    branding = profile.get("branding")
    if not isinstance(branding, dict):
        errors.append("Profile 'branding' must be a dictionary.")
    else:
        theme_key = branding.get("theme_key")
        if not isinstance(theme_key, str) or not theme_key.strip():
            errors.append("Profile 'branding.theme_key' must be a non-empty string.")

        brand_logo = branding.get("brand_logo")
        if not isinstance(brand_logo, str) or not brand_logo.strip():
            errors.append("Profile 'branding.brand_logo' must be a non-empty string.")
        elif base_dir is not None:
            logo_path = (base_dir / brand_logo).resolve()
            if not logo_path.is_file():
                errors.append(f"Profile logo file does not exist: {brand_logo}")

    copy = profile.get("copy")
    if copy is not None and not isinstance(copy, dict):
        errors.append("Profile 'copy' must be a dictionary if provided.")

    rendering = profile.get("rendering")
    if rendering is not None:
        if not isinstance(rendering, dict):
            errors.append("Profile 'rendering' must be a dictionary if provided.")
        else:
            show_hotel_logo = rendering.get("show_hotel_logo")
            if show_hotel_logo is not None and not isinstance(show_hotel_logo, bool):
                errors.append("Profile 'rendering.show_hotel_logo' must be a boolean if provided.")

            header_mode = rendering.get("header_mode")
            if header_mode is not None and (not isinstance(header_mode, str) or not header_mode.strip()):
                errors.append("Profile 'rendering.header_mode' must be a non-empty string if provided.")

    return errors


def assert_valid_profile_config(profile: Dict[str, Any], base_dir: Path | None = None) -> None:
    errors = validate_profile_config(profile, base_dir=base_dir)
    if errors:
        raise ProfileValidationError("Invalid profile config:\n- " + "\n- ".join(errors))