(async function () {
  async function start() {
    if (typeof window.bootstrapApp === "function") {
      await window.bootstrapApp();
    } else {
      console.error("bootstrapApp no está disponible");
    }

    if (window.hotelLogoBtn && window.hotelLogoModal) {
      window.hotelLogoBtn.addEventListener("click", () => {
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

    if (window.hotelLogoForm) {
      window.hotelLogoForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const hotelName = window.hotelNameInput?.value?.trim() || "";
        const file = window.hotelLogoInput?.files?.[0];

        if (!hotelName || !file) {
          alert("Completá el nombre del hotel y elegí un archivo.");
          return;
        }

        // ✅ CREAR FORMDATA ACÁ
        const formData = new FormData();
        formData.append("hotel_name", hotelName);
        formData.append("file", file);

        // estado loading
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

          // success UI
          if (window.hotelLogoStatus) {
            window.hotelLogoStatus.classList.remove("hidden", "neutral", "error");
            window.hotelLogoStatus.classList.add("success");
            window.hotelLogoStatus.textContent = "Logo cargado";
            window.hotelLogoStatus.title = data.hotel_name || "";
          }

          alert(`Logo guardado para: ${data.hotel_name}`);
          window.hotelLogoForm.reset();
          window.hotelLogoModal.classList.add("hidden");

        } catch (error) {
          // error UI
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