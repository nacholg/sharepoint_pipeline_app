from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.pipeline_runner import run_full_voucher_pipeline

router = APIRouter(prefix="/api", tags=["jobs"])


import subprocess


router = APIRouter(prefix="/api", tags=["jobs"])

class LocalRunRequest(BaseModel):
    local_excel_path: str
    brand_logo: str | None = None


@router.post("/run-local")
def run_local_job(payload: LocalRunRequest):
    input_file = Path(payload.local_excel_path).resolve()

    if not input_file.exists():
        raise HTTPException(status_code=400, detail=f"No existe el archivo: {input_file}")

    job_id = str(uuid4())
    jobs_root = Path("work/jobs").resolve()
    jobs_root.mkdir(parents=True, exist_ok=True)

    result = run_full_voucher_pipeline(
        job_id=job_id,
        source_excel=input_file,
        jobs_root=jobs_root,
        brand_logo=payload.brand_logo,
        pretty_json=True,
    )

    return result.to_dict()


@router.get("/download-zip/{job_id}")
def download_zip(job_id: str):
    zip_path = (Path("work/jobs").resolve() / job_id / "artifacts.zip").resolve()

    print("DOWNLOAD ZIP PATH:", zip_path)
    print("ZIP EXISTS:", zip_path.exists())

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP no encontrado")

    return FileResponse(
        path=zip_path,
        filename=zip_path.name,
        media_type="application/zip",
    )

class LocalRunRequest(BaseModel):
    local_excel_path: str
    brand_logo: str | None = None


@router.post("/run-local")
def run_local_job(payload: LocalRunRequest):
    input_file = Path(payload.local_excel_path).resolve()

    if not input_file.exists():
        raise HTTPException(status_code=400, detail=f"No existe el archivo: {input_file}")

    job_id = str(uuid4())
    jobs_root = Path("work/jobs").resolve()
    jobs_root.mkdir(parents=True, exist_ok=True)

    result = run_full_voucher_pipeline(
        job_id=job_id,
        source_excel=input_file,
        jobs_root=jobs_root,
        brand_logo=payload.brand_logo,
        pretty_json=True,
    )

    return result.to_dict()


@router.get("/download-zip/{job_id}")
def download_zip(job_id: str):
    zip_path = (Path("work/jobs").resolve() / job_id / "artifacts.zip").resolve()

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP no encontrado")

    return FileResponse(
        path=zip_path,
        filename=zip_path.name,
        media_type="application/zip",
    )


@router.post("/open-job-folder/{job_id}")
def open_job_folder(job_id: str):
    job_dir = (Path("work/jobs").resolve() / job_id).resolve()

    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Carpeta del job no encontrada")

    subprocess.Popen(["explorer", str(job_dir)])
    return {"ok": True, "job_dir": str(job_dir)}