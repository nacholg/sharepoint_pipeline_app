const API = {
  localRun: "/api/local/run",
  sharepointRun: "/api/sharepoint/run",
  sharepointExplore: "/api/sharepoint/explore",
  sharepointSites: "/api/sharepoint/sites",
};

const currentUser = (() => {
  const el = document.getElementById("user-data");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
})();

const btnLocal = document.getElementById("btnLocal");
const btnSP = document.getElementById("btnSP");

const localSection = document.getElementById("localSection");
const spSection = document.getElementById("spSection");

const runLocalBtn = document.getElementById("runLocalBtn");
const runSPBtn = document.getElementById("runSPBtn");
const pickSPFileBtn = document.getElementById("pickSPFileBtn");
const pickSPFolderBtn = document.getElementById("pickSPFolderBtn");

const fileInput = document.getElementById("fileInput");

const progressCard = document.getElementById("progressCard");
const progressFill = document.getElementById("progressFill");
const progressLabel = document.getElementById("progressLabel");
const progressPercent = document.getElementById("progressPercent");
const pipelineStatusBadge = document.getElementById("pipelineStatusBadge");
const stepsDiv = document.getElementById("steps");

const resultCard = document.getElementById("resultCard");
const resultContent = document.getElementById("resultContent");

const selectedSourceLabel = document.getElementById("selectedSourceLabel");
const selectedDestLabel = document.getElementById("selectedDestLabel");

const sourceSiteSelect = document.getElementById("sourceSiteSelect");
const destinationSiteSelect = document.getElementById("destinationSiteSelect");
const modalSiteSelect = document.getElementById("modalSiteSelect");

const spModal = document.getElementById("spModal");
const spModalBackdrop = document.getElementById("spModalBackdrop");
const closeSPModalBtn = document.getElementById("closeSPModalBtn");
const confirmSPSelectionBtn = document.getElementById("confirmSPSelectionBtn");
const spModalBody = document.getElementById("spModalBody");

const spModalTitle = document.getElementById("spModalTitle");
const spCurrentPathLabel = document.getElementById("spCurrentPathLabel");
const spBackBtn = document.getElementById("spBackBtn");
const selectCurrentFolderBtn = document.getElementById("selectCurrentFolderBtn");

const spPickedSourceInline = document.getElementById("spPickedSourceInline");
const spPickedDestInline = document.getElementById("spPickedDestInline");

let sharepointSites = [];

let selectedSourceFileId = null;
let selectedSourceFileName = null;
let selectedSourceSiteKey = null;

let selectedDestinationFolderId = null;
let selectedDestinationFolderName = null;
let selectedDestinationSiteKey = null;

let currentSharePointFolderId = null;
let currentSharePointFolderName = null;
let currentModalSiteKey = null;
let spBrowseMode = "source";
let spFolderStack = [];

btnLocal?.addEventListener("click", () => switchMode("local"));
btnSP?.addEventListener("click", () => switchMode("sharepoint"));

runLocalBtn?.addEventListener("click", runLocalPipeline);
runSPBtn?.addEventListener("click", runSharePointPipeline);

pickSPFileBtn?.addEventListener("click", async () => {
  spBrowseMode = "source";
  currentModalSiteKey = sourceSiteSelect?.value || getDefaultSiteKey();
  if (modalSiteSelect) modalSiteSelect.value = currentModalSiteKey;
  openSPModal();
  await loadSharePointFolder(null, true);
});

pickSPFolderBtn?.addEventListener("click", async () => {
  spBrowseMode = "dest";
  currentModalSiteKey = destinationSiteSelect?.value || getDefaultSiteKey();
  if (modalSiteSelect) modalSiteSelect.value = currentModalSiteKey;
  openSPModal();
  await loadSharePointFolder(null, true);
});

closeSPModalBtn?.addEventListener("click", closeSPModal);
spModalBackdrop?.addEventListener("click", closeSPModal);

confirmSPSelectionBtn?.addEventListener("click", () => {
  syncPickedLabels();
  closeSPModal();
});

spBackBtn?.addEventListener("click", async () => {
  if (spFolderStack.length <= 1) {
    await loadSharePointFolder(null, true);
    return;
  }

  spFolderStack.pop();
  const previous = spFolderStack[spFolderStack.length - 1] || null;
  await loadSharePointFolder(previous?.id || null, false, true);
});

