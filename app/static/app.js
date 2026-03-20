const API = {
  localRun: "/api/local/run",
  sharepointRun: "/api/sharepoint/run",
  sharepointExplore: "/api/sharepoint/explore",
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

let selectedSourceFileId = null;
let selectedSourceFileName = null;
let selectedDestinationFolderId = null;
let selectedDestinationFolderName = null;

let currentSharePointFolderId = null;
let currentSharePointFolderName = null;
let spBrowseMode = "source";
let spFolderStack = [];

btnLocal?.addEventListener("click", () => switchMode("local"));
btnSP?.addEventListener("click", () => switchMode("sharepoint"));

runLocalBtn?.addEventListener("click", runLocalPipeline);
runSPBtn?.addEventListener("click", runSharePointPipeline);

pickSPFileBtn?.addEventListener("click", async () => {
  spBrowseMode = "source";
  openSPModal();
  await loadSharePointFolder(null, true);
});

pickSPFolderBtn?.addEventListener("click", async () => {
  spBrowseMode = "dest";
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
  syncPickedLabels();
  await loadSharePointFolder(currentSharePointFolderId, false, true);
});

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
    selectedSourceLabel.textContent = selectedSourceFileName || "Sin seleccionar";
  }
  if (selectedDestLabel) {
    selectedDestLabel.textContent = selectedDestinationFolderName || "Sin seleccionar";
  }
  if (spPickedSourceInline) {
    spPickedSourceInline.textContent = selectedSourceFileName || "Sin seleccionar";
  }
  if (spPickedDestInline) {
    spPickedDestInline.textContent = selectedDestinationFolderName || "Sin seleccionar";
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
    if (folderId) {
      url += `?folder_id=${encodeURIComponent(folderId)}`;
    }

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
    if (spCurrentPathLabel) {
      spCurrentPathLabel.textContent = currentSharePointFolderName;
    }

    if (resetStack) {
      spFolderStack = [];
    }

    if (!preserveStack) {
      const exists = spFolderStack.some((x) => x.id === currentSharePointFolderId);
      if (!exists) {
        spFolderStack.push({
          id: currentSharePointFolderId,
          name: currentSharePointFolderName,
        });
      }
    }

    renderSharePointModalBrowser(data);
  } catch (error) {
    spModalBody.innerHTML = `
      <div class="error-banner">
        Error cargando SharePoint: ${escapeHtml(error?.message || "desconocido")}
      </div>
    `;
  }
}

