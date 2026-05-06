// ==========================
// PIPELINE RUNNER MODULE
// ==========================

async function runLocalPipeline(event) {
  event?.preventDefault?.();
  event?.stopPropagation?.();

  if (!requireSelectedClient()) return;
  if (!lockPipelineExecution()) return;

  const file = fileInput?.files?.[0];
  const selectedProfile = localProfileSelect?.value || "default";
  const language = getSelectedLanguage(languageSelect);

  if (!file) {
    unlockPipelineExecution();
    alert("Seleccioná un archivo Excel.");
    return;
  }

  if (!isValidExcelFilename(file.name || "")) {
    unlockPipelineExecution();
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

    const selectedVoucherIds =
      window.APP_STATE?.data?.selectedVoucherIds || [];

    if (window.APP_STATE?.data?.voucherPreview) {
      formData.append(
        "selected_voucher_ids",
        JSON.stringify(selectedVoucherIds)
      );
    }

    const response = await fetch(API.localRun, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok || !data?.ok || !data?.job_id) {
      throw new Error(data?.detail || "Error iniciando pipeline local.");
    }
    window.fileInput?.addEventListener("change", () => {
    window.setActiveStep?.(2);
  });

    window.currentRunningJobId = data.job_id;
    await pollJob(data.job_id);
  } catch (error) {
    unlockPipelineExecution();
    renderFatalError(error);
  }
}

async function runSharePointPipeline(event) {
  event?.preventDefault?.();
  event?.stopPropagation?.();

  if (!requireSelectedClient()) return;
  if (!lockPipelineExecution()) return;

  const selectedProfile = sharepointProfileSelect?.value || "default";
  const language = getSelectedLanguage(languageSelect);

  if (!selectedSourceFileId) {
    unlockPipelineExecution();
    alert("Seleccioná un Excel de origen en SharePoint.");
    return;
  }

  if (!selectedDestinationFolderId) {
    unlockPipelineExecution();
    alert("Seleccioná una carpeta destino en SharePoint.");
    return;
  }

  if (!isValidExcelFilename(selectedSourceFileName || "")) {
    unlockPipelineExecution();
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



    window.currentRunningJobId = data.job_id;
    await pollJob(data.job_id);
  } catch (error) {
    unlockPipelineExecution();
    renderFatalError(error);
  }
}