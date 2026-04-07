import { API, fetchJson } from "./api.js";
import { dom } from "./dom.js";
import { state } from "./state.js";
import { loadPrefs, savePrefs } from "./prefs.js";
import { escapeHtml } from "./helpers.js";

export function getDefaultSiteKey() {
  if (state.data.sharepointSites.find((x) => x.key === "globalevents2")) {
    return "globalevents2";
  }
  return state.data.sharepointSites[0]?.key || null;
}

export function getSiteConfig(siteKey) {
  return state.data.sharepointSites.find((site) => site.key === siteKey) || null;
}

export function getClientConfig(clientKey) {
  return state.data.availableClients.find((client) => client.key === clientKey) || null;
}

export function requireSelectedClient() {
  if (!state.data.selectedClient) {
    alert("Seleccioná un cliente antes de ejecutar.");
    return false;
  }
  return true;
}

export function applyDefaultProfileForSite(siteKey, mode = "sharepoint") {
  const site = getSiteConfig(siteKey);
  const defaultProfile = site?.default_profile || "default";

  if (mode === "local") {
    if (dom.localProfileSelect) dom.localProfileSelect.value = defaultProfile;
    return;
  }

  if (dom.sharepointProfileSelect) {
    dom.sharepointProfileSelect.value = defaultProfile;
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

export async function loadProfiles() {
  const { response, data } = await fetchJson(API.profiles);
  if (!response.ok || !data?.ok) return;

  state.data.availableProfiles = Array.isArray(data.profiles) ? data.profiles : [];
  const defaultProfile = data.default_profile || "default";

  fillProfileSelect(dom.localProfileSelect, state.data.availableProfiles, defaultProfile);
  fillProfileSelect(dom.sharepointProfileSelect, state.data.availableProfiles, defaultProfile);
}

export async function loadSharePointSites() {
  const { response, data } = await fetchJson(API.sharepointSites);
  if (!response.ok || !data?.ok) {
    throw new Error("No se pudieron cargar los sites");
  }

  state.data.sharepointSites = data.sites || [];

  fillSiteSelect(dom.sourceSiteSelect, state.data.sharepointSites);
  fillSiteSelect(dom.destinationSiteSelect, state.data.sharepointSites);
  fillSiteSelect(dom.modalSiteSelect, state.data.sharepointSites);

  const defaultKey = getDefaultSiteKey();
  if (dom.sourceSiteSelect && defaultKey) dom.sourceSiteSelect.value = defaultKey;
  if (dom.destinationSiteSelect && defaultKey) dom.destinationSiteSelect.value = defaultKey;
  if (dom.modalSiteSelect && defaultKey) dom.modalSiteSelect.value = defaultKey;
}

export function onClientChange(event) {
  const clientKey = event.target.value;
  state.data.selectedClient = getClientConfig(clientKey);
  if (!state.data.selectedClient) return;

  const prefs = loadPrefs();
  prefs.client = state.data.selectedClient.key;
  savePrefs(prefs);
  localStorage.setItem("voucherClientKey", state.data.selectedClient.key);

  if (dom.clientMeta) {
    dom.clientMeta.innerHTML = `
      <div><strong>Cliente:</strong> ${escapeHtml(state.data.selectedClient.label)}</div>
      <div><strong>Site:</strong> ${escapeHtml(state.data.selectedClient.site_key || "-")}</div>
      <div><strong>Profile:</strong> ${escapeHtml(state.data.selectedClient.default_profile || "default")}</div>
      <div><strong>Carpeta default:</strong> ${escapeHtml(state.data.selectedClient.default_folder_path || "/")}</div>
    `;
  }

  if (dom.localProfileSelect) {
    dom.localProfileSelect.value = state.data.selectedClient.default_profile || "default";
  }

  if (dom.sharepointProfileSelect) {
    dom.sharepointProfileSelect.value = state.data.selectedClient.default_profile || "default";
  }

  if (dom.sourceSiteSelect && state.data.selectedClient.source_site_key) {
    dom.sourceSiteSelect.value = state.data.selectedClient.source_site_key;
  } else if (dom.sourceSiteSelect && state.data.selectedClient.site_key) {
    dom.sourceSiteSelect.value = state.data.selectedClient.site_key;
  }

  if (dom.destinationSiteSelect && state.data.selectedClient.destination_site_key) {
    dom.destinationSiteSelect.value = state.data.selectedClient.destination_site_key;
  } else if (dom.destinationSiteSelect && state.data.selectedClient.site_key) {
    dom.destinationSiteSelect.value = state.data.selectedClient.site_key;
  }
}

export async function loadClients() {
  const { response, data } = await fetchJson(API.clients);
  if (!response.ok || !data?.ok) {
    throw new Error("No se pudieron cargar los clientes");
  }

  state.data.availableClients = Array.isArray(data.clients) ? data.clients : [];
  if (!dom.clientSelect) return;

  dom.clientSelect.innerHTML = "";
  for (const client of state.data.availableClients) {
    const opt = document.createElement("option");
    opt.value = client.key;
    opt.textContent = client.label;
    dom.clientSelect.appendChild(opt);
  }

  dom.clientSelect.addEventListener("change", onClientChange);
}

export function restoreDefaultClientSelection() {
  if (!dom.clientSelect || !state.data.availableClients.length) return;

  const prefs = loadPrefs();
  const saved = prefs.client || localStorage.getItem("voucherClientKey");

  const fallback =
    saved && state.data.availableClients.some((c) => c.key === saved)
      ? saved
      : state.data.availableClients[0].key;

  dom.clientSelect.value = fallback;
  onClientChange({ target: dom.clientSelect });
}