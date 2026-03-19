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

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
LOGO_DEV_TOKEN = os.getenv("LOGO_DEV_TOKEN")

if not GOOGLE_API_KEY:
    raise ValueError("Falta GOOGLE_PLACES_API_KEY en .env")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places"


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
        # Official Logo.dev image API uses the token query param with a publishable key.
        return f"https://img.logo.dev/www.{domain}?token={LOGO_DEV_TOKEN}&size=256&format=png"
    return None


def search_place(query: str) -> Optional[str]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
    }
    payload = {"textQuery": query}
    res = requests.post(TEXT_SEARCH_URL, headers=headers, json=payload, timeout=30)
    if res.status_code != 200:
        print(f"[ERROR] search_place {query}: {res.status_code} {res.text}")
        return None
    data = res.json()
    places = data.get("places", [])
    if not places:
        return None
    return places[0].get("id")


def get_place_details(place_id: str) -> Dict[str, Any]:
    url = f"{DETAILS_URL}/{place_id}"
    headers = {
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "id,displayName,formattedAddress,addressComponents,"
            "internationalPhoneNumber,websiteUri,googleMapsUri"
        ),
    }
    res = requests.get(url, headers=headers, timeout=30)
    if res.status_code != 200:
        print(f"[ERROR] get_place_details {place_id}: {res.status_code} {res.text}")
        return {}
    return res.json()


def parse_address_components(components: list[dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
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


def download_logo(domain: Optional[str], destination_dir: Path) -> tuple[Optional[str], Optional[str]]:
    url = logo_url_for_domain(domain)
    if not url:
        return None, None

    destination_dir.mkdir(parents=True, exist_ok=True)
    local_filename = f"{slugify(domain)}.png"
    local_path = destination_dir / local_filename

    if local_path.exists() and local_path.stat().st_size > 0:
        return url, str(local_path.as_posix())

    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200 and res.content:
            local_path.write_bytes(res.content)
            return url, str(local_path.as_posix())
        print(f"[WARN] logo download failed for {domain}: {res.status_code} {res.text[:200]}")
    except Exception as exc:
        print(f"[WARN] logo download exception for {domain}: {exc}")
    return url, None


def enrich_hotel(hotel: Dict[str, Any], destination: Optional[str], cache: Dict[str, Any], logos_dir: Path) -> Dict[str, Any]:
    hotel_name = clean_text(hotel.get("name"))
    destination_name = clean_text(destination)
    if not hotel_name:
        enriched = {**hotel, "enrichment_status": "missing_hotel_name"}
        return enriched

    cache_key = f"{hotel_name}|{destination_name or ''}"
    if cache_key in cache:
        return cache[cache_key]

    query = " ".join(part for part in [hotel_name, destination_name] if part)
    print(f"[SEARCH] {query}")
    place_id = search_place(query)

    if not place_id:
        enriched = {**hotel, "enrichment_status": "not_found"}
        cache[cache_key] = enriched
        return enriched

    details = get_place_details(place_id)
    components = details.get("addressComponents", [])
    city, country = parse_address_components(components)
    website = details.get("websiteUri")
    domain = extract_domain(website)
    remote_logo_url, local_logo_path = download_logo(domain, logos_dir)

    enriched = {
        **hotel,
        "address": details.get("formattedAddress") or hotel.get("address"),
        "city": city or hotel.get("city"),
        "country": country or hotel.get("country"),
        "phone": details.get("internationalPhoneNumber") or hotel.get("phone"),
        "website": website,
        "domain": domain,
        "logo_url": remote_logo_url,
        "local_logo_path": local_logo_path,
        "google_place_id": details.get("id") or place_id,
        "google_maps_uri": details.get("googleMapsUri"),
        "enrichment_status": "ok",
    }
    cache[cache_key] = enriched
    return enriched



def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich hotel data with Google Places and download local hotel logos.")
    parser.add_argument("input", help="Path to voucher_payloads.json")
    parser.add_argument("-o", "--output", default="voucher_payloads_enriched.json", help="Output JSON path")
    parser.add_argument("--cache", default="hotel_cache.json", help="Cache JSON path")
    parser.add_argument("--logos-dir", default="assets/logos", help="Directory to save local logo files")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    cache_path = Path(args.cache)
    logos_dir = Path(args.logos_dir)

    vouchers = load_json(input_path)
    cache = load_cache(cache_path)

    for voucher in vouchers:
        hotel = voucher.get("hotel", {})
        destination = voucher.get("destination", {}).get("name")
        voucher["hotel"] = enrich_hotel(hotel, destination, cache, logos_dir)

    save_cache(cache_path, cache)
    save_json(output_path, vouchers)
    print(f"\n[OK] Enriched file saved: {output_path}\n")
    print(f"\n[OK] Cache updated: {cache_path}")
    print(f"\n[OK] Logos directory: {logos_dir}")


if __name__ == "__main__":
    main()