selectCurrentFolderBtn?.addEventListener("click", async () => {
  if (!currentSharePointFolderId) return;
  selectedDestinationFolderId = currentSharePointFolderId;
  selectedDestinationFolderName = currentSharePointFolderName;
  selectedDestinationSiteKey = currentModalSiteKey;
  if (destinationSiteSelect) destinationSiteSelect.value = currentModalSiteKey;
  syncPickedLabels();
  await loadSharePointFolder(currentSharePointFolderId, false, true);
});

modalSiteSelect?.addEventListener("change", async () => {
  currentModalSiteKey = modalSiteSelect.value;
  await loadSharePointFolder(null, true);
});

sourceSiteSelect?.addEventListener("change", () => {
  if (selectedSourceSiteKey !== sourceSiteSelect.value) {
    selectedSourceFileId = null;
    selectedSourceFileName = null;
    selectedSourceSiteKey = null;
    syncPickedLabels();
  }
});

destinationSiteSelect?.addEventListener("change", () => {
  if (selectedDestinationSiteKey !== destinationSiteSelect.value) {
    selectedDestinationFolderId = null;
    selectedDestinationFolderName = null;
    selectedDestinationSiteKey = null;
    syncPickedLabels();
  }
});

document.addEventListener("DOMContentLoaded", async () => {
  if (currentUser) {
    await loadSharePointSites();
  }
  syncPickedLabels();
});

function getDefaultSiteKey() {
  if (sharepointSites.find((x) => x.key === "globalevents2")) {
    return "globalevents2";
  }
  return sharepointSites[0]?.key || null;
}

async function loadSharePointSites() {
  try {
    const response = await fetch(API.sharepointSites);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      return;
    }

    sharepointSites = data.sites || [];

    fillSiteSelect(sourceSiteSelect, sharepointSites);
    fillSiteSelect(destinationSiteSelect, sharepointSites);
    fillSiteSelect(modalSiteSelect, sharepointSites);

    const defaultKey = getDefaultSiteKey();
    if (sourceSiteSelect && defaultKey) sourceSiteSelect.value = defaultKey;
    if (destinationSiteSelect && defaultKey) destinationSiteSelect.value = defaultKey;
    if (modalSiteSelect && defaultKey) modalSiteSelect.value = defaultKey;
  } catch (error) {
    console.error("No se pudieron cargar los sites:", error);
  }
}

function fillSiteSelect(selectEl, sites) {
  if (!selectEl) return;
  selectEl.innerHTML = "";
  for (const site of sites) {
    const opt = document.createElement("option");
    opt.value = site.key;
    opt.textContent = site.label;
    selectEl.appendChild(opt);
  }
}

function switchMode(mode) {
  const isLocal = mode === "local";
  btnLocal?.classList.toggle("active", isLocal);
  btnSP?.classList.toggle("active", !isLocal);
  localSection?.classList.toggle("hidden", !isLocal);
  spSection?.classList.toggle("hidden", isLocal);
}

function openSPModal() {
  spModal?.classList.remove("hidden");
  document.body.style.overflow = "hidden";
  updateModalContext();
  syncPickedLabels();
}

function closeSPModal() {
  spModal?.classList.add("hidden");
  document.body.style.overflow = "";
}

function updateModalContext() {
  if (spModalTitle) {
    spModalTitle.textContent =
      spBrowseMode === "source"
        ? "Seleccionar Excel de origen"
        : "Seleccionar carpeta destino";
  }

  selectCurrentFolderBtn?.classList.toggle("hidden", spBrowseMode !== "dest");
}

function syncPickedLabels() {
  if (selectedSourceLabel) {
    selectedSourceLabel.textContent = selectedSourceFileName
      ? `${selectedSourceFileName} (${selectedSourceSiteKey || "-"})`
      : "Sin seleccionar";
  }
  if (selectedDestLabel) {
    selectedDestLabel.textContent = selectedDestinationFolderName
      ? `${selectedDestinationFolderName} (${selectedDestinationSiteKey || "-"})`
      : "Sin seleccionar";
  }
  if (spPickedSourceInline) {
    spPickedSourceInline.textContent = selectedSourceFileName
      ? `${selectedSourceFileName} (${selectedSourceSiteKey || "-"})`
      : "Sin seleccionar";
  }
  if (spPickedDestInline) {
    spPickedDestInline.textContent = selectedDestinationFolderName
      ? `${selectedDestinationFolderName} (${selectedDestinationSiteKey || "-"})`
      : "Sin seleccionar";
  }
}

