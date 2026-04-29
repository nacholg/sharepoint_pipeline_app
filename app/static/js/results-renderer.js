function rrEscapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function rrDownloadFile(path) {
  const encoded = encodeURIComponent(path);
  window.open(`/api/download-file?path=${encoded}`, "_blank");
}

function rrDownloadZip(path) {
  const encoded = encodeURIComponent(path);
  window.open(`/api/download-zip?path=${encoded}`, "_blank");
}

window.downloadFile = rrDownloadFile;
window.downloadZip = rrDownloadZip;

// -----------------------------------------------------------------------------
// Premium mode flags
// -----------------------------------------------------------------------------

const RR_PREMIUM_MODE = true;
const RR_SHOW_DEBUG_BY_DEFAULT = false;
const RR_SHOW_FILES_BY_DEFAULT = false;
const RR_SHOW_UPLOADS_BY_DEFAULT = false;

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function rrBaseName(path) {
  return String(path || "").split(/[\\/]/).pop() || "";
}

function rrPluralize(count, singular, plural = null) {
  const safeCount = Number(count || 0);
  return `${safeCount} ${safeCount === 1 ? singular : (plural || `${singular}s`)}`;
}

function rrFormatDuration(value) {
  if (value == null || value === "") return "—";

  const num = Number(value);
  if (!Number.isFinite(num)) return rrEscapeHtml(value);

  if (num < 1) {
    return `${Math.round(num * 1000)} ms`;
  }

  if (num < 60) {
    return `${num.toFixed(1)} s`;
  }

  const minutes = Math.floor(num / 60);
  const seconds = Math.round(num % 60);
  return `${minutes}m ${seconds}s`;
}

function rrTextOrDash(value) {
  if (value == null || value === "") return "—";
  return String(value);
}

function rrCountFilesByExt(files, ext) {
  return files.filter((f) => String(f).toLowerCase().endsWith(ext)).length;
}

function rrBuildDownloadButtons(files) {
  if (!Array.isArray(files) || !files.length) return "";

  return files
    .map((file) => {
      const cleanName = rrBaseName(file);
      return `
        <button
          class="btn secondary small"
          type="button"
          onclick='downloadFile(${JSON.stringify(file)})'
          title="${rrEscapeHtml(cleanName)}"
        >
          ${rrEscapeHtml(cleanName)}
        </button>
      `;
    })
    .join("");
}

function rrBuildUploadedFilesHtml(uploadedFiles) {
  if (!uploadedFiles.length) {
    return `<div class="empty-state-inline">No hubo uploads a SharePoint en esta corrida.</div>`;
  }

  return `
    <div class="upload-results-list">
      ${uploadedFiles
        .map((item) => {
          const name = item.name || item.displayName || "archivo";
          const error = item.upload_error;

          return `
            <div class="premium-upload-row">
              <span class="file-name">${rrEscapeHtml(name)}</span>
              ${
                error
                  ? `<span class="error-text">${rrEscapeHtml(error)}</span>`
                  : `<span class="premium-ok-pill">OK</span>`
              }
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function rrBuildValidationSummary(result) {
  const summary = result.pipeline_summary || {};
  const validation = result.validation || {};

  const preflightErrors = Array.isArray(validation.errors) ? validation.errors.length : 0;
  const preflightWarnings = Array.isArray(validation.warnings) ? validation.warnings.length : 0;
  const excelErrors = typeof summary.errors === "number" ? summary.errors : 0;
  const excelWarnings = typeof summary.warnings === "number" ? summary.warnings : 0;

  return {
    totalErrors: preflightErrors + excelErrors,
    totalWarnings: preflightWarnings + excelWarnings,
  };
}

function rrRenderValidationBlock(validation) {
  if (!validation) return "";

  const errors = Array.isArray(validation.errors) ? validation.errors : [];
  const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];

  if (!errors.length && !warnings.length) return "";

  const errorHtml = errors.length
    ? `
      <div class="validation-group validation-errors">
        <div class="validation-title">Errores de validación previa</div>
        <ul>${errors.map((e) => `<li>${rrEscapeHtml(e)}</li>`).join("")}</ul>
      </div>
    `
    : "";

  const warningHtml = warnings.length
    ? `
      <div class="validation-group validation-warnings">
        <div class="validation-title">Advertencias de validación previa</div>
        <ul>${warnings.map((w) => `<li>${rrEscapeHtml(w)}</li>`).join("")}</ul>
      </div>
    `
    : "";

  return `
    <section class="result-card validation-card">
      <h3>Validación previa</h3>
      ${errorHtml}
      ${warningHtml}
    </section>
  `;
}

