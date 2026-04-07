const PREFS_KEY = "voucher_prefs";

function savePrefs(prefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}

function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
  } catch {
    return {};
  }
}

function persistSourceFolderPreference(folderId, folderName, siteKey) {
  if (!folderId || !siteKey) return;

  const prefs = loadPrefs();
  prefs.sourceFolderId = folderId;
  prefs.sourceFolderName = folderName || "Carpeta recordada";
  prefs.sourceFolderSite = siteKey;
  savePrefs(prefs);
}

/* -------------------------------------------------------------------------- */
/* AUTH / SESSION HARDENING                                                    */
/* -------------------------------------------------------------------------- */

const originalFetch = window.fetch.bind(window);

let authState = {
  authenticated: false,
  user: null,
  reason: null,
};

let sessionExpiredAlertShown = false;

function isAuthStatusEndpoint(input) {
  const url = typeof input === "string" ? input : input?.url || "";
  return url.includes("/auth/session-status");
}

function shouldHandleAuthFailure(input) {
  const url = typeof input === "string" ? input : input?.url || "";
  return (
    url.includes("/api/sharepoint/") ||
    url.includes("/auth/session-status")
  );
}

function setSharePointControlsEnabled(enabled) {
  const elements = [
    runSPBtn,
    pickSPFileBtn,
    pickSPFolderBtn,
    sourceSiteSelect,
    destinationSiteSelect,
    modalSiteSelect,
    sharepointProfileSelect,
  ];

  for (const el of elements) {
    if (!el) continue;
    el.disabled = !enabled;
    el.classList.toggle("is-disabled", !enabled);
  }

  if (spSection) {
    spSection.classList.toggle("is-disabled", !enabled);
  }
}

function ensureSessionBanner() {
  let banner = document.getElementById("session-banner");
  if (banner) return banner;

  const topbarActions = document.querySelector(".topbar-actions");
  if (!topbarActions) return null;

  banner = document.createElement("div");
  banner.id = "session-banner";
  banner.className = "notice warning hidden";
  banner.style.minWidth = "260px";
  topbarActions.prepend(banner);
  return banner;
}

function getLoginButton() {
  return document.querySelector('a[href="/auth/login"]');
}

function getLogoutButton() {
  return document.querySelector('a[href="/auth/logout"]');
}

function getUserPill() {
  return document.querySelector(".user-pill");
}

function renderUserPillAuthenticated(user) {
  const pill = getUserPill();
  if (!pill) return;

  pill.classList.add("success");
  pill.innerHTML = `
    <div class="user-avatar user-avatar-status" aria-label="Usuario conectado">
      <span class="status-dot status-dot-online"></span>
    </div>
    <div>
      <strong>${escapeHtml(user?.name || "Usuario autenticado")}</strong>
      <small>${escapeHtml(user?.email || "")}</small>
    </div>
  `;
}

function renderUserPillUnauthenticated(expired = false) {
  const pill = getUserPill();
  if (!pill) return;

  pill.classList.remove("success");
  pill.innerHTML = `
    <div class="user-avatar user-avatar-status" aria-label="Sin sesión activa">
      <span class="status-dot status-dot-idle"></span>
    </div>
    <div>
      <strong>SharePoint</strong>
      <small>${expired ? "Sesión vencida. Volvé a iniciar sesión" : "Conectá tu cuenta Microsoft"}</small>
    </div>
  `;
}

function applyAuthStateToUI(state) {
  authState = {
    authenticated: !!state?.authenticated,
    user: state?.user || null,
    reason: state?.reason || null,
  };

  const banner = ensureSessionBanner();
  const loginBtn = getLoginButton();
  const logoutBtn = getLogoutButton();

  if (authState.authenticated) {
    renderUserPillAuthenticated(authState.user);

    if (banner) {
      banner.textContent = "";
      banner.classList.add("hidden");
    }

    if (loginBtn) loginBtn.classList.add("hidden");
    if (logoutBtn) logoutBtn.classList.remove("hidden");

    setSharePointControlsEnabled(true);
    sessionExpiredAlertShown = false;
    return;
  }

  const expired = authState.reason === "expired";
  renderUserPillUnauthenticated(expired);

  if (banner) {
    banner.textContent = expired
      ? "Tu sesión de Microsoft expiró. Volvé a iniciar sesión para usar SharePoint."
      : "Iniciá sesión con Microsoft para usar SharePoint.";
    banner.classList.remove("hidden");
  }

  if (loginBtn) loginBtn.classList.remove("hidden");
  if (logoutBtn) logoutBtn.classList.add("hidden");

  setSharePointControlsEnabled(false);
}

