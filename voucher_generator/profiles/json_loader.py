from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from voucher_generator.profiles.profile_validator import assert_valid_profile_config

def load_json_profiles(base_dir: Path) -> Dict[str, Dict[str, Any]]:
    profiles_dir = base_dir / "config" / "profiles"

    if not profiles_dir.exists():
        return {}

    profiles: Dict[str, Dict[str, Any]] = {}

    for file in profiles_dir.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            key = (data.get("key") or file.stem).strip().lower()

            if not key:
                continue

            profiles[key] = data

        except Exception as e:
            print(f"[WARN] Failed loading profile {file}: {e}")

    return profiles