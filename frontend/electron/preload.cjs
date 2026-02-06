const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  // Add IPC methods here
  ping: () => ipcRenderer.invoke('ping'),
});