async function fetchSessionStatus() {
  const resp = await originalFetch("/auth/session-status", {
    credentials: "same-origin",
    cache: "no-store",
  });

  if (!resp.ok) {
    throw new Error("No se pudo validar la sesión");
  }

  return await resp.json();
}

async function initAuthState() {
  try {
    const status = await fetchSessionStatus();
    applyAuthStateToUI(status);
  } catch (err) {
    applyAuthStateToUI({
      authenticated: false,
      reason: "unknown",
      user: null,
    });
    console.error("Error validando sesión:", err);
  }
}

function handleExpiredSessionUI() {
  applyAuthStateToUI({
    authenticated: false,
    reason: "expired",
    user: null,
  });

  if (!sessionExpiredAlertShown) {
    sessionExpiredAlertShown = true;
    alert("Tu sesión de Microsoft expiró. Volvé a iniciar sesión.");
  }
}

async function fetchWithAuthHandling(input, init = {}) {
  const mergedInit = {
    credentials: "same-origin",
    cache: "no-store",
    ...init,
  };

  const response = await originalFetch(input, mergedInit);

  if (
    shouldHandleAuthFailure(input) &&
    !isAuthStatusEndpoint(input) &&
    (response.status === 401 || response.status === 403)
  ) {
    handleExpiredSessionUI();
    throw new Error("SESSION_EXPIRED");
  }

  return response;
}

window.fetch = fetchWithAuthHandling;

/* -------------------------------------------------------------------------- */
/* API                                                                         */
/* -------------------------------------------------------------------------- */

const API = {
  localRun: "/api/local/run",
  sharepointRun: "/api/sharepoint/run",
  sharepointSites: "/api/sharepoint/sites",
  sharepointExplore: "/api/sharepoint/explore",
  profiles: "/api/profiles",
  clients: "/api/clients",
  jobStatus: (jobId) => `/api/jobs/${encodeURIComponent(jobId)}`,
};

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
const cancelJobBtn = document.getElementById("cancelJobBtn");

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

let activeJobPollTimer = null;
let activeJobId = null;

window.pipelineExecutionLocked = false;

function setPipelineButtonsDisabled(disabled) {
  if (runLocalBtn) runLocalBtn.disabled = disabled;
  if (runSPBtn) runSPBtn.disabled = disabled || !authState.authenticated;

  runLocalBtn?.classList.toggle("is-disabled", disabled);
  runSPBtn?.classList.toggle("is-disabled", disabled || !authState.authenticated);
}

function lockPipelineExecution() {
  if (window.pipelineExecutionLocked) {
    return false;
  }

  window.pipelineExecutionLocked = true;
  setPipelineButtonsDisabled(true);
  return true;
}

function unlockPipelineExecution() {
  window.pipelineExecutionLocked = false;
  setPipelineButtonsDisabled(false);
}

/* -------------------------------------------------------------------------- */
/* Helpers                                                                     */
/* -------------------------------------------------------------------------- */

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

function getStepLabel(stepName) {
  const labels = {
    preparing_local_job: "Preparando ejecución local",
    preparing_sharepoint_job: "Preparando ejecución SharePoint",
    loading_sharepoint_source: "Descargando archivo desde SharePoint",
    uploading_outputs: "Subiendo resultados a SharePoint",
    xlsx_to_voucher_json: "Preparando vouchers",
    enrich_hotels: "Obteniendo información de hoteles",
    render_vouchers_html: "Generando vouchers",
    render_vouchers_pdf: "Generando PDFs finales",
  };
  return labels[stepName] || stepName || "Procesando";
}

