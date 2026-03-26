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


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BRAND_LOGO = "assets/logos/GEOBYPATAGONIK.png"


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
    return resolve_logo_src(
        hotel.get("local_logo_path") or hotel.get("logo_url"),
        output_dir=output_dir,
        debug=debug,
        label="hotel_logo",
    )


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
    brand_logo: Optional[str],
    theme_key: str = "default",
    debug: bool = False,
) -> str:
    voucher = voucher_payload.get("voucher", {})
    destination = voucher_payload.get("destination", {})
    hotel = voucher_payload.get("hotel", {})
    stay = voucher_payload.get("stay", {})
    rooms = voucher_payload.get("rooms", [])
    passengers = voucher_payload.get("passengers", [])

    theme_key = theme_key or "default"

    brand_logo_src = resolve_logo_src(
        brand_logo,
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

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(hotel_name)} - Voucher</title>
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
      --header-grad-1: #223a69;
      --header-grad-2: #314b7b;
      --accent: #223a69;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: Inter, Arial, Helvetica, sans-serif;
      color: var(--text);
      background: #e9edf4;
      padding: 18px;
    }}

    body.theme-mastercard {{
      --paper: #fcfbfa;
      --panel: #f6f3f1;
      --line: #eadfd9;
      --text: #241c1a;
      --muted: #7b6963;
      --header-grad-1: #EB001B;
      --header-grad-2: #F79E1B;
      --accent: #EB001B;
      --shadow: 0 12px 32px rgba(111, 41, 23, 0.12);
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
      display: grid;
      grid-template-columns: minmax(0, 1fr) 246px 170px;
      gap: 14px;
      align-items: stretch;
      padding: 22px 22px 18px;
      background: linear-gradient(135deg, var(--header-grad-1), var(--header-grad-2));
      color: #fff;
    }}

    .header-left {{
      min-width: 0;
      display: grid;
      align-content: center;
      gap: 8px;
    }}

    .voucher-kicker {{
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      opacity: 0.82;
    }}

    .header-title {{
      font-size: 34px;
      line-height: 1.02;
      font-weight: 900;
      letter-spacing: -0.02em;
      overflow-wrap: anywhere;
    }}

    .header-subtitle {{
      font-size: 13px;
      line-height: 1.35;
      opacity: 0.90;
      max-width: 100%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .header-meta {{
      width: 246px;
      min-width: 246px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      align-content: stretch;
    }}

    .meta-box {{
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 18px;
      padding: 12px 10px;
      min-height: 98px;
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
      width: 170px;
      min-width: 170px;
      background: #ffffff;
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 12px;
      min-height: 98px;
      overflow: hidden;
    }}

    .brand-box-logo {{
      width: 100%;
      height: 64px;
      object-fit: contain;
      display: block;
    }}

    .brand-box-placeholder {{
      color: var(--accent);
      border: 1px dashed #cad2e2;
      border-radius: 12px;
      width: 100%;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
    }}

    .hotel-logo {{
      width: 100%;
      height: 58px;
      object-fit: contain;
      display: block;
    }}

    .hotel-logo-placeholder {{
      color: var(--accent);
      border: 1px dashed #cad2e2;
      border-radius: 12px;
      width: 100%;
      height: 58px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
    }}

    .body {{
      padding: 18px;
      display: grid;
      gap: 14px;
    }}

    .top-grid {{
      display: grid;
      grid-template-columns: 1.45fr 1fr;
      gap: 14px;
    }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      min-width: 0;
    }}

    .section-title {{
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }}

    .hotel-card {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 124px;
      gap: 14px;
      align-items: center;
      min-width: 0;
    }}

    .hotel-name {{
      font-size: 22px;
      line-height: 1.04;
      font-weight: 900;
      margin-bottom: 8px;
    }}

    .hotel-address {{
      font-size: 13px;
      line-height: 1.45;
      color: var(--muted);
      margin-bottom: 12px;
    }}

    .facts {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}

    .fact-label {{
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 4px;
    }}

    .fact-value {{
      font-size: 13px;
      font-weight: 700;
      line-height: 1.3;
    }}

    .hotel-mini-logo {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 10px;
      min-height: 84px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}

    .summary-tile {{
      background: var(--white);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      min-height: 84px;
      overflow: hidden;
    }}

    .tile-label {{
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
    }}

    .tile-value {{
      font-size: 17px;
      line-height: 1.08;
      font-weight: 800;
    }}

    .table-wrap {{
      overflow: hidden;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: var(--white);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}

    th, td {{
      padding: 10px 10px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid #e3e8f1;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}

    th {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      background: #f8faff;
    }}

    body.theme-mastercard th {{
      background: #fff5ef;
    }}

    tbody tr:last-child td {{
      border-bottom: none;
    }}

    th:nth-child(1), td:nth-child(1) {{ width: 12%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 30%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 40%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 18%; }}

    .passengers-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}

    .pax-card {{
      background: var(--white);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      min-width: 0;
      overflow: hidden;
    }}

    .pax-name {{
      font-size: 15px;
      font-weight: 800;
      line-height: 1.15;
      margin-bottom: 10px;
      min-height: 34px;
      overflow-wrap: anywhere;
    }}

    .pax-meta-row {{
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      margin-bottom: 6px;
    }}

    .pax-meta-row:last-child {{
      margin-bottom: 0;
    }}

    .pax-label {{
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      padding-top: 2px;
    }}

    .pax-value {{
      font-size: 12px;
      line-height: 1.35;
      font-weight: 600;
    }}

    .footer-note {{
      color: var(--muted);
      font-size: 11px;
      line-height: 1.45;
      padding: 2px 2px 0;
    }}

    .empty-state {{
      color: var(--muted);
      font-size: 12px;
    }}

    @page {{ size: A4; margin: 8mm; }}

    @media print {{
      body {{ background: #fff; padding: 0; }}
      .page {{ box-shadow: none; border-radius: 0; border: none; width: auto; min-height: auto; }}
      .header {{ grid-template-columns: minmax(0, 1fr) 234px 156px; gap: 12px; padding: 18px 20px; }}
      .header-meta {{ width: 234px; min-width: 234px; gap: 6px; }}
      .meta-box {{ min-height: 90px; padding: 10px 8px; border-radius: 16px; }}
      .meta-label {{ font-size: 9px; }}
      .meta-value {{ font-size: 10px; }}
      .logo-box {{ width: 156px; min-width: 156px; min-height: 90px; }}
      .brand-box-logo, .brand-box-placeholder {{ height: 54px; }}
      .header-title {{ font-size: 28px; }}
      .header-subtitle {{ font-size: 12px; }}
      .panel, .meta-box, .summary-tile, .pax-card, .table-wrap, .logo-box {{ break-inside: avoid; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body class="theme-{e(theme_key)}">
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
    return html_doc


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one compact premium HTML voucher per JSON payload.")
    parser.add_argument("input", help="Path to enriched voucher JSON")
    parser.add_argument("-o", "--output-dir", default="rendered_vouchers", help="Output directory")
    parser.add_argument("--brand-logo", default=None, help="Optional path, URL or data URI for official brand logo")
    parser.add_argument("--theme-key", default="default", help="Theme key for styling")
    parser.add_argument("--debug-logo", action="store_true", help="Print debug info for logo resolution")
    args = parser.parse_args()

    args.brand_logo = args.brand_logo or DEFAULT_BRAND_LOGO

    print(f"[DEBUG] input_json='{args.input}'")
    print(f"[DEBUG] output_dir='{args.output_dir}'")
    print(f"[DEBUG] BASE_DIR='{BASE_DIR}'")
    print(f"[DEBUG] brand_logo_arg='{args.brand_logo}'")
    print(f"[DEBUG] theme_key='{args.theme_key}'")

    if not str(args.brand_logo).startswith(("http://", "https://", "data:")):
        resolved_brand_path = (BASE_DIR / args.brand_logo).resolve()
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
            voucher_payload=voucher_payload,
            output_dir=output_dir,
            brand_logo=args.brand_logo,
            theme_key=args.theme_key,
            debug=args.debug_logo,
        )
        (output_dir / filename).write_text(html_text, encoding="utf-8")
        print(f"[DEBUG] wrote_html='{output_dir / filename}'")

    print(f"✔ HTML vouchers generated in: {output_dir}")


if __name__ == "__main__":
    main()