(function () {
  function getStepEls() {
    const steps = Array.from(document.querySelectorAll(".setup-step"));

    return {
      steps,
      step1: steps[0] || null,
      step2: steps[1] || null,
      step3: steps[2] || null,

      step1Body: document.getElementById("step1Body"),
      step2Body: document.getElementById("step2Body"),
      step3Body: document.getElementById("step3Body"),

      step1Summary: document.getElementById("step1Summary"),
      step2Summary: document.getElementById("step2Summary"),
      step3Summary: document.getElementById("step3Summary"),
    };
  }

  function getSelectedText(selectEl) {
    if (!selectEl) return "-";
    const option = selectEl.options?.[selectEl.selectedIndex];
    return option?.textContent?.trim() || selectEl.value || "-";
  }

  function isLocalMode() {
    return !!window.btnLocal?.classList.contains("active");
  }

  function canConfirmStep1() {
    return !!(window.selectedClient || window.clientSelect?.value);
  }

  function canConfirmStep2() {
    if (isLocalMode()) {
      return !!window.fileInput?.files?.[0];
    }

    return !!window.selectedSourceFileId && !!window.selectedDestinationFolderId;
  }

  function isStep1Complete() {
    return !!window.step1Confirmed;
  }

  function isStep2Complete() {
    return !!window.step2Confirmed;
  }

  function isStep3Complete() {
    const resultVisible = !!window.resultCard && !window.resultCard.classList.contains("hidden");
    const terminalStatus =
      window.statusBadge?.classList.contains("success") ||
      window.statusBadge?.classList.contains("error");

    return resultVisible || terminalStatus;
  }

  function buildStep1Summary() {
    const client =
      window.selectedClient?.label ||
      getSelectedText(window.clientSelect);

    const language = getSelectedText(window.languageSelect);

    return `
      <strong>Cliente:</strong> ${client}<br>
      <strong>Idioma:</strong> ${language}
    `;
  }
  function buildStep2Summary() {
    if (isLocalMode()) {
      const fileName = window.fileInput?.files?.[0]?.name || "Sin archivo";
      const profile = getSelectedText(window.localProfileSelect);

      return `
        <strong>Origen:</strong> Local<br>
        <strong>Archivo:</strong> ${fileName}<br>
        <strong>Profile:</strong> ${profile}
      `;
    }

    const source = window.selectedSourceLabel?.textContent?.trim() || "Sin Excel";
    const dest = window.selectedDestLabel?.textContent?.trim() || "Sin carpeta";
    const profile = getSelectedText(window.sharepointProfileSelect);

    return `
      <strong>Origen:</strong> SharePoint<br>
      <strong>Excel:</strong> ${source}<br>
      <strong>Destino:</strong> ${dest}<br>
      <strong>Profile:</strong> ${profile}
    `;
  }

  function buildStep3Summary() {
    if (isStep3Complete()) {
      return `
        <strong>Estado:</strong> Resultado disponible.
        Revisá el panel de resultados debajo.
      `;
    }

    if (isStep2Complete()) {
      return `
        <strong>Estado:</strong> Listo para ejecutar.
      `;
    }

    return `
      <strong>Estado:</strong> Completá el origen del archivo para habilitar la ejecución.
    `;
  }

  function renderStepSummary(summaryEl, html, shouldShow) {
    if (!summaryEl) return;

    summaryEl.innerHTML = html || "";

    if (shouldShow) {
      summaryEl.classList.remove("hidden");
    } else {
      summaryEl.classList.add("hidden");
    }
  }

  function refreshContinueButtons() {
    if (window.continueStep1Btn) {
      window.continueStep1Btn.disabled = !canConfirmStep1();
      window.continueStep1Btn.classList.toggle("is-disabled", !canConfirmStep1());
    }

    if (window.continueStep2Btn) {
      window.continueStep2Btn.disabled = !canConfirmStep2();
      window.continueStep2Btn.classList.toggle("is-disabled", !canConfirmStep2());
    }
  }

function refreshWizardState() {
  const {
    step1,
    step2,
    step3,
    step1Body,
    step2Body,
    step3Body,
    step1Summary,
    step2Summary,
    step3Summary,
  } = getStepEls();

  const step1Complete = isStep1Complete();
  const step2Complete = isStep2Complete();
  const step3Complete = isStep3Complete();

  let activeIndex = 0;

  if (step1Complete && !step2Complete) {
    activeIndex = 1;
  } else if (step1Complete && step2Complete) {
    activeIndex = 2;
  }

  [step1, step2, step3].forEach((step, i) => {
    if (!step) return;

    const isActive = i === activeIndex;
    const isComplete = i < activeIndex || (i === 2 && step3Complete);
    const isCollapsed = !isActive;

    step.classList.toggle("is-active", isActive);
    step.classList.toggle("is-complete", isComplete);
    step.classList.toggle("is-collapsed", isCollapsed);
  });

  if (step1Body) step1Body.classList.toggle("hidden", activeIndex !== 0);
  if (step2Body) step2Body.classList.toggle("hidden", activeIndex !== 1);
  if (step3Body) step3Body.classList.toggle("hidden", activeIndex !== 2);

  renderStepSummary(step1Summary, buildStep1Summary(), step1Complete && activeIndex !== 0);
  renderStepSummary(step2Summary, buildStep2Summary(), step2Complete && activeIndex !== 1);
  renderStepSummary(step3Summary, buildStep3Summary(), activeIndex !== 2);

  refreshContinueButtons();
}

  function switchMode(mode) {
    const isLocal = mode === "local";

    window.btnLocal?.classList.toggle("active", isLocal);
    window.btnSP?.classList.toggle("active", !isLocal);

    window.localSection?.classList.toggle("hidden", !isLocal);
    window.spSection?.classList.toggle("hidden", isLocal);

    window.runLocalBtn?.classList.toggle("hidden", !isLocal);
    window.runSPBtn?.classList.toggle("hidden", isLocal);

    window.step2Confirmed = false;

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

    refreshWizardState();
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
    refreshWizardState();
    return true;
  }

  function unlockPipelineExecution() {
    window.pipelineExecutionLocked = false;
    setPipelineButtonsDisabled(false);
    refreshWizardState();
  }

  function attachWizardObservers() {
    const targets = [
      window.clientMeta,
      window.selectedSourceLabel,
      window.selectedDestLabel,
      window.resultCard,
      window.statusBadge,
      window.progressLabel,
    ].filter(Boolean);

    if (!targets.length) return;

    const observer = new MutationObserver(() => {
      refreshWizardState();
    });

    targets.forEach((target) => {
      observer.observe(target, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ["class"],
      });
    });
  }

  let staticEventsBound = false;
  let sharepointPickerBound = false;
  let wizardObserversBound = false;

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

    window.continueStep1Btn?.addEventListener("click", () => {
      if (!canConfirmStep1()) {
        alert("Seleccioná un cliente antes de continuar.");
        return;
      }

      window.step1Confirmed = true;
      refreshWizardState();
    });

    window.continueStep2Btn?.addEventListener("click", () => {
      if (!canConfirmStep2()) {
        alert("Completá el origen del archivo antes de continuar.");
        return;
      }

      window.step2Confirmed = true;
      refreshWizardState();
    });

    window.backStep2Btn?.addEventListener("click", () => {
    window.step1Confirmed = false;
    window.step2Confirmed = false;
    refreshWizardState();
  });

  window.backStep3Btn?.addEventListener("click", () => {
    window.step2Confirmed = false;
    refreshWizardState();
  });

    window.runLocalBtn?.addEventListener("click", window.runLocalPipeline);

    window.runSPBtn?.addEventListener("click", async (...args) => {
      if (!window.authState?.authenticated) {
        window.handleExpiredSessionUI?.();
        return;
      }
      return window.runSharePointPipeline?.(...args);
    });
    
    window.bindVoucherPreviewModalEvents?.();
    window.loadVoucherPreviewBtn?.addEventListener(
      "click",
      window.loadVoucherPreview
    );

    window.cancelJobBtn?.addEventListener("click", async () => {
      if (!window.currentRunningJobId) return;

      try {
        await fetch(window.API.jobCancel(window.currentRunningJobId), {
          method: "POST",
        });

        if (window.progressLabel) {
          window.progressLabel.textContent = "Cancelando ejecución...";
        }

        refreshWizardState();
      } catch (err) {
        console.error("Error cancelando job", err);
      }
    });

    window.refreshHistoryBtn?.addEventListener("click", window.loadJobHistory);

    window.toggleHistoryBtn?.addEventListener("click", () => {
      const collapsed = window.jobHistoryBody?.classList.contains("hidden");
      window.setJobHistoryCollapsed?.(!collapsed);
    });

    window.clientSelect?.addEventListener("change", () => {
      window.step1Confirmed = false;
      window.step2Confirmed = false;
      refreshWizardState();
    });

    window.languageSelect?.addEventListener("change", () => {
      const prefs = window.loadPrefs();
      prefs.language = window.languageSelect.value;
      window.savePrefs(prefs);

      window.step1Confirmed = false;
      refreshWizardState();
    });

    window.fileInput?.addEventListener("change", () => {
      window.step2Confirmed = false;
      refreshWizardState();
    });

    window.localProfileSelect?.addEventListener("change", () => {
      window.step2Confirmed = false;
      refreshWizardState();
    });

    window.sharepointProfileSelect?.addEventListener("change", () => {
      window.step2Confirmed = false;
      refreshWizardState();
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

      window.step2Confirmed = false;
      refreshWizardState();
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

      window.step2Confirmed = false;
      refreshWizardState();
    });
  }

  function bindSharePointPickerEarly() {
    if (sharepointPickerBound) return;
    if (typeof window.bindSharePointPickerEvents !== "function") return;

    window.bindSharePointPickerEvents();
    sharepointPickerBound = true;
  }

  function bindWizardStateObservers() {
    if (wizardObserversBound) return;
    wizardObserversBound = true;
    attachWizardObservers();
  }

  
  async function bootstrapApp() {
    bindStaticEvents();
    bindSharePointPickerEarly();
    bindWizardStateObservers();

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

      window.step1Confirmed = false;
      window.step2Confirmed = false;

      window.syncPickedLabels?.();
      window.restoreJobHistoryCollapsedState?.();
      setTimeout(() => window.loadJobHistory?.(), 300);

      refreshWizardState();
    } catch (error) {
      console.error("Init error:", error);

      try {
        window.syncPickedLabels?.();
        refreshWizardState();
      } catch (e) {
        console.error("Post-init recovery error:", e);
      }
    }
  }

  window.switchMode = switchMode;
  window.setPipelineButtonsDisabled = setPipelineButtonsDisabled;
  window.lockPipelineExecution = lockPipelineExecution;
  window.unlockPipelineExecution = unlockPipelineExecution;
  window.refreshWizardState = refreshWizardState;
  window.bootstrapApp = bootstrapApp;
})();