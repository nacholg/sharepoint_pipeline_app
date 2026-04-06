// ==========================
// UI STATE MODULE
// ==========================

function setProgress(percent, label) {
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
  progressPercent.textContent = `${safePercent}%`;
  progressFill.style.width = `${safePercent}%`;

  if (label) {
    progressLabel.textContent = label;
  }
}

function resetUI(label = "Esperando ejecución") {
  stopActivePolling();
  statusBadge.textContent = "Idle";
  statusBadge.className = "status-badge neutral";
  progressLabel.textContent = label;
  progressPercent.textContent = "0%";
  progressFill.style.width = "0%";
  stepsEl.innerHTML = "";
  resultCard.classList.add("hidden");
  resultContent.innerHTML = "";
}

function setRunningState(mode = "local") {
  statusBadge.textContent = "Running";
  statusBadge.className = "status-badge running";

  setProgress(
    mode === "sharepoint" ? 6 : 8,
    mode === "sharepoint"
      ? "Preparando pipeline SharePoint"
      : "Preparando pipeline local"
  );

  stepsEl.innerHTML = "";
  resultCard.classList.add("hidden");
  resultContent.innerHTML = "";
}

function setFinishedState(ok) {
  stopActivePolling();
  statusBadge.textContent = ok ? "Success" : "Error";
  statusBadge.className = `status-badge ${ok ? "success" : "error"}`;
  progressLabel.textContent = ok ? "Pipeline finalizado" : "Pipeline con error";
  progressPercent.textContent = "100%";
  progressFill.style.width = "100%";
}

function renderFatalError(error) {
  stopActivePolling();

  statusBadge.textContent = "Error";
  statusBadge.className = "status-badge error";
  progressLabel.textContent = "Pipeline con error";
  progressPercent.textContent = "100%";
  progressFill.style.width = "100%";

  stepsEl.innerHTML = `
    <div class="step-item error">
      <div class="step-bullet"></div>
      <div class="step-body">
        <div class="step-head">
          <div class="step-title">Error fatal</div>
        </div>
        <pre class="log-block">${escapeHtml(error?.message || String(error))}</pre>
      </div>
    </div>
  `;

  resultCard.classList.remove("hidden");
  resultContent.innerHTML = `
    <div class="error-banner">${escapeHtml(error?.message || String(error))}</div>
  `;
}