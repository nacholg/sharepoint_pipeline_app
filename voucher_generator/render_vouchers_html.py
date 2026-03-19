from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import os


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


def passenger_cards(passengers: List[Dict[str, Any]]) -> str:
    cards = []
    for pax in passengers:
        cards.append(
            f"""
            <div class=\"pax-card\">
              <div class=\"pax-name\">{e(pax.get('full_name') or 'Passenger')}</div>
              <div class=\"pax-meta\">Nationality: {display_or_pending(pax.get('nationality'), '-')}</div>
              <div class=\"pax-meta\">Passport: {display_or_pending(pax.get('passport_number'), '-')}</div>
              <div class=\"pax-meta\">Passport Exp.: {display_or_pending(pax.get('passport_expiration'), '-')}</div>
            </div>
            """
        )
    return "\n".join(cards)


def room_rows(rooms: List[Dict[str, Any]]) -> str:
    rows = []
    for room in rooms:
        rows.append(
            f"""
            <tr>
              <td>{display_or_pending(room.get('room_count'), '-')}</td>
              <td>{display_or_pending(room.get('room_category'), '-')}</td>
              <td>{display_or_pending(room.get('additional_info'), '-')}</td>
              <td>{display_or_pending(room.get('pax_count'), '-')}</td>
            </tr>
            """
        )
    return "\n".join(rows)


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


