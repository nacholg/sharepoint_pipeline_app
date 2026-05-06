
from __future__ import annotations

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

    return text


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


@dataclass
class NormalizedRow:
    source_index: int
    passenger_number: Optional[int]
    voucher_block_start: bool
    qty_value: Optional[int]
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
    destination: Optional[str]
    check_in: Optional[str]
    check_out: Optional[str]
    nights: Optional[int]
    remarks: Optional[str]
    food_restrictions: Optional[str]
    passenger_key: str

    @property
    def full_name(self) -> str:
        value = " ".join(filter(None, [self.first_name, self.last_name])).strip()
        return value or "NAME PENDING"


def _first_present(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            value = row.get(key)
            if value not in (None, ""):
                return value
    return None


def normalize_rows(import_rows: List[Dict[str, Any]]) -> List[NormalizedRow]:
    """
    Regla de negocio:
    - 1 voucher por bloque lógico.
    - Un bloque lógico empieza cuando la fila trae QTY / QTY Raw con valor.
    - Si QTY está mergeado en Excel, las filas siguientes vienen sin QTY y pertenecen
      al mismo voucher hasta encontrar otro QTY con valor.
    - El campo # se usa como número de pasajero dentro del voucher.
    """
    last_values: Dict[str, Any] = {
        "group_label": None,
        "hotel_name": None,
        "room": None,
        "destination": None,
        "check_in": None,
        "check_out": None,
        "nights": None,
    }

    normalized: List[NormalizedRow] = []

    for idx, row in enumerate(import_rows, start=1):
        qty_raw = _first_present(row, "QTY Raw", "QTY")
        effective_group_label = clean_text(_first_present(row, "Group Label")) or last_values["group_label"]
        effective_hotel = clean_text(_first_present(row, "Hotel Name Raw", "HOTEL NAME", "Hotel Name")) or last_values["hotel_name"]
        effective_room = clean_text(_first_present(row, "Room Raw", "HAB", "Room")) or last_values["room"]
        effective_destination = clean_text(_first_present(row, "Destination Raw", "DESTINATION", "Destination")) or last_values["destination"]
        effective_check_in = normalize_date(_first_present(row, "Check In Raw", "CHECK IN HOTEL", "Check In")) or last_values["check_in"]
        effective_check_out = normalize_date(_first_present(row, "Check Out Raw", "CHECK OUT HOTEL", "Check Out")) or last_values["check_out"]
        effective_nights = normalize_int(_first_present(row, "Nights Raw", "ROOM NIGHTS", "Nights")) or last_values["nights"]

        last_values["group_label"] = effective_group_label
        last_values["hotel_name"] = effective_hotel
        last_values["room"] = effective_room
        last_values["destination"] = effective_destination
        last_values["check_in"] = effective_check_in
        last_values["check_out"] = effective_check_out
        last_values["nights"] = effective_nights

        row_data = {
            "first_name": clean_text(_first_present(row, "Traveler First Name Raw", "TRAVELER FIRST NAME", "First Name")),
            "last_name": clean_text(_first_present(row, "Traveler Last Name Raw", "TRAVELER LAST NAME", "Last Name")),
            "mail": normalize_email(_first_present(row, "Mail", "MAIL")),
            "phone": clean_text(_first_present(row, "Telefono", "TELEFONO ", "Phone")),
            "nationality": clean_text(_first_present(row, "Nationality", "NATIONALITY")),
            "passport_number": clean_text(_first_present(row, "Passport Number", "PASSPORT NUMBER")),
            "passport_expiration": normalize_date(_first_present(row, "Passport Expiration", "EXPIRATION DATE ")),
            "remarks": clean_text(_first_present(row, "Remarks Raw", "REMARKS")),
            "meals": clean_text(_first_present(row, "Meals", "MEALS", "Comidas", "COMIDAS", "Meal Plan", "MEAL PLAN", "Food", "FOOD", "Food Restrictions", "FOOD RESTRICTIONS")),
            "date_of_birth": normalize_date(_first_present(row, "Date of Birth", "DATE OF BIRTH")),
        }

        passenger_key = build_passenger_key(row_data)

        normalized.append(
            NormalizedRow(
                source_index=idx,
                passenger_number=normalize_int(_first_present(row, "#", "Passenger #")),
                voucher_block_start=qty_raw not in (None, ""),
                qty_value=normalize_int(qty_raw),
                group_label=effective_group_label,
                first_name=row_data["first_name"],
                last_name=row_data["last_name"],
                mail=row_data["mail"],
                phone=row_data["phone"],
                nationality=row_data["nationality"],
                passport_number=row_data["passport_number"],
                passport_expiration=row_data["passport_expiration"],
                hotel_name=effective_hotel,
                room=effective_room,
                destination=effective_destination,
                check_in=effective_check_in,
                check_out=effective_check_out,
                nights=effective_nights,
                remarks=row_data["remarks"],
                meals=row_data["meals"],
                passenger_key=passenger_key,
            )
        )

    return normalized


def group_rows_by_voucher(rows: List[NormalizedRow]) -> List[List[NormalizedRow]]:
    grouped: List[List[NormalizedRow]] = []
    current_block: List[NormalizedRow] = []

    for row in rows:
        is_effectively_empty = not any(
            [
                row.first_name,
                row.last_name,
                row.hotel_name,
                row.room,
                row.check_in,
                row.check_out,
                row.destination,
                row.voucher_block_start,
            ]
        )
        if is_effectively_empty:
            continue

        if row.voucher_block_start:
            if current_block:
                grouped.append(current_block)
            current_block = [row]
        else:
            if not current_block:
                current_block = [row]
            else:
                current_block.append(row)

    if current_block:
        grouped.append(current_block)

    return grouped


def _build_passengers(rows: List[NormalizedRow]) -> List[Dict[str, Any]]:
    passengers: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        passengers.append(
            {
                "passenger_key": row.passenger_key,
                "passenger_number": row.passenger_number or idx,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "full_name": row.full_name,
                "mail": row.mail,
                "phone": row.phone,
                "nationality": row.nationality,
                "passport_number": row.passport_number,
                "passport_expiration": row.passport_expiration,
                "meals": row.meals,
                "remarks": row.remarks,
            }
        )

    max_passenger_number = max((p["passenger_number"] or 0) for p in passengers) if passengers else 0
    target_count = max(len(passengers), max_passenger_number)

    while len(passengers) < target_count:
        next_num = len(passengers) + 1
        passengers.append(
            {
                "passenger_key": f"PENDING-{next_num}",
                "passenger_number": next_num,
                "first_name": None,
                "last_name": None,
                "full_name": "NAME PENDING",
                "mail": None,
                "phone": None,
                "nationality": None,
                "passport_number": None,
                "passport_expiration": None,
                "meals": None,
                "remarks": None,
            }
        )

    return passengers


def build_voucher_payloads(grouped: List[List[NormalizedRow]]) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []

    for seq, rows in enumerate(grouped, start=1):
        first = rows[0]
        passengers = _build_passengers(rows)
        passenger_count = len(passengers)

        payload = {
            "voucher_id": f"{seq:02d}",
            "voucher_group_key": f"voucher-{seq:02d}",
            "source_rows": [row.source_index for row in rows],
            "destination": {
                "name": first.destination,
                "display_name": first.destination,
            },
            "hotel": {
                "name": first.hotel_name,
                "display_name": first.hotel_name,
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
                    "pax_count": passenger_count,
                }
            ],
            "passengers": passengers,
        }
        payloads.append(payload)

    return payloads
