from pathlib import Path

from voucher_generator.profiles.profile_loader import load_profile
from voucher_generator.themes.theme_registry import get_theme_config


BASE_DIR = Path(__file__).resolve().parents[1] / "voucher_generator"


def test_toyota_profile_loads_with_supplied_logo() -> None:
    profile = load_profile("toyota", BASE_DIR)

    assert profile["key"] == "toyota"
    assert profile["label"] == "Toyota"
    assert profile["branding"]["theme_key"] == "toyota"
    assert (
        BASE_DIR / profile["branding"]["brand_logo"]
    ).is_file()


def test_toyota_theme_uses_restrained_brand_treatment() -> None:
    theme = get_theme_config("toyota")

    assert theme["colors"]["navy"] == "#EB0A1E"
    assert theme["colors"]["header_gradient_end"] == "#EB0A1E"
    assert theme["colors"]["text"] == "#111111"
    assert theme["fonts"]["family"].startswith("Arial")
    assert theme["radius"]["page"] == "12px"


def test_hotel_facts_reserve_space_for_long_phone_numbers() -> None:
    css = (BASE_DIR / "assets" / "css" / "voucher.css").read_text(encoding="utf-8")

    assert (
        "grid-template-columns: minmax(0, 0.8fr) minmax(0, 0.8fr) "
        "minmax(0, 1.4fr);"
    ) in css
    assert ".facts > div {\n      min-width: 0;\n    }" in css
    assert "overflow-wrap: anywhere;" in css
