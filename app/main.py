from __future__ import annotations

import json
import os
import httpx
import shutil
import threading
import tempfile
import time
import re
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Query
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
from voucher_generator.profiles import list_profile_configs

load_dotenv()

GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"


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
    {
        "key": p.get("key"),
        "label": p.get("label", p.get("key")),
        "enabled": True,
    }
    for p in list_profile_configs()
]

BASE_WORK_DIR = Path("work/jobs").resolve()
BASE_JOB_STATE_DIR = (Path(tempfile.gettempdir()) / "voucher_job_state").resolve()
BASE_JOB_STATE_DIR.mkdir(parents=True, exist_ok=True)

STEP_DEFINITIONS = [
    {
        "name": "xlsx_to_voucher_json",
        "label": "Generando payload de vouchers",
        "progress_done": 25,
    },
    {
        "name": "enrich_hotels",
        "label": "Enriqueciendo hoteles",
        "progress_done": 50,
    },
    {
        "name": "render_vouchers_html",
        "label": "Renderizando vouchers HTML",
        "progress_done": 75,
    },
    {
        "name": "render_vouchers_pdf",
        "label": "Generando PDFs",
        "progress_done": 95,
    },
]

JOB_STORE: dict[str, dict] = {}
JOB_STORE_LOCK = threading.Lock()

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
    language: str | None = None


def get_session_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user


def get_access_token_from_session(request: Request):
    return request.session.get("access_token")


def validate_graph_access_token(access_token: str) -> bool:
    if not access_token:
        return False

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(
                GRAPH_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        return response.status_code == 200
    except Exception:
        return False


def get_graph_access_token_from_session(request: Request) -> str:
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=401,
            detail="No hay usuario autenticado en sesión. Volvé a iniciar sesión.",
        )

    user_email = user.get("email")
    if not user_email:
        clear_auth_session(request)
        raise HTTPException(
            status_code=401,
            detail="La sesión no tiene email de usuario. Volvé a iniciar sesión.",
        )

    access_token = get_user_token(user_email)
    if not access_token:
        clear_auth_session(request)
        raise HTTPException(
            status_code=401,
            detail="Sesión Microsoft no válida o vencida. Volvé a iniciar sesión.",
        )

    if not validate_graph_access_token(access_token):
        clear_auth_session(request)
        raise HTTPException(
            status_code=401,
            detail="La sesión de Microsoft venció. Volvé a iniciar sesión.",
        )

    return access_token


def clear_auth_session(request: Request):
    request.session.pop("user", None)
    request.session.pop("access_token", None)
    request.session.pop("refresh_token", None)
    request.session.pop("token_expires_at", None)


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


SUPPORTED_LANGUAGES = {"es", "en", "pt"}
DEFAULT_LANGUAGE = "es"


def normalize_language(language: str | None) -> str | None:
    value = (language or "").strip().lower()
    if not value:
        return None
    return value if value in SUPPORTED_LANGUAGES else None


def resolve_language(language: str | None) -> str:
    return normalize_language(language) or DEFAULT_LANGUAGE


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


def _job_state_file(job_id: str) -> Path:
    return (BASE_JOB_STATE_DIR / f"{job_id}.json").resolve()


