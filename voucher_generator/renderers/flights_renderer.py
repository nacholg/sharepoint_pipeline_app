from typing import Any, Dict, List

from voucher_generator.flight_catalogs import (
    airline_display_name,
    airport_city_name,
)

from voucher_generator.renderers.common import (
    e,
    display_or_pending,
    no_break_iso_date,
)


def format_flight_datetime(date_value: Any, time_value: Any, language: str) -> str:
    date_html = no_break_iso_date(date_value, language=language) if date_value else ""
    time_html = e(time_value) if time_value not in (None, "") else ""

    if date_html and time_html:
        return f"{date_html} · {time_html}"
    return date_html or time_html or ""


def flight_segment_cards(
    segments: List[Dict[str, Any]],
    language: str,
    passengers: List[Dict[str, Any]] | None = None,
) -> str:
    cards: List[str] = []
    passengers = passengers or []

    for idx, segment in enumerate(segments or []):
        segment_order = segment.get("segment_order") or segment.get("source_segment_number") or ""
        flight_number = display_or_pending(segment.get("flight_number"), "Pendiente")
        origin = display_or_pending(segment.get("origin"), "—")
        destination = display_or_pending(segment.get("destination_airport"), "—")

        departure_date = (
            no_break_iso_date(segment.get("departure_date"), language=language)
            if segment.get("departure_date")
            else e("Pendiente")
        )
        arrival_date = (
            no_break_iso_date(segment.get("arrival_date"), language=language)
            if segment.get("arrival_date")
            else e("Pendiente")
        )

        departure_time = e(segment.get("departure_time")) if segment.get("departure_time") not in (None, "") else e("—")
        arrival_time = e(segment.get("arrival_time")) if segment.get("arrival_time") not in (None, "") else e("—")

        airline_name = airline_display_name(segment.get("flight_number"))
        origin_city = airport_city_name(segment.get("origin"))
        destination_city = airport_city_name(segment.get("destination_airport"))

        identity_rows = ""
        for passenger in passengers:
            identity_rows += f"""
              <div class="flight-identity-passenger">
                <div class="flight-passenger-name">
                  {e(passenger.get("full_name") or "Passenger")}
                </div>

                <div class="flight-identity-fields">
                  <div>
                    <div class="flight-label">Ticket Number</div>
                    <div class="flight-value">
                      {display_or_pending(passenger.get("ticket_number"), "—")}
                    </div>
                  </div>

                  <div>
                    <div class="flight-label">Airline Reservation Code</div>
                    <div class="flight-value">
                      {display_or_pending(passenger.get("airline_reservation_code"), "—")}
                    </div>
                  </div>
                </div>
              </div>
            """

        identity_html = ""
        if identity_rows:
            identity_html = f"""
              <div class="flight-identity">
                {identity_rows}
              </div>
            """

        cards.append(
            f"""
            <article class="flight-card flight-card-premium">
              <div class="flight-card-top">
                <div>
                  <div class="flight-kicker">Flight {e(segment_order)}</div>
                  <div class="flight-number">{e(airline_name) if airline_name else flight_number}</div>
                </div>
              </div>

              <div class="flight-route-premium">
                <div class="flight-airport">
                  <div class="flight-airport-code">{origin}</div>
                  <div class="flight-airport-city">{e(origin_city)}</div>
                  <div class="flight-time-main">{departure_time}</div>
                  <div class="flight-date-main">{departure_date}</div>
                </div>

                <div class="flight-path">
                  <div class="flight-path-line"></div>
                  <div class="flight-path-plane">✈</div>
                </div>

                <div class="flight-airport flight-airport-right">
                  <div class="flight-airport-code">{destination}</div>
                  <div class="flight-airport-city">{e(destination_city)}</div>
                  <div class="flight-time-main">{arrival_time}</div>
                  <div class="flight-date-main">{arrival_date}</div>
                </div>
              </div>

              {identity_html}
            </article>
            """
        )

        if idx < len(segments or []) - 1:
            cards.append(
                """
                <div class="flight-connection">
                  <div class="flight-connection-line"></div>
                  <div class="flight-connection-pill">Connecting flight</div>
                </div>
                """
            )

    return "\n".join(cards) or '<div class="empty-state">No flight segments loaded.</div>'


def flights_section(
    flights: Dict[str, Any],
    language: str,
    passengers: List[Dict[str, Any]] | None = None,
) -> str:
    flights = flights or {}
    passengers = passengers or []

    outbound = flights.get("outbound") or []
    return_flights = flights.get("return") or []

    if not outbound and not return_flights:
        return ""

    return f"""
      <section class="panel flights-panel">
        <button class="flights-toggle" type="button" onclick="this.closest('.flights-panel').classList.toggle('is-collapsed')">
          Flights
        </button>

        <div class="flights-collapsible-body">
          <div class="flights-grid">

            <section class="flight-direction">
                <button class="flight-direction-title flight-direction-toggle" type="button" onclick="this.closest('.flight-direction').classList.toggle('is-collapsed')">
                    Outbound
                </button>
                <div class="flight-direction-content">
                    {flight_segment_cards(outbound, language, passengers)}
                </div>
            </section>

            <section class="flight-direction">
                <button class="flight-direction-title flight-direction-toggle" type="button" onclick="this.closest('.flight-direction').classList.toggle('is-collapsed')">
                    Return
                </button>
                <div class="flight-direction-content">
                    {flight_segment_cards(return_flights, language, passengers)}
                </div>
            </section>

          </div>
        </div>
      </section>
    """