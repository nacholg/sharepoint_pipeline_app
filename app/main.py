from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app.client_registry import CLIENTS
from app.config import settings
from app.pipeline_runner import run_full_voucher_pipeline
from app.routes.auth_routes import router as auth_router
from app.routes.jobs import router as jobs_router
from app.routes.ui import router as ui_router
from app.services.sharepoint_graph import GraphSharePointService
from app.token_store import get_user_token

load_dotenv()


def _load_sharepoint_sites() -> dict[str, dict]:
    raw = os.getenv("SHAREPOINT_SITES_JSON", "").strip()

    if raw:
        try:
            data = json.loads(raw)
            result = {}
            for item in data:
                key = str(item["key"]).strip()
                result[key] = {
                    "key": key,
                    "label": item.get("label", key),
                    "site_path": item["site_path"],
                    "library_name": item["library_name"],
                    "default_folder_path": item.get("default_folder_path", "/"),
                    "brand_logo": item.get("brand_logo"),
                    "default_profile": item.get("default_profile", "default"),
                }
            if result:
                return result
        except Exception as e:
            raise RuntimeError(f"SHAREPOINT_SITES_JSON inválido: {e}")

    site_path = os.getenv("SHAREPOINT_SITE_PATH", "/sites/GLOBALEVENTS2")
    library_name = os.getenv("SHAREPOINT_LIBRARY_NAME", "Documentos")
    folder_path = os.getenv("SHAREPOINT_FOLDER_PATH", "/General")

    return {
        "globalevents2": {
            "key": "globalevents2",
            "label": "Global Events",
            "site_path": site_path,
            "library_name": library_name,
            "default_folder_path": folder_path,
            "brand_logo": None,
            "default_profile": "default",
        },
        "mastercard": {
            "key": "mastercard",
            "label": "Mastercard",
            "site_path": "/sites/MASTERCARD",
            "library_name": "Documentos",
            "default_folder_path": "/",
            "brand_logo": "assets/logos/MASTERCARD.png",
            "default_profile": "mastercard",
        },
    }


SHAREPOINT_HOSTNAME = os.getenv("SHAREPOINT_HOSTNAME", "patagonik.sharepoint.com")
SHAREPOINT_SITES = _load_sharepoint_sites()

AVAILABLE_PROFILES = [
    {"key": "default", "label": "Default", "enabled": True},
    {"key": "mastercard", "label": "Mastercard", "enabled": True},
    {"key": "banco_guayaquil", "label": "Banco Guayaquil", "enabled": True},

]


app = FastAPI(title="Voucher Generator")
app.add_middleware(SessionMiddleware, secret_key=settings.APP_SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(ui_router)
app.include_router(auth_router)
app.include_router(jobs_router)


class SharePointRunRequest(BaseModel):
    source_file_id: str
    destination_folder_id: str | None = None
    source_site_key: str | None = None
    destination_site_key: str | None = None
    profile: str | None = None
    client_key: str | None = None


def get_graph_access_token_from_session(request: Request) -> str:
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=401,
            detail="No hay usuario autenticado en sesión. Volvé a iniciar sesión.",
        )

    user_email = user.get("email")
    if not user_email:
        raise HTTPException(
            status_code=401,
            detail="La sesión no tiene email de usuario. Volvé a iniciar sesión.",
        )

    access_token = get_user_token(user_email)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Sesión Microsoft no válida o vencida. Volvé a iniciar sesión.",
        )

    return access_token


def get_site_config(site_key: str | None) -> dict:
    if site_key and site_key in SHAREPOINT_SITES:
        return SHAREPOINT_SITES[site_key]

    if "globalevents2" in SHAREPOINT_SITES:
        return SHAREPOINT_SITES["globalevents2"]

    return next(iter(SHAREPOINT_SITES.values()))


def get_client_config(client_key: str | None) -> dict:
    if client_key and client_key in CLIENTS:
        return CLIENTS[client_key]

    if "globalevents2" in CLIENTS:
        return CLIENTS["globalevents2"]

    return next(iter(CLIENTS.values()))


def resolve_profile(profile: str | None, site_key: str | None = None) -> str:
    requested = (profile or "").strip()
    valid_keys = {item["key"] for item in AVAILABLE_PROFILES if item.get("enabled")}

    if requested and requested in valid_keys:
        return requested

    site_cfg = get_site_config(site_key)
    default_profile = site_cfg.get("default_profile", "default")

    if default_profile in valid_keys:
        return default_profile

    return "default"


