const API = {
  localRun: "/api/local/run",
  sharepointRun: "/api/sharepoint/run",
  sharepointSites: "/api/sharepoint/sites",
  sharepointExplore: "/api/sharepoint/explore",
  profiles: "/api/profiles",
  clients: "/api/clients",
};

const ALLOWED_EXCEL_EXTENSIONS = [".xlsx", ".xlsm", ".xls"];

const languageSelect = document.getElementById("languageSelect");

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

const clientSelect = document.getElementById("clientSelect");
const clientMeta = document.getElementById("clientMeta");

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
let availableClients = [];
let selectedClient = null;

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

let currentWarningRows = [];
let currentErrorRows = [];

/* -------------------------------------------------------------------------- */
/* Helpers                                                                     */
/* -------------------------------------------------------------------------- */

function getSelectedLanguage() {
  return languageSelect?.value || "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getDefaultSiteKey() {
  if (sharepointSites.find((x) => x.key === "globalevents2")) {
    return "globalevents2";
  }
  return sharepointSites[0]?.key || null;
}

function getSiteConfig(siteKey) {
  return sharepointSites.find((site) => site.key === siteKey) || null;
}

function getClientConfig(clientKey) {
  return availableClients.find((client) => client.key === clientKey) || null;
}

function requireSelectedClient() {
  if (!selectedClient) {
    alert("Seleccioná un cliente antes de ejecutar.");
    return false;
  }
  return true;
}

