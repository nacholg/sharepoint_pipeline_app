export const API = {
  localRun: "/api/local/run",
  sharepointRun: "/api/sharepoint/run",
  sharepointSites: "/api/sharepoint/sites",
  sharepointExplore: "/api/sharepoint/explore",
  profiles: "/api/profiles",
  clients: "/api/clients",
  jobStatus: (jobId) => `/api/jobs/${encodeURIComponent(jobId)}`,
  jobCancel: (jobId) => `/api/jobs/${encodeURIComponent(jobId)}/cancel`,
  jobsHistory: "/api/jobs/history",
};

export async function fetchJson(url, init = {}) {
  const response = await fetch(url, init);
  const data = await response.json();
  return { response, data };
}