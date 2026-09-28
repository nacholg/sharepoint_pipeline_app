from pathlib import Path

from app.client_registry import build_clients
from voucher_generator.profiles.profile_loader import load_profile
from voucher_generator.themes.theme_registry import get_theme_config


BASE_DIR = Path(__file__).resolve().parents[1] / "voucher_generator"


def test_zurich_santander_profile_loads_with_argentina_logo() -> None:
    profile = load_profile("zurich_santander", BASE_DIR)

    assert profile["key"] == "zurich_santander"
    assert profile["label"] == "Zurich Santander"
    assert profile["branding"]["theme_key"] == "zurich_santander"
    assert (BASE_DIR / profile["branding"]["brand_logo"]).is_file()


def test_zurich_santander_theme_uses_official_rgb_palette() -> None:
    theme = get_theme_config("zurich_santander")

    assert theme["colors"]["navy"] == "#3A57F0"
    assert theme["colors"]["navy_2"] == "#FF3333"
    assert theme["colors"]["text"] == "#080808"
    assert theme["fonts"]["family"].startswith("'Open Sans'")


def test_zurich_santander_is_available_as_client() -> None:
    client = build_clients()["zurich_santander"]

    assert client["label"] == "Zurich Santander"
    assert client["default_profile"] == "zurich_santander"
