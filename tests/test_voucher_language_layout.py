from pathlib import Path

from voucher_generator.i18n import get_translations


BASE_DIR = Path(__file__).resolve().parents[1] / "voucher_generator"


def test_supported_languages_have_all_hotel_fact_labels() -> None:
    for language in ("es", "en", "pt"):
        translations = get_translations(language)

        assert translations["city"]
        assert translations["country"]
        assert translations["phone"]


def test_english_hotel_facts_reserve_more_space_for_country() -> None:
    css = (BASE_DIR / "assets" / "css" / "voucher.css").read_text(encoding="utf-8")

    assert 'html[lang="en"] .facts {' in css
    assert (
        "grid-template-columns: minmax(0, 0.55fr) minmax(0, 1.05fr) "
        "minmax(0, 1.4fr);"
    ) in css
    assert "white-space: nowrap;" in css
    assert 'html[lang="en"] .facts > div:last-child .fact-value {' in css
    assert "overflow-wrap: normal;" in css
