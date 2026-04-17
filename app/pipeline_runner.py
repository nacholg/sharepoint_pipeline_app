from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from voucher_generator.profiles import get_profile_config


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
class PipelineValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

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
    validation: Optional[dict] = None

    pipeline_summary: Optional[dict] = None
    summary_file: Optional[str] = None
    warnings_file: Optional[str] = None
    errors_file: Optional[str] = None
    rows_file: Optional[str] = None

    profile_used: Optional[str] = None
    language: Optional[str] = None

    warning_rows: Optional[list] = None
    error_rows: Optional[list] = None
    enrichment_warnings: Optional[list] = None

    logo_summary: Optional[dict] = None
    job_quality: Optional[dict] = None
    logo_details: Optional[list] = None

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

    for suffix in [
        "voucher_payloads.summary.json",
        "voucher_payloads.warnings.json",
        "voucher_payloads.errors.json",
        "voucher_payloads.rows.json",
    ]:
        p = job_dir / suffix
        if p.exists():
            wanted.append(p)

    html_dir = job_dir / "rendered_vouchers"
    pdf_dir = job_dir / "rendered_pdfs"

    if html_dir.exists():
        wanted.extend([p for p in html_dir.rglob("*") if p.is_file()])

    if pdf_dir.exists():
        wanted.extend([p for p in pdf_dir.rglob("*") if p.is_file()])

    return sorted(str(p.resolve()) for p in wanted)


def _is_valid_excel_file(path: Path) -> bool:
    return path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}


def _read_json_if_exists(path: Path) -> Optional[Any]:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_enrichment_warnings(enriched_json_path: Path) -> list[dict]:
    data = _read_json_if_exists(enriched_json_path)
    if not isinstance(data, list):
        return []

    grouped: dict[str, list[str]] = {}

    for item in data:
        hotel = item.get("hotel", {}) or {}
        hotel_name = (
            hotel.get("display_name")
            or hotel.get("name")
            or "Hotel sin nombre"
        )
        warnings = hotel.get("validation_warnings") or []

        if not warnings:
            continue

        if hotel_name not in grouped:
            grouped[hotel_name] = []

        for warning in warnings:
            if warning not in grouped[hotel_name]:
                grouped[hotel_name].append(warning)

    return [
        {"hotel_name": hotel_name, "warnings": warnings}
        for hotel_name, warnings in grouped.items()
    ]


def _build_logo_summary(enriched_json_path: Path) -> dict:
    data = _read_json_if_exists(enriched_json_path)
    if not isinstance(data, list):
        return {"manual": 0, "google": 0, "none": 0, "coverage_pct": 0.0, "total_hotels": 0, "resolved_hotels": 0}

    manual = 0
    google = 0
    none = 0

    for item in data:
        hotel = item.get("hotel") or {}
        source = hotel.get("logo_source")

        if source == "manual":
            manual += 1
        elif source == "google":
            google += 1
        else:
            none += 1

    total_hotels = manual + google + none
    resolved_hotels = manual + google
    coverage_pct = round((resolved_hotels / total_hotels) * 100, 1) if total_hotels > 0 else 0.0

    return {
        "manual": manual,
        "google": google,
        "none": none,
        "total_hotels": total_hotels,
        "resolved_hotels": resolved_hotels,
        "coverage_pct": coverage_pct,
    }


def _build_job_quality_score(
    *,
    pipeline_summary: Optional[dict],
    logo_metrics: Optional[dict],
) -> dict:
    summary = pipeline_summary or {}
    logos = logo_metrics or {}

    skipped_rows = int(summary.get("skipped_rows") or 0)
    warnings = int(summary.get("warnings") or 0)
    hotels_without_logo = int(logos.get("none") or 0)

    score = 100
    score -= skipped_rows * 8
    score -= warnings * 2
    score -= hotels_without_logo * 12
    score = max(0, min(100, score))

    if score >= 90:
        label = "Excelente"
    elif score >= 75:
        label = "Bueno"
    elif score >= 60:
        label = "Aceptable"
    else:
        label = "Revisar"

    return {
        "score": score,
        "label": label,
    }


