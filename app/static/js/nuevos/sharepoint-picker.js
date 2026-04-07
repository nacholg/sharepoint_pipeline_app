import { API } from "./api.js";
import { dom } from "./dom.js";
import { state } from "./state.js";
import { loadPrefs, savePrefs, persistSourceFolderPreference } from "./prefs.js";
import { escapeHtml } from "./helpers.js";
import { handleExpiredSessionUI } from "./auth.js";
import { getDefaultSiteKey, applyDefaultProfileForSite } from "./clients.js";

export function openSPModal() {
  if (!dom.spModal) return;
  dom.spModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

export function closeSPModal() {
  if (!dom.spModal) return;
  dom.spModal.classList.add("hidden");
  document.body.style.overflow = "";
}

export function syncPickedLabels() {
  const sourceText = state.sharepoint.selectedSourceFileName
    ? `${state.sharepoint.selectedSourceFileName}${state.sharepoint.selectedSourceSiteKey ? ` · ${state.sharepoint.selectedSourceSiteKey}` : ""}`
    : "Sin seleccionar";

  const destText = state.sharepoint.selectedDestinationFolderName
    ? `${state.sharepoint.selectedDestinationFolderName}${state.sharepoint.selectedDestinationSiteKey ? ` · ${state.sharepoint.selectedDestinationSiteKey}` : ""}`
    : "Sin seleccionar";

  if (dom.selectedSourceLabel) dom.selectedSourceLabel.textContent = sourceText;
  if (dom.selectedDestLabel) dom.selectedDestLabel.textContent = destText;
  if (dom.spPickedSourceInline) dom.spPickedSourceInline.textContent = sourceText;
  if (dom.spPickedDestInline) dom.spPickedDestInline.textContent = destText;
}

export async function loadSharePointFolder(folderId = null, resetStack = false) {
  if (!state.auth.authenticated) {
    handleExpiredSessionUI();
    return;
  }

  const siteKey = state.sharepoint.currentModalSiteKey || dom.modalSiteSelect?.value || getDefaultSiteKey();
  const params = new URLSearchParams();

  if (siteKey) params.set("site_key", siteKey);
  if (folderId) params.set("folder_id", folderId);

  const response = await fetch(`${API.sharepointExplore}?${params.toString()}`);
  const data = await response.json();

  if (!response.ok || !data?.ok) {
    throw new Error(data?.detail || "No se pudo explorar SharePoint");
  }

  const currentFolder = data.current_folder || null;
  const items = Array.isArray(data.items) ? data.items : [];

  state.sharepoint.currentFolderId = currentFolder?.id || null;
  state.sharepoint.currentFolderName = currentFolder?.name || currentFolder?.path || data.site_label || "Raíz";
  state.sharepoint.currentModalSiteKey = data.site_key || siteKey;

  if (dom.modalSiteSelect && state.sharepoint.currentModalSiteKey) {
    dom.modalSiteSelect.value = state.sharepoint.currentModalSiteKey;
  }

  if (dom.spCurrentPathLabel) {
    dom.spCurrentPathLabel.textContent = currentFolder?.path || currentFolder?.name || "Raíz";
  }

  if (dom.spModalTitle) {
    dom.spModalTitle.textContent =
      state.sharepoint.browseMode === "source"
        ? "Seleccionar Excel de origen"
        : "Seleccionar carpeta destino";
  }

  if (dom.selectCurrentFolderBtn) {
    dom.selectCurrentFolderBtn.classList.toggle("hidden", state.sharepoint.browseMode !== "dest");
  }

  if (resetStack) {
    state.sharepoint.folderStack = [];
  }

  if (currentFolder?.id) {
    const alreadyInStack = state.sharepoint.folderStack.some((x) => x.id === currentFolder.id);
    if (!alreadyInStack) {
      state.sharepoint.folderStack.push({
        id: currentFolder.id,
        name: state.sharepoint.currentFolderName,
      });
    }
  }

  if (state.sharepoint.browseMode === "source" && state.sharepoint.currentFolderId && state.sharepoint.currentModalSiteKey) {
    persistSourceFolderPreference(
      state.sharepoint.currentFolderId,
      state.sharepoint.currentFolderName,
      state.sharepoint.currentModalSiteKey
    );
  }

  if (!dom.spModalBody) return;

  if (!items.length) {
    dom.spModalBody.innerHTML = `
      <div class="empty-state">
        <div>
          <div class="empty-icon">📂</div>
          <div>No hay elementos en esta carpeta.</div>
        </div>
      </div>
    `;
    return;
  }

  dom.spModalBody.innerHTML = `
    <div class="browser-list">
      ${items.map(renderBrowserItem).join("")}
    </div>
  `;

  bindModalListEvents();
}

function renderBrowserItem(item) {
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
            state.sharepoint.browseMode === "dest"
              ? `<button class="btn secondary small" type="button" data-use-folder-id="${itemId}" data-use-folder-name="${itemName}">Usar carpeta</button>`
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
            isExcel && state.sharepoint.browseMode === "source"
              ? `<button class="btn secondary small" type="button" data-pick-file-id="${itemId}" data-pick-file-name="${itemName}">Elegir</button>`
              : `<span class="muted-pill">Solo lectura</span>`
          }
        </div>
      </div>
    `;
  }

  return "";
}

function bindModalListEvents() {
  dom.spModalBody?.querySelectorAll("[data-folder-id]").forEach((el) => {
    el.addEventListener("click", async (event) => {
      const nextFolderId = event.currentTarget.getAttribute("data-folder-id");
      if (!nextFolderId) return;
      await loadSharePointFolder(nextFolderId, false);
    });
  });

  dom.spModalBody?.querySelectorAll("[data-use-folder-id]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();

      state.sharepoint.selectedDestinationFolderId = btn.getAttribute("data-use-folder-id");
      state.sharepoint.selectedDestinationFolderName = btn.getAttribute("data-use-folder-name");
      state.sharepoint.selectedDestinationSiteKey = state.sharepoint.currentModalSiteKey;

      const prefs = loadPrefs();
      prefs.destFolderId = state.sharepoint.selectedDestinationFolderId;
      prefs.destFolderName = state.sharepoint.selectedDestinationFolderName;
      prefs.destFolderSite = state.sharepoint.selectedDestinationSiteKey;
      savePrefs(prefs);

      if (dom.destinationSiteSelect) {
        dom.destinationSiteSelect.value = state.sharepoint.currentModalSiteKey;
      }

      syncPickedLabels();
      closeSPModal();
    });
  });

  dom.spModalBody?.querySelectorAll("[data-pick-file-id]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();

      state.sharepoint.selectedSourceFileId = btn.getAttribute("data-pick-file-id");
      state.sharepoint.selectedSourceFileName = btn.getAttribute("data-pick-file-name");
      state.sharepoint.selectedSourceSiteKey = state.sharepoint.currentModalSiteKey;

      const prefs = loadPrefs();
      prefs.sourceFileId = state.sharepoint.selectedSourceFileId;
      prefs.sourceFileName = state.sharepoint.selectedSourceFileName;
      prefs.sourceFileSite = state.sharepoint.selectedSourceSiteKey;
      savePrefs(prefs);

      syncPickedLabels();
      closeSPModal();
    });
  });
}

export function bindSharepointPickerEvents() {
  dom.pickSPFileBtn?.addEventListener("click", async () => {
    if (!state.auth.authenticated) {
      handleExpiredSessionUI();
      return;
    }

    const prefs = loadPrefs();
    state.sharepoint.browseMode = "source";
    state.sharepoint.currentModalSiteKey = dom.sourceSiteSelect?.value || getDefaultSiteKey();

    if (dom.modalSiteSelect) {
      dom.modalSiteSelect.value = state.sharepoint.currentModalSiteKey;
    }

    applyDefaultProfileForSite(state.sharepoint.currentModalSiteKey, "sharepoint");
    openSPModal();

    if (
      prefs.sourceFolderId &&
      prefs.sourceFolderSite &&
      prefs.sourceFolderSite === state.sharepoint.currentModalSiteKey
    ) {
      await loadSharePointFolder(prefs.sourceFolderId, true);
      return;
    }

    await loadSharePointFolder(null, true);
  });

  dom.pickSPFolderBtn?.addEventListener("click", async () => {
    if (!state.auth.authenticated) {
      handleExpiredSessionUI();
      return;
    }

    const prefs = loadPrefs();
    state.sharepoint.browseMode = "dest";
    state.sharepoint.currentModalSiteKey = dom.destinationSiteSelect?.value || getDefaultSiteKey();

    if (dom.modalSiteSelect) {
      dom.modalSiteSelect.value = state.sharepoint.currentModalSiteKey;
    }

    openSPModal();

    if (
      prefs.destFolderId &&
      prefs.destFolderSite &&
      prefs.destFolderSite === state.sharepoint.currentModalSiteKey
    ) {
      await loadSharePointFolder(prefs.destFolderId, true);
      return;
    }

    await loadSharePointFolder(null, true);
  });

  dom.closeSPModalBtn?.addEventListener("click", closeSPModal);
  dom.spModalBackdrop?.addEventListener("click", closeSPModal);
  dom.confirmSPSelectionBtn?.addEventListener("click", () => {
    syncPickedLabels();
    closeSPModal();
  });

  dom.spBackBtn?.addEventListener("click", async () => {
    if (!state.auth.authenticated) {
      handleExpiredSessionUI();
      return;
    }

    if (state.sharepoint.folderStack.length <= 1) {
      await loadSharePointFolder(null, true);
      return;
    }

    state.sharepoint.folderStack.pop();
    const previous = state.sharepoint.folderStack[state.sharepoint.folderStack.length - 1] || null;
    await loadSharePointFolder(previous?.id || null, false);
  });

  dom.selectCurrentFolderBtn?.addEventListener("click", () => {
    if (!state.sharepoint.currentFolderId) return;

    state.sharepoint.selectedDestinationFolderId = state.sharepoint.currentFolderId;
    state.sharepoint.selectedDestinationFolderName = state.sharepoint.currentFolderName;
    state.sharepoint.selectedDestinationSiteKey = state.sharepoint.currentModalSiteKey;

    const prefs = loadPrefs();
    prefs.destFolderId = state.sharepoint.selectedDestinationFolderId;
    prefs.destFolderName = state.sharepoint.selectedDestinationFolderName;
    prefs.destFolderSite = state.sharepoint.selectedDestinationSiteKey;
    savePrefs(prefs);

    if (dom.destinationSiteSelect) {
      dom.destinationSiteSelect.value = state.sharepoint.currentModalSiteKey;
    }

    syncPickedLabels();
    closeSPModal();
  });

  dom.modalSiteSelect?.addEventListener("change", async () => {
    if (!state.auth.authenticated) {
      handleExpiredSessionUI();
      return;
    }

    state.sharepoint.currentModalSiteKey = dom.modalSiteSelect.value;

    if (state.sharepoint.browseMode === "source") {
      applyDefaultProfileForSite(state.sharepoint.currentModalSiteKey, "sharepoint");
    }

    await loadSharePointFolder(null, true);
  });
}