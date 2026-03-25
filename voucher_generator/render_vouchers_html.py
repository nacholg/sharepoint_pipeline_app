from __future__ import annotations

import argparse
import html
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def make_relative_asset_path(asset_path: str, output_dir: Path) -> str:
    return Path(os.path.relpath(asset_path, start=output_dir)).as_posix()


def hotel_logo_src(hotel: Dict[str, Any], output_dir: Path) -> Optional[str]:
    local_logo_path = hotel.get("local_logo_path")
    if local_logo_path:
        try:
            return make_relative_asset_path(local_logo_path, output_dir)
        except Exception:
            return Path(local_logo_path).as_posix()
    return hotel.get("logo_url")


def passenger_cards(passengers: List[Dict[str, Any]]) -> str:
    cards = []
    for pax in passengers:
        cards.append(
            f"""
            <article class=\"pax-card\">
              <div class=\"pax-name text-wrap\">{e(pax.get('full_name') or 'Passenger')}</div>
              <div class=\"pax-meta-row\"><span class=\"pax-label\">Nationality</span><span class=\"pax-value text-safe\">{display_or_pending(pax.get('nationality'), '-')}</span></div>
              <div class=\"pax-meta-row\"><span class=\"pax-label\">Passport</span><span class=\"pax-value text-safe\">{display_or_pending(pax.get('passport_number'), '-')}</span></div>
              <div class=\"pax-meta-row\"><span class=\"pax-label\">Exp.</span><span class=\"pax-value text-safe\">{display_or_pending(pax.get('passport_expiration'), '-')}</span></div>
            </article>
            """
        )
    return "\n".join(cards) or '<div class="empty-state">No passengers loaded.</div>'


