document.addEventListener("DOMContentLoaded", () => {
  const btnLoadSpFiles = document.getElementById("pickSourceBtn");
  const btnLoadSpFolders = document.getElementById("pickDestBtn");
  const btnRunSpPipeline = document.getElementById("runSharepointBtn");

  const sourceInput = document.getElementById("sourceFileName");
  const destInput = document.getElementById("destFolderName");

  const statusCard = document.getElementById("statusCard");
  const statusMessage = document.getElementById("statusMessage");
  const resultBox = document.getElementById("resultBox");
  const rawCard = document.getElementById("rawCard");

  const modal = document.getElementById("spExplorerModal");
  const modalBackdrop = document.getElementById("spExplorerBackdrop");
  const modalCloseBtn = document.getElementById("spExplorerCloseBtn");
  const modalBackBtn = document.getElementById("spExplorerBackBtn");
  const modalTitle = document.getElementById("spExplorerTitle");
  const modalSubtitle = document.getElementById("spExplorerSubtitle");
  const modalPath = document.getElementById("spExplorerPath");
  const modalStatus = document.getElementById("spExplorerStatus");
  const modalList = document.getElementById("spExplorerList");

  let selectedFileId = null;
  let selectedFolderId = null;

  let explorerMode = null;
  let explorerHistory = [];
  let currentFolderId = null;

  function setStatus(msg) {
    if (statusCard) statusCard.classList.remove("hidden");
    if (statusMessage) statusMessage.textContent = msg;
  }

  function showTechnicalResult(data) {
    if (rawCard) rawCard.classList.remove("hidden");
    if (resultBox) resultBox.textContent = JSON.stringify(data, null, 2);
  }

  function openExplorer(mode) {
    explorerMode = mode;
    explorerHistory = [];
    currentFolderId = null;

    if (modalTitle) {
      modalTitle.textContent =
        mode === "file"
          ? "Explorar SharePoint - Excel origen"
          : "Explorar SharePoint - Carpeta destino";
    }

    if (modalSubtitle) {
      modalSubtitle.textContent =
        mode === "file"
          ? "Navegá carpetas y seleccioná un archivo Excel"
          : "Navegá carpetas y seleccioná la carpeta destino";
    }

    modal?.classList.remove("hidden");
    loadExplorerFolder(null, true);
  }

  function closeExplorer() {
    modal?.classList.add("hidden");
    explorerMode = null;
    explorerHistory = [];
    currentFolderId = null;
    if (modalList) modalList.innerHTML = "";
  }

  async function loadExplorerFolder(folderId = null, resetHistory = false) {
    if (modalStatus) modalStatus.textContent = "Cargando contenido de SharePoint...";
    if (modalList) modalList.innerHTML = "";

    try {
      const url = folderId
        ? `/api/sharepoint/explore?folder_id=${encodeURIComponent(folderId)}`
        : `/api/sharepoint/explore`;

      const res = await fetch(url);
      const data = await res.json();

      console.log("EXPLORE RESULT:", data);
      showTechnicalResult(data);

      if (!res.ok) {
        throw new Error(data.detail || "Error explorando SharePoint.");
      }

      const currentFolder = data.current_folder || null;
      const items = data.items || [];

      if (!resetHistory && currentFolderId && folderId && currentFolderId !== folderId) {
        explorerHistory.push(currentFolderId);
      }

      currentFolderId = currentFolder?.id || null;

      if (modalPath) {
        modalPath.textContent = currentFolder?.parent_path
          ? `${currentFolder.parent_path}/${currentFolder.name || ""}`
          : currentFolder?.name || "/";
      }

      if (modalStatus) {
        modalStatus.textContent =
          explorerMode === "file"
            ? "Seleccioná una carpeta para entrar o un Excel para elegir."
            : "Seleccioná una carpeta para entrar o elegir como destino.";
      }

      renderExplorerItems(items);
    } catch (err) {
      console.error(err);
      if (modalStatus) modalStatus.textContent = `Error: ${err.message}`;
    }
  }

  function renderExplorerItems(items) {
    if (!modalList) return;

    modalList.innerHTML = "";

    const folders = items.filter((x) => x.is_folder);
    const files = items.filter((x) => x.is_file);

    const visibleFiles =
      explorerMode === "file"
        ? files.filter((x) => {
            const name = String(x.name || "").toLowerCase();
            return name.endsWith(".xlsx") || name.endsWith(".xlsm");
          })
        : [];

    const finalItems = [...folders, ...visibleFiles];

    if (finalItems.length === 0) {
      modalList.innerHTML = `<div class="status-box">No hay elementos disponibles en esta carpeta.</div>`;
      return;
    }

    finalItems.forEach((item) => {
      const isFolder = item.is_folder;
      const wrapper = document.createElement("div");
      wrapper.className = "explorer-item";

      const left = document.createElement("div");
      left.className = "explorer-item-left";

      const name = document.createElement("div");
      name.className = "explorer-item-name";
      name.textContent = isFolder ? `📁 ${item.name}` : `📄 ${item.name}`;

      const meta = document.createElement("div");
      meta.className = "explorer-item-meta";
      meta.textContent = isFolder
        ? "Carpeta"
        : `${item.mime_type || "Archivo"} · ${item.size || 0} bytes`;

      left.appendChild(name);
      left.appendChild(meta);

      const actions = document.createElement("div");
      actions.className = "explorer-actions";

      if (isFolder) {
        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "secondary-btn";
        openBtn.textContent = "Abrir";
        openBtn.addEventListener("click", () => loadExplorerFolder(item.id));

        actions.appendChild(openBtn);

        if (explorerMode === "folder") {
          const selectBtn = document.createElement("button");
          selectBtn.type = "button";
          selectBtn.className = "primary-btn";
          selectBtn.textContent = "Seleccionar";
          selectBtn.addEventListener("click", () => selectFolder(item));
          actions.appendChild(selectBtn);
        }
      } else if (explorerMode === "file") {
        const selectBtn = document.createElement("button");
        selectBtn.type = "button";
        selectBtn.className = "primary-btn";
        selectBtn.textContent = "Seleccionar";
        selectBtn.addEventListener("click", () => selectFile(item));
        actions.appendChild(selectBtn);
      }

      wrapper.appendChild(left);
      wrapper.appendChild(actions);
      modalList.appendChild(wrapper);
    });
  }

  function selectFile(item) {
    selectedFileId = item.id;
    if (sourceInput) sourceInput.value = item.name || "";
    setStatus(`Archivo seleccionado: ${item.name}`);
    closeExplorer();
  }

  function selectFolder(item) {
    selectedFolderId = item.id;
    if (destInput) destInput.value = item.name || "";
    setStatus(`Carpeta seleccionada: ${item.name}`);
    closeExplorer();
  }

  function goBackExplorer() {
    if (explorerHistory.length === 0) {
      loadExplorerFolder(null, true);
      return;
    }

    const previousId = explorerHistory.pop();
    loadExplorerFolder(previousId, true);
  }

  async function runSharePointPipeline() {
    if (!selectedFileId) return setStatus("Primero seleccioná un archivo.");
    if (!selectedFolderId) return setStatus("Primero seleccioná una carpeta.");

    setStatus("Descargando Excel desde SharePoint y ejecutando pipeline...");

    try {
      const res = await fetch("/api/sharepoint/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          source_file_id: selectedFileId,
          destination_folder_id: selectedFolderId
        })
      });

      const data = await res.json();

      console.log("RUN RESULT:", data);
      showTechnicalResult(data);

      if (!res.ok) {
        throw new Error(data.detail || "Error HTTP desconocido");
      }

      if (data.ok === false) {
        throw new Error(data.error || "El pipeline devolvió ok=false");
      }

      setStatus("Pipeline ejecutado correctamente ✅");
    } catch (err) {
      console.error(err);
      setStatus(`Error ejecutando pipeline: ${err.message}`);
    }
  }

  btnLoadSpFiles?.addEventListener("click", () => openExplorer("file"));
  btnLoadSpFolders?.addEventListener("click", () => openExplorer("folder"));
  btnRunSpPipeline?.addEventListener("click", runSharePointPipeline);

  modalCloseBtn?.addEventListener("click", closeExplorer);
  modalBackdrop?.addEventListener("click", closeExplorer);
  modalBackBtn?.addEventListener("click", goBackExplorer);

  console.log("Explorador modal SharePoint listo");
});