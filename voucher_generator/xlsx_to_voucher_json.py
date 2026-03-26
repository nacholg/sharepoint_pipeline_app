from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from voucher_generator.voucher_validator import validate_rows
from voucher_generator.xlsx_importer import read_effective_rows
from voucher_generator.voucher_model import build_canonical_voucher, canonical_to_payload

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


def build_voucher_payloads(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks = build_voucher_blocks(rows)
    canonical_vouchers: List[Dict[str, Any]] = []
    payloads: List[Dict[str, Any]] = []

    for voucher_index, block_rows in enumerate(blocks, start=1):
        canonical = build_canonical_voucher(block_rows, voucher_index)
        canonical_vouchers.append(canonical)
        payloads.append(canonical_to_payload(canonical))

    payloads.sort(
        key=lambda p: (
            str(p.get("voucher_id") or ""),
            p["stay"]["check_in"] or "",
            p["destination"]["name"] or "",
            p["hotel"]["name"] or "",
        )
    )
    return payloads

def run_pipeline(input_path: Path, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    rows = read_effective_rows(input_path, sheet_name=sheet_name)

    validation = validate_rows(rows)
    valid_rows = validation["valid_rows"]
    rows_with_errors = validation["rows_with_errors"]

    if rows_with_errors:
        raise ValueError("Validation errors found")

    payloads = build_voucher_payloads(valid_rows)

    return {
        "rows": rows,
        "validation": validation,
        "payloads": payloads,
    }

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
    parser.add_argument(
        "--profile",
        default="default",
        help="Profile name (default, future clients, etc.)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".voucher_payloads.json")
    
    rows = read_effective_rows(input_path, sheet_name=args.sheet)

    validation = validate_rows(rows)
    valid_rows = validation["valid_rows"]
    rows_with_errors = validation["rows_with_errors"]
    rows_with_warnings = validation["rows_with_warnings"]

    print(f"Rows processed: {len(rows)}")
    print(f"Valid rows: {len(valid_rows)}")
    print(f"Rows with errors: {len(rows_with_errors)}")
    print(f"Rows with warnings: {len(rows_with_warnings)}")

    if rows_with_errors:
        print("\nERRORS FOUND:")
        for err in rows_with_errors[:5]:
            print(f"- Row {err['row_index']}: {err['errors']}")
        raise SystemExit("Aborting due to validation errors")

    payloads = build_voucher_payloads(valid_rows)

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

        if rows_with_errors:
            debug_errors_path = output_path.with_suffix(".errors.json")
            debug_errors_path.write_text(
                json.dumps(rows_with_errors, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Error rows: {debug_errors_path}")

        if rows_with_warnings:
            debug_warnings_path = output_path.with_suffix(".warnings.json")
            debug_warnings_path.write_text(
                json.dumps(rows_with_warnings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Warning rows: {debug_warnings_path}")

    print(f"Voucher payloads generated: {len(payloads)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()