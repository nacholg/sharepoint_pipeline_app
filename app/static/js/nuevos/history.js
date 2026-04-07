import { API, fetchJson } from "./api.js";
import { dom } from "./dom.js";

const HISTORY_COLLAPSED_KEY = "voucher_history_collapsed";

export function setJobHistoryCollapsed(collapsed) {
  dom.jobHistoryBody?.classList.toggle("hidden", collapsed);
  localStorage.setItem(HISTORY_COLLAPSED_KEY, collapsed ? "1" : "0");
}

export function restoreJobHistoryCollapsedState() {
  const collapsed = localStorage.getItem(HISTORY_COLLAPSED_KEY) === "1";
  setJobHistoryCollapsed(collapsed);
}

export async function loadJobHistory() {
  const { response, data } = await fetchJson(API.jobsHistory);
  if (!response.ok || !data?.ok || !dom.jobHistoryBody) return;

  const jobs = Array.isArray(data.jobs) ? data.jobs : [];
  dom.jobHistoryBody.innerHTML = jobs.length
    ? jobs.map((job) => `<div class="history-item"><div class="history-main"><div class="history-title">${job.job_id}</div></div></div>`).join("")
    : `<div class="muted-text">No hay ejecuciones registradas todavía.</div>`;
}

export function bindHistoryEvents() {
  dom.refreshHistoryBtn?.addEventListener("click", loadJobHistory);

  dom.toggleHistoryBtn?.addEventListener("click", () => {
    const collapsed = dom.jobHistoryBody?.classList.contains("hidden");
    setJobHistoryCollapsed(!collapsed);
  });
}