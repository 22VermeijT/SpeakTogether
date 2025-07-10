"""
Audio Stream Handler for SpeakTogether
Manages PyAudio capture sessions and WebSocket integration with Speech-to-Text
"""

import asyncio
import json
import time
import os
import base64
import requests
from typing import Dict, Optional, Any, Union, Callable, Awaitable
import structlog
import threading

from .capture import PyAudioCapture
from ..google_cloud_client import GoogleCloudClient
from ..agents.translation_polisher_agent_multilingual import TranslationPolisherAgentMultilingual

logger = structlog.get_logger()


class AudioStreamHandler:
    """
    Manages audio capture sessions for WebSocket clients
    Integrates PyAudio capture with real-time streaming and Speech-to-Text
    """
    
    def __init__(self):
        """Initialize the audio stream handler"""
        self.active_captures: Dict[str, PyAudioCapture] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        self.google_client: Optional[GoogleCloudClient] = None
        self.use_rest_api = False
        self.api_key = None
        self.audio_buffers: Dict[str, bytes] = {}
        self.buffer_durations: Dict[str, float] = {}
        self.silence_buffers: Dict[str, float] = {}  # Track silence duration
        self.last_speech_time: Dict[str, float] = {}  # Track last speech activity
        
        # Enhanced buffer configuration for longer speech recognition
        # Load from config if available, otherwise use defaults
        try:
            from ..config import settings  # Use the global settings instance with error handling
            self.target_buffer_duration = settings.SPEECH_BUFFER_TARGET_DURATION
            self.max_buffer_duration = settings.SPEECH_BUFFER_MAX_DURATION
            self.min_buffer_duration = settings.SPEECH_BUFFER_MIN_DURATION
            self.silence_threshold = settings.SPEECH_SILENCE_THRESHOLD
            self.volume_threshold = settings.SPEECH_VOLUME_THRESHOLD
            logger.info("✅ Using speech recognition settings from config")
        except Exception as e:
            # PROPER fallback defaults that match config.py values
            self.target_buffer_duration = 5.0   # Target buffer duration for processing
            self.max_buffer_duration = 15.0     # Maximum buffer duration before forced processing
            self.min_buffer_duration = 2.0      # Minimum buffer duration before processing
            self.silence_threshold = 1.5        # Seconds of silence before processing
            self.volume_threshold = 20.0        # Minimum volume percentage to consider as speech
            logger.warning(f"⚠️ Failed to load config, using fallback defaults: {e}")
        
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'total_audio_bytes': 0,
            'total_chunks_processed': 0,
            'total_transcriptions': 0,
            'successful_transcriptions': 0,
            'sentences_detected': 0,
            'silence_breaks': 0
        }
        self._main_loop = None
        
        # Language code mapping for Google Cloud Speech-to-Text
        self._language_code_map = self._create_language_code_map()
        
        # Initialize Speech-to-Text client
        self._initialize_speech_client()
        
        # Initialize Translation Polisher Agent
        self.translation_polisher = TranslationPolisherAgentMultilingual()
        self._polisher_initialized = False
        
        # Initialize polisher immediately (don't wait)
        import asyncio
        try:
            # Create a task to initialize the polisher early
            asyncio.create_task(self._initialize_polisher_early())
        except Exception as e:
            logger.warning(f"Failed to create polisher initialization task: {e}")
        
        logger.info("Audio stream handler initialized with enhanced Speech-to-Text support", 
                   target_duration=self.target_buffer_duration,
                   max_duration=self.max_buffer_duration,
                   min_duration=self.min_buffer_duration,
                   silence_threshold=self.silence_threshold,
                   volume_threshold=self.volume_threshold)
    
    async def _ensure_polisher_initialized(self):
        """Ensure the translation polisher is initialized"""
        if not self._polisher_initialized:
            try:
                await self.translation_polisher.initialize()
                self._polisher_initialized = True
                logger.info("Translation polisher initialized successfully")
            except Exception as e:
                logger.warning(f"Translation polisher initialization failed: {e}")
                self._polisher_initialized = False
    
    def update_speech_settings(self, **kwargs):
        """Update speech recognition settings dynamically"""
        if 'target_buffer_duration' in kwargs:
            self.target_buffer_duration = kwargs['target_buffer_duration']
        if 'max_buffer_duration' in kwargs:
            self.max_buffer_duration = kwargs['max_buffer_duration'] 
        if 'min_buffer_duration' in kwargs:
            self.min_buffer_duration = kwargs['min_buffer_duration']
        if 'silence_threshold' in kwargs:
            self.silence_threshold = kwargs['silence_threshold']
        if 'volume_threshold' in kwargs:
            self.volume_threshold = kwargs['volume_threshold']
            
        logger.info("Speech recognition settings updated", 
                   target_duration=self.target_buffer_duration,
                   max_duration=self.max_buffer_duration,
                   min_duration=self.min_buffer_duration,
                   silence_threshold=self.silence_threshold,
                   volume_threshold=self.volume_threshold)
    
    def get_speech_stats(self) -> Dict[str, Any]:
        """Get comprehensive speech recognition statistics"""
        return {
            **self.stats,
            'settings': {
                'target_buffer_duration': self.target_buffer_duration,
                'max_buffer_duration': self.max_buffer_duration,
                'min_buffer_duration': self.min_buffer_duration,
                'silence_threshold': self.silence_threshold,
                'volume_threshold': self.volume_threshold
            },
            'success_rate': (
                self.stats['successful_transcriptions'] / self.stats['total_transcriptions']
                if self.stats['total_transcriptions'] > 0 else 0.0
            )
        }
    
    def _create_language_code_map(self) -> Dict[str, str]:
        """Create mapping from UI language codes to Google Cloud Speech-to-Text language codes"""
        return {
            # Major languages with proper regional codes
            'en': 'en-US',
            'es': 'es-ES',
            'fr': 'fr-FR', 
            'de': 'de-DE',
            'it': 'it-IT',
            'pt': 'pt-BR',
            'ru': 'ru-RU',
            'ja': 'ja-JP',
            'ko': 'ko-KR',
            'zh': 'zh-CN',
            'ar': 'ar-SA',
            'hi': 'hi-IN',
            'th': 'th-TH',
            'vi': 'vi-VN',
            'tr': 'tr-TR',
            'pl': 'pl-PL',
            'nl': 'nl-NL',
            'sv': 'sv-SE',
            'da': 'da-DK',
            'no': 'nb-NO',
            'fi': 'fi-FI',
            'cs': 'cs-CZ',
            'sk': 'sk-SK',
            'hu': 'hu-HU',
            'ro': 'ro-RO',
            'bg': 'bg-BG',
            'hr': 'hr-HR',
            'sl': 'sl-SI',
            'et': 'et-EE',
            'lv': 'lv-LV',
            'lt': 'lt-LT',
            'uk': 'uk-UA',
            'he': 'he-IL',
            'fa': 'fa-IR',
            'ur': 'ur-PK',
            'bn': 'bn-BD',
            'ta': 'ta-IN',
            'te': 'te-IN',
            'ml': 'ml-IN',
            'kn': 'kn-IN',
            'gu': 'gu-IN',
            'pa': 'pa-IN',
            'ne': 'ne-NP',
            'si': 'si-LK',
            'my': 'my-MM',
            'km': 'km-KH',
            'lo': 'lo-LA',
            'ka': 'ka-GE',
            'hy': 'hy-AM',
            'az': 'az-AZ',
            'kk': 'kk-KZ',
            'ky': 'ky-KG',
            'uz': 'uz-UZ',
            'tg': 'tg-TJ',
            'mn': 'mn-MN',
            'is': 'is-IS',
            'mt': 'mt-MT',
            'eu': 'eu-ES',
            'ca': 'ca-ES',
            'gl': 'gl-ES',
            'cy': 'cy-GB',
            'ga': 'ga-IE',
            'sw': 'sw-KE',
            'zu': 'zu-ZA',
            'af': 'af-ZA',
            'am': 'am-ET',
            'ig': 'ig-NG',
            'ha': 'ha-NG',
            'yo': 'yo-NG',
            'so': 'so-SO',
            'rw': 'rw-RW',
            'lg': 'lg-UG',
            'ln': 'ln-CD',
            'mg': 'mg-MG',
            'ny': 'ny-MW',
            'sn': 'sn-ZW',
            'st': 'st-ZA',
            'tn': 'tn-ZA',
            'ts': 'ts-ZA',
            've': 've-ZA',
            'xh': 'xh-ZA',
            'ss': 'ss-ZA'
        }
    
    def _get_speech_language_config(self, source_language: str) -> Dict[str, Any]:
        """Get Google Cloud Speech-to-Text language configuration"""
        try:
            # Use specific language only (no auto-detection)
            speech_language = self._language_code_map.get(source_language, 'en-US')
            config = {
                'language_code': speech_language,
                'alternative_language_codes': [],  # No alternatives needed
                'enable_language_detection': False
            }
            
            logger.info("🎯 Using specific language for speech recognition", 
                       ui_language=source_language, 
                       speech_language=speech_language)
            
            return config
            
        except Exception as e:
            logger.error("Error creating speech language config", error=str(e))
            # Fallback to English
            return {
                'language_code': 'en-US',
                'alternative_language_codes': [],
                'enable_language_detection': False
            }
    
    def _initialize_speech_client(self):
        """Initialize Google Cloud Speech-to-Text client"""
        try:
            # Load environment variables
            try:
                from dotenv import load_dotenv
                load_dotenv()
                logger.info("✅ Loaded environment variables from .env file")
            except ImportError:
                logger.warning("python-dotenv not installed, using system environment variables only")
            
            # Get API key or credentials
            api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('ADK_API_KEY')
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if api_key:
                logger.info("🔑 Using API key for Speech-to-Text", api_key_preview=api_key[:10] + "...")
                self.use_rest_api = True
                self.api_key = api_key
            elif creds_path and os.path.exists(creds_path):
                logger.info("🔑 Using credentials file for Speech-to-Text", creds_path=creds_path)
                self.google_client = GoogleCloudClient(credentials_path=creds_path)
                self.use_rest_api = False
            else:
                logger.info("🔑 Using default credentials for Speech-to-Text")
                self.google_client = GoogleCloudClient()
                self.use_rest_api = False
                
        except Exception as e:
            logger.error("Failed to initialize Speech-to-Text client", error=str(e))
            self.use_rest_api = False
            self.google_client = None
    
    async def _transcribe_with_rest_api(self, audio_data: bytes, language_code: str = "en-US", alternative_languages: list = None):
        """Transcribe audio using REST API with API key"""
        try:
            # Encode audio data
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare request configuration for longer speech recognition
            config = {
                "encoding": "LINEAR16",
                "sampleRateHertz": 16000,
                "languageCode": language_code,
                "enableAutomaticPunctuation": True,
                "enableWordTimeOffsets": True,
                "enableWordConfidence": True,
                "model": "latest_long",  # Best model for longer audio content
                "useEnhanced": True,     # Use enhanced model for better accuracy
                "maxAlternatives": 1,    # Focus on best result for speed
                "profanityFilter": False # Don't filter content
            }
            
            # Add alternative language codes for better detection
            if alternative_languages and len(alternative_languages) > 0:
                config["alternativeLanguageCodes"] = alternative_languages
                logger.info("🌐 Added alternative languages for detection", 
                           primary=language_code, 
                           alternatives=alternative_languages[:5])  # Log first 5 for brevity
            
            # Prepare request
            url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
            
            payload = {
                "config": config,
                "audio": {
                    "content": audio_base64
                }
            }
            
            logger.info("🔄 Making Speech-to-Text API request", 
                       audio_size=len(audio_data), 
                       language=language_code,
                       has_alternatives=bool(alternative_languages))
            
            response = requests.post(url, json=payload)
            
            logger.info("📨 Speech-to-Text API response", 
                       status_code=response.status_code,
                       response_size=len(response.text))
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Speech-to-Text API success", response_data=result)
                
                if 'results' in result and len(result['results']) > 0:
                    # Get the best alternative from the first result
                    first_result = result['results'][0]
                    if 'alternatives' in first_result and len(first_result['alternatives']) > 0:
                        best_alternative = first_result['alternatives'][0]
                        transcript = best_alternative.get('transcript', '')
                        confidence = best_alternative.get('confidence', 0.0)
                        
                        # Try to extract detected language if available
                        detected_language = language_code
                        if 'languageCode' in first_result:
                            detected_language = first_result['languageCode']
                        
                        logger.info("📝 Transcription successful", 
                                   transcript=transcript,
                                   confidence=confidence,
                                   detected_language=detected_language)
                        
                        return transcript, confidence, detected_language
                    else:
                        logger.warning("⚠️ No alternatives found in result")
                        return None, 0, language_code
                else:
                    logger.info("🔇 No speech detected in audio")
                    return None, 0, language_code
            else:
                logger.error("❌ Speech-to-Text API error", 
                           status_code=response.status_code,
                           error=response.text)
                return None, 0, language_code
                
        except Exception as e:
            logger.error("❌ Speech-to-Text REST API error", error=str(e))
            return None, 0, language_code
    
    async def _translate_with_rest_api(
        self, 
        text: str, 
        target_language: str,
        source_language: str = None
    ) -> Optional[Dict[str, Any]]:
        """Translate text using Google Translate REST API"""
        try:
            # Prepare request
            url = f"https://translation.googleapis.com/language/translate/v2?key={self.api_key}"
            
            payload = {
                "q": text,
                "target": target_language,
                "format": "text"
            }
            
            # Add source language if specified
            if source_language:
                payload["source"] = source_language
            
            logger.info("🔄 Making Translation API request", 
                       text=text[:100] + "..." if len(text) > 100 else text,
                       target_language=target_language,
                       source_language=source_language)
            
            response = requests.post(url, json=payload)
            
            logger.info("📨 Translation API response", 
                       status_code=response.status_code,
                       response_size=len(response.text))
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Translation API success", response_data=result)
                
                if 'data' in result and 'translations' in result['data']:
                    translation = result['data']['translations'][0]
                    
                    return {
                        'translated_text': translation['translatedText'],
                        'source_language': translation.get('detectedSourceLanguage', source_language),
                        'target_language': target_language,
                        'success': True
                    }
                else:
                    logger.error("❌ Invalid translation response format", response=result)
                    return None
            else:
                logger.error("❌ Translation API error", 
                           status_code=response.status_code,
                           error=response.text)
                return None
                
        except Exception as e:
            logger.error("❌ Translation REST API error", error=str(e))
            return None

    async def _transcribe_with_client(self, audio_data: bytes, language_code: str = "en-US", alternative_languages: list = None):
        """Transcribe audio using Google Cloud client library"""
        try:
            if self.google_client is None:
                logger.error("Google Cloud client not initialized")
                return None, 0, language_code
                
            # Initialize client if not already done
            if not self.google_client.is_initialized:
                await self.google_client.initialize()
            
            # Use the client to transcribe
            from google.cloud import speech
            
            # Configure recognition with dynamic language support for longer audio
            config_params = {
                'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                'sample_rate_hertz': 16000,
                'language_code': language_code,
                'enable_automatic_punctuation': True,
                'enable_word_time_offsets': True,
                'enable_word_confidence': True,
                'model': "latest_long",  # Best model for longer audio content
                'use_enhanced': True,    # Use enhanced model for better accuracy
                'max_alternatives': 1,   # Focus on best result for speed
                'profanity_filter': False # Don't filter content
            }
            
            # Add alternative language codes for better detection
            if alternative_languages and len(alternative_languages) > 0:
                config_params['alternative_language_codes'] = alternative_languages
                logger.info("🌐 Added alternative languages to client config", 
                           primary=language_code, 
                           alternatives=alternative_languages[:5])
            
            config = speech.RecognitionConfig(**config_params)
            audio = speech.RecognitionAudio(content=audio_data)
            
            logger.info("🔄 Making Speech-to-Text request via client", 
                       audio_size=len(audio_data), 
                       language=language_code,
                       has_alternatives=bool(alternative_languages))
            
            # Perform transcription
            if self.google_client.speech_client is None:
                logger.error("Google Cloud speech client not initialized")
                return None, 0, language_code
                
            response = self.google_client.speech_client.recognize(config=config, audio=audio)
            
            logger.info("📨 Speech-to-Text client response", 
                       results_count=len(response.results))
            
            if response.results:
                result = response.results[0]
                alternative = result.alternatives[0]
                transcript = alternative.transcript
                confidence = alternative.confidence
                
                # Try to get detected language from the result
                detected_language = language_code  # Default to requested language
                if hasattr(result, 'language_code') and result.language_code:
                    detected_language = result.language_code
                elif hasattr(result, 'language') and result.language:
                    detected_language = result.language
                
                logger.info("📝 Transcription result", 
                           transcript=transcript,
                           confidence=confidence,
                           detected_language=detected_language)
                
                # Update stats for successful transcription
                if transcript and transcript.strip():
                    self.stats['successful_transcriptions'] += 1
                return transcript, confidence, detected_language
            else:
                logger.info("🔇 No speech detected in audio")
                return None, 0, language_code
                
        except Exception as e:
            logger.error("❌ Speech-to-Text transcription error", error=str(e))
            return None, 0, language_code

    async def start_audio_session(
        self, 
        session_id: str, 
        websocket_callback,
        audio_config: Dict[str, Any] = None
    ) -> bool:
        """
        Start audio capture for a session
        
        Args:
            session_id: Unique session identifier
            websocket_callback: Function to send audio data via WebSocket
            audio_config: Optional audio configuration overrides
        
        Returns:
            bool: True if capture started successfully
        """
        if session_id in self.active_captures:
            logger.warning("Audio session already exists", session_id=session_id)
            print(f"🎤 SESSION DEBUG: Session {session_id} already exists")
            return True
        
        print(f"🎤 SESSION DEBUG: Starting new audio session for {session_id}")
        
        try:
            # Store the main event loop reference at session start
            try:
                self._main_loop = asyncio.get_running_loop()
                print(f"🎤 SESSION DEBUG: Got running event loop")
            except RuntimeError:
                self._main_loop = asyncio.get_event_loop()
                print(f"🎤 SESSION DEBUG: Got default event loop")
            
            # Create audio config
            config = self._create_audio_config(audio_config)
            print(f"🎤 SESSION DEBUG: Created config: {config}")
            
            # Check if system audio was requested and provide feedback
            requested_source = audio_config.get('audio_source') if audio_config else 'microphone'
            if requested_source == 'system':
                logger.info("🔊 System audio capture requested - checking for virtual audio devices...")
            
            # Initialize audio buffer for this session
            self.audio_buffers[session_id] = b""
            self.buffer_durations[session_id] = 0.0
            self.silence_buffers[session_id] = 0.0 # Initialize silence buffer
            self.last_speech_time[session_id] = time.time() # Initialize last speech time
            
            # Create PyAudio capture instance
            capture = PyAudioCapture(
                sample_rate=config['sample_rate'],
                channels=config['channels'],
                chunk_size=config['chunk_size'],
                buffer_duration_seconds=config['buffer_duration'],
                audio_source=config['audio_source'],
                device_index=config.get('device_index')
            )
            
            def create_audio_callback():
                def audio_callback(audio_data: bytes, metrics: Dict[str, Any]):
                    """Callback function for audio data - runs in capture thread"""
                    # We need to schedule the async processing on the main event loop
                    try:
                        if self._main_loop and not self._main_loop.is_closed():
                            asyncio.run_coroutine_threadsafe(
                                self._handle_audio_data(session_id, audio_data, metrics, websocket_callback),
                                self._main_loop
                            )
                        else:
                            print(f"⚠️ Warning: Main event loop not available for session {session_id}")
                    except Exception as e:
                        print(f"❌ Error scheduling audio processing: {e}")
                        logger.error("Error in audio callback scheduling", session_id=session_id, error=str(e))
                
                return audio_callback
            
            audio_callback = create_audio_callback()
            
            capture.set_audio_callback(audio_callback)
            
            # Initialize and start capture
            print(f"🎤 SESSION DEBUG: Initializing PyAudio capture...")
            if await capture.initialize():
                print(f"🎤 SESSION DEBUG: PyAudio initialized successfully, starting capture...")
                if await capture.start_capture():
                    print(f"🎤 SESSION DEBUG: PyAudio capture started successfully!")
                    
                    # Check if we got the requested audio source
                    if requested_source == 'system' and config['audio_source'] == 'system':
                        # Get the actual device being used
                        device_info = capture.py_audio.get_device_info_by_index(capture.device_index)
                        actual_device_name = device_info['name']
                        
                        # Check if it's actually a system audio device
                        system_keywords = ['blackhole', 'soundflower', 'loopback', 'stereo mix', 'what u hear', 'multi-output']
                        is_actual_system_audio = any(keyword in actual_device_name.lower() for keyword in system_keywords)
                        
                        if is_actual_system_audio:
                            logger.info(f"✅ System audio capture active using: {actual_device_name}")
                            await websocket_callback({
                                'type': 'audio_source_status',
                                'session_id': session_id,
                                'requested_source': 'system',
                                'actual_source': 'system',
                                'device_name': actual_device_name,
                                'status': 'success',
                                'message': f'System audio capture active using {actual_device_name}',
                                'timestamp': time.time()
                            })
                        else:
                            logger.warning(f"⚠️ System audio requested but using microphone: {actual_device_name}")
                            await websocket_callback({
                                'type': 'audio_source_status',
                                'session_id': session_id,
                                'requested_source': 'system',
                                'actual_source': 'microphone',
                                'device_name': actual_device_name,
                                'status': 'fallback',
                                'message': 'System audio not available - using microphone instead. Install BlackHole (macOS) or enable Stereo Mix (Windows) for system audio capture.',
                                'timestamp': time.time()
                            })
                    
                    # Store capture instance and metadata
                    self.active_captures[session_id] = capture
                    
                    # Check if there's existing language-only session config
                    existing_metadata = self.session_metadata.get(session_id, {})
                    existing_config = existing_metadata.get('config', {})
                    
                    # Preserve existing language settings if they exist
                    if existing_config and existing_metadata.get('language_only'):
                        # Merge existing language config with new audio config
                        config.update({
                            'source_language': existing_config.get('source_language', config.get('source_language', 'en')),
                            'target_language': existing_config.get('target_language', config.get('target_language', 'en'))
                        })
                        logger.info("✅ Merged existing language config with audio session", 
                                   session_id=session_id,
                                   source_language=config['source_language'],
                                   target_language=config['target_language'])
                    
                    # Create/update session metadata
                    self.session_metadata[session_id] = {
                        'started_at': time.time(),
                        'config': config,
                        'total_chunks': 0,
                        'total_bytes': 0,
                        'websocket_callback': websocket_callback,
                        'language_only': False  # This is now an active audio session
                    }
                    
                    # Update stats
                    self.stats['total_sessions'] += 1
                    self.stats['active_sessions'] = len(self.active_captures)
                    
                    logger.info("Audio session started with Speech-to-Text", 
                               session_id=session_id,
                               config=config)
                    
                    # Send confirmation to client
                    await websocket_callback({
                        'type': 'audio_session_started',
                        'session_id': session_id,
                        'config': config,
                        'timestamp': time.time()
                    })
                    
                    return True
                else:
                    await capture.cleanup()
            
            logger.error("Failed to start audio capture", session_id=session_id)
            return False
            
        except Exception as e:
            logger.error("Error starting audio session", session_id=session_id, error=str(e))
            return False

    async def stop_audio_session(self, session_id: str) -> bool:
        """
        Stop audio capture for a session
        
        Args:
            session_id: Session to stop
            
        Returns:
            bool: True if stopped successfully
        """
        if session_id not in self.active_captures:
            logger.warning("Audio session not found", session_id=session_id)
            return False
        
        try:
            capture = self.active_captures[session_id]
            metadata = self.session_metadata[session_id]
            
            # Stop capture
            await capture.stop_capture()
            await capture.cleanup()
            
            # Clean up audio buffers
            if session_id in self.audio_buffers:
                del self.audio_buffers[session_id]
            if session_id in self.buffer_durations:
                del self.buffer_durations[session_id]
            if session_id in self.silence_buffers:
                del self.silence_buffers[session_id]
            if session_id in self.last_speech_time:
                del self.last_speech_time[session_id]
            
            # Get final stats
            session_duration = time.time() - metadata['started_at']
            final_stats = {
                'session_id': session_id,
                'duration_seconds': session_duration,
                'total_chunks': metadata['total_chunks'],
                'total_bytes': metadata['total_bytes'],
                'config': metadata['config']
            }
            
            # Clean up session data
            del self.active_captures[session_id]
            del self.session_metadata[session_id]
            
            # Update stats
            self.stats['active_sessions'] = len(self.active_captures)
            
            logger.info("Audio session stopped", 
                       session_id=session_id,
                       duration_seconds=session_duration,
                       total_chunks=metadata['total_chunks'])
            
            # Send confirmation to client
            await metadata['websocket_callback']({
                'type': 'audio_session_ended',
                'session_id': session_id,
                'stats': final_stats,
                'timestamp': time.time()
            })
            
            return True
            
        except Exception as e:
            logger.error("Error stopping audio session", 
                        session_id=session_id, 
                        error=str(e))
            return False

    async def _handle_audio_data(
        self, 
        session_id: str, 
        audio_data: bytes, 
        metrics: Dict[str, Any],
        websocket_callback
    ):
        """
        Handle audio data from PyAudio capture with Speech-to-Text processing
        
        Args:
            session_id: Session ID
            audio_data: Raw audio bytes
            metrics: Audio quality metrics
            websocket_callback: WebSocket callback function
        """
        try:
            # Update session metadata
            if session_id in self.session_metadata:
                metadata = self.session_metadata[session_id]
                metadata['total_chunks'] += 1
                metadata['total_bytes'] += len(audio_data)
                
                # Get language settings from config
                config = metadata['config']
                source_language = config.get('source_language', 'en') # Changed default to 'en'
                target_language = config.get('target_language', 'en')
                
                # Get dynamic speech language configuration
                speech_config = self._get_speech_language_config(source_language)
                language_code = speech_config['language_code']
                alternative_languages = speech_config['alternative_language_codes']
                
                logger.info("🎤 Processing audio with language config", 
                           session_id=session_id,
                           source_language=source_language,
                           speech_language_code=language_code,
                           alternatives_count=len(alternative_languages),
                           enable_detection=speech_config.get('enable_language_detection', False))
            else:
                # Fallback if session not found
                language_code = 'en-US'
                alternative_languages = []
                source_language = 'en'
                target_language = 'en'
                logger.warning("Session metadata not found, using English fallback", session_id=session_id)
            
            # Add audio to buffer
            if session_id not in self.audio_buffers:
                self.audio_buffers[session_id] = b""
                self.buffer_durations[session_id] = 0.0
                self.silence_buffers[session_id] = 0.0 # Initialize silence buffer
                self.last_speech_time[session_id] = time.time() # Initialize last speech time
            
            self.audio_buffers[session_id] += audio_data
            self.buffer_durations[session_id] += len(audio_data) / (16000 * 2)  # 16kHz, 2 bytes per sample
            
            # Update silence buffer
            current_silence_duration = self.silence_buffers[session_id]
            if metrics.get('volume_percent', 0) < self.volume_threshold:
                current_silence_duration += len(audio_data) / (16000 * 2) # Increment by chunk duration
            else:
                current_silence_duration = 0.0 # Reset if speech detected
            
            self.silence_buffers[session_id] = current_silence_duration
            
            # Enhanced processing conditions for better sentence detection
            should_process = False
            process_reason = ""
            
            if self.buffer_durations[session_id] >= self.max_buffer_duration:
                should_process = True
                process_reason = "max_duration_reached"
                self.stats['sentences_detected'] += 1
            elif (self.buffer_durations[session_id] >= self.min_buffer_duration and 
                  self.silence_buffers[session_id] >= self.silence_threshold):
                should_process = True
                process_reason = "silence_break_detected"
                self.stats['silence_breaks'] += 1
            elif self.buffer_durations[session_id] >= self.target_buffer_duration:
                should_process = True
                process_reason = "target_duration_reached"
                
            if should_process:
                logger.info("🎙️ Processing audio buffer for transcription", 
                           session_id=session_id,
                           buffer_duration=self.buffer_durations[session_id],
                           buffer_size=len(self.audio_buffers[session_id]),
                           silence_duration=self.silence_buffers[session_id],
                           process_reason=process_reason)
                
                # Transcribe audio
                
                if self.use_rest_api and self.api_key:
                    transcript, confidence, detected_language = await self._transcribe_with_rest_api(
                        self.audio_buffers[session_id], 
                        language_code,
                        alternative_languages
                    )
                elif self.google_client:
                    transcript, confidence, detected_language = await self._transcribe_with_client(
                        self.audio_buffers[session_id], 
                        language_code,
                        alternative_languages
                    )
                    
                    # Update stats for successful transcription
                    if transcript and transcript.strip():
                        self.stats['successful_transcriptions'] += 1
                else:
                    logger.warning("No transcription service available")
                    transcript = None
                    confidence = 0
                    detected_language = language_code
                
                # Log transcription attempt
                self.stats['total_transcriptions'] += 1
                
                # Send transcription result to client
                if transcript and transcript.strip():
                    # Prepare transcription result
                    transcription_result = {
                        'transcript': transcript,
                        'confidence': confidence,
                        'language_detected': detected_language.split('-')[0],
                        'service_type': 'google_speech_to_text',
                        'processing_time_ms': int(time.time() * 1000),
                        'audio_duration_seconds': self.buffer_durations[session_id]
                    }
                    
                    # Add translation if target language is different from source
                    if session_id in self.session_metadata:
                        config = self.session_metadata[session_id]['config']
                        source_language = config.get('source_language', 'en')
                        target_language = config.get('target_language', 'en')
                        
                        # Translate if needed
                        if target_language != source_language:
                            logger.info("🌐 Translating text", 
                                       text=transcript,
                                       source_lang=source_language,
                                       target_lang=target_language)
                            
                            # DEBUG: Log the current session configuration
                            logger.info("🔍 Current session language config", 
                                       session_id=session_id,
                                       config=config,
                                       source_language=source_language,
                                       target_language=target_language)
                            
                            try:
                                # Ensure translation polisher is initialized
                                await self._ensure_polisher_initialized()
                                
                                raw_translation = None
                                translation_service = None
                                
                                # Get raw translation using Google Cloud client
                                if self.google_client:
                                    translation_result = await self.google_client.translate_text(
                                        transcript,
                                        target_language=target_language,
                                        source_language=source_language
                                    )
                                    
                                    if translation_result.get('success'):
                                        raw_translation = translation_result['translated_text']
                                        translation_service = 'google_cloud_translate'
                                        logger.info("✅ Raw translation obtained (Google Cloud)", 
                                                   original=transcript,
                                                   raw_translated=raw_translation)
                                    else:
                                        logger.error("❌ Translation failed", 
                                                   error=translation_result.get('error', 'Unknown error'))
                                        
                                elif self.use_rest_api and self.api_key:
                                    # Use REST API for translation
                                    translation_result = await self._translate_with_rest_api(
                                        transcript, 
                                        target_language,
                                        source_language
                                    )
                                    
                                    if translation_result:
                                        raw_translation = translation_result['translated_text']
                                        translation_service = 'google_translate_rest'
                                        logger.info("✅ Raw translation obtained (REST)", 
                                                   original=transcript,
                                                   raw_translated=raw_translation)
                                    else:
                                        logger.error("❌ Translation failed (REST)")
                                
                                # Apply translation polishing if we have a raw translation
                                if raw_translation and self._polisher_initialized:
                                    logger.info("🔧 Applying translation polisher", 
                                               raw_translation=raw_translation,
                                               target_language=target_language)
                                    
                                    # DEBUG: Log polisher status
                                    logger.info("🔍 POLISHER DEBUG", 
                                               polisher_initialized=self._polisher_initialized,
                                               raw_translation_length=len(raw_translation),
                                               target_language=target_language)
                                    
                                    # Convert language code to full language name for polisher
                                    language_map = {
                                        'en': 'english',
                                        'es': 'spanish', 
                                        'fr': 'french',
                                        'de': 'german',
                                        'pt': 'portuguese',
                                        'it': 'italian',
                                        'nl': 'dutch'
                                    }
                                    polisher_language = language_map.get(target_language, 'english')
                                    
                                    logger.info("🌐 LANGUAGE MAPPING", 
                                               original_code=target_language,
                                               polisher_language=polisher_language,
                                               available_languages=list(language_map.keys()))
                                    
                                    # Define AI enhancement callback for later improvements
                                    async def ai_enhancement_callback(enhanced_translation: str):
                                        """Send AI-enhanced translation to frontend"""
                                        try:
                                            logger.info("🤖 AI-enhanced translation ready", 
                                                       original=raw_translation,
                                                       enhanced=enhanced_translation)
                                            
                                            # Send enhanced translation update
                                            enhanced_result = {
                                                'transcript': transcript,
                                                'confidence': confidence,
                                                'language_detected': detected_language.split('-')[0],
                                                'service_type': 'google_speech_to_text',
                                                'processing_time_ms': int(time.time() * 1000),
                                                'audio_duration_seconds': self.buffer_durations[session_id],
                                                'translation': {
                                                    'text': enhanced_translation,
                                                    'source_language': source_language,
                                                    'target_language': target_language,
                                                    'service_type': translation_service + '_ai_enhanced',
                                                    'polisher_applied': True,
                                                    'enhancement_type': 'ai_enhanced'
                                                }
                                            }
                                            
                                            await websocket_callback({
                                                'type': 'transcription_result',
                                                'session_id': session_id,
                                                'data': enhanced_result,
                                                'timestamp': time.time(),
                                                'is_enhancement': True
                                            })
                                            
                                        except Exception as e:
                                            logger.error("❌ AI enhancement callback error", error=str(e))
                                    
                                    # Apply instant polishing (0-5ms) with AI enhancement queued
                                    # Use polisher_language instead of target_language
                                    polished_translation = await self.translation_polisher.polish_translation(
                                        raw_translation=raw_translation,
                                        target_language=polisher_language,  # Fixed: use proper language name
                                        ai_callback=ai_enhancement_callback
                                    )
                                    
                                    logger.info("✨ Translation polished successfully", 
                                               raw=raw_translation,
                                               polished=polished_translation,
                                               improvement_applied=polished_translation != raw_translation,
                                               character_change=len(polished_translation) - len(raw_translation))
                                    
                                    # DEBUG: Log specific changes made
                                    if polished_translation != raw_translation:
                                        logger.info("🎯 GRAMMAR CORRECTION APPLIED", 
                                                   before=raw_translation,
                                                   after=polished_translation,
                                                   language=polisher_language)
                                    else:
                                        logger.info("ℹ️ No grammar correction needed", 
                                                   text=raw_translation,
                                                   language=polisher_language)
                                    
                                    # Use polished translation for immediate response
                                    transcription_result['translation'] = {
                                        'text': polished_translation,
                                        'source_language': source_language,
                                        'target_language': target_language,
                                        'service_type': translation_service + '_polished',
                                        'polisher_applied': True,
                                        'raw_translation': raw_translation  # Keep for reference
                                    }
                                    
                                elif raw_translation:
                                    # DEBUG: Log why polisher wasn't used
                                    logger.warning("⚠️ Translation polisher not available", 
                                                  polisher_initialized=self._polisher_initialized,
                                                  raw_translation_present=bool(raw_translation))
                                    transcription_result['translation'] = {
                                        'text': raw_translation,
                                        'source_language': source_language,
                                        'target_language': target_language,
                                        'service_type': translation_service,
                                        'polisher_applied': False
                                    }
                                else:
                                    logger.warning("⚠️ No raw translation to polish")
                                        
                            except Exception as e:
                                logger.error("❌ Translation error", error=str(e))
                    
                    # Send result to client
                    await websocket_callback({
                        'type': 'transcription_result',
                        'session_id': session_id,
                        'data': transcription_result,
                        'timestamp': time.time()
                    })
                    
                    logger.info("📝 Transcription sent to client", 
                               session_id=session_id,
                               transcript=transcript,
                               confidence=confidence,
                               has_translation=bool(transcription_result.get('translation')))
                else:
                    logger.info("🔇 No speech detected in audio buffer", 
                               session_id=session_id)
                
                # Reset buffer
                self.audio_buffers[session_id] = b""
                self.buffer_durations[session_id] = 0.0
                self.silence_buffers[session_id] = 0.0 # Reset silence buffer
                self.last_speech_time[session_id] = time.time() # Reset last speech time
            
            # Create message for WebSocket (for debugging/monitoring)
            message = {
                'type': 'audio_chunk',
                'session_id': session_id,
                'audio_data': {
                    'size_bytes': len(audio_data),
                    'timestamp': metrics['timestamp'],
                    'duration_seconds': metrics['duration_seconds'],
                    'sample_rate': metrics['sample_rate'],
                    'channels': metrics['channels']
                },
                'audio_metrics': {
                    'volume_db': metrics['volume_db'],
                    'volume_percent': metrics['volume_percent'],
                    'rms': metrics['rms']
                },
                'timestamp': time.time()
            }
            
            # Send audio data via WebSocket (for monitoring)
            await websocket_callback(message)
            
            # Log audio processing
            logger.debug("Audio chunk processed", 
                        session_id=session_id,
                        bytes=len(audio_data),
                        volume_percent=metrics['volume_percent'])
            
        except Exception as e:
            logger.error("Error handling audio data", 
                        session_id=session_id, 
                        error=str(e))

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a session"""
        if session_id not in self.active_captures:
            return None
        
        capture = self.active_captures[session_id]
        metadata = self.session_metadata[session_id]
        
        current_time = time.time()
        session_duration = current_time - metadata['started_at']
        
        return {
            'session_id': session_id,
            'is_active': capture.is_capturing,
            'started_at': metadata['started_at'],
            'duration_seconds': session_duration,
            'config': metadata['config'],
            'capture_stats': capture.get_stats(),
            'session_stats': {
                'total_chunks': metadata['total_chunks'],
                'total_bytes': metadata['total_bytes']
            }
        }
    
    async def list_active_sessions(self) -> Dict[str, Any]:
        """List all active audio sessions"""
        sessions = {}
        
        for session_id in self.active_captures:
            session_status = await self.get_session_status(session_id)
            if session_status:
                sessions[session_id] = session_status
        
        return {
            'active_sessions': sessions,
            'total_active': len(sessions),
            'global_stats': self.stats
        }
    
    async def stop_all_sessions(self):
        """Stop all active audio sessions"""
        logger.info("Stopping all audio sessions", 
                   active_count=len(self.active_captures))
        
        # Create list of session IDs to avoid modifying dict during iteration
        session_ids = list(self.active_captures.keys())
        
        for session_id in session_ids:
            await self.stop_audio_session(session_id)
        
        logger.info("All audio sessions stopped")
    
    def _create_audio_config(self, custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create audio configuration with defaults and custom overrides"""
        config = {
            'sample_rate': 16000,
            'channels': 1,
            'chunk_size': 1024,
            'buffer_duration': 1.0,
            'audio_source': 'microphone',  # Default to microphone
            'device_index': None,  # Auto-select device
            'format': 'int16'
        }
        
        # Apply custom overrides
        if custom_config:
            config.update(custom_config)
        
        # Validate audio source
        if config['audio_source'] not in ['microphone', 'system']:
            logger.warning("Invalid audio source, falling back to microphone", 
                         source=config['audio_source'])
            config['audio_source'] = 'microphone'
        
        # Adjust channels for system audio (usually stereo)
        if config['audio_source'] == 'system' and config['channels'] == 1:
            config['channels'] = 2  # System audio is typically stereo
            logger.info("Adjusted channels for system audio", channels=2)
        
        return config
    
    async def handle_websocket_message(
        self, 
        session_id: str, 
        message: Dict[str, Any],
        websocket_callback
    ) -> bool:
        """
        Handle WebSocket message for audio control
        
        Args:
            session_id: Session ID
            message: WebSocket message
            websocket_callback: WebSocket callback function
            
        Returns:
            bool: True if message was handled
        """
        try:
            message_type = message.get('type')
            print(f"🎤 HANDLER DEBUG: Processing message type: {message_type}")
            
            if message_type == 'start_audio_capture' or message_type == 'start_capture':
                print(f"🎤 HANDLER DEBUG: Starting audio capture for session {session_id}")
                # Start audio capture (handle both message types)
                audio_config = message.get('config', {}) or message.get('audio_config', {})
                print(f"🎤 HANDLER DEBUG: Audio config: {audio_config}")
                result = await self.start_audio_session(
                    session_id, 
                    websocket_callback, 
                    audio_config
                )
                print(f"🎤 HANDLER DEBUG: Start session result: {result}")
                return result
            
            elif message_type == 'stop_audio_capture' or message_type == 'stop_capture':
                # Stop audio capture (handle both message types)
                return await self.stop_audio_session(session_id)
            
            elif message_type == 'get_audio_status':
                # Get session status
                status = await self.get_session_status(session_id)
                await websocket_callback({
                    'type': 'audio_status',
                    'session_id': session_id,
                    'status': status,
                    'timestamp': time.time()
                })
                return True
            
            elif message_type == 'get_audio_devices':
                # Get available audio devices
                if session_id in self.active_captures:
                    capture = self.active_captures[session_id]
                    device_info = capture._get_device_info()
                    await websocket_callback({
                        'type': 'audio_devices',
                        'session_id': session_id,
                        'devices': device_info,
                        'timestamp': time.time()
                    })
                    return True
                else:
                    return False
            
            elif message_type == 'update_language_config':
                # Update language configuration (works with or without active session)
                language_config = message.get('language_config', {})
                if language_config:
                    # Get source and target languages from the message
                    source_language = language_config.get('source_language', 'en')
                    target_language = language_config.get('target_language', 'en')
                    
                    # Store language preferences for the session (create if doesn't exist)
                    if session_id not in self.session_metadata:
                        # Create a placeholder session metadata to store language config
                        self.session_metadata[session_id] = {
                            'config': {
                                'source_language': source_language,
                                'target_language': target_language,
                                'audio_source': 'microphone',  # default
                                'sample_rate': 16000,
                                'channels': 1
                            },
                            'language_only': True  # Flag to indicate this is language-only config
                        }
                        logger.info("Created language-only session config", 
                                   session_id=session_id,
                                   source_language=source_language,
                                   target_language=target_language)
                    else:
                        # Update existing session configuration
                        current_config = self.session_metadata[session_id]['config']
                        current_config.update({
                            'source_language': source_language,
                            'target_language': target_language
                        })
                        logger.info("Updated existing session language config", 
                                   session_id=session_id,
                                   source_language=source_language,
                                   target_language=target_language)
                    
                    # Send confirmation to client
                    await websocket_callback({
                        'type': 'language_config_updated',
                        'session_id': session_id,
                        'config': {
                            'source_language': source_language,
                            'target_language': target_language
                        },
                        'timestamp': time.time()
                    })
                    
                    return True
                else:
                    logger.warning("Invalid language config - no language_config data", session_id=session_id)
                    return False
            
            elif message_type == 'update_speech_settings':
                # Handle dynamic speech recognition settings updates
                settings_data = message.get('settings', {})
                
                # Update speech settings
                self.update_speech_settings(**settings_data)
                
                # Send confirmation back to client
                await websocket_callback({
                    'type': 'speech_settings_updated',
                    'session_id': session_id,
                    'settings': {
                        'target_buffer_duration': self.target_buffer_duration,
                        'max_buffer_duration': self.max_buffer_duration,
                        'min_buffer_duration': self.min_buffer_duration,
                        'silence_threshold': self.silence_threshold,
                        'volume_threshold': self.volume_threshold
                    },
                    'timestamp': time.time()
                })
                
                return True
            
            elif message_type == 'get_speech_stats':
                # Handle speech statistics request
                stats = self.get_speech_stats()
                
                # Send stats back to client
                await websocket_callback({
                    'type': 'speech_stats_response',
                    'session_id': session_id,
                    'stats': stats,
                    'timestamp': time.time()
                })
                
                return True
            
            else:
                logger.warning("Unknown message type", 
                             message_type=message_type,
                             session_id=session_id)
                return False
                
        except Exception as e:
            logger.error("Error handling WebSocket message", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up audio stream handler")
        
        # Stop all active sessions
        await self.stop_all_sessions()
        
        # Clear all buffers
        self.audio_buffers.clear()
        self.buffer_durations.clear()
        self.silence_buffers.clear()
        self.last_speech_time.clear()
        
        # Clean up Google Cloud client
        if self.google_client:
            await self.google_client.cleanup()
        
        logger.info("Audio stream handler cleanup completed") 

    async def _initialize_polisher_early(self):
        """Initialize the polisher early during startup"""
        try:
            await asyncio.sleep(0.1)  # Small delay to let the main init finish
            await self.translation_polisher.initialize()
            self._polisher_initialized = True
            logger.info("✅ Translation polisher initialized early and ready!")
            
            # Test the polisher with a simple example
            await self._test_polisher()
            
        except Exception as e:
            logger.error(f"❌ Early polisher initialization failed: {e}")
            self._polisher_initialized = False
    
    async def _test_polisher(self):
        """Test the polisher with sample text to verify it's working"""
        try:
            test_texts = [
                "Hello, my name is Rashawn",  # Should stay the same
                "Hallo, my name is Rashawn", # Should fix "Hallo" -> "Hello"
                "me name is John",          # Should fix "me name" -> "my name"
                "I am go to the store",     # Should fix "I am go" -> "I am going"
            ]
            
            for test_text in test_texts:
                polished = await self.translation_polisher.polish_translation(
                    raw_translation=test_text,
                    target_language="english"
                )
                
                logger.info("🧪 POLISHER TEST", 
                           input=test_text,
                           output=polished,
                           changed=polished != test_text)
                           
        except Exception as e:
            logger.error(f"❌ Polisher test failed: {e}") 