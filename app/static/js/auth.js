(function () {
  const originalFetch = window.fetch.bind(window);

  function authEscapeHtml(value) {
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

  function isAuthStatusEndpoint(input) {
    const url = typeof input === "string" ? input : input?.url || "";
    return url.includes("/auth/session-status");
  }

  function shouldHandleAuthFailure(input) {
    const url = typeof input === "string" ? input : input?.url || "";
    return url.includes("/api/sharepoint/") || url.includes("/auth/session-status");
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

  function setSharePointControlsEnabled(enabled) {
    const elements = [
      window.runSPBtn,
      window.pickSPFileBtn,
      window.pickSPFolderBtn,
      window.sourceSiteSelect,
      window.destinationSiteSelect,
      window.modalSiteSelect,
      window.sharepointProfileSelect,
    ];

    for (const el of elements) {
      if (!el) continue;
      el.disabled = !enabled;
      el.classList.toggle("is-disabled", !enabled);
    }

    if (window.spSection) {
      window.spSection.classList.toggle("is-disabled", !enabled);
    }
  }

  function ensureSessionBanner() {
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
    pill.classList.remove("expired");

    pill.innerHTML = `
      <div class="user-avatar user-avatar-status" aria-label="Usuario conectado">
        <span class="status-dot status-dot-online"></span>
      </div>
      <div>
        <strong>${authEscapeHtml(user?.name || "Usuario autenticado")}</strong>
        <small>${authEscapeHtml(user?.email || "")}</small>
      </div>
    `;
  }

  function renderUserPillUnauthenticated(expired = false) {
    const pill = getUserPill();
    if (!pill) return;

    pill.classList.remove("success");
    pill.classList.toggle("expired", expired);

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

  function applyAuthStateToUI(nextState) {
    window.authState = {
      ...window.authState,
      authenticated: !!nextState?.authenticated,
      user: nextState?.user || null,
      reason: nextState?.reason || null,
    };

    const banner = ensureSessionBanner();
    const loginBtn = getLoginButton();
    const logoutBtn = getLogoutButton();

    if (window.authState.authenticated) {
      renderUserPillAuthenticated(window.authState.user);

      if (banner) {
        banner.textContent = "";
        banner.classList.add("hidden");
      }

      if (loginBtn) loginBtn.classList.add("hidden");
      if (logoutBtn) logoutBtn.classList.remove("hidden");

      setSharePointControlsEnabled(true);
      window.sessionExpiredAlertShown = false;
      window.authState.sessionExpiredAlertShown = false;
      return;
    }

    const expired = window.authState.reason === "expired";
    renderUserPillUnauthenticated(expired);

    if (banner) {
      banner.textContent = expired
        ? "Tu sesión de Microsoft expiró. Volvé a iniciar sesión para usar SharePoint."
        : "Iniciá sesión con Microsoft para usar SharePoint.";
      banner.classList.remove("hidden");
    }

    if (loginBtn) loginBtn.classList.remove("hidden");
    if (logoutBtn) logoutBtn.classList.add("hidden");

    setSharePointControlsEnabled(false);
  }

  async function fetchSessionStatus() {
    const resp = await originalFetch("/auth/session-status", {
      credentials: "same-origin",
      cache: "no-store",
    });

    if (!resp.ok) {
      throw new Error("No se pudo validar la sesión");
    }

    return await resp.json();
  }

  async function initAuthState() {
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

  function handleExpiredSessionUI() {
    applyAuthStateToUI({
      authenticated: false,
      reason: "expired",
      user: null,
    });

    if (!window.sessionExpiredAlertShown) {
      window.sessionExpiredAlertShown = true;
      window.authState.sessionExpiredAlertShown = true;
      alert("Tu sesión de Microsoft expiró. Volvé a iniciar sesión.");
    }
  }

  async function fetchWithAuthHandling(input, init = {}) {
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

  function installFetchInterceptor() {
    window.fetch = fetchWithAuthHandling;
  }

  window.setSharePointControlsEnabled = setSharePointControlsEnabled;
  window.ensureSessionBanner = ensureSessionBanner;
  window.applyAuthStateToUI = applyAuthStateToUI;
  window.fetchSessionStatus = fetchSessionStatus;
  window.initAuthState = initAuthState;
  window.handleExpiredSessionUI = handleExpiredSessionUI;
  window.fetchWithAuthHandling = fetchWithAuthHandling;
  window.installFetchInterceptor = installFetchInterceptor;
})();