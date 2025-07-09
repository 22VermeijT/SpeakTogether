"""
Simple translation fallback using API key
"""

import os
import requests
from typing import Dict, Any
import structlog

logger = structlog.get_logger()


class SimpleTranslationClient:
    """Simple translation client using API key"""
    
    def __init__(self):
        self.api_key = os.getenv('ADK_API_KEY')  # Using the same API key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
    
    async def translate_text(self, text: str, target_language: str = "en", 
                           source_language: str = "auto") -> Dict[str, Any]:
        """Translate text using Google Translation API with API key"""
        try:
            params = {
                'key': self.api_key,
                'q': text,
                'target': target_language,
                'format': 'text'
            }
            
            if source_language != "auto":
                params['source'] = source_language
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            translated_text = data['data']['translations'][0]['translatedText']
            
            return {
                'translation': translated_text,
                'source_language': source_language,
                'target_language': target_language,
                'confidence': 0.95,
                'success': True,
                'original_text': text
            }
            
        except Exception as e:
            logger.error("Simple translation failed", error=str(e))
            return {
                'translation': text,  # Return original text on error
                'source_language': source_language,
                'target_language': target_language,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language using Google Translation API with API key"""
        try:
            detect_url = "https://translation.googleapis.com/language/translate/v2/detect"
            params = {
                'key': self.api_key,
                'q': text
            }
            
            response = requests.get(detect_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            detected_language = data['data']['detections'][0][0]
            
            return {
                'detected_language': {
                    'code': detected_language['language'],
                    'confidence': detected_language['confidence'],
                    'name': detected_language['language'].upper()
                },
                'alternatives': [],
                'success': True
            }
            
        except Exception as e:
            logger.error("Simple language detection failed", error=str(e))
            return {
                'detected_language': {'code': 'en', 'confidence': 0.0, 'name': 'EN'},
                'alternatives': [],
                'success': False,
                'error': str(e)
            } 