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
  if (modalSiteSelect) {
    modalSiteSelect.value = currentModalSiteKey;
  }
  applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
  openSPModal();
  await loadSharePointFolder(null, true);
});

pickSPFolderBtn?.addEventListener("click", async () => {
  spBrowseMode = "dest";
  currentModalSiteKey = destinationSiteSelect?.value || getDefaultSiteKey();
  if (modalSiteSelect) {
    modalSiteSelect.value = currentModalSiteKey;
  }
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
    ensureValidationModal();
    await loadClients();
    await loadProfiles();

    if (sourceSiteSelect || destinationSiteSelect || modalSiteSelect) {
      await loadSharePointSites();
    }

    restoreDefaultClientSelection();
    syncPickedLabels();
    restoreJobHistoryCollapsedState();
    setTimeout(loadJobHistory, 300);
  } catch (error) {
    console.error("Init error:", error);
  }
});