def room_rows(rooms: List[Dict[str, Any]]) -> str:
    rows = []
    for room in rooms:
        rows.append(
            f"""
            <tr>
              <td>{display_or_pending(room.get('room_count'), '-')}</td>
              <td class=\"text-wrap\">{display_or_pending(room.get('room_category'), '-')}</td>
              <td class=\"text-wrap\">{display_or_pending(room.get('additional_info'), '-')}</td>
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
        f'''<div class="summary-tile"><div class="tile-label">{e(label)}</div><div class="tile-value text-wrap">{display_or_pending(value, '-')}</div></div>'''
        for label, value in items
    )


def build_html(voucher_payload: Dict[str, Any], output_dir: Path, brand_logo: Optional[str]) -> str:
    voucher = voucher_payload.get("voucher", {})
    destination = voucher_payload.get("destination", {})
    hotel = voucher_payload.get("hotel", {})
    stay = voucher_payload.get("stay", {})
    rooms = voucher_payload.get("rooms", [])
    passengers = voucher_payload.get("passengers", [])

    brand_logo_html = (
        f'<img class="brand-logo" src="{e(brand_logo)}" alt="Brand logo">'
        if brand_logo
        else '<div class="brand-wordmark">PRICELESS TRAVEL</div>'
    )

    logo_src = hotel_logo_src(hotel, output_dir)
    hotel_logo_html = (
        f'<img class="hotel-logo" src="{e(logo_src)}" alt="Hotel logo">'
        if logo_src
        else '<div class="hotel-logo-placeholder">HOTEL LOGO</div>'
    )

    title_destination = destination.get("display_name") or destination.get("name") or "Destination"
    hotel_name = hotel.get("display_name") or hotel.get("name") or "Hotel"
    hotel_meta = " · ".join(part for part in [hotel.get("city"), hotel.get("country")] if part)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(title_destination)} - {e(hotel_name)}</title>
  <style>
    :root {{
      --navy: #223a69;
      --navy-2: #314b7b;
      --paper: #f5f7fb;
      --panel: #eef2f8;
      --line: #cfd7e6;
      --text: #0e1b3d;
      --muted: #6c7894;
      --white: #ffffff;
      --radius-xl: 22px;
      --radius-lg: 18px;
      --radius-md: 14px;
      --shadow: 0 12px 32px rgba(21, 36, 70, 0.10);
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: Inter, Arial, Helvetica, sans-serif;
      color: var(--text);
      background: #e9edf4;
      padding: 18px;
    }}

    .page {{
      width: 794px;
      min-height: 1123px;
      margin: 0 auto;
      background: var(--paper);
      border: 1px solid #d7deeb;
      border-radius: 28px;
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
      background: linear-gradient(180deg, var(--navy) 0%, #263f70 100%);
      color: var(--white);
      padding: 22px 24px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto 170px;
      gap: 16px;
      align-items: stretch;
    }}

    .header-left {{
      min-width: 0;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}

    .voucher-kicker {{ font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; opacity: 0.78; margin: 8px 0 10px; }}
    .brand-logo {{ max-width: 170px; max-height: 34px; object-fit: contain; display: block; }}
    .brand-wordmark {{ font-size: 14px; font-weight: 700; letter-spacing: 0.18em; }}

    .header-title {{
      font-size: 30px;
      line-height: 1.06;
      font-weight: 800;
      letter-spacing: -0.03em;
      margin: 0 0 6px;
      max-width: 100%;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }}

    .header-subtitle {{
      font-size: 13px;
      line-height: 1.35;
      opacity: 0.88;
      max-width: 100%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .header-meta {{
      display: grid;
      grid-template-columns: repeat(3, 86px);
      gap: 10px;
      align-content: center;
      justify-content: end;
    }}

    .meta-box {{
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 18px;
      padding: 12px 10px;
      min-height: 92px;
      width: 86px;
      overflow: hidden;
    }}

    .meta-label {{
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      opacity: 0.78;
      margin-bottom: 8px;
      line-height: 1.15;
    }}

    .meta-value {{
      font-size: 11px;
      font-weight: 700;
      line-height: 1.15;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      word-break: break-word;
    }}

    .logo-box {{
      width: 170px;
      min-width: 170px;
      background: #ffffff;
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 12px;
      min-height: 92px;
      overflow: hidden;
    }}

    .hotel-logo {{ width: 100%; height: 58px; object-fit: contain; display: block; }}
    .hotel-logo-placeholder {{ color: var(--navy); border: 1px dashed #cad2e2; border-radius: 12px; width: 100%; height: 58px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; }}

    .body {{ padding: 18px; display: grid; gap: 14px; }}

    .top-grid {{ display: grid; grid-template-columns: 1.45fr 1fr; gap: 14px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 20px; padding: 18px; min-width: 0; }}
    .section-title {{ font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; }}

    .hotel-card {{ display: grid; grid-template-columns: minmax(0, 1fr) 150px; gap: 16px; align-items: start; }}
    .hotel-name {{ font-size: 24px; line-height: 1.02; font-weight: 800; letter-spacing: -0.03em; margin: 0 0 10px; overflow-wrap: anywhere; }}
    .hotel-address {{ font-size: 13px; line-height: 1.45; margin-bottom: 14px; color: #233356; overflow-wrap: anywhere; }}
    .hotel-mini-logo {{ border: 1px solid var(--line); border-radius: 16px; background: var(--white); display: flex; align-items: center; justify-content: center; padding: 10px; height: 118px; overflow: hidden; }}
    .hotel-mini-logo .hotel-logo, .hotel-mini-logo .hotel-logo-placeholder {{ height: 44px; }}

    .facts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .fact-label {{ font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }}
    .fact-value {{ font-size: 12.5px; line-height: 1.35; font-weight: 600; overflow-wrap: anywhere; }}

    .summary-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .summary-tile {{ background: var(--white); border: 1px solid var(--line); border-radius: 16px; padding: 12px; min-height: 84px; min-width: 0; overflow: hidden; }}
    .tile-label {{ font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }}
    .tile-value {{ font-size: 17px; line-height: 1.08; font-weight: 800; }}

    .table-wrap {{ overflow: hidden; border-radius: 14px; border: 1px solid var(--line); background: var(--white); }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ padding: 10px 10px; text-align: left; vertical-align: top; border-bottom: 1px solid #e3e8f1; font-size: 12px; line-height: 1.35; overflow-wrap: anywhere; }}
    th {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); background: #f8faff; }}
    tbody tr:last-child td {{ border-bottom: none; }}
    th:nth-child(1), td:nth-child(1) {{ width: 12%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 30%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 40%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 18%; }}

    .passengers-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .pax-card {{ background: var(--white); border: 1px solid var(--line); border-radius: 16px; padding: 12px; min-width: 0; overflow: hidden; }}
    .pax-name {{ font-size: 15px; font-weight: 800; line-height: 1.15; margin-bottom: 10px; min-height: 34px; }}
    .pax-meta-row {{ display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 8px; align-items: start; margin-bottom: 6px; }}
    .pax-meta-row:last-child {{ margin-bottom: 0; }}
    .pax-label {{ font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); padding-top: 2px; }}
    .pax-value {{ font-size: 12px; line-height: 1.35; font-weight: 600; }}

    .footer-note {{ color: var(--muted); font-size: 11px; line-height: 1.45; padding: 2px 2px 0; }}
    .empty-state {{ color: var(--muted); font-size: 12px; }}

    @page {{ size: A4; margin: 8mm; }}

    @media print {{
      body {{ background: #fff; padding: 0; }}
      .page {{ box-shadow: none; border-radius: 0; border: none; width: auto; min-height: auto; }}
      .header {{ grid-template-columns: minmax(0, 1fr) auto 160px; gap: 12px; }}
      .header-meta {{ grid-template-columns: repeat(3, 78px); gap: 8px; }}
      .meta-box {{ width: 78px; padding: 10px 8px; min-height: 86px; }}
      .meta-label {{ font-size: 9px; }}
      .meta-value {{ font-size: 10px; }}
      .logo-box {{ width: 160px; min-width: 160px; }}
      .header-title {{ font-size: 28px; }}
      .panel, .meta-box, .summary-tile, .pax-card, .table-wrap, .logo-box {{ break-inside: avoid; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="header">
      <div class="header-left">
        <div>
          {brand_logo_html}
          <div class="voucher-kicker">Hotel Voucher</div>
          <div class="header-title text-wrap">{e(hotel_name)}</div>
          <div class="header-subtitle">{e(title_destination)}{(' · ' + e(hotel_meta)) if hotel_meta else ''}</div>
        </div>
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
        {hotel_logo_html}
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
    parser.add_argument("--brand-logo", default=None, help="Optional path or URL to official brand logo")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vouchers = load_json(input_path)

    for idx, voucher_payload in enumerate(vouchers, start=1):
        destination = voucher_payload.get("destination", {}).get("display_name") or voucher_payload.get("destination", {}).get("name") or "Destination"
        hotel = voucher_payload.get("hotel", {}).get("display_name") or voucher_payload.get("hotel", {}).get("name") or "Hotel"
        filename = clean_filename(f"{idx:02d}_{destination}_{hotel}.html")
        html_text = build_html(voucher_payload, output_dir, args.brand_logo)
        (output_dir / filename).write_text(html_text, encoding="utf-8")

    print(f"✔ HTML vouchers generated in: {output_dir}")


if __name__ == "__main__":
    main()
