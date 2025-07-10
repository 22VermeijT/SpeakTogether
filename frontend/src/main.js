/**
 * SpeakTogether - Main Electron Process
 * Handles desktop app window creation, system audio access, and backend communication
 */

const { app, BrowserWindow, ipcMain, systemPreferences, Menu, screen } = require('electron');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Development vs Production configuration
const isDev = process.env.NODE_ENV === 'development';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

class SpeakTogetherApp {
    constructor() {
        this.mainWindow = null;
        this.dashboardWindow = null;
        this.captionWindow = null;
        this.captionEnabled = false;
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
        
        // Caption overlay controls
        ipcMain.handle('toggle-caption-overlay', (event, enabled) => this.toggleCaptionOverlay(enabled));
        ipcMain.handle('update-caption-text', (event, data) => this.updateCaptionText(data));
        ipcMain.handle('is-caption-enabled', () => this.captionEnabled);
        
        // Debugging and testing controls
        ipcMain.handle('debug-caption-state', () => {
            const state = {
                captionEnabled: this.captionEnabled,
                windowExists: !!this.captionWindow,
                windowVisible: this.captionWindow ? this.captionWindow.isVisible() : false,
                windowBounds: this.captionWindow ? this.captionWindow.getBounds() : null,
                alwaysOnTop: this.captionWindow ? this.captionWindow.isAlwaysOnTop() : false,
                platform: process.platform,
                electronVersion: process.versions.electron
            };
            console.log('🔍 Debug caption state:', state);
            return state;
        });
        
        ipcMain.handle('force-show-caption-window', async () => {
            try {
                if (!this.captionWindow) {
                    await this.createCaptionWindow();
                }
                return this.showCaptionWindow();
            } catch (error) {
                console.error('❌ Force show failed:', error);
                return false;
            }
        });

        // Test function for caption data flow
        ipcMain.handle('test-caption-data', () => {
            console.log('🧪 Testing caption data flow...');
            const testData = {
                original: "Testing caption data flow from main process",
                translation: "Probando el flujo de datos de subtítulos desde el proceso principal",
                confidence: 0.95,
                sourceLanguage: "en",
                targetLanguage: "es",
                fromTranscription: true,
                isRealTime: true,
                timestamp: Date.now()
            };
            
            return this.updateCaptionText(testData);
        });
    }

    getAppIcon() {
        // Return platform-specific icon path
        const assetsPath = path.join(__dirname, '../assets');
        
        if (process.platform === 'darwin') {
            // Use ICNS format for macOS for better integration
            const icnsPath = path.join(assetsPath, 'icon.icns');
            try {
                if (require('fs').existsSync(icnsPath)) {
                    return icnsPath;
                }
            } catch (e) {
                console.warn('ICNS file not found, falling back to PNG');
            }
        }
        
        // Fallback to PNG for all platforms or if ICNS not found
        return path.join(assetsPath, 'icon.png');
    }

    async createMainWindow() {
        // Request audio permissions on macOS
        if (process.platform === 'darwin') {
            await this.requestAudioPermission();
        }

        // Create the main application window
        this.mainWindow = new BrowserWindow({
            width: 420,
            height: 650,
            minWidth: 350,
            minHeight: 500,
            maxWidth: 600,
            maxHeight: 1000,
            titleBarStyle: process.platform === 'darwin' ? 'default' : 'default',
            resizable: true,
            movable: true,
            minimizable: true,
            maximizable: true,
            closable: true,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            },
            icon: this.getAppIcon(),
            show: true // Show immediately to avoid timing issues
        });

        // Load the app
        if (isDev) {
            // Wait a moment for Vite server to be ready
            setTimeout(async () => {
                await this.mainWindow.loadURL('http://localhost:5173');
                this.mainWindow.webContents.openDevTools();
                this.mainWindow.focus();
            }, 1000);
        } else {
            await this.mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
        }