function isValidExcelFilename(name) {
  const lowerName = (name || "").toLowerCase();
  return ALLOWED_EXCEL_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

/* -------------------------------------------------------------------------- */
/* Download actions                                                            */
/* -------------------------------------------------------------------------- */

function downloadFile(path) {
  const encoded = encodeURIComponent(path);
  window.open(`/api/download-file?path=${encoded}`, "_blank");
}

function downloadZip(path) {
  const encoded = encodeURIComponent(path);
  window.open(`/api/download-zip?path=${encoded}`, "_blank");
}

window.downloadFile = downloadFile;
window.downloadZip = downloadZip;

/* -------------------------------------------------------------------------- */
/* UI state                                                                    */
/* -------------------------------------------------------------------------- */

function resetUI(label = "Esperando ejecución") {
  statusBadge.textContent = "Idle";
  statusBadge.className = "status-badge neutral";
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

function switchMode(mode) {
  const isLocal = mode === "local";
  btnLocal?.classList.toggle("active", isLocal);
  btnSP?.classList.toggle("active", !isLocal);
  localSection?.classList.toggle("hidden", !isLocal);
  spSection?.classList.toggle("hidden", isLocal);

  if (isLocal) {
    if (selectedClient?.default_profile) {
      localProfileSelect.value = selectedClient.default_profile;
    } else {
      applyDefaultProfileForSite("globalevents2", "local");
    }
  } else {
    if (selectedClient?.default_profile) {
      sharepointProfileSelect.value = selectedClient.default_profile;
    } else {
      const selectedKey = sourceSiteSelect?.value || getDefaultSiteKey();
      applyDefaultProfileForSite(selectedKey, "sharepoint");
    }
  }
}

/* -------------------------------------------------------------------------- */
/* Client / profile / sites                                                    */
/* -------------------------------------------------------------------------- */

function applyDefaultProfileForSite(siteKey, mode = "sharepoint") {
  const site = getSiteConfig(siteKey);
  const defaultProfile = site?.default_profile || "default";

  if (mode === "local") {
    if (localProfileSelect && defaultProfile) {
      localProfileSelect.value = defaultProfile;
    }
    return;
  }

  if (sharepointProfileSelect && defaultProfile) {
    sharepointProfileSelect.value = defaultProfile;
  }
}

async function loadClients() {
  const response = await fetch(API.clients);
  const data = await response.json();

  if (!response.ok || !data?.ok) {
    throw new Error("No se pudieron cargar los clientes");
  }

  availableClients = Array.isArray(data.clients) ? data.clients : [];

  if (!clientSelect) return;

  clientSelect.innerHTML = "";

  for (const client of availableClients) {
    const opt = document.createElement("option");
    opt.value = client.key;
    opt.textContent = client.label;
    clientSelect.appendChild(opt);
  }

  clientSelect.addEventListener("change", onClientChange);
}

function restoreDefaultClientSelection() {
  if (!clientSelect || !availableClients.length) return;

  const saved = localStorage.getItem("voucherClientKey");
  const fallback =
    saved && availableClients.some((c) => c.key === saved)
      ? saved
      : availableClients[0].key;

  clientSelect.value = fallback;
  onClientChange({ target: clientSelect });
}

function onClientChange(event) {
  const clientKey = event.target.value;
  selectedClient = getClientConfig(clientKey);

  if (!selectedClient) return;

  localStorage.setItem("voucherClientKey", selectedClient.key);

  if (clientMeta) {
    clientMeta.innerHTML = `
      <div><strong>Cliente:</strong> ${escapeHtml(selectedClient.label)}</div>
      <div><strong>Site:</strong> ${escapeHtml(selectedClient.site_key || "-")}</div>
      <div><strong>Profile:</strong> ${escapeHtml(selectedClient.default_profile || "default")}</div>
      <div><strong>Carpeta default:</strong> ${escapeHtml(selectedClient.default_folder_path || "/")}</div>
    `;
  }

  if (localProfileSelect) {
    localProfileSelect.value = selectedClient.default_profile || "default";
  }

  if (sharepointProfileSelect) {
    sharepointProfileSelect.value = selectedClient.default_profile || "default";
  }

  if (sourceSiteSelect && selectedClient.source_site_key) {
    sourceSiteSelect.value = selectedClient.source_site_key;
  } else if (sourceSiteSelect && selectedClient.site_key) {
    sourceSiteSelect.value = selectedClient.site_key;
  }

  if (destinationSiteSelect && selectedClient.destination_site_key) {
    destinationSiteSelect.value = selectedClient.destination_site_key;
  } else if (destinationSiteSelect && selectedClient.site_key) {
    destinationSiteSelect.value = selectedClient.site_key;
  }

  selectedSourceFileId = null;
  selectedSourceFileName = null;
  selectedSourceSiteKey = null;

  selectedDestinationFolderId = null;
  selectedDestinationFolderName = null;
  selectedDestinationSiteKey = null;

  syncPickedLabels();
  switchMode(btnLocal?.classList.contains("active") ? "local" : "sharepoint");
}

async function loadProfiles() {
  try {
    const response = await fetch(API.profiles);
    const data = await response.json();

    if (!response.ok || !data?.ok) return;

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

/* -------------------------------------------------------------------------- */
/* SharePoint picker                                                           */
/* -------------------------------------------------------------------------- */

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

  const list = document.createElement("div");
  list.className = "browser-list";

  for (const item of items) {
    const row = document.createElement("div");
    row.className = "browser-row";

    const isFolder = !!item.is_folder;
    const isFile = !!item.is_file;

    row.innerHTML = `
      <div class="browser-main">
        <div class="browser-name">
          <span class="browser-icon">${isFolder ? "📁" : "📄"}</span>
          <span>${escapeHtml(item.name || "Sin nombre")}</span>
        </div>
        <div class="browser-meta">${isFolder ? "Carpeta" : "Archivo"}</div>
      </div>
      <div class="browser-actions"></div>
    `;

    const actions = row.querySelector(".browser-actions");

    if (isFolder) {
      const openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.className = "btn secondary small";
      openBtn.textContent = "Abrir";
      openBtn.addEventListener("click", async () => {
        await loadSharePointFolder(item.id);
      });
      actions.appendChild(openBtn);

      if (spBrowseMode === "dest") {
        const useBtn = document.createElement("button");
        useBtn.type = "button";
        useBtn.className = "btn primary small";
        useBtn.textContent = "Usar carpeta";
        useBtn.addEventListener("click", () => {
          selectedDestinationFolderId = item.id;
          selectedDestinationFolderName = item.name;
          selectedDestinationSiteKey = currentModalSiteKey;
          if (destinationSiteSelect) destinationSiteSelect.value = currentModalSiteKey;
          syncPickedLabels();
        });
        actions.appendChild(useBtn);
      }
    }

    if (isFile && spBrowseMode === "source") {
      const isExcel = isValidExcelFilename(item.name || "");

      if (!isExcel) {
        const badge = document.createElement("span");
        badge.className = "file-badge invalid";
        badge.textContent = "No válido";
        actions.appendChild(badge);
      } else {
        const pickBtn = document.createElement("button");
        pickBtn.type = "button";
        pickBtn.className = "btn primary small";
        pickBtn.textContent = "Elegir archivo";
        pickBtn.addEventListener("click", () => {
          selectedSourceFileId = item.id;
          selectedSourceFileName = item.name;
          selectedSourceSiteKey = currentModalSiteKey;
          if (sourceSiteSelect) sourceSiteSelect.value = currentModalSiteKey;
          applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
          syncPickedLabels();
        });
        actions.appendChild(pickBtn);
      }
    }

    list.appendChild(row);
  }

  spModalBody.appendChild(list);
}

/* -------------------------------------------------------------------------- */
/* Validation modal                                                            */
/* -------------------------------------------------------------------------- */

function ensureValidationModal() {
  if (document.getElementById("validationModal")) return;

  const modal = document.createElement("div");
  modal.id = "validationModal";
  modal.className = "validation-modal hidden";
  modal.innerHTML = `
    <div class="validation-modal-backdrop" id="validationModalBackdrop"></div>
    <div class="validation-modal-dialog">
      <div class="validation-modal-header">
        <h3 id="validationModalTitle">Detalle</h3>
        <button type="button" class="validation-modal-close" id="validationModalClose">×</button>
      </div>
      <div class="validation-modal-body" id="validationModalBody"></div>
    </div>
  `;
  document.body.appendChild(modal);

  document
    .getElementById("validationModalBackdrop")
    ?.addEventListener("click", closeValidationModal);

  document
    .getElementById("validationModalClose")
    ?.addEventListener("click", closeValidationModal);
}

function openValidationModal(title, rows, type = "warning") {
  ensureValidationModal();

  const modal = document.getElementById("validationModal");
  const titleEl = document.getElementById("validationModalTitle");
  const bodyEl = document.getElementById("validationModalBody");

  if (!modal || !titleEl || !bodyEl) return;

  titleEl.textContent = title;

  if (!Array.isArray(rows) || !rows.length) {
    bodyEl.innerHTML = `<p class="muted-text">No hay detalles para mostrar.</p>`;
  } else {
    bodyEl.innerHTML = rows
      .map((item) => renderValidationRowCard(item, type))
      .join("");
  }

  modal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeValidationModal() {
  const modal = document.getElementById("validationModal");
  if (!modal) return;
  modal.classList.add("hidden");
  document.body.style.overflow = "";
}

function renderValidationRowCard(item, type = "warning") {
  const row = item?.row || {};
  const issues =
    type === "error"
      ? Array.isArray(item?.errors)
        ? item.errors
        : []
      : Array.isArray(item?.warnings)
        ? item.warnings
        : [];

  const fullName =
    row.full_name ||
    [row.first_name, row.last_name].filter(Boolean).join(" ") ||
    "-";

  const excelRow = row.excel_row_number ?? "-";
  const hotel = row.hotel_name || "-";
  const room = row.room || "-";
  const destination = row.destination || "-";
  const passport = row.passport_number || "-";
  const checkIn = row.check_in || "-";
  const checkOut = row.check_out || "-";

  return `
    <article class="validation-row-card">
      <div class="validation-row-top">
        <div>
          <div class="validation-row-title">${escapeHtml(fullName)}</div>
          <div class="validation-row-subtitle">Fila Excel: ${escapeHtml(excelRow)}</div>
        </div>
        <div class="validation-row-badge ${type === "error" ? "is-error" : "is-warning"}">
          ${type === "error" ? "Error" : "Warning"}
        </div>
      </div>

      <div class="validation-row-issues">
        ${issues
          .map((issue) => `<span class="validation-issue-pill">${escapeHtml(issue)}</span>`)
          .join("")}
      </div>

      <div class="validation-row-grid">
        <div><strong>Hotel:</strong> ${escapeHtml(hotel)}</div>
        <div><strong>Destino:</strong> ${escapeHtml(destination)}</div>
        <div><strong>Hab:</strong> ${escapeHtml(room)}</div>
        <div><strong>Pasaporte:</strong> ${escapeHtml(passport)}</div>
        <div><strong>Check-in:</strong> ${escapeHtml(checkIn)}</div>
        <div><strong>Check-out:</strong> ${escapeHtml(checkOut)}</div>
      </div>
    </article>
  `;
}

/* -------------------------------------------------------------------------- */
/* Render helpers                                                              */
/* -------------------------------------------------------------------------- */

function renderStep(step) {
  const wrap = document.createElement("div");
  wrap.className = `step-item ${step.ok ? "success" : "error"}`;

  const output = [step.stdout, step.stderr].filter(Boolean).join("\n").trim();

  wrap.innerHTML = `
    <div class="step-bullet"></div>
    <div class="step-body">
      <div class="step-head">
        <div class="step-title">${escapeHtml(step.name)}</div>
        <div class="step-state">Return code: ${escapeHtml(step.returncode)}</div>
      </div>
      ${
        output
          ? `<pre class="log-block">${escapeHtml(output)}</pre>`
          : `<div class="muted-text">Sin salida</div>`
      }
    </div>
  `;

  return wrap;
}

function renderFatalError(error) {
  setFinishedState(false);

  stepsEl.innerHTML = `
    <div class="step-item error">
      <div class="step-bullet"></div>
      <div class="step-body">
        <div class="step-head">
          <div class="step-title">Error fatal</div>
        </div>
        <pre class="log-block">${escapeHtml(error?.message || String(error))}</pre>
      </div>
    </div>
  `;

  resultCard.classList.remove("hidden");
  resultContent.innerHTML = `
    <div class="error-banner">${escapeHtml(error?.message || String(error))}</div>
  `;
}

function renderValidationBlock(validation) {
  if (!validation) return "";

  const errors = Array.isArray(validation.errors) ? validation.errors : [];
  const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];

  if (!errors.length && !warnings.length) return "";

  const errorHtml = errors.length
    ? `
      <div class="validation-group validation-errors">
        <div class="validation-title">Errores de validación</div>
        <ul>
          ${errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}
        </ul>
      </div>
    `
    : "";

  const warningHtml = warnings.length
    ? `
      <div class="validation-group validation-warnings">
        <div class="validation-title">Warnings</div>
        <ul>
          ${warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}
        </ul>
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

function buildSummaryGrid(result) {
  const summary = result.pipeline_summary || {};
  const resolvedProfile = result.resolved_profile || result.profile_used || "-";
  const language = result.language || result.resolved_language || "-";

  const totalRows = summary.total_rows ?? "-";
  const validRows = summary.valid_rows ?? "-";
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
        <strong>${escapeHtml(result.client_label || "-")}</strong>
      </div>

      <div class="summary-card">
        <span>Profile</span>
        <strong>${escapeHtml(resolvedProfile)}</strong>
      </div>

      <div class="summary-card">
        <span>Idioma</span>
        <strong>${escapeHtml(language)}</strong>
      </div>

      <div class="summary-card">
        <span>Validación</span>
        <strong>${escapeHtml(validationStatus)}</strong>
      </div>

      <div class="summary-card">
        <span>Rows procesadas</span>
        <strong>${escapeHtml(totalRows)}</strong>
      </div>

      <div class="summary-card">
        <span>Rows válidas</span>
        <strong>${escapeHtml(validRows)}</strong>
      </div>

      <div
        class="summary-card summary-card-clickable"
        id="warningsSummaryCard"
        role="button"
        tabindex="0"
        onclick="window.__openWarningsModal && window.__openWarningsModal()"
      >
        <span>Warnings</span>
        <strong>${escapeHtml(warnings)}</strong>
      </div>

      <div
        class="summary-card ${typeof errors === "number" && errors > 0 ? "summary-card-clickable" : ""}"
        id="errorsSummaryCard"
        role="button"
        tabindex="0"
        onclick="window.__openErrorsModal && window.__openErrorsModal()"
      >
        <span>Errors</span>
        <strong>${escapeHtml(errors)}</strong>
      </div>

      <div class="summary-card">
        <span>Vouchers</span>
        <strong>${escapeHtml(vouchers)}</strong>
      </div>
    </div>
  `;
}

function buildDebugFilesGrid(result) {
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
              <span>${escapeHtml(item.label)}</span>
              <code>${escapeHtml(item.value)}</code>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function buildFilesSection(result) {
  const files = Array.isArray(result.generated_files) ? result.generated_files : [];

  if (!files.length) {
    return `
      <div class="result-section">
        <h4>Archivos generados</h4>
        <p class="muted-text">No hay archivos generados.</p>
      </div>
    `;
  }

  const pdfs = files.filter((f) => f.toLowerCase().endsWith(".pdf"));
  const htmls = files.filter((f) => f.toLowerCase().endsWith(".html"));
  const jsons = files.filter((f) => f.toLowerCase().endsWith(".json"));

  return `
    <div class="result-section">
      <h4>Archivos generados</h4>
      ${buildFileGroup("PDFs", pdfs, "📄")}
      ${buildFileGroup("HTML", htmls, "🌐")}
      ${buildFileGroup("Debug / JSON", jsons, "🧠")}
    </div>
  `;
}

function buildFileGroup(title, files, icon) {
  if (!files.length) return "";

  return `
    <div class="file-group">
      <div class="file-group-title">${icon} ${title}</div>
      <ul class="file-list">
        ${files
          .map((file) => {
            const cleanName = file.split("\\").pop().split("/").pop();
            return `
              <li class="file-row">
                <div class="file-main">
                  <span class="file-name">${escapeHtml(cleanName)}</span>
                  <span class="file-path">${escapeHtml(file)}</span>
                </div>
                <div class="file-actions">
                  <button class="btn small" onclick='downloadFile(${JSON.stringify(file)})'>
                    Descargar
                  </button>
                </div>
              </li>
            `;
          })
          .join("")}
      </ul>
    </div>
  `;
}

function renderResult(result, mode) {
  setFinishedState(!!result.ok);

  currentWarningRows = Array.isArray(result.warning_rows) ? result.warning_rows : [];
  currentErrorRows = Array.isArray(result.error_rows) ? result.error_rows : [];

  const steps = Array.isArray(result.steps) ? result.steps : [];
  stepsEl.innerHTML = "";

  if (steps.length) {
    for (const step of steps) {
      stepsEl.appendChild(renderStep(step));
    }
  } else {
    stepsEl.innerHTML = `
      <div class="step-item ${result.ok ? "success" : "error"}">
        <div class="step-bullet"></div>
        <div class="step-body">
          <div class="step-head">
            <div class="step-title">${result.ok ? "Sin pasos detallados" : "Error final"}</div>
          </div>
          <pre class="log-block">${escapeHtml(result.error || "Sin detalles")}</pre>
        </div>
      </div>
    `;
  }

  resultCard.classList.remove("hidden");

  const uploadedFiles = Array.isArray(result.uploaded_files) ? result.uploaded_files : [];
  const preflightValidation = result.validation || null;
  const validationHtml = renderValidationBlock(preflightValidation);

  window.__openWarningsModal = () => {
    openValidationModal("Detalle de warnings", currentWarningRows, "warning");
  };

  window.__openErrorsModal = () => {
    openValidationModal("Detalle de errores", currentErrorRows, "error");
  };

  resultContent.innerHTML = `
    ${buildSummaryGrid(result)}
    ${validationHtml}

    ${
      result.error
        ? `<div class="error-banner">${escapeHtml(result.error)}</div>`
        : ""
    }

    ${buildFilesSection(result)}

    ${
      result.zip_file
        ? `
          <div class="result-section zip-section">
            <h4>📦 Descargar resultado</h4>
            <button class="btn primary" onclick='downloadZip(${JSON.stringify(result.zip_file)})'>
              Descargar ZIP
            </button>
            <div class="zip-path">${escapeHtml(result.zip_file)}</div>
          </div>
        `
        : ""
    }

    <div class="result-section">
      <h4>Artifacts de debug</h4>
      ${buildDebugFilesGrid(result)}
    </div>

    ${
      uploadedFiles.length
        ? `
          <div class="result-section">
            <h4>Uploads a SharePoint</h4>
            <ul class="file-list">
              ${uploadedFiles
                .map((item) => {
                  const name = item.name || item.displayName || "archivo";
                  const error = item.upload_error;
                  return `
                    <li class="file-name">
                      ${escapeHtml(name)}
                      ${error ? ` — <span class="error-text">${escapeHtml(error)}</span>` : ""}
                    </li>
                  `;
                })
                .join("")}
            </ul>
          </div>
        `
        : mode === "sharepoint"
          ? `<div class="result-section"><h4>Uploads a SharePoint</h4><p class="muted-text">No hubo uploads individuales.</p></div>`
          : ""
    }
  `;
}

/* -------------------------------------------------------------------------- */
/* Pipeline execution                                                          */
/* -------------------------------------------------------------------------- */

async function runLocalPipeline() {
  if (!requireSelectedClient()) return;

  const file = fileInput?.files?.[0];
  const selectedProfile = localProfileSelect?.value || "default";
  const language = getSelectedLanguage();

  if (!file) {
    alert("Seleccioná un archivo Excel.");
    return;
  }

  if (!isValidExcelFilename(file.name || "")) {
    alert("El archivo seleccionado no es un Excel válido (.xlsx, .xlsm o .xls).");
    return;
  }

  resetUI("Ejecutando pipeline local...");
  setRunningState();

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("profile", selectedProfile);
    formData.append("client_key", selectedClient?.key || "");
    formData.append("language", language);

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
          validation: data?.validation || null,
          warning_rows: data?.warning_rows || [],
          error_rows: data?.error_rows || [],
          pipeline_summary: data?.pipeline_summary || null,
          language: data?.language || data?.resolved_language || "-",
          profile_used: data?.profile_used || data?.resolved_profile || "-",
          client_label: selectedClient?.label || "-",
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
  if (!requireSelectedClient()) return;

  const selectedProfile = sharepointProfileSelect?.value || "default";
  const language = getSelectedLanguage();

  if (!selectedSourceFileId) {
    alert("Seleccioná un Excel de origen en SharePoint.");
    return;
  }

  if (!selectedDestinationFolderId) {
    alert("Seleccioná una carpeta destino en SharePoint.");
    return;
  }

  if (!isValidExcelFilename(selectedSourceFileName || "")) {
    alert("El archivo seleccionado no es un Excel válido.");
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
      client_key: selectedClient?.key || null,
      language,
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
          validation: data?.validation || null,
          warning_rows: data?.warning_rows || [],
          error_rows: data?.error_rows || [],
          pipeline_summary: data?.pipeline_summary || null,
          language: data?.language || data?.resolved_language || "-",
          profile_used: data?.profile_used || data?.resolved_profile || "-",
          client_label: selectedClient?.label || "-",
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

/* -------------------------------------------------------------------------- */
/* Events                                                                      */
/* -------------------------------------------------------------------------- */

btnLocal?.addEventListener("click", () => switchMode("local"));
btnSP?.addEventListener("click", () => switchMode("sharepoint"));

runLocalBtn?.addEventListener("click", runLocalPipeline);
runSPBtn?.addEventListener("click", runSharePointPipeline);

pickSPFileBtn?.addEventListener("click", async () => {
  spBrowseMode = "source";
  currentModalSiteKey = sourceSiteSelect?.value || getDefaultSiteKey();
  if (modalSiteSelect) modalSiteSelect.value = currentModalSiteKey;
  applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
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

  if (destinationSiteSelect) {
    destinationSiteSelect.value = currentModalSiteKey;
  }

  syncPickedLabels();
  await loadSharePointFolder(currentSharePointFolderId, false, true);
});

modalSiteSelect?.addEventListener("change", async () => {
  currentModalSiteKey = modalSiteSelect.value;
  if (spBrowseMode === "source") {
    applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
  }
  await loadSharePointFolder(null, true);
});

sourceSiteSelect?.addEventListener("change", () => {
  const selectedKey = sourceSiteSelect.value;
  applyDefaultProfileForSite(selectedKey, "sharepoint");

  if (selectedSourceSiteKey !== selectedKey) {
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
    ensureValidationModal();
    await loadClients();
    await loadProfiles();

    if (sourceSiteSelect || destinationSiteSelect || modalSiteSelect) {
      await loadSharePointSites();
    }

    restoreDefaultClientSelection();
    syncPickedLabels();
  } catch (error) {
    console.error("Init error:", error);
  }
});