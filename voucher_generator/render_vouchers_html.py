from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from voucher_generator.themes.theme_registry import get_theme_config
from voucher_generator.i18n import get_translations, normalize_language
from voucher_generator.flight_catalogs import airline_display_name, airport_city_name
from voucher_generator.profiles.profile_loader import load_profile



BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE_KEY = "default"


def clean_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value[:120] or "voucher"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def e(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def display_or_pending(value: Any, pending: str = "Pendiente") -> str:
    return e(value) if value not in (None, "") else e(pending)


def no_break_phone(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = html.escape(str(value).strip())
    text = text.replace(" ", "&nbsp;")
    text = text.replace("-", "&#8209;")
    return text


def no_break_iso_date(value: Any, language: str = "es") -> str:
    if value in (None, ""):
        return ""

    text = str(value).strip()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year, month, day = text.split("-")

        month_maps = {
            "es": {
                "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr",
                "05": "May", "06": "Jun", "07": "Jul", "08": "Ago",
                "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic",
            },
            "en": {
                "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
            },
            "pt": {
                "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
                "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
                "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
            },
        }

        month_map = month_maps.get(language, month_maps["es"])
        month_label = month_map.get(month, month)
        formatted = f"{day} {month_label} {year}"
        return html.escape(formatted)

    return html.escape(text)


def format_fact_value(label: str, value: Any, t: dict[str, str], language: str) -> str:
    raw_label = (label or "").strip().lower()

    if value in (None, ""):
        return e(t["empty"])

    if raw_label in {"city", "country", "destination"}:
        return e(value)

    if raw_label in {"phone", "telephone"}:
        return no_break_phone(value)

    if raw_label in {"check in", "check-out", "check out", "date"}:
        return no_break_iso_date(value, language=language)

    return e(value)


def file_to_data_uri(path: Path) -> Optional[str]:
    try:
        if not path.exists() or not path.is_file():
            return None
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None


def resolve_logo_src(
    value: Optional[str],
    output_dir: Path,
    debug: bool = False,
    label: str = "logo",
) -> Optional[str]:
    if not value:
        if debug:
            print(f"[DEBUG] {label}: no value provided")
        return None

    value = str(value).strip()
    if not value:
        if debug:
            print(f"[DEBUG] {label}: empty value after strip")
        return None

    if value.startswith(("http://", "https://", "data:")):
        if debug:
            print(f"[DEBUG] {label}: using remote/data URI source")
        return value

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (BASE_DIR / candidate).resolve()

    if debug:
        print(f"[DEBUG] {label}: raw='{value}'")
        print(f"[DEBUG] {label}: BASE_DIR='{BASE_DIR}'")
        print(f"[DEBUG] {label}: resolved='{candidate}'")
        print(
            f"[DEBUG] {label}: exists={candidate.exists()} "
            f"is_file={candidate.is_file() if candidate.exists() else False}"
        )

    data_uri = file_to_data_uri(candidate)
    if data_uri:
        if debug:
            print(f"[DEBUG] {label}: embedded as data URI")
        return data_uri

    try:
        relative_path = Path(os.path.relpath(candidate, start=output_dir)).as_posix()
        if debug:
            print(f"[DEBUG] {label}: fallback relative path='{relative_path}'")
        return relative_path
    except Exception as exc:
        if debug:
            print(f"[DEBUG] {label}: relpath fallback failed: {exc}")
        return candidate.as_posix()


def hotel_logo_src(hotel: Dict[str, Any], output_dir: Path, debug: bool = False) -> Optional[str]:
    preferred_logo = (
        hotel.get("manual_logo_path")
        or hotel.get("local_logo_path")
        or hotel.get("downloaded_logo_path")
        or hotel.get("logo_url")
    )
    return resolve_logo_src(
        preferred_logo,
        output_dir=output_dir,
        debug=debug,
        label="hotel_logo",
    )


def passenger_cards(passengers: List[Dict[str, Any]], t: dict[str, str], language: str) -> str:
    cards: List[str] = []
    for pax in passengers:
        nationality_html = display_or_pending(pax.get("nationality"), t["empty"])
        passport_html = display_or_pending(pax.get("passport_number"), t["empty"])
        expiration_html = display_or_pending(pax.get("passport_expiration"), t["empty"])
        if pax.get("passport_expiration") not in (None, ""):
            expiration_html = no_break_iso_date(pax.get("passport_expiration"), language=language)

        cards.append(
            f"""
            <article class="pax-card">
              <div class="pax-name">{e(pax.get('full_name') or t['passenger_fallback'])}</div>
              <div class="pax-meta-row"><span class="pax-label">{e(t["nationality"])}</span><span class="pax-value">{nationality_html}</span></div>
              <div class="pax-meta-row"><span class="pax-label">{e(t["passport"])}</span><span class="pax-value">{passport_html}</span></div>
              <div class="pax-meta-row"><span class="pax-label">{e(t["passport_expiry"])}</span><span class="pax-value">{expiration_html}</span></div>
            </article>
            """
        )
    return "\n".join(cards) or f'<div class="empty-state">{e(t["no_passengers_loaded"])}</div>'


def room_rows(rooms: List[Dict[str, Any]], t: dict[str, str]) -> str:
    rows: List[str] = []
    for room in rooms:
        rows.append(
            f"""
            <tr>
              <td>{display_or_pending(room.get('room_count'), t['empty'])}</td>
              <td class="text-wrap">{display_or_pending(room.get('room_category'), t['empty'])}</td>
              <td class="text-wrap">{display_or_pending(room.get('additional_info'), t['empty'])}</td>
              <td>{display_or_pending(room.get('pax_count'), t['empty'])}</td>
            </tr>
            """
        )
    return "\n".join(rows) or f'<tr><td colspan="4">{e(t["no_rooming_details"])}</td></tr>'



def format_flight_datetime(date_value: Any, time_value: Any, language: str) -> str:
    date_html = no_break_iso_date(date_value, language=language) if date_value else ""
    time_html = e(time_value) if time_value not in (None, "") else ""

    if date_html and time_html:
        return f"{date_html} · {time_html}"
    return date_html or time_html or ""


def flight_segment_cards(segments: List[Dict[str, Any]], language: str) -> str:
    cards: List[str] = []

    for idx, segment in enumerate(segments or []):
        segment_order = segment.get("segment_order") or segment.get("source_segment_number") or ""
        flight_number = display_or_pending(segment.get("flight_number"), "Pendiente")
        origin = display_or_pending(segment.get("origin"), "—")
        destination = display_or_pending(segment.get("destination_airport"), "—")

        departure_date = no_break_iso_date(segment.get("departure_date"), language=language) if segment.get("departure_date") else e("Pendiente")
        arrival_date = no_break_iso_date(segment.get("arrival_date"), language=language) if segment.get("arrival_date") else e("Pendiente")

        departure_time = e(segment.get("departure_time")) if segment.get("departure_time") not in (None, "") else e("—")
        arrival_time = e(segment.get("arrival_time")) if segment.get("arrival_time") not in (None, "") else e("—")

        airline_name = airline_display_name(segment.get("flight_number"))
        origin_city = airport_city_name(segment.get("origin"))
        destination_city = airport_city_name(segment.get("destination_airport"))

        ticket_number = segment.get("ticket_number")
        airline_reservation_code = segment.get("airline_reservation_code")

        identity_html = ""
        if ticket_number or airline_reservation_code:
            identity_html = f"""
              <div class="flight-identity">
                <div>
                  <div class="flight-label">Ticket Number</div>
                  <div class="flight-value">{display_or_pending(ticket_number, "—")}</div>
                </div>
                <div>
                  <div class="flight-label">Airline Reservation Code</div>
                  <div class="flight-value">{display_or_pending(airline_reservation_code, "—")}</div>
                </div>
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

def flights_section(flights: Dict[str, Any], language: str) -> str:
    flights = flights or {}
    outbound = flights.get("outbound") or []
    return_flights = flights.get("return") or []

    if not outbound and not return_flights:
        return ""

    return f"""
      <section class="panel flights-panel">
        <div class="section-title">Flights</div>
        <div class="flights-grid">
          <div class="flight-direction">
            <div class="flight-direction-title">Outbound</div>
            {flight_segment_cards(outbound, language)}
          </div>
          <div class="flight-direction">
            <div class="flight-direction-title">Return</div>
            {flight_segment_cards(return_flights, language)}
          </div>
        </div>
      </section>
    """


def summary_tiles(
    stay: Dict[str, Any],
    t: dict[str, str],
    language: str,
    passengers: Optional[List[Dict[str, Any]]] = None,
) -> str:
    passengers = passengers or []

    def first_present(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", "-", "--"):
                return value
        return None

    meals_value = first_present(
        stay.get("meal_plan"),
        stay.get("meals"),
        *(pax.get("meals") for pax in passengers if isinstance(pax, dict)),
        *(pax.get("remarks") for pax in passengers if isinstance(pax, dict)),
    )

    food_restrictions_value = first_present(
        stay.get("food_restrictions"),
        *(pax.get("food_restrictions") for pax in passengers if isinstance(pax, dict)),
    )

    items = [
        (
            t["check_in"],
            no_break_iso_date(stay.get("check_in"), language=language)
            if stay.get("check_in")
            else e(t["empty"]),
        ),
        (
            t["check_out"],
            no_break_iso_date(stay.get("check_out"), language=language)
            if stay.get("check_out")
            else e(t["empty"]),
        ),
        (
            t["nights"],
            display_or_pending(stay.get("nights"), t["empty"]),
        ),
        (
            t["meals"],
            display_or_pending(meals_value, t["empty"]),
        ),
    ]

    if "food_restrictions" in t:
        items.append(
            (
                t["food_restrictions"],
                display_or_pending(food_restrictions_value, t["empty"]),
            )
        )

    return "\n".join(
        f'<div class="summary-tile"><div class="tile-label">{e(label)}</div><div class="tile-value">{value}</div></div>'
        for label, value in items
    )


def extract_primary_last_name(voucher_payload: Dict[str, Any], idx: int) -> str:
    passengers = voucher_payload.get("passengers", []) or []

    for pax in passengers:
        last_name = str(pax.get("last_name") or "").strip()
        if last_name:
            return last_name

        full_name = str(pax.get("full_name") or "").strip()
        if full_name:
            parts = [p for p in full_name.split() if p.strip()]
            if parts:
                return parts[-1]

    return f"VOUCHER_{idx:02d}"


def build_output_filename(voucher_payload: Dict[str, Any], idx: int) -> str:
    last_name = extract_primary_last_name(voucher_payload, idx)
    return clean_filename(f"{last_name}_{idx:02d}.html")


def build_html(
    voucher_payload: Dict[str, Any],
    output_dir: Path,
    profile_config: Dict[str, Any],
    brand_logo: Optional[str],
    debug: bool = False,
    language_override: Optional[str] = None,
    render_mode: str = "hotel",
) -> str:
    voucher = voucher_payload.get("voucher", {})
    hotel = voucher_payload.get("hotel", {})
    stay = voucher_payload.get("stay", {})
    rooms = voucher_payload.get("rooms", [])
    flights = voucher_payload.get("flights", {}) or {}
    passengers = voucher_payload.get("passengers", [])

    render_mode = (render_mode or "hotel").strip().lower()
    if render_mode not in {"hotel", "flights", "full"}:
        render_mode = "hotel"

    branding = profile_config.get("branding", {}) or {}
    theme_key = branding.get("theme_key") or DEFAULT_PROFILE_KEY
    theme = get_theme_config(theme_key)
    voucher_css = load_text(BASE_DIR / "assets" / "css" / "voucher.css")
    colors = theme["colors"]
    fonts = theme["fonts"]
    radius = theme["radius"]
    layout = theme["layout"]
    copy_config = profile_config.get("copy", {}) or {}

    profile_lang = normalize_language(profile_config.get("language"))
    language = language_override or profile_lang or "es"
    t = get_translations(language)

    voucher_kicker = copy_config.get("voucher_kicker") or t["voucher_kicker"]
    if render_mode == "full":
        voucher_kicker = "Voucher de Hotel + Vuelos"
    footer_note = copy_config.get("footer_note") or t["footer_note"]

    brand_logo_src = resolve_logo_src(
        brand_logo or branding.get("brand_logo"),
        output_dir=output_dir,
        debug=debug,
        label="brand_logo",
    )
    header_brand_logo_html = (
        f'<img class="brand-box-logo" src="{e(brand_logo_src)}" alt="Brand logo">'
        if brand_logo_src
        else f'<div class="brand-box-placeholder">{e(t["brand_logo_placeholder"])}</div>'
    )

    hotel_src = hotel_logo_src(hotel, output_dir, debug=debug)
    hotel_logo_html = (
        f'<img class="hotel-logo" src="{e(hotel_src)}" alt="Hotel logo">'
        if hotel_src
        else f'<div class="hotel-logo-placeholder">{e(t["hotel_logo_placeholder"])}</div>'
    )

    hotel_name = hotel.get("display_name") or hotel.get("name") or "Hotel"
    header_title = e(
        voucher_payload.get("event_name")
        or hotel.get("display_name")
        or hotel.get("name")
        or voucher_kicker
    )

    city = hotel.get("city")
    country = hotel.get("country")
    subtitle_parts = [p for p in [city, country] if p]
    header_subtitle = e(" · ".join(subtitle_parts))

    conf_html = display_or_pending(voucher_payload.get("confirmation_number"), t["pending"])

    city_html = format_fact_value("city", hotel.get("city"), t, language)
    country_html = format_fact_value("country", hotel.get("country"), t, language)
    phone_html = format_fact_value("phone", hotel.get("phone"), t, language)
    flights_html = flights_section(flights, language)

    if render_mode == "flights":
        return f"""<!DOCTYPE html>
<html lang="{e(language)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{header_title} - Flight Voucher</title>
  <style>
  :root {{
      --section-title: {colors['section_title']};
      --footer-bg: {colors['footer_bg']};
      --navy: {colors['navy']};
      --paper: {colors['paper']};
      --panel: {colors['panel']};
      --line: {colors['line']};
      --text: {colors['text']};
      --muted: {colors['muted']};
      --white: {colors['white']};
      --page-bg: {colors['page_bg']};
      --page-border: {colors['border']};
      --header-gradient-end: {colors['header_gradient_end']};
      --shadow-color: {colors['shadow']};
      --radius-page: {radius['page']};
      --radius-lg: {radius['lg']};
      --radius-md: {radius['md']};
      --radius-sm: {radius['sm']};
      --page-width: {layout['page_width_px']}px;
      --page-min-height: {layout['page_min_height_px']}px;
      --font-family: {fonts['family']};
      --shadow: 0 12px 32px var(--shadow-color);
    }}
  {voucher_css}
  
  </style>
    
</head>
<body>
  <div class="page">
    <header class="header">
      <div>
        <div class="voucher-kicker">Flight Voucher</div>
        <div class="header-title">{header_title}</div>
        <div class="header-subtitle">{header_subtitle}</div>
      </div>
      <div class="logo-box">
        {header_brand_logo_html}
      </div>
    </header>
    <main class="body">
      {flights_html or '<section class="panel"><div class="section-title">Flights</div><div class="empty-state">No flight segments loaded.</div></section>'}

      <section class="panel">
        <div class="section-title">{e(t["passengers"])}</div>
        <div class="passengers-grid">
          {passenger_cards(passengers, t, language)}
        </div>
      </section>
      <div class="footer-note">{e(footer_note)}</div>
    </main>
  </div>
</body>
</html>"""

    return f"""<!DOCTYPE html>
<html lang="{e(language)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(hotel_name)} - Voucher</title>
  <style>
    :root {{
      --section-title: {colors['section_title']};
      --footer-bg: {colors['footer_bg']};
      --navy: {colors['navy']};
      --navy-2: {colors['navy_2']};
      --paper: {colors['paper']};
      --panel: {colors['panel']};
      --line: {colors['line']};
      --text: {colors['text']};
      --muted: {colors['muted']};
      --white: {colors['white']};
      --page-bg: {colors['page_bg']};
      --page-border: {colors['border']};
      --header-gradient-end: {colors['header_gradient_end']};
      --hotel-address: {colors['hotel_address']};
      --table-head: {colors['table_head']};
      --table-row: {colors['table_row']};
      --placeholder: {colors['placeholder']};
      --overlay: {colors['overlay']};
      --overlay-border: {colors['overlay_border']};
      --shadow-color: {colors['shadow']};
      --radius-page: {radius['page']};
      --radius-xl: {radius['xl']};
      --radius-lg: {radius['lg']};
      --radius-md: {radius['md']};
      --radius-sm: {radius['sm']};
      --radius-xs: {radius['xs']};
      --page-width: {layout['page_width_px']}px;
      --page-min-height: {layout['page_min_height_px']}px;
      --body-padding: {layout['body_padding']};
      --header-padding: {layout['header_padding']};
      --header-gap: {layout['header_gap']};
      --header-meta-width: {layout['header_meta_width']}px;
      --logo-box-width: {layout['logo_box_width']}px;
      --logo-box-min-height: {layout['logo_box_min_height']}px;
      --brand-logo-height: {layout['brand_logo_height']}px;
      --brand-logo-height-print: {layout['brand_logo_height_print']}px;
      --header-title-size: {layout['header_title_size']};
      --header-title-size-print: {layout['header_title_size_print']};
      --header-subtitle-size: {layout['header_subtitle_size']};
      --header-subtitle-size-print: {layout['header_subtitle_size_print']};
      --top-grid-left: {layout['top_grid_left']};
      --top-grid-right: {layout['top_grid_right']};
      --panel-gap: {layout['panel_gap']};
      --print-page-margin: {layout['print_page_margin']};
      --print-header-padding: {layout['print_header_padding']};
      --print-header-gap: {layout['print_header_gap']};
      --print-header-meta-width: {layout['print_header_meta_width']}px;
      --print-logo-box-width: {layout['print_logo_box_width']}px;
      --print-logo-box-min-height: {layout['print_logo_box_min_height']}px;
      --meta-box-min-height: {layout['meta_box_min_height']}px;
      --meta-box-min-height-print: {layout['meta_box_min_height_print']}px;
      --shadow: 0 12px 32px var(--shadow-color);
      --font-family: {fonts['family']};
    }}
  {voucher_css}
  </style>
</head>
<body>
  <div class="page">
    <header class="header">
      <div class="header-left">
        <div class="voucher-kicker">{e(voucher_kicker)}</div>
        <div class="header-title">{header_title}</div>
        <div class="header-subtitle">{header_subtitle}</div>
      </div>

      <div class="header-meta">
        <div class="meta-box">
          <div class="meta-label">{e(t["conf_number"])}</div>
          <div class="meta-value">{conf_html}</div>
        </div>
      </div>

      <div class="logo-box">
        {header_brand_logo_html}
      </div>
    </header>

    <main class="body">
      <section class="top-grid">
        <section class="panel">
          <div class="section-title">{e(t["hotel_address"])}</div>
          <div class="hotel-card">
            <div>
              <div class="hotel-name text-wrap">{display_or_pending(hotel.get('display_name') or hotel.get('name'), t['empty'])}</div>
              <div class="hotel-address text-wrap">{display_or_pending(hotel.get('address'), t['empty'])}</div>
              <div class="facts">
                <div>
                  <div class="fact-label">{e(t["city"])}</div>
                  <div class="fact-value">{city_html}</div>
                </div>
                <div>
                  <div class="fact-label">{e(t["country"])}</div>
                  <div class="fact-value">{country_html}</div>
                </div>
                <div>
                  <div class="fact-label">{e(t["phone"])}</div>
                  <div class="fact-value">{phone_html}</div>
                </div>
              </div>
            </div>
            <div class="hotel-mini-logo">
              {hotel_logo_html}
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">{e(t["stay_summary"])}</div>
          <div class="summary-grid">
            {summary_tiles(stay, t, language, passengers)}
          </div>
        </section>
      </section>

      <section class="panel">
        <div class="section-title">{e(t["room_details"])}</div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{e(t["rooms"])}</th>
                <th>{e(t["category"])}</th>
                <th>{e(t["additional_info"])}</th>
                <th>{e(t["passengers"])}</th>
              </tr>
            </thead>
            <tbody>
              {room_rows(rooms, t)}
            </tbody>
          </table>
        </div>
      </section>

      {flights_html if render_mode == "full" else ""}

      <section class="panel">
        <div class="section-title">{e(t["passengers"])}</div>
        <div class="passengers-grid">
          {passenger_cards(passengers, t, language)}
        </div>
      </section>

      <div class="footer-note">{e(footer_note)}</div>
    </main>
  </div>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one compact premium HTML voucher per JSON payload.")
    parser.add_argument("input", help="Path to enriched voucher JSON")
    parser.add_argument("-o", "--output-dir", default="rendered_vouchers", help="Output directory")
    parser.add_argument("--profile", default=DEFAULT_PROFILE_KEY, help="Profile key, for example default or mastercard")
    parser.add_argument("--brand-logo", default=None, help="Optional path, URL or data URI for official brand logo")
    parser.add_argument("--debug-logo", action="store_true", help="Print debug info for logo resolution")
    parser.add_argument("--lang", dest="lang", choices=["es", "en", "pt"], help="Override language from UI")
    parser.add_argument(
        "--render-mode",
        choices=["hotel", "flights", "full"],
        default="hotel",
        help="Define qué secciones renderizar: hotel, flights o full",
    )

    args = parser.parse_args()

    profile_config = load_profile(args.profile, BASE_DIR)
    branding = profile_config.get("branding", {}) or {}
    brand_logo = args.brand_logo or branding.get("brand_logo")

    profile_lang = normalize_language(profile_config.get("language"))
    cli_lang = normalize_language(args.lang)
    language = cli_lang or profile_lang or "es"

    print(f"[DEBUG] input_json='{args.input}'")
    print(f"[DEBUG] output_dir='{args.output_dir}'")
    print(f"[DEBUG] BASE_DIR='{BASE_DIR}'")
    print(f"[DEBUG] profile='{args.profile}'")
    print(f"[DEBUG] theme_key='{branding.get('theme_key', DEFAULT_PROFILE_KEY)}'")
    print(f"[DEBUG] profile_language='{profile_lang}'")
    print(f"[DEBUG] cli_language='{cli_lang}'")
    print(f"[DEBUG] resolved_language='{language}'")
    print(f"[DEBUG] brand_logo_arg='{brand_logo}'")
    print("[DEBUG] profile branding:", profile_config["branding"])

    if brand_logo and not str(brand_logo).startswith(("http://", "https://", "data:")):
        resolved_brand_path = (BASE_DIR / brand_logo).resolve()
        print(f"[DEBUG] brand_logo_resolved='{resolved_brand_path}'")
        print(f"[DEBUG] brand_logo_exists={resolved_brand_path.exists()}")
        print(
            f"[DEBUG] brand_logo_is_file="
            f"{resolved_brand_path.is_file() if resolved_brand_path.exists() else False}"
        )

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vouchers = load_json(input_path)

    for idx, voucher_payload in enumerate(vouchers, start=1):
        filename = build_output_filename(voucher_payload, idx)
        html_text = build_html(
            voucher_payload,
            output_dir,
            profile_config=profile_config,
            brand_logo=brand_logo,
            debug=args.debug_logo,
            language_override=language,
            render_mode=args.render_mode,
        )
        (output_dir / filename).write_text(html_text, encoding="utf-8")
        print(f"[DEBUG] wrote_html='{output_dir / filename}'")

    print(f"✔ HTML vouchers generated in: {output_dir}")


if __name__ == "__main__":
    main()