        // Window is already shown, just ensure it's focused when ready
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.focus();
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
            icon: this.getAppIcon(),
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

    async toggleCaptionOverlay(enabled) {
        console.log(`🎬 toggleCaptionOverlay called with enabled: ${enabled}`);
        console.log(`📊 Current state - window exists: ${!!this.captionWindow}, enabled: ${this.captionEnabled}, platform: ${process.platform}`);
        
        try {
            if (enabled) {
                if (!this.captionWindow) {
                    console.log('🎬 Creating new caption window...');
                    await this.createCaptionWindow();
                    console.log('🎬 Caption window creation completed');
                } else {
                    console.log('🎬 Caption window already exists, showing it...');
                    this.showCaptionWindow();
                }
            } else {
                if (this.captionWindow) {
                    console.log('🎬 Hiding caption window...');
                    this.hideCaptionWindow();
                    console.log('🎬 Caption window hidden');
                } else {
                    console.log('🎬 No caption window to hide');
                }
            }
            
            this.captionEnabled = enabled;
            
            // Final verification
            const finalState = {
                enabled: this.captionEnabled,
                windowExists: !!this.captionWindow,
                windowVisible: this.captionWindow ? this.captionWindow.isVisible() : false,
                alwaysOnTop: this.captionWindow ? this.captionWindow.isAlwaysOnTop() : false
            };
            
            console.log(`✅ Caption overlay toggle completed:`, finalState);
            return { success: true, enabled: this.captionEnabled, state: finalState };
            
        } catch (error) {
            console.error('❌ CRITICAL ERROR toggling caption overlay:', error);
            console.error('Stack trace:', error.stack);
            
            // Attempt emergency cleanup
            try {
                if (this.captionWindow) {
                    this.captionWindow.hide();
                }
            } catch (cleanupError) {
                console.error('Emergency cleanup failed:', cleanupError);
            }
            
            return { success: false, error: error.message, stack: error.stack };
        }
    }

