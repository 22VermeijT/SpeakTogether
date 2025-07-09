"""
Google Cloud API Client for SpeakTogether
Handles real integration with Google Cloud Speech-to-Text, Translation, and Text-to-Speech APIs
"""

import os
import asyncio
from typing import Dict, Any, Optional
import structlog

# Google Cloud imports
from google.cloud import speech, translate, texttospeech
from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError

logger = structlog.get_logger()


class GoogleCloudClient:
    """Client for Google Cloud APIs used in SpeakTogether"""
    
    def __init__(self):
        self.speech_client = None
        self.translate_client = None
        self.tts_client = None
        self.credentials = None
        self.project_id = None
        
    async def initialize(self):
        """Initialize Google Cloud clients"""
        try:
            # Get credentials from environment
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            
            if not credentials_path or not os.path.exists(credentials_path):
                raise ValueError(f"Google credentials file not found: {credentials_path}")
            
            if not self.project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT not set")
            
            # Load credentials
            self.credentials = service_account.Credentials.from_service_account_file(credentials_path)
            
            # Initialize clients
            self.speech_client = speech.SpeechClient(credentials=self.credentials)
            self.translate_client = translate.TranslationServiceClient(credentials=self.credentials)
            self.tts_client = texttospeech.TextToSpeechClient(credentials=self.credentials)
            
            logger.info("Google Cloud clients initialized successfully", 
                       project_id=self.project_id)
            
        except Exception as e:
            logger.error("Failed to initialize Google Cloud clients", error=str(e))
            raise
    
    async def speech_to_text(self, audio_data: bytes, language_code: str = "en-US") -> Dict[str, Any]:
        """Convert speech to text using Google Cloud Speech-to-Text"""
        try:
            # Configure recognition
            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model="latest_long"
            )
            
            # Perform recognition
            response = self.speech_client.recognize(config=config, audio=audio)
            
            if not response.results:
                return {
                    'transcript': '',
                    'language': language_code,
                    'confidence': 0.0,
                    'success': False,
                    'error': 'No speech detected'
                }
            
            # Get the best result
            result = response.results[0]
            transcript = result.alternatives[0].transcript
            confidence = result.alternatives[0].confidence
            
            return {
                'transcript': transcript,
                'language': language_code,
                'confidence': confidence,
                'success': True,
                'word_count': len(transcript.split())
            }
            
        except GoogleCloudError as e:
            logger.error("Google Cloud Speech-to-Text error", error=str(e))
            return {
                'transcript': '',
                'language': language_code,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error("Unexpected error in speech-to-text", error=str(e))
            return {
                'transcript': '',
                'language': language_code,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
    
    async def translate_text(self, text: str, target_language: str = "en", 
                           source_language: str = "auto") -> Dict[str, Any]:
        """Translate text using Google Cloud Translation API"""
        try:
            # Try service account first, fallback to API key
            parent = f"projects/{self.project_id}"
            
            # Handle auto-detection
            if source_language == "auto":
                try:
                    # First detect the language
                    detect_request = translate.DetectLanguageRequest(
                        parent=parent,
                        content=text
                    )
                    detect_response = self.translate_client.detect_language(request=detect_request)
                    detected_language = detect_response.languages[0].language_code
                except Exception as e:
                    logger.warning("Language detection failed, using English as default", error=str(e))
                    detected_language = "en"
            else:
                detected_language = source_language
            
            # Translate the text
            translate_request = translate.TranslateTextRequest(
                parent=parent,
                contents=[text],
                mime_type="text/plain",
                source_language_code=detected_language,
                target_language_code=target_language
            )
            
            response = self.translate_client.translate_text(request=translate_request)
            
            translated_text = response.translations[0].translated_text
            
            return {
                'translation': translated_text,
                'source_language': detected_language,
                'target_language': target_language,
                'confidence': 0.95,  # Google doesn't provide confidence for translation
                'success': True,
                'original_text': text
            }
            
        except GoogleCloudError as e:
            logger.error("Google Cloud Translation error", error=str(e))
            return {
                'translation': text,  # Return original text on error
                'source_language': source_language,
                'target_language': target_language,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error("Unexpected error in translation", error=str(e))
            return {
                'translation': text,  # Return original text on error
                'source_language': source_language,
                'target_language': target_language,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
    
    async def text_to_speech(self, text: str, voice_name: str = "en-US-Neural2-C",
                            language_code: str = "en-US") -> Dict[str, Any]:
        """Convert text to speech using Google Cloud Text-to-Speech"""
        try:
            # Configure the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure the voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # Configure the audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000
            )
            
            # Perform the synthesis
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Convert audio content to base64 for transmission
            import base64
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            
            return {
                'audio_data': audio_base64,
                'voice_name': voice_name,
                'language_code': language_code,
                'duration_seconds': len(text.split()) * 0.6,  # Rough estimate
                'success': True,
                'audio_format': 'wav',
                'sample_rate': 24000
            }
            
        except GoogleCloudError as e:
            logger.error("Google Cloud Text-to-Speech error", error=str(e))
            return {
                'audio_data': '',
                'voice_name': voice_name,
                'language_code': language_code,
                'duration_seconds': 0,
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error("Unexpected error in text-to-speech", error=str(e))
            return {
                'audio_data': '',
                'voice_name': voice_name,
                'language_code': language_code,
                'duration_seconds': 0,
                'success': False,
                'error': str(e)
            }
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect the language of text using Google Cloud Translation API"""
        try:
            parent = f"projects/{self.project_id}"
            request = translate.DetectLanguageRequest(
                parent=parent,
                content=text
            )
            
            response = self.translate_client.detect_language(request=request)
            
            # Get the most likely language
            detected_language = response.languages[0]
            
            return {
                'detected_language': {
                    'code': detected_language.language_code,
                    'confidence': detected_language.confidence,
                    'name': detected_language.language_code.upper()
                },
                'alternatives': [
                    {
                        'code': lang.language_code,
                        'confidence': lang.confidence,
                        'name': lang.language_code.upper()
                    }
                    for lang in response.languages[:3]  # Top 3 alternatives
                ],
                'success': True
            }
            
        except GoogleCloudError as e:
            logger.error("Google Cloud language detection error", error=str(e))
            return {
                'detected_language': {'code': 'en', 'confidence': 0.0, 'name': 'EN'},
                'alternatives': [],
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error("Unexpected error in language detection", error=str(e))
            return {
                'detected_language': {'code': 'en', 'confidence': 0.0, 'name': 'EN'},
                'alternatives': [],
                'success': False,
                'error': str(e)
            }
    
    async def shutdown(self):
        """Shutdown Google Cloud clients"""
        logger.info("Shutting down Google Cloud clients")
        self.speech_client = None
        self.translate_client = None
        self.tts_client = None
        self.credentials = None 