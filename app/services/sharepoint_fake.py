from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[2]

# Este archivo local actúa como si fuera el Excel descargado desde SharePoint.
# Debe existir dentro del proyecto principal en: sample_data/input.xlsx
FAKE_SOURCE_EXCEL = BASE_DIR / "sample_data" / "input.xlsx"


FAKE_FILES: List[Dict] = [
    {
        "id": "sp-file-001",
        "name": "Pasajeros marzo.xlsx",
        "web_url": "https://fake-sharepoint.local/files/pasajeros-marzo",
        "size": 182344,
    },
    {
        "id": "sp-file-002",
        "name": "Rooming list grupo Hilton.xlsx",
        "web_url": "https://fake-sharepoint.local/files/rooming-hilton",
        "size": 223891,
    },
    {
        "id": "sp-file-003",
        "name": "Voucher inputs prueba.xlsx",
        "web_url": "https://fake-sharepoint.local/files/voucher-inputs-prueba",
        "size": 99123,
    },
]

FAKE_FOLDERS: List[Dict] = [
    {
        "id": "sp-folder-001",
        "name": "Resultados vouchers",
        "web_url": "https://fake-sharepoint.local/folders/resultados-vouchers",
    },
    {
        "id": "sp-folder-002",
        "name": "Operaciones / Hoteles",
        "web_url": "https://fake-sharepoint.local/folders/operaciones-hoteles",
    },
    {
        "id": "sp-folder-003",
        "name": "Pruebas pipeline",
        "web_url": "https://fake-sharepoint.local/folders/pruebas-pipeline",
    },
]


def list_fake_files() -> List[Dict]:
    return FAKE_FILES


def list_fake_folders() -> List[Dict]:
    return FAKE_FOLDERS


def get_fake_file(file_id: str) -> Optional[Dict]:
    return next((f for f in FAKE_FILES if f["id"] == file_id), None)


def get_fake_folder(folder_id: str) -> Optional[Dict]:
    return next((f for f in FAKE_FOLDERS if f["id"] == folder_id), None)


def fake_download_excel(file_id: str, destination_path: Path) -> Path:
    """
    Simula la descarga desde SharePoint copiando un Excel local de prueba.
    """
    file_meta = get_fake_file(file_id)
    if not file_meta:
        raise ValueError("Archivo fake no encontrado.")

    if not FAKE_SOURCE_EXCEL.exists():
        raise FileNotFoundError(
            "No existe el Excel local de prueba. "
            f"Creá este archivo: {FAKE_SOURCE_EXCEL}"
        )

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FAKE_SOURCE_EXCEL, destination_path)
    return destination_path