def get_sharepoint_context(graph: GraphSharePointService, site_key: str | None = None) -> dict:
    site_cfg = get_site_config(site_key)

    print(
        "SP CONFIG:",
        SHAREPOINT_HOSTNAME,
        site_cfg["site_path"],
        site_cfg["library_name"],
        site_cfg["default_folder_path"],
    )

    site = graph.get_site_by_path(SHAREPOINT_HOSTNAME, site_cfg["site_path"])
    if not site or not site.get("id"):
        raise HTTPException(
            status_code=500,
            detail="No se pudo resolver el site de SharePoint.",
        )

    drives = graph.list_site_drives(site["id"])
    print("AVAILABLE DRIVES:", [d.get("name") for d in drives])
    print("TARGET DRIVE NAME:", site_cfg["library_name"])

    target_drive = next(
        (
            d
            for d in drives
            if str(d.get("name", "")).strip().lower()
            == site_cfg["library_name"].strip().lower()
        ),
        None,
    )

    if not target_drive:
        available = [d.get("name") for d in drives]
        raise HTTPException(
            status_code=500,
            detail=(
                f"No se encontró la biblioteca '{site_cfg['library_name']}' en el site. "
                f"Disponibles: {available}"
            ),
        )

    base_folder = None
    folder_path = site_cfg["default_folder_path"]

    if folder_path and folder_path.strip() not in ("", "/"):
        try:
            base_folder = graph.get_drive_item_by_path(
                target_drive["id"],
                folder_path,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo resolver la carpeta base '{folder_path}': {e}",
            )

        if not base_folder.get("is_folder"):
            raise HTTPException(
                status_code=500,
                detail=f"La ruta base '{folder_path}' no es una carpeta válida.",
            )

    return {
        "site_config": site_cfg,
        "site": site,
        "drive": target_drive,
        "base_folder": base_folder,
    }


@app.get("/api/clients")
def api_clients():
    return {
        "ok": True,
        "clients": list(CLIENTS.values()),
        "default_client": "globalevents2" if "globalevents2" in CLIENTS else next(iter(CLIENTS.keys()), None),
    }


@app.get("/api/sharepoint/sites")
def api_sharepoint_sites():
    return {
        "ok": True,
        "hostname": SHAREPOINT_HOSTNAME,
        "sites": [
            {
                "key": cfg["key"],
                "label": cfg["label"],
                "site_path": cfg["site_path"],
                "library_name": cfg["library_name"],
                "default_folder_path": cfg["default_folder_path"],
                "brand_logo": cfg.get("brand_logo"),
                "default_profile": cfg.get("default_profile", "default"),
            }
            for cfg in SHAREPOINT_SITES.values()
        ],
    }


@app.get("/api/profiles")
def api_profiles():
    return {
        "ok": True,
        "profiles": AVAILABLE_PROFILES,
        "default_profile": "default",
    }


@app.post("/api/local/run")
async def api_local_run(
    file: UploadFile = File(...),
    profile: str = Form(""),
    client_key: str = Form(""),
):
    try:
        client_cfg = get_client_config(client_key or None)
        resolved_profile = resolve_profile(
            profile or client_cfg.get("default_profile"),
            site_key=client_cfg.get("site_key"),
        )
        brand_logo = client_cfg.get("brand_logo")

        job_id = str(uuid4())
        jobs_root = Path("work/jobs").resolve()
        job_dir = (jobs_root / job_id).resolve()
        input_dir = (job_dir / "input").resolve()
        input_dir.mkdir(parents=True, exist_ok=True)

        local_excel_path = input_dir / file.filename

        with open(local_excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = run_full_voucher_pipeline(
            job_id=job_id,
            source_excel=local_excel_path,
            jobs_root=jobs_root,
            brand_logo=brand_logo,
            pretty_json=True,
            profile_name=resolved_profile,
        )

        response = result.to_dict()
        response["mode"] = "local"
        response["requested_profile"] = profile
        response["resolved_profile"] = resolved_profile
        response["client_key"] = client_cfg["key"]
        response["client_label"] = client_cfg["label"]
        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando pipeline local: {e}",
        )


