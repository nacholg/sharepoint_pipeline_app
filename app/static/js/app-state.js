(function () {
  const state = {
    auth: {
      authenticated: false,
      user: null,
      reason: null,
      sessionExpiredAlertShown: false,
    },

    wizard: {
      step1Confirmed: false,
      step2Confirmed: false,
    },

    data: {
      sharepointSites: [],
      availableProfiles: [],
      availableClients: [],
      selectedClient: null,
    },
    

    sharepoint: {
      selectedSourceFileId: null,
      selectedSourceFileName: null,
      selectedSourceSiteKey: null,

      selectedDestinationFolderId: null,
      selectedDestinationFolderName: null,
      selectedDestinationSiteKey: null,

      currentSharePointFolderId: null,
      currentSharePointFolderName: null,
      currentModalSiteKey: null,
      spBrowseMode: "source",
      spFolderStack: [],
    },

    jobs: {
      activeJobPollTimer: null,
      activeJobId: null,
      currentRunningJobId: null,
    },

    ui: {
      pipelineExecutionLocked: false,
    },
  };

  window.APP_STATE = state;

  function proxy(windowKey, getter, setter) {
    Object.defineProperty(window, windowKey, {
      configurable: true,
      enumerable: true,
      get: getter,
      set: setter,
    });
  }

  proxy(
    "sharepointSites",
    () => state.data.sharepointSites,
    (v) => { state.data.sharepointSites = Array.isArray(v) ? v : []; }
  );

  proxy(
    "step1Confirmed",
    () => state.wizard.step1Confirmed,
    (v) => { state.wizard.step1Confirmed = !!v; }
  );

  proxy(
    "step2Confirmed",
    () => state.wizard.step2Confirmed,
    (v) => { state.wizard.step2Confirmed = !!v; }
  );
  proxy(
    "availableProfiles",
    () => state.data.availableProfiles,
    (v) => { state.data.availableProfiles = Array.isArray(v) ? v : []; }
  );

  proxy(
    "availableClients",
    () => state.data.availableClients,
    (v) => { state.data.availableClients = Array.isArray(v) ? v : []; }
  );

  proxy(
    "selectedClient",
    () => state.data.selectedClient,
    (v) => { state.data.selectedClient = v; }
  );

  proxy(
    "selectedSourceFileId",
    () => state.sharepoint.selectedSourceFileId,
    (v) => { state.sharepoint.selectedSourceFileId = v; }
  );

  proxy(
    "selectedSourceFileName",
    () => state.sharepoint.selectedSourceFileName,
    (v) => { state.sharepoint.selectedSourceFileName = v; }
  );

  proxy(
    "selectedSourceSiteKey",
    () => state.sharepoint.selectedSourceSiteKey,
    (v) => { state.sharepoint.selectedSourceSiteKey = v; }
  );

  proxy(
    "selectedDestinationFolderId",
    () => state.sharepoint.selectedDestinationFolderId,
    (v) => { state.sharepoint.selectedDestinationFolderId = v; }
  );

  proxy(
    "selectedDestinationFolderName",
    () => state.sharepoint.selectedDestinationFolderName,
    (v) => { state.sharepoint.selectedDestinationFolderName = v; }
  );

  proxy(
    "selectedDestinationSiteKey",
    () => state.sharepoint.selectedDestinationSiteKey,
    (v) => { state.sharepoint.selectedDestinationSiteKey = v; }
  );

  proxy(
    "currentSharePointFolderId",
    () => state.sharepoint.currentSharePointFolderId,
    (v) => { state.sharepoint.currentSharePointFolderId = v; }
  );

  proxy(
    "currentSharePointFolderName",
    () => state.sharepoint.currentSharePointFolderName,
    (v) => { state.sharepoint.currentSharePointFolderName = v; }
  );

  proxy(
    "currentModalSiteKey",
    () => state.sharepoint.currentModalSiteKey,
    (v) => { state.sharepoint.currentModalSiteKey = v; }
  );

  proxy(
    "spBrowseMode",
    () => state.sharepoint.spBrowseMode,
    (v) => { state.sharepoint.spBrowseMode = v || "source"; }
  );

  proxy(
    "spFolderStack",
    () => state.sharepoint.spFolderStack,
    (v) => { state.sharepoint.spFolderStack = Array.isArray(v) ? v : []; }
  );

  proxy(
    "activeJobPollTimer",
    () => state.jobs.activeJobPollTimer,
    (v) => { state.jobs.activeJobPollTimer = v; }
  );

  proxy(
    "activeJobId",
    () => state.jobs.activeJobId,
    (v) => { state.jobs.activeJobId = v; }
  );

  proxy(
    "authState",
    () => state.auth,
    (v) => {
      state.auth = {
        authenticated: !!v?.authenticated,
        user: v?.user || null,
        reason: v?.reason || null,
        sessionExpiredAlertShown: !!v?.sessionExpiredAlertShown,
      };
    }
  );

  proxy(
    "sessionExpiredAlertShown",
    () => state.auth.sessionExpiredAlertShown,
    (v) => { state.auth.sessionExpiredAlertShown = !!v; }
  );

  proxy(
    "currentRunningJobId",
    () => state.jobs.currentRunningJobId,
    (v) => { state.jobs.currentRunningJobId = v; }
  );

  proxy(
    "pipelineExecutionLocked",
    () => state.ui.pipelineExecutionLocked,
    (v) => { state.ui.pipelineExecutionLocked = !!v; }
  );

  Object.defineProperty(window, "currentRunningJobId", {
    configurable: true,
    enumerable: true,
    get() {
      return state.jobs.currentRunningJobId;
    },
    set(value) {
      state.jobs.currentRunningJobId = value;
    },
  });

  Object.defineProperty(window, "pipelineExecutionLocked", {
    configurable: true,
    enumerable: true,
    get() {
      return state.ui.pipelineExecutionLocked;
    },
    set(value) {
      state.ui.pipelineExecutionLocked = !!value;
    },
  });
})();