async function runLocalPipeline() {
  const file = fileInput?.files?.[0];
  if (!file) {
    alert("Seleccioná un Excel.");
    return;
  }

  resetUI("Ejecutando pipeline local...");
  setRunningState();

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(API.localRun, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    renderResult(data, "local");
  } catch (error) {
    renderFatalError(error);
  }
}

async function runSharePointPipeline() {
  if (!currentUser) {
    window.location.href = "/auth/login";
    return;
  }

  if (!selectedSourceFileId) {
    alert("Seleccioná un archivo Excel de SharePoint.");
    return;
  }

  if (!selectedDestinationFolderId) {
    alert("Seleccioná una carpeta destino de SharePoint.");
    return;
  }

  resetUI("Ejecutando pipeline desde SharePoint...");
  setRunningState();

  try {
    const response = await fetch(API.sharepointRun, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        source_file_id: selectedSourceFileId,
        destination_folder_id: selectedDestinationFolderId,
        source_site_key: selectedSourceSiteKey || sourceSiteSelect?.value || getDefaultSiteKey(),
        destination_site_key: selectedDestinationSiteKey || destinationSiteSelect?.value || getDefaultSiteKey(),
      }),
    });

    const data = await response.json();
    renderResult(data, "sharepoint");
  } catch (error) {
    renderFatalError(error);
  }
}

async function loadSharePointFolder(folderId = null, resetStack = false, preserveStack = false) {
  if (!currentUser || !spModalBody) return;

  spModalBody.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⏳</div>
      <p>Cargando SharePoint...</p>
    </div>
  `;

  try {
    let url = API.sharepointExplore;
    const params = new URLSearchParams();

    if (folderId) params.set("folder_id", folderId);
    if (currentModalSiteKey) params.set("site_key", currentModalSiteKey);

    const qs = params.toString();
    if (qs) url += `?${qs}`;

    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      spModalBody.innerHTML = `
        <div class="error-banner">
          No se pudo cargar SharePoint.
        </div>
      `;
      return;
    }

    currentSharePointFolderId = data.current_folder?.id || null;
    currentSharePointFolderName = data.current_folder?.name || "Raíz";
    currentModalSiteKey = data.site_key || currentModalSiteKey;

    if (modalSiteSelect && currentModalSiteKey) {
      modalSiteSelect.value = currentModalSiteKey;
    }

    if (spCurrentPathLabel) {
      const siteLabel = data.site_label ? `${data.site_label} / ` : "";
      spCurrentPathLabel.textContent = `${siteLabel}${currentSharePointFolderName}`;
    }

    if (resetStack) {
      spFolderStack = [];
    }

    if (!preserveStack) {
      const alreadyTop = spFolderStack[spFolderStack.length - 1]?.id === currentSharePointFolderId;
      if (!alreadyTop) {
        spFolderStack.push({
          id: currentSharePointFolderId,
          name: currentSharePointFolderName,
          site_key: currentModalSiteKey,
        });
      }
    }

    renderSharePointItems(data.items || []);
  } catch (error) {
    spModalBody.innerHTML = `
      <div class="error-banner">
        Error: ${escapeHtml(error.message || "No se pudo cargar SharePoint")}
      </div>
    `;
  }
}

function renderSharePointItems(items) {
  if (!spModalBody) return;

  if (!items.length) {
    spModalBody.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📂</div>
        <p>No hay elementos en esta carpeta.</p>
      </div>
    `;
    return;
  }

  const rows = items
    .map((item) => {
      const isFolder = !!item.is_folder;
      const isFile = !!item.is_file;

      let actionButtons = "";

      if (isFolder) {
        actionButtons += `
          <button
            class="btn secondary small"
            type="button"
            onclick="window.__openSharePointFolder('${escapeJs(item.id)}')"
          >
            Abrir
          </button>
        `;

        if (spBrowseMode === "dest") {
          actionButtons += `
            <button
              class="btn primary small"
              type="button"
              onclick="window.__pickDestinationFolder('${escapeJs(item.id)}','${escapeJs(item.name)}')"
            >
              Elegir
            </button>
          `;
        }
      }

      if (isFile && spBrowseMode === "source") {
        const validExcel = String(item.name || "").toLowerCase().endsWith(".xlsx")
          || String(item.name || "").toLowerCase().endsWith(".xlsm");

        if (validExcel) {
          actionButtons += `
            <button
              class="btn primary small"
              type="button"
              onclick="window.__pickSourceFile('${escapeJs(item.id)}','${escapeJs(item.name)}')"
            >
              Seleccionar
            </button>
          `;
        }
      }

      return `
        <div class="browser-row">
          <div class="browser-main">
            <div class="browser-name">
              <span class="browser-icon">${isFolder ? "📁" : "📄"}</span>
              ${escapeHtml(item.name || "Sin nombre")}
            </div>
            <div class="browser-meta">
              ${isFolder ? "Carpeta" : (item.mime_type || "Archivo")}
            </div>
          </div>
          <div class="browser-actions">
            ${actionButtons || `<span class="muted-pill">Sin acción</span>`}
          </div>
        </div>
      `;
    })
    .join("");

  spModalBody.innerHTML = `<div class="browser-list">${rows}</div>`;
}

