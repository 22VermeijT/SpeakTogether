/**
 * SpeakTogether - Enhanced Bilingual Caption Renderer
 * Handles real-time bilingual caption display with enhanced UX
 */

console.log('🎨 Enhanced Bilingual Caption Renderer Loading...');

class EnhancedBilingualCaptionRenderer {
    constructor() {
        console.log('🎬 Initializing Enhanced Bilingual Caption Renderer');
        
        // DOM elements
        this.originalElement = document.getElementById('original-text');
        this.translatedElement = document.getElementById('translated-text');
        this.chevronElement = document.getElementById('chevron');
        this.confidenceElement = document.getElementById('confidence-dot');
        this.sourceLangElement = document.getElementById('source-lang');
        this.targetLangElement = document.getElementById('target-lang');
        
        // State tracking
        this.currentState = {
            hasOriginal: false,
            hasTranslation: false,
            confidence: 0,
            lastUpdate: 0
        };
        
        this.initializeRenderer();
    }

    initializeRenderer() {
        console.log('🔗 Setting up enhanced bilingual caption listener');
        
        // Connect with captionAPI from preload script
        if (window.captionAPI) {
            console.log('✅ captionAPI available, setting up bilingual listener');
            window.captionAPI.onCaptionUpdate((data) => {
                console.log('📥 Enhanced bilingual caption data received:', data);
                this.updateBilingualDisplay(data);
            });
        } else {
            console.warn('⚠️ captionAPI not available, setting up fallback');
            this.setupFallbackListener();
        }
        
        // Global function for direct updates (backup method)
        window.updateBilingualCaption = (data) => {
            console.log('📝 Direct bilingual caption update:', data);
            this.updateBilingualDisplay(data);
        };
        
        // Initialize visual state
        this.updateChevronState();
        
        console.log('✅ Enhanced bilingual caption renderer initialized');
    }

    setupFallbackListener() {
        console.log('🔄 Setting up fallback listener for enhanced captions');
        
        // Listen for Electron IPC messages directly
        if (window.electronAPI) {
            // Fallback method
            console.log('📡 Using electronAPI fallback for caption updates');
        } else {
            console.log('🌐 Browser mode - enhanced captions ready for testing');
        }
    }

    updateBilingualDisplay(data) {
        try {
            console.log('🎨 Updating enhanced bilingual display:', data);
            
            // Throttle updates to prevent excessive rendering
            const now = Date.now();
            if (now - this.currentState.lastUpdate < 100) {
                console.log('⏱️ Throttling update - too frequent');
                return;
            }
            this.currentState.lastUpdate = now;
            
            // Update original text with enhanced styling
            this.updateOriginalText(data);
            
            // Update translated text with proper handling
            this.updateTranslatedText(data);
            
            // Update confidence indicator
            this.updateConfidenceIndicator(data.confidence);
            
            // Update language tags
            this.updateLanguageTags(data.sourceLanguage, data.targetLanguage);
            
            // Update chevron state based on content
            this.updateChevronState();
            
            // Visual feedback for real-time updates
            this.showUpdateFeedback();
            
            console.log('✅ Enhanced bilingual display updated successfully');
            
        } catch (error) {
            console.error('❌ Error updating enhanced bilingual display:', error);
        }
    }

    updateOriginalText(data) {
        if (!this.originalElement) return;
        
        if (data.original && data.original.trim()) {
            this.originalElement.textContent = data.original;
            this.originalElement.classList.remove('placeholder-text');
            this.currentState.hasOriginal = true;
            
            // Apply confidence-based opacity
            if (typeof data.confidence === 'number') {
                const opacity = Math.max(0.7, data.confidence);
                this.originalElement.style.opacity = opacity;
            }
            
            console.log('📝 Original text updated:', data.original.substring(0, 50) + '...');
        } else {
            this.originalElement.textContent = 'Ready for live captions...';
            this.originalElement.classList.add('placeholder-text');
            this.currentState.hasOriginal = false;
        }
    }

    updateTranslatedText(data) {
        if (!this.translatedElement) return;
        
        if (data.translation && data.translation.trim() && data.translation !== data.original) {
            this.translatedElement.textContent = data.translation;
            this.translatedElement.classList.remove('placeholder-text');
            this.currentState.hasTranslation = true;
            
            console.log('🌐 Translation updated:', data.translation.substring(0, 50) + '...');
        } else if (data.original && data.original.trim()) {
            // Show "Translating..." when we have original but no translation
            this.translatedElement.textContent = 'Translating...';
            this.translatedElement.classList.add('placeholder-text');
            this.currentState.hasTranslation = false;
        } else {
            this.translatedElement.textContent = 'Translation will appear here...';
            this.translatedElement.classList.add('placeholder-text');
            this.currentState.hasTranslation = false;
        }
    }

