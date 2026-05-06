// ==========================
// VOUCHER PREVIEW MODULE
// ==========================

function vpGetVoucherId(voucher) {
  return String(
    voucher?.selection_id ||
    voucher?.voucher_group_key ||
    voucher?.voucher_id ||
    ""
  );
}

function vpIsReviewVoucher(voucher) {
  const passengers = voucher.passengers || [];
  const hasPendingName = passengers.some((p) =>
    String(p || "").toUpperCase().includes("NAME PENDING")
  );

  const hasWarnings = Array.isArray(voucher.warnings) && voucher.warnings.length > 0;
  const hasErrors = Array.isArray(voucher.errors) && voucher.errors.length > 0;

  return hasPendingName || hasWarnings || hasErrors;
}

function vpGetSelectedVoucherIds() {
  return Array.from(document.querySelectorAll(".voucher-select-checkbox:checked"))
    .map((input) => String(input.dataset.voucherId || ""))
    .filter(Boolean);
}

function vpGetPreviewVouchers() {
  return window.APP_STATE?.data?.voucherPreview?.voucher_candidates || [];
}

function vpSyncSelectedVoucherIds() {
  const selectedIds = vpGetSelectedVoucherIds();

  if (window.APP_STATE?.data) {
    window.APP_STATE.data.selectedVoucherIds = selectedIds;
  }

  vpUpdateSelectionSummary();
  return selectedIds;
}

function vpUpdateSelectionSummary() {
  const summaryEl = document.getElementById("voucherPreviewSelectionSummary");
  const hintEl = document.getElementById("voucherPreviewRunHint");
  const footerEl = document.getElementById("voucherPreviewModalFooterLabel");
  const inlineSummaryEl = document.getElementById("voucherPreviewInlineSummary");

  const vouchers = vpGetPreviewVouchers();
  const selectedIds = window.APP_STATE?.data?.selectedVoucherIds || [];
  const okCount = vouchers.filter((v) => !vpIsReviewVoucher(v)).length;
  const reviewCount = vouchers.length - okCount;
  const text = `${selectedIds.length} de ${vouchers.length} vouchers seleccionados`;

  if (summaryEl) summaryEl.textContent = text;
  if (inlineSummaryEl) inlineSummaryEl.textContent = text;

  if (hintEl) {
    hintEl.textContent = selectedIds.length
      ? "Se generarán únicamente los vouchers seleccionados."
      : "Seleccioná al menos un voucher para generar.";
  }

  if (footerEl) {
    footerEl.textContent = selectedIds.length
      ? "La selección está lista para ejecutar el pipeline."
      : "No hay vouchers seleccionados.";
  }

  if (window.runLocalBtn && window.APP_STATE?.data?.voucherPreview) {
    window.runLocalBtn.disabled = selectedIds.length === 0;
    window.runLocalBtn.classList.toggle("is-disabled", selectedIds.length === 0);
  }
}

function vpApplySelectionByIds(ids) {
  const selected = new Set(ids.map(String));

  document.querySelectorAll(".voucher-select-checkbox").forEach((input) => {
    input.checked = selected.has(String(input.dataset.voucherId || ""));
  });

  vpSyncSelectedVoucherIds();
}

function vpSelectAll(value) {
  document.querySelectorAll(".voucher-select-checkbox").forEach((input) => {
    input.checked = !!value;
  });

  vpSyncSelectedVoucherIds();
}

function vpSelectOnlyOk() {
  const okIds = vpGetPreviewVouchers()
    .filter((voucher) => !vpIsReviewVoucher(voucher))
    .map(vpGetVoucherId)
    .filter(Boolean);

  vpApplySelectionByIds(okIds);
}

function vpDeselectReview() {
  const keepIds = vpGetPreviewVouchers()
    .filter((voucher) => !vpIsReviewVoucher(voucher))
    .map(vpGetVoucherId)
    .filter(Boolean);

  vpApplySelectionByIds(keepIds);
}