window.__openSharePointFolder = async function (folderId) {
  await loadSharePointFolder(folderId, false, false);
};

window.__pickSourceFile = function (fileId, fileName) {
  selectedSourceFileId = fileId;
  selectedSourceFileName = fileName;
  selectedSourceSiteKey = currentModalSiteKey;
  if (sourceSiteSelect) sourceSiteSelect.value = currentModalSiteKey;
  syncPickedLabels();
};

window.__pickDestinationFolder = function (folderId, folderName) {
  selectedDestinationFolderId = folderId;
  selectedDestinationFolderName = folderName;
  selectedDestinationSiteKey = currentModalSiteKey;
  if (destinationSiteSelect) destinationSiteSelect.value = currentModalSiteKey;
  syncPickedLabels();
};

function resetUI(message = "Procesando...") {
  progressCard?.classList.remove("hidden");
  resultCard?.classList.add("hidden");

  if (progressFill) progressFill.style.width = "12%";
  if (progressLabel) progressLabel.textContent = message;
  if (progressPercent) progressPercent.textContent = "12%";
  if (pipelineStatusBadge) {
    pipelineStatusBadge.textContent = "Running";
    pipelineStatusBadge.className = "status-badge running";
  }

  if (stepsDiv) {
    stepsDiv.innerHTML = `
      <div class="step-item running">
        <div class="step-bullet"></div>
        <div>
          <strong>Pipeline iniciado</strong>
          <p>Esperando respuesta del backend...</p>
        </div>
      </div>
    `;
  }
}

function setRunningState() {
  runLocalBtn && (runLocalBtn.disabled = true);
  runSPBtn && (runSPBtn.disabled = true);
  pickSPFileBtn && (pickSPFileBtn.disabled = true);
  pickSPFolderBtn && (pickSPFolderBtn.disabled = true);
}

function clearRunningState() {
  runLocalBtn && (runLocalBtn.disabled = false);
  runSPBtn && (runSPBtn.disabled = false);
  pickSPFileBtn && (pickSPFileBtn.disabled = false);
  pickSPFolderBtn && (pickSPFolderBtn.disabled = false);
}