    updateConfidenceIndicator(confidence) {
        if (!this.confidenceElement) return;
        
        this.currentState.confidence = confidence || 0;
        
        // Update confidence visual indicator
        if (confidence >= 0.8) {
            this.confidenceElement.className = 'confidence-indicator';
        } else if (confidence >= 0.6) {
            this.confidenceElement.className = 'confidence-indicator low';
        } else {
            this.confidenceElement.className = 'confidence-indicator very-low';
        }
        
        console.log(`📊 Confidence updated: ${(confidence * 100).toFixed(1)}%`);
    }

    updateLanguageTags(sourceLanguage, targetLanguage) {
        if (this.sourceLangElement && sourceLanguage) {
            const sourceLang = sourceLanguage.toUpperCase().substring(0, 3);
            this.sourceLangElement.textContent = sourceLang;
        }
        
        if (this.targetLangElement && targetLanguage) {
            const targetLang = targetLanguage.toUpperCase().substring(0, 3);
            this.targetLangElement.textContent = targetLang;
        }
    }

    updateChevronState() {
        if (!this.chevronElement) return;
        
        if (this.currentState.hasOriginal && this.currentState.hasTranslation) {
            this.chevronElement.classList.add('active');
            this.chevronElement.style.opacity = '1.0';
        } else if (this.currentState.hasOriginal) {
            this.chevronElement.classList.remove('active');
            this.chevronElement.style.opacity = '0.4';
        } else {
            this.chevronElement.classList.remove('active');
            this.chevronElement.style.opacity = '0.8';
        }
    }

    showUpdateFeedback() {
        // Brief visual feedback for updates
        const container = document.querySelector('.caption-container');
        if (container) {
            container.style.transform = 'scale(1.02)';
            setTimeout(() => {
                container.style.transform = 'scale(1.0)';
            }, 150);
        }
    }

    // Debug methods
    debugState() {
        console.log('🔍 Enhanced Bilingual Caption Renderer State:');
        console.log('  Elements:', {
            original: !!this.originalElement,
            translated: !!this.translatedElement,
            chevron: !!this.chevronElement,
            confidence: !!this.confidenceElement,
            sourceLang: !!this.sourceLangElement,
            targetLang: !!this.targetLangElement
        });
        console.log('  State:', this.currentState);
        console.log('  APIs:', {
            captionAPI: !!window.captionAPI,
            electronAPI: !!window.electronAPI,
            updateBilingualCaption: !!window.updateBilingualCaption
        });
    }

    // Test method for manual testing
    testBilingualDisplay() {
        console.log('🧪 Testing enhanced bilingual display...');
        
        const testData = {
            original: "This is a test of the enhanced bilingual caption system with larger size and better accessibility!",
            translation: "¡Esta es una prueba del sistema de subtítulos bilingües mejorado con mayor tamaño y mejor accesibilidad!",
            confidence: 0.93,
            sourceLanguage: "en",
            targetLanguage: "es",
            fromTranscription: true,
            isRealTime: true,
            timestamp: Date.now()
        };
        
        this.updateBilingualDisplay(testData);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM ready, initializing Enhanced Bilingual Caption Renderer');
    
    try {
        window.bilingualRenderer = new EnhancedBilingualCaptionRenderer();
        
        // Make debug methods available
        window.debugCaptions = () => window.bilingualRenderer.debugState();
        window.testCaptions = () => window.bilingualRenderer.testBilingualDisplay();
        
        console.log('✅ Enhanced Bilingual Caption Renderer ready');
        console.log('🎯 Debug commands: debugCaptions(), testCaptions()');
        
    } catch (error) {
        console.error('❌ Failed to initialize Enhanced Bilingual Caption Renderer:', error);
    }
});

// Fallback initialization
if (document.readyState === 'loading') {
    console.log('📄 Waiting for DOM to load...');
} else {
    console.log('📄 DOM already ready, initializing immediately');
    if (!window.bilingualRenderer) {
        window.bilingualRenderer = new EnhancedBilingualCaptionRenderer();
    }
}

console.log('🎬 Enhanced Bilingual Caption Renderer script loaded'); 