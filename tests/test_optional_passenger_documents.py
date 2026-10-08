from voucher_generator.i18n import get_translations
from voucher_generator.renderers.hotel_renderer import passenger_cards


PASSENGERS = [
    {
        "full_name": "Victor Kevin Anzulovich",
        "nationality": "Argentina",
        "passport_number": "AAJ140834",
        "passport_expiration": "2033-06-29",
    }
]


def test_passenger_documents_are_included_by_default() -> None:
    html = passenger_cards(PASSENGERS, get_translations("es"), "es")

    assert "Victor Kevin Anzulovich" in html
    assert "Argentina" in html
    assert "AAJ140834" in html
    assert "29 Jun 2033" in html


def test_passenger_documents_can_be_hidden_without_hiding_name() -> None:
    html = passenger_cards(
        PASSENGERS,
        get_translations("es"),
        "es",
        include_documents=False,
    )

    assert "Victor Kevin Anzulovich" in html
    assert "pax-card-name-only" in html
    assert "Argentina" not in html
    assert "AAJ140834" not in html
    assert "29 Jun 2033" not in html
    assert "pax-meta-row" not in html
