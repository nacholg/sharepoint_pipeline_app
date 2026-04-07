import { dom } from "./dom.js";
import { state } from "./state.js";
import { escapeHtml } from "./helpers.js";

const originalFetch = window.fetch.bind(window);
const GRAPH_RELATED_PATHS = ["/api/sharepoint/", "/auth/session-status"];

function isAuthStatusEndpoint(input) {
  const url = typeof input === "string" ? input : input?.url || "";
  return url.includes("/auth/session-status");
}

function shouldHandleAuthFailure(input) {
  const url = typeof input === "string" ? input : input?.url || "";
  return GRAPH_RELATED_PATHS.some((path) => url.includes(path));
}

function getLoginButton() {
  return document.querySelector('a[href="/auth/login"]');
}

function getLogoutButton() {
  return document.querySelector('a[href="/auth/logout"]');
}

function getUserPill() {
  return document.querySelector(".user-pill");
}

export function setSharePointControlsEnabled(enabled) {
  const elements = [
    dom.runSPBtn,
    dom.pickSPFileBtn,
    dom.pickSPFolderBtn,
    dom.sourceSiteSelect,
    dom.destinationSiteSelect,
    dom.modalSiteSelect,
    dom.sharepointProfileSelect,
  ];

  for (const el of elements) {
    if (!el) continue;
    el.disabled = !enabled;
    el.classList.toggle("is-disabled", !enabled);
  }

  dom.spSection?.classList.toggle("is-disabled", !enabled);
}

export function ensureSessionBanner() {
  let banner = document.getElementById("session-banner");
  if (banner) return banner;

  const topbarActions = document.querySelector(".topbar-actions");
  if (!topbarActions) return null;

  banner = document.createElement("div");
  banner.id = "session-banner";
  banner.className = "notice warning hidden";
  banner.style.minWidth = "260px";
  topbarActions.prepend(banner);
  return banner;
}

function renderUserPillAuthenticated(user) {
  const pill = getUserPill();
  if (!pill) return;

  pill.classList.add("success");
  pill.innerHTML = `
    <div class="user-avatar user-avatar-status" aria-label="Usuario conectado">
      <span class="status-dot status-dot-online"></span>
    </div>
    <div>
      <strong>${escapeHtml(user?.name || "Usuario autenticado")}</strong>
      <small>${escapeHtml(user?.email || "")}</small>
    </div>
  `;
}

function renderUserPillUnauthenticated(expired = false) {
  const pill = getUserPill();
  if (!pill) return;

  pill.classList.remove("success");
  pill.innerHTML = `
    <div class="user-avatar user-avatar-status" aria-label="Sin sesión activa">
      <span class="status-dot status-dot-idle"></span>
    </div>
    <div>
      <strong>SharePoint</strong>
      <small>${expired ? "Sesión vencida. Volvé a iniciar sesión" : "Conectá tu cuenta Microsoft"}</small>
    </div>
  `;
}

export function applyAuthStateToUI(nextState) {
  state.auth.authenticated = !!nextState?.authenticated;
  state.auth.user = nextState?.user || null;
  state.auth.reason = nextState?.reason || null;

  const banner = ensureSessionBanner();
  const loginBtn = getLoginButton();
  const logoutBtn = getLogoutButton();

  if (state.auth.authenticated) {
    renderUserPillAuthenticated(state.auth.user);

    if (banner) {
      banner.textContent = "";
      banner.classList.add("hidden");
    }

    loginBtn?.classList.add("hidden");
    logoutBtn?.classList.remove("hidden");

    setSharePointControlsEnabled(true);
    state.auth.sessionExpiredAlertShown = false;
    return;
  }

  const expired = state.auth.reason === "expired";
  renderUserPillUnauthenticated(expired);

  if (banner) {
    banner.textContent = expired
      ? "Tu sesión de Microsoft expiró. Volvé a iniciar sesión para usar SharePoint."
      : "Iniciá sesión con Microsoft para usar SharePoint.";
    banner.classList.remove("hidden");
  }

  loginBtn?.classList.remove("hidden");
  logoutBtn?.classList.add("hidden");

  setSharePointControlsEnabled(false);
}

export async function fetchSessionStatus() {
  const resp = await originalFetch("/auth/session-status", {
    credentials: "same-origin",
    cache: "no-store",
  });

  if (!resp.ok) {
    throw new Error("No se pudo validar la sesión");
  }

  return await resp.json();
}

export async function initAuthState() {
  try {
    const status = await fetchSessionStatus();
    applyAuthStateToUI(status);
  } catch (err) {
    applyAuthStateToUI({
      authenticated: false,
      reason: "unknown",
      user: null,
    });
    console.error("Error validando sesión:", err);
  }
}

export function handleExpiredSessionUI() {
  applyAuthStateToUI({
    authenticated: false,
    reason: "expired",
    user: null,
  });

  if (!state.auth.sessionExpiredAlertShown) {
    state.auth.sessionExpiredAlertShown = true;
    alert("Tu sesión de Microsoft expiró. Volvé a iniciar sesión.");
  }
}

export async function fetchWithAuthHandling(input, init = {}) {
  const mergedInit = {
    credentials: "same-origin",
    cache: "no-store",
    ...init,
  };

  const response = await originalFetch(input, mergedInit);

  if (
    shouldHandleAuthFailure(input) &&
    !isAuthStatusEndpoint(input) &&
    (response.status === 401 || response.status === 403)
  ) {
    handleExpiredSessionUI();
    throw new Error("SESSION_EXPIRED");
  }

  return response;
}

export function installFetchInterceptor() {
  window.fetch = fetchWithAuthHandling;
}