(function () {
  function spEscapeHtml(value) {
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

  function spLoadPrefsSafe() {
    if (typeof window.loadPrefs === "function") {
      return window.loadPrefs();
    }

    try {
      return JSON.parse(localStorage.getItem("voucher_prefs")) || {};
    } catch {
      return {};
    }
  }

  function spSavePrefsSafe(prefs) {
    if (typeof window.savePrefs === "function") {
      window.savePrefs(prefs);
      return;
    }

    localStorage.setItem("voucher_prefs", JSON.stringify(prefs || {}));
  }

  function openSPModal() {
    window.spModal?.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    updateModalContext();
    syncPickedLabels();
  }

  function closeSPModal() {
    window.spModal?.classList.add("hidden");
    document.body.style.overflow = "";
  }

  function updateModalContext() {
    if (window.spModalTitle) {
      window.spModalTitle.textContent =
        window.spBrowseMode === "source"
          ? "Seleccionar Excel de origen"
          : "Seleccionar carpeta destino";
    }

    window.selectCurrentFolderBtn?.classList.toggle(
      "hidden",
      window.spBrowseMode !== "dest"
    );
  }

  function syncPickedLabels() {
    const sourceText = window.selectedSourceFileName
      ? `${window.selectedSourceFileName}${window.selectedSourceSiteKey ? ` · ${window.selectedSourceSiteKey}` : ""}`
      : "Sin seleccionar";

    const destText = window.selectedDestinationFolderName
      ? `${window.selectedDestinationFolderName}${window.selectedDestinationSiteKey ? ` · ${window.selectedDestinationSiteKey}` : ""}`
      : "Sin seleccionar";

    if (window.selectedSourceLabel) window.selectedSourceLabel.textContent = sourceText;
    if (window.selectedDestLabel) window.selectedDestLabel.textContent = destText;
    if (window.spPickedSourceInline) window.spPickedSourceInline.textContent = sourceText;
    if (window.spPickedDestInline) window.spPickedDestInline.textContent = destText;
  }

  async function loadSharePointFolder(folderId = null, resetStack = false, preserveStack = false) {
    if (!window.authState?.authenticated) {
      window.handleExpiredSessionUI?.();
      return null;
    }

    const siteKey =
      window.currentModalSiteKey ||
      window.modalSiteSelect?.value ||
      window.getDefaultSiteKey?.();

    const params = new URLSearchParams();

    if (siteKey) {
      params.set("site_key", siteKey);
    }

    if (folderId) {
      params.set("folder_id", folderId);
    }

    const response = await fetch(`${window.API.sharepointExplore}?${params.toString()}`);
    const data = await response.json();

    if (!response.ok || !data?.ok) {
      throw new Error(data?.detail || "No se pudo explorar SharePoint");
    }

    const currentFolder = data.current_folder || null;
    const items = Array.isArray(data.items) ? data.items : [];

    window.currentSharePointFolderId = currentFolder?.id || null;
    window.currentSharePointFolderName =
      currentFolder?.name ||
      currentFolder?.path ||
      data.site_label ||
      "Raíz";

    window.currentModalSiteKey = data.site_key || siteKey;

    if (window.modalSiteSelect && window.currentModalSiteKey) {
      window.modalSiteSelect.value = window.currentModalSiteKey;
    }

    if (window.spCurrentPathLabel) {
      window.spCurrentPathLabel.textContent =
        currentFolder?.path ||
        currentFolder?.name ||
        "Raíz";
    }

    updateModalContext();

    if (resetStack) {
      window.spFolderStack = [];
    }

    if (!preserveStack && currentFolder?.id) {
      const alreadyInStack = (window.spFolderStack || []).some(
        (x) => x.id === currentFolder.id
      );

      if (!alreadyInStack) {
        window.spFolderStack = [
          ...(window.spFolderStack || []),
          {
            id: currentFolder.id,
            name: window.currentSharePointFolderName,
          },
        ];
      }
    }

    if (
      window.spBrowseMode === "source" &&
      window.currentSharePointFolderId &&
      window.currentModalSiteKey &&
      typeof window.persistSourceFolderPreference === "function"
    ) {
      window.persistSourceFolderPreference(
        window.currentSharePointFolderId,
        window.currentSharePointFolderName,
        window.currentModalSiteKey
      );
    }

    renderSharePointBrowser(items);
    return data;
  }

  function renderSharePointBrowser(items) {
    if (!window.spModalBody) return;

    if (!items.length) {
      window.spModalBody.innerHTML = `
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
        const itemName = spEscapeHtml(item.name || "Sin nombre");
        const itemId = String(item.id || "");
        const itemPath = spEscapeHtml(item.path || "");
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
                  window.spBrowseMode === "dest"
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
          const isExcel =
            typeof window.isValidExcelFilename === "function"
              ? window.isValidExcelFilename(item.name || "")
              : /\.(xlsx|xlsm|xls)$/i.test(item.name || "");

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
                  isExcel && window.spBrowseMode === "source"
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

    window.spModalBody.innerHTML = `<div class="browser-list">${rows}</div>`;
    bindBrowserListEvents();
  }

  function bindBrowserListEvents() {
    window.spModalBody?.querySelectorAll("[data-folder-id]").forEach((el) => {
      el.addEventListener("click", async (event) => {
        const nextFolderId = event.currentTarget.getAttribute("data-folder-id");
        if (!nextFolderId) return;
        await loadSharePointFolder(nextFolderId, false, false);
      });
    });

    window.spModalBody?.querySelectorAll("[data-use-folder-id]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.stopPropagation();

        const folderIdToUse = btn.getAttribute("data-use-folder-id");
        const folderNameToUse = btn.getAttribute("data-use-folder-name");

        window.selectedDestinationFolderId = folderIdToUse;
        window.selectedDestinationFolderName = folderNameToUse;
        window.selectedDestinationSiteKey = window.currentModalSiteKey;

        const prefs = spLoadPrefsSafe();
        prefs.destFolderId = window.selectedDestinationFolderId;
        prefs.destFolderName = window.selectedDestinationFolderName;
        prefs.destFolderSite = window.selectedDestinationSiteKey;
        spSavePrefsSafe(prefs);

        if (window.destinationSiteSelect) {
          window.destinationSiteSelect.value = window.currentModalSiteKey;
        }

        syncPickedLabels();
        closeSPModal();
      });
    });

    window.spModalBody?.querySelectorAll("[data-pick-file-id]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.stopPropagation();

        window.selectedSourceFileId = btn.getAttribute("data-pick-file-id");
        window.selectedSourceFileName = btn.getAttribute("data-pick-file-name");
        window.selectedSourceSiteKey = window.currentModalSiteKey;

        const prefs = spLoadPrefsSafe();
        prefs.sourceFileId = window.selectedSourceFileId;
        prefs.sourceFileName = window.selectedSourceFileName;
        prefs.sourceFileSite = window.selectedSourceSiteKey;
        spSavePrefsSafe(prefs);

        if (window.sourceSiteSelect) {
          window.sourceSiteSelect.value = window.currentModalSiteKey;
        }

        if (typeof window.applyDefaultProfileForSite === "function") {
          window.applyDefaultProfileForSite(window.currentModalSiteKey, "sharepoint");
        }

        syncPickedLabels();
        closeSPModal();
      });
    });
  }

  function bindSharePointPickerEvents() {
    if (window.__sharePointPickerEventsBound) return;
    window.__sharePointPickerEventsBound = true;

    const pickFileBtn = document.getElementById("pickSPFileBtn");
    const pickFolderBtn = document.getElementById("pickSPFolderBtn");
    const closeBtn = document.getElementById("closeSPModalBtn");
    const backdrop = document.getElementById("spModalBackdrop");
    const confirmBtn = document.getElementById("confirmSPSelectionBtn");
    const backBtn = document.getElementById("spBackBtn");
    const selectCurrentFolderBtn = document.getElementById("selectCurrentFolderBtn");
    const modalSiteSelect = document.getElementById("modalSiteSelect");

    pickFileBtn?.addEventListener("click", async () => {

      try {
        if (!window.authState?.authenticated) {
          console.warn("[SP PICKER] sesión no autenticada");
          window.handleExpiredSessionUI?.();
          return;
        }

        const prefs = spLoadPrefsSafe();
        window.spBrowseMode = "source";
        window.currentModalSiteKey =
          window.sourceSiteSelect?.value || window.getDefaultSiteKey?.();

        if (modalSiteSelect) {
          modalSiteSelect.value = window.currentModalSiteKey;
        }

        window.applyDefaultProfileForSite?.(window.currentModalSiteKey, "sharepoint");

        openSPModal();

        const data =
          prefs.sourceFolderId &&
          prefs.sourceFolderSite &&
          prefs.sourceFolderSite === window.currentModalSiteKey
            ? await loadSharePointFolder(prefs.sourceFolderId, true, false)
            : await loadSharePointFolder(null, true, false);

        
      } catch (error) {
        console.error("[SP PICKER] error archivo:", error);
        alert(error?.message || "Error abriendo explorador de SharePoint");
      }
    });

    pickFolderBtn?.addEventListener("click", async () => {

      try {
        if (!window.authState?.authenticated) {
          console.warn("[SP PICKER] sesión no autenticada");
          window.handleExpiredSessionUI?.();
          return;
        }

        const prefs = spLoadPrefsSafe();
        window.spBrowseMode = "dest";
        window.currentModalSiteKey =
          window.destinationSiteSelect?.value || window.getDefaultSiteKey?.();

        if (modalSiteSelect) {
          modalSiteSelect.value = window.currentModalSiteKey;
        }

        openSPModal();

        const data =
          prefs.destFolderId &&
          prefs.destFolderSite &&
          prefs.destFolderSite === window.currentModalSiteKey
            ? await loadSharePointFolder(prefs.destFolderId, true, false)
            : await loadSharePointFolder(null, true, false);

      } catch (error) {
        console.error("[SP PICKER] error carpeta:", error);
        alert(error?.message || "Error abriendo explorador de SharePoint");
      }
    });

    closeBtn?.addEventListener("click", closeSPModal);
    backdrop?.addEventListener("click", closeSPModal);

    confirmBtn?.addEventListener("click", () => {
      syncPickedLabels();
      closeSPModal();
    });

    backBtn?.addEventListener("click", async () => {
      try {
        if (!window.authState?.authenticated) {
          window.handleExpiredSessionUI?.();
          return;
        }

        if ((window.spFolderStack || []).length <= 1) {
          await loadSharePointFolder(null, true, false);
          return;
        }

        window.spFolderStack.pop();
        const previous = window.spFolderStack[window.spFolderStack.length - 1] || null;
        await loadSharePointFolder(previous?.id || null, false, true);
      } catch (error) {
        console.error("[SP PICKER] error volver:", error);
      }
    });

    selectCurrentFolderBtn?.addEventListener("click", () => {
      try {
        if (!window.authState?.authenticated) {
          window.handleExpiredSessionUI?.();
          return;
        }

        if (!window.currentSharePointFolderId) return;

        window.selectedDestinationFolderId = window.currentSharePointFolderId;
        window.selectedDestinationFolderName = window.currentSharePointFolderName;
        window.selectedDestinationSiteKey = window.currentModalSiteKey;

        const prefs = spLoadPrefsSafe();
        prefs.destFolderId = window.selectedDestinationFolderId;
        prefs.destFolderName = window.selectedDestinationFolderName;
        prefs.destFolderSite = window.selectedDestinationSiteKey;
        spSavePrefsSafe(prefs);

        if (window.destinationSiteSelect) {
          window.destinationSiteSelect.value = window.currentModalSiteKey;
        }

        syncPickedLabels();
        closeSPModal();
      } catch (error) {
        console.error("[SP PICKER] error seleccionar carpeta actual:", error);
      }
    });

    modalSiteSelect?.addEventListener("change", async () => {
      try {
        if (!window.authState?.authenticated) {
          window.handleExpiredSessionUI?.();
          return;
        }

        window.currentModalSiteKey = modalSiteSelect.value;

        if (window.spBrowseMode === "source") {
          window.applyDefaultProfileForSite?.(window.currentModalSiteKey, "sharepoint");
        }

        await loadSharePointFolder(null, true, false);
      } catch (error) {
        console.error("[SP PICKER] error cambio site:", error);
      }
    });
  }

  window.openSPModal = openSPModal;
  window.closeSPModal = closeSPModal;
  window.updateModalContext = updateModalContext;
  window.syncPickedLabels = syncPickedLabels;
  window.loadSharePointFolder = loadSharePointFolder;
  window.renderSharePointBrowser = renderSharePointBrowser;
  window.bindSharePointPickerEvents = bindSharePointPickerEvents;
})();