function vpOpenModal() {
  document.getElementById("voucherPreviewModal")?.classList.remove("hidden");
}

function vpCloseModal() {
  document.getElementById("voucherPreviewModal")?.classList.add("hidden");
}

function vpBuildStatusBadge(voucher) {
  const hasErrors = Array.isArray(voucher.errors) && voucher.errors.length > 0;
  const hasWarnings = Array.isArray(voucher.warnings) && voucher.warnings.length > 0;
  const hasReview = vpIsReviewVoucher(voucher);

  if (hasErrors) return `<span class="badge error">Error</span>`;
  if (hasWarnings || hasReview) return `<span class="badge warning">Revisar</span>`;
  return `<span class="badge success">OK</span>`;
}

function vpFormatPassengers(passengers) {
  const list = Array.isArray(passengers) ? passengers : [];

  if (!list.length) {
    return `<span class="muted-text">Sin pasajeros</span>`;
  }

  return list
    .map((name) => {
      const safeName = escapeHtml(name || "NAME PENDING");
      const isPending = String(name || "").toUpperCase().includes("NAME PENDING");

      return `
        <div class="voucher-preview-passenger ${isPending ? "is-pending" : ""}">
          ${safeName}
        </div>
      `;
    })
    .join("");
}

function vpRenderInlineSummary(data) {
  const host = document.getElementById("voucherPreviewHost");
  if (!host) return;

  const vouchers = data?.voucher_candidates || [];
  const selectedIds = window.APP_STATE?.data?.selectedVoucherIds || [];

  const okCount = vouchers.filter((v) => !vpIsReviewVoucher(v)).length;
  const reviewCount = vouchers.length - okCount;

  host.innerHTML = `
    <div class="voucher-preview-inline-summary">
      <div>
        <strong>${vouchers.length} vouchers detectados</strong>

        <p id="voucherPreviewInlineSummary" class="muted-text">
          ${selectedIds.length} de ${vouchers.length} vouchers seleccionados
        </p>

        <p class="muted-text">
          ${okCount} OK · ${reviewCount} revisar
        </p>
      </div>

      <div class="panel-actions panel-actions-inline">
        <button
          id="openVoucherPreviewModalBtn"
          class="btn secondary"
          type="button"
        >
          Revisar selección
        </button>
      </div>
    </div>
  `;

  document
    .getElementById("openVoucherPreviewModalBtn")
    ?.addEventListener("click", vpOpenModal);
}
function vpRenderModalCards(data) {
  const body = document.getElementById("voucherPreviewModalBody");
  if (!body) return;

  const vouchers = data?.voucher_candidates || [];
  const selectedIds = new Set(window.APP_STATE?.data?.selectedVoucherIds || []);

  if (!vouchers.length) {
    body.innerHTML = `
      <div class="empty-state-inline">
        No se detectaron vouchers.
      </div>
    `;
    return;
  }

  body.innerHTML = `
    <div class="voucher-preview-grid">
      ${vouchers.map((v) => {
        const voucherId = vpGetVoucherId(v);
        const checked = selectedIds.has(voucherId) ? "checked" : "";

        return `
          <article class="voucher-preview-card">
            <div class="voucher-preview-card-head">
              <label class="voucher-preview-check">
                <input
                  type="checkbox"
                  ${checked}
                  data-voucher-id="${escapeHtml(voucherId)}"
                  class="voucher-select-checkbox"
                />
                <span>Generar</span>
              </label>

              ${vpBuildStatusBadge(v)}
            </div>

            <div>
              <span class="eyebrow">Voucher</span>
              <h4>${escapeHtml(voucherId || "—")}</h4>
            </div>

            <div class="voucher-preview-main">
              <div>
                <span class="voucher-preview-label">Pasajeros</span>
                <div class="voucher-preview-passengers">
                  ${vpFormatPassengers(v.passengers)}
                </div>
              </div>

              <div>
                <span class="voucher-preview-label">Hotel</span>
                <strong>${escapeHtml(v.hotel_name || "—")}</strong>
              </div>
            </div>

            <div class="voucher-preview-meta">
              <div>
                <span>Check-in</span>
                <strong>${escapeHtml(v.check_in || "—")}</strong>
              </div>

              <div>
                <span>Check-out</span>
                <strong>${escapeHtml(v.check_out || "—")}</strong>
              </div>

              <div>
                <span>Noches</span>
                <strong>${escapeHtml(v.nights ?? "—")}</strong>
              </div>

              <div>
                <span>Pax</span>
                <strong>${escapeHtml(v.passenger_count ?? v.pax_count ?? "—")}</strong>
              </div>
            </div>

            <div class="voucher-preview-room">
              <span>Habitación</span>
              <strong>${escapeHtml(v.room_category || "—")}</strong>
            </div>
          </article>
        `;
      }).join("")}
    </div>
  `;

  document.querySelectorAll(".voucher-select-checkbox").forEach((input) => {
    input.addEventListener("change", vpSyncSelectedVoucherIds);
  });
}