function openSPModal() {
  if (!spModal) return;
  spModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeSPModal() {
  if (!spModal) return;
  spModal.classList.add("hidden");
  document.body.style.overflow = "";
}

function syncPickedLabels() {
  const sourceText = selectedSourceFileName
    ? `${selectedSourceFileName}${selectedSourceSiteKey ? ` · ${selectedSourceSiteKey}` : ""}`
    : "Sin seleccionar";

  const destText = selectedDestinationFolderName
    ? `${selectedDestinationFolderName}${selectedDestinationSiteKey ? ` · ${selectedDestinationSiteKey}` : ""}`
    : "Sin seleccionar";

  if (selectedSourceLabel) selectedSourceLabel.textContent = sourceText;
  if (selectedDestLabel) selectedDestLabel.textContent = destText;
  if (spPickedSourceInline) spPickedSourceInline.textContent = sourceText;
  if (spPickedDestInline) spPickedDestInline.textContent = destText;
}

async function loadSharePointFolder(folderId = null, resetStack = false, preserveStack = false) {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  const siteKey = currentModalSiteKey || modalSiteSelect?.value || getDefaultSiteKey();
  const params = new URLSearchParams();

  if (siteKey) {
    params.set("site_key", siteKey);
  }

  if (folderId) {
    params.set("folder_id", folderId);
  }

  const response = await fetch(`${API.sharepointExplore}?${params.toString()}`);
  const data = await response.json();

  if (!response.ok || !data?.ok) {
    throw new Error(data?.detail || "No se pudo explorar SharePoint");
  }

  const currentFolder = data.current_folder || null;
  const items = Array.isArray(data.items) ? data.items : [];

  currentSharePointFolderId = currentFolder?.id || null;
  currentSharePointFolderName =
    currentFolder?.name ||
    currentFolder?.path ||
    data.site_label ||
    "Raíz";

  currentModalSiteKey = data.site_key || siteKey;

  if (modalSiteSelect && currentModalSiteKey) {
    modalSiteSelect.value = currentModalSiteKey;
  }

  if (spCurrentPathLabel) {
    spCurrentPathLabel.textContent =
      currentFolder?.path ||
      currentFolder?.name ||
      "Raíz";
  }

  if (spModalTitle) {
    spModalTitle.textContent =
      spBrowseMode === "source"
        ? "Seleccionar Excel de origen"
        : "Seleccionar carpeta destino";
  }

  if (selectCurrentFolderBtn) {
    selectCurrentFolderBtn.classList.toggle("hidden", spBrowseMode !== "dest");
  }

  if (resetStack) {
    spFolderStack = [];
  }

  if (currentFolder?.id) {
    const alreadyInStack = spFolderStack.some((x) => x.id === currentFolder.id);

    if (!alreadyInStack) {
      spFolderStack.push({
        id: currentFolder.id,
        name: currentSharePointFolderName,
      });
    }
  }

  if (spBrowseMode === "source" && currentSharePointFolderId && currentModalSiteKey) {
    persistSourceFolderPreference(
      currentSharePointFolderId,
      currentSharePointFolderName,
      currentModalSiteKey
    );
  }

  if (!spModalBody) return;

  if (!items.length) {
    spModalBody.innerHTML = `
      <div class="empty-state">
        <div>
          <div class="empty-icon">📂</div>
          <div>No hay elementos en esta carpeta.</div>
        </div>
      </div>
    `;
    return;
  }

  const rows = items
    .map((item) => {
      const isFolder = !!item.is_folder;
      const isFile = !!item.is_file;
      const itemName = escapeHtml(item.name || "Sin nombre");
      const itemId = String(item.id || "");
      const itemPath = escapeHtml(item.path || "");
      const icon = isFolder ? "📁" : "📄";

      if (isFolder) {
        return `
          <div class="browser-row browser-row-clickable" data-folder-id="${itemId}">
            <div class="browser-main">
              <div class="browser-name">
                <span class="browser-icon">${icon}</span>
                <span>${itemName}</span>
              </div>
            </div>
            <div class="browser-actions">
              ${
                spBrowseMode === "dest"
                  ? `<button class="btn secondary small" type="button" data-use-folder-id="${itemId}" data-use-folder-name="${itemName}">
                      Usar carpeta
                    </button>`
                  : ""
              }
            </div>
          </div>
        `;
      }

      if (isFile) {
        const isExcel = /\.(xlsx|xlsm|xls)$/i.test(item.name || "");
        return `
          <div class="browser-row ${isExcel ? "browser-row-clickable" : ""}" ${isExcel ? `data-file-id="${itemId}" data-file-name="${itemName}"` : ""}>
            <div class="browser-main">
              <div class="browser-name">
                <span class="browser-icon">${icon}</span>
                <span>${itemName}</span>
              </div>
              ${itemPath ? `<div class="browser-meta">${itemPath}</div>` : ""}
            </div>
            <div class="browser-actions">
              ${
                isExcel && spBrowseMode === "source"
                  ? `<button class="btn secondary small" type="button" data-pick-file-id="${itemId}" data-pick-file-name="${itemName}">
                      Elegir
                    </button>`
                  : `<span class="muted-pill">Solo lectura</span>`
              }
            </div>
          </div>
        `;
      }

      return "";
    })
    .join("");

  spModalBody.innerHTML = `<div class="browser-list">${rows}</div>`;

  spModalBody.querySelectorAll("[data-folder-id]").forEach((el) => {
    el.addEventListener("click", async (event) => {
      const folderTarget = event.currentTarget;
      const nextFolderId = folderTarget.getAttribute("data-folder-id");
      if (!nextFolderId) return;
      await loadSharePointFolder(nextFolderId, false, false);
    });
  });

  spModalBody.querySelectorAll("[data-use-folder-id]").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.stopPropagation();

      const folderIdToUse = btn.getAttribute("data-use-folder-id");
      const folderNameToUse = btn.getAttribute("data-use-folder-name");

      selectedDestinationFolderId = folderIdToUse;
      selectedDestinationFolderName = folderNameToUse;
      selectedDestinationSiteKey = currentModalSiteKey;

      const prefs = loadPrefs();
      prefs.destFolderId = selectedDestinationFolderId;
      prefs.destFolderName = selectedDestinationFolderName;
      prefs.destFolderSite = selectedDestinationSiteKey;
      savePrefs(prefs);

      if (destinationSiteSelect) {
        destinationSiteSelect.value = currentModalSiteKey;
      }

      syncPickedLabels();
      closeSPModal();
    });
  });

  spModalBody.querySelectorAll("[data-pick-file-id]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();

      selectedSourceFileId = btn.getAttribute("data-pick-file-id");
      selectedSourceFileName = btn.getAttribute("data-pick-file-name");
      selectedSourceSiteKey = currentModalSiteKey;

      const prefs = loadPrefs();
      prefs.sourceFileId = selectedSourceFileId;
      prefs.sourceFileName = selectedSourceFileName;
      prefs.sourceFileSite = selectedSourceSiteKey;
      savePrefs(prefs);

      syncPickedLabels();
      closeSPModal();
    });
  });
}