def _write_job_state(job_id: str) -> None:
    job = JOB_STORE.get(job_id)
    if not job:
        print("WRITE JOB STATE SKIPPED, NOT IN MEMORY:", job_id)
        return

    state_file = _job_state_file(job_id)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(job, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("JOB STATE WRITTEN:", state_file)


def _read_job_state_from_disk(job_id: str) -> dict | None:
    state_file = _job_state_file(job_id)
    print("READ JOB STATE FILE:", state_file)

    if not state_file.exists() or not state_file.is_file():
        print("JOB STATE FILE DOES NOT EXIST:", state_file)
        return None

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        print("JOB STATE FILE LOADED:", job_id)
        return data
    except Exception as e:
        print("ERROR READING JOB STATE FILE:", job_id, e)
        return None


def _build_initial_steps() -> list[dict]:
    steps: list[dict] = []
    for item in STEP_DEFINITIONS:
        steps.append(
            {
                "name": item["name"],
                "label": item["label"],
                "status": "pending",
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "ok": None,
            }
        )
    return steps


def _create_job_record(
    *,
    job_id: str,
    mode: str,
    client_key: str | None = None,
    client_label: str | None = None,
    source_name: str | None = None,
    profile_name: str | None = None,
    language: str | None = None,
) -> None:
    with JOB_STORE_LOCK:
        JOB_STORE[job_id] = {
            "job_id": job_id,
            "mode": mode,
            "status": "pending",
            "progress": 0,
            "progress_label": "Esperando ejecución",
            "current_step": None,
            "steps": _build_initial_steps(),
            "result": None,
            "error": None,
            "client_key": client_key,
            "client_label": client_label,
            "source_name": source_name,
            "profile_name": profile_name,
            "language": language,
            "cancel_requested": False,
            "created_at": time.time(),
            "updated_at": time.time(),
            "_last_persist_ts": 0.0,
        }
        print("JOB CREATED IN MEMORY:", job_id)
        print("JOB STORE KEYS AFTER CREATE:", list(JOB_STORE.keys()))
        _write_job_state(job_id)
        JOB_STORE[job_id]["_last_persist_ts"] = time.time()


def _patch_job(job_id: str, force_persist: bool = False, **values) -> None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return

        job.update(values)
        now = time.time()
        job["updated_at"] = now

        last_persist = job.get("_last_persist_ts", 0.0)

        if force_persist or (now - last_persist > 0.5):
            _write_job_state(job_id)
            job["_last_persist_ts"] = now


def _is_job_cancel_requested(job_id: str) -> bool:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return False
        return bool(job.get("cancel_requested", False))


def _mark_job_cancelled(job_id: str, progress_label: str = "Ejecución cancelada") -> None:
    _patch_job(
        job_id,
        status="cancelled",
        progress=0,
        progress_label=progress_label,
        current_step=None,
        force_persist=True,
    )


def _get_job(job_id: str) -> dict | None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if job:
            print("JOB FOUND IN MEMORY:", job_id)
            return json.loads(json.dumps(job))

    print("JOB NOT IN MEMORY, TRY DISK:", job_id)
    disk_job = _read_job_state_from_disk(job_id)
    if disk_job:
        print("JOB RECOVERED FROM DISK:", job_id)
        with JOB_STORE_LOCK:
            JOB_STORE[job_id] = disk_job
        return disk_job

    print("JOB NOT FOUND ANYWHERE:", job_id)
    return None


def _job_history_summary(job: dict) -> dict:
    result = job.get("result") or {}
    generated_files = result.get("generated_files") or []
    zip_file = result.get("zip_file")

    return {
        "job_id": job.get("job_id"),
        "mode": job.get("mode"),
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "progress_label": job.get("progress_label"),
        "current_step": job.get("current_step"),
        "client_key": job.get("client_key"),
        "client_label": job.get("client_label"),
        "source_name": job.get("source_name"),
        "profile_name": job.get("profile_name"),
        "language": job.get("language"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "has_result": bool(result),
        "has_zip": bool(zip_file),
        "zip_file": zip_file,
        "generated_files_count": len(generated_files),
        "error": job.get("error"),
    }


def _list_jobs(limit: int = 20) -> list[dict]:
    combined: dict[str, dict] = {}

    with JOB_STORE_LOCK:
        for job_id, job in JOB_STORE.items():
            combined[job_id] = json.loads(json.dumps(job))

    for state_file in BASE_JOB_STATE_DIR.glob("*.json"):
        try:
            disk_job = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        job_id = str(disk_job.get("job_id") or state_file.stem)
        memory_job = combined.get(job_id)

        if not memory_job or float(disk_job.get("updated_at") or 0) > float(memory_job.get("updated_at") or 0):
            combined[job_id] = disk_job

    jobs = sorted(
        (_job_history_summary(job) for job in combined.values()),
        key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0),
        reverse=True,
    )

    safe_limit = max(1, min(int(limit or 20), 100))
    return jobs[:safe_limit]


def _set_job_steps_from_result(job_id: str, result_steps: list[dict]) -> None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        job["steps"] = result_steps
        job["updated_at"] = time.time()
        _write_job_state(job_id)


def _sync_job_progress_from_outputs(job_id: str, job_dir: Path) -> None:
    payload_json = job_dir / "voucher_payloads.json"
    enriched_json = job_dir / "voucher_payloads_enriched.json"
    html_dir = job_dir / "rendered_vouchers"
    pdf_dir = job_dir / "rendered_pdfs"

    html_ready = html_dir.exists() and any(html_dir.rglob("*.html"))
    pdf_ready = pdf_dir.exists() and any(pdf_dir.rglob("*.pdf"))

    if payload_json.exists():
        steps_status = ["done", "running", "pending", "pending"]
        progress = 25
        current_label = STEP_DEFINITIONS[1]["label"]
        current_step = STEP_DEFINITIONS[1]["name"]
    else:
        steps_status = ["running", "pending", "pending", "pending"]
        progress = 12
        current_label = STEP_DEFINITIONS[0]["label"]
        current_step = STEP_DEFINITIONS[0]["name"]

    if enriched_json.exists():
        steps_status = ["done", "done", "running", "pending"]
        progress = 50
        current_label = STEP_DEFINITIONS[2]["label"]
        current_step = STEP_DEFINITIONS[2]["name"]

    if html_ready:
        steps_status = ["done", "done", "done", "running"]
        progress = 75
        current_label = STEP_DEFINITIONS[3]["label"]
        current_step = STEP_DEFINITIONS[3]["name"]

    if pdf_ready:
        steps_status = ["done", "done", "done", "done"]
        progress = 95
        current_label = "Finalizando pipeline"
        current_step = STEP_DEFINITIONS[3]["name"]

    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job or job.get("status") not in {"pending", "running"}:
            return

        for idx, status in enumerate(steps_status):
            job["steps"][idx]["status"] = status

        job["status"] = "running"
        job["progress"] = progress
        job["progress_label"] = current_label
        job["current_step"] = current_step
        job["updated_at"] = time.time()
        _write_job_state(job_id)


def _monitor_job_outputs(job_id: str, job_dir: Path, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        if _is_job_cancel_requested(job_id):
            return
        _sync_job_progress_from_outputs(job_id, job_dir)
        time.sleep(0.6)

    if not _is_job_cancel_requested(job_id):
        _sync_job_progress_from_outputs(job_id, job_dir)


def _run_local_job_async(
    *,
    job_id: str,
    source_excel: Path,
    jobs_root: Path,
    brand_logo: str | None,
    profile_name: str,
    language: str,
    client_cfg: dict,
) -> None:
    job_dir = (jobs_root / job_id).resolve()
    stop_event = threading.Event()
    monitor = threading.Thread(
        target=_monitor_job_outputs,
        args=(job_id, job_dir, stop_event),
        daemon=True,
    )

    try:
        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        _patch_job(
            job_id,
            status="running",
            progress=8,
            progress_label="Preparando pipeline local",
            current_step="preparing_local_job",
        )

        monitor.start()

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        result = run_full_voucher_pipeline(
            job_id=job_id,
            source_excel=source_excel,
            jobs_root=jobs_root,
            brand_logo=brand_logo,
            pretty_json=True,
            profile_name=profile_name,
            language=language,
        )

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        response = result.to_dict()
        response["mode"] = "local"
        response["requested_profile"] = profile_name
        response["resolved_profile"] = profile_name
        response["client_key"] = client_cfg["key"]
        response["client_label"] = client_cfg["label"]
        response["requested_language"] = normalize_language(language)
        response["resolved_language"] = language
        response["language"] = response.get("language") or language
        response["profile_used"] = response.get("profile_used") or profile_name

        result_steps = []
        for step in response.get("steps", []):
            step_copy = dict(step)
            step_copy["status"] = "done" if step_copy.get("ok") else "error"
            result_steps.append(step_copy)

        _set_job_steps_from_result(job_id, result_steps)

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        _patch_job(
            job_id,
            status="success" if result.ok else "error",
            progress=100,
            progress_label="Pipeline finalizado" if result.ok else "Pipeline con error",
            current_step=None,
            result=response,
            error=response.get("error"),
            force_persist=True,
        )

    except Exception as e:
        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
        else:
            _patch_job(
                job_id,
                status="error",
                progress=100,
                progress_label="Pipeline con error",
                current_step=None,
                error=str(e),
                force_persist=True,
            )

    finally:
        stop_event.set()
        monitor.join(timeout=1.5)


def _run_sharepoint_job_async(
    *,
    job_id: str,
    access_token: str,
    payload: SharePointRunRequest,
    client_cfg: dict,
    source_site_key: str | None,
    destination_site_key: str | None,
    resolved_profile: str,
    resolved_language: str,
) -> None:
    jobs_root = Path("work/jobs").resolve()
    job_dir = (jobs_root / job_id).resolve()
    input_dir = (job_dir / "input").resolve()
    input_dir.mkdir(parents=True, exist_ok=True)

    stop_event = threading.Event()
    monitor_thread = None

    try:
        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        graph = GraphSharePointService(access_token)

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        _patch_job(
            job_id,
            status="running",
            progress=6,
            progress_label="Preparando pipeline SharePoint",
            current_step="preparing_sharepoint_job",
        )

        source_resolved = get_sharepoint_context(graph, site_key=source_site_key)
        source_site = source_resolved["site"]
        source_drive = source_resolved["drive"]
        source_site_cfg = source_resolved["site_config"]

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        _patch_job(
            job_id,
            progress=10,
            progress_label="Leyendo archivo origen desde SharePoint",
            current_step="loading_sharepoint_source",
        )

        source_file = graph.get_drive_item(source_drive["id"], payload.source_file_id)
        if not source_file:
            raise RuntimeError("Archivo origen no encontrado.")

        if not source_file.get("is_file"):
            raise RuntimeError("El item seleccionado no es un archivo.")

        source_name = str(source_file.get("name", ""))
        if not source_name.lower().endswith((".xlsx", ".xlsm", ".xls")):
            raise RuntimeError("El archivo seleccionado no es un Excel válido.")

        local_excel_path = input_dir / (source_name or "sharepoint_input.xlsx")
        graph.download_drive_file(source_drive["id"], payload.source_file_id, local_excel_path)

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        _patch_job(
            job_id,
            source_name=source_name,
            profile_name=resolved_profile,
            language=resolved_language,
        )

        destination_folder = None
        destination_site = None
        destination_drive = None
        destination_site_cfg = None

        if payload.destination_folder_id:
            destination_resolved = get_sharepoint_context(graph, site_key=destination_site_key)
            destination_site = destination_resolved["site"]
            destination_drive = destination_resolved["drive"]
            destination_site_cfg = destination_resolved["site_config"]

            destination_folder = graph.get_drive_item(
                destination_drive["id"],
                payload.destination_folder_id,
            )

            if not destination_folder:
                raise RuntimeError("Carpeta destino no encontrada.")

            if not destination_folder.get("is_folder"):
                raise RuntimeError("El destino seleccionado no es una carpeta.")

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        brand_logo = client_cfg.get("brand_logo") or source_site_cfg.get("brand_logo")

        monitor_thread = threading.Thread(
            target=_monitor_job_outputs,
            args=(job_id, job_dir, stop_event),
            daemon=True,
        )
        monitor_thread.start()

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        result = run_full_voucher_pipeline(
            job_id=job_id,
            source_excel=local_excel_path,
            jobs_root=jobs_root,
            brand_logo=brand_logo,
            pretty_json=True,
            profile_name=resolved_profile,
            language=resolved_language,
        )

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        response = result.to_dict()

        uploaded_files = []
        uploaded_zip = None

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        if destination_folder and destination_drive:
            _patch_job(
                job_id,
                progress=98,
                progress_label="Subiendo resultado a SharePoint",
                current_step="uploading_outputs",
            )

            for file_path_str in response.get("generated_files", []):
                if _is_job_cancel_requested(job_id):
                    _mark_job_cancelled(job_id)
                    return

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
                if _is_job_cancel_requested(job_id):
                    _mark_job_cancelled(job_id)
                    return

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
        response["requested_language"] = normalize_language(payload.language)
        response["resolved_language"] = resolved_language
        response["language"] = response.get("language") or resolved_language
        response["profile_used"] = response.get("profile_used") or resolved_profile
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

        result_steps = []
        for step in response.get("steps", []):
            step_copy = dict(step)
            step_copy["status"] = "done" if step_copy.get("ok") else "error"
            result_steps.append(step_copy)

        _set_job_steps_from_result(job_id, result_steps)

        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
            return

        _patch_job(
            job_id,
            status="success" if result.ok else "error",
            progress=100,
            progress_label="Pipeline finalizado" if result.ok else "Pipeline con error",
            current_step=None,
            result=response,
            error=response.get("error"),
            force_persist=True,
        )

    except Exception as e:
        if _is_job_cancel_requested(job_id):
            _mark_job_cancelled(job_id)
        else:
            _patch_job(
                job_id,
                status="error",
                progress=100,
                progress_label="Pipeline con error",
                current_step=None,
                error=str(e),
                force_persist=True,
            )
    finally:
        stop_event.set()
        if monitor_thread:
            monitor_thread.join(timeout=1.5)


@app.get("/api/preview")
def preview_file(path: str = Query(...)):
    try:
        file_path = Path(path).resolve()

        if not str(file_path).startswith(str(BASE_WORK_DIR)):
            raise HTTPException(status_code=403, detail="Acceso no permitido")

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="HTML no encontrado")

        if file_path.suffix.lower() != ".html":
            raise HTTPException(status_code=400, detail="Solo se permite preview de HTML")

        return FileResponse(file_path, media_type="text/html")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/history")
def api_job_history(limit: int = Query(20, ge=1, le=100)):
    jobs = _list_jobs(limit=limit)
    return {
        "ok": True,
        "jobs": jobs,
        "count": len(jobs),
    }


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return {"ok": True, **job}


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel_job(job_id: str):
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job no encontrado")

        if job.get("status") in {"success", "error", "cancelled"}:
            return {"ok": True, "job_id": job_id, "status": job.get("status")}

        job["cancel_requested"] = True
        job["status"] = "cancelling"
        job["progress_label"] = "Cancelando ejecución..."
        job["updated_at"] = time.time()

    _write_job_state(job_id)

    return {"ok": True, "job_id": job_id, "status": "cancelling"}


@app.get("/api/clients")
def api_clients():
    return {
        "ok": True,
        "clients": list(CLIENTS.values()),
        "default_client": "globalevents2" if "globalevents2" in CLIENTS else next(iter(CLIENTS.keys()), None),
    }

@app.get("/api/hotel-logos")
def api_hotel_logos():
    try:
        registry_path = Path("voucher_generator/config/hotel_logo_registry.json")

        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            if not isinstance(registry, dict):
                registry = {}
        else:
            registry = {}

        items = [
            {
                "hotel_name": hotel_name,
                "logo_path": logo_path,
            }
            for hotel_name, logo_path in sorted(registry.items(), key=lambda item: str(item[0]).lower())
        ]

        return {
            "ok": True,
            "items": items,
            "count": len(items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hotel-logos/upload")
async def upload_hotel_logo(
    hotel_name: str = Form(...),
    file: UploadFile = File(...),
    overwrite: str = Form("false"),
):
    try:
        normalized = hotel_name.strip().lower()
        if not normalized:
            raise HTTPException(status_code=400, detail="El nombre del hotel es obligatorio.")

        slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        if not slug:
            raise HTTPException(status_code=400, detail="Nombre de hotel inválido.")

        overwrite_bool = str(overwrite).strip().lower() == "true"

        logos_dir = Path("voucher_generator/assets/logos/hotels")
        logos_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(file.filename or "").suffix.lower() or ".png"
        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            raise HTTPException(status_code=400, detail="Formato de archivo no permitido.")

        filename = f"{slug}{ext}"
        file_path = logos_dir / filename

        registry_path = Path("voucher_generator/config/hotel_logo_registry.json")

        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            if not isinstance(registry, dict):
                registry = {}
        else:
            registry = {}

        already_exists = normalized in registry
        if already_exists and not overwrite_bool:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un logo registrado para '{normalized}'.",
            )

        old_path = registry.get(normalized)
        if old_path:
            old_file = Path("voucher_generator") / old_path
            if old_file.exists() and old_file.is_file():
                try:
                    if old_file.resolve() != file_path.resolve():
                        old_file.unlink()
                except Exception:
                    pass

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        registry[normalized] = f"assets/logos/hotels/{filename}"

        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "hotel_name": normalized,
            "logo_path": registry[normalized],
            "overwritten": already_exists,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def is_graph_session_valid(request: Request) -> bool:
    user = get_session_user(request)
    if not user:
        return False

    user_email = user.get("email")
    if not user_email:
        return False

    access_token = get_user_token(user_email)
    if not access_token:
        return False

    return validate_graph_access_token(access_token)


@app.get("/auth/session-status")
def auth_session_status(request: Request):
    user = get_session_user(request)
    if not user:
        return {
            "authenticated": False,
            "reason": "no_session",
        }

    valid = is_graph_session_valid(request)
    if not valid:
        clear_auth_session(request)
        return {
            "authenticated": False,
            "reason": "expired",
        }

    return {
        "authenticated": True,
        "user": {
            "name": user.get("name"),
            "email": user.get("email"),
        },
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


@app.get("/api/download-zip")
def download_zip(path: str = Query(...)):
    try:
        file_path = Path(path).resolve()

        if not str(file_path).startswith(str(BASE_WORK_DIR)):
            raise HTTPException(status_code=403, detail="Acceso no permitido")

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="ZIP no encontrado")

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/zip",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-file")
def download_file(path: str = Query(...)):
    try:
        file_path = Path(path).resolve()

        if not str(file_path).startswith(str(BASE_WORK_DIR)):
            return {"ok": False, "error": "Acceso no permitido"}

        if not file_path.exists() or not file_path.is_file():
            return {"ok": False, "error": "Archivo inválido"}

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream"
        )

    except Exception as e:
        return {"ok": False, "error": str(e)}


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
    language: str = Form(""),
):
    try:
        client_cfg = get_client_config(client_key or None)
        resolved_profile = resolve_profile(
            profile or client_cfg.get("default_profile"),
            site_key=client_cfg.get("site_key"),
        )
        brand_logo = client_cfg.get("brand_logo")
        resolved_language = resolve_language(language)

        job_id = str(uuid4())
        jobs_root = BASE_WORK_DIR
        job_dir = (jobs_root / job_id).resolve()
        input_dir = (job_dir / "input").resolve()
        input_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename or "input.xlsx"
        local_excel_path = input_dir / filename

        with open(local_excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        _create_job_record(
            job_id=job_id,
            mode="local",
            client_key=client_cfg["key"],
            client_label=client_cfg["label"],
            source_name=filename,
            profile_name=resolved_profile,
            language=resolved_language,
        )

        worker = threading.Thread(
            target=_run_local_job_async,
            kwargs={
                "job_id": job_id,
                "source_excel": local_excel_path,
                "jobs_root": jobs_root,
                "brand_logo": brand_logo,
                "profile_name": resolved_profile,
                "language": resolved_language,
                "client_cfg": client_cfg,
            },
            daemon=True,
        )
        worker.start()

        return {
            "ok": True,
            "job_id": job_id,
            "mode": "local",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error iniciando pipeline local: {e}",
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
    resolved_language = resolve_language(payload.language)

    job_id = str(uuid4())

    _create_job_record(
        job_id=job_id,
        mode="graph_sharepoint_site",
        client_key=client_cfg["key"],
        client_label=client_cfg["label"],
        source_name=None,
        profile_name=resolved_profile,
        language=resolved_language,
    )

    worker = threading.Thread(
        target=_run_sharepoint_job_async,
        kwargs={
            "job_id": job_id,
            "access_token": access_token,
            "payload": payload,
            "client_cfg": client_cfg,
            "source_site_key": source_site_key,
            "destination_site_key": destination_site_key,
            "resolved_profile": resolved_profile,
            "resolved_language": resolved_language,
        },
        daemon=True,
    )
    worker.start()

    return {
        "ok": True,
        "job_id": job_id,
        "mode": "graph_sharepoint_site",
    }


@app.on_event("startup")
def debug_routes():
    print("=== ROUTES LOADED ===")
    for route in app.routes:
        try:
            print(route.path)
        except Exception:
            pass