async function loadVoucherPreview() {
  const file = fileInput?.files?.[0];

  if (!file) {
    alert("Seleccioná un Excel.");
    return;
  }

  const selectedProfile = localProfileSelect?.value || "default";
  const language = getSelectedLanguage(languageSelect);
  const host = document.getElementById("voucherPreviewHost");

  if (host) {
    host.innerHTML = `
      <div class="empty-state-inline">
        Leyendo Excel y detectando vouchers...
      </div>
    `;
  }

  try {
    const formData = new FormData();

    formData.append("file", file);
    formData.append("profile", selectedProfile);
    formData.append("client_key", selectedClient?.key || "");
    formData.append("language", language);

    const response = await fetch(API.localPreviewVouchers, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok || !data?.ok) {
      throw new Error(data?.detail || "No se pudo leer el Excel.");
    }

    window.APP_STATE.data.voucherPreview = data;
    window.APP_STATE.data.selectedVoucherIds = (data.voucher_candidates || [])
      .filter((voucher) => !vpIsReviewVoucher(voucher))
      .map(vpGetVoucherId)
      .filter(Boolean);

    vpRenderInlineSummary(data);
    vpRenderModalCards(data);
    vpUpdateSelectionSummary();
    vpOpenModal();
  } catch (error) {
    if (host) {
      host.innerHTML = `
        <div class="error-banner">
          ${escapeHtml(error?.message || String(error))}
        </div>
      `;
    } else {
      alert(error?.message || String(error));
    }
  }
}

function bindVoucherPreviewModalEvents() {
  document
    .getElementById("closeVoucherPreviewModalBtn")
    ?.addEventListener("click", vpCloseModal);

  document
    .getElementById("voucherPreviewModalBackdrop")
    ?.addEventListener("click", vpCloseModal);

  document
    .getElementById("confirmVoucherSelectionBtn")
    ?.addEventListener("click", () => {
      vpSyncSelectedVoucherIds();
      vpCloseModal();
    });

  document
    .getElementById("selectAllVouchersBtn")
    ?.addEventListener("click", () => vpSelectAll(true));

  document
    .getElementById("clearVoucherSelectionBtn")
    ?.addEventListener("click", () => vpSelectAll(false));

  document
    .getElementById("selectOkVouchersBtn")
    ?.addEventListener("click", vpSelectOnlyOk);

  document
    .getElementById("deselectReviewVouchersBtn")
    ?.addEventListener("click", vpDeselectReview);
}

window.loadVoucherPreview = loadVoucherPreview;
window.bindVoucherPreviewModalEvents = bindVoucherPreviewModalEvents;
window.vpSyncSelectedVoucherIds = vpSyncSelectedVoucherIds;