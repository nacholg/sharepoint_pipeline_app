const API = {
  localRun: "/api/local/run",
  sharepointRun: "/api/sharepoint/run",
  sharepointSites: "/api/sharepoint/sites",
  sharepointExplore: "/api/sharepoint/explore",
  profiles: "/api/profiles",
};

const userDataEl = document.getElementById("user-data");
const currentUser = userDataEl ? JSON.parse(userDataEl.textContent) : null;

const btnLocal = document.getElementById("btnLocal");
const btnSP = document.getElementById("btnSP");

const localSection = document.getElementById("localSection");
const spSection = document.getElementById("spSection");

const fileInput = document.getElementById("fileInput");
const runLocalBtn = document.getElementById("runLocalBtn");
const runSPBtn = document.getElementById("runSPBtn");

const localProfileSelect = document.getElementById("localProfileSelect");
const sharepointProfileSelect = document.getElementById("sharepointProfileSelect");

const sourceSiteSelect = document.getElementById("sourceSiteSelect");
const destinationSiteSelect = document.getElementById("destinationSiteSelect");

const pickSPFileBtn = document.getElementById("pickSPFileBtn");
const pickSPFolderBtn = document.getElementById("pickSPFolderBtn");

const selectedSourceLabel = document.getElementById("selectedSourceLabel");
const selectedDestLabel = document.getElementById("selectedDestLabel");

const statusBadge = document.getElementById("statusBadge");
const progressLabel = document.getElementById("progressLabel");
const progressPercent = document.getElementById("progressPercent");
const progressFill = document.getElementById("progressFill");
const stepsEl = document.getElementById("steps");

const resultCard = document.getElementById("resultCard");
const resultContent = document.getElementById("resultContent");

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
let availableProfiles = [];

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
  try {
    await loadProfiles();

    if (sourceSiteSelect || destinationSiteSelect || modalSiteSelect) {
      await loadSharePointSites();
    }

    syncPickedLabels();
  } catch (error) {
    console.error("Init error:", error);
  }
});

function getDefaultSiteKey() {
  if (sharepointSites.find((x) => x.key === "globalevents2")) {
    return "globalevents2";
  }
  return sharepointSites[0]?.key || null;
}

async function loadProfiles() {
  try {
    const response = await fetch(API.profiles);
    const data = await response.json();

    if (!response.ok || !data?.ok) {
      return;
    }

    availableProfiles = Array.isArray(data.profiles) ? data.profiles : [];
    const defaultProfile = data.default_profile || "default";

    fillProfileSelect(localProfileSelect, availableProfiles, defaultProfile);
    fillProfileSelect(sharepointProfileSelect, availableProfiles, defaultProfile);
  } catch (error) {
    console.warn("No se pudieron cargar los profiles:", error);
  }
}

function fillProfileSelect(selectEl, profiles, defaultProfile = "default") {
  if (!selectEl) return;

  selectEl.innerHTML = "";

  if (!profiles.length) {
    const opt = document.createElement("option");
    opt.value = "default";
    opt.textContent = "Default";
    opt.selected = true;
    selectEl.appendChild(opt);
    return;
  }

  for (const profile of profiles) {
    const opt = document.createElement("option");
    opt.value = profile.key;
    opt.textContent = profile.label || profile.key;
    if (profile.key === defaultProfile) opt.selected = true;
    selectEl.appendChild(opt);
  }
}

