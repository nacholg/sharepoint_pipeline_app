(function () {
  "use strict";
  const KEY = "voucher-ui-theme";
  const allowed = ["light", "dark", "system"];
  const select = document.getElementById("themeSelect");
  if (!select) return;
  let saved = "system";
  try { saved = localStorage.getItem(KEY) || "system"; } catch (_) {}
  if (!allowed.includes(saved)) saved = "system";
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  function apply(value) {
    const resolved = value === "system" ? (media.matches ? "dark" : "light") : value;
    document.documentElement.dataset.theme = resolved;
    select.value = value;
  }
  apply(saved);
  select.addEventListener("change", () => {
    const value = allowed.includes(select.value) ? select.value : "system";
    try { localStorage.setItem(KEY, value); } catch (_) {}
    apply(value);
  });
  const onSystemChange = () => { if (select.value === "system") apply("system"); };
  if (media.addEventListener) media.addEventListener("change", onSystemChange);
  else if (media.addListener) media.addListener(onSystemChange);
})();
