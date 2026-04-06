function prEscapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function prBuildPreviewUrl(path) {
  return `/api/preview?path=${encodeURIComponent(path)}`;
}

function prGetBaseName(path) {
  const clean = String(path || "").split(/[\\/]/).pop() || "";
  const lastDot = clean.lastIndexOf(".");
  return lastDot >= 0 ? clean.slice(0, lastDot) : clean;
}

function prCollectArtifacts(result) {
  const files = Array.isArray(result.generated_files) ? result.generated_files : [];

  const htmlFiles = files.filter((f) => String(f).toLowerCase().endsWith(".html"));
  const pdfFiles = files.filter((f) => String(f).toLowerCase().endsWith(".pdf"));

  const pdfMap = new Map(
    pdfFiles.map((pdfPath) => [prGetBaseName(pdfPath).toLowerCase(), pdfPath])
  );

  return htmlFiles.map((htmlPath) => {
    const baseName = prGetBaseName(htmlPath);
    const pairedPdf = pdfMap.get(baseName.toLowerCase()) || null;

    return {
      name: htmlPath.split(/[\\/]/).pop() || baseName,
      htmlPath,
      previewUrl: prBuildPreviewUrl(htmlPath),
      pdfPath: pairedPdf,
    };
  });
}

function prRenderEmptyState() {
  return `
    <div class="preview-empty">
      <div class="preview-empty-icon">🖼️</div>
      <div class="preview-empty-title">No hay vouchers HTML para previsualizar</div>
      <div class="preview-empty-text">
        Cuando el pipeline genere archivos HTML, vas a poder verlos acá inline.
      </div>
    </div>
  `;
}

function prSetActiveButton(listEl, activeIndex) {
  const buttons = listEl.querySelectorAll(".preview-voucher-item");
  buttons.forEach((btn, idx) => {
    btn.classList.toggle("active", idx === activeIndex);
  });
}

function prMountPreview(sectionEl, artifacts, initialIndex = 0) {
  const listEl = sectionEl.querySelector(".preview-voucher-list");
  const frameEl = sectionEl.querySelector(".preview-frame");
  const titleEl = sectionEl.querySelector(".preview-title");
  const subtitleEl = sectionEl.querySelector(".preview-subtitle");
  const openHtmlBtn = sectionEl.querySelector(".preview-open-html");
  const downloadPdfBtn = sectionEl.querySelector(".preview-download-pdf");

  function selectArtifact(index) {
    const item = artifacts[index];
    if (!item) return;

    prSetActiveButton(listEl, index);

    titleEl.textContent = item.name;
    subtitleEl.textContent = item.htmlPath;

    frameEl.src = item.previewUrl;
    openHtmlBtn.href = item.previewUrl;

    if (item.pdfPath) {
      downloadPdfBtn.classList.remove("hidden");
      downloadPdfBtn.onclick = () => {
        if (typeof window.downloadFile === "function") {
          window.downloadFile(item.pdfPath);
        }
      };
    } else {
      downloadPdfBtn.classList.add("hidden");
      downloadPdfBtn.onclick = null;
    }
  }

  artifacts.forEach((item, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "preview-voucher-item";
    btn.innerHTML = `
      <span class="preview-voucher-name">${prEscapeHtml(item.name)}</span>
      <span class="preview-voucher-meta">${prEscapeHtml(prGetBaseName(item.htmlPath))}</span>
    `;
    btn.addEventListener("click", () => selectArtifact(index));
    listEl.appendChild(btn);
  });

  selectArtifact(initialIndex);
}

function renderPreviewSection(result) {
  const artifacts = prCollectArtifacts(result);

  if (!artifacts.length) {
    return `
      <section class="result-section preview-shell">
        <div class="preview-shell-header">
          <div>
            <h4>Preview inline</h4>
            <p class="muted-text">Vista embebida del voucher HTML generado.</p>
          </div>
        </div>
        ${prRenderEmptyState()}
      </section>
    `;
  }

  const wrapperId = `preview-shell-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

  const html = `
    <section class="result-section preview-shell" id="${wrapperId}">
      <div class="preview-shell-header">
        <div>
          <h4>Preview inline</h4>
          <p class="muted-text">Vista embebida del voucher HTML generado.</p>
        </div>
        <div class="preview-shell-badge">
          ${artifacts.length} voucher${artifacts.length > 1 ? "s" : ""}
        </div>
      </div>

      <div class="preview-layout">
        <aside class="preview-sidebar">
          <div class="preview-sidebar-title">Vouchers</div>
          <div class="preview-voucher-list"></div>
        </aside>

        <div class="preview-stage">
          <div class="preview-toolbar">
            <div class="preview-toolbar-main">
              <div class="preview-title">Preview</div>
              <div class="preview-subtitle muted-text">—</div>
            </div>

            <div class="preview-toolbar-actions">
              <a
                class="btn secondary small preview-open-html"
                href="#"
                target="_blank"
                rel="noopener noreferrer"
              >
                Abrir HTML
              </a>
              <button
                type="button"
                class="btn primary small preview-download-pdf hidden"
              >
                Descargar PDF
              </button>
            </div>
          </div>

          <div class="preview-frame-wrap">
            <iframe
              class="preview-frame"
              title="Voucher preview inline"
              loading="lazy"
            ></iframe>
          </div>
        </div>
      </div>
    </section>
  `;

  setTimeout(() => {
    const sectionEl = document.getElementById(wrapperId);
    if (!sectionEl) return;
    prMountPreview(sectionEl, artifacts, 0);
  }, 0);

  return html;
}

window.renderPreviewSection = renderPreviewSection;