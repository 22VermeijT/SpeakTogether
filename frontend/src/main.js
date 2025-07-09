/**
 * SpeakTogether - Main Electron Process
 * Handles desktop app window creation, system audio access, and backend communication
 */

const { app, BrowserWindow, ipcMain, systemPreferences, Menu } = require('electron');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Development vs Production configuration
const isDev = process.env.NODE_ENV === 'development';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

class SpeakTogetherApp {
    constructor() {
        this.mainWindow = null;
        this.dashboardWindow = null;
        this.sessionId = uuidv4();
        this.audioPermissionGranted = false;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        // App event listeners
        app.whenReady().then(() => this.createMainWindow());
        app.on('window-all-closed', () => this.handleAllWindowsClosed());
        app.on('activate', () => this.handleActivate());

        // IPC event listeners
        ipcMain.handle('get-session-id', () => this.sessionId);
        ipcMain.handle('request-audio-permission', () => this.requestAudioPermission());
        ipcMain.handle('get-backend-url', () => BACKEND_URL);
        ipcMain.handle('open-dashboard', () => this.openAgentDashboard());
        ipcMain.handle('get-app-info', () => this.getAppInfo());
        ipcMain.handle('minimize-to-tray', () => this.minimizeToTray());
    }

    async createMainWindow() {
        // Request audio permissions on macOS
        if (process.platform === 'darwin') {
            await this.requestAudioPermission();
        }

        // Create the main application window
        this.mainWindow = new BrowserWindow({
            width: 1200,
            height: 800,
            minWidth: 800,
            minHeight: 600,
            titleBarStyle: 'hiddenInset',
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            },
            icon: path.join(__dirname, '../assets/icon.png'),
            show: false // Don't show until ready
        });

        // Load the app
        if (isDev) {
            await this.mainWindow.loadURL('http://localhost:5173');
            this.mainWindow.webContents.openDevTools();
        } else {
            await this.mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
        }

        // Show window when ready
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.show();
            
