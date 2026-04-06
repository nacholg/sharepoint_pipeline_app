// ==========================
// VALIDATION MODAL MODULE
// ==========================

function ensureValidationModal() {
  if (document.getElementById("validationModal")) return;

  const modal = document.createElement("div");
  modal.id = "validationModal";
  modal.className = "validation-modal hidden";
  modal.innerHTML = `
    <div class="validation-modal-backdrop" id="validationModalBackdrop"></div>
    <div class="validation-modal-dialog">
      <div class="validation-modal-header">
        <h3 id="validationModalTitle">Detalle</h3>
        <button type="button" class="validation-modal-close" id="validationModalClose">×</button>
      </div>
      <div class="validation-modal-body" id="validationModalBody"></div>
    </div>
  `;
  document.body.appendChild(modal);

  document
    .getElementById("validationModalBackdrop")
    ?.addEventListener("click", closeValidationModal);

  document
    .getElementById("validationModalClose")
    ?.addEventListener("click", closeValidationModal);
}

function openValidationModal(title, rows, type = "warning") {
  ensureValidationModal();

  const modal = document.getElementById("validationModal");
  const titleEl = document.getElementById("validationModalTitle");
  const bodyEl = document.getElementById("validationModalBody");

  if (!modal || !titleEl || !bodyEl) return;

  titleEl.textContent = title;

  if (!Array.isArray(rows) || !rows.length) {
    bodyEl.innerHTML = `<p class="muted-text">No hay detalles para mostrar.</p>`;
  } else {
    bodyEl.innerHTML = rows
      .map((item) => renderValidationRowCard(item, type))
      .join("");
  }

  modal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeValidationModal() {
  const modal = document.getElementById("validationModal");
  if (!modal) return;

  modal.classList.add("hidden");
  document.body.style.overflow = "";
}

function renderValidationRowCard(item, type = "warning") {
  const row = item?.row || {};
  const issues =
    type === "error"
      ? Array.isArray(item?.errors)
        ? item.errors
        : []
      : Array.isArray(item?.warnings)
        ? item.warnings
        : [];

  const fullName =
    row.full_name ||
    [row.first_name, row.last_name].filter(Boolean).join(" ") ||
    "-";

  const excelRow = row.excel_row_number ?? "-";
  const hotel = row.hotel_name || "-";
  const room = row.room || "-";
  const destination = row.destination || "-";
  const passport = row.passport_number || "-";
  const checkIn = row.check_in || "-";
  const checkOut = row.check_out || "-";

  return `
    <article class="validation-row-card">
      <div class="validation-row-top">
        <div>
          <div class="validation-row-title">${escapeHtml(fullName)}</div>
          <div class="validation-row-subtitle">Fila Excel: ${escapeHtml(excelRow)}</div>
        </div>
        <div class="validation-row-badge ${type === "error" ? "is-error" : "is-warning"}">
          ${type === "error" ? "Error" : "Warning"}
        </div>
      </div>

      <div class="validation-row-issues">
        ${issues.map((issue) => `<span class="validation-issue-pill">${escapeHtml(issue)}</span>`).join("")}
      </div>

      <div class="validation-row-grid">
        <div><strong>Hotel:</strong> ${escapeHtml(hotel)}</div>
        <div><strong>Destino:</strong> ${escapeHtml(destination)}</div>
        <div><strong>Hab:</strong> ${escapeHtml(room)}</div>
        <div><strong>Pasaporte:</strong> ${escapeHtml(passport)}</div>
        <div><strong>Check-in:</strong> ${escapeHtml(checkIn)}</div>
        <div><strong>Check-out:</strong> ${escapeHtml(checkOut)}</div>
      </div>
    </article>
  `;
}

window.openValidationModal = openValidationModal;