from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.pipeline_runner import run_full_voucher_pipeline
from app.routes.auth_routes import router as auth_router
from app.routes.jobs import router as jobs_router
from app.routes.ui import router as ui_router
from app.services.sharepoint_graph import GraphSharePointService
from app.token_store import get_user_token


load_dotenv()

SHAREPOINT_HOSTNAME = os.getenv("SHAREPOINT_HOSTNAME", "patagonik.sharepoint.com")
SHAREPOINT_SITE_PATH = os.getenv("SHAREPOINT_SITE_PATH", "/sites/GLOBALEVENTS2")
SHAREPOINT_LIBRARY_NAME = os.getenv("SHAREPOINT_LIBRARY_NAME", "Documentos")
SHAREPOINT_FOLDER_PATH = os.getenv("SHAREPOINT_FOLDER_PATH", "/General")


app = FastAPI(title="Voucher Generator")
app.add_middleware(SessionMiddleware, secret_key=settings.APP_SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(ui_router)
app.include_router(auth_router)
app.include_router(jobs_router)


class SharePointRunRequest(BaseModel):
    source_file_id: str
    destination_folder_id: str | None = None


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


def get_sharepoint_context(graph: GraphSharePointService) -> dict:
    print(
        "SP CONFIG:",
        SHAREPOINT_HOSTNAME,
        SHAREPOINT_SITE_PATH,
        SHAREPOINT_LIBRARY_NAME,
        SHAREPOINT_FOLDER_PATH,
    )

    site = graph.get_site_by_path(SHAREPOINT_HOSTNAME, SHAREPOINT_SITE_PATH)
    if not site or not site.get("id"):
        raise HTTPException(
            status_code=500,
            detail="No se pudo resolver el site de SharePoint.",
        )

    drives = graph.list_site_drives(site["id"])
    print("AVAILABLE DRIVES:", [d.get("name") for d in drives])
    print("TARGET DRIVE NAME:", SHAREPOINT_LIBRARY_NAME)

    target_drive = next(
        (
            d
            for d in drives
            if str(d.get("name", "")).strip().lower()
            == SHAREPOINT_LIBRARY_NAME.strip().lower()
        ),
        None,
    )

    if not target_drive:
        available = [d.get("name") for d in drives]
        raise HTTPException(
            status_code=500,
            detail=(
                f"No se encontró la biblioteca '{SHAREPOINT_LIBRARY_NAME}' en el site. "
                f"Disponibles: {available}"
            ),
        )

    base_folder = None
    if SHAREPOINT_FOLDER_PATH and SHAREPOINT_FOLDER_PATH.strip() not in ("", "/"):
        try:
            base_folder = graph.get_drive_item_by_path(
                target_drive["id"],
                SHAREPOINT_FOLDER_PATH,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo resolver la carpeta base '{SHAREPOINT_FOLDER_PATH}': {e}",
            )

        if not base_folder.get("is_folder"):
            raise HTTPException(
                status_code=500,
                detail=f"La ruta base '{SHAREPOINT_FOLDER_PATH}' no es una carpeta válida.",
            )

    return {
        "site": site,
        "drive": target_drive,
        "base_folder": base_folder,
    }


@app.get("/api/sharepoint/explore")
def api_sharepoint_explore(request: Request, folder_id: str | None = None):
    access_token = get_graph_access_token_from_session(request)
    graph = GraphSharePointService(access_token)

    try:
        resolved = get_sharepoint_context(graph)
        site = resolved["site"]
        drive = resolved["drive"]
        base_folder = resolved["base_folder"]

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
        "site": site,
        "drive": drive,
        "current_folder": current_folder,
        "items": folders + files,
    }


@app.post("/api/sharepoint/run")
def api_sharepoint_run(payload: SharePointRunRequest, request: Request):
    access_token = get_graph_access_token_from_session(request)
    graph = GraphSharePointService(access_token)

    try:
        resolved = get_sharepoint_context(graph)
        site = resolved["site"]
        drive = resolved["drive"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo resolver el site/drive de SharePoint: {e}",
        )

    try:
        source_file = graph.get_drive_item(drive["id"], payload.source_file_id)
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
    if not source_name.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail="El archivo seleccionado no es un Excel válido.",
        )

    destination_folder = None
    if payload.destination_folder_id:
        try:
            destination_folder = graph.get_drive_item(
                drive["id"],
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
        graph.download_drive_file(drive["id"], payload.source_file_id, local_excel_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo descargar el Excel desde SharePoint Graph: {e}",
        )

    try:
        result = run_full_voucher_pipeline(
            job_id=job_id,
            source_excel=local_excel_path,
            jobs_root=jobs_root,
            brand_logo=None,
            pretty_json=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando pipeline: {e}",
        )

    response = result.to_dict()

    uploaded_files = []
    uploaded_zip = None

    if destination_folder:
        for file_path_str in response.get("generated_files", []):
            try:
                uploaded = graph.upload_file_to_folder(
                    drive_id=drive["id"],
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
                    drive_id=drive["id"],
                    folder_id=destination_folder["id"],
                    local_file_path=Path(zip_path),
                )
            except Exception as e:
                uploaded_zip = {
                    "name": Path(zip_path).name,
                    "upload_error": str(e),
                }

    response["mode"] = "graph_sharepoint_site"
    response["site"] = site
    response["drive"] = drive
    response["source_file"] = source_file
    response["destination_folder"] = destination_folder
    response["downloaded_excel_path"] = str(local_excel_path)
    response["uploaded_files"] = uploaded_files
    response["uploaded_zip"] = uploaded_zip

    return response