            // Focus the window on creation
            if (isDev) {
                this.mainWindow.focus();
            }
        });

        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        // Set up the application menu
        this.createApplicationMenu();

        console.log('SpeakTogether main window created');
    }

    async openAgentDashboard() {
        if (this.dashboardWindow) {
            this.dashboardWindow.focus();
            return;
        }

        this.dashboardWindow = new BrowserWindow({
            width: 1000,
            height: 700,
            minWidth: 600,
            minHeight: 400,
            parent: this.mainWindow,
            titleBarStyle: 'hiddenInset',
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            },
            title: 'Agent Dashboard - SpeakTogether'
        });

        // Load dashboard page
        if (isDev) {
            await this.dashboardWindow.loadURL('http://localhost:5173/dashboard.html');
        } else {
            await this.dashboardWindow.loadFile(path.join(__dirname, '../dist/dashboard.html'));
        }

        this.dashboardWindow.on('closed', () => {
            this.dashboardWindow = null;
        });

        console.log('Agent dashboard window opened');
    }

    async requestAudioPermission() {
        try {
            if (process.platform === 'darwin') {
                // Request microphone access on macOS
                const microphoneAccess = await systemPreferences.askForMediaAccess('microphone');
                
                // In production, you'd also request system audio access
                // This requires additional setup and possibly elevated permissions
                
                this.audioPermissionGranted = microphoneAccess;
                
                console.log('Audio permission granted:', microphoneAccess);
                return { granted: microphoneAccess, type: 'microphone' };
            } else {
                // On Windows/Linux, assume permission is available
                this.audioPermissionGranted = true;
                return { granted: true, type: 'system' };
            }
        } catch (error) {
            console.error('Error requesting audio permission:', error);
            return { granted: false, error: error.message };
        }
    }

    createApplicationMenu() {
        const template = [
            {
                label: 'SpeakTogether',
                submenu: [
                    { role: 'about' },
                    { type: 'separator' },
                    {
                        label: 'Preferences...',
                        accelerator: 'CmdOrCtrl+,',
                        click: () => {
                            // Open preferences window
                            this.mainWindow?.webContents.send('open-preferences');
                        }
                    },
                    { type: 'separator' },
                    { role: 'hide' },
                    { role: 'hideothers' },
                    { role: 'unhide' },
                    { type: 'separator' },
                    { role: 'quit' }
                ]
            },
            {
                label: 'View',
                submenu: [
                    { role: 'reload' },
                    { role: 'forceReload' },
                    { role: 'toggleDevTools' },
                    { type: 'separator' },
                    {
                        label: 'Agent Dashboard',
                        accelerator: 'CmdOrCtrl+D',
                        click: () => this.openAgentDashboard()
                    },
                    { type: 'separator' },
                    { role: 'resetZoom' },
                    { role: 'zoomIn' },
                    { role: 'zoomOut' },
                    { type: 'separator' },
                    { role: 'togglefullscreen' }
                ]
            },
            {
                label: 'Audio',
                submenu: [
                    {
                        label: 'Start Listening',
                        accelerator: 'CmdOrCtrl+L',
                        click: () => {
                            this.mainWindow?.webContents.send('start-audio-capture');
                        }
                    },
                    {
                        label: 'Stop Listening', 
                        accelerator: 'CmdOrCtrl+S',
                        click: () => {
                            this.mainWindow?.webContents.send('stop-audio-capture');
                        }
                    },
                    { type: 'separator' },
                    {
                        label: 'Upload Audio File...',
                        accelerator: 'CmdOrCtrl+O',
                        click: () => {
                            this.mainWindow?.webContents.send('upload-audio-file');
                        }
                    }
                ]
            },
            {
                label: 'Window',
                submenu: [
                    { role: 'minimize' },
                    { role: 'close' },
                    { type: 'separator' },
                    {
                        label: 'Always on Top',
                        type: 'checkbox',
                        click: (menuItem) => {
                            this.mainWindow?.setAlwaysOnTop(menuItem.checked);
                        }
                    }
                ]
            },
            {
                label: 'Help',
                submenu: [
                    {
                        label: 'About SpeakTogether',
                        click: () => {
                            this.mainWindow?.webContents.send('show-about');
                        }
                    },
                    {
                        label: 'Learn More',
                        click: async () => {
                            const { shell } = require('electron');
                            await shell.openExternal('https://github.com/speaktogether/app');
                        }
                    }
                ]
            }
        ];

        const menu = Menu.buildFromTemplate(template);
        Menu.setApplicationMenu(menu);
    }

    getAppInfo() {
        return {
            name: 'SpeakTogether',
            version: app.getVersion(),
            electronVersion: process.versions.electron,
            nodeVersion: process.versions.node,
            platform: process.platform,
            arch: process.arch,
            sessionId: this.sessionId,
            audioPermissionGranted: this.audioPermissionGranted,
            backendUrl: BACKEND_URL
        };
    }

    minimizeToTray() {
        if (this.mainWindow) {
            this.mainWindow.hide();
        }
        
        // In production, you'd create a system tray icon here
        console.log('App minimized to tray');
    }

    handleAllWindowsClosed() {
        // On macOS, keep the app running even when all windows are closed
        if (process.platform !== 'darwin') {
            app.quit();
        }
    }

    handleActivate() {
        // On macOS, re-create the window when the app is activated
        if (BrowserWindow.getAllWindows().length === 0) {
            this.createMainWindow();
        }
    }
}

// Create and start the application
const speakTogetherApp = new SpeakTogetherApp();

// Handle app events
app.on('before-quit', () => {
    console.log('SpeakTogether is shutting down...');
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
    contents.on('new-window', (event, navigationUrl) => {
        event.preventDefault();
        console.log('Blocked new window creation to:', navigationUrl);
    });
});

console.log('SpeakTogether Electron app starting...'); 