function renderSharePointModalBrowser(data) {
  const items = data.items || [];

  if (!items.length) {
    spModalBody.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📂</div>
        <p>No hay elementos en esta carpeta.</p>
      </div>
    `;
    return;
  }

  let html = `<div class="sp-list">`;

  for (const item of items) {
    const isSelectedSource = selectedSourceFileId && item.id === selectedSourceFileId;
    const isSelectedDest = selectedDestinationFolderId && item.id === selectedDestinationFolderId;

    if (item.is_folder) {
      html += `
        <div class="sp-item ${isSelectedDest ? "active-pick" : ""}">
          <div class="sp-main" data-open-folder="${escapeHtml(item.id)}">
            📁 ${escapeHtml(item.name)}
          </div>
          <div class="panel-actions" style="margin-top:0;">
            <button class="btn secondary small" data-open-folder="${escapeHtml(item.id)}" type="button">
              Abrir
            </button>
            ${
              spBrowseMode === "dest"
                ? `<button class="btn secondary small" data-select-folder="${escapeHtml(item.id)}" data-select-folder-name="${escapeHtml(item.name)}" type="button">Elegir destino</button>`
                : ""
            }
          </div>
        </div>
      `;
    } else if (item.is_file) {
      const isExcel = /\.(xlsx|xlsm)$/i.test(item.name || "");
      html += `
        <div class="sp-item ${isSelectedSource ? "active-pick" : ""}">
          <div class="sp-main">
            ${isExcel ? "📄" : "📎"} ${escapeHtml(item.name)}
          </div>
          <div class="panel-actions" style="margin-top:0;">
            ${
              isExcel && spBrowseMode === "source"
                ? `<button class="btn secondary small" data-select-file="${escapeHtml(item.id)}" data-select-file-name="${escapeHtml(item.name)}" type="button">Elegir Excel</button>`
                : `<span class="muted">${isExcel ? "Disponible" : "No compatible"}</span>`
            }
          </div>
        </div>
      `;
    }
  }

  html += `</div>`;
  spModalBody.innerHTML = html;

  spModalBody.querySelectorAll("[data-open-folder]").forEach((el) => {
    el.addEventListener("click", async () => {
      const folderId = el.getAttribute("data-open-folder");
      await loadSharePointFolder(folderId, false);
    });
  });

  spModalBody.querySelectorAll("[data-select-folder]").forEach((el) => {
    el.addEventListener("click", async () => {
      selectedDestinationFolderId = el.getAttribute("data-select-folder");
      selectedDestinationFolderName = el.getAttribute("data-select-folder-name");
      syncPickedLabels();
      await loadSharePointFolder(currentSharePointFolderId, false, true);
    });
  });

  spModalBody.querySelectorAll("[data-select-file]").forEach((el) => {
    el.addEventListener("click", async () => {
      selectedSourceFileId = el.getAttribute("data-select-file");
      selectedSourceFileName = el.getAttribute("data-select-file-name");
      syncPickedLabels();
      await loadSharePointFolder(currentSharePointFolderId, false, true);
    });
  });
}

function resetUI(labelText = "Procesando...") {
  progressCard?.classList.remove("hidden");
  resultCard?.classList.add("hidden");
  stepsDiv.innerHTML = "";
  progressFill.style.width = "0%";
  progressLabel.textContent = labelText;
  progressPercent.textContent = "0%";
  pipelineStatusBadge.textContent = "Ejecutando";
  pipelineStatusBadge.className = "status-badge running";
}

function setRunningState() {
  progressCard?.classList.remove("hidden");
  resultCard?.classList.add("hidden");
}

function renderResult(data, mode) {
  const steps = data.steps || [];
  stepsDiv.innerHTML = "";

  if (steps.length) {
    steps.forEach((step, index) => {
      const percent = Math.round(((index + 1) / steps.length) * 100);
      progressFill.style.width = `${percent}%`;
      progressPercent.textContent = `${percent}%`;
      progressLabel.textContent = `Paso ${index + 1} de ${steps.length}: ${step.name}`;

      const div = document.createElement("div");
      div.className = `step ${step.ok ? "ok" : "error"}`;
      div.innerHTML = `
        <div class="step-head">
          <div class="step-title">${escapeHtml(step.name)}</div>
          <div class="step-state">${step.ok ? "OK" : "Error"}</div>
        </div>
        ${step.stdout ? `<pre>${escapeHtml(step.stdout)}</pre>` : ""}
        ${step.stderr ? `<pre>${escapeHtml(step.stderr)}</pre>` : ""}
      `;
      stepsDiv.appendChild(div);
    });
  }

  const finalPercent = steps.length ? 100 : 0;
  progressFill.style.width = `${finalPercent}%`;
  progressPercent.textContent = `${finalPercent}%`;

  if (data.ok) {
    progressLabel.textContent = "Pipeline completado";
    pipelineStatusBadge.textContent = "Completado";
    pipelineStatusBadge.className = "status-badge success";
  } else {
    progressLabel.textContent = "Pipeline finalizó con errores";
    pipelineStatusBadge.textContent = "Error";
    pipelineStatusBadge.className = "status-badge error";
  }

  resultCard?.classList.remove("hidden");

  const generatedFiles = data.generated_files || [];
  const uploadedFiles = data.uploaded_files || [];
  const uploadedZip = data.uploaded_zip || null;
  const zipFile = data.zip_file || null;

  resultContent.innerHTML = `
    <div class="result-grid">
      <div class="result-kpi">
        <span>Job ID</span>
        <strong>${escapeHtml(data.job_id || "-")}</strong>
      </div>
      <div class="result-kpi">
        <span>Estado</span>
        <strong>${data.ok ? "OK" : "Con error"}</strong>
      </div>
      <div class="result-kpi">
        <span>Generados</span>
        <strong>${generatedFiles.length}</strong>
      </div>
      <div class="result-kpi">
        <span>Subidos</span>
        <strong>${uploadedFiles.length}</strong>
      </div>
    </div>

    ${
      mode === "sharepoint" && uploadedFiles.length
        ? `
          <h4>Archivos en SharePoint</h4>
          <div class="file-list">
            ${uploadedFiles
              .map((file) => {
                const name = escapeHtml(file.name || "archivo");
                const action = file.web_url
                  ? `<a class="btn secondary small" target="_blank" rel="noopener noreferrer" href="${file.web_url}">Abrir</a>`
                  : `<span class="muted">Sin link</span>`;
                return `
                  <div class="file-item">
                    <div class="file-name">${name}</div>
                    <div>${action}</div>
                  </div>
                `;
              })
              .join("")}
          </div>
        `
        : ""
    }

    ${
      mode === "sharepoint" && uploadedZip && uploadedZip.web_url
        ? `
          <div class="panel-actions">
            <a class="btn primary" target="_blank" rel="noopener noreferrer" href="${uploadedZip.web_url}">
              Abrir ZIP en SharePoint
            </a>
          </div>
        `
        : ""
    }

    ${
      mode === "local" && zipFile
        ? `
          <div class="panel-actions">
            <div class="notice">
              ZIP generado: <strong>${escapeHtml(zipFile)}</strong>
            </div>
          </div>
        `
        : ""
    }

    ${
      data.error
        ? `<div class="error-banner"><strong>Error:</strong> ${escapeHtml(data.error)}</div>`
        : ""
    }
  `;
}

function renderFatalError(error) {
  progressCard?.classList.remove("hidden");
  resultCard?.classList.remove("hidden");
  progressFill.style.width = "100%";
  progressPercent.textContent = "100%";
  progressLabel.textContent = "Error inesperado";
  pipelineStatusBadge.textContent = "Error";
  pipelineStatusBadge.className = "status-badge error";

  resultContent.innerHTML = `
    <div class="error-banner">
      <strong>Error inesperado:</strong> ${escapeHtml(error?.message || "desconocido")}
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

syncPickedLabels();