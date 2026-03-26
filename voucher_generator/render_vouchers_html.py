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
from importlib import import_module

from voucher_generator.themes.theme_registry import get_theme_config



BASE_DIR = Path(__file__).resolve().parent


DEFAULT_PROFILE_KEY = "default"
PROFILE_MODULES = {
    "default": "profiles.default_profile",
    "mastercard": "profiles.mastercard_profile",
}


def clean_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value[:120] or "voucher"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def e(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def display_or_pending(value: Any, pending: str = "Pending") -> str:
    return e(value) if value not in (None, "") else pending


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


def resolve_logo_src(value: Optional[str], output_dir: Path, debug: bool = False, label: str = "logo") -> Optional[str]:
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
        print(f"[DEBUG] {label}: exists={candidate.exists()} is_file={candidate.is_file() if candidate.exists() else False}")

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
    return resolve_logo_src(
        hotel.get("local_logo_path") or hotel.get("logo_url"),
        output_dir=output_dir,
        debug=debug,
        label="hotel_logo",
    )


def load_profile_config(profile_name: str | None) -> dict:
    profile_key = (profile_name or "default").strip().lower()
    module_name = f"voucher_generator.profiles.{profile_key}_profile"

    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if profile_key != "default":
            module = import_module("voucher_generator.profiles.default_profile")
        else:
            raise exc

    return getattr(module, "PROFILE_CONFIG")

def passenger_cards(passengers: List[Dict[str, Any]]) -> str:
    cards: List[str] = []
    for pax in passengers:
        cards.append(
            f"""
            <article class="pax-card">
              <div class="pax-name">{e(pax.get('full_name') or 'Passenger')}</div>
              <div class="pax-meta-row"><span class="pax-label">Nationality</span><span class="pax-value text-safe">{display_or_pending(pax.get('nationality'), '-')}</span></div>
              <div class="pax-meta-row"><span class="pax-label">Passport</span><span class="pax-value text-safe">{display_or_pending(pax.get('passport_number'), '-')}</span></div>
              <div class="pax-meta-row"><span class="pax-label">Exp.</span><span class="pax-value text-safe">{display_or_pending(pax.get('passport_expiration'), '-')}</span></div>
            </article>
            """
        )
    return "\n".join(cards) or '<div class="empty-state">No passengers loaded.</div>'


def room_rows(rooms: List[Dict[str, Any]]) -> str:
    rows: List[str] = []
    for room in rooms:
        rows.append(
            f"""
            <tr>
              <td>{display_or_pending(room.get('room_count'), '-')}</td>
              <td class="text-wrap">{display_or_pending(room.get('room_category'), '-')}</td>
              <td class="text-wrap">{display_or_pending(room.get('additional_info'), '-')}</td>
              <td>{display_or_pending(room.get('pax_count'), '-')}</td>
            </tr>
            """
        )
    return "\n".join(rows) or '<tr><td colspan="4">No rooming details available.</td></tr>'


def summary_tiles(stay: Dict[str, Any]) -> str:
    items = [
        ("Check-in", stay.get("check_in")),
        ("Check-out", stay.get("check_out")),
        ("Nights", stay.get("nights")),
        ("Meals", stay.get("meal_plan") or stay.get("meals")),
    ]
    return "\n".join(
        f'<div class="summary-tile"><div class="tile-label">{e(label)}</div><div class="tile-value text-wrap">{display_or_pending(value, "-")}</div></div>'
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
) -> str:
    voucher = voucher_payload.get("voucher", {})
    destination = voucher_payload.get("destination", {})
    hotel = voucher_payload.get("hotel", {})
    stay = voucher_payload.get("stay", {})
    rooms = voucher_payload.get("rooms", [])
    passengers = voucher_payload.get("passengers", [])

    branding = profile_config.get("branding", {})
    theme_key = branding.get("theme_key") or DEFAULT_PROFILE_KEY
    theme = get_theme_config(theme_key)
    colors = theme["colors"]
    fonts = theme["fonts"]
    radius = theme["radius"]
    layout = theme["layout"]

    brand_logo_src = resolve_logo_src(
        brand_logo or branding.get("brand_logo"),
        output_dir=output_dir,
        debug=debug,
        label="brand_logo",
    )
    header_brand_logo_html = (
        f'<img class="brand-box-logo" src="{e(brand_logo_src)}" alt="Brand logo">'
        if brand_logo_src
        else '<div class="brand-box-placeholder">BRAND LOGO</div>'
    )

    hotel_src = hotel_logo_src(hotel, output_dir, debug=debug)
    hotel_logo_html = (
        f'<img class="hotel-logo" src="{e(hotel_src)}" alt="Hotel logo">'
        if hotel_src
        else '<div class="hotel-logo-placeholder">HOTEL LOGO</div>'
    )

    hotel_name = hotel.get("display_name") or hotel.get("name") or "Hotel"
    subtitle_parts = [
        rooms[0].get("room_category") if rooms else None,
        hotel.get("city"),
        hotel.get("country"),
    ]
    hotel_meta = " · ".join(str(part) for part in subtitle_parts if part)

    return f"""<!DOCTYPE html>
<html lang="en">
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

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-family);
      color: var(--text);
      background: var(--page-bg);
      padding: 18px;
    }}

    .page {{
      width: var(--page-width);
      min-height: var(--page-min-height);
      margin: 0 auto;
      background: var(--paper);
      border: 1px solid var(--page-border);
      border-radius: var(--radius-page);
      overflow: hidden;
      box-shadow: var(--shadow);
    }}

    .text-safe {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
      display: block;
    }}

    .text-wrap {{
      overflow-wrap: anywhere;
      word-break: break-word;
      min-width: 0;
    }}

    .header {{
      background: linear-gradient(90deg, var(--navy) 0%, var(--header-gradient-end) 100%);
      color: var(--white);
      padding: var(--header-padding);
      display: grid;
      grid-template-columns: minmax(0, 1fr) var(--header-meta-width) var(--logo-box-width);
      gap: var(--header-gap);
      align-items: stretch;
    }}

    .header-left {{
      min-width: 0;
      display: flex;
      flex-direction: column;
      justify-content: center;
      overflow: hidden;
    }}

    .voucher-kicker {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      opacity: 0.78;
      margin-bottom: 14px;
    }}

    .header-title {{
      font-size: var(--header-title-size);
      line-height: 1.06;
      font-weight: 800;
      letter-spacing: -0.03em;
      margin: 0 0 10px;
      max-width: 100%;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      word-break: break-word;
    }}

    .header-subtitle {{
      font-size: var(--header-subtitle-size);
      line-height: 1.35;
      opacity: 0.90;
      max-width: 100%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .header-meta {{
      width: var(--header-meta-width);
      min-width: var(--header-meta-width);
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      align-content: stretch;
    }}

    .meta-box {{
      background: var(--overlay);
      border: 1px solid var(--overlay-border);
      border-radius: var(--radius-md);
      padding: 12px 10px;
      min-height: var(--meta-box-min-height);
      min-width: 0;
      overflow: hidden;
    }}

    .meta-label {{
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      opacity: 0.82;
      margin-bottom: 8px;
    }}

    .meta-value {{
      font-size: 11px;
      font-weight: 700;
      line-height: 1.16;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      word-break: break-word;
    }}

    .logo-box {{
      width: var(--logo-box-width);
      min-width: var(--logo-box-width);
      background: var(--white);
      border-radius: var(--radius-lg);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 12px;
      min-height: var(--logo-box-min-height);
      overflow: hidden;
    }}

    .brand-box-logo {{
      width: 100%;
      height: var(--brand-logo-height);
      object-fit: contain;
      display: block;
    }}

    .brand-box-placeholder {{
      color: var(--navy);
      border: 1px dashed var(--placeholder);
      border-radius: 12px;
      width: 100%;
      height: var(--brand-logo-height);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
    }}

    .hotel-logo {{ width: 100%; height: 58px; object-fit: contain; display: block; }}
    .hotel-logo-placeholder {{ color: var(--navy); border: 1px dashed var(--placeholder); border-radius: 12px; width: 100%; height: 58px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; }}

    .body {{ padding: var(--body-padding); display: grid; gap: var(--panel-gap); }}

    .top-grid {{ display: grid; grid-template-columns: var(--top-grid-left) var(--top-grid-right); gap: var(--panel-gap); }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: 18px; min-width: 0; }}
    .section-title {{ font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--section-title); margin-bottom: 10px; font-weight: 700; }}

    .hotel-card {{ display: grid; grid-template-columns: minmax(0, 1fr) 150px; gap: 16px; align-items: start; }}
    .hotel-name {{ font-size: 24px; line-height: 1.02; font-weight: 800; letter-spacing: -0.03em; margin: 0 0 10px; overflow-wrap: anywhere; }}
    .hotel-address {{ font-size: 13px; line-height: 1.45; margin-bottom: 14px; color: var(--hotel-address); overflow-wrap: anywhere; }}
    .hotel-mini-logo {{ border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--white); display: flex; align-items: center; justify-content: center; padding: 10px; height: 118px; overflow: hidden; }}
    .hotel-mini-logo .hotel-logo, .hotel-mini-logo .hotel-logo-placeholder {{ height: 44px; }}

    .facts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .fact-label {{ font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }}
    .fact-value {{ font-size: 12.5px; line-height: 1.35; font-weight: 600; overflow-wrap: anywhere; }}

    .summary-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .summary-tile {{ background: var(--white); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; min-height: 84px; overflow: hidden; }}
    .tile-label {{ font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }}
    .tile-value {{ font-size: 17px; line-height: 1.08; font-weight: 800; }}

    .table-wrap {{ overflow: hidden; border-radius: var(--radius-xs); border: 1px solid var(--line); background: var(--white); }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ padding: 10px 10px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--table-row); font-size: 12px; line-height: 1.35; overflow-wrap: anywhere; }}
    th {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); background: var(--table-head); }}
    tbody tr:last-child td {{ border-bottom: none; }}
    th:nth-child(1), td:nth-child(1) {{ width: 12%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 30%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 40%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 18%; }}

    .passengers-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .pax-card {{ background: var(--white); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; min-width: 0; overflow: hidden; }}
    .pax-name {{ font-size: 15px; font-weight: 800; line-height: 1.15; margin-bottom: 10px; min-height: 34px; overflow-wrap: anywhere; }}
    .pax-meta-row {{ display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 8px; align-items: start; margin-bottom: 6px; }}
    .pax-meta-row:last-child {{ margin-bottom: 0; }}
    .pax-label {{ font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); padding-top: 2px; }}
    .pax-value {{ font-size: 12px; line-height: 1.35; font-weight: 600; }}

    .footer-note {{color: var(--hotel-address); background: var(--footer-bg); border: 1px solid var(--line); border-radius: var(--radius-md); font-size: 11px; line-height: 1.55; padding: 14px 16px; margin-top: 4px;}}
    .empty-state {{ color: var(--muted); font-size: 12px; }}

    @page {{ size: A4; margin: var(--print-page-margin); }}

    @media print {{
      body {{ background: #fff; padding: 0; }}
      .page {{ box-shadow: none; border-radius: 0; border: none; width: auto; min-height: auto; }}
      .header {{ grid-template-columns: minmax(0, 1fr) var(--print-header-meta-width) var(--print-logo-box-width); gap: var(--print-header-gap); padding: var(--print-header-padding); }}
      .header-meta {{ width: var(--print-header-meta-width); min-width: var(--print-header-meta-width); gap: 6px; }}
      .meta-box {{ min-height: var(--meta-box-min-height-print); padding: 10px 8px; border-radius: var(--radius-sm); }}
      .meta-label {{ font-size: 9px; }}
      .meta-value {{ font-size: 10px; }}
      .logo-box {{ width: var(--print-logo-box-width); min-width: var(--print-logo-box-width); min-height: var(--print-logo-box-min-height); }}
      .brand-box-logo, .brand-box-placeholder {{ height: var(--brand-logo-height-print); }}
      .header-title {{ font-size: var(--header-title-size-print); }}
      .header-subtitle {{ font-size: var(--header-subtitle-size-print); }}
      .panel, .meta-box, .summary-tile, .pax-card, .table-wrap, .logo-box {{ break-inside: avoid; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="header">
      <div class="header-left">
        <div class="voucher-kicker">Hotel Voucher</div>
        <div class="header-title">{e(hotel_name)}</div>
        <div class="header-subtitle">{e(hotel_meta)}</div>
      </div>

      <div class="header-meta">
        <div class="meta-box">
          <div class="meta-label">Conf. nbr.</div>
          <div class="meta-value">{display_or_pending(voucher.get('confirmation_number'))}</div>
        </div>
        <div class="meta-box">
          <div class="meta-label">Date</div>
          <div class="meta-value">{display_or_pending(voucher.get('issue_date'))}</div>
        </div>
        <div class="meta-box">
          <div class="meta-label">Voucher code</div>
          <div class="meta-value">{display_or_pending(voucher.get('voucher_code'))}</div>
        </div>
      </div>

      <div class="logo-box">
        {header_brand_logo_html}
      </div>
    </header>

    <main class="body">
      <section class="top-grid">
        <section class="panel">
          <div class="section-title">Hotel / Address</div>
          <div class="hotel-card">
            <div>
              <div class="hotel-name text-wrap">{display_or_pending(hotel.get('display_name') or hotel.get('name'))}</div>
              <div class="hotel-address text-wrap">{display_or_pending(hotel.get('address'), '-')}</div>
              <div class="facts">
                <div>
                  <div class="fact-label">City</div>
                  <div class="fact-value text-wrap">{display_or_pending(hotel.get('city'), '-')}</div>
                </div>
                <div>
                  <div class="fact-label">Country</div>
                  <div class="fact-value text-wrap">{display_or_pending(hotel.get('country'), '-')}</div>
                </div>
                <div>
                  <div class="fact-label">Phone</div>
                  <div class="fact-value text-wrap">{display_or_pending(hotel.get('phone'), '-')}</div>
                </div>
              </div>
            </div>
            <div class="hotel-mini-logo">
              {hotel_logo_html}
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">Stay Summary</div>
          <div class="summary-grid">
            {summary_tiles(stay)}
          </div>
        </section>
      </section>

      <section class="panel">
        <div class="section-title">Room Details</div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rooms</th>
                <th>Category</th>
                <th>Additional info</th>
                <th>Passengers</th>
              </tr>
            </thead>
            <tbody>
              {room_rows(rooms)}
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <div class="section-title">Passengers</div>
        <div class="passengers-grid">
          {passenger_cards(passengers)}
        </div>
      </section>

      <div class="footer-note">Issued for travel operations. Please verify passenger documentation, rooming, and hotel details before dispatching the final voucher.</div>
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
    args = parser.parse_args()

    profile_config = load_profile_config(args.profile)
    branding = profile_config.get("branding", {})
    brand_logo = args.brand_logo or branding.get("brand_logo") or "assets/logos/GEOBYPATAGONIK.png"

    print(f"[DEBUG] input_json='{args.input}'")
    print(f"[DEBUG] output_dir='{args.output_dir}'")
    print(f"[DEBUG] BASE_DIR='{BASE_DIR}'")
    print(f"[DEBUG] profile='{args.profile}'")
    print(f"[DEBUG] theme_key='{branding.get('theme_key', DEFAULT_PROFILE_KEY)}'")
    print(f"[DEBUG] brand_logo_arg='{brand_logo}'")

    if not str(brand_logo).startswith(("http://", "https://", "data:")):
        resolved_brand_path = (BASE_DIR / brand_logo).resolve()
        print(f"[DEBUG] brand_logo_resolved='{resolved_brand_path}'")
        print(f"[DEBUG] brand_logo_exists={resolved_brand_path.exists()}")
        print(f"[DEBUG] brand_logo_is_file={resolved_brand_path.is_file() if resolved_brand_path.exists() else False}")

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
        )
        (output_dir / filename).write_text(html_text, encoding="utf-8")
        print(f"[DEBUG] wrote_html='{output_dir / filename}'")

    print(f"✔ HTML vouchers generated in: {output_dir}")


if __name__ == "__main__":
    main()