def _preflight_validate_pipeline(
    *,
    source_excel: Path,
    generator_root: Path,
    logos_dir: Path,
    profile_name: Optional[str],
    brand_logo: Optional[str],
    language: Optional[str],
) -> PipelineValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    if not generator_root.exists():
        errors.append(f"voucher_generator no existe: {generator_root}")

    if not logos_dir.exists():
        errors.append(f"No existe la carpeta de logos: {logos_dir}")

    if not source_excel.exists():
        errors.append(f"Excel de entrada no existe: {source_excel}")
    else:
        if not source_excel.is_file():
            errors.append(f"La ruta de entrada no es un archivo: {source_excel}")
        if not _is_valid_excel_file(source_excel):
            errors.append(
                f"El archivo de entrada debe ser Excel (.xlsx, .xlsm o .xls): {source_excel.name}"
            )

    if language:
        normalized_language = language.strip().lower()
        if normalized_language not in {"es", "en", "pt"}:
            errors.append(
                f"Idioma inválido '{language}'. Valores permitidos: es, en, pt."
            )

    if profile_name:
        try:
            profile_config = get_profile_config(profile_name)
            if not profile_config:
                errors.append(f"No se pudo cargar el profile: {profile_name}")
        except Exception as exc:
            errors.append(f"Profile inválido '{profile_name}': {exc}")

    if brand_logo:
        raw_logo = str(brand_logo).strip()
        if not raw_logo:
            warnings.append("Se recibió brand_logo vacío; se ignorará.")
        elif not raw_logo.startswith(("http://", "https://", "data:")):
            logo_path = Path(raw_logo)
            if not logo_path.is_absolute():
                logo_path = (generator_root / logo_path).resolve()
            if not logo_path.exists():
                errors.append(f"Brand logo override no existe: {logo_path}")
            elif not logo_path.is_file():
                errors.append(f"Brand logo override no es archivo: {logo_path}")

    return PipelineValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )

def _build_logo_details(enriched_json_path: Path) -> list[dict]:
    data = _read_json_if_exists(enriched_json_path)
    if not isinstance(data, list):
        return []

    seen = {}
    result = []

    for item in data:
        hotel = item.get("hotel") or {}
        name = hotel.get("display_name") or hotel.get("name")
        source = hotel.get("logo_source")

        if not name:
            continue

        key = name.lower().strip()

        if key in seen:
            continue

        seen[key] = True

        result.append({
            "hotel_name": name,
            "logo_source": source or "none"
        })

    return result
    
def _build_error_result(
    *,
    job_id: str,
    local_excel: Path,
    job_dir: Path,
    steps: List[PipelineStepResult],
    validation: PipelineValidationResult,
    error_message: str,
    summary_file_path: Path,
    warnings_file_path: Path,
    errors_file_path: Path,
    rows_file_path: Path,
    profile_name: Optional[str],
    resolved_language: str,
    enriched_json: Path,
) -> PipelineRunResult:
    enrichment_warnings = _extract_enrichment_warnings(enriched_json)
    pipeline_summary = _read_json_if_exists(summary_file_path)
    logo_summary = _build_logo_summary(enriched_json)
    job_quality = _build_job_quality_score(
        pipeline_summary=pipeline_summary,
        logo_metrics=logo_summary,
    )

    return PipelineRunResult(
        ok=False,
        job_id=job_id,
        working_dir=str(job_dir),
        input_file=str(local_excel),
        steps=steps,
        generated_files=_collect_outputs(job_dir),
        error=error_message,
        validation=validation.to_dict(),
        pipeline_summary=pipeline_summary,
        warning_rows=_read_json_if_exists(warnings_file_path),
        error_rows=_read_json_if_exists(errors_file_path),
        summary_file=str(summary_file_path) if summary_file_path.exists() else None,
        warnings_file=str(warnings_file_path) if warnings_file_path.exists() else None,
        errors_file=str(errors_file_path) if errors_file_path.exists() else None,
        rows_file=str(rows_file_path) if rows_file_path.exists() else None,
        profile_used=profile_name,
        language=resolved_language,
        enrichment_warnings=enrichment_warnings,
        logo_summary=logo_summary,
        job_quality=job_quality,
    )


