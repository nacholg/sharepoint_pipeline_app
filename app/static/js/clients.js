(function () {
  function clientEscapeHtml(value) {
    if (typeof window.escapeHtml === "function") {
      return window.escapeHtml(value);
    }

    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getDefaultSiteKey() {
    if ((window.sharepointSites || []).find((x) => x.key === "globalevents2")) {
      return "globalevents2";
    }
    return window.sharepointSites?.[0]?.key || null;
  }

  function getSiteConfig(siteKey) {
    return (window.sharepointSites || []).find((site) => site.key === siteKey) || null;
  }

  function getClientConfig(clientKey) {
    return (window.availableClients || []).find((client) => client.key === clientKey) || null;
  }

  function requireSelectedClient() {
    if (!window.selectedClient && window.clientSelect?.value) {
        window.selectedClient = getClientConfig(window.clientSelect.value);
    }

    if (!window.selectedClient) {
        alert("Seleccioná un cliente antes de ejecutar.");
        return false;
    }

    return true;
    }

  function applyDefaultProfileForSite(siteKey, mode = "sharepoint") {
    const site = getSiteConfig(siteKey);
    const defaultProfile = site?.default_profile || "default";

    if (mode === "local") {
      if (window.localProfileSelect) {
        window.localProfileSelect.value = defaultProfile;
      }
      return;
    }

    if (window.sharepointProfileSelect) {
      window.sharepointProfileSelect.value = defaultProfile;
    }
  }

  async function loadClients() {
    const response = await fetch(window.API.clients);
    const data = await response.json();

    if (!response.ok || !data?.ok) {
      throw new Error("No se pudieron cargar los clientes");
    }

    window.availableClients = Array.isArray(data.clients) ? data.clients : [];

    if (!window.clientSelect) return;

    window.clientSelect.innerHTML = "";

    for (const client of window.availableClients) {
      const opt = document.createElement("option");
      opt.value = client.key;
      opt.textContent = client.label;
      window.clientSelect.appendChild(opt);
    }

    window.clientSelect.addEventListener("change", onClientChange);
  }

  function restoreDefaultClientSelection() {
    if (!window.clientSelect || !window.availableClients.length) return;

    const prefs = window.loadPrefs();
    const saved = prefs.client || localStorage.getItem("voucherClientKey");

    const fallback =
      saved && window.availableClients.some((c) => c.key === saved)
        ? saved
        : window.availableClients[0].key;

    window.clientSelect.value = fallback;
    onClientChange({ target: window.clientSelect });
  }

  function onClientChange(event) {
    const clientKey = event.target.value;
    window.selectedClient = getClientConfig(clientKey);

    if (!window.selectedClient) return;

    const prefs = window.loadPrefs();
    prefs.client = window.selectedClient.key;
    window.savePrefs(prefs);

    localStorage.setItem("voucherClientKey", window.selectedClient.key);

    if (window.clientMeta) {
      window.clientMeta.innerHTML = `
        <div><strong>Cliente:</strong> ${clientEscapeHtml(window.selectedClient.label)}</div>
        <div><strong>Site:</strong> ${clientEscapeHtml(window.selectedClient.site_key || "-")}</div>
        <div><strong>Profile:</strong> ${clientEscapeHtml(window.selectedClient.default_profile || "default")}</div>
        <div><strong>Carpeta default:</strong> ${clientEscapeHtml(window.selectedClient.default_folder_path || "/")}</div>
      `;
    }

    if (window.localProfileSelect) {
      window.localProfileSelect.value = window.selectedClient.default_profile || "default";
    }

    if (window.sharepointProfileSelect) {
      window.sharepointProfileSelect.value = window.selectedClient.default_profile || "default";
    }

    if (window.sourceSiteSelect && window.selectedClient.source_site_key) {
      window.sourceSiteSelect.value = window.selectedClient.source_site_key;
    } else if (window.sourceSiteSelect && window.selectedClient.site_key) {
      window.sourceSiteSelect.value = window.selectedClient.site_key;
    }

    if (window.destinationSiteSelect && window.selectedClient.destination_site_key) {
      window.destinationSiteSelect.value = window.selectedClient.destination_site_key;
    } else if (window.destinationSiteSelect && window.selectedClient.site_key) {
      window.destinationSiteSelect.value = window.selectedClient.site_key;
    }

    window.selectedSourceFileId = null;
    window.selectedSourceFileName = null;
    window.selectedSourceSiteKey = null;

    window.selectedDestinationFolderId = null;
    window.selectedDestinationFolderName = null;
    window.selectedDestinationSiteKey = null;

    if (typeof window.syncPickedLabels === "function") {
      window.syncPickedLabels();
    }

    if (typeof window.switchMode === "function") {
      window.switchMode(window.btnLocal?.classList.contains("active") ? "local" : "sharepoint");
    }
  }

  async function loadProfiles() {
    try {
      const response = await fetch(window.API.profiles);
      const data = await response.json();

      if (!response.ok || !data?.ok) return;

      window.availableProfiles = Array.isArray(data.profiles) ? data.profiles : [];
      const defaultProfile = data.default_profile || "default";

      fillProfileSelect(window.localProfileSelect, window.availableProfiles, defaultProfile);
      fillProfileSelect(window.sharepointProfileSelect, window.availableProfiles, defaultProfile);
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
      const response = await fetch(window.API.sharepointSites);
      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error("No se pudieron cargar los sites");
      }

      window.sharepointSites = data.sites || [];

      fillSiteSelect(window.sourceSiteSelect, window.sharepointSites);
      fillSiteSelect(window.destinationSiteSelect, window.sharepointSites);
      fillSiteSelect(window.modalSiteSelect, window.sharepointSites);

      const defaultKey = getDefaultSiteKey();

      if (window.sourceSiteSelect && defaultKey) window.sourceSiteSelect.value = defaultKey;
      if (window.destinationSiteSelect && defaultKey) window.destinationSiteSelect.value = defaultKey;
      if (window.modalSiteSelect && defaultKey) window.modalSiteSelect.value = defaultKey;
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

  window.getDefaultSiteKey = getDefaultSiteKey;
  window.getSiteConfig = getSiteConfig;
  window.getClientConfig = getClientConfig;
  window.requireSelectedClient = requireSelectedClient;
  window.applyDefaultProfileForSite = applyDefaultProfileForSite;
  window.loadClients = loadClients;
  window.restoreDefaultClientSelection = restoreDefaultClientSelection;
  window.onClientChange = onClientChange;
  window.loadProfiles = loadProfiles;
  window.fillProfileSelect = fillProfileSelect;
  window.loadSharePointSites = loadSharePointSites;
  window.fillSiteSelect = fillSiteSelect;
})();