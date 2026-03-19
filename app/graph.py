from pathlib import Path
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

class GraphService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def me(self):
        r = requests.get(f"{GRAPH_BASE}/me", headers=self.headers, timeout=60)
        r.raise_for_status()
        return r.json()

    def download_file_by_drive_item(self, drive_id: str, item_id: str, dest_path: Path):
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"
        r = requests.get(url, headers=self.headers, timeout=120)
        r.raise_for_status()
        dest_path.write_bytes(r.content)
        return dest_path

    def upload_small_file(self, drive_id: str, parent_item_id: str, filename: str, local_file: Path):
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{parent_item_id}:/{filename}:/content"
        data = local_file.read_bytes()
        headers = {
            **self.headers,
            "Content-Type": "application/octet-stream"
        }
        r = requests.put(url, headers=headers, data=data, timeout=120)
        r.raise_for_status()
        return r.json()