(async function () {
  let hotelLogoRegistry = [];

  function normalizeHotelName(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");
  }

  async function loadHotelLogoRegistry() {
    try {
      const response = await fetch(window.API.hotelLogos);
      const data = await response.json();

      if (!response.ok || !data?.ok) {
        throw new Error(data?.detail || "No se pudo cargar el registry de logos");
      }

      hotelLogoRegistry = Array.isArray(data.items) ? data.items : [];

      if (window.hotelNameDatalist) {
        window.hotelNameDatalist.innerHTML = hotelLogoRegistry
          .map((item) => `<option value="${String(item.hotel_name || "").replace(/"/g, "&quot;")}"></option>`)
          .join("");
      }
    } catch (error) {
      console.error("Error cargando hotel logo registry:", error);
      hotelLogoRegistry = [];
    }
  }

  function updateDuplicateHint() {
    if (!window.hotelNameInput || !window.hotelDuplicateHint) return;

    const normalized = normalizeHotelName(window.hotelNameInput.value);
    const exactMatch = hotelLogoRegistry.find(
      (item) => normalizeHotelName(item.hotel_name) === normalized
    );

    if (normalized && exactMatch) {
      window.hotelDuplicateHint.classList.remove("hidden");
    } else {
      window.hotelDuplicateHint.classList.add("hidden");
    }
  }

  function clearLogoPreview() {
    if (window.hotelLogoPreviewImg) {
      window.hotelLogoPreviewImg.removeAttribute("src");
    }
    if (window.hotelLogoPreviewWrap) {
      window.hotelLogoPreviewWrap.classList.add("hidden");
    }
  }

  function updateLogoPreview() {
    const file = window.hotelLogoInput?.files?.[0];
    if (!file) {
      clearLogoPreview();
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (window.hotelLogoPreviewImg) {
        window.hotelLogoPreviewImg.src = reader.result;
      }
      if (window.hotelLogoPreviewWrap) {
        window.hotelLogoPreviewWrap.classList.remove("hidden");
      }
    };
    reader.readAsDataURL(file);
  }

  function resetHotelLogoFormState() {
    if (window.hotelLogoForm) {
      window.hotelLogoForm.reset();
    }
    if (window.hotelDuplicateHint) {
      window.hotelDuplicateHint.classList.add("hidden");
    }
    clearLogoPreview();
  }

  async function start() {
    if (typeof window.bootstrapApp === "function") {
      await window.bootstrapApp();
    } else {
      console.error("bootstrapApp no está disponible");
    }

    await loadHotelLogoRegistry();

    if (window.hotelLogoBtn && window.hotelLogoModal) {
      window.hotelLogoBtn.addEventListener("click", async () => {
        await loadHotelLogoRegistry();
        resetHotelLogoFormState();
        window.hotelLogoModal.classList.remove("hidden");
      });
    }

    if (window.closeHotelLogoModal && window.hotelLogoModal) {
      window.closeHotelLogoModal.addEventListener("click", () => {
        window.hotelLogoModal.classList.add("hidden");
      });
    }

    if (window.hotelLogoModalBackdrop && window.hotelLogoModal) {
      window.hotelLogoModalBackdrop.addEventListener("click", () => {
        window.hotelLogoModal.classList.add("hidden");
      });
    }

    if (window.hotelNameInput) {
      window.hotelNameInput.addEventListener("input", updateDuplicateHint);
      window.hotelNameInput.addEventListener("change", updateDuplicateHint);
    }

    if (window.hotelLogoInput) {
      window.hotelLogoInput.addEventListener("change", updateLogoPreview);
    }

    if (window.hotelLogoForm) {
      window.hotelLogoForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const hotelName = window.hotelNameInput?.value?.trim() || "";
        const file = window.hotelLogoInput?.files?.[0];

        if (!hotelName || !file) {
          alert("Completá el nombre del hotel y elegí un archivo.");
          return;
        }

        const normalized = normalizeHotelName(hotelName);
        const exactMatch = hotelLogoRegistry.find(
          (item) => normalizeHotelName(item.hotel_name) === normalized
        );

        let overwrite = false;
        if (exactMatch) {
          overwrite = window.confirm(
            `Ya existe un logo para "${exactMatch.hotel_name}". ¿Querés reemplazarlo?`
          );
          if (!overwrite) {
            return;
          }
        }

        const formData = new FormData();
        formData.append("hotel_name", hotelName);
        formData.append("file", file);
        formData.append("overwrite", overwrite ? "true" : "false");

        if (window.hotelLogoStatus) {
          window.hotelLogoStatus.classList.remove("hidden", "success", "error");
          window.hotelLogoStatus.classList.add("neutral");
          window.hotelLogoStatus.textContent = "Guardando...";
          window.hotelLogoStatus.title = "";
        }

        try {
          const response = await fetch(window.API.uploadHotelLogo, {
            method: "POST",
            body: formData,
          });

          const data = await response.json();

          if (!response.ok || !data?.ok) {
            throw new Error(data?.error || data?.detail || "No se pudo guardar el logo.");
          }

          if (window.hotelLogoStatus) {
            window.hotelLogoStatus.classList.remove("hidden", "neutral", "error");
            window.hotelLogoStatus.classList.add("success");
            window.hotelLogoStatus.textContent = "Logo cargado";
            window.hotelLogoStatus.title = data.hotel_name || "";
          }

          await loadHotelLogoRegistry();

          alert(`Logo guardado para: ${data.hotel_name}`);
          resetHotelLogoFormState();
          window.hotelLogoModal.classList.add("hidden");
        } catch (error) {
          if (window.hotelLogoStatus) {
            window.hotelLogoStatus.classList.remove("hidden", "neutral", "success");
            window.hotelLogoStatus.classList.add("error");
            window.hotelLogoStatus.textContent = "Error al guardar logo";
            window.hotelLogoStatus.title = "";
          }

          console.error("Error subiendo logo:", error);
          alert(error.message || "Error subiendo logo.");
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    await start();
  }
})();