async function loadSharePointSites() {
  const response = await fetch(API.sharepointSites);
  const data = await response.json();

  if (!response.ok || !data.ok) {
    throw new Error("No se pudieron cargar los sites");
  }

  sharepointSites = data.sites || [];

  fillSiteSelect(sourceSiteSelect, sharepointSites);
  fillSiteSelect(destinationSiteSelect, sharepointSites);
  fillSiteSelect(modalSiteSelect, sharepointSites);

  const defaultKey = getDefaultSiteKey();

  if (sourceSiteSelect && defaultKey) sourceSiteSelect.value = defaultKey;
  if (destinationSiteSelect && defaultKey) destinationSiteSelect.value = defaultKey;
  if (modalSiteSelect && defaultKey) modalSiteSelect.value = defaultKey;
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

function resetUI(label = "Esperando ejecución") {
  statusBadge.textContent = "Idle";
  statusBadge.className = "status-badge idle";
  progressLabel.textContent = label;
  progressPercent.textContent = "0%";
  progressFill.style.width = "0%";
  stepsEl.innerHTML = "";
  resultCard.classList.add("hidden");
  resultContent.innerHTML = "";
}

function setRunningState() {
  statusBadge.textContent = "Running";
  statusBadge.className = "status-badge running";
  progressLabel.textContent = "Pipeline en ejecución";
  progressPercent.textContent = "10%";
  progressFill.style.width = "10%";
  stepsEl.innerHTML = "";
  resultCard.classList.add("hidden");
  resultContent.innerHTML = "";
}

function setFinishedState(ok) {
  statusBadge.textContent = ok ? "Success" : "Error";
  statusBadge.className = `status-badge ${ok ? "success" : "error"}`;
  progressLabel.textContent = ok ? "Pipeline finalizado" : "Pipeline con error";
  progressPercent.textContent = "100%";
  progressFill.style.width = "100%";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderStep(step) {
  const wrap = document.createElement("div");
  wrap.className = "step-card";

  const statusClass = step.ok ? "success-dot" : "error-dot";
  const output = [step.stdout, step.stderr].filter(Boolean).join("\n").trim();

  wrap.innerHTML = `
    <div class="step-header">
      <div class="step-title-row">
        <span class="step-dot ${statusClass}"></span>
        <h4>${escapeHtml(step.name)}</h4>
      </div>
      <div class="step-meta">Return code: ${escapeHtml(step.returncode)}</div>
    </div>
    ${
      output
        ? `<pre class="step-output">${escapeHtml(output)}</pre>`
        : `<div class="step-empty">Sin salida</div>`
    }
  `;

  return wrap;
}

function renderFatalError(error) {
  setFinishedState(false);
  stepsEl.innerHTML = `
    <div class="step-card">
      <div class="step-header">
        <div class="step-title-row">
          <span class="step-dot error-dot"></span>
          <h4>Error fatal</h4>
        </div>
      </div>
      <pre class="step-output">${escapeHtml(error?.message || String(error))}</pre>
    </div>
  `;

  resultCard.classList.remove("hidden");
  resultContent.innerHTML = `
    <div class="notice danger">${escapeHtml(error?.message || String(error))}</div>
  `;
}

function renderResult(result, mode) {
  setFinishedState(!!result.ok);

  const steps = Array.isArray(result.steps) ? result.steps : [];
  stepsEl.innerHTML = "";

  if (steps.length) {
    for (const step of steps) {
      stepsEl.appendChild(renderStep(step));
    }
  } else {
    stepsEl.innerHTML = `
      <div class="step-card">
        <div class="step-header">
          <div class="step-title-row">
            <span class="step-dot ${result.ok ? "success-dot" : "error-dot"}"></span>
            <h4>${result.ok ? "Sin pasos detallados" : "Error final"}</h4>
          </div>
        </div>
        <pre class="step-output">${escapeHtml(result.error || "Sin detalles")}</pre>
      </div>
    `;
  }

  resultCard.classList.remove("hidden");

  const generatedFiles = Array.isArray(result.generated_files) ? result.generated_files : [];
  const uploadedFiles = Array.isArray(result.uploaded_files) ? result.uploaded_files : [];
  const summary = result.pipeline_summary || {};
  const resolvedProfile = result.resolved_profile || result.profile_used || "-";

  resultContent.innerHTML = `
    <div class="result-meta-grid">
      <div class="result-meta-card">
        <div class="result-meta-label">Job ID</div>
        <div class="result-meta-value">${escapeHtml(result.job_id || "-")}</div>
      </div>
      <div class="result-meta-card">
        <div class="result-meta-label">Modo</div>
        <div class="result-meta-value">${escapeHtml(mode || result.mode || "-")}</div>
      </div>
      <div class="result-meta-card">
        <div class="result-meta-label">Profile</div>
        <div class="result-meta-value">${escapeHtml(resolvedProfile)}</div>
      </div>
      <div class="result-meta-card">
        <div class="result-meta-label">Vouchers</div>
        <div class="result-meta-value">${escapeHtml(summary.vouchers ?? "-")}</div>
      </div>
      <div class="result-meta-card">
        <div class="result-meta-label">Rows procesadas</div>
        <div class="result-meta-value">${escapeHtml(summary.total_rows ?? "-")}</div>
      </div>
      <div class="result-meta-card">
        <div class="result-meta-label">Warnings</div>
        <div class="result-meta-value">${escapeHtml(summary.warnings ?? "-")}</div>
      </div>
    </div>

    ${
      result.error
        ? `<div class="notice danger">${escapeHtml(result.error)}</div>`
        : ""
    }

    <div class="result-section">
      <h4>Archivos generados</h4>
      ${
        generatedFiles.length
          ? `<ul class="result-list">
              ${generatedFiles
                .map((file) => `<li><code>${escapeHtml(file)}</code></li>`)
                .join("")}
            </ul>`
          : `<p class="muted">No hay archivos generados.</p>`
      }
    </div>

    ${
      result.zip_file
        ? `<div class="result-section">
            <h4>ZIP</h4>
            <p><code>${escapeHtml(result.zip_file)}</code></p>
          </div>`
        : ""
    }

    ${
      uploadedFiles.length
        ? `<div class="result-section">
            <h4>Uploads a SharePoint</h4>
            <ul class="result-list">
              ${uploadedFiles
                .map((item) => {
                  const name = item.name || item.displayName || "archivo";
                  const error = item.upload_error;
                  return `<li>${escapeHtml(name)}${
                    error ? ` — <span class="danger-text">${escapeHtml(error)}</span>` : ""
                  }</li>`;
                })
                .join("")}
            </ul>
          </div>`
        : mode === "sharepoint"
          ? `<div class="result-section"><h4>Uploads a SharePoint</h4><p class="muted">No hubo uploads individuales.</p></div>`
          : ""
    }
  `;
}

async function runLocalPipeline() {
  const file = fileInput?.files?.[0];
  const selectedProfile = localProfileSelect?.value || "default";

  if (!file) {
    alert("Seleccioná un archivo Excel.");
    return;
  }

  const allowedExtensions = [".xlsx", ".xlsm", ".xls"];
  const lowerName = (file.name || "").toLowerCase();
  const isValidExcel = allowedExtensions.some((ext) => lowerName.endsWith(ext));

  if (!isValidExcel) {
    alert("El archivo seleccionado no es un Excel válido (.xlsx, .xlsm o .xls).");
    return;
  }

  resetUI("Ejecutando pipeline local...");
  setRunningState();

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("profile", selectedProfile);

    const response = await fetch(API.localRun, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      renderResult(
        {
          ok: false,
          error: data?.detail || "Error ejecutando pipeline local.",
          steps: [],
          generated_files: [],
        },
        "local"
      );
      return;
    }

    renderResult(data, "local");
  } catch (error) {
    renderFatalError(error);
  }
}

async function runSharePointPipeline() {
  const selectedProfile = sharepointProfileSelect?.value || "default";

  if (!selectedSourceFileId) {
    alert("Seleccioná un Excel de origen en SharePoint.");
    return;
  }

  if (!selectedDestinationFolderId) {
    alert("Seleccioná una carpeta destino en SharePoint.");
    return;
  }

  resetUI("Ejecutando pipeline SharePoint...");
  setRunningState();

  try {
    const payload = {
      source_file_id: selectedSourceFileId,
      destination_folder_id: selectedDestinationFolderId,
      source_site_key: sourceSiteSelect?.value || selectedSourceSiteKey || null,
      destination_site_key: destinationSiteSelect?.value || selectedDestinationSiteKey || null,
      profile: selectedProfile,
    };

    const response = await fetch(API.sharepointRun, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      renderResult(
        {
          ok: false,
          error: data?.detail || "Error ejecutando pipeline SharePoint.",
          steps: [],
          generated_files: [],
        },
        "sharepoint"
      );
      return;
    }

    renderResult(data, "sharepoint");
  } catch (error) {
    renderFatalError(error);
  }
}

async function loadSharePointFolder(folderId = null, resetStack = false, preserveStack = false) {
  const params = new URLSearchParams();
  if (folderId) params.set("folder_id", folderId);
  if (currentModalSiteKey) params.set("site_key", currentModalSiteKey);

  const response = await fetch(`${API.sharepointExplore}?${params.toString()}`);
  const data = await response.json();

  if (!response.ok || !data.ok) {
    throw new Error(data?.detail || "No se pudo explorar SharePoint");
  }

  const currentFolder = data.current_folder || null;
  const items = Array.isArray(data.items) ? data.items : [];

  currentSharePointFolderId = currentFolder?.id || null;
  currentSharePointFolderName = currentFolder?.name || "Raíz";

  if (spCurrentPathLabel) {
    spCurrentPathLabel.textContent = currentSharePointFolderName || "Raíz";
  }

  if (resetStack) {
    spFolderStack = [];
  }

  if (!preserveStack) {
    const currentEntry = {
      id: currentSharePointFolderId,
      name: currentSharePointFolderName,
    };

    const last = spFolderStack[spFolderStack.length - 1];
    if (!last || last.id !== currentEntry.id) {
      spFolderStack.push(currentEntry);
    }
  }

  renderSharePointBrowser(items);
}

function renderSharePointBrowser(items) {
  if (!spModalBody) return;

  if (!items.length) {
    spModalBody.innerHTML = `<div class="browser-empty">No hay elementos en esta carpeta.</div>`;
    return;
  }

  spModalBody.innerHTML = "";

  for (const item of items) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "browser-item";

    const isFolder = !!item.is_folder;
    const isFile = !!item.is_file;

    row.innerHTML = `
      <div class="browser-item-main">
        <span class="browser-item-icon">${isFolder ? "📁" : "📄"}</span>
        <div>
          <div class="browser-item-title">${escapeHtml(item.name || "Sin nombre")}</div>
          <div class="browser-item-meta">${isFolder ? "Carpeta" : "Archivo"}</div>
        </div>
      </div>
    `;

    row.addEventListener("click", async () => {
      if (isFolder) {
        await loadSharePointFolder(item.id);
        return;
      }

      if (spBrowseMode === "source" && isFile) {
        selectedSourceFileId = item.id;
        selectedSourceFileName = item.name;
        selectedSourceSiteKey = currentModalSiteKey;
        if (sourceSiteSelect) sourceSiteSelect.value = currentModalSiteKey;
        syncPickedLabels();
      }
    });

    spModalBody.appendChild(row);
  }
}