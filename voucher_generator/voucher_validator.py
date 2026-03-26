from __future__ import annotations

from typing import Any, Dict, List, Tuple
from datetime import datetime


def _parse_date(value: Any):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except Exception:
        return None


def validate_row(row: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Devuelve (errors, warnings)
    """
    errors = []
    warnings = []

    # -------------------------
    # REQUIRED FIELDS
    # -------------------------
    required_fields = [
        "hotel_name",
        "destination",
        "check_in",
        "check_out",
        "room",
    ]

    for field in required_fields:
        if not row.get(field):
            errors.append(f"Missing required field: {field}")

    # -------------------------
    # DATE VALIDATION
    # -------------------------
    check_in = _parse_date(row.get("check_in"))
    check_out = _parse_date(row.get("check_out"))

    if check_in and check_out:
        if check_out < check_in:
            errors.append("check_out is before check_in")

        # nights consistency (si existe)
        nights = row.get("nights")
        if nights:
            try:
                nights = int(nights)
                diff = (check_out - check_in).days
                if diff != nights:
                    warnings.append(
                        f"nights mismatch: expected {diff}, got {nights}"
                    )
            except Exception:
                warnings.append("invalid nights value")

    # -------------------------
    # QUANTITY
    # -------------------------
    qty = row.get("qty")
    if qty is not None:
        try:
            qty = int(qty)
            if qty <= 0:
                errors.append("qty must be > 0")
        except Exception:
            warnings.append("invalid qty format")

    # -------------------------
    # PASSENGER DATA
    # -------------------------
    if not row.get("full_name"):
        warnings.append("missing passenger name")

    if not row.get("passport_number"):
        warnings.append("missing passport")


    # -------------------------
    # EMAIL (simple check)
    # -------------------------
    email = row.get("mail")
    if email and "@" not in str(email):
        warnings.append("invalid email format")

    return errors, warnings


def validate_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = []
    rows_with_errors = []
    rows_with_warnings = []

    for idx, row in enumerate(rows):
        errors, warnings = validate_row(row)

        if errors:
            rows_with_errors.append({
                "row_index": idx,
                "errors": errors,
                "row": row,
            })
        else:
            valid_rows.append(row)

        if warnings:
            rows_with_warnings.append({
                "row_index": idx,
                "warnings": warnings,
                "row": row,
            })

    return {
        "valid_rows": valid_rows,
        "rows_with_errors": rows_with_errors,
        "rows_with_warnings": rows_with_warnings,
    }