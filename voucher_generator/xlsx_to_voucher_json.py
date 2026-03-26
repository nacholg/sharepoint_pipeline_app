from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from xlsx_importer import clean_text, read_effective_rows
except ImportError:
    from voucher_generator.xlsx_importer import clean_text, read_effective_rows


def to_title_case(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return text.title()


def build_voucher_blocks(rows: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    blocks: List[List[Dict[str, Any]]] = []
    current_block: List[Dict[str, Any]] = []
    current_block_key: Optional[str] = None

    for row in rows:
        qty = row.get("qty")
        qty_anchor = row.get("qty_merge_anchor")

        if qty_anchor:
            block_key = f"MERGED:{qty_anchor}"
            if current_block and current_block_key != block_key:
                blocks.append(current_block)
                current_block = []
            current_block_key = block_key
            current_block.append(row)
            continue

        if current_block:
            blocks.append(current_block)
            current_block = []
            current_block_key = None

        if qty is not None or row.get("full_name") or row.get("hotel_name") or row.get("destination"):
            blocks.append([row])

    if current_block:
        blocks.append(current_block)

    return blocks


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
                "food_restrictions": row["food_restrictions"],
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


def build_voucher_payloads(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks = build_voucher_blocks(rows)
    payloads: List[Dict[str, Any]] = []

    for voucher_index, block_rows in enumerate(blocks, start=1):
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

        payloads.append(
            {
                "voucher_id": voucher_id,
                "voucher_group_key": f"VOUCHER-{voucher_id}",
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
                    "group_label": header.get("group_label"),
                    "excel_rows": [r["excel_row_number"] for r in block_rows],
                    "row_numbers": [
                        r["source_row_number"] for r in block_rows if r.get("source_row_number") is not None
                    ],
                    "qty_merge_anchor": header.get("qty_merge_anchor"),
                },
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
            }
        )

    payloads.sort(
        key=lambda p: (
            str(p.get("voucher_id") or ""),
            p["stay"]["check_in"] or "",
            p["destination"]["name"] or "",
            p["hotel"]["name"] or "",
        )
    )
    return payloads


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the operational XLSX into voucher JSON payloads, honoring merged QTY blocks."
    )
    parser.add_argument("input", help="Path to the source .xlsx file")
    parser.add_argument("-o", "--output", help="Path to the output .json file")
    parser.add_argument("--sheet", help="Optional sheet name. Defaults to the first sheet.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output.")
    parser.add_argument(
        "--debug-rows",
        action="store_true",
        help="Also emit a .rows.json file with normalized rows for debugging.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".voucher_payloads.json")

    rows = read_effective_rows(input_path, sheet_name=args.sheet)
    payloads = build_voucher_payloads(rows)

    output_path.write_text(
        json.dumps(payloads, ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )

    if args.debug_rows:
        debug_path = output_path.with_suffix(".rows.json")
        debug_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Debug rows: {debug_path}")

    print(f"Rows processed: {len(rows)}")
    print(f"Voucher payloads generated: {len(payloads)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()