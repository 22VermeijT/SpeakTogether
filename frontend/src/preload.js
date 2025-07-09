/**
 * SpeakTogether - Preload Script
 * Safely exposes main process APIs to the renderer process
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose APIs to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    // App information
    getSessionId: () => ipcRenderer.invoke('get-session-id'),
    getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
    getAppInfo: () => ipcRenderer.invoke('get-app-info'),

    // Audio permissions
    requestAudioPermission: () => ipcRenderer.invoke('request-audio-permission'),

    // Window management
    openDashboard: () => ipcRenderer.invoke('open-dashboard'),
    minimizeToTray: () => ipcRenderer.invoke('minimize-to-tray'),

    // IPC listeners for menu actions
    onStartAudioCapture: (callback) => {
        ipcRenderer.on('start-audio-capture', callback);
        return () => ipcRenderer.removeListener('start-audio-capture', callback);
    },

    onStopAudioCapture: (callback) => {
        ipcRenderer.on('stop-audio-capture', callback);
        return () => ipcRenderer.removeListener('stop-audio-capture', callback);
    },

    onUploadAudioFile: (callback) => {
        ipcRenderer.on('upload-audio-file', callback);
        return () => ipcRenderer.removeListener('upload-audio-file', callback);
    },

    onOpenPreferences: (callback) => {
        ipcRenderer.on('open-preferences', callback);
        return () => ipcRenderer.removeListener('open-preferences', callback);
    },

    onShowAbout: (callback) => {
        ipcRenderer.on('show-about', callback);
        return () => ipcRenderer.removeListener('show-about', callback);
    }
});

console.log('SpeakTogether preload script loaded'); 