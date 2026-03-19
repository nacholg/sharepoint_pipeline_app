from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import requests


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphSharePointService:
    def __init__(self, access_token: str) -> None:
        if not access_token:
            raise ValueError("Falta access token de Microsoft Graph.")
        self.access_token = access_token

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = requests.get(url, headers=self.headers, params=params, timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Graph GET {url} -> {resp.status_code}: {resp.text}")
        return resp.json()

    @staticmethod
    def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        is_folder = item.get("folder") is not None
        is_file = item.get("file") is not None

        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "web_url": item.get("webUrl"),
            "size": item.get("size", 0),
            "is_folder": is_folder,
            "is_file": is_file,
            "mime_type": (item.get("file") or {}).get("mimeType"),
            "parent_path": ((item.get("parentReference") or {}).get("path")),
        }

    def list_root_children(self) -> List[Dict[str, Any]]:
        url = f"{GRAPH_BASE}/me/drive/root/children"
        data = self._get(url, params={"$top": 200})
        return [self._normalize_item(x) for x in data.get("value", [])]

    def list_children(self, item_id: str) -> List[Dict[str, Any]]:
        url = f"{GRAPH_BASE}/me/drive/items/{item_id}/children"
        data = self._get(url, params={"$top": 200})
        return [self._normalize_item(x) for x in data.get("value", [])]

    def get_item(self, item_id: str) -> Dict[str, Any]:
        url = f"{GRAPH_BASE}/me/drive/items/{item_id}"
        data = self._get(url)
        return self._normalize_item(data)

    def download_file(self, item_id: str, destination_path: Path) -> Path:
        url = f"{GRAPH_BASE}/me/drive/items/{item_id}/content"
        resp = requests.get(url, headers=self.headers, timeout=120, allow_redirects=True)

        if not resp.ok:
            raise RuntimeError(f"Graph download failed -> {resp.status_code}: {resp.text}")

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(resp.content)
        return destination_path

    def get_site_by_path(self, hostname: str, site_path: str) -> Dict[str, Any]:
        url = f"{GRAPH_BASE}/sites/{hostname}:{site_path}"
        data = self._get(url)
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "web_url": data.get("webUrl"),
        }

    def list_site_drives(self, site_id: str) -> List[Dict[str, Any]]:
        url = f"{GRAPH_BASE}/sites/{site_id}/drives"
        data = self._get(url)

        return [
            {
                "id": x.get("id"),
                "name": x.get("name"),
                "web_url": x.get("webUrl"),
            }
            for x in data.get("value", [])
        ]

    def list_drive_root_children(self, drive_id: str) -> List[Dict[str, Any]]:
        url = f"{GRAPH_BASE}/drives/{drive_id}/root/children"
        data = self._get(url, params={"$top": 200})
        return [self._normalize_item(x) for x in data.get("value", [])]

    def list_drive_children(self, drive_id: str, item_id: str) -> List[Dict[str, Any]]:
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/children"
        data = self._get(url, params={"$top": 200})
        return [self._normalize_item(x) for x in data.get("value", [])]

    def get_drive_item(self, drive_id: str, item_id: str) -> Dict[str, Any]:
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}"
        data = self._get(url)
        return self._normalize_item(data)

    def get_drive_root(self, drive_id: str) -> Dict[str, Any]:
        url = f"{GRAPH_BASE}/drives/{drive_id}/root"
        data = self._get(url)
        return self._normalize_item(data)

    def get_drive_item_by_path(self, drive_id: str, item_path: str) -> Dict[str, Any]:
        clean_path = item_path.strip("/")
        url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{clean_path}"
        data = self._get(url)
        return self._normalize_item(data)

    def download_drive_file(
        self,
        drive_id: str,
        item_id: str,
        destination_path: Path,
    ) -> Path:
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"
        resp = requests.get(url, headers=self.headers, timeout=120, allow_redirects=True)

        if not resp.ok:
            raise RuntimeError(f"Graph download failed -> {resp.status_code}: {resp.text}")

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(resp.content)
        return destination_path

    def upload_file_to_folder(
        self,
        drive_id: str,
        folder_id: str,
        local_file_path: Path,
        remote_filename: str | None = None,
    ) -> Dict[str, Any]:
        local_file_path = Path(local_file_path)
        if not local_file_path.exists():
            raise FileNotFoundError(f"No existe el archivo local: {local_file_path}")

        filename = remote_filename or local_file_path.name
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_id}:/{filename}:/content"

        with local_file_path.open("rb") as f:
            resp = requests.put(
                url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/octet-stream",
                },
                data=f,
                timeout=180,
            )

        if not resp.ok:
            raise RuntimeError(f"Graph upload failed -> {resp.status_code}: {resp.text}")

        return self._normalize_item(resp.json())