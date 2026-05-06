from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from voucher_generator.xlsx_importer import clean_text


def to_title_case(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return text.title()


def dedupe_real_passengers(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    passengers: List[Dict[str, Any]] = []

    for row in sorted(rows, key=lambda r: (r["excel_row_number"], r.get("source_row_number") or 0)):
        if not row.get("full_name"):
            continue

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
                "meals": row["meals"],
                "remarks": row["remarks"],
            }
        )

    return passengers


def pad_passengers(passengers: List[Dict[str, Any]], qty: int, block_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    padded = list(passengers)
    next_index = len(padded) + 1

    while len(padded) < qty:
        padded.append(
            {
                "passenger_key": f"PENDING-{block_rows[0]['excel_row_number']}-{next_index}",
                "first_name": None,
                "last_name": None,
                "full_name": "NAME PENDING",
                "mail": None,
                "phone": None,
                "nationality": None,
                "date_of_birth": None,
                "passport_number": None,
                "passport_expiration": None,
                "food_restrictions": None,
                "remarks": None,
            }
        )
        next_index += 1

    return padded


def choose_block_header(block_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return sorted(block_rows, key=lambda r: r["excel_row_number"])[0]


def build_canonical_voucher(block_rows: List[Dict[str, Any]], voucher_index: int) -> Dict[str, Any]:
    block_rows = sorted(block_rows, key=lambda r: r["excel_row_number"])
    header = choose_block_header(block_rows)
    passengers = dedupe_real_passengers(block_rows)

    declared_qty = header.get("qty") or 0
    is_merged_qty_block = bool(header.get("qty_merge_anchor"))

    if is_merged_qty_block:
        pax_count = max(1, len(block_rows))
    else:
        pax_count = declared_qty if declared_qty > 0 else max(1, len(passengers))

    passengers = pad_passengers(passengers, pax_count, block_rows)

    voucher_id = header.get("source_row_number") or voucher_index

    return {
        "id": voucher_id,
        "group_key": f"VOUCHER-{voucher_id}",
        "group_label": header.get("group_label"),
        "destination": {
            "name": header.get("destination"),
            "display_name": to_title_case(header.get("destination")) or header.get("destination"),
        },
        "hotel": {
            "name": header.get("hotel_name"),
            "display_name": to_title_case(header.get("hotel_name")) or header.get("hotel_name"),
            "address": None,
            "city": None,
            "country": None,
            "phone": None,
        },
        "stay": {
            "check_in": header.get("check_in"),
            "check_out": header.get("check_out"),
            "nights": header.get("nights"),
        },
        "rooms": [
            {
                "room_sequence": 1,
                "room_count": 1,
                "room_category": header.get("room"),
                "additional_info": None,
                "pax_count": pax_count,
            }
        ],
        "passengers": passengers,
        "voucher_info": {
            "voucher_code": None,
            "confirmation_number": None,
            "issue_date": None,
            "remarks": None,
            "meals": None,
            "other_services": None,
        },
        "meta": {
            "source_excel_rows": [r["excel_row_number"] for r in block_rows],
            "source_row_numbers": [
                r["source_row_number"] for r in block_rows if r.get("source_row_number") is not None
            ],
            "qty_merge_anchor": header.get("qty_merge_anchor"),
        },
    }


def canonical_to_payload(voucher: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "voucher_id": voucher["id"],
        "voucher_group_key": voucher["group_key"],
        "voucher": voucher["voucher_info"],
        "source": {
            "sheet_name": None,
            "group_label": voucher.get("group_label"),
            "excel_rows": voucher["meta"]["source_excel_rows"],
            "row_numbers": voucher["meta"]["source_row_numbers"],
            "qty_merge_anchor": voucher["meta"]["qty_merge_anchor"],
        },
        "destination": voucher["destination"],
        "hotel": voucher["hotel"],
        "stay": voucher["stay"],
        "rooms": voucher["rooms"],
        "passengers": voucher["passengers"],
    }