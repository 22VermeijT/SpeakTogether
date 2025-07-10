/**
 * SpeakTogether - Caption Window Preload Script
 * Safely exposes IPC APIs for the floating caption overlay
 */

const { contextBridge, ipcRenderer } = require('electron');

console.log('🎬 Caption preload script loading...');

// Enhanced bilingual caption API
const captionAPI = {
    // Listen for live caption updates with bilingual support
    onCaptionUpdate: (callback) => {
        console.log('🔗 Setting up enhanced bilingual caption update listener');
        ipcRenderer.on('update-live-caption', (event, data) => {
            console.log('📥 Bilingual caption data received in preload:', data);
            
            // Enhanced data validation and processing
            const processedData = {
                original: data.original || data.text || '',
                translation: data.translation || '',
                confidence: typeof data.confidence === 'number' ? data.confidence : 0,
                sourceLanguage: data.sourceLanguage || 'auto',
                targetLanguage: data.targetLanguage || 'en',
                timestamp: data.timestamp || Date.now(),
                fromTranscription: data.fromTranscription || false,
                isRealTime: data.isRealTime || false
            };
            
            console.log('✅ Processed bilingual data:', processedData);
            
            // Call the renderer callback
            if (typeof callback === 'function') {
                callback(processedData);
            }
            
            // Note: Removed direct window.updateBilingualCaption call to avoid race conditions
            // The HTML renderer now properly sets up the callback via onCaptionUpdate
        });
    },
    
    // Send caption control commands to main process
    sendCaptionCommand: (command, data) => {
        console.log('📤 Sending caption command:', command, data);
        ipcRenderer.send('caption-command', { command, data });
    },
    
    // Request current caption status
    getCaptionStatus: () => {
        console.log('📊 Requesting caption status');
        return ipcRenderer.invoke('get-caption-status');
    }
};

// Expose the enhanced API to the renderer
contextBridge.exposeInMainWorld('captionAPI', captionAPI);

console.log('✅ Enhanced bilingual caption preload script loaded successfully');
console.log('🔗 Available API methods:', Object.keys(captionAPI));

// Additional debugging for renderer context
window.addEventListener('DOMContentLoaded', () => {
    console.log('📄 Caption window DOM loaded');
    console.log('🌐 Window location:', window.location.href);
    console.log('🔍 captionAPI exposed:', !!window.captionAPI);
    
    // Test API availability
    if (window.captionAPI) {
        console.log('✅ captionAPI is available in renderer');
        console.log('🎯 Available methods:', Object.keys(window.captionAPI));
    } else {
        console.error('❌ captionAPI is NOT available in renderer');
    }
});

// Handle any preload errors
process.on('uncaughtException', (error) => {
    console.error('❌ Caption preload uncaught exception:', error);
});

window.addEventListener('error', (event) => {
    console.error('❌ Caption window error:', event.error);
});

console.log('🎬 Caption preload script initialization complete'); 