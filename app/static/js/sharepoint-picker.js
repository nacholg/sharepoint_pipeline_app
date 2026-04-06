// ==========================
// SHAREPOINT PICKER MODULE
// ==========================

// Estado compartido (usa variables globales existentes del app.js)

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
    const isExcel = isValidExcelFilename(item.name || "");

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

    const main = row.querySelector(".browser-main");
    const actions = row.querySelector(".browser-actions");

    if (isFolder) {
      row.classList.add("browser-row-clickable");
      main.style.cursor = "pointer";

      main.addEventListener("click", async () => {
        await loadSharePointFolder(item.id);
      });

      const openBtn = document.createElement("button");
      openBtn.className = "btn secondary small";
      openBtn.textContent = "Abrir";
      openBtn.onclick = async (e) => {
        e.stopPropagation();
        await loadSharePointFolder(item.id);
      };
      actions.appendChild(openBtn);

      if (spBrowseMode === "dest") {
        const useBtn = document.createElement("button");
        useBtn.className = "btn primary small";
        useBtn.textContent = "Usar carpeta";
        useBtn.onclick = (e) => {
          e.stopPropagation();
          selectedDestinationFolderId = item.id;
          selectedDestinationFolderName = item.name;
          selectedDestinationSiteKey = currentModalSiteKey;

          if (destinationSiteSelect) {
            destinationSiteSelect.value = currentModalSiteKey;
          }

          syncPickedLabels();
        };
        actions.appendChild(useBtn);
      }
    }

    if (isFile && spBrowseMode === "source") {
      if (!isExcel) {
        const badge = document.createElement("span");
        badge.className = "file-badge invalid";
        badge.textContent = "No válido";
        actions.appendChild(badge);
      } else {
        row.classList.add("browser-row-clickable");
        main.style.cursor = "pointer";

        main.onclick = () => {
          selectedSourceFileId = item.id;
          selectedSourceFileName = item.name;
          selectedSourceSiteKey = currentModalSiteKey;

          if (sourceSiteSelect) {
            sourceSiteSelect.value = currentModalSiteKey;
          }

          applyDefaultProfileForSite(currentModalSiteKey, "sharepoint");
          syncPickedLabels();
        };

        const pickBtn = document.createElement("button");
        pickBtn.className = "btn primary small";
        pickBtn.textContent = "Elegir archivo";
        pickBtn.onclick = (e) => {
          e.stopPropagation();
          main.onclick();
        };

        actions.appendChild(pickBtn);
      }
    }

    list.appendChild(row);
  }

  spModalBody.appendChild(list);
}