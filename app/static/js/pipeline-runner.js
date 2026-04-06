// ==========================
// PIPELINE RUNNER MODULE
// ==========================

async function runLocalPipeline() {
  if (!requireSelectedClient()) return;

  const file = fileInput?.files?.[0];
  const selectedProfile = localProfileSelect?.value || "default";
  const language = getSelectedLanguage(languageSelect);

  if (!file) {
    alert("Seleccioná un archivo Excel.");
    return;
  }

  if (!isValidExcelFilename(file.name || "")) {
    alert("El archivo seleccionado no es un Excel válido (.xlsx, .xlsm o .xls).");
    return;
  }

  resetUI("Ejecutando pipeline local...");
  setRunningState("local");

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("profile", selectedProfile);
    formData.append("client_key", selectedClient?.key || "");
    formData.append("language", language);

    const response = await fetch(API.localRun, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok || !data?.ok || !data?.job_id) {
      throw new Error(data?.detail || "Error iniciando pipeline local.");
    }

    await pollJob(data.job_id);
  } catch (error) {
    renderFatalError(error);
  }
}

async function runSharePointPipeline() {
  if (!requireSelectedClient()) return;

  const selectedProfile = sharepointProfileSelect?.value || "default";
  const language = getSelectedLanguage(languageSelect);

  if (!selectedSourceFileId) {
    alert("Seleccioná un Excel de origen en SharePoint.");
    return;
  }

  if (!selectedDestinationFolderId) {
    alert("Seleccioná una carpeta destino en SharePoint.");
    return;
  }

  if (!isValidExcelFilename(selectedSourceFileName || "")) {
    alert("El archivo seleccionado no es un Excel válido.");
    return;
  }

  resetUI("Ejecutando pipeline SharePoint...");
  setRunningState("sharepoint");

  try {
    const payload = {
      source_file_id: selectedSourceFileId,
      destination_folder_id: selectedDestinationFolderId,
      source_site_key: sourceSiteSelect?.value || selectedSourceSiteKey || null,
      destination_site_key: destinationSiteSelect?.value || selectedDestinationSiteKey || null,
      profile: selectedProfile,
      client_key: selectedClient?.key || null,
      language,
    };

    const response = await fetch(API.sharepointRun, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok || !data?.ok || !data?.job_id) {
      throw new Error(data?.detail || "Error iniciando pipeline SharePoint.");
    }

    await pollJob(data.job_id);
  } catch (error) {
    renderFatalError(error);
  }
}