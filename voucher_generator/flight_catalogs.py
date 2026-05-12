from __future__ import annotations

import re
from typing import Any, Optional


AIRLINE_NAMES: dict[str, str] = {
    # Americas
    "AA": "American Airlines",
    "UA": "United Airlines",
    "DL": "Delta Air Lines",
    "LA": "LATAM Airlines",
    "AR": "Aerolíneas Argentinas",
    "B6": "JetBlue",
    "BW": "Caribbean Airlines",
    "KX": "Cayman Airways",

    # Europe
    "LX": "SWISS",
    "LH": "Lufthansa",
    "IB": "Iberia",
    "UX": "Air Europa",
    "DE": "Condor",
    "EW": "Eurowings",
    "BA": "British Airways",
    "FI": "Icelandair",
    "AZ": "ITA Airways",

    # Middle East / Africa / Asia / Oceania
    "QR": "Qatar Airways",
    "EK": "Emirates",
    "ET": "Ethiopian Airlines",
    "EY": "Etihad Airways",
    "CX": "Cathay Pacific",
    "JL": "Japan Airlines",
    "CA": "Air China",
    "QF": "Qantas",
}


AIRPORT_CITY_NAMES: dict[str, str] = {
    # Argentina
    "EZE": "Buenos Aires",
    "AEP": "Buenos Aires",
    "COR": "Córdoba",
    "MDZ": "Mendoza",
    "ROS": "Rosario",
    "BRC": "Bariloche",
    "SLA": "Salta",
    "IGR": "Iguazú",
    "USH": "Ushuaia",

    # Chile
    "SCL": "Santiago de Chile",
    "ANF": "Antofagasta",
    "PMC": "Puerto Montt",
    "PUQ": "Punta Arenas",

    # Brazil
    "GRU": "São Paulo",
    "CGH": "São Paulo",
    "VCP": "Campinas",
    "GIG": "Rio de Janeiro",
    "SDU": "Rio de Janeiro",
    "BSB": "Brasília",
    "CNF": "Belo Horizonte",
    "SSA": "Salvador",
    "REC": "Recife",
    "FOR": "Fortaleza",
    "POA": "Porto Alegre",
    "CWB": "Curitiba",
    "FLN": "Florianópolis",
    "NAT": "Natal",
    "BEL": "Belém",
    "MAO": "Manaus",

    # Venezuela
    "CCS": "Caracas",
    "MAR": "Maracaibo",
    "VLN": "Valencia",
    "PMV": "Isla Margarita",

    # Colombia
    "BOG": "Bogotá",
    "MDE": "Medellín",
    "CLO": "Cali",
    "CTG": "Cartagena",
    "BAQ": "Barranquilla",
    "SMR": "Santa Marta",

    # Ecuador
    "UIO": "Quito",
    "GYE": "Guayaquil",
    "CUE": "Cuenca",
    "GPS": "Galápagos",

    # Bolivia
    "VVI": "Santa Cruz de la Sierra",
    "LPB": "La Paz",
    "CBB": "Cochabamba",
    "SRE": "Sucre",
    "TJA": "Tarija",

    # Peru
    "LIM": "Lima",
    "CUZ": "Cusco",
    "AQP": "Arequipa",
    "TRU": "Trujillo",
    "IQT": "Iquitos",

    # Panama / Caribbean / Central America
    "PTY": "Panama City",
    "POS": "Port of Spain",
    "TAB": "Tobago",
    "UVF": "Saint Lucia",
    "SLU": "Saint Lucia",
    "GUA": "Guatemala City",
    "CUN": "Cancún",
    "MEX": "Mexico City",
    "NLU": "Mexico City",
    "GDL": "Guadalajara",
    "MTY": "Monterrey",
    "SJD": "Los Cabos",
    "ASU": "Asunción",

    # United States
    "MIA": "Miami",
    "FLL": "Fort Lauderdale",
    "MCO": "Orlando",
    "TPA": "Tampa",
    "JFK": "New York",
    "LGA": "New York",
    "EWR": "Newark",
    "BOS": "Boston",
    "IAD": "Washington, DC",
    "DCA": "Washington, DC",
    "ORD": "Chicago",
    "DFW": "Dallas",
    "IAH": "Houston",
    "ATL": "Atlanta",
    "LAX": "Los Angeles",
    "SFO": "San Francisco",
    "SEA": "Seattle",
    "LAS": "Las Vegas",
    "PHX": "Phoenix",
    "DEN": "Denver",
    "CLT": "Charlotte",
    "MSP": "Minneapolis",   
    

    # Germany
    "FRA": "Frankfurt",
    "MUC": "Munich",
    "BER": "Berlin",
    "DUS": "Düsseldorf",
    "HAM": "Hamburg",

    # Spain
    "MAD": "Madrid",
    "BCN": "Barcelona",
    "PMI": "Palma de Mallorca",
    "AGP": "Málaga",
    "VLC": "Valencia",
    "SVQ": "Seville",
    "BIO": "Bilbao",

    # France
    "CDG": "Paris",
    "ORY": "Paris",
    "NCE": "Nice",
    "LYS": "Lyon",
    "MRS": "Marseille",
    "TLS": "Toulouse",

    # Hungary
    "BUD": "Budapest",

    # Italy
    "FCO": "Rome",
    "CIA": "Rome",
    "MXP": "Milan",
    "LIN": "Milan",
    "VCE": "Venice",
    "NAP": "Naples",
    "FLR": "Florence",
    "BLQ": "Bologna",
    "TRN": "Turin",

    # Switzerland
    "ZRH": "Zurich",
    "GVA": "Geneva",
    "BSL": "Basel",

    # Sweden / Norway / Finland / Poland
    "ARN": "Stockholm",
    "GOT": "Gothenburg",
    "OSL": "Oslo",
    "BGO": "Bergen",
    "HEL": "Helsinki",
    "WAW": "Warsaw",
    "KRK": "Kraków",
    "GDN": "Gdańsk",

    # United Kingdom / Ireland
    "LHR": "London",
    "LGW": "London",
    "LCY": "London",
    "STN": "London",
    "MAN": "Manchester",
    "EDI": "Edinburgh",
    "DUB": "Dublin",
    "SNN": "Shannon",
    "ORK": "Cork",

    # Russia
    "SVO": "Moscow",
    "DME": "Moscow",
    "VKO": "Moscow",
    "LED": "Saint Petersburg",
}


def normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def extract_airline_code(flight_number: Any) -> Optional[str]:
    text = normalize_code(flight_number).replace(" ", "")
    match = re.match(r"([A-Z0-9]{2})(\d+.*)?$", text)
    if not match:
        return None
    return match.group(1)


def airline_name_for_code(code: Any) -> str:
    return AIRLINE_NAMES.get(normalize_code(code), "")


def airline_display_name(flight_number: Any) -> str:
    raw = str(flight_number or "").strip()
    code = extract_airline_code(raw)
    if not code:
        return raw

    airline_name = airline_name_for_code(code)
    if airline_name:
        return f"{airline_name} · {raw}"

    return raw


def airport_city_name(airport_code: Any) -> str:
    return AIRPORT_CITY_NAMES.get(normalize_code(airport_code), "")
