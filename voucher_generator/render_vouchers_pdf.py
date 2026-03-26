from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import List

from playwright.async_api import async_playwright


async def html_to_pdf(html_file: Path, pdf_file: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page()

        await page.goto(html_file.resolve().as_uri(), wait_until="networkidle")

        await page.pdf(
            path=str(pdf_file),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={
                "top": "0mm",
                "right": "0mm",
                "bottom": "0mm",
                "left": "0mm",
            },
        )

        await browser.close()


async def render_all(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    html_files: List[Path] = sorted(input_dir.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No se encontraron archivos HTML en {input_dir}")

    for html_file in html_files:
        pdf_file = output_dir / f"{html_file.stem}.pdf"
        print(f"[PDF] {html_file.name} -> {pdf_file.name}")
        await html_to_pdf(html_file, pdf_file)

    print(f"\n✔ PDFs generados en: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderiza vouchers HTML a PDF usando Playwright.")
    parser.add_argument(
        "input_dir",
        help="Directorio donde están los HTML, por ejemplo rendered_vouchers",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="rendered_pdfs",
        help="Directorio de salida para PDFs",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    asyncio.run(render_all(input_dir, output_dir))


if __name__ == "__main__":
    main()
