from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from openpyxl import load_workbook

# Expected layout based on the updated spreadsheet.
# Row 3 contains headers. Data starts on row 4.
COL = {
    "row_number": 1,
    "group_label": 6,   # referencia operativa interna
    "last_name": 7,
    "first_name": 8,
    "mail": 9,
    "phone": 11,
    "nationality": 12,
    "date_of_birth": 14,
    "passport_number": 15,
    "passport_expiration": 16,
    "remarks": 18,
    "food_restrictions": 19,
    "qty": 36,
    "destination": 37,  # destino a mostrar en el voucher
    "hotel_name": 38,
    "room": 39,
    "check_in": 40,
    "check_out": 41,
    "nights": 42,
}


# -------- Normalization helpers --------
def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if text in {"", "-", "--", "N/A", "n/a"}:
        return None
    return text


def normalize_display_text(value: Any) -> Optional[str]:
    return clean_text(value)


def normalize_key_text(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return text.upper()


def normalize_email(value: Any) -> Optional[str]:
    text = clean_text(value)
    return text.lower() if text else None


def normalize_phone(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if int(value) == value:
            return str(int(value))
    return clean_text(value)


def normalize_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def normalize_date(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, (int, float)):
        try:
            serial = float(value)
            if 1 <= serial <= 60000:
                excel_epoch = datetime(1899, 12, 30)
                parsed = excel_epoch + timedelta(days=serial)
                return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass

    text = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return text


def to_title_case(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return text.title()


def build_passenger_key(
    passport_number: Optional[str],
    last_name: Optional[str],
    first_name: Optional[str],
    date_of_birth: Optional[str],
) -> str:
    passport = normalize_key_text(passport_number)
    if passport:
        return passport

    return "|".join(
        [
            normalize_key_text(last_name) or "NO-LASTNAME",
            normalize_key_text(first_name) or "NO-FIRSTNAME",
            normalize_date(date_of_birth) or "NO-DOB",
        ]
    )


def build_voucher_group_key(
    destination: Optional[str],
    hotel_name: Optional[str],
    room: Optional[str],
    check_in: Optional[str],
    check_out: Optional[str],
) -> str:
    return "|".join(
        [
            normalize_key_text(destination) or "NO-DESTINATION",
            normalize_key_text(hotel_name) or "NO-HOTEL",
            normalize_date(check_in) or "NO-CHECKIN",
            normalize_date(check_out) or "NO-CHECKOUT",
            normalize_key_text(room) or "NO-ROOM",
        ]
    )


# -------- Row extraction / forward fill --------
def read_effective_rows(xlsx_path: Path, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb[wb.sheetnames[0]]

    rows: List[Dict[str, Any]] = []
    last_values = {
        "group_label": None,
        "destination": None,
        "hotel_name": None,
        "room": None,
        "check_in": None,
        "check_out": None,
        "nights": None,
        "qty": None,
    }

    for excel_row in range(4, ws.max_row + 1):
        first_name_raw = ws.cell(excel_row, COL["first_name"]).value
        last_name_raw = ws.cell(excel_row, COL["last_name"]).value
        destination_raw = ws.cell(excel_row, COL["destination"]).value
        hotel_name_raw = ws.cell(excel_row, COL["hotel_name"]).value
        room_raw = ws.cell(excel_row, COL["room"]).value
        check_in_raw = ws.cell(excel_row, COL["check_in"]).value
        check_out_raw = ws.cell(excel_row, COL["check_out"]).value

        # Skip fully blank trailing rows.
        if all(
            v in (None, "")
            for v in [
                first_name_raw,
                last_name_raw,
                destination_raw,
                hotel_name_raw,
                room_raw,
                check_in_raw,
                check_out_raw,
            ]
        ):
            continue

        current_group_label_raw = clean_text(ws.cell(excel_row, COL["group_label"]).value)
        current_destination_raw = clean_text(ws.cell(excel_row, COL["destination"]).value)

        # Si aparece un destination explícito nuevo, reiniciar todo el contexto del voucher
        if current_destination_raw:
            if normalize_key_text(current_destination_raw) != normalize_key_text(last_values["destination"]):
                last_values = {
                    "group_label": None,
                    "destination": None,
                    "hotel_name": None,
                    "room": None,
                    "check_in": None,
                    "check_out": None,
                    "nights": None,
                    "qty": None,
                }

        group_label = current_group_label_raw if current_group_label_raw else last_values["group_label"]
        destination = current_destination_raw if current_destination_raw else last_values["destination"]
        hotel_name = clean_text(hotel_name_raw) if clean_text(hotel_name_raw) else last_values["hotel_name"]
        room = clean_text(room_raw) if clean_text(room_raw) else last_values["room"]
        check_in = normalize_date(check_in_raw) if normalize_date(check_in_raw) else last_values["check_in"]
        check_out = normalize_date(check_out_raw) if normalize_date(check_out_raw) else last_values["check_out"]
        nights = normalize_int(ws.cell(excel_row, COL["nights"]).value) if normalize_int(ws.cell(excel_row, COL["nights"]).value) is not None else last_values["nights"]
        qty = normalize_int(ws.cell(excel_row, COL["qty"]).value) if normalize_int(ws.cell(excel_row, COL["qty"]).value) is not None else last_values["qty"]

        print({
            "excel_row": excel_row,
            "group_label_raw": ws.cell(excel_row, COL["group_label"]).value,
            "destination_raw": ws.cell(excel_row, COL["destination"]).value,
            "hotel_name_raw": ws.cell(excel_row, COL["hotel_name"]).value,
        })

        last_values.update(
            {
                "group_label": group_label,
                "destination": destination,
                "hotel_name": hotel_name,
                "room": room,
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "qty": qty,
            }
        )

        first_name = clean_text(first_name_raw)
        last_name = clean_text(last_name_raw)

        if not first_name and not last_name:
            continue

        date_of_birth = normalize_date(ws.cell(excel_row, COL["date_of_birth"]).value)
        passport_number = clean_text(ws.cell(excel_row, COL["passport_number"]).value)
        passenger_key = build_passenger_key(passport_number, last_name, first_name, date_of_birth)
        voucher_group_key = build_voucher_group_key(destination, hotel_name, room, check_in, check_out)

        rows.append(
            {
                "excel_row_number": excel_row,
                "source_row_number": normalize_int(ws.cell(excel_row, COL["row_number"]).value),
                "group_label": group_label,
                "destination": destination,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": " ".join([p for p in [first_name, last_name] if p]),
                "mail": normalize_email(ws.cell(excel_row, COL["mail"]).value),
                "phone": normalize_phone(ws.cell(excel_row, COL["phone"]).value),
                "nationality": clean_text(ws.cell(excel_row, COL["nationality"]).value),
                "date_of_birth": date_of_birth,
                "passport_number": passport_number,
                "passport_expiration": normalize_date(ws.cell(excel_row, COL["passport_expiration"]).value),
                "remarks": clean_text(ws.cell(excel_row, COL["remarks"]).value),
                "food_restrictions": clean_text(ws.cell(excel_row, COL["food_restrictions"]).value),
                "hotel_name": hotel_name,
                "room": room,
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "qty": qty,
                "passenger_key": passenger_key,
                "voucher_group_key": voucher_group_key,
            }
        )

    return rows


# -------- Grouping / payload generation --------
def dedupe_passengers(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    passengers: List[Dict[str, Any]] = []

    for row in rows:
        passenger_key = row["passenger_key"]
        if passenger_key in seen:
            continue
        seen.add(passenger_key)

        passengers.append(
            {
                "passenger_key": passenger_key,
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "full_name": row["full_name"],
                "mail": row["mail"],
                "phone": row["phone"],
                "nationality": row["nationality"],
                "date_of_birth": row["date_of_birth"],
                "passport_number": row["passport_number"],
                "passport_expiration": row["passport_expiration"],
                "food_restrictions": row["food_restrictions"],
                "remarks": row["remarks"],
            }
        )

    return passengers


def build_voucher_payloads(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["voucher_group_key"]].append(row)

    payloads: List[Dict[str, Any]] = []

    for voucher_group_key, group_rows in grouped.items():
        group_rows.sort(key=lambda r: (r["excel_row_number"], r["full_name"] or ""))
        first = group_rows[0]
        passengers = dedupe_passengers(group_rows)

        destination_name = first["destination"]
        hotel_name = first["hotel_name"]

        payloads.append(
            {
                "voucher_group_key": voucher_group_key,
                "voucher": {
                    "voucher_code": None,
                    "confirmation_number": None,
                    "issue_date": None,
                    "remarks": None,
                    "meals": None,
                    "other_services": None,
                },
                "source": {
                    "sheet_name": None,
                    "group_label": first["group_label"],
                    "excel_rows": [r["excel_row_number"] for r in group_rows],
                },
                "destination": {
                    "name": destination_name,
                    "display_name": to_title_case(destination_name) or destination_name,
                },
                "hotel": {
                    "name": hotel_name,
                    "display_name": to_title_case(hotel_name) or hotel_name,
                    "address": None,
                    "city": None,
                    "country": None,
                    "phone": None,
                },
                "stay": {
                    "check_in": first["check_in"],
                    "check_out": first["check_out"],
                    "nights": first["nights"],
                },
                "rooms": [
                    {
                        "room_sequence": 1,
                        "room_count": first["qty"] or 1,
                        "room_category": first["room"],
                        "additional_info": None,
                        "pax_count": len(passengers),
                    }
                ],
                "passengers": passengers,
            }
        )

    payloads.sort(
        key=lambda p: (
            p["stay"]["check_in"] or "",
            p["destination"]["name"] or "",
            p["hotel"]["name"] or "",
            p["voucher_group_key"],
        )
    )
    return payloads


# -------- CLI --------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the operational XLSX into voucher-grouped JSON payloads."
    )
    parser.add_argument("input", help="Path to the source .xlsx file")
    parser.add_argument("-o", "--output", help="Path to the output .json file")
    parser.add_argument("--sheet", help="Optional sheet name. Defaults to the first sheet.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".voucher_payloads.json")

    rows = read_effective_rows(input_path, sheet_name=args.sheet)
    payloads = build_voucher_payloads(rows)

    output_path.write_text(
        json.dumps(payloads, ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )

    print(f"Rows processed: {len(rows)}")
    print(f"Voucher payloads generated: {len(payloads)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()