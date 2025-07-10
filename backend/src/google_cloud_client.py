"""
Google Cloud Speech-to-Text Client for SpeakTogether
Real-time streaming speech recognition with translation
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, AsyncGenerator, List
import structlog

try:
    from google.cloud import speech
    from google.cloud import translate_v2 as translate
    from google.cloud import texttospeech
    from google.api_core import exceptions as google_exceptions
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    speech = None
    translate = None
    texttospeech = None
    google_exceptions = None

logger = structlog.get_logger()


class GoogleCloudClient:
    """
    Google Cloud client for speech-to-text, translation, and text-to-speech
    Supports real-time streaming and batch processing
    """
    
    def __init__(self, project_id: str = None, credentials_path: str = None):
        """
        Initialize Google Cloud client
        
        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account credentials JSON file
        """
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.error("Google Cloud libraries not available")
            raise ImportError("Google Cloud libraries not installed")
        
        self.project_id = project_id
        self.credentials_path = credentials_path
        
        # Initialize clients
        self.speech_client: Optional[speech.SpeechClient] = None
        self.translate_client: Optional[translate.Client] = None
        self.tts_client: Optional[texttospeech.TextToSpeechClient] = None
        
        # Streaming state
        self.streaming_sessions: Dict[str, Any] = {}
        self.is_initialized = False
        
        logger.info("Google Cloud client initialized", 
                   project_id=project_id,
                   credentials_path=bool(credentials_path))
    
    async def initialize(self) -> bool:
        """Initialize Google Cloud clients"""
        try:
            # Initialize Speech-to-Text client
            if self.credentials_path:
                import os
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
            
            self.speech_client = speech.SpeechClient()
            self.translate_client = translate.Client()
            self.tts_client = texttospeech.TextToSpeechClient()
            
            # Test connection
            await self._test_connection()
            
            self.is_initialized = True
            logger.info("Google Cloud clients initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Google Cloud clients", error=str(e))
            return False
    
    async def _test_connection(self):
        """Test connection to Google Cloud services"""
        try:
            # Test speech client
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
            )
            # This doesn't actually make a request, just validates config
            
            # Test translate client
            self.translate_client.get_languages()
            
            logger.info("Google Cloud connection test successful")
            
        except Exception as e:
            logger.error("Google Cloud connection test failed", error=str(e))
            raise
    
    async def start_streaming_recognition(
        self, 
        session_id: str,
        language_code: str = "en-US",
        sample_rate: int = 16000,
        audio_channel_count: int = 1
    ) -> bool:
        """
        Start streaming speech recognition session
        
        Args:
            session_id: Unique session identifier
            language_code: Language code (e.g., "en-US", "es-ES")
            sample_rate: Audio sample rate in Hz
            audio_channel_count: Number of audio channels
            
        Returns:
            bool: True if session started successfully
        """
        if not self.is_initialized:
            logger.error("Google Cloud client not initialized")
            return False
        
        try:
            # Create streaming config
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=language_code,
                audio_channel_count=audio_channel_count,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model="latest_long",  # Use latest model for better accuracy
                use_enhanced=True,    # Use enhanced model if available
            )
            
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,
                single_utterance=False,
            )
            
            # Create streaming session
            session = {
                'config': streaming_config,
                'requests': [],
                'active': True,
                'start_time': time.time(),
                'total_audio_bytes': 0,
                'result_count': 0
            }
            
            self.streaming_sessions[session_id] = session
            
            logger.info("Started streaming recognition session", 
                       session_id=session_id,
                       language_code=language_code,
                       sample_rate=sample_rate)
            
            return True
            
        except Exception as e:
            logger.error("Failed to start streaming recognition", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def process_audio_chunk(
        self, 
        session_id: str, 
        audio_data: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Process audio chunk and return recognition results
        
        Args:
            session_id: Session identifier
            audio_data: Raw audio bytes
            
        Returns:
            Dict containing recognition results or None if no results
        """
        if session_id not in self.streaming_sessions:
            logger.error("Session not found", session_id=session_id)
            return None
        
        session = self.streaming_sessions[session_id]
        
        try:
            # Create audio request
            audio_request = speech.StreamingRecognizeRequest(
                audio_content=audio_data
            )
            
            # Add to request queue
            session['requests'].append(audio_request)
            session['total_audio_bytes'] += len(audio_data)
            
            # Process requests if we have enough data
            if len(session['requests']) >= 10:  # Process every 10 chunks
                return await self._process_streaming_requests(session_id)
            
            return None
            
        except Exception as e:
            logger.error("Error processing audio chunk", 
                        session_id=session_id, 
                        error=str(e))
            return None
    
    async def _process_streaming_requests(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Process accumulated streaming requests"""
        session = self.streaming_sessions[session_id]
        
        try:
            # Create request generator
            def request_generator():
                # First, send the configuration
                yield speech.StreamingRecognizeRequest(
                    streaming_config=session['config']
                )
                
                # Then send all accumulated audio requests
                for request in session['requests']:
                    yield request
            
            # Call streaming recognition
            responses = self.speech_client.streaming_recognize(request_generator())
            
            results = []
            for response in responses:
                if response.results:
                    for result in response.results:
                        if result.alternatives:
                            alternative = result.alternatives[0]
                            results.append({
                                'transcript': alternative.transcript,
                                'confidence': alternative.confidence,
                                'is_final': result.is_final,
                                'stability': result.stability if hasattr(result, 'stability') else 0.0
                            })
            
            # Clear processed requests
            session['requests'] = []
            session['result_count'] += len(results)
            
            # Return best result
            if results:
                # Get the most confident final result or the most stable interim result
                final_results = [r for r in results if r['is_final']]
                if final_results:
                    best_result = max(final_results, key=lambda x: x['confidence'])
                else:
                    best_result = max(results, key=lambda x: x['stability'])
                
                return {
                    'session_id': session_id,
                    'transcript': best_result['transcript'],
                    'confidence': best_result['confidence'],
                    'is_final': best_result['is_final'],
                    'language_detected': session['config'].config.language_code,
                    'processing_time_ms': int((time.time() - session['start_time']) * 1000),
                    'service_type': 'google_cloud_speech',
                    'total_results': session['result_count']
                }
            
            return None
            
        except google_exceptions.GoogleAPIError as e:
            logger.error("Google API error in streaming recognition", 
                        session_id=session_id, 
                        error=str(e))
            return None
        except Exception as e:
            logger.error("Error in streaming recognition", 
                        session_id=session_id, 
                        error=str(e))
            return None
    
    async def stop_streaming_recognition(self, session_id: str) -> Dict[str, Any]:
        """Stop streaming recognition session and return statistics"""
        if session_id not in self.streaming_sessions:
            logger.warning("Session not found for stopping", session_id=session_id)
            return {}
        
        session = self.streaming_sessions[session_id]
        
        try:
            # Process any remaining requests
            final_result = None
            if session['requests']:
                final_result = await self._process_streaming_requests(session_id)
            
            # Calculate session statistics
            session_duration = time.time() - session['start_time']
            stats = {
                'session_id': session_id,
                'duration_seconds': session_duration,
                'total_audio_bytes': session['total_audio_bytes'],
                'total_results': session['result_count'],
                'average_processing_rate': session['total_audio_bytes'] / session_duration if session_duration > 0 else 0,
                'final_result': final_result
            }
            
            # Clean up session
            del self.streaming_sessions[session_id]
            
            logger.info("Stopped streaming recognition session", 
                       session_id=session_id,
                       stats=stats)
            
            return stats
            
        except Exception as e:
            logger.error("Error stopping streaming recognition", 
                        session_id=session_id, 
                        error=str(e))
            return {}
    
    async def speech_to_text(
        self, 
        audio_data: bytes, 
        language_code: str = "en-US",
        sample_rate: int = 16000,
        audio_channel_count: int = 1
    ) -> Dict[str, Any]:
        """
        Convert speech to text using Google Cloud Speech-to-Text API
        
        Args:
            audio_data: Raw audio data in bytes
            language_code: Language code (e.g., "en-US")
            sample_rate: Audio sample rate in Hz
            audio_channel_count: Number of audio channels
            
        Returns:
            Dict containing transcription results
        """
        if not self.is_initialized:
            logger.error("Google Cloud client not initialized")
            return {
                'success': False,
                'error': 'Client not initialized',
                'transcript': '',
                'confidence': 0.0
            }
        
        try:
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=language_code,
                audio_channel_count=audio_channel_count,
                enable_automatic_punctuation=True,
                model="latest_short"
            )
            
            # Create audio object
            audio = speech.RecognitionAudio(content=audio_data)
            
            logger.info("Making Speech-to-Text request", 
                       audio_size=len(audio_data),
                       language=language_code,
                       sample_rate=sample_rate)
            
            # Perform the transcription
            response = self.speech_client.recognize(config=config, audio=audio)
            
            # Process response
            if response.results:
                # Get the first result with the highest confidence
                result = response.results[0]
                alternative = result.alternatives[0]
                
                logger.info("Speech-to-Text successful", 
                           transcript=alternative.transcript,
                           confidence=alternative.confidence)
                
                return {
                    'success': True,
                    'transcript': alternative.transcript,
                    'confidence': alternative.confidence,
                    'language': language_code,
                    'service_type': 'google_cloud_speech',
                    'audio_duration_seconds': len(audio_data) / (sample_rate * audio_channel_count * 2)
                }
            else:
                logger.info("No speech detected in audio")
                return {
                    'success': False,
                    'error': 'No speech detected',
                    'transcript': '',
                    'confidence': 0.0,
                    'language': language_code,
                    'service_type': 'google_cloud_speech'
                }
                
        except google_exceptions.GoogleAPIError as e:
            logger.error("Google API error in speech recognition", error=str(e))
            return {
                'success': False,
                'error': f'Google API error: {str(e)}',
                'transcript': '',
                'confidence': 0.0
            }
        except Exception as e:
            logger.error("Error in speech recognition", error=str(e))
            return {
                'success': False,
                'error': f'Recognition error: {str(e)}',
                'transcript': '',
                'confidence': 0.0
            }

    async def translate_text(
        self, 
        text: str, 
        target_language: str = "en",
        source_language: str = None
    ) -> Dict[str, Any]:
        """
        Translate text using Google Cloud Translation API
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (None for auto-detect)
            
        Returns:
            Dict containing translation results
        """
        if not self.is_initialized:
            logger.error("Google Cloud client not initialized")
            return {'error': 'Client not initialized'}
        
        try:
            # Translate text
            if source_language:
                result = self.translate_client.translate(
                    text, 
                    target_language=target_language,
                    source_language=source_language
                )
            else:
                result = self.translate_client.translate(
                    text, 
                    target_language=target_language
                )
            
            return {
                'original_text': text,
                'translated_text': result['translatedText'],
                'source_language': result['detectedSourceLanguage'],
                'target_language': target_language,
                'service_type': 'google_cloud_translate',
                'success': True
            }
            
        except Exception as e:
            logger.error("Error in translation", error=str(e))
            return {
                'error': str(e),
                'success': False
            }
    
    async def synthesize_speech(
        self, 
        text: str, 
        language_code: str = "en-US",
        voice_name: str = None,
        gender: str = "NEUTRAL"
    ) -> Optional[bytes]:
        """
        Synthesize speech using Google Cloud Text-to-Speech
        
        Args:
            text: Text to synthesize
            language_code: Language and region code
            voice_name: Specific voice name (optional)
            gender: Voice gender (MALE, FEMALE, NEUTRAL)
            
        Returns:
            Audio data in bytes or None if failed
        """
        if not self.is_initialized:
            logger.error("Google Cloud client not initialized")
            return None
        
        try:
            # Configure voice
            if voice_name:
                voice = texttospeech.VoiceSelectionParams(
                    name=voice_name,
                    language_code=language_code
                )
            else:
                voice = texttospeech.VoiceSelectionParams(
                    language_code=language_code,
                    ssml_gender=getattr(texttospeech.SsmlVoiceGender, gender)
                )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # Create synthesis request
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Perform synthesis
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            logger.info("Speech synthesis successful", 
                       text_length=len(text),
                       language_code=language_code)
            
            return response.audio_content
            
        except Exception as e:
            logger.error("Error in speech synthesis", error=str(e))
            return None
    
    async def get_supported_languages(self) -> Dict[str, List[str]]:
        """Get supported languages for each service"""
        if not self.is_initialized:
            return {}
        
        try:
            # Get translation languages
            translate_languages = self.translate_client.get_languages()
            
            # Get TTS voices
            tts_voices = self.tts_client.list_voices()
            
            return {
                'translation_languages': [lang['language'] for lang in translate_languages],
                'tts_languages': list(set(voice.language_codes[0] for voice in tts_voices.voices)),
                'speech_languages': [
                    'en-US', 'es-ES', 'fr-FR', 'de-DE', 'ja-JP', 'zh-CN', 'ar-SA', 'hi-IN', 'pt-BR'
                ]  # Common speech recognition languages
            }
            
        except Exception as e:
            logger.error("Error getting supported languages", error=str(e))
            return {}
    
    async def cleanup(self):
        """Clean up resources and close connections"""
        try:
            # Stop all active streaming sessions
            for session_id in list(self.streaming_sessions.keys()):
                await self.stop_streaming_recognition(session_id)
            
            # Close clients if needed
            if self.speech_client:
                self.speech_client.close()
            if self.tts_client:
                self.tts_client.close()
            
            self.is_initialized = False
            logger.info("Google Cloud client cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e)) 