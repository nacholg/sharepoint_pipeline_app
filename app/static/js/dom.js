(function () {
  const dom = {
    languageSelect: document.getElementById("languageSelect"),

    userDataEl: document.getElementById("user-data"),

    btnLocal: document.getElementById("btnLocal"),
    btnSP: document.getElementById("btnSP"),

    localSection: document.getElementById("localSection"),
    spSection: document.getElementById("spSection"),

    fileInput: document.getElementById("fileInput"),
    runLocalBtn: document.getElementById("runLocalBtn"),
    runSPBtn: document.getElementById("runSPBtn"),
    cancelJobBtn: document.getElementById("cancelJobBtn"),

    continueStep1Btn: document.getElementById("continueStep1Btn"),
    continueStep2Btn: document.getElementById("continueStep2Btn"),

    localProfileSelect: document.getElementById("localProfileSelect"),
    sharepointProfileSelect: document.getElementById("sharepointProfileSelect"),

    clientSelect: document.getElementById("clientSelect"),
    clientMeta: document.getElementById("clientMeta"),

    sourceSiteSelect: document.getElementById("sourceSiteSelect"),
    destinationSiteSelect: document.getElementById("destinationSiteSelect"),

    pickSPFileBtn: document.getElementById("pickSPFileBtn"),
    pickSPFolderBtn: document.getElementById("pickSPFolderBtn"),

    selectedSourceLabel: document.getElementById("selectedSourceLabel"),
    selectedDestLabel: document.getElementById("selectedDestLabel"),

    statusBadge: document.getElementById("statusBadge"),
    progressLabel: document.getElementById("progressLabel"),
    progressPercent: document.getElementById("progressPercent"),
    progressFill: document.getElementById("progressFill"),
    stepsEl: document.getElementById("steps"),

    resultCard: document.getElementById("resultCard"),
    resultContent: document.getElementById("resultContent"),

    modalSiteSelect: document.getElementById("modalSiteSelect"),

    spModal: document.getElementById("spModal"),
    spModalBackdrop: document.getElementById("spModalBackdrop"),
    closeSPModalBtn: document.getElementById("closeSPModalBtn"),
    confirmSPSelectionBtn: document.getElementById("confirmSPSelectionBtn"),
    spModalBody: document.getElementById("spModalBody"),

    spModalTitle: document.getElementById("spModalTitle"),
    spCurrentPathLabel: document.getElementById("spCurrentPathLabel"),
    spBackBtn: document.getElementById("spBackBtn"),
    selectCurrentFolderBtn: document.getElementById("selectCurrentFolderBtn"),

    spPickedSourceInline: document.getElementById("spPickedSourceInline"),
    spPickedDestInline: document.getElementById("spPickedDestInline"),

    refreshHistoryBtn: document.getElementById("refreshHistoryBtn"),
    jobHistoryBody: document.getElementById("jobHistoryBody"),
    toggleHistoryBtn: document.getElementById("toggleHistoryBtn"),

    hotelLogoBtn: document.getElementById("hotelLogoBtn"),
    hotelLogoStatus: document.getElementById("hotelLogoStatus"),
    hotelLogoModal: document.getElementById("hotelLogoModal"),
    hotelLogoModalBackdrop: document.getElementById("hotelLogoModalBackdrop"),
    hotelLogoForm: document.getElementById("hotelLogoForm"),
    hotelNameInput: document.getElementById("hotelNameInput"),
    hotelLogoInput: document.getElementById("hotelLogoInput"),
    hotelNameDatalist: document.getElementById("hotelNameSuggestions"),
    closeHotelLogoModal: document.getElementById("closeHotelLogoModal"),
    hotelLogoPreviewWrap: document.getElementById("hotelLogoPreviewWrap"),
    hotelLogoPreviewImg: document.getElementById("hotelLogoPreviewImg"),
    hotelDuplicateHint: document.getElementById("hotelDuplicateHint"),
  };

  window.APP_DOM = dom;

  Object.entries(dom).forEach(([key, value]) => {
    window[key] = value;
  });
})();