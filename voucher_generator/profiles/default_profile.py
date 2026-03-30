from __future__ import annotations

from copy import deepcopy


PROFILE_CONFIG = {
    "key": "default",
    "label": "Default",
    "language": "es",
    "header_row": 3,
    "start_row": 4,
    "field_aliases": {
        "row_number": ["#", "NRO", "ROW NUMBER", "ROW #", "PASSENGER #"],
        "group_label": ["GROUP LABEL", "GROUP", "LABEL"],
        "last_name": ["TRAVELER LAST NAME", "LAST NAME", "SURNAME", "APELLIDO"],
        "first_name": ["TRAVELER FIRST NAME", "FIRST NAME", "NAME", "NOMBRE"],
        "mail": ["MAIL", "EMAIL", "E-MAIL"],
        "phone": ["TELEFONO", "TELEFONO ", "PHONE", "PHONE NUMBER", "CELLPHONE"],
        "nationality": ["NATIONALITY", "NACIONALIDAD"],
        "date_of_birth": ["DATE OF BIRTH", "DOB", "BIRTH DATE", "FECHA DE NACIMIENTO"],
        "passport_number": ["PASSPORT NUMBER", "PASSPORT", "PASSPORT NO", "NRO PASAPORTE"],
        "passport_expiration": [
            "EXPIRATION DATE",
            "EXPIRATION DATE ",
            "PASSPORT EXPIRATION",
            "PASSPORT EXPIRY",
            "VENCIMIENTO PASAPORTE",
        ],
        "remarks": ["REMARKS", "COMMENTS", "OBSERVATIONS", "OBSERVACIONES"],
        "food_restrictions": ["FOOD RESTRICTIONS", "FOOD", "DIETARY RESTRICTIONS"],
        "qty": ["QTY", "PAX", "PAX QTY", "QUANTITY"],
        "room": ["HAB", "ROOM", "ROOM CATEGORY", "ROOM TYPE"],
        "hotel_name": ["HOTEL NAME", "HOTEL", "HOTEL NAME RAW"],
        "destination": ["DESTINATION", "CITY", "DESTINO"],
        "check_in": ["CHECK IN HOTEL", "CHECK IN", "IN", "ARRIVAL"],
        "check_out": ["CHECK OUT HOTEL", "CHECK OUT", "OUT", "DEPARTURE"],
        "nights": ["ROOM NIGHTS", "NIGHTS", "NIGHTS QTY"],
        "confirmation_number": [
            "CONFIRMATION",
            "CONFIRMATION NUMBER",
            "CONF NBR",
            "CONFIRMATION NBR",
        ],
    },
    "required_fields": [
        "row_number",
        "qty",
        "room",
        "hotel_name",
        "destination",
        "check_in",
        "check_out",
    ],
    "branding": {
        "theme_key": "default",
        "brand_logo": "assets/logos/GEOBYPATAGONIK.png",
    },
    "rendering": {
        "header_mode": "event_destination",
        "show_hotel_logo": True,
    },
    "copy": {
        "voucher_kicker": "Voucher de Hotel",
        "footer_note": "Emitido para operación de viajes. Verificar documentación, rooming y datos del hotel antes del envío final.",
    },
}