from voucher_generator.xlsx_importer import get_flight_field_from_header
from voucher_generator.renderers.flights_renderer import flight_labels, flights_section


def test_destination_airport_header_aliases():
    for header in (
        "AIRPORT",
        "AIRPORT DESTINATION",
        "DESTINATION AIRPORT",
        "ARRIVAL AIRPORT",
        "AIRPORT OF ARRIVAL",
        "TO AIRPORT",
    ):
        assert get_flight_field_from_header(header) == "destination_airport"


def test_flight_labels_localized_in_spanish():
    assert flight_labels("es")["flights"] == "Vuelos"
    assert flight_labels("es")["connection"] == "Vuelo de conexión"
    assert flight_labels("en")["flights"] == "Flights"


def test_spanish_airline_identity_and_segments():
    flights = {"outbound": [{"segment_order": 1, "flight_number": "AA1486",
                            "origin": "GUA", "destination_airport": "DFW",
                            "departure_date": "2026-11-09", "arrival_date": "2026-11-09",
                            "departure_time": "13:06", "arrival_time": "16:50"}],
               "return": []}
    passengers = [{"full_name": "Test Passenger", "ticket_number": "0012387343411",
                   "airline_reservation_code": "HZKYTO"}]
    html = flights_section(flights, "es", passengers)
    assert "Vuelo 1" in html
    assert "Número de ticket" in html
    assert "Código de reserva aérea" in html
    assert "HZKYTO" in html
    assert "DFW" in html
