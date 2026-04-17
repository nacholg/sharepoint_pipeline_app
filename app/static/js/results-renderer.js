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

function rrToggleSection(sectionId, triggerEl) {
  const section = document.getElementById(sectionId);
  if (!section) return;

  const isHidden = section.classList.toggle("hidden");
  if (triggerEl) {
    triggerEl.textContent = isHidden ? "Ver más" : "Ocultar";
  }
}

function rrPluralize(count, singular, plural = null) {
  const safeCount = Number(count || 0);
  return `${safeCount} ${safeCount === 1 ? singular : (plural || `${singular}s`)}`;
}

function rrRenderValidationBlock(validation) {
  if (!validation) return "";

  const errors = Array.isArray(validation.errors) ? validation.errors : [];
  const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];

  if (!errors.length && !warnings.length) return "";

  const errorHtml = errors.length
    ? `
      <div class="validation-group validation-errors">
        <div class="validation-title">Errores de validación</div>
        <ul>${errors.map((e) => `<li>${rrEscapeHtml(e)}</li>`).join("")}</ul>
      </div>
    `
    : "";

  const warningHtml = warnings.length
    ? `
      <div class="validation-group validation-warnings">
        <div class="validation-title">Warnings de validación</div>
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

function rrBuildSummaryGrid(result) {
  const summary = result.pipeline_summary || {};
  const resolvedProfile = result.resolved_profile || result.profile_used || "-";
  const language = result.language || result.resolved_language || "-";

  const totalRows = summary.total_rows ?? "-";
  const validRows = summary.valid_rows ?? "-";
  const skippedRows = summary.skipped_rows ?? 0;
  const errors = summary.errors ?? "-";
  const warnings = summary.warnings ?? "-";
  const vouchers = summary.vouchers ?? "-";

  const validation = result.validation || {};
  const preflightErrors = Array.isArray(validation.errors) ? validation.errors.length : 0;
  const preflightWarnings = Array.isArray(validation.warnings) ? validation.warnings.length : 0;
  const excelErrors = typeof summary.errors === "number" ? summary.errors : 0;
  const excelWarnings = typeof summary.warnings === "number" ? summary.warnings : 0;

  const totalValidationErrors = preflightErrors + excelErrors;
  const totalValidationWarnings = preflightWarnings + excelWarnings;

  const validationStatus = totalValidationErrors
    ? `${totalValidationErrors} errores`
    : totalValidationWarnings
      ? `${totalValidationWarnings} warnings`
      : "OK";

  return `
    <div class="summary-grid">
      <div class="summary-card">
        <span>Cliente</span>
        <strong>${rrEscapeHtml(result.client_label || "-")}</strong>
      </div>

      <div class="summary-card">
        <span>Profile</span>
        <strong>${rrEscapeHtml(resolvedProfile)}</strong>
      </div>

      <div class="summary-card">
        <span>Idioma</span>
        <strong>${rrEscapeHtml(language)}</strong>
      </div>

      <div class="summary-card">
        <span>Validación</span>
        <strong>${rrEscapeHtml(validationStatus)}</strong>
      </div>

      <div class="summary-card">
        <span>Rows procesadas</span>
        <strong>${rrEscapeHtml(totalRows)}</strong>
      </div>

      <div class="summary-card">
        <span>Rows válidas</span>
        <strong>${rrEscapeHtml(validRows)}</strong>
      </div>

      <div class="summary-card">
        <span>Rows omitidas</span>
        <strong>${rrEscapeHtml(skippedRows)}</strong>
      </div>

      <div
        class="summary-card summary-card-clickable"
        id="warningsSummaryCard"
        role="button"
        tabindex="0"
        onclick="window.__openWarningsModal && window.__openWarningsModal()"
      >
        <span>Warnings</span>
        <strong>${rrEscapeHtml(warnings)}</strong>
      </div>

      <div
        class="summary-card ${typeof errors === "number" && errors > 0 ? "summary-card-clickable" : ""}"
        id="errorsSummaryCard"
        role="button"
        tabindex="0"
        onclick="window.__openErrorsModal && window.__openErrorsModal()"
      >
        <span>Errors</span>
        <strong>${rrEscapeHtml(errors)}</strong>
      </div>

      <div class="summary-card summary-card-highlight">
        <span>Vouchers</span>
        <strong>${rrEscapeHtml(vouchers)}</strong>
      </div>
    </div>
  `;
}

function rrBuildPremiumHero(result) {
  const summary = result.pipeline_summary || {};
  const quality = result.job_quality || {};
  const logoSummary = result.logo_summary || {};

  const vouchers = Number(summary.vouchers ?? 0);
  const warnings = Number(summary.warnings ?? 0);
  const skippedRows = Number(summary.skipped_rows ?? 0);
  const zipFile = result.zip_file || null;

  const qualityScore = Number(quality.score ?? 0);
  const qualityLabel = quality.label || "-";
  const logoCoverage = Number(logoSummary.coverage_pct ?? 0);

  let heroText = `Se generaron ${rrPluralize(vouchers, "voucher")} correctamente.`;

  if (skippedRows > 0) {
    heroText += ` Se omitieron ${rrPluralize(skippedRows, "fila")} con error.`;
  }

  if (warnings > 0) {
    heroText += ` Se detectaron ${rrPluralize(warnings, "warning")}.`;
  }

  heroText += ` Cobertura de logos: ${logoCoverage}%.`;

  if (!zipFile) {
    heroText += " El paquete ZIP no está disponible.";
  }

  return `
    <section class="result-section premium-hero executive-hero">
      <div class="premium-hero-copy">
        <div class="premium-kicker">Resultado listo</div>
        <h4>${rrPluralize(vouchers, "voucher")} generado${vouchers === 1 ? "" : "s"}</h4>
        <p class="muted-text">${rrEscapeHtml(heroText)}</p>

        <div class="summary-grid" style="margin-top:16px;">
          <div class="summary-card summary-card-highlight">
            <span>Score del job</span>
            <strong>${rrEscapeHtml(qualityScore)}/100</strong>
          </div>
          <div class="summary-card">
            <span>Calidad</span>
            <strong>${rrEscapeHtml(qualityLabel)}</strong>
          </div>
          <div class="summary-card">
            <span>Cobertura logos</span>
            <strong>${rrEscapeHtml(logoCoverage)}%</strong>
          </div>
        </div>
      </div>

      <div class="premium-hero-actions">
        ${
          zipFile
            ? `
              <button class="btn primary premium-zip-btn" onclick='downloadZip(${JSON.stringify(zipFile)})'>
                Descargar ZIP
              </button>
            `
            : ""
        }
      </div>
    </section>
  `;
}

function rrBuildDebugFilesGrid(result) {
  const debugItems = [
    { label: "Summary JSON", value: result.summary_file },
    { label: "Rows JSON", value: result.rows_file },
    { label: "Warnings JSON", value: result.warnings_file },
    { label: "Errors JSON", value: result.errors_file },
  ].filter((x) => !!x.value);

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

function rrBuildFileGroup(title, files, icon) {
  if (!files.length) return "";

  return `
    <div class="executive-file-group">
      <div class="executive-file-group-head">
        <div class="executive-file-group-title">${icon} ${title}</div>
        <div class="executive-file-group-count">${files.length}</div>
      </div>

      <div class="executive-file-grid">
        ${files
          .map((file) => {
            const cleanName = rrBaseName(file);
            return `
              <div class="executive-file-card">
                <div class="executive-file-main">
                  <div class="executive-file-name">${rrEscapeHtml(cleanName)}</div>
                </div>
                <div class="executive-file-actions">
                  <button class="btn small" onclick='downloadFile(${JSON.stringify(file)})'>
                    Descargar
                  </button>
                </div>
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function rrBuildFilesSection(result) {
  const files = Array.isArray(result.generated_files) ? result.generated_files : [];

  if (!files.length) {
    return `
      <div class="result-section premium-collapsible-shell">
        <div class="premium-collapsible-head">
          <div>
            <h4>Archivos generados</h4>
            <p class="muted-text">No hay archivos generados.</p>
          </div>
        </div>
      </div>
    `;
  }

  const pdfs = files.filter((f) => f.toLowerCase().endsWith(".pdf"));
  const htmls = files.filter((f) => f.toLowerCase().endsWith(".html"));
  const jsons = files.filter((f) => f.toLowerCase().endsWith(".json"));

  const sectionId = "generatedFilesSection";
  const hiddenClass = RR_PREMIUM_MODE && !RR_SHOW_FILES_BY_DEFAULT ? "hidden" : "";

  return `
    <div class="result-section premium-collapsible-shell executive-files-shell">
      <div class="premium-collapsible-head">
        <div>
          <h4>Entregables</h4>
          <p class="muted-text">Descargas individuales disponibles si necesitás revisar o compartir archivos específicos.</p>
        </div>
        <button
          type="button"
          class="btn secondary small"
          onclick="rrToggleSection('${sectionId}', this)"
        >
          ${hiddenClass ? "Ver archivos" : "Ocultar"}
        </button>
      </div>

      <div id="${sectionId}" class="${hiddenClass}">
        ${rrBuildFileGroup("PDFs", pdfs, "📄")}
        ${rrBuildFileGroup("HTML", htmls, "🌐")}
        ${RR_PREMIUM_MODE ? "" : rrBuildFileGroup("Debug / JSON", jsons, "🧠")}
      </div>
    </div>
  `;
}

function rrBuildPreviewSection(result) {
  if (typeof window.renderPreviewSection === "function") {
    return window.renderPreviewSection(result);
  }

  return "";
}

function rrBuildZipSection(result) {
  if (!result.zip_file || RR_PREMIUM_MODE) return "";

  return `
    <div class="result-section zip-section">
      <h4>📦 Descargar resultado</h4>
      <button class="btn primary" onclick='downloadZip(${JSON.stringify(result.zip_file)})'>
        Descargar ZIP
      </button>
      <div class="zip-path">${rrEscapeHtml(result.zip_file)}</div>
    </div>
  `;
}

function rrBuildDebugSection(result) {
  if (RR_PREMIUM_MODE && !RR_SHOW_DEBUG_BY_DEFAULT) {
    const sectionId = "debugArtifactsSection";
    return `
      <div class="result-section premium-collapsible-shell">
        <div class="premium-collapsible-head">
          <div>
            <h4>Artifacts de debug</h4>
            <p class="muted-text">Información técnica para revisión interna.</p>
          </div>
          <button
            type="button"
            class="btn secondary small"
            onclick="rrToggleSection('${sectionId}', this)"
          >
            Ver más
          </button>
        </div>

        <div id="${sectionId}" class="hidden">
          ${rrBuildDebugFilesGrid(result)}
        </div>
      </div>
    `;
  }

  return `
    <div class="result-section">
      <h4>Artifacts de debug</h4>
      ${rrBuildDebugFilesGrid(result)}
    </div>
  `;
}

function rrBuildUploadsSection(uploadedFiles) {
  if (!uploadedFiles.length) return "";

  const sectionId = "sharepointUploadsSection";
  const hiddenClass = RR_PREMIUM_MODE && !RR_SHOW_UPLOADS_BY_DEFAULT ? "hidden" : "";

  return `
    <div class="result-section premium-collapsible-shell">
      <div class="premium-collapsible-head">
        <div>
          <h4>Uploads a SharePoint</h4>
          <p class="muted-text">Resultado de la subida automática al destino seleccionado.</p>
        </div>
        <button
          type="button"
          class="btn secondary small"
          onclick="rrToggleSection('${sectionId}', this)"
        >
          ${hiddenClass ? "Ver más" : "Ocultar"}
        </button>
      </div>

      <div id="${sectionId}" class="${hiddenClass}">
        <ul class="file-list">
          ${uploadedFiles
            .map((item) => {
              const name = item.name || item.displayName || "archivo";
              const error = item.upload_error;
              return `
                <li class="premium-upload-row">
                  <span class="file-name">${rrEscapeHtml(name)}</span>
                  ${error ? `<span class="error-text"> ${rrEscapeHtml(error)}</span>` : `<span class="premium-ok-pill">OK</span>`}
                </li>
              `;
            })
            .join("")}
        </ul>
      </div>
    </div>
  `;
}

function rrBuildLogoSourceSection(result) {
  const summary = result.logo_summary || null;
  if (!summary) return "";

  const manual = Number(summary.manual ?? 0);
  const google = Number(summary.google ?? 0);
  const none = Number(summary.none ?? 0);

  return `
    <section class="result-section premium-collapsible-shell">
      <div class="premium-collapsible-head">
        <div>
          <h4>Fuente de logos</h4>
          <p class="muted-text">Resumen de cómo se resolvieron los logos de hoteles en esta corrida.</p>
        </div>
      </div>

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
      </div>
    </section>
  `;
}

function renderResult(result) {
  const container = document.getElementById("resultContent");

  if (!container) return;

  container.innerHTML = "";

  const warningRows = Array.isArray(result.warning_rows) ? result.warning_rows : [];
  const errorRows = Array.isArray(result.error_rows) ? result.error_rows : [];
  const uploadedFiles = Array.isArray(result.uploaded_files) ? result.uploaded_files : [];

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

  container.innerHTML = `
    ${rrBuildSummaryGrid(result)}

    ${RR_PREMIUM_MODE ? rrBuildPremiumHero(result) : ""}

    ${rrRenderValidationBlock(result.validation || null)}
    ${rrRenderEnrichmentWarnings(result.enrichment_warnings || [])}
    ${rrBuildLogoSourceSection(result)}

    ${result.error ? `<div class="error-banner">${rrEscapeHtml(result.error)}</div>` : ""}

    ${rrBuildPreviewSection(result)}

    ${rrBuildFilesSection(result)}

    ${rrBuildZipSection(result)}

    ${rrBuildDebugSection(result)}

    ${rrBuildUploadsSection(uploadedFiles)}
    ${rrBuildLogoSourceSection(result)}
    ${rrBuildLogoDetailsSection(result)}
  `;
}

function rrRenderEnrichmentWarnings(enrichmentWarnings) {
  if (!Array.isArray(enrichmentWarnings) || !enrichmentWarnings.length) {
    return "";
  }

  return `
    <section class="result-card validation-card">
      <h3>⚠️ Enrichment de hoteles</h3>
      ${enrichmentWarnings.map(h => `
        <div class="validation-group validation-warnings">
          <div class="validation-title">${rrEscapeHtml(h.hotel_name)}</div>
          <ul>
            ${(Array.isArray(h.warnings) ? h.warnings : []).map(w => `<li>${rrEscapeHtml(w)}</li>`).join("")}
          </ul>
        </div>
      `).join("")}
    </section>
  `;
}


function rrBuildLogoDetailsSection(result) {
  const items = result.logo_details || [];
  if (!items.length) return "";

  return `
    <section class="result-section">
      <h4>Detalle de logos por hotel</h4>

      <div class="summary-grid">
        ${items.map(h => {
          const source = h.logo_source || "none";

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
              <span>${rrEscapeHtml(h.hotel_name)}</span>
              <strong>${badge}</strong>
            </div>
          `;
        }).join("")}
      </div>
    </section>
  `;
}

window.renderResult = renderResult;
window.rrToggleSection = rrToggleSection;