/* -------------------------------------------------------------------------- */
/* Client / profile / sites                                                    */
/* -------------------------------------------------------------------------- */

function applyDefaultProfileForSite(siteKey, mode = "sharepoint") {
  const site = getSiteConfig(siteKey);
  const defaultProfile = site?.default_profile || "default";

  if (mode === "local") {
    if (localProfileSelect) {
      localProfileSelect.value = defaultProfile;
    }
    return;
  }

  if (sharepointProfileSelect) {
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

  const prefs = loadPrefs();
  const saved = prefs.client || localStorage.getItem("voucherClientKey");

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

  const prefs = loadPrefs();
  prefs.client = selectedClient.key;
  savePrefs(prefs);

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
  try {
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
  } catch (error) {
    if (error.message === "SESSION_EXPIRED") return;
    throw error;
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

// ==========================
// MODE SWITCH
// ==========================

function switchMode(mode) {
  const isLocal = mode === "local";

  btnLocal?.classList.toggle("active", isLocal);
  btnSP?.classList.toggle("active", !isLocal);

  localSection?.classList.toggle("hidden", !isLocal);
  spSection?.classList.toggle("hidden", isLocal);

  if (isLocal) {
    if (selectedClient?.default_profile && localProfileSelect) {
      localProfileSelect.value = selectedClient.default_profile;
    }
  } else {
    if (selectedClient?.default_profile && sharepointProfileSelect) {
      sharepointProfileSelect.value = selectedClient.default_profile;
    }
  }

  if (!isLocal && !authState.authenticated) {
    setSharePointControlsEnabled(false);
  }
}

/* -------------------------------------------------------------------------- */
/* Events                                                                      */
/* -------------------------------------------------------------------------- */

btnLocal?.addEventListener("click", () => switchMode("local"));
btnSP?.addEventListener("click", () => switchMode("sharepoint"));

runLocalBtn?.addEventListener("click", runLocalPipeline);

runSPBtn?.addEventListener("click", async (...args) => {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }
  return runSharePointPipeline(...args);
});

cancelJobBtn?.addEventListener("click", async () => {
  if (!window.currentRunningJobId) return;

  try {
    await fetch(`/api/jobs/${window.currentRunningJobId}/cancel`, {
      method: "POST",
    });

    progressLabel.textContent = "Cancelando ejecución...";
  } catch (err) {
    console.error("Error cancelando job", err);
  }
});

pickSPFileBtn?.addEventListener("click", async () => {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  const prefs = loadPrefs();

  spBrowseMode = "source";
  currentModalSiteKey = sourceSiteSelect?.value || getDefaultSiteKey();

  if (modalSiteSelect) {
    modalSiteSelect.value = currentModalSiteKey;
  }

  applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
  openSPModal();

  if (
    prefs.sourceFolderId &&
    prefs.sourceFolderSite &&
    prefs.sourceFolderSite === currentModalSiteKey
  ) {
    await loadSharePointFolder(prefs.sourceFolderId, true);
    return;
  }

  await loadSharePointFolder(null, true);
});

pickSPFolderBtn?.addEventListener("click", async () => {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  const prefs = loadPrefs();

  spBrowseMode = "dest";
  currentModalSiteKey = destinationSiteSelect?.value || getDefaultSiteKey();

  if (modalSiteSelect) {
    modalSiteSelect.value = currentModalSiteKey;
  }

  openSPModal();

  if (
    prefs.destFolderId &&
    prefs.destFolderSite &&
    prefs.destFolderSite === currentModalSiteKey
  ) {
    await loadSharePointFolder(prefs.destFolderId, true);
    return;
  }

  await loadSharePointFolder(null, true);
});

closeSPModalBtn?.addEventListener("click", closeSPModal);
spModalBackdrop?.addEventListener("click", closeSPModal);

confirmSPSelectionBtn?.addEventListener("click", () => {
  syncPickedLabels();
  closeSPModal();
});

spBackBtn?.addEventListener("click", async () => {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  if (spFolderStack.length <= 1) {
    await loadSharePointFolder(null, true);
    return;
  }

  spFolderStack.pop();
  const previous = spFolderStack[spFolderStack.length - 1] || null;
  await loadSharePointFolder(previous?.id || null, false, true);
});

selectCurrentFolderBtn?.addEventListener("click", async () => {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  if (!currentSharePointFolderId) return;

  selectedDestinationFolderId = currentSharePointFolderId;
  selectedDestinationFolderName = currentSharePointFolderName;
  selectedDestinationSiteKey = currentModalSiteKey;

  const prefs = loadPrefs();
  prefs.destFolderId = selectedDestinationFolderId;
  prefs.destFolderName = selectedDestinationFolderName;
  prefs.destFolderSite = selectedDestinationSiteKey;
  savePrefs(prefs);

  if (destinationSiteSelect) {
    destinationSiteSelect.value = currentModalSiteKey;
  }

  syncPickedLabels();
  await loadSharePointFolder(currentSharePointFolderId, false, true);
});

modalSiteSelect?.addEventListener("change", async () => {
  if (!authState.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  currentModalSiteKey = modalSiteSelect.value;

  if (spBrowseMode === "source") {
    applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
  }

  await loadSharePointFolder(null, true);
});

sourceSiteSelect?.addEventListener("change", () => {
  const selectedKey = sourceSiteSelect.value;
  applyDefaultProfileForSite(selectedKey, "sharepoint");

  const prefs = loadPrefs();
  prefs.sourceSite = selectedKey;

  if (prefs.sourceFolderSite && prefs.sourceFolderSite !== selectedKey) {
    delete prefs.sourceFolderId;
    delete prefs.sourceFolderName;
    delete prefs.sourceFolderSite;
  }

  savePrefs(prefs);

  if (selectedSourceSiteKey !== selectedKey) {
    selectedSourceFileId = null;
    selectedSourceFileName = null;
    selectedSourceSiteKey = null;
    syncPickedLabels();
  }
});

destinationSiteSelect?.addEventListener("change", () => {
  const selectedKey = destinationSiteSelect.value;

  const prefs = loadPrefs();
  prefs.destSite = selectedKey;

  if (prefs.destFolderSite && prefs.destFolderSite !== selectedKey) {
    delete prefs.destFolderId;
    delete prefs.destFolderName;
    delete prefs.destFolderSite;
  }

  savePrefs(prefs);

  if (selectedDestinationSiteKey !== selectedKey) {
    selectedDestinationFolderId = null;
    selectedDestinationFolderName = null;
    selectedDestinationSiteKey = null;
    syncPickedLabels();
  }
});

languageSelect?.addEventListener("change", () => {
  const prefs = loadPrefs();
  prefs.language = languageSelect.value;
  savePrefs(prefs);
});

const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const jobHistoryBody = document.getElementById("jobHistoryBody");
const toggleHistoryBtn = document.getElementById("toggleHistoryBtn");

refreshHistoryBtn?.addEventListener("click", loadJobHistory);

toggleHistoryBtn?.addEventListener("click", () => {
  const collapsed = jobHistoryBody?.classList.contains("hidden");
  setJobHistoryCollapsed(!collapsed);
});

/* -------------------------------------------------------------------------- */
/* Init                                                                        */
/* -------------------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await initAuthState();
    ensureValidationModal();

    await loadClients();
    await loadProfiles();

    if (authState.authenticated && (sourceSiteSelect || destinationSiteSelect || modalSiteSelect)) {
      await loadSharePointSites();
    }

    const prefs = loadPrefs();

    if (prefs.client && clientSelect && availableClients.some((c) => c.key === prefs.client)) {
      clientSelect.value = prefs.client;
      onClientChange({ target: clientSelect });
    } else {
      restoreDefaultClientSelection();
    }

    if (prefs.language && languageSelect) {
      languageSelect.value = prefs.language;
    }

    if (
      authState.authenticated &&
      prefs.sourceSite &&
      sourceSiteSelect &&
      sharepointSites.some((s) => s.key === prefs.sourceSite)
    ) {
      sourceSiteSelect.value = prefs.sourceSite;
    }

    if (
      authState.authenticated &&
      prefs.destSite &&
      destinationSiteSelect &&
      sharepointSites.some((s) => s.key === prefs.destSite)
    ) {
      destinationSiteSelect.value = prefs.destSite;
    }

    if (
      authState.authenticated &&
      prefs.destFolderId &&
      prefs.destFolderSite &&
      destinationSiteSelect &&
      prefs.destFolderSite === destinationSiteSelect.value
    ) {
      selectedDestinationFolderId = prefs.destFolderId;
      selectedDestinationFolderName = prefs.destFolderName || "Carpeta recordada";
      selectedDestinationSiteKey = prefs.destFolderSite;
    }

    syncPickedLabels();
    restoreJobHistoryCollapsedState();
    setTimeout(loadJobHistory, 300);
  } catch (error) {
    console.error("Init error:", error);
  }
});