def run_full_voucher_pipeline(
    *,
    job_id: str,
    source_excel: Path,
    jobs_root: Optional[Path] = None,
    brand_logo: Optional[str] = None,
    profile_name: Optional[str] = None,
    profile: Optional[str] = None,
    pretty_json: bool = True,
    language: Optional[str] = None,
) -> PipelineRunResult:
    if profile_name is None and profile is not None:
        profile_name = profile

    resolved_language = (language or "es").strip().lower() if language else "es"

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
    source_excel = Path(source_excel).resolve()

    validation = _preflight_validate_pipeline(
        source_excel=source_excel,
        generator_root=generator_root,
        logos_dir=logos_dir,
        profile_name=profile_name,
        brand_logo=brand_logo,
        language=resolved_language,
    )

    if not validation.ok:
        return PipelineRunResult(
            ok=False,
            job_id=job_id,
            working_dir=str(generator_root),
            input_file=str(source_excel),
            error="Falló validación previa del pipeline",
            validation=validation.to_dict(),
            profile_used=profile_name,
            language=resolved_language,
            enrichment_warnings=[],
            logo_summary={"manual": 0, "google": 0, "none": 0, "coverage_pct": 0.0, "total_hotels": 0, "resolved_hotels": 0},
            job_quality={"score": 0, "label": "Revisar"},
        )

    job_dir = (jobs_root / job_id).resolve()
    _ensure_dir(job_dir)

    local_excel = _copy_input_excel(source_excel.resolve(), job_dir).resolve()

    payload_json = (job_dir / "voucher_payloads.json").resolve()
    enriched_json = (job_dir / "voucher_payloads_enriched.json").resolve()
    hotel_cache = (job_dir / "hotel_cache.json").resolve()
    rendered_html_dir = (job_dir / "rendered_vouchers").resolve()
    rendered_pdf_dir = (job_dir / "rendered_pdfs").resolve()

    summary_file_path = payload_json.with_suffix(".summary.json")
    warnings_file_path = payload_json.with_suffix(".warnings.json")
    errors_file_path = payload_json.with_suffix(".errors.json")
    rows_file_path = payload_json.with_suffix(".rows.json")

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
    cmd_1.append("--debug-rows")

    step_1 = _run_step("xlsx_to_voucher_json", cmd_1, cwd=project_root)
    steps.append(step_1)
    if not step_1.ok:
        return _build_error_result(
            job_id=job_id,
            local_excel=local_excel,
            job_dir=job_dir,
            steps=steps,
            validation=validation,
            error_message="Falló xlsx_to_voucher_json.py",
            summary_file_path=summary_file_path,
            warnings_file_path=warnings_file_path,
            errors_file_path=errors_file_path,
            rows_file_path=rows_file_path,
            profile_name=profile_name,
            resolved_language=resolved_language,
            enriched_json=enriched_json,
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
        return _build_error_result(
            job_id=job_id,
            local_excel=local_excel,
            job_dir=job_dir,
            steps=steps,
            validation=validation,
            error_message="Falló enrich_hotels.py",
            summary_file_path=summary_file_path,
            warnings_file_path=warnings_file_path,
            errors_file_path=errors_file_path,
            rows_file_path=rows_file_path,
            profile_name=profile_name,
            resolved_language=resolved_language,
            enriched_json=enriched_json,
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

    if resolved_language:
        cmd_3.extend(["--lang", resolved_language])

    logo_to_use = brand_logo
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
        return _build_error_result(
            job_id=job_id,
            local_excel=local_excel,
            job_dir=job_dir,
            steps=steps,
            validation=validation,
            error_message="Falló render_vouchers_html.py",
            summary_file_path=summary_file_path,
            warnings_file_path=warnings_file_path,
            errors_file_path=errors_file_path,
            rows_file_path=rows_file_path,
            profile_name=profile_name,
            resolved_language=resolved_language,
            enriched_json=enriched_json,
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
        return _build_error_result(
            job_id=job_id,
            local_excel=local_excel,
            job_dir=job_dir,
            steps=steps,
            validation=validation,
            error_message="Falló render_vouchers_pdf.py",
            summary_file_path=summary_file_path,
            warnings_file_path=warnings_file_path,
            errors_file_path=errors_file_path,
            rows_file_path=rows_file_path,
            profile_name=profile_name,
            resolved_language=resolved_language,
            enriched_json=enriched_json,
        )

    generated_files = _collect_outputs(job_dir)

    zip_path = job_dir / "artifacts.zip"
    created_zip = _zip_folder(job_dir, zip_path)

    enrichment_warnings = _extract_enrichment_warnings(enriched_json)
    pipeline_summary = _read_json_if_exists(summary_file_path)
    logo_summary = _build_logo_summary(enriched_json)
    job_quality = _build_job_quality_score(
        pipeline_summary=pipeline_summary,
        logo_metrics=logo_summary,
    )

    logo_details = _build_logo_details(enriched_json),


    return PipelineRunResult(
        ok=True,
        job_id=job_id,
        working_dir=str(job_dir),
        input_file=str(local_excel),
        steps=steps,
        generated_files=generated_files,
        zip_file=str(created_zip.resolve()) if created_zip else None,
        error=None,
        validation=validation.to_dict(),
        pipeline_summary=pipeline_summary,
        warning_rows=_read_json_if_exists(warnings_file_path),
        error_rows=_read_json_if_exists(errors_file_path),
        summary_file=str(summary_file_path) if summary_file_path.exists() else None,
        warnings_file=str(warnings_file_path) if warnings_file_path.exists() else None,
        errors_file=str(errors_file_path) if errors_file_path.exists() else None,
        rows_file=str(rows_file_path) if rows_file_path.exists() else None,
        profile_used=profile_name,
        language=resolved_language,
        enrichment_warnings=enrichment_warnings,
        logo_summary=logo_summary,
        job_quality=job_quality,
        logo_details=logo_details, 
        
    )