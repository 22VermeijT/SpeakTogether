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
        self.target_buffer_duration = 3.0  # Process every 3 seconds
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'total_audio_bytes': 0,
            'total_chunks_processed': 0,
            'total_transcriptions': 0,
            'successful_transcriptions': 0
        }
        self._main_loop = None
        
        # Initialize Speech-to-Text client
        self._initialize_speech_client()
        
        logger.info("Audio stream handler initialized with Speech-to-Text support")
    
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
    
    async def _transcribe_with_rest_api(self, audio_data: bytes, language_code: str = "en-US"):
        """Transcribe audio using REST API with API key"""
        try:
            # Encode audio data
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare request
            url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
            
            payload = {
                "config": {
                    "encoding": "LINEAR16",
                    "sampleRateHertz": 16000,
                    "languageCode": language_code,
                    "enableAutomaticPunctuation": True,
                    "model": "latest_long"
                },
                "audio": {
                    "content": audio_base64
                }
            }
            
            logger.info("🔄 Making Speech-to-Text API request", 
                       audio_size=len(audio_data), 
                       language=language_code)
            
            response = requests.post(url, json=payload)
            
            logger.info("📨 Speech-to-Text API response", 
                       status_code=response.status_code,
                       response_size=len(response.text))
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Speech-to-Text API success", response_data=result)
                
                if 'results' in result and result['results']:
                    transcript = result['results'][0]['alternatives'][0]['transcript']
                    confidence = result['results'][0]['alternatives'][0].get('confidence', 0)
                    
                    logger.info("📝 Transcription result", 
                               transcript=transcript,
                               confidence=confidence)
                    
                    self.stats['successful_transcriptions'] += 1
                    return transcript, confidence
                else:
                    logger.info("🔇 No speech detected in audio")
                    return None, 0
            else:
                logger.error("❌ Speech-to-Text API error", 
                           status_code=response.status_code,
                           error=response.text)
                return None, 0
                
        except Exception as e:
            logger.error("❌ Speech-to-Text transcription error", error=str(e))
            return None, 0
    
    async def _transcribe_with_client(self, audio_data: bytes, language_code: str = "en-US"):
        """Transcribe audio using Google Cloud client library"""
        try:
            if self.google_client is None:
                logger.error("Google Cloud client not initialized")
                return None, 0
                
            # Initialize client if not already done
            if not self.google_client.is_initialized:
                await self.google_client.initialize()
            
            # Use the client to transcribe
            from google.cloud import speech
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="latest_long"
            )
            
            audio = speech.RecognitionAudio(content=audio_data)
            
            logger.info("🔄 Making Speech-to-Text request via client", 
                       audio_size=len(audio_data), 
                       language=language_code)
            
            # Perform transcription
            if self.google_client.speech_client is None:
                logger.error("Google Cloud speech client not initialized")
                return None, 0
                
            response = self.google_client.speech_client.recognize(config=config, audio=audio)
            
            logger.info("📨 Speech-to-Text client response", 
                       results_count=len(response.results))
            
            if response.results:
                result = response.results[0]
                transcript = result.alternatives[0].transcript
                confidence = result.alternatives[0].confidence
                
                logger.info("📝 Transcription result", 
                           transcript=transcript,
                           confidence=confidence)
                
                self.stats['successful_transcriptions'] += 1
                return transcript, confidence
            else:
                logger.info("🔇 No speech detected in audio")
                return None, 0
                
        except Exception as e:
            logger.error("❌ Speech-to-Text transcription error", error=str(e))
            return None, 0

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
            
            # Initialize audio buffer for this session
            self.audio_buffers[session_id] = b""
            self.buffer_durations[session_id] = 0.0
            
            # Create PyAudio capture instance
            capture = PyAudioCapture(
                sample_rate=config['sample_rate'],
                channels=config['channels'],
                chunk_size=config['chunk_size'],
                buffer_duration_seconds=config['buffer_duration'],
                audio_source=config['audio_source'],
                device_index=config.get('device_index')
            )
            
            # Set up callback for audio data with proper event loop handling
            def audio_callback(audio_data: bytes, metrics: Dict[str, Any]):
                print(f"🎤 CALLBACK DEBUG: Audio callback called! Data: {len(audio_data)} bytes, Volume: {metrics.get('volume_percent', 0):.1f}%")
                # Use thread-safe approach for asyncio from PyAudio thread
                try:
                    # Validate inputs
                    if not audio_data or not metrics:
                        logger.warning("Invalid audio data or metrics in callback", 
                                     session_id=session_id)
                        print(f"🎤 CALLBACK DEBUG: Invalid audio data or metrics")
                        return
                    
                    # Check if we have a valid event loop reference
                    if self._main_loop and not self._main_loop.is_closed():
                        # Schedule the coroutine on the main event loop from PyAudio thread
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                self._handle_audio_data(session_id, audio_data, metrics, websocket_callback),
                                self._main_loop
                            )
                            # Don't wait for result to avoid blocking PyAudio thread
                            logger.debug("Audio callback scheduled successfully", 
                                       session_id=session_id,
                                       thread=threading.current_thread().name,
                                       audio_bytes=len(audio_data))
                        except RuntimeError as e:
                            if "cannot schedule" in str(e).lower():
                                logger.error("Event loop closed, cannot schedule audio callback", 
                                           session_id=session_id)
                            else:
                                logger.error("Runtime error in audio callback", 
                                           session_id=session_id, 
                                           error=str(e))
                    else:
                        logger.warning("Main event loop not available for audio callback", 
                                     session_id=session_id,
                                     loop_available=self._main_loop is not None,
                                     loop_closed=self._main_loop.is_closed() if self._main_loop else "N/A")
                except Exception as e:
                    logger.error("Error scheduling audio callback", 
                               session_id=session_id, 
                               thread=threading.current_thread().name,
                               error=str(e),
                               error_type=type(e).__name__)
            
            capture.set_audio_callback(audio_callback)
            
            # Initialize and start capture
            print(f"🎤 SESSION DEBUG: Initializing PyAudio capture...")
            if await capture.initialize():
                print(f"🎤 SESSION DEBUG: PyAudio initialized successfully, starting capture...")
                if await capture.start_capture():
                    print(f"🎤 SESSION DEBUG: PyAudio capture started successfully!")
                    # Store capture instance and metadata
                    self.active_captures[session_id] = capture
                    self.session_metadata[session_id] = {
                        'started_at': time.time(),
                        'config': config,
                        'total_chunks': 0,
                        'total_bytes': 0,
                        'websocket_callback': websocket_callback
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
            logger.error("Error starting audio session", 
                        session_id=session_id, 
                        error=str(e))
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
            language_code = "en-US"  # Default
            if session_id in self.session_metadata:
                metadata = self.session_metadata[session_id]
                metadata['total_chunks'] += 1
                metadata['total_bytes'] += len(audio_data)
                
                # Get language settings from config
                config = metadata['config']
                source_language = config.get('source_language', 'en')
                target_language = config.get('target_language', 'en')
                
                # Convert language codes for Google API
                if source_language != 'auto':
                    language_code = f"{source_language}-US" if source_language == 'en' else source_language
            
            # Add audio to buffer
            if session_id not in self.audio_buffers:
                self.audio_buffers[session_id] = b""
                self.buffer_durations[session_id] = 0.0
            
            self.audio_buffers[session_id] += audio_data
            self.buffer_durations[session_id] += len(audio_data) / (16000 * 2)  # 16kHz, 2 bytes per sample
            
            # Process when we have enough audio
            if self.buffer_durations[session_id] >= self.target_buffer_duration:
                logger.info("🎙️ Processing audio buffer for transcription", 
                           session_id=session_id,
                           buffer_duration=self.buffer_durations[session_id],
                           buffer_size=len(self.audio_buffers[session_id]))
                
                # Transcribe audio
                self.stats['total_transcriptions'] += 1
                
                if self.use_rest_api and self.api_key:
                    transcript, confidence = await self._transcribe_with_rest_api(
                        self.audio_buffers[session_id], 
                        language_code
                    )
                elif self.google_client:
                    transcript, confidence = await self._transcribe_with_client(
                        self.audio_buffers[session_id], 
                        language_code
                    )
                else:
                    logger.error("No Speech-to-Text client available")
                    transcript, confidence = None, 0
                
                # Send transcription result to client
                if transcript and transcript.strip():
                    await websocket_callback({
                        'type': 'transcription_result',
                        'session_id': session_id,
                        'data': {
                            'transcript': transcript,
                            'confidence': confidence,
                            'language_detected': language_code.split('-')[0],
                            'service_type': 'google_speech_to_text',
                            'processing_time_ms': int(time.time() * 1000),
                            'audio_duration_seconds': self.buffer_durations[session_id]
                        },
                        'timestamp': time.time()
                    })
                    
                    logger.info("📝 Transcription sent to client", 
                               session_id=session_id,
                               transcript=transcript,
                               confidence=confidence)
                else:
                    logger.info("🔇 No speech detected in audio buffer", 
                               session_id=session_id)
                
                # Reset buffer
                self.audio_buffers[session_id] = b""
                self.buffer_durations[session_id] = 0.0
            
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
        
        # Clean up Google Cloud client
        if self.google_client:
            await self.google_client.cleanup()
        
        logger.info("Audio stream handler cleanup completed") 