from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, List, Optional

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

    profile_used: Optional[str] = None
    pipeline_summary: Optional[dict[str, Any]] = None
    warnings_file: Optional[str] = None
    errors_file: Optional[str] = None
    rows_file: Optional[str] = None
    summary_file: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_read_json(path: Path) -> Optional[dict[str, Any] | list[Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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
    _ensure_dir(job_dir)
    dest = job_dir / source_excel.name
    shutil.copy2(source_excel, dest)
    return dest


def _collect_outputs(job_dir: Path) -> List[str]:
    wanted: List[Path] = []

    for name in [
        "voucher_payloads.json",
        "voucher_payloads_enriched.json",
        "hotel_cache.json",
        "voucher_payloads.rows.json",
        "voucher_payloads.warnings.json",
        "voucher_payloads.errors.json",
        "voucher_payloads.summary.json",
    ]:
        p = job_dir / name
        if p.exists():
            wanted.append(p)

    for folder in ["rendered_vouchers", "rendered_pdfs"]:
        d = job_dir / folder
        if d.exists():
            wanted.extend([p for p in d.rglob("*") if p.is_file()])

    return sorted(str(p.resolve()) for p in wanted)


def _build_result(
    *,
    ok: bool,
    job_id: str,
    working_dir: Path,
    input_file: Path,
    steps: List[PipelineStepResult],
    job_dir: Path,
    profile: str,
    error: Optional[str] = None,
    zip_file: Optional[Path] = None,
) -> PipelineRunResult:
    summary_json = job_dir / "voucher_payloads.summary.json"
    warnings_json = job_dir / "voucher_payloads.warnings.json"
    errors_json = job_dir / "voucher_payloads.errors.json"
    rows_json = job_dir / "voucher_payloads.rows.json"

    return PipelineRunResult(
        ok=ok,
        job_id=job_id,
        working_dir=str(working_dir),
        input_file=str(input_file),
        steps=steps,
        generated_files=_collect_outputs(job_dir),
        zip_file=str(zip_file) if zip_file and zip_file.exists() else None,
        error=error,
        profile_used=profile,
        pipeline_summary=_safe_read_json(summary_json),
        warnings_file=str(warnings_json) if warnings_json.exists() else None,
        errors_file=str(errors_json) if errors_json.exists() else None,
        rows_file=str(rows_json) if rows_json.exists() else None,
        summary_file=str(summary_json) if summary_json.exists() else None,
    )


def run_full_voucher_pipeline(
    *,
    job_id: str,
    source_excel: Path,
    jobs_root: Optional[Path] = None,
    brand_logo: Optional[str] = None,
    pretty_json: bool = True,
    profile: str = "default",
) -> PipelineRunResult:

    project_root = Path(__file__).resolve().parent.parent
    generator_root = project_root / "voucher_generator"
    python_exe = Path(sys.executable)

    if jobs_root is None:
        jobs_root = project_root / settings.JOBS_ROOT

    job_dir = jobs_root / job_id
    _ensure_dir(job_dir)

    local_excel = _copy_input_excel(source_excel, job_dir)

    payload_json = job_dir / "voucher_payloads.json"
    enriched_json = job_dir / "voucher_payloads_enriched.json"
    hotel_cache = job_dir / "hotel_cache.json"
    html_dir = job_dir / "rendered_vouchers"
    pdf_dir = job_dir / "rendered_pdfs"

    steps: List[PipelineStepResult] = []

    # STEP 1
    cmd_1 = [
        str(python_exe),
        "-m",
        "voucher_generator.xlsx_to_voucher_json",
        str(local_excel),
        "-o",
        str(payload_json),
        "--profile",
        profile,
        "--debug-rows",
    ]
    if pretty_json:
        cmd_1.append("--pretty")

    step_1 = _run_step("xlsx_to_voucher_json", cmd_1, cwd=project_root)
    steps.append(step_1)
    if not step_1.ok:
        return _build_result(
            ok=False,
            job_id=job_id,
            working_dir=job_dir,
            input_file=local_excel,
            steps=steps,
            job_dir=job_dir,
            profile=profile,
            error="Falló xlsx_to_voucher_json.py",
        )

    # STEP 2
    cmd_2 = [
        str(python_exe),
        "-m",
        "voucher_generator.enrich_hotels",
        str(payload_json),
        "-o",
        str(enriched_json),
        "--cache",
        str(hotel_cache),
    ]

    step_2 = _run_step("enrich_hotels", cmd_2, cwd=project_root)
    steps.append(step_2)
    if not step_2.ok:
        return _build_result(
            ok=False,
            job_id=job_id,
            working_dir=job_dir,
            input_file=local_excel,
            steps=steps,
            job_dir=job_dir,
            profile=profile,
            error="Falló enrich_hotels.py",
        )

    # STEP 3
    cmd_3 = [
        str(python_exe),
        "-m",
        "voucher_generator.render_vouchers_html",
        str(enriched_json),
        "-o",
        str(html_dir),
    ]

    step_3 = _run_step("render_html", cmd_3, cwd=project_root)
    steps.append(step_3)

    # STEP 4
    cmd_4 = [
        str(python_exe),
        "-m",
        "voucher_generator.render_vouchers_pdf",
        str(html_dir),
        "-o",
        str(pdf_dir),
    ]

    step_4 = _run_step("render_pdf", cmd_4, cwd=project_root)
    steps.append(step_4)

    zip_path = job_dir / "artifacts.zip"
    zip_result = _zip_folder(job_dir, zip_path)

    return _build_result(
        ok=True,
        job_id=job_id,
        working_dir=job_dir,
        input_file=local_excel,
        steps=steps,
        job_dir=job_dir,
        profile=profile,
        zip_file=zip_result,
    )