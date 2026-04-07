function () {
  const PREFS_KEY = "voucher_prefs";

  function savePrefs(prefs) {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  }

  function loadPrefs() {
    try {
      return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
    } catch {
      return {};
    }
  }

  function persistSourceFolderPreference(folderId, folderName, siteKey) {
    if (!folderId || !siteKey) return;

    const prefs = loadPrefs();
    prefs.sourceFolderId = folderId;
    prefs.sourceFolderName = folderName || "Carpeta recordada";
    prefs.sourceFolderSite = siteKey;
    savePrefs(prefs);
  }

  window.PREFS_KEY = PREFS_KEY;
  window.savePrefs = savePrefs;
  window.loadPrefs = loadPrefs;
  window.persistSourceFolderPreference = persistSourceFolderPreference;
})();