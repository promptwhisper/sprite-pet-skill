const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktopPet', {
  onState: (callback) => ipcRenderer.on('pet-state', (_event, state) => callback(state)),
  onCaught: (callback) => ipcRenderer.on('cursor-caught', callback),
  showMenu: () => ipcRenderer.send('show-pet-menu'),
  quit: () => ipcRenderer.send('quit-pet'),
});