    async createCaptionWindow() {
        if (this.captionWindow) {
            console.log('🎬 Caption window already exists, showing existing window');
            this.showCaptionWindow();
            return;
        }

        try {
            console.log('🎬 Creating new caption window with Electron best practices...');
            
            // Enhanced caption window configuration for better accessibility
            const screenBounds = screen.getPrimaryDisplay().workAreaSize;
            const windowWidth = 1000;  // Increased from 800
            const windowHeight = 200;  // Increased from 150
            
            this.captionWindow = new BrowserWindow({
                // Enhanced size and positioning
                width: windowWidth,
                height: windowHeight,
                minWidth: 600,           // Minimum resize limit
                minHeight: 120,          // Minimum resize limit  
                maxWidth: 1400,          // Maximum resize limit
                maxHeight: 400,          // Maximum resize limit
                
                // Position - larger window, still bottom-center
                x: Math.floor((screenBounds.width - windowWidth) / 2),
                y: screenBounds.height - windowHeight - 50, // 50px from bottom
                
                // Enable user interaction while maintaining overlay properties
                resizable: true,         // Allow resizing
                movable: true,           // Allow moving/dragging
                
                // Maintain overlay characteristics
                alwaysOnTop: true,
                frame: false,
                transparent: true,
                skipTaskbar: true,
                show: false,
                
                // Accessibility and interaction
                acceptFirstMouse: true,  // Allow interaction without focus
                enableLargerThanScreen: false,
                
                // Enhanced window properties
                webPreferences: {
                    nodeIntegration: false,
                    contextIsolation: true,
                    enableRemoteModule: false,
                    backgroundThrottling: false,  // Keep window active
                    preload: path.join(__dirname, isDev ? 'caption-preload.js' : '../src/caption-preload.js')
                }
            });

            console.log('🎬 BrowserWindow created, setting up event handlers...');

            // Platform-specific always-on-top configuration
            if (process.platform === 'darwin') {
                console.log('🍎 macOS: Setting screen-saver level for always-on-top');
                this.captionWindow.setAlwaysOnTop(true, 'screen-saver');
            } else if (process.platform === 'win32') {
                console.log('🪟 Windows: Setting always-on-top with proper level');
                this.captionWindow.setAlwaysOnTop(true, 'pop-up-menu');
            } else {
                console.log('🐧 Linux: Setting always-on-top');
                this.captionWindow.setAlwaysOnTop(true);
            }

            // Set up comprehensive event logging
            this.captionWindow.once('ready-to-show', () => {
                console.log('🎬 Caption window ready-to-show event fired');
                console.log('📊 Window bounds:', this.captionWindow.getBounds());
                console.log('👁️ Is visible:', this.captionWindow.isVisible());
                console.log('⬆️ Always on top:', this.captionWindow.isAlwaysOnTop());
                console.log('🖥️ Display info:', screen.getDisplayMatching(this.captionWindow.getBounds()));
                
                // Show the window now that it's ready
                this.showCaptionWindow();
            });

            this.captionWindow.on('show', () => {
                console.log('✅ Caption window SHOW event - window is now visible');
            });

            this.captionWindow.on('hide', () => {
                console.log('👻 Caption window HIDE event');
            });

            this.captionWindow.on('focus', () => {
                console.log('🎯 Caption window FOCUS event');
            });

            this.captionWindow.on('blur', () => {
                console.log('😴 Caption window BLUR event');
            });

            this.captionWindow.on('closed', () => {
                console.log('❌ Caption window CLOSED event');
                this.captionWindow = null;
                this.captionEnabled = false;
            });

            // Handle load completion with detailed logging
            this.captionWindow.webContents.once('did-finish-load', () => {
                console.log('📄 Caption window content finished loading');
                console.log('🌐 Current URL:', this.captionWindow.webContents.getURL());
            });

            // Handle load errors with detailed information
            this.captionWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
                console.error('❌ Caption window failed to load:');
                console.error('  Error code:', errorCode);
                console.error('  Description:', errorDescription);
                console.error('  URL:', validatedURL);
            });

            // Load caption HTML with proper error handling
            const captionUrl = isDev 
                ? 'http://localhost:5173/caption.html'
                : path.join(__dirname, '../dist/caption.html');
                
            console.log(`🌐 Loading caption URL: ${captionUrl}`);
            
            try {
                if (isDev) {
                    await this.captionWindow.loadURL('http://localhost:5173/caption.html');
                    console.log('📥 Development URL loaded successfully');
                } else {
                    await this.captionWindow.loadFile(path.join(__dirname, '../dist/caption.html'));
                    console.log('📄 Production file loaded successfully');
                }
            } catch (loadError) {
                console.error('❌ Failed to load caption HTML:', loadError);
                throw new Error(`Failed to load caption content: ${loadError.message}`);
            }

