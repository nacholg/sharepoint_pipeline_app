from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Tuple


def _parse_date(value: Any):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def _today() -> date:
    return date.today()


def _is_reasonable_birth_date(d: date) -> bool:
    today = _today()
    if d > today:
        return False
    age_years = (today - d).days / 365.25
    return 0 <= age_years <= 120


def _is_reasonable_passport_expiration(d: date) -> bool:
    today = _today()
    # tolera expirados recientes como warning, pero invalida años absurdos
    return today.year - 1 <= d.year <= today.year + 25


def _is_reasonable_stay_date(d: date) -> bool:
    return 2000 <= d.year <= 2100


def validate_row(row: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Devuelve (errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

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

    check_in = _parse_date(row.get("check_in"))
    check_out = _parse_date(row.get("check_out"))
    dob = _parse_date(row.get("date_of_birth"))
    passport_exp = _parse_date(row.get("passport_expiration"))

    # Stay dates
    if row.get("check_in") and not check_in:
        errors.append("invalid check_in format")
    if row.get("check_out") and not check_out:
        errors.append("invalid check_out format")

    if check_in:
        if not _is_reasonable_stay_date(check_in):
            errors.append(f"check_in out of reasonable range: {check_in.isoformat()}")

    if check_out:
        if not _is_reasonable_stay_date(check_out):
            errors.append(f"check_out out of reasonable range: {check_out.isoformat()}")

    if check_in and check_out:
        if check_out < check_in:
            errors.append("check_out is before check_in")

        nights = row.get("nights")
        if nights not in (None, ""):
            try:
                nights = int(nights)
                diff = (check_out - check_in).days
                if diff != nights:
                    warnings.append(f"nights mismatch: expected {diff}, got {nights}")
            except Exception:
                warnings.append("invalid nights value")

    # Qty
    qty = row.get("qty")
    if qty is not None:
        try:
            qty = int(qty)
            if qty <= 0:
                errors.append("qty must be > 0")
        except Exception:
            warnings.append("invalid qty format")

    # Passenger data
    if not row.get("full_name"):
        warnings.append("missing passenger name")

    if not row.get("passport_number"):
        warnings.append("missing passport")

    # DOB
    if row.get("date_of_birth") and not dob:
        warnings.append("invalid date_of_birth format")
    elif dob and not _is_reasonable_birth_date(dob):
        warnings.append(f"suspicious date_of_birth: {dob.isoformat()}")

    # Passport expiration
    if row.get("passport_expiration") and not passport_exp:
        warnings.append("invalid passport_expiration format")
    elif passport_exp:
        if not _is_reasonable_passport_expiration(passport_exp):
            errors.append(f"suspicious passport_expiration: {passport_exp.isoformat()}")
        elif passport_exp < _today():
            warnings.append(f"passport expired: {passport_exp.isoformat()}")

    # Email
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