import { dom } from "./dom.js";
import { state } from "./state.js";
import { loadPrefs, savePrefs } from "./prefs.js";
import { installFetchInterceptor, initAuthState, setSharePointControlsEnabled } from "./auth.js";
import { loadClients, loadProfiles, loadSharePointSites, restoreDefaultClientSelection, applyDefaultProfileForSite } from "./clients.js";
import { bindSharepointPickerEvents, syncPickedLabels } from "./sharepoint-picker.js";
import { bindHistoryEvents, loadJobHistory, restoreJobHistoryCollapsedState } from "./history.js";

function switchMode(mode) {
  const isLocal = mode === "local";

  dom.btnLocal?.classList.toggle("active", isLocal);
  dom.btnSP?.classList.toggle("active", !isLocal);

  dom.localSection?.classList.toggle("hidden", !isLocal);
  dom.spSection?.classList.toggle("hidden", isLocal);

  if (isLocal) {
    if (state.data.selectedClient?.default_profile && dom.localProfileSelect) {
      dom.localProfileSelect.value = state.data.selectedClient.default_profile;
    }
  } else {
    if (state.data.selectedClient?.default_profile && dom.sharepointProfileSelect) {
      dom.sharepointProfileSelect.value = state.data.selectedClient.default_profile;
    }
  }

  if (!isLocal && !state.auth.authenticated) {
    setSharePointControlsEnabled(false);
  }
}

function bindModeEvents() {
  dom.btnLocal?.addEventListener("click", () => switchMode("local"));
  dom.btnSP?.addEventListener("click", () => switchMode("sharepoint"));
}

function bindSiteEvents() {
  dom.sourceSiteSelect?.addEventListener("change", () => {
    const selectedKey = dom.sourceSiteSelect.value;
    applyDefaultProfileForSite(selectedKey, "sharepoint");

    const prefs = loadPrefs();
    prefs.sourceSite = selectedKey;
    savePrefs(prefs);
  });

  dom.destinationSiteSelect?.addEventListener("change", () => {
    const prefs = loadPrefs();
    prefs.destSite = dom.destinationSiteSelect.value;
    savePrefs(prefs);
  });

  dom.languageSelect?.addEventListener("change", () => {
    const prefs = loadPrefs();
    prefs.language = dom.languageSelect.value;
    savePrefs(prefs);
  });
}

export async function bootstrapApp() {
  try {
    installFetchInterceptor();
    await initAuthState();

    await loadClients();
    await loadProfiles();

    if (state.auth.authenticated && (dom.sourceSiteSelect || dom.destinationSiteSelect || dom.modalSiteSelect)) {
      await loadSharePointSites();
    }

    restoreDefaultClientSelection();

    const prefs = loadPrefs();
    if (prefs.language && dom.languageSelect) {
      dom.languageSelect.value = prefs.language;
    }

    bindModeEvents();
    bindSiteEvents();
    bindSharepointPickerEvents();
    bindHistoryEvents();

    syncPickedLabels();
    restoreJobHistoryCollapsedState();
    setTimeout(loadJobHistory, 300);
  } catch (error) {
    console.error("Init error:", error);
  }
}