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
    payloads: List[Dict[str, Any]] = []

    for voucher_index, block_rows in enumerate(blocks, start=1):
        canonical = build_canonical_voucher(block_rows, voucher_index)
        payload = canonical_to_payload(canonical)

        first_row = block_rows[0] if block_rows else {}
        payload["event_name"] = first_row.get("event_name")
        payload["confirmation_number"] = first_row.get("confirmation_number")

        payloads.append(payload)

    payloads.sort(
        key=lambda p: (
            str(p.get("voucher_id") or ""),
            p["stay"]["check_in"] or "",
            p["destination"]["name"] or "",
            p["hotel"]["name"] or "",
        )
    )
    return payloads


def build_summary(
    *,
    profile_name: str,
    rows: List[Dict[str, Any]],
    valid_rows: List[Dict[str, Any]],
    rows_with_errors: List[Dict[str, Any]],
    rows_with_warnings: List[Dict[str, Any]],
    payloads: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "profile_used": profile_name,
        "total_rows": len(rows),
        "valid_rows": len(valid_rows),
        "errors": len(rows_with_errors),
        "skipped_rows": len(rows_with_errors),
        "warnings": len(rows_with_warnings),
        "vouchers": len(payloads),
    }


def write_json(path: Path, data: Any, *, pretty: bool = True) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2 if pretty else None),
        encoding="utf-8",
    )


def run_pipeline(
    input_path: Path,
    sheet_name: Optional[str] = None,
    profile_name: str = "default",
) -> Dict[str, Any]:
    rows = read_effective_rows(
        input_path,
        sheet_name=sheet_name,
        profile_name=profile_name,
    )

    validation = validate_rows(rows)
    valid_rows = validation["valid_rows"]
    rows_with_errors = validation["rows_with_errors"]
    rows_with_warnings = validation["rows_with_warnings"]

    if not valid_rows:
        raise ValueError("No valid rows found")

    payloads = build_voucher_payloads(valid_rows)
    summary = build_summary(
        profile_name=profile_name,
        rows=rows,
        valid_rows=valid_rows,
        rows_with_errors=rows_with_errors,
        rows_with_warnings=rows_with_warnings,
        payloads=payloads,
    )

    return {
        "rows": rows,
        "validation": validation,
        "payloads": payloads,
        "profile_used": profile_name,
        "pipeline_summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert XLSX into voucher JSON payloads, honoring merged QTY blocks."
    )
    parser.add_argument("input", help="Path to the source .xlsx file")
    parser.add_argument("-o", "--output", help="Path to the output .json file")
    parser.add_argument("--sheet", help="Optional sheet name. Defaults to the first sheet.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output.")
    parser.add_argument("--profile", default="default", help="Profile name to use during import.")
    parser.add_argument(
        "--debug-rows",
        action="store_true",
        help="Also emit .rows.json in addition to summary/errors/warnings.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".voucher_payloads.json")

    rows = read_effective_rows(
        input_path,
        sheet_name=args.sheet,
        profile_name=args.profile,
    )

    validation = validate_rows(rows)
    valid_rows = validation["valid_rows"]
    rows_with_errors = validation["rows_with_errors"]
    rows_with_warnings = validation["rows_with_warnings"]

    print(f"Rows processed: {len(rows)}")
    print(f"Valid rows: {len(valid_rows)}")
    print(f"Rows with errors: {len(rows_with_errors)}")
    print(f"Rows with warnings: {len(rows_with_warnings)}")
    print(f"Profile used: {args.profile}")

    if not valid_rows:
        summary = build_summary(
            profile_name=args.profile,
            rows=rows,
            valid_rows=valid_rows,
            rows_with_errors=rows_with_errors,
            rows_with_warnings=rows_with_warnings,
            payloads=[],
        )

        summary_path = output_path.with_suffix(".summary.json")
        write_json(summary_path, summary)
        print(f"Summary: {summary_path}")

        warnings_path = output_path.with_suffix(".warnings.json")
        write_json(warnings_path, rows_with_warnings)
        print(f"Warning rows: {warnings_path}")

        errors_path = output_path.with_suffix(".errors.json")
        write_json(errors_path, rows_with_errors)
        print(f"Error rows: {errors_path}")

        if args.debug_rows:
            debug_rows_path = output_path.with_suffix(".rows.json")
            write_json(debug_rows_path, rows)
            print(f"Debug rows: {debug_rows_path}")

        raise SystemExit("No valid rows to process")

    payloads = build_voucher_payloads(valid_rows)

    summary = build_summary(
        profile_name=args.profile,
        rows=rows,
        valid_rows=valid_rows,
        rows_with_errors=rows_with_errors,
        rows_with_warnings=rows_with_warnings,
        payloads=payloads,
    )

    # Siempre escribir summary / warnings / errors
    summary_path = output_path.with_suffix(".summary.json")
    write_json(summary_path, summary)
    print(f"Summary: {summary_path}")

    warnings_path = output_path.with_suffix(".warnings.json")
    write_json(warnings_path, rows_with_warnings)
    print(f"Warning rows: {warnings_path}")

    errors_path = output_path.with_suffix(".errors.json")
    write_json(errors_path, rows_with_errors)
    print(f"Error rows: {errors_path}")

    if args.debug_rows:
        debug_rows_path = output_path.with_suffix(".rows.json")
        write_json(debug_rows_path, rows)
        print(f"Debug rows: {debug_rows_path}")

    if rows_with_errors:
        print("\nERRORS FOUND:")
        for err in rows_with_errors[:5]:
            print(f"- Row {err['row_index']}: {err['errors']}")
        print(f"\nSkipped {len(rows_with_errors)} row(s) with errors")

    write_json(output_path, payloads, pretty=args.pretty)

    print(f"Processed {len(payloads)} vouchers successfully")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()