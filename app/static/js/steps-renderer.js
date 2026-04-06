// ==========================
// STEPS RENDERER MODULE
// ==========================

function toggleStepLog(logId, btn) {
  const el = document.getElementById(logId);
  if (!el) return;

  const isHidden = el.classList.toggle("hidden");
  if (btn) {
    btn.textContent = isHidden ? "Ver log" : "Ocultar log";
  }
}

function renderStep(step, index = 0) {
  const rawStatus =
    step.status || (step.ok === true ? "done" : step.ok === false ? "error" : "pending");

  const visualStatus =
    rawStatus === "done"
      ? "success"
      : rawStatus === "error"
        ? "error"
        : rawStatus === "running"
          ? "running"
          : "pending";

  const wrap = document.createElement("div");
  wrap.className = `step-item ${visualStatus}`;

  const output = [step.stdout, step.stderr].filter(Boolean).join("\n").trim();
  const hasUsefulLog = Boolean(output);
  const logId = `step-log-${index}-${Math.random().toString(36).slice(2, 8)}`;

  let stateText = "Pendiente";
  if (rawStatus === "running") stateText = "En proceso";
  if (rawStatus === "done") stateText = "Listo";
  if (rawStatus === "error") stateText = "Error";

  const showLogButton = hasUsefulLog;

  wrap.innerHTML = `
    <div class="step-bullet"></div>
    <div class="step-body">
      <div class="step-head">
        <div class="step-head-main">
          <div class="step-title">${escapeHtml(step.label || getStepLabel(step.name))}</div>
        </div>

        <div class="step-head-actions">
          <span class="step-status-pill step-status-pill-${visualStatus}">
            ${stateText}
          </span>

          ${
            showLogButton
              ? `<button type="button" class="btn secondary small step-log-btn" onclick="toggleStepLog('${logId}', this)">Ver log</button>`
              : ""
          }
        </div>
      </div>

      ${
        hasUsefulLog
          ? `<pre id="${logId}" class="log-block hidden">${escapeHtml(output)}</pre>`
          : ""
      }
    </div>
  `;

  return wrap;
}

function renderSteps(steps = []) {
  stepsEl.innerHTML = "";
  steps.forEach((step, index) => {
    stepsEl.appendChild(renderStep(step, index));
  });
}

window.toggleStepLog = toggleStepLog;