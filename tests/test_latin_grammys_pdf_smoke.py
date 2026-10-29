"""PDF smoke test using verified rows 8-9 of Latin Grammys 2026 workbook."""
from pathlib import Path
import asyncio

from playwright.async_api import async_playwright
from pypdf import PdfReader

from voucher_generator.profiles import get_profile_config
from voucher_generator.render_vouchers_html import build_html


def test_latin_grammys_pdf_print(tmp_path):
    itinerary = {
        "outbound": [
            {"segment_order": 1, "flight_number": "AA 1486", "origin": "GUA", "destination_airport": "DFW", "departure_date": "2026-11-09", "departure_time": "13:06", "arrival_date": "2026-11-09", "arrival_time": "16:50"},
            {"segment_order": 2, "flight_number": "AA2530", "origin": "DFW", "destination_airport": "LAS", "departure_date": "2026-11-09", "departure_time": "19:05", "arrival_date": "2026-11-09", "arrival_time": "20:03"},
        ],
        "return": [
            {"segment_order": 1, "flight_number": "AA 1482", "origin": "LAS", "destination_airport": "DFW", "departure_date": "2026-11-13", "departure_time": "12:44", "arrival_date": "2026-11-13", "arrival_time": "17:41"},
            {"segment_order": 2, "flight_number": "AA 2455", "origin": "DFW", "destination_airport": "GUA", "departure_date": "2026-11-13", "departure_time": "19:18", "arrival_date": "2026-11-13", "arrival_time": "22:36"},
        ],
    }
    passengers = [
        {"full_name": "Luis Estuardo Alejos Rodriguez", "first_name": "Luis Estuardo", "last_name": "Alejos Rodriguez", "ticket_number": "0012387343411", "airline_reservation_code": "HZKYTO", "nationality": "Guatemalteca"},
        {"full_name": "Rosemarie Lucrecia Castillo Barrios", "first_name": "Rosemarie Lucrecia", "last_name": "Castillo Barrios", "ticket_number": "0012387343417", "airline_reservation_code": "HZKYTO", "nationality": "Guatemalteca"},
    ]
    payload = {"event_name": "LATIN GRAMMYS 2026", "voucher": {}, "destination": {"name": "Las Vegas"}, "hotel": {"name": "ARIA RESORT & HOTEL", "city": "Las Vegas", "country": "United States"}, "stay": {}, "rooms": [], "flights": itinerary, "passengers": passengers}
    html = build_html(payload, tmp_path, get_profile_config("default"), None, language_override="es", render_mode="flights")
    assert "HZKYTO" in html
    assert "0012387343411" in html and "0012387343417" in html
    source = tmp_path / "latin_grammys_test.html"
    output = tmp_path / "latin_grammys_test.pdf"
    source.write_text(html, encoding="utf-8")

    async def render():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(source.as_uri(), wait_until="networkidle")
            await page.pdf(path=str(output), format="A4", print_background=True,
                           prefer_css_page_size=True,
                           margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"})
            await browser.close()
    asyncio.run(render())
    from shutil import copyfile
    artifact_dir = Path("test-results")
    artifact_dir.mkdir(exist_ok=True)
    copyfile(output, artifact_dir / "latin_grammys_actual_renderer.pdf")
    pdf = PdfReader(str(output))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    first = pdf.pages[0].extract_text() or ""
    assert len(pdf.pages) <= 3, f"Unexpected page count: {len(pdf.pages)}"
    assert "AA 1486" in text and "AA 2455" in text
    assert "HZKYTO" in text
    assert "DFW" in text
    assert "AA1482" in text.replace(" ", "") and "AA2530" in text.replace(" ", "")
    assert "VUELO 1" in first.upper(), "First page contains only header (empty-page regression)"
    from shutil import copyfile
    artifact_dir = Path("test-results")
    artifact_dir.mkdir(exist_ok=True)
    copyfile(output, artifact_dir / "latin_grammys_actual_renderer.pdf")
    print(f"PDF smoke test passed: {len(pdf.pages)} pages, first page contains flight content")