@app.get("/api/sharepoint/explore")
def api_sharepoint_explore(
    request: Request,
    folder_id: str | None = None,
    site_key: str | None = None,
):
    access_token = get_graph_access_token_from_session(request)
    graph = GraphSharePointService(access_token)

    try:
        resolved = get_sharepoint_context(graph, site_key=site_key)
        site = resolved["site"]
        drive = resolved["drive"]
        base_folder = resolved["base_folder"]
        site_cfg = resolved["site_config"]

        if folder_id:
            current_folder = graph.get_drive_item(drive["id"], folder_id)
            if not current_folder or not current_folder.get("is_folder"):
                raise HTTPException(status_code=400, detail="La carpeta solicitada no es válida.")
            items = graph.list_drive_children(drive["id"], folder_id)
        else:
            current_folder = base_folder
            if base_folder:
                items = graph.list_drive_children(drive["id"], base_folder["id"])
            else:
                current_folder = graph.get_drive_root(drive["id"])
                items = graph.list_drive_root_children(drive["id"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error explorando SharePoint Graph: {e}",
        )

    folders = [x for x in items if x.get("is_folder")]
    files = [x for x in items if x.get("is_file")]

    return {
        "ok": True,
        "mode": "graph_sharepoint_site",
        "site_key": site_cfg["key"],
        "site_label": site_cfg["label"],
        "default_profile": site_cfg.get("default_profile", "default"),
        "site": site,
        "drive": drive,
        "current_folder": current_folder,
        "items": folders + files,
    }


@app.post("/api/sharepoint/run")
def api_sharepoint_run(payload: SharePointRunRequest, request: Request):
    access_token = get_graph_access_token_from_session(request)
    graph = GraphSharePointService(access_token)

    client_cfg = get_client_config(payload.client_key)

    source_site_key = payload.source_site_key or client_cfg.get("source_site_key") or client_cfg.get("site_key")
    destination_site_key = (
        payload.destination_site_key
        or client_cfg.get("destination_site_key")
        or client_cfg.get("site_key")
        or source_site_key
    )
    resolved_profile = resolve_profile(
        payload.profile or client_cfg.get("default_profile"),
        site_key=source_site_key,
    )

    try:
        source_resolved = get_sharepoint_context(graph, site_key=source_site_key)
        source_site = source_resolved["site"]
        source_drive = source_resolved["drive"]
        source_site_cfg = source_resolved["site_config"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo resolver el site/drive origen de SharePoint: {e}",
        )

    try:
        source_file = graph.get_drive_item(source_drive["id"], payload.source_file_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo leer el archivo origen en SharePoint Graph: {e}",
        )

    if not source_file:
        raise HTTPException(status_code=404, detail="Archivo origen no encontrado.")

    if not source_file.get("is_file"):
        raise HTTPException(
            status_code=400,
            detail="El item seleccionado no es un archivo.",
        )

    source_name = str(source_file.get("name", ""))
    if not source_name.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="El archivo seleccionado no es un Excel válido.",
        )

    destination_folder = None
    destination_site = None
    destination_drive = None
    destination_site_cfg = None

    if payload.destination_folder_id:
        try:
            destination_resolved = get_sharepoint_context(graph, site_key=destination_site_key)
            destination_site = destination_resolved["site"]
            destination_drive = destination_resolved["drive"]
            destination_site_cfg = destination_resolved["site_config"]

            destination_folder = graph.get_drive_item(
                destination_drive["id"],
                payload.destination_folder_id,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo leer la carpeta destino en SharePoint Graph: {e}",
            )

        if not destination_folder:
            raise HTTPException(
                status_code=404,
                detail="Carpeta destino no encontrada.",
            )

        if not destination_folder.get("is_folder"):
            raise HTTPException(
                status_code=400,
                detail="El destino seleccionado no es una carpeta.",
            )

    job_id = str(uuid4())
    jobs_root = Path("work/jobs").resolve()
    job_dir = (jobs_root / job_id).resolve()
    input_dir = (job_dir / "input").resolve()
    input_dir.mkdir(parents=True, exist_ok=True)

    local_excel_path = input_dir / (source_name or "sharepoint_input.xlsx")

    try:
        graph.download_drive_file(source_drive["id"], payload.source_file_id, local_excel_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo descargar el Excel desde SharePoint Graph: {e}",
        )

    brand_logo = client_cfg.get("brand_logo") or source_site_cfg.get("brand_logo")

    try:
        result = run_full_voucher_pipeline(
            job_id=job_id,
            source_excel=local_excel_path,
            jobs_root=jobs_root,
            brand_logo=brand_logo,
            pretty_json=True,
            profile_name=resolved_profile,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando pipeline: {e}",
        )

    response = result.to_dict()

    uploaded_files = []
    uploaded_zip = None

    if destination_folder and destination_drive:
        for file_path_str in response.get("generated_files", []):
            try:
                uploaded = graph.upload_file_to_folder(
                    drive_id=destination_drive["id"],
                    folder_id=destination_folder["id"],
                    local_file_path=Path(file_path_str),
                )
                uploaded_files.append(uploaded)
            except Exception as e:
                uploaded_files.append(
                    {
                        "name": Path(file_path_str).name,
                        "upload_error": str(e),
                    }
                )

        zip_path = response.get("zip_file")
        if zip_path:
            try:
                uploaded_zip = graph.upload_file_to_folder(
                    drive_id=destination_drive["id"],
                    folder_id=destination_folder["id"],
                    local_file_path=Path(zip_path),
                )
            except Exception as e:
                uploaded_zip = {
                    "name": Path(zip_path).name,
                    "upload_error": str(e),
                }

    response["mode"] = "graph_sharepoint_site"
    response["requested_profile"] = payload.profile
    response["resolved_profile"] = resolved_profile
    response["client_key"] = client_cfg["key"]
    response["client_label"] = client_cfg["label"]
    response["source_site_key"] = source_site_cfg["key"]
    response["source_site_label"] = source_site_cfg["label"]
    response["source_site_default_profile"] = source_site_cfg.get("default_profile", "default")
    response["destination_site_key"] = destination_site_cfg["key"] if destination_site_cfg else None
    response["destination_site_label"] = destination_site_cfg["label"] if destination_site_cfg else None
    response["source_site"] = source_site
    response["source_drive"] = source_drive
    response["destination_site"] = destination_site
    response["destination_drive"] = destination_drive
    response["source_file"] = source_file
    response["destination_folder"] = destination_folder
    response["downloaded_excel_path"] = str(local_excel_path)
    response["uploaded_files"] = uploaded_files
    response["uploaded_zip"] = uploaded_zip

    return response