def build_html(voucher_payload: Dict[str, Any], output_dir: Path, brand_logo: Optional[str]) -> str:
    voucher = voucher_payload.get("voucher", {})
    destination = voucher_payload.get("destination", {})
    hotel = voucher_payload.get("hotel", {})
    stay = voucher_payload.get("stay", {})
    rooms = voucher_payload.get("rooms", [])
    passengers = voucher_payload.get("passengers", [])

    brand_logo_html = f'<img class="brand-logo" src="{e(brand_logo)}" alt="Brand logo">' if brand_logo else '<div class="brand-wordmark">PRICELESS TRAVEL</div>'

    logo_src = hotel_logo_src(hotel, output_dir)
    hotel_logo_html = (
        f'<img class="hotel-logo" src="{e(logo_src)}" alt="Hotel logo">' if logo_src else '<div class="hotel-logo-placeholder">Hotel</div>'
    )

    hotel_meta = " · ".join(part for part in [hotel.get("city"), hotel.get("country")] if part)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(destination.get('display_name') or 'Voucher')} - {e(hotel.get('display_name') or 'Hotel')}</title>
  <style>
    :root {{
      --bg: #0b0b0f;
      --panel: rgba(255,255,255,0.08);
      --panel-2: rgba(255,255,255,0.05);
      --line: rgba(255,255,255,0.12);
      --text: #f4efe8;
      --muted: #c9b9a3;
      --accent: #ff5f1f;
      --accent-2: #eb001b;
      --shadow: 0 20px 50px rgba(0,0,0,0.35);
      --radius: 28px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Arial, Helvetica, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 85% 20%, rgba(255,95,31,0.20), transparent 25%),
        radial-gradient(circle at 95% 38%, rgba(235,0,27,0.22), transparent 22%),
        linear-gradient(135deg, #130d0c 0%, #090b11 45%, #0b0b0f 100%);
      min-height: 100vh;
      padding: 24px;
    }}
    .page {{
      max-width: 1460px;
      margin: 0 auto;
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 32px;
      overflow: hidden;
      box-shadow: var(--shadow);
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.35fr 0.85fr;
      gap: 36px;
      padding: 40px;
    }}
    .left {{ padding: 8px 8px 8px 24px; }}
    .right {{
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
      border: 1px solid var(--line);
      border-radius: 36px;
      padding: 28px;
      backdrop-filter: blur(10px);
    }}
    .brand-logo {{ max-height: 54px; max-width: 220px; object-fit: contain; }}
    .brand-wordmark {{
      font-size: 20px; letter-spacing: 0.28em; color: var(--text); opacity: 0.95;
    }}
    .eyebrow {{
      margin-top: 72px; display: flex; align-items: center; gap: 18px;
      color: var(--muted); letter-spacing: 0.28em; font-size: 17px; text-transform: uppercase;
    }}
    .eyebrow::before {{ content: ""; width: 52px; height: 2px; background: var(--accent); display: block; }}
    h1 {{ font-size: 92px; line-height: 0.95; letter-spacing: -0.04em; margin: 26px 0 22px; }}
    .lede {{
      max-width: 760px; font-size: 28px; line-height: 1.5; color: rgba(244,239,232,0.82); margin: 0 0 44px;
    }}
    .hotel-name {{ font-size: 36px; font-weight: 700; margin-bottom: 18px; }}
    .hotel-meta {{ color: rgba(244,239,232,0.72); font-size: 20px; margin-bottom: 24px; }}
    .hotel-logo {{ max-height: 74px; max-width: 220px; object-fit: contain; filter: drop-shadow(0 8px 16px rgba(0,0,0,0.25)); }}
    .hotel-logo-placeholder {{
      width: 160px; height: 56px; display: flex; align-items: center; justify-content: center;
      border: 1px dashed rgba(255,255,255,0.24); border-radius: 14px; color: rgba(255,255,255,0.6);
    }}
    .section-title {{ font-size: 16px; letter-spacing: 0.24em; text-transform: uppercase; color: var(--muted); margin-bottom: 20px; }}
    .info-card {{
      border: 1px solid var(--line); border-radius: 24px; padding: 26px 28px; margin-bottom: 22px;
      background: linear-gradient(90deg, rgba(255,255,255,0.05), rgba(255,95,31,0.04));
    }}
    .label {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.22em; color: var(--muted); margin-bottom: 12px; }}
    .value {{ font-size: 26px; font-weight: 700; }}
    .body {{ padding: 0 40px 40px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    .panel {{ border: 1px solid var(--line); border-radius: 28px; padding: 28px; background: var(--panel-2); }}
    .meta-list {{ display: grid; gap: 14px; }}
    .meta-item {{ color: rgba(244,239,232,0.8); font-size: 18px; line-height: 1.5; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 16px 12px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }}
    th {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.16em; font-size: 12px; }}
    .passengers-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .pax-card {{ border: 1px solid var(--line); border-radius: 22px; padding: 22px; background: var(--panel); }}
    .pax-name {{ font-size: 24px; font-weight: 700; margin-bottom: 10px; }}
    .pax-meta {{ color: rgba(244,239,232,0.75); font-size: 16px; margin-bottom: 6px; }}
    .footer-note {{ margin-top: 20px; color: rgba(244,239,232,0.55); font-size: 14px; }}
    @media (max-width: 1100px) {{
      .hero, .grid, .passengers-grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 64px; }}
      .lede {{ font-size: 22px; }}
    }}
    @media print {{
      body {{ padding: 0; background: #111; }}
      .page {{ border-radius: 0; box-shadow: none; }}
      .hero {{ break-inside: avoid;}}
      .panel {{ break-inside: avoid;}}
      .pax_card {{ break-inside: avoid;}}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="left">
        {brand_logo_html}
        <div class="eyebrow">Travel Voucher</div>
        <h1>{e(destination.get('display_name') or 'Destination')}</h1>
        <p class="lede">Curated travel details prepared for a premium guest experience. Present this voucher at check-in together with valid passenger documentation.</p>
        <div class="hotel-name">{display_or_pending(hotel.get('display_name'))}</div>
        <div class="hotel-meta">{e(hotel_meta)}</div>
        {hotel_logo_html}
      </div>
      <aside class="right">
        <div class="section-title">Voucher Information</div>
        <div class="info-card"><div class="label">Confirmation</div><div class="value">{display_or_pending(voucher.get('confirmation_number'))}</div></div>
        <div class="info-card"><div class="label">Issue Date</div><div class="value">{display_or_pending(voucher.get('issue_date'))}</div></div>
        <div class="info-card"><div class="label">Voucher Code</div><div class="value">{display_or_pending(voucher.get('voucher_code'))}</div></div>
      </aside>
    </section>

    <div class="body">
      <div class="grid">
        <section class="panel">
          <div class="section-title">Hotel Details</div>
          <div class="meta-list">
            <div class="meta-item"><strong>Address:</strong> {display_or_pending(hotel.get('address'), '-')}</div>
            <div class="meta-item"><strong>City:</strong> {display_or_pending(hotel.get('city'), '-')}</div>
            <div class="meta-item"><strong>Country:</strong> {display_or_pending(hotel.get('country'), '-')}</div>
            <div class="meta-item"><strong>Phone:</strong> {display_or_pending(hotel.get('phone'), '-')}</div>
          </div>
        </section>
        <section class="panel">
          <div class="section-title">Stay Details</div>
          <div class="meta-list">
            <div class="meta-item"><strong>Check-in:</strong> {display_or_pending(stay.get('check_in'), '-')}</div>
            <div class="meta-item"><strong>Check-out:</strong> {display_or_pending(stay.get('check_out'), '-')}</div>
            <div class="meta-item"><strong>Nights:</strong> {display_or_pending(stay.get('nights'), '-')}</div>
          </div>
        </section>
      </div>

      <section class="panel" style="margin-top:24px;">
        <div class="section-title">Room Details</div>
        <table>
          <thead>
            <tr><th>Rooms</th><th>Category</th><th>Additional Info</th><th>Passengers</th></tr>
          </thead>
          <tbody>
            {room_rows(rooms)}
          </tbody>
        </table>
      </section>

      <section class="panel" style="margin-top:24px;">
        <div class="section-title">Passengers</div>
        <div class="passengers-grid">
          {passenger_cards(passengers)}
        </div>
      </section>

      <div class="footer-note">Issued for travel operations. Use official brand artwork as provided by your organization and keep hotel data under review before final dispatch.</div>
    </div>
  </div>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one premium HTML voucher per JSON payload.")
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