            console.log('✅ Caption window created and configured successfully');
            
        } catch (error) {
            console.error('❌ CRITICAL ERROR creating caption window:', error);
            console.error('Stack trace:', error.stack);
            
            // Cleanup on error
            if (this.captionWindow) {
                try {
                    this.captionWindow.close();
                } catch (closeError) {
                    console.error('Error closing failed window:', closeError);
                }
                this.captionWindow = null;
            }
            
            throw error;
        }
    }

    showCaptionWindow() {
        if (!this.captionWindow) {
            console.error('❌ Cannot show caption window - window does not exist');
            return false;
        }

        try {
            console.log('👁️ Showing caption window...');
            console.log('📊 Pre-show bounds:', this.captionWindow.getBounds());
            console.log('👁️ Pre-show visible:', this.captionWindow.isVisible());
            
            // Force window to front and show
            this.captionWindow.show();
            this.captionWindow.focus();
            this.captionWindow.setAlwaysOnTop(true);
            
            // Platform-specific window management
            if (process.platform === 'darwin') {
                this.captionWindow.setAlwaysOnTop(true, 'screen-saver');
            }
            
            console.log('📊 Post-show bounds:', this.captionWindow.getBounds());
            console.log('👁️ Post-show visible:', this.captionWindow.isVisible());
            console.log('⬆️ Post-show always-on-top:', this.captionWindow.isAlwaysOnTop());
            
            return true;
        } catch (error) {
            console.error('❌ Error showing caption window:', error);
            return false;
        }
    }

    hideCaptionWindow() {
        if (!this.captionWindow) {
            console.log('👻 No caption window to hide');
            return false;
        }

        try {
            console.log('👻 Hiding caption window...');
            console.log('📊 Pre-hide bounds:', this.captionWindow.getBounds());
            console.log('👁️ Pre-hide visible:', this.captionWindow.isVisible());
            
            this.captionWindow.hide();
            
            console.log('👁️ Post-hide visible:', this.captionWindow.isVisible());
            console.log('✅ Caption window hidden successfully');
            return true;
        } catch (error) {
            console.error('❌ Error hiding caption window:', error);
            return false;
        }
    }

    destroyCaptionWindow() {
        console.log('🎬 destroyCaptionWindow called');
        try {
            if (this.captionWindow) {
                console.log('🎬 Closing caption window...');
                console.log('📊 Final window bounds:', this.captionWindow.getBounds());
                console.log('👁️ Final visible state:', this.captionWindow.isVisible());
                
                // First hide, then close to ensure clean shutdown
                this.captionWindow.hide();
                this.captionWindow.close();
                this.captionWindow = null;
                console.log('🎬 Caption window closed and reference cleared');
            } else {
                console.log('🎬 No caption window to destroy');
            }
            this.captionEnabled = false;
            console.log('✅ Caption window destroyed successfully');
        } catch (error) {
            console.error('❌ Error destroying caption window:', error);
            console.error('Error details:', error.stack);
            // Force cleanup even if there was an error
            this.captionWindow = null;
            this.captionEnabled = false;
        }
    }

    updateCaptionText(data) {
        console.log('📝 Updating caption with enhanced bilingual data:', data);
        
        // ENHANCED DEBUGGING: Log detailed translation processing
        console.log('🔍 MAIN PROCESS TRANSLATION DEBUG:', {
            'raw_data': data,
            'data.translation': data.translation,
            'data.translated': data.translated,
            'translation_length': (data.translation || '').length,
            'translated_length': (data.translated || '').length,
            'translation_truthy': !!data.translation,
            'translated_truthy': !!data.translated
        });
        
        if (!this.captionWindow || this.captionWindow.isDestroyed()) {
            console.log('👻 No caption window to update');
            return;
        }

        try {
            // Enhanced data processing for bilingual display
            const bilingual_data = {
                // Original text (primary source)
                original: data.original || data.text || '',
                
                // Translation (if available)
                translation: data.translation || data.translated || '',
                
                // Confidence and metadata
                confidence: typeof data.confidence === 'number' ? data.confidence : 0,
                sourceLanguage: data.sourceLanguage || data.source_language || 'auto',
                targetLanguage: data.targetLanguage || data.target_language || 'en',
                
                // Real-time indicators
                fromTranscription: data.fromTranscription || true,
                isRealTime: data.isRealTime || true,
                timestamp: Date.now()
            };
            
            console.log('📡 Sending enhanced bilingual caption data:', bilingual_data);
            console.log('🔍 FINAL TRANSLATION CHECK:', {
                'final_translation': bilingual_data.translation,
                'final_translation_length': bilingual_data.translation.length,
                'final_translation_truthy': !!bilingual_data.translation
            });
            
            // Send to caption window via IPC
            this.captionWindow.webContents.send('update-live-caption', bilingual_data);
            
            console.log('✅ Bilingual caption data sent successfully');
            
        } catch (error) {
            console.error('❌ Error updating caption text:', error);
        }
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