function renderResult(data, mode) {
  clearRunningState();

  progressCard?.classList.remove("hidden");
  resultCard?.classList.remove("hidden");

  if (progressFill) progressFill.style.width = data.ok ? "100%" : "100%";
  if (progressLabel) progressLabel.textContent = data.ok ? "Pipeline finalizado" : "Pipeline con error";
  if (progressPercent) progressPercent.textContent = "100%";

  if (pipelineStatusBadge) {
    pipelineStatusBadge.textContent = data.ok ? "Success" : "Error";
    pipelineStatusBadge.className = `status-badge ${data.ok ? "success" : "error"}`;
  }

  renderSteps(data.steps || [], data.error);

  const generatedFiles = Array.isArray(data.generated_files) ? data.generated_files : [];
  const uploadedFiles = Array.isArray(data.uploaded_files) ? data.uploaded_files : [];

  const uploadedZipHtml = data.uploaded_zip
    ? `
      <div class="result-kpi">
        <span>ZIP subido</span>
        <strong>${escapeHtml(data.uploaded_zip.name || "artifacts.zip")}</strong>
        ${data.uploaded_zip.web_url ? `<a href="${escapeHtml(data.uploaded_zip.web_url)}" target="_blank">Abrir</a>` : ""}
        ${data.uploaded_zip.upload_error ? `<p class="error-text">${escapeHtml(data.uploaded_zip.upload_error)}</p>` : ""}
      </div>
    `
    : "";

  resultContent.innerHTML = `
    <div class="result-grid">
      <div class="result-kpi">
        <span>Job ID</span>
        <strong>${escapeHtml(data.job_id || "-")}</strong>
      </div>
      <div class="result-kpi">
        <span>Modo</span>
        <strong>${escapeHtml(mode)}</strong>
      </div>
      <div class="result-kpi">
        <span>Site origen</span>
        <strong>${escapeHtml(data.source_site_label || "-")}</strong>
      </div>
      <div class="result-kpi">
        <span>Site destino</span>
        <strong>${escapeHtml(data.destination_site_label || "-")}</strong>
      </div>
      ${uploadedZipHtml}
    </div>

    <div class="result-section">
      <h4>Archivos generados</h4>
      ${
        generatedFiles.length
          ? `<ul class="file-list">${generatedFiles.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul>`
          : `<p class="muted-text">No hay archivos generados.</p>`
      }
    </div>

    <div class="result-section">
      <h4>Uploads a SharePoint</h4>
      ${
        uploadedFiles.length
          ? `
          <ul class="file-list">
            ${uploadedFiles
              .map((f) => {
                if (f.upload_error) {
                  return `<li>${escapeHtml(f.name || "-")} — <span class="error-text">${escapeHtml(f.upload_error)}</span></li>`;
                }
                if (f.web_url) {
                  return `<li><a href="${escapeHtml(f.web_url)}" target="_blank">${escapeHtml(f.name || "-")}</a></li>`;
                }
                return `<li>${escapeHtml(f.name || "-")}</li>`;
              })
              .join("")}
          </ul>`
          : `<p class="muted-text">No hubo uploads individuales.</p>`
      }
    </div>

    ${
      data.error
        ? `<div class="error-banner">Error: ${escapeHtml(data.error)}</div>`
        : ""
    }
  `;
}

function renderSteps(steps, fatalError = null) {
  if (!stepsDiv) return;

  if (!steps.length && !fatalError) {
    stepsDiv.innerHTML = `
      <div class="step-item success">
        <div class="step-bullet"></div>
        <div>
          <strong>Sin pasos detallados</strong>
        </div>
      </div>
    `;
    return;
  }

  const parts = steps.map((step) => {
    const statusClass = step.ok ? "success" : "error";
    const output = [step.stdout, step.stderr].filter(Boolean).join("\n");

    return `
      <div class="step-item ${statusClass}">
        <div class="step-bullet"></div>
        <div>
          <strong>${escapeHtml(step.name || "Paso")}</strong>
          <p>Return code: ${escapeHtml(String(step.returncode ?? "-"))}</p>
          ${output ? `<pre class="log-block">${escapeHtml(output)}</pre>` : ""}
        </div>
      </div>
    `;
  });

  if (fatalError) {
    parts.push(`
      <div class="step-item error">
        <div class="step-bullet"></div>
        <div>
          <strong>Error final</strong>
          <pre class="log-block">${escapeHtml(fatalError)}</pre>
        </div>
      </div>
    `);
  }

  stepsDiv.innerHTML = parts.join("");
}

function renderFatalError(error) {
  clearRunningState();

  progressCard?.classList.remove("hidden");
  resultCard?.classList.remove("hidden");

  if (progressFill) progressFill.style.width = "100%";
  if (progressLabel) progressLabel.textContent = "Error en la ejecución";
  if (progressPercent) progressPercent.textContent = "100%";

  if (pipelineStatusBadge) {
    pipelineStatusBadge.textContent = "Error";
    pipelineStatusBadge.className = "status-badge error";
  }

  const msg = error?.message || "Ocurrió un error inesperado.";

  if (stepsDiv) {
    stepsDiv.innerHTML = `
      <div class="step-item error">
        <div class="step-bullet"></div>
        <div>
          <strong>Error fatal</strong>
          <pre class="log-block">${escapeHtml(msg)}</pre>
        </div>
      </div>
    `;
  }

  if (resultContent) {
    resultContent.innerHTML = `
      <div class="error-banner">
        ${escapeHtml(msg)}
      </div>
    `;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeJs(value) {
  return String(value ?? "")
    .replaceAll("\\", "\\\\")
    .replaceAll("'", "\\'")
    .replaceAll('"', '\\"')
    .replaceAll("\n", "\\n")
    .replaceAll("\r", "\\r");
}