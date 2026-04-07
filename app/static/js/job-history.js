(function () {
  const JOB_HISTORY_COLLAPSED_KEY = "jobHistoryCollapsed";

  function historyEscapeHtml(value) {
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

  function setJobHistoryCollapsed(collapsed) {
    const jobHistoryBody = window.jobHistoryBody;
    const toggleHistoryBtn = window.toggleHistoryBtn;

    if (!jobHistoryBody || !toggleHistoryBtn) return;

    jobHistoryBody.classList.toggle("hidden", collapsed);
    toggleHistoryBtn.textContent = collapsed ? "Expandir" : "Ocultar";

    localStorage.setItem(JOB_HISTORY_COLLAPSED_KEY, collapsed ? "1" : "0");
  }

  function restoreJobHistoryCollapsedState() {
    const saved = localStorage.getItem(JOB_HISTORY_COLLAPSED_KEY);

    if (saved === null) {
      setJobHistoryCollapsed(true);
      return;
    }

    setJobHistoryCollapsed(saved === "1");
  }

  async function loadJobHistory() {
    try {
      const response = await fetch(`${window.API.jobsHistory}?limit=20`);
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
    const host = window.jobHistoryBody || document.getElementById("jobHistoryBody");
    if (!host) return;

    if (!jobs.length) {
      host.innerHTML = `<div class="empty-state">No hay ejecuciones aún</div>`;
      return;
    }

    host.innerHTML = jobs
      .map((job) => buildHistoryItemHtml(job))
      .join("");

    bindHistoryItemEvents(host, jobs);
  }

  function buildHistoryItemHtml(job) {
    const statusClass =
      job.status === "success"
        ? "success"
        : job.status === "error"
          ? "error"
          : job.status === "running"
            ? "running"
            : job.status === "cancelled"
              ? "pending"
              : "neutral";

    const created =
      typeof window.formatDate === "function"
        ? window.formatDate(job.created_at)
        : "-";

    const updated =
      typeof window.formatDate === "function"
        ? window.formatDate(job.updated_at)
        : "-";

    const title = historyEscapeHtml(job.source_name || "Sin nombre");
    const client = historyEscapeHtml(job.client_label || "-");
    const mode = historyEscapeHtml(job.mode || "-");
    const profile = historyEscapeHtml(job.profile_name || "-");
    const language = historyEscapeHtml(job.language || "-");
    const status = historyEscapeHtml(job.status || "pending");
    const progress = Math.max(0, Math.min(100, Number(job.progress) || 0));
    const zipFile = job.zip_file || "";

    return `
      <div class="history-item" data-job-id="${historyEscapeHtml(job.job_id)}">
        <div class="history-main">
          <div class="history-title">${title}</div>
          <div class="history-meta">
            ${client} · ${mode} · ${profile} · ${language}
          </div>
          <div class="history-dates">
            <small>Inicio: ${created}</small> · <small>Update: ${updated}</small>
          </div>
          <div class="job-history-progress" style="margin-top:10px;">
            <div class="job-history-progress-bar">
              <div class="job-history-progress-fill" style="width:${progress}%"></div>
            </div>
            <span class="muted-text">${progress}%</span>
          </div>
        </div>

        <div class="history-actions">
          <span class="status-badge ${statusClass}">
            ${status}
          </span>

          <button class="btn secondary small" data-action="view-status" data-job-id="${historyEscapeHtml(job.job_id)}">
            Ver estado
          </button>

          ${
            job.has_zip && zipFile
              ? `<button class="btn primary small" data-action="download-zip" data-zip-path="${historyEscapeHtml(zipFile)}">
                  ZIP
                </button>`
              : ""
          }
        </div>
      </div>
    `;
  }

  function bindHistoryItemEvents(host) {
    host.querySelectorAll('[data-action="view-status"]').forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        if (!jobId) return;

        if (typeof window.resetUI === "function") {
          window.resetUI("Cargando job histórico...");
        }

        if (typeof window.setRunningState === "function") {
          window.setRunningState("local");
        }

        try {
          await window.pollJob(jobId);
        } catch (error) {
          if (typeof window.renderFatalError === "function") {
            window.renderFatalError(error);
          } else {
            console.error(error);
          }
        }
      });
    });

    host.querySelectorAll('[data-action="download-zip"]').forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const path = e.currentTarget.dataset.zipPath;
        if (!path) return;

        if (typeof window.downloadZip === "function") {
          window.downloadZip(path);
          return;
        }

        window.open(`/api/download-zip?path=${encodeURIComponent(path)}`, "_blank");
      });
    });
  }

  window.setJobHistoryCollapsed = setJobHistoryCollapsed;
  window.restoreJobHistoryCollapsedState = restoreJobHistoryCollapsedState;
  window.loadJobHistory = loadJobHistory;
  window.renderJobHistory = renderJobHistory;
})();