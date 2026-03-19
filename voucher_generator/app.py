from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_key_text(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return text.upper()


def normalize_email(value: Any) -> Optional[str]:
    text = clean_text(value)
    return text.lower() if text else None


def normalize_date(value: Any) -> Optional[str]:
    if value in (None, "", "None"):
        return None

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return text  # fallback


def normalize_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def build_passenger_key(row: Dict[str, Any]) -> str:
    passport = normalize_key_text(row.get("passport_number"))
    if passport:
        return passport

    last_name = normalize_key_text(row.get("last_name")) or "NO-LASTNAME"
    first_name = normalize_key_text(row.get("first_name")) or "NO-FIRSTNAME"
    dob = normalize_date(row.get("date_of_birth")) or "NO-DOB"
    return f"{last_name}|{first_name}|{dob}"


def build_group_key(row: Dict[str, Any]) -> str:
    hotel = normalize_key_text(row.get("hotel_name")) or "NO-HOTEL"
    check_in = normalize_date(row.get("check_in")) or "NO-CHECKIN"
    check_out = normalize_date(row.get("check_out")) or "NO-CHECKOUT"
    room = normalize_key_text(row.get("room")) or "NO-ROOM"
    group_label = normalize_key_text(row.get("group_label")) or "NO-GROUP"
    return f"{hotel}|{check_in}|{check_out}|{room}|{group_label}"


@dataclass
class NormalizedRow:
    group_label: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    mail: Optional[str]
    phone: Optional[str]
    nationality: Optional[str]
    passport_number: Optional[str]
    passport_expiration: Optional[str]
    hotel_name: Optional[str]
    room: Optional[str]
    check_in: Optional[str]
    check_out: Optional[str]
    nights: Optional[int]
    remarks: Optional[str]
    food_restrictions: Optional[str]
    passenger_key: str
    voucher_group_key: str


def normalize_rows(import_rows: List[Dict[str, Any]]) -> List[NormalizedRow]:
    last_values: Dict[str, Any] = {
        "group_label": None,
        "hotel_name": None,
        "room": None,
        "check_in": None,
        "check_out": None,
        "nights": None,
    }

    normalized: List[NormalizedRow] = []

    for row in import_rows:
        effective_group_label = clean_text(row.get("Group Label")) or last_values["group_label"]
        effective_hotel = clean_text(row.get("Hotel Name Raw")) or last_values["hotel_name"]
        effective_room = clean_text(row.get("Room Raw")) or last_values["room"]
        effective_check_in = normalize_date(row.get("Check In Raw")) or last_values["check_in"]
        effective_check_out = normalize_date(row.get("Check Out Raw")) or last_values["check_out"]
        effective_nights = normalize_int(row.get("Nights Raw")) or last_values["nights"]

        last_values["group_label"] = effective_group_label
        last_values["hotel_name"] = effective_hotel
        last_values["room"] = effective_room
        last_values["check_in"] = effective_check_in
        last_values["check_out"] = effective_check_out
        last_values["nights"] = effective_nights

        row_data = {
            "group_label": effective_group_label,
            "first_name": clean_text(row.get("Traveler First Name Raw")),
            "last_name": clean_text(row.get("Traveler Last Name Raw")),
            "mail": normalize_email(row.get("Mail")),
            "phone": clean_text(row.get("Telefono")),
            "nationality": clean_text(row.get("Nationality")),
            "passport_number": clean_text(row.get("Passport Number")),
            "passport_expiration": normalize_date(row.get("Passport Expiration")),
            "hotel_name": effective_hotel,
            "room": effective_room,
            "check_in": effective_check_in,
            "check_out": effective_check_out,
            "nights": effective_nights,
            "remarks": clean_text(row.get("Remarks Raw")),
            "food_restrictions": clean_text(row.get("Food Restrictions")),
            "date_of_birth": normalize_date(row.get("Date of Birth")),
        }

        passenger_key = build_passenger_key(row_data)
        voucher_group_key = build_group_key(row_data)

        normalized.append(
            NormalizedRow(
                group_label=row_data["group_label"],
                first_name=row_data["first_name"],
                last_name=row_data["last_name"],
                mail=row_data["mail"],
                phone=row_data["phone"],
                nationality=row_data["nationality"],
                passport_number=row_data["passport_number"],
                passport_expiration=row_data["passport_expiration"],
                hotel_name=row_data["hotel_name"],
                room=row_data["room"],
                check_in=row_data["check_in"],
                check_out=row_data["check_out"],
                nights=row_data["nights"],
                remarks=row_data["remarks"],
                food_restrictions=row_data["food_restrictions"],
                passenger_key=passenger_key,
                voucher_group_key=voucher_group_key,
            )
        )

    return normalized


def group_rows_by_voucher(rows: List[NormalizedRow]) -> Dict[str, List[NormalizedRow]]:
    grouped: Dict[str, List[NormalizedRow]] = defaultdict(list)
    for row in rows:
        grouped[row.voucher_group_key].append(row)
    return grouped


def build_voucher_payloads(grouped: Dict[str, List[NormalizedRow]]) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []

    for group_key, rows in grouped.items():
        first = rows[0]

        passengers = []
        seen_passenger_keys = set()

        for row in rows:
            if row.passenger_key in seen_passenger_keys:
                continue
            seen_passenger_keys.add(row.passenger_key)

            passengers.append({
                "passenger_key": row.passenger_key,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "full_name": " ".join(filter(None, [row.first_name, row.last_name])),
                "mail": row.mail,
                "phone": row.phone,
                "nationality": row.nationality,
                "passport_number": row.passport_number,
                "passport_expiration": row.passport_expiration,
                "food_restrictions": row.food_restrictions,
                "remarks": row.remarks,
            })

        payload = {
            "voucher_group_key": group_key,
            "hotel": {
                "name": first.hotel_name,
            },
            "stay": {
                "check_in": first.check_in,
                "check_out": first.check_out,
                "nights": first.nights,
            },
            "rooms": [
                {
                    "room_sequence": 1,
                    "room_count": 1,
                    "room_category": first.room,
                    "additional_info": "",
                    "pax_count": len(passengers),
                }
            ],
            "passengers": passengers,
        }
        payloads.append(payload)

    return payloads