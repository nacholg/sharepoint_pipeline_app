export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function getStepLabel(stepName) {
  const labels = {
    preparing_local_job: "Preparando ejecución local",
    preparing_sharepoint_job: "Preparando ejecución SharePoint",
    loading_sharepoint_source: "Descargando archivo desde SharePoint",
    uploading_outputs: "Subiendo resultados a SharePoint",
    xlsx_to_voucher_json: "Preparando vouchers",
    enrich_hotels: "Obteniendo información de hoteles",
    render_vouchers_html: "Generando vouchers",
    render_vouchers_pdf: "Generando PDFs finales",
  };
  return labels[stepName] || stepName || "Procesando";
}