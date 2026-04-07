const PREFS_KEY = "voucher_prefs";

export function savePrefs(prefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}

export function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
  } catch {
    return {};
  }
}

export function persistSourceFolderPreference(folderId, folderName, siteKey) {
  if (!folderId || !siteKey) return;

  const prefs = loadPrefs();
  prefs.sourceFolderId = folderId;
  prefs.sourceFolderName = folderName || "Carpeta recordada";
  prefs.sourceFolderSite = siteKey;
  savePrefs(prefs);
}