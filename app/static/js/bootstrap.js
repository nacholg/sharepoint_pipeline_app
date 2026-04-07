(function () {
  function switchMode(mode) {
    const isLocal = mode === "local";

    window.btnLocal?.classList.toggle("active", isLocal);
    window.btnSP?.classList.toggle("active", !isLocal);

    window.localSection?.classList.toggle("hidden", !isLocal);
    window.spSection?.classList.toggle("hidden", isLocal);

    if (isLocal) {
      if (window.selectedClient?.default_profile && window.localProfileSelect) {
        window.localProfileSelect.value = window.selectedClient.default_profile;
      }
    } else {
      if (window.selectedClient?.default_profile && window.sharepointProfileSelect) {
        window.sharepointProfileSelect.value = window.selectedClient.default_profile;
      }
    }

    if (!isLocal && !window.authState?.authenticated) {
      window.setSharePointControlsEnabled?.(false);
    }
  }

  function setPipelineButtonsDisabled(disabled) {
    if (window.runLocalBtn) window.runLocalBtn.disabled = disabled;
    if (window.runSPBtn) window.runSPBtn.disabled = disabled || !window.authState?.authenticated;

    window.runLocalBtn?.classList.toggle("is-disabled", disabled);
    window.runSPBtn?.classList.toggle("is-disabled", disabled || !window.authState?.authenticated);
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

  let staticEventsBound = false;
  let sharepointPickerBound = false;

  function bindStaticEvents() {
    if (staticEventsBound) return;
    staticEventsBound = true;

    window.btnLocal?.addEventListener("click", (event) => {
      event.preventDefault?.();
      switchMode("local");
    });

    window.btnSP?.addEventListener("click", (event) => {
      event.preventDefault?.();
      switchMode("sharepoint");
    });

    window.runLocalBtn?.addEventListener("click", window.runLocalPipeline);

    window.runSPBtn?.addEventListener("click", async (...args) => {
      if (!window.authState?.authenticated) {
        window.handleExpiredSessionUI?.();
        return;
      }
      return window.runSharePointPipeline?.(...args);
    });

    window.cancelJobBtn?.addEventListener("click", async () => {
      if (!window.currentRunningJobId) return;

      try {
        await fetch(window.API.jobCancel(window.currentRunningJobId), {
          method: "POST",
        });

        if (window.progressLabel) {
          window.progressLabel.textContent = "Cancelando ejecución...";
        }
      } catch (err) {
        console.error("Error cancelando job", err);
      }
    });

    window.refreshHistoryBtn?.addEventListener("click", window.loadJobHistory);

    window.toggleHistoryBtn?.addEventListener("click", () => {
      const collapsed = window.jobHistoryBody?.classList.contains("hidden");
      window.setJobHistoryCollapsed?.(!collapsed);
    });

    window.sourceSiteSelect?.addEventListener("change", () => {
      const selectedKey = window.sourceSiteSelect.value;
      window.applyDefaultProfileForSite?.(selectedKey, "sharepoint");

      const prefs = window.loadPrefs();
      prefs.sourceSite = selectedKey;

      if (prefs.sourceFolderSite && prefs.sourceFolderSite !== selectedKey) {
        delete prefs.sourceFolderId;
        delete prefs.sourceFolderName;
        delete prefs.sourceFolderSite;
      }

      window.savePrefs(prefs);

      if (window.selectedSourceSiteKey !== selectedKey) {
        window.selectedSourceFileId = null;
        window.selectedSourceFileName = null;
        window.selectedSourceSiteKey = null;
        window.syncPickedLabels?.();
      }
    });

    window.destinationSiteSelect?.addEventListener("change", () => {
      const selectedKey = window.destinationSiteSelect.value;

      const prefs = window.loadPrefs();
      prefs.destSite = selectedKey;

      if (prefs.destFolderSite && prefs.destFolderSite !== selectedKey) {
        delete prefs.destFolderId;
        delete prefs.destFolderName;
        delete prefs.destFolderSite;
      }

      window.savePrefs(prefs);

      if (window.selectedDestinationSiteKey !== selectedKey) {
        window.selectedDestinationFolderId = null;
        window.selectedDestinationFolderName = null;
        window.selectedDestinationSiteKey = null;
        window.syncPickedLabels?.();
      }
    });

    window.languageSelect?.addEventListener("change", () => {
      const prefs = window.loadPrefs();
      prefs.language = window.languageSelect.value;
      window.savePrefs(prefs);
    });
  }

  function bindSharePointPickerEarly() {
    if (sharepointPickerBound) return;
    if (typeof window.bindSharePointPickerEvents !== "function") return;

    window.bindSharePointPickerEvents();
    sharepointPickerBound = true;
  }

  async function bootstrapApp() {
    bindStaticEvents();
    bindSharePointPickerEarly();

    switchMode("local");

    try {
      window.installFetchInterceptor?.();
      await window.initAuthState?.();

      window.ensureValidationModal?.();

      await window.loadClients?.();
      await window.loadProfiles?.();

      if (
        window.authState?.authenticated &&
        (window.sourceSiteSelect || window.destinationSiteSelect || window.modalSiteSelect)
      ) {
        await window.loadSharePointSites?.();
      }

      const prefs = window.loadPrefs();

      if (
        prefs.client &&
        window.clientSelect &&
        window.availableClients.some((c) => c.key === prefs.client)
        ) {
        window.clientSelect.value = prefs.client;
        window.onClientChange?.({ target: window.clientSelect });
        } else {
        window.restoreDefaultClientSelection?.();
        }

        if (!window.selectedClient && window.clientSelect?.value) {
        window.onClientChange?.({ target: window.clientSelect });
        }

      if (prefs.language && window.languageSelect) {
        window.languageSelect.value = prefs.language;
      }

      if (
        window.authState?.authenticated &&
        prefs.sourceSite &&
        window.sourceSiteSelect &&
        window.sharepointSites.some((s) => s.key === prefs.sourceSite)
      ) {
        window.sourceSiteSelect.value = prefs.sourceSite;
      }

      if (
        window.authState?.authenticated &&
        prefs.destSite &&
        window.destinationSiteSelect &&
        window.sharepointSites.some((s) => s.key === prefs.destSite)
      ) {
        window.destinationSiteSelect.value = prefs.destSite;
      }

      if (
        window.authState?.authenticated &&
        prefs.destFolderId &&
        prefs.destFolderSite &&
        window.destinationSiteSelect &&
        prefs.destFolderSite === window.destinationSiteSelect.value
      ) {
        window.selectedDestinationFolderId = prefs.destFolderId;
        window.selectedDestinationFolderName = prefs.destFolderName || "Carpeta recordada";
        window.selectedDestinationSiteKey = prefs.destFolderSite;
      }

      window.syncPickedLabels?.();
      window.restoreJobHistoryCollapsedState?.();
      setTimeout(() => window.loadJobHistory?.(), 300);
    } catch (error) {
      console.error("Init error:", error);

      try {
        window.syncPickedLabels?.();
      } catch (e) {
        console.error("Post-init recovery error:", e);
      }
    }
  }

  window.switchMode = switchMode;
  window.setPipelineButtonsDisabled = setPipelineButtonsDisabled;
  window.lockPipelineExecution = lockPipelineExecution;
  window.unlockPipelineExecution = unlockPipelineExecution;
  window.bootstrapApp = bootstrapApp;
})();