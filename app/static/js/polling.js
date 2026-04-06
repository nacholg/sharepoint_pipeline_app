// ==========================
// POLLING MODULE
// ==========================

function stopActivePolling() {
  if (activeJobPollTimer) {
    clearTimeout(activeJobPollTimer);
    activeJobPollTimer = null;
  }
  activeJobId = null;
}

async function fetchJobStatus(jobId) {
  const response = await fetch(API.jobStatus(jobId));
  const data = await response.json();

  if (!response.ok || !data?.ok) {
    throw new Error(data?.detail || "No se pudo obtener el estado del job");
  }

  return data;
}

function applyJobState(job) {
  const status = job.status || "pending";
  const progress = Number(job.progress) || 0;
  const progressText = job.progress_label || getStepLabel(job.current_step);

  if (status === "pending") {
    statusBadge.textContent = "Pending";
    statusBadge.className = "status-badge neutral";
  } else if (status === "running") {
    statusBadge.textContent = "Running";
    statusBadge.className = "status-badge running";
  } else if (status === "success") {
    statusBadge.textContent = "Success";
    statusBadge.className = "status-badge success";
  } else if (status === "error") {
    statusBadge.textContent = "Error";
    statusBadge.className = "status-badge error";
  }
    else if (status === "cancelling") {
  statusBadge.textContent = "Cancelling";
  statusBadge.className = "status-badge neutral";

  } else if (status === "cancelled") {
  statusBadge.textContent = "Cancelled";
  statusBadge.className = "status-badge neutral";
  }

  setProgress(progress, progressText || "Procesando");

  const steps = Array.isArray(job.steps) ? job.steps : [];
  renderSteps(steps);
}

async function pollJob(jobId) {
  activeJobId = jobId;

  let pollingDelay = 800;
  let hasRenderedResult = false;

  const finishAndUnlock = () => {
    unlockPipelineExecution();
    window.currentRunningJobId = null;
  };

  const tick = async () => {
    try {
      const job = await fetchJobStatus(jobId);

      if (activeJobId !== jobId) return;

      applyJobState(job);

      if (job.status === "cancelled") {
        stopActivePolling();

        statusBadge.textContent = "Cancelled";
        statusBadge.className = "status-badge neutral";

        progressLabel.textContent = "Ejecución cancelada";
        progressPercent.textContent = "0%";
        progressFill.style.width = "0%";

        resultCard.classList.remove("hidden");
        resultContent.innerHTML = `
          <div class="error-banner">El job fue cancelado por el usuario</div>
        `;

        finishAndUnlock();
        window.currentRunningJobId = null;
        return;
      }
      
      if (job.status === "success" && !hasRenderedResult) {
        hasRenderedResult = true;
        stopActivePolling();
        setFinishedState(true);
        renderSteps(Array.isArray(job.steps) ? job.steps : []);
        resultCard.classList.remove("hidden");

        if (job.result && typeof window.renderResult === "function") {
          window.renderResult(job.result);
        } else {
          resultContent.innerHTML = `
            <div class="error-banner">El job finalizó correctamente pero no devolvió resultado renderizable.</div>
          `;
        }

        finishAndUnlock();
        return;
      }

      if (job.status === "error") {
        stopActivePolling();
        statusBadge.textContent = "Error";
        statusBadge.className = "status-badge error";
        progressLabel.textContent = "Pipeline con error";
        progressPercent.textContent = "100%";
        progressFill.style.width = "100%";
        renderSteps(Array.isArray(job.steps) ? job.steps : []);
        resultCard.classList.remove("hidden");

        if (job.result && typeof window.renderResult === "function") {
          window.renderResult(job.result);
        } else {
          resultContent.innerHTML = `
            <div class="error-banner">${escapeHtml(job.error || "Error ejecutando pipeline")}</div>
          `;
        }

        finishAndUnlock();
        return;
      }

      if (pollingDelay < 1500) {
        pollingDelay += 100;
      }

      activeJobPollTimer = setTimeout(tick, pollingDelay);
    } catch (error) {
      stopActivePolling();
      finishAndUnlock();
      renderFatalError(error);
    }
      
    };

  await tick();
}