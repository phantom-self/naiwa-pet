const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('naiwa', {
  onLedger: (cb) => ipcRenderer.on('ledger', (_e, data) => cb(data)),
  refresh: () => ipcRenderer.invoke('refresh'),
})
