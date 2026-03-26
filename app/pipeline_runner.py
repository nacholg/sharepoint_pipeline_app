from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from app.config import settings


@dataclass
class PipelineStepResult:
    name: str
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    ok: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineRunResult:
    ok: bool
    job_id: str
    working_dir: str
    input_file: str
    steps: List[PipelineStepResult] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    zip_file: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _zip_folder(folder: Path, zip_path: Path) -> Optional[Path]:
    if not folder.exists():
        return None

    files = [
        p for p in folder.rglob("*")
        if p.is_file() and p.resolve() != zip_path.resolve()
    ]
    if not files:
        return None

    _ensure_dir(zip_path.parent)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = file_path.relative_to(folder)
            zf.write(file_path, arcname)

    return zip_path


def _run_step(
    name: str,
    command: List[str],
    cwd: Path,
    timeout_seconds: int = 1200,
) -> PipelineStepResult:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        timeout=timeout_seconds,
        shell=False,
        env=env,
    )

    return PipelineStepResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        ok=completed.returncode == 0,
    )


def _copy_input_excel(source_excel: Path, job_dir: Path) -> Path:
    source_excel = source_excel.resolve()
    job_dir = job_dir.resolve()

    _ensure_dir(job_dir)
    dest = (job_dir / source_excel.name).resolve()
    shutil.copy2(source_excel, dest)
    return dest


def _collect_outputs(job_dir: Path) -> List[str]:
    wanted: List[Path] = []

    for name in [
        "voucher_payloads.json",
        "voucher_payloads_enriched.json",
        "hotel_cache.json",
    ]:
        p = job_dir / name
        if p.exists():
            wanted.append(p)

    html_dir = job_dir / "rendered_vouchers"
    pdf_dir = job_dir / "rendered_pdfs"

    if html_dir.exists():
        wanted.extend([p for p in html_dir.rglob("*") if p.is_file()])

    if pdf_dir.exists():
        wanted.extend([p for p in pdf_dir.rglob("*") if p.is_file()])

    return sorted(str(p.resolve()) for p in wanted)


def run_full_voucher_pipeline(
    *,
    job_id: str,
    source_excel: Path,
    jobs_root: Optional[Path] = None,
    brand_logo: Optional[str] = None,
    profile_name: Optional[str] = None,
    profile: Optional[str] = None,
    pretty_json: bool = True,
) -> PipelineRunResult:
    if profile_name is None and profile is not None:
        profile_name = profile

    project_root = Path(__file__).resolve().parent.parent
    generator_root = project_root / "voucher_generator"
    python_exe = Path(sys.executable)

    if jobs_root is None:
        jobs_root = project_root / settings.JOBS_ROOT
    else:
        jobs_root = Path(jobs_root)

    jobs_root = jobs_root.resolve()
    _ensure_dir(jobs_root)

    logos_dir = (generator_root / "assets" / "logos").resolve()

    if not generator_root.exists():
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(generator_root),
            input_file=str(source_excel),
            error=f"voucher_generator no existe: {generator_root}",
        )

    if not logos_dir.exists():
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(generator_root),
            input_file=str(source_excel),
            error=f"No existe la carpeta de logos: {logos_dir}",
        )

    if not source_excel.exists():
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(generator_root),
            input_file=str(source_excel),
            error=f"Excel de entrada no existe: {source_excel}",
        )

    job_dir = (jobs_root / job_id).resolve()
    _ensure_dir(job_dir)

    local_excel = _copy_input_excel(source_excel.resolve(), job_dir).resolve()

    payload_json = (job_dir / "voucher_payloads.json").resolve()
    enriched_json = (job_dir / "voucher_payloads_enriched.json").resolve()
    hotel_cache = (job_dir / "hotel_cache.json").resolve()
    rendered_html_dir = (job_dir / "rendered_vouchers").resolve()
    rendered_pdf_dir = (job_dir / "rendered_pdfs").resolve()

    steps: List[PipelineStepResult] = []

    cmd_1 = [
        str(python_exe),
        "-m",
        "voucher_generator.xlsx_to_voucher_json",
        str(local_excel),
        "-o",
        str(payload_json),
    ]
    if pretty_json:
        cmd_1.append("--pretty")
    if profile_name:
        cmd_1.extend(["--profile", profile_name])

    step_1 = _run_step("xlsx_to_voucher_json", cmd_1, cwd=project_root)
    steps.append(step_1)
    if not step_1.ok:
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(job_dir),
            input_file=str(local_excel),
            steps=steps,
            generated_files=_collect_outputs(job_dir),
            error="Falló xlsx_to_voucher_json.py",
        )

    cmd_2 = [
        str(python_exe),
        "-m",
        "voucher_generator.enrich_hotels",
        str(payload_json),
        "-o",
        str(enriched_json),
        "--cache",
        str(hotel_cache),
        "--logos-dir",
        str(logos_dir),
    ]

    step_2 = _run_step("enrich_hotels", cmd_2, cwd=project_root)
    steps.append(step_2)
    if not step_2.ok:
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(job_dir),
            input_file=str(local_excel),
            steps=steps,
            generated_files=_collect_outputs(job_dir),
            error="Falló enrich_hotels.py",
        )

    cmd_3 = [
        str(python_exe),
        "-m",
        "voucher_generator.render_vouchers_html",
        str(enriched_json),
        "-o",
        str(rendered_html_dir),
    ]

    if profile_name:
        cmd_3.extend(["--profile", profile_name])

    logo_to_use = brand_logo  # solo override explícito
    if logo_to_use:
        logo_path = Path(logo_to_use)
        if (
            not logo_path.is_absolute()
            and not str(logo_to_use).startswith(("http://", "https://", "data:"))
        ):
            logo_path = (generator_root / logo_path).resolve()
        cmd_3.extend(["--brand-logo", str(logo_path)])
        
    step_3 = _run_step("render_vouchers_html", cmd_3, cwd=project_root)
    steps.append(step_3)
    if not step_3.ok:
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(job_dir),
            input_file=str(local_excel),
            steps=steps,
            generated_files=_collect_outputs(job_dir),
            error="Falló render_vouchers_html.py",
        )

    cmd_4 = [
        str(python_exe),
        "-m",
        "voucher_generator.render_vouchers_pdf",
        str(rendered_html_dir),
        "-o",
        str(rendered_pdf_dir),
    ]

    step_4 = _run_step("render_vouchers_pdf", cmd_4, cwd=project_root)
    steps.append(step_4)
    if not step_4.ok:
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(job_dir),
            input_file=str(local_excel),
            steps=steps,
            generated_files=_collect_outputs(job_dir),
            error="Falló render_vouchers_pdf.py",
        )

    generated_files = _collect_outputs(job_dir)

    zip_path = job_dir / "artifacts.zip"
    created_zip = _zip_folder(job_dir, zip_path)

    return PipelineRunResult(
        ok=True,
        job_id=job_id,
        working_dir=str(job_dir),
        input_file=str(local_excel),
        steps=steps,
        generated_files=generated_files,
        zip_file=str(created_zip.resolve()) if created_zip else None,
        error=None,
    )