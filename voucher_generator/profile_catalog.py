from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

CANDIDATE_CONFIG_DIRS = [
    BASE_DIR / "config" / "profiles",
    PROJECT_ROOT / "config" / "profiles",
    BASE_DIR / "config_profiles",
    PROJECT_ROOT / "config_profiles",
]


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        print(f"[profile_catalog] JSON no es objeto: {path}")
    except Exception as e:
        print(f"[profile_catalog] Error leyendo {path}: {e}")
        return None
    return None


def _resolve_config_dir() -> Path | None:
    for candidate in CANDIDATE_CONFIG_DIRS:
       # print(
        #    f"[profile_catalog] probing CONFIG_DIR={candidate} "
        #    f"exists={candidate.exists()} is_dir={candidate.is_dir()}"
        #)
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def load_profiles_map() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}

    #print(f"[profile_catalog] BASE_DIR={BASE_DIR}")
    #print(f"[profile_catalog] PROJECT_ROOT={PROJECT_ROOT}")

    config_dir = _resolve_config_dir()
    if not config_dir:
        #print("[profile_catalog] No se encontró ninguna carpeta de profiles válida")
        return profiles

    #print(f"[profile_catalog] Usando CONFIG_DIR={config_dir}")

    for path in sorted(config_dir.glob("*.json")):
        #print(f"[profile_catalog] Leyendo profile JSON: {path}")
        data = _safe_load_json(path)
        if not data:
            continue

        key = str(data.get("key", "")).strip()
        if not key:
            #print(f"[profile_catalog] JSON sin key: {path}")
            continue

        profiles[key] = data
        #print(f"[profile_catalog] Profile cargado: key={key}")

    #print(f"[profile_catalog] Profiles finales: {list(profiles.keys())}")
    return profiles


def load_available_profiles() -> list[dict[str, Any]]:
    profiles_map = load_profiles_map()

    profiles: list[dict[str, Any]] = []

    for key, data in profiles_map.items():
        label = str(data.get("label", key)).strip() or key
        profiles.append(
            {
                "key": key,
                "label": label,
                "enabled": True,
            }
        )

    if "default" not in profiles_map:
        profiles.insert(
            0,
            {
                "key": "default",
                "label": "Default",
                "enabled": True,
            },
        )

    return profiles