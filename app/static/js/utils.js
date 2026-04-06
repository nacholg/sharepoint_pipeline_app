const ALLOWED_EXCEL_EXTENSIONS = [".xlsx", ".xlsm", ".xls"];

function getSelectedLanguage(selectEl) {
  return selectEl?.value || "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function isValidExcelFilename(name) {
  const lowerName = (name || "").toLowerCase();
  return ALLOWED_EXCEL_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

function formatDate(ts) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}