function rrRenderEnrichmentWarnings(enrichmentWarnings) {
  if (!Array.isArray(enrichmentWarnings) || !enrichmentWarnings.length) {
    return "";
  }

  return `
    <section class="result-card validation-card">
      <h3>Enrichment de hoteles</h3>
      ${enrichmentWarnings
        .map(
          (hotel) => `
            <div class="validation-group validation-warnings">
              <div class="validation-title">${rrEscapeHtml(hotel.hotel_name)}</div>
              <ul>
                ${(Array.isArray(hotel.warnings) ? hotel.warnings : [])
                  .map((warning) => `<li>${rrEscapeHtml(warning)}</li>`)
                  .join("")}
              </ul>
            </div>
          `
        )
        .join("")}
    </section>
  `;
}

function rrBuildDebugFilesGrid(result) {
  const debugItems = [
    { label: "Summary JSON", value: result.summary_file },
    { label: "Rows JSON", value: result.rows_file },
    { label: "Warnings JSON", value: result.warnings_file },
    { label: "Errors JSON", value: result.errors_file },
    { label: "Input file", value: result.input_file },
    { label: "Working dir", value: result.working_dir },
  ].filter((item) => !!item.value);

  if (!debugItems.length) {
    return `<p class="muted-text">No hay artifacts de debug expuestos.</p>`;
  }

  return `
    <div class="debug-grid">
      ${debugItems
        .map(
          (item) => `
            <div class="debug-card">
              <span>${rrEscapeHtml(item.label)}</span>
              <code>${rrEscapeHtml(item.value)}</code>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function rrBuildLogoSourceSummary(result) {
  const summary = result.logo_summary || null;
  if (!summary) return "";

  const manual = Number(summary.manual ?? 0);
  const google = Number(summary.google ?? 0);
  const none = Number(summary.none ?? 0);
  const coverage = Number(summary.coverage_pct ?? 0);

  return `
    <section class="result-card validation-card">
      <h3>Fuente de logos</h3>
      <div class="summary-grid">
        <div class="summary-card">
          <span>Manual</span>
          <strong>${rrEscapeHtml(manual)}</strong>
        </div>
        <div class="summary-card">
          <span>Google</span>
          <strong>${rrEscapeHtml(google)}</strong>
        </div>
        <div class="summary-card">
          <span>Sin logo</span>
          <strong>${rrEscapeHtml(none)}</strong>
        </div>
        <div class="summary-card summary-card-highlight">
          <span>Cobertura</span>
          <strong>${rrEscapeHtml(coverage)}%</strong>
        </div>
      </div>
    </section>
  `;
}

function rrBuildLogoDetailsSection(result) {
  const items = Array.isArray(result.logo_details) ? result.logo_details : [];
  if (!items.length) return "";

  return `
    <section class="result-section">
      <h4>Detalle de logos por hotel</h4>
      <div class="summary-grid">
        ${items
          .map((hotel) => {
            const source = hotel.logo_source || "none";

            let badge = "";
            if (source === "manual") {
              badge = `<span class="badge success">Manual</span>`;
            } else if (source === "google") {
              badge = `<span class="badge info">Google</span>`;
            } else {
              badge = `<span class="badge warning">Sin logo</span>`;
            }

            return `
              <div class="summary-card">
                <span>${rrEscapeHtml(hotel.hotel_name)}</span>
                <strong>${badge}</strong>
              </div>
            `;
          })
          .join("")}
      </div>
    </section>
  `;
}

function rrRenderPreviewIntoHost(result) {
  const host = document.getElementById("resultPreviewHost");
  if (!host) return;

  if (typeof window.renderPreviewSection === "function") {
    host.innerHTML = window.renderPreviewSection(result) || "";
    if (!host.innerHTML.trim()) {
      host.innerHTML = `
        <div class="empty-state-inline">
          La vista previa no está disponible para este resultado.
        </div>
      `;
    }
    return;
  }

  host.innerHTML = `
    <div class="empty-state-inline">
      La vista previa no está disponible para este resultado.
    </div>
  `;
}

function rrRenderHero(result) {
  const summary = result.pipeline_summary || {};
  const quality = result.job_quality || {};
  const logoSummary = result.logo_summary || {};
  const validationSummary = rrBuildValidationSummary(result);

  const vouchers = Number(summary.vouchers ?? 0);
  const skippedRows = Number(summary.skipped_rows ?? 0);
  const warnings = validationSummary.totalWarnings;
  const errors = validationSummary.totalErrors;
  const qualityScore = Number(quality.score ?? 0);
  const qualityLabel = quality.label || "Resultado listo";
  const logoCoverage = Number(logoSummary.coverage_pct ?? 0);

  const titleEl = document.getElementById("resultHeroTitle");
  const subtitleEl = document.getElementById("resultHeroSubtitle");
  const statusEl = document.getElementById("resultHeroStatus");
  const vouchersEl = document.getElementById("resultMetricVouchers");
  const durationEl = document.getElementById("resultMetricDuration");
  const sourceEl = document.getElementById("resultMetricSource");
  const destinationEl = document.getElementById("resultMetricDestination");
  const warningsBtn = document.getElementById("resultWarningsBtn");
  const warningsCountEl = document.getElementById("resultWarningsCount");
  const errorsBtn = document.getElementById("resultErrorsBtn");
  const errorsCountEl = document.getElementById("resultErrorsCount");
  const profilePillEl = document.getElementById("resultProfilePill");

  if (statusEl) {
    statusEl.className = "status-badge success";
    statusEl.textContent = errors > 0 ? "Completado con observaciones" : "Completado";
  }

  if (titleEl) {
    titleEl.textContent = `${rrPluralize(vouchers, "voucher")} generado${vouchers === 1 ? "" : "s"}`;
  }

  let subtitle = `Score ${qualityScore}/100`;

  if (warnings > 0) {
    subtitle += ` · ${warnings} warnings`;
  }
  if (skippedRows > 0) {
    subtitle += ` · ${skippedRows} omitidas`;
  }

  if (subtitleEl) {
    subtitleEl.textContent = subtitle;
  }

  if (vouchersEl) {
    vouchersEl.textContent = String(summary.vouchers ?? "—");
  }

  if (durationEl) {
    durationEl.textContent = rrFormatDuration(result.duration_seconds || result.duration || result.elapsed_seconds);
  }

  if (sourceEl) {
    sourceEl.textContent = rrTextOrDash(
      result.source_label ||
      result.source_mode ||
      result.input_mode ||
      result.mode
    );
  }

  if (destinationEl) {
    destinationEl.textContent = rrTextOrDash(
      result.destination_label ||
      result.destination_path ||
      result.output_folder ||
      (Array.isArray(result.uploaded_files) && result.uploaded_files.length ? "SharePoint" : "Local")
    );
  }

  if (warningsBtn && warningsCountEl) {
    if (warnings > 0) {
      warningsBtn.classList.remove("hidden");
      warningsCountEl.textContent = String(warnings);
      warningsBtn.onclick = () => window.__openWarningsModal && window.__openWarningsModal();
    } else {
      warningsBtn.classList.add("hidden");
    }
  }

  if (errorsBtn && errorsCountEl) {
    if (errors > 0) {
      errorsBtn.classList.remove("hidden");
      errorsCountEl.textContent = String(errors);
      errorsBtn.onclick = () => window.__openErrorsModal && window.__openErrorsModal();
    } else {
      errorsBtn.classList.add("hidden");
    }
  }

  if (profilePillEl) {
    const resolvedProfile = result.resolved_profile || result.profile_used || result.client_label || "";
    if (resolvedProfile) {
      profilePillEl.classList.remove("hidden");
      profilePillEl.textContent = `Profile: ${resolvedProfile}`;
    } else {
      profilePillEl.classList.add("hidden");
    }
  }
}

function rrRenderDeliverables(result) {
  const files = Array.isArray(result.generated_files) ? result.generated_files : [];
  const htmlFiles = files.filter((f) => String(f).toLowerCase().endsWith(".html"));
  const pdfFiles = files.filter((f) => String(f).toLowerCase().endsWith(".pdf"));
  const jsonFiles = files.filter((f) => String(f).toLowerCase().endsWith(".json"));

  const htmlSummaryEl = document.getElementById("resultHtmlSummary");
  const pdfSummaryEl = document.getElementById("resultPdfSummary");
  const zipSummaryEl = document.getElementById("resultZipSummary");

  const htmlActionsEl = document.getElementById("resultHtmlActions");
  const pdfActionsEl = document.getElementById("resultPdfActions");
  const zipActionsEl = document.getElementById("resultZipActions");

  if (htmlSummaryEl) {
    htmlSummaryEl.textContent = htmlFiles.length
      ? `${rrPluralize(htmlFiles.length, "archivo")} HTML disponible${htmlFiles.length === 1 ? "" : "s"}.`
      : "Sin archivos HTML generados.";
  }

  if (pdfSummaryEl) {
    pdfSummaryEl.textContent = pdfFiles.length
      ? `${rrPluralize(pdfFiles.length, "archivo")} PDF disponible${pdfFiles.length === 1 ? "" : "s"}.`
      : "Sin archivos PDF generados.";
  }

  if (zipSummaryEl) {
    zipSummaryEl.textContent = result.zip_file
      ? "Descargá el paquete completo con todos los entregables."
      : "Todavía no hay ZIP disponible para esta ejecución.";
  }

  if (htmlActionsEl) {
    htmlActionsEl.innerHTML = htmlFiles.length
      ? rrBuildDownloadButtons(htmlFiles)
      : `<span class="muted-text">Sin descargas</span>`;
  }

  if (pdfActionsEl) {
    pdfActionsEl.innerHTML = pdfFiles.length
      ? rrBuildDownloadButtons(pdfFiles)
      : `<span class="muted-text">Sin descargas</span>`;
  }

  if (zipActionsEl) {
    const zipActions = [];

    if (result.zip_file) {
      zipActions.push(`
        <button
          class="btn primary small"
          type="button"
          onclick='downloadZip(${JSON.stringify(result.zip_file)})'
        >
          Descargar ZIP
        </button>
      `);
    }

    if (!RR_PREMIUM_MODE && jsonFiles.length) {
      zipActions.push(rrBuildDownloadButtons(jsonFiles));
    }

    zipActionsEl.innerHTML = zipActions.length
      ? zipActions.join("")
      : `<span class="muted-text">Sin descargas</span>`;
  }
}

function rrRenderLogos(result) {
  const host = document.getElementById("resultLogosHost");
  if (!host) return;

  const logoSummaryHtml = rrBuildLogoSourceSummary(result);
  const logoDetailsHtml = rrBuildLogoDetailsSection(result);

  if (!logoSummaryHtml && !logoDetailsHtml) {
    host.innerHTML = `
      <div class="empty-state-inline">
        No hay información de logos para mostrar en este job.
      </div>
    `;
    return;
  }

  host.innerHTML = `
    ${logoSummaryHtml}
    ${logoDetailsHtml}
  `;
}

function rrRenderValidationSection(result) {
  const host = document.getElementById("resultValidationHost");
  const body = document.getElementById("resultValidationBody");
  const toggleBtn = document.getElementById("toggleResultValidationBtn");

  if (!host || !body || !toggleBtn) return;

  const warningRows = Array.isArray(result.warning_rows) ? result.warning_rows : [];
  const errorRows = Array.isArray(result.error_rows) ? result.error_rows : [];

  const blocks = [
    result.error ? `<div class="error-banner">${rrEscapeHtml(result.error)}</div>` : "",
    rrRenderValidationBlock(result.validation || null),
    rrRenderEnrichmentWarnings(result.enrichment_warnings || []),
    warningRows.length
      ? `
        <div class="result-card validation-card">
          <div class="validation-group validation-warnings">
            <div class="validation-title">Warnings detectados en filas</div>
            <p class="muted-text">Abrí el detalle para revisar cada caso.</p>
            <button
              class="btn secondary small"
              type="button"
              onclick="window.__openWarningsModal && window.__openWarningsModal()"
            >
              Ver detalle
            </button>
          </div>
        </div>
      `
      : "",
    errorRows.length
      ? `
        <div class="result-card validation-card">
          <div class="validation-group validation-errors">
            <div class="validation-title">Errores detectados en filas</div>
            <p class="muted-text">Abrí el detalle para revisar cada caso.</p>
            <button
              class="btn secondary small"
              type="button"
              onclick="window.__openErrorsModal && window.__openErrorsModal()"
            >
              Ver detalle
            </button>
          </div>
        </div>
      `
      : "",
  ].filter(Boolean);

  if (!blocks.length) {
    host.innerHTML = `
      <div class="empty-state-inline">
        No hubo advertencias ni errores para esta ejecución.
      </div>
    `;
    body.classList.add("hidden");
    toggleBtn.textContent = "Expandir";
    return;
  }

  host.innerHTML = blocks.join("");

  if (RR_PREMIUM_MODE) {
    body.classList.add("hidden");
    toggleBtn.textContent = "Expandir";
  } else {
    body.classList.remove("hidden");
    toggleBtn.textContent = "Ocultar";
  }

  toggleBtn.onclick = () => {
    const isHidden = body.classList.toggle("hidden");
    toggleBtn.textContent = isHidden ? "Expandir" : "Ocultar";
  };
}

function rrRenderDebugSection(result) {
  const host = document.getElementById("resultDebugHost");
  const body = document.getElementById("resultDebugBody");
  const toggleBtn = document.getElementById("toggleResultDebugBtn");

  if (!host || !body || !toggleBtn) return;

  const uploadedFiles = Array.isArray(result.uploaded_files) ? result.uploaded_files : [];

  const sections = [
    rrBuildDebugFilesGrid(result),
    rrBuildUploadedFilesHtml(uploadedFiles),
  ].filter(Boolean);

  host.innerHTML = sections.join("");

  if (RR_SHOW_DEBUG_BY_DEFAULT) {
    body.classList.remove("hidden");
    toggleBtn.textContent = "Ocultar";
  } else {
    body.classList.add("hidden");
    toggleBtn.textContent = "Mostrar";
  }

  toggleBtn.onclick = () => {
    const isHidden = body.classList.toggle("hidden");
    toggleBtn.textContent = isHidden ? "Mostrar" : "Ocultar";
  };
}

function rrResetResultSkeleton() {
  const htmlActionsEl = document.getElementById("resultHtmlActions");
  const pdfActionsEl = document.getElementById("resultPdfActions");
  const zipActionsEl = document.getElementById("resultZipActions");
  const logosHost = document.getElementById("resultLogosHost");
  const validationHost = document.getElementById("resultValidationHost");
  const debugHost = document.getElementById("resultDebugHost");
  const previewHost = document.getElementById("resultPreviewHost");

  if (htmlActionsEl) htmlActionsEl.innerHTML = "";
  if (pdfActionsEl) pdfActionsEl.innerHTML = "";
  if (zipActionsEl) zipActionsEl.innerHTML = "";
  if (logosHost) logosHost.innerHTML = "";
  if (validationHost) validationHost.innerHTML = "";
  if (debugHost) debugHost.innerHTML = "";
  if (previewHost) {
    previewHost.innerHTML = `
      <div class="empty-state-inline">
        La vista previa aparecerá acá cuando el job termine.
      </div>
    `;
  }
}

function renderResult(result) {
  const container = document.getElementById("resultContent");
  if (!container) return;

  rrResetResultSkeleton();

  const warningRows = Array.isArray(result.warning_rows) ? result.warning_rows : [];
  const errorRows = Array.isArray(result.error_rows) ? result.error_rows : [];

  window.__openWarningsModal = () => {
    if (typeof window.openValidationModal === "function") {
      window.openValidationModal("Detalle de warnings", warningRows, "warning");
    }
  };

  window.__openErrorsModal = () => {
    if (typeof window.openValidationModal === "function") {
      window.openValidationModal("Detalle de errores", errorRows, "error");
    }
  };

  rrRenderHero(result);
  rrRenderPreviewIntoHost(result);
  rrRenderDeliverables(result);
  rrRenderLogos(result);
  rrRenderValidationSection(result);
  rrRenderDebugSection(result);
}

window.renderResult = renderResult;