function setJobHistoryCollapsed(collapsed) {
  const jobHistoryBody = document.getElementById("jobHistoryBody");
  const toggleHistoryBtn = document.getElementById("toggleHistoryBtn");

  if (!jobHistoryBody || !toggleHistoryBtn) return;

  jobHistoryBody.classList.toggle("hidden", collapsed);
  toggleHistoryBtn.textContent = collapsed ? "Expandir" : "Ocultar";

  localStorage.setItem("jobHistoryCollapsed", collapsed ? "1" : "0");
}

function restoreJobHistoryCollapsedState() {
  const saved = localStorage.getItem("jobHistoryCollapsed");

  if (saved === null) {
    setJobHistoryCollapsed(true);
    return;
  }

  setJobHistoryCollapsed(saved === "1");
}

async function loadJobHistory() {
  try {
    const response = await fetch("/api/jobs/history?limit=20");
    const data = await response.json();

    if (!response.ok || !data?.ok) {
      throw new Error(data?.detail || "Error cargando historial");
    }

    renderJobHistory(data.jobs || []);
  } catch (err) {
    console.error("Error loading history:", err);
  }
}

function renderJobHistory(jobs) {
  const jobHistoryList = document.getElementById("jobHistoryList");
  const jobHistoryCount = document.getElementById("jobHistoryCount");

  if (!jobHistoryList) return;

  if (jobHistoryCount) {
    jobHistoryCount.textContent = `${jobs.length} jobs`;
  }

  if (!jobs.length) {
    jobHistoryList.innerHTML = `<div class="empty-state">No hay ejecuciones aún</div>`;
    return;
  }

  jobHistoryList.innerHTML = "";

  jobs.forEach((job) => {
    const row = document.createElement("div");
    row.className = "history-item";

    const statusClass =
      job.status === "success"
        ? "success"
        : job.status === "error"
          ? "error"
          : job.status === "running"
            ? "running"
            : "neutral";

    const created = formatDate(job.created_at);
    const updated = formatDate(job.updated_at);

    row.innerHTML = `
      <div class="history-main">
        <div class="history-title">
          ${escapeHtml(job.source_name || "Sin nombre")}
        </div>
        <div class="history-meta">
          ${escapeHtml(job.client_label || "-")} · ${escapeHtml(job.mode || "-")} · ${escapeHtml(job.profile_name || "-")} · ${escapeHtml(job.language || "-")}
        </div>
        <div class="history-dates">
          <small>Inicio: ${created}</small> · <small>Update: ${updated}</small>
        </div>
      </div>

      <div class="history-actions">
        <span class="status-badge ${statusClass}">
          ${job.status}
        </span>

        <button class="btn secondary small" data-job="${job.job_id}">
          Ver estado
        </button>

        ${
          job.has_zip
            ? `<button class="btn primary small" data-zip="${job.zip_path}">
                ZIP
              </button>`
            : ""
        }
      </div>
    `;

    row.querySelector("[data-job]")?.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.job;
        if (!jobId) return;

        resetUI("Cargando job histórico...");
        setRunningState("local");

        try {
            await pollJob(jobId);
        } catch (error) {
            renderFatalError(error);
        }
    });

    row.querySelector("[data-zip]")?.addEventListener("click", (e) => {
      const path = e.currentTarget.dataset.zip;
      window.open(`/api/download-zip?path=${encodeURIComponent(path)}`, "_blank");
    });

    jobHistoryList.appendChild(row);
  });
}