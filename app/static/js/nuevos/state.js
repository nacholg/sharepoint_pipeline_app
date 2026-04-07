export const state = {
  auth: {
    authenticated: false,
    user: null,
    reason: null,
    sessionExpiredAlertShown: false,
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

    currentFolderId: null,
    currentFolderName: null,
    currentModalSiteKey: null,
    browseMode: "source",
    folderStack: [],
  },

  jobs: {
    activeJobPollTimer: null,
    activeJobId: null,
  },

  ui: {
    pipelineExecutionLocked: false,
  },
};