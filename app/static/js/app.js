(async function () {
  async function start() {
    if (typeof window.bootstrapApp === "function") {
      await window.bootstrapApp();
    } else {
      console.error("bootstrapApp no está disponible");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    await start();
  }
})();