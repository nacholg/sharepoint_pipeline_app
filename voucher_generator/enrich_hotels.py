from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from voucher_generator.hotel_logo_registry import find_manual_logo, load_hotel_logo_registry

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
LOGO_DEV_TOKEN = os.getenv("LOGO_DEV_TOKEN")

if not GOOGLE_API_KEY:
    raise ValueError("Falta GOOGLE_PLACES_API_KEY en .env")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places"

BASE_DIR = Path(__file__).resolve().parent

HOTEL_LIKE_TYPES = {
    "lodging",
    "hotel",
    "resort_hotel",
    "extended_stay_hotel",
    "motel",
    "inn",
    "bed_and_breakfast",
}

BAD_GEOGRAPHIC_TYPES = {
    "locality",
    "political",
    "administrative_area_level_1",
    "administrative_area_level_2",
    "country",
    "postal_code",
    "neighborhood",
    "sublocality",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_cache(path: Path) -> Dict[str, Any]:
    if path.exists():
        return load_json(path)
    return {}


def save_cache(path: Path, cache: Dict[str, Any]) -> None:
    save_json(path, cache)


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    return text or None


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "logo"


def extract_domain(website: Optional[str]) -> Optional[str]:
    if not website:
        return None
    parsed = urlparse(website)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def logo_url_for_domain(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    if LOGO_DEV_TOKEN:
        return f"https://img.logo.dev/www.{domain}?token={LOGO_DEV_TOKEN}&size=256&format=png"
    return None


def append_warning(warnings: list[str], message: str) -> None:
    if message and message not in warnings:
        warnings.append(message)


def resolve_local_asset_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    path = Path(raw)
    if path.is_absolute():
        return path

    return (BASE_DIR / path).resolve()


def local_logo_exists(value: Optional[str]) -> bool:
    candidate = resolve_local_asset_path(value)
    return bool(candidate and candidate.exists() and candidate.is_file())


def build_search_query(hotel: Dict[str, Any], destination: Optional[str]) -> Optional[str]:
    hotel_name = clean_text(hotel.get("name"))
    destination_name = clean_text(destination)
    city = clean_text(hotel.get("city"))
    address = clean_text(hotel.get("address"))

    if not hotel_name:
        return None

    parts: list[str] = [hotel_name, "hotel"]

    if city:
        parts.append(city)

    if destination_name and normalize_text(destination_name) != normalize_text(city):
        parts.append(destination_name)

    if address:
        parts.append(address)

    return " ".join(part for part in parts if part)


def search_places(query: str) -> list[Dict[str, Any]]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.types,"
            "places.primaryType,"
            "places.websiteUri"
        ),
    }
    payload = {"textQuery": query}

    try:
        res = requests.post(TEXT_SEARCH_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        print(f"[ERROR] search_places exception for '{query}': {exc}")
        return []

    if res.status_code != 200:
        print(f"[ERROR] search_places {query}: {res.status_code} {res.text}")
        return []

    data = res.json()
    places = data.get("places", [])
    print(f"[SEARCH] query='{query}' -> {len(places)} candidatos")
    return places


def score_candidate(
    candidate: Dict[str, Any],
    hotel_name: Optional[str],
    city: Optional[str],
    address: Optional[str],
    destination: Optional[str],
) -> int:
    score = 0

    candidate_name = normalize_text(((candidate.get("displayName") or {}).get("text")))
    candidate_address = normalize_text(candidate.get("formattedAddress"))
    candidate_types = set(candidate.get("types", []) or [])
    primary_type = candidate.get("primaryType")

    hotel_name_n = normalize_text(hotel_name)
    city_n = normalize_text(city)
    address_n = normalize_text(address)
    destination_n = normalize_text(destination)

    if primary_type in HOTEL_LIKE_TYPES:
        score += 40

    if candidate_types & HOTEL_LIKE_TYPES:
        score += 35

    if candidate_types & BAD_GEOGRAPHIC_TYPES:
        score -= 80

    if hotel_name_n and hotel_name_n in candidate_name:
        score += 25

    if hotel_name_n:
        hotel_tokens = set(hotel_name_n.split())
        name_tokens = set(candidate_name.split())
        score += min(len(hotel_tokens & name_tokens) * 4, 16)

    if city_n and city_n in candidate_address:
        score += 15

    if destination_n and destination_n in candidate_address:
        score += 10

    if address_n:
        address_tokens = [t for t in address_n.split() if len(t) > 2]
        matches = sum(1 for t in address_tokens if t in candidate_address)
        score += min(matches * 3, 18)

    if candidate.get("websiteUri"):
        score += 10

    return score


def choose_best_candidate(
    places: list[Dict[str, Any]],
    hotel: Dict[str, Any],
    destination: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not places:
        return None

    hotel_name = clean_text(hotel.get("name"))
    city = clean_text(hotel.get("city"))
    address = clean_text(hotel.get("address"))

    ranked: list[tuple[int, Dict[str, Any]]] = []

    for place in places:
        score = score_candidate(place, hotel_name, city, address, destination)
        ranked.append((score, place))

        print(
            "[CANDIDATE] "
            f"score={score} | "
            f"name={((place.get('displayName') or {}).get('text'))} | "
            f"primaryType={place.get('primaryType')} | "
            f"types={place.get('types')} | "
            f"address={place.get('formattedAddress')} | "
            f"website={place.get('websiteUri')}"
        )

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_place = ranked[0]

    if best_score < 0:
        print("[WARN] mejor candidato con score negativo, se descarta")
        return None

    print(
        "[BEST] "
        f"score={best_score} | "
        f"name={((best_place.get('displayName') or {}).get('text'))} | "
        f"address={best_place.get('formattedAddress')}"
    )
    return best_place


def get_place_details(place_id: str) -> Dict[str, Any]:
    url = f"{DETAILS_URL}/{place_id}"
    headers = {
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "id,displayName,formattedAddress,addressComponents,"
            "internationalPhoneNumber,websiteUri,googleMapsUri,types,primaryType"
        ),
    }

    try:
        res = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as exc:
        print(f"[ERROR] get_place_details exception {place_id}: {exc}")
        return {}

    if res.status_code != 200:
        print(f"[ERROR] get_place_details {place_id}: {res.status_code} {res.text}")
        return {}

    return res.json()


def parse_address_components(
    components: list[dict[str, Any]]
) -> tuple[Optional[str], Optional[str]]:
    city = None
    country = None

    for comp in components:
        types = comp.get("types", [])
        long_text = comp.get("longText") or comp.get("shortText")

        if "locality" in types and not city:
            city = long_text
        if "administrativeAreaLevel1" in types and not city:
            city = city or long_text
        if "country" in types and not country:
            country = long_text

    return city, country


def maybe_guess_domain(hotel_name: Optional[str]) -> Optional[str]:
    if not hotel_name:
        return None

    normalized = slugify(hotel_name).replace("-", "")
    if not normalized:
        return None

    guesses = [
        f"{normalized}.com",
        f"{normalized}hotel.com",
        f"hotel{normalized}.com",
    ]
    return guesses[0]


def download_logo(
    domain: Optional[str],
    destination_dir: Path,
) -> tuple[Optional[str], Optional[str]]:
    url = logo_url_for_domain(domain)
    if not url:
        return None, None

    destination_dir.mkdir(parents=True, exist_ok=True)
    local_filename = f"{slugify(domain)}.png"
    local_path = destination_dir / local_filename

    if local_path.exists() and local_path.is_file() and local_path.stat().st_size > 0:
        return url, str(local_path.as_posix())

    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200 and res.content:
            local_path.write_bytes(res.content)
            return url, str(local_path.as_posix())
        print(f"[WARN] logo download failed for {domain}: {res.status_code}")
    except requests.RequestException as exc:
        print(f"[WARN] logo download exception for {domain}: {exc}")

    return url, None


def build_base_result(
    hotel: Dict[str, Any],
    *,
    manual_logo_path: Optional[str],
    warnings: list[str],
    enrichment_status: str,
    logo_source: str,
    logo_status: str,
    logo_url: Optional[str] = None,
    local_logo_path: Optional[str] = None,
    website: Optional[str] = None,
    domain: Optional[str] = None,
    google_place_id: Optional[str] = None,
    google_maps_uri: Optional[str] = None,
    downloaded_logo_path: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        **hotel,
        "logo_url": logo_url,
        "local_logo_path": local_logo_path,
        "manual_logo_path": manual_logo_path,
        "downloaded_logo_path": downloaded_logo_path,
        "logo_source": logo_source,
        "logo_status": logo_status,
        "website": website,
        "domain": domain,
        "google_place_id": google_place_id,
        "google_maps_uri": google_maps_uri,
        "enrichment_status": enrichment_status,
        "validation_warnings": warnings,
    }


def enrich_hotel(
    hotel: Dict[str, Any],
    destination: Optional[str],
    cache: Dict[str, Any],
    logos_dir: Path,
    manual_logo_registry: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    hotel_name = clean_text(hotel.get("name"))
    destination_name = clean_text(destination)
    warnings: list[str] = []

    manual_logo_path = find_manual_logo(hotel_name, registry=manual_logo_registry)
    manual_logo_valid = False

    if manual_logo_path:
        manual_logo_valid = local_logo_exists(manual_logo_path)
        if not manual_logo_valid:
            append_warning(
                warnings,
                f"Manual logo path does not exist: {manual_logo_path}",
            )

    if not hotel_name:
        append_warning(warnings, "Missing hotel name")
        return build_base_result(
            hotel,
            manual_logo_path=manual_logo_path,
            warnings=warnings,
            enrichment_status="missing_hotel_name",
            logo_source="manual" if manual_logo_valid else "none",
            logo_status="ok" if manual_logo_valid else ("missing_file" if manual_logo_path else "none"),
            local_logo_path=manual_logo_path if manual_logo_valid else None,
        )

    cache_key = f"{hotel_name}|{destination_name or ''}"

    if cache_key in cache:
        print(f"[CACHE] {cache_key}")
        cached = dict(cache[cache_key])
        cached_warnings = list(cached.get("validation_warnings") or [])

        for item in warnings:
            append_warning(cached_warnings, item)

        cached_manual_logo_path = cached.get("manual_logo_path")
        cached_downloaded_logo_path = cached.get("downloaded_logo_path") or cached.get("local_logo_path")

        final_manual_logo_path = manual_logo_path or cached_manual_logo_path
        final_manual_logo_valid = local_logo_exists(final_manual_logo_path) if final_manual_logo_path else False

        if final_manual_logo_path and not final_manual_logo_valid:
            append_warning(
                cached_warnings,
                f"Manual logo path does not exist: {final_manual_logo_path}",
            )

        if final_manual_logo_valid:
            cached["manual_logo_path"] = final_manual_logo_path
            cached["local_logo_path"] = final_manual_logo_path
            cached["logo_source"] = "manual"
            cached["logo_status"] = "ok"
        else:
            cached["manual_logo_path"] = final_manual_logo_path
            cached["downloaded_logo_path"] = cached_downloaded_logo_path
            if cached_downloaded_logo_path:
                cached["local_logo_path"] = cached_downloaded_logo_path
                cached["logo_source"] = "google"
                cached["logo_status"] = "ok"
            else:
                cached["local_logo_path"] = None
                cached["logo_source"] = "none"
                cached["logo_status"] = "missing_file" if final_manual_logo_path else "none"

        cached["validation_warnings"] = cached_warnings
        cache[cache_key] = cached
        return cached

    query = build_search_query(hotel, destination)
    if not query:
        append_warning(warnings, "Missing search query for Google Places")
        result = build_base_result(
            hotel,
            manual_logo_path=manual_logo_path,
            warnings=warnings,
            enrichment_status="missing_query",
            logo_source="manual" if manual_logo_valid else "none",
            logo_status="ok" if manual_logo_valid else ("missing_file" if manual_logo_path else "none"),
            local_logo_path=manual_logo_path if manual_logo_valid else None,
        )
        cache[cache_key] = result
        return result

    try:
        candidates = search_places(query)
    except Exception as exc:
        append_warning(warnings, f"Google Places search failed: {exc}")
        result = build_base_result(
            hotel,
            manual_logo_path=manual_logo_path,
            warnings=warnings,
            enrichment_status="google_lookup_error",
            logo_source="manual" if manual_logo_valid else "none",
            logo_status="ok" if manual_logo_valid else ("missing_file" if manual_logo_path else "none"),
            local_logo_path=manual_logo_path if manual_logo_valid else None,
        )
        cache[cache_key] = result
        return result

    if not candidates:
        append_warning(warnings, "Google Places returned no candidates")
        result = build_base_result(
            hotel,
            manual_logo_path=manual_logo_path,
            warnings=warnings,
            enrichment_status="not_found",
            logo_source="manual" if manual_logo_valid else "none",
            logo_status="ok" if manual_logo_valid else ("missing_file" if manual_logo_path else "none"),
            logo_url=None,
            local_logo_path=manual_logo_path if manual_logo_valid else None,
        )
        cache[cache_key] = result
        return result

    best_candidate = choose_best_candidate(candidates, hotel, destination)

    if not best_candidate:
        append_warning(warnings, "Google Places best candidate was discarded")
        result = build_base_result(
            hotel,
            manual_logo_path=manual_logo_path,
            warnings=warnings,
            enrichment_status="not_found",
            logo_source="manual" if manual_logo_valid else "none",
            logo_status="ok" if manual_logo_valid else ("missing_file" if manual_logo_path else "none"),
            logo_url=None,
            local_logo_path=manual_logo_path if manual_logo_valid else None,
        )
        cache[cache_key] = result
        return result

    place_id = best_candidate.get("id")
    if not place_id:
        append_warning(warnings, "Google Places candidate missing place_id")
        result = build_base_result(
            hotel,
            manual_logo_path=manual_logo_path,
            warnings=warnings,
            enrichment_status="missing_place_id",
            logo_source="manual" if manual_logo_valid else "none",
            logo_status="ok" if manual_logo_valid else ("missing_file" if manual_logo_path else "none"),
            logo_url=None,
            local_logo_path=manual_logo_path if manual_logo_valid else None,
        )
        cache[cache_key] = result
        return result

    try:
        details = get_place_details(place_id)
    except Exception as exc:
        append_warning(warnings, f"Google Places details lookup failed: {exc}")
        details = {}

    if not details:
        append_warning(warnings, "Google Places details response was empty")

    components = details.get("addressComponents", [])
    city, country = parse_address_components(components)

    website = details.get("websiteUri") or best_candidate.get("websiteUri")
    domain = extract_domain(website)

    if not domain:
        domain = maybe_guess_domain(hotel_name)
        if domain:
            print(f"[FALLBACK_DOMAIN] hotel='{hotel_name}' -> {domain}")
            append_warning(warnings, f"Website missing, using guessed domain: {domain}")
        else:
            append_warning(warnings, "Website/domain not available for logo lookup")

    remote_logo_url = None
    downloaded_local_logo_path = None
    if domain:
        try:
            remote_logo_url, downloaded_local_logo_path = download_logo(domain, logos_dir)
        except Exception as exc:
            append_warning(warnings, f"Logo download failed: {exc}")

    final_local_logo_path = manual_logo_path if manual_logo_valid else downloaded_local_logo_path

    if manual_logo_valid:
        logo_source = "manual"
        logo_status = "ok"
    elif manual_logo_path and not manual_logo_valid and downloaded_local_logo_path:
        logo_source = "google"
        logo_status = "ok"
        append_warning(warnings, "Manual logo missing; fallback logo was downloaded successfully")
    elif manual_logo_path and not manual_logo_valid:
        logo_source = "none"
        logo_status = "missing_file"
    elif downloaded_local_logo_path or remote_logo_url:
        logo_source = "google"
        logo_status = "ok"
    else:
        logo_source = "none"
        logo_status = "none"
        append_warning(warnings, "No hotel logo could be resolved")

    address_value = details.get("formattedAddress") or hotel.get("address")
    city_value = city or hotel.get("city")
    country_value = country or hotel.get("country")
    phone_value = details.get("internationalPhoneNumber") or hotel.get("phone")

    if not address_value:
        append_warning(warnings, "Missing hotel address after enrichment")
    if not city_value:
        append_warning(warnings, "Missing hotel city after enrichment")
    if not country_value:
        append_warning(warnings, "Missing hotel country after enrichment")
    if not phone_value:
        append_warning(warnings, "Missing hotel phone after enrichment")

    if details:
        enrichment_status = "ok"
        if warnings:
            enrichment_status = "partial"
    else:
        enrichment_status = "partial"

    enriched = {
        **hotel,
        "address": address_value,
        "city": city_value,
        "country": country_value,
        "phone": phone_value,
        "website": website,
        "domain": domain,
        "logo_url": remote_logo_url,
        "local_logo_path": final_local_logo_path,
        "manual_logo_path": manual_logo_path,
        "downloaded_logo_path": downloaded_local_logo_path,
        "logo_source": logo_source,
        "logo_status": logo_status,
        "google_place_id": details.get("id") or place_id,
        "google_maps_uri": details.get("googleMapsUri"),
        "enrichment_status": enrichment_status,
        "validation_warnings": warnings,
    }

    print(
        f"[ENRICH] hotel='{hotel_name}' | "
        f"website={website} | "
        f"domain={domain} | "
        f"manual_logo={manual_logo_path} | "
        f"downloaded_logo={downloaded_local_logo_path} | "
        f"final_logo={final_local_logo_path} | "
        f"logo_source={logo_source} | "
        f"logo_status={logo_status} | "
        f"warnings={len(warnings)}"
    )

    cache[cache_key] = enriched
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich hotel data with Google Places and download local hotel logos."
    )
    parser.add_argument("input", help="Path to voucher_payloads.json")
    parser.add_argument("-o", "--output", default="voucher_payloads_enriched.json", help="Output JSON path")
    parser.add_argument("--cache", default="hotel_cache.json", help="Cache JSON path")
    parser.add_argument("--logos-dir", default="assets/logos", help="Directory to save local logo files")
    parser.add_argument(
        "--manual-logo-registry",
        default="voucher_generator/config/hotel_logo_registry.json",
        help="JSON file with manual hotel_name -> logo path mappings",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    cache_path = Path(args.cache)
    logos_dir = Path(args.logos_dir)

    vouchers = load_json(input_path)
    cache = load_cache(cache_path)
    manual_logo_registry = load_hotel_logo_registry(args.manual_logo_registry)

    print(f"[INFO] manual hotel logo entries: {len(manual_logo_registry)}")

    for voucher in vouchers:
        hotel = voucher.get("hotel", {})
        destination = voucher.get("destination", {}).get("name")
        voucher["hotel"] = enrich_hotel(
            hotel,
            destination,
            cache,
            logos_dir,
            manual_logo_registry=manual_logo_registry,
        )

    save_cache(cache_path, cache)
    save_json(output_path, vouchers)

    print(f"\n[OK] Enriched file saved: {output_path}")
    print(f"[OK] Cache updated: {cache_path}")
    print(f"[OK] Logos directory: {logos_dir}")


if __name__ == "__main__":
    main()