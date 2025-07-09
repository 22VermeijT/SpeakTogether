"""
Translation API endpoints for SpeakTogether
Handles text translation requests and language detection
"""

import asyncio
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.response import SuccessResponse, ErrorResponse, TranslationRequest, TranslationResponse
from ..config import settings

router = APIRouter()


class BatchTranslationRequest(BaseModel):
    """Request model for batch translation"""
    texts: List[str]
    source_language: str = "auto"
    target_language: str = "en"
    context: Optional[str] = None
    style: Optional[str] = "neutral"


class LanguageDetectionRequest(BaseModel):
    """Request model for language detection"""
    text: str


@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Translate a single text string
    Uses the translation strategy agent for context-aware translation
    """
    try:
        start_time = time.time()
        
        # Validate input
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(request.text) > settings.MAX_TRANSLATION_LENGTH:
            raise HTTPException(
                status_code=400, 
                detail=f"Text exceeds maximum length of {settings.MAX_TRANSLATION_LENGTH} characters"
            )
        
        # Simulate translation processing (in production, would use Google Translate API)
        translated_text = await _perform_translation(
            request.text, 
            request.source_language, 
            request.target_language,
            request.context,
            request.style
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return TranslationResponse(
            original_text=request.text,
            translated_text=translated_text,
            source_language=request.source_language if request.source_language != "auto" else "en",
            target_language=request.target_language,
            confidence=0.92,
            style_applied=request.style or "neutral",
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation error: {str(e)}"
        )


@router.post("/translate/batch", response_model=SuccessResponse)
async def translate_batch(request: BatchTranslationRequest):
    """
    Translate multiple texts in a single request
    Optimized for bulk processing
    """
    try:
        start_time = time.time()
        
        # Validate input
        if not request.texts or len(request.texts) == 0:
            raise HTTPException(status_code=400, detail="Texts list cannot be empty")
        
        if len(request.texts) > 100:  # Limit batch size
            raise HTTPException(status_code=400, detail="Batch size cannot exceed 100 texts")
        
        # Process translations
        translations = []
        for i, text in enumerate(request.texts):
            if text and len(text.strip()) > 0:
                translated_text = await _perform_translation(
                    text,
                    request.source_language,
                    request.target_language,
                    request.context,
                    request.style
                )
                
                translations.append({
                    "index": i,
                    "original_text": text,
                    "translated_text": translated_text,
                    "confidence": 0.89
                })
            else:
                translations.append({
                    "index": i,
                    "original_text": text,
                    "translated_text": "",
                    "confidence": 0.0,
                    "error": "Empty text"
                })
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return SuccessResponse(
            message=f"Batch translation completed for {len(request.texts)} texts",
            data={
                "translations": translations,
                "source_language": request.source_language,
                "target_language": request.target_language,
                "processing_time_ms": processing_time,
                "success_count": len([t for t in translations if "error" not in t]),
                "error_count": len([t for t in translations if "error" in t])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch translation error: {str(e)}"
        )


@router.post("/detect-language", response_model=SuccessResponse)
async def detect_language(request: LanguageDetectionRequest):
    """
    Detect the language of input text
    """
    try:
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Simulate language detection (in production, would use Google Cloud Translation API)
        detected_language = await _detect_text_language(request.text)
        
        return SuccessResponse(
            message="Language detected successfully",
            data=detected_language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Language detection error: {str(e)}"
        )


@router.get("/translation-styles", response_model=SuccessResponse)
async def get_translation_styles():
    """
    Get available translation styles and their descriptions
    """
    styles = {
        "formal_business": {
            "name": "Formal Business",
            "description": "Professional tone suitable for business communications",
            "use_cases": ["Business meetings", "Corporate presentations", "Official documents"]
        },
        "casual_conversation": {
            "name": "Casual Conversation", 
            "description": "Natural, informal tone for everyday conversations",
            "use_cases": ["Social interactions", "Personal conversations", "Informal discussions"]
        },
        "educational_clear": {
            "name": "Educational Clear",
            "description": "Clear, accessible language for learning and instruction",
            "use_cases": ["Educational content", "Training materials", "Tutorials"]
        },
        "technical_expert": {
            "name": "Technical Expert",
            "description": "Precise terminology for technical and specialized content",
            "use_cases": ["Technical documentation", "Scientific papers", "Expert discussions"]
        },
        "neutral": {
            "name": "Neutral",
            "description": "Balanced tone suitable for general purposes",
            "use_cases": ["General content", "Mixed audiences", "Uncertain context"]
        }
    }
    
    return SuccessResponse(
        message="Translation styles retrieved",
        data={"styles": styles}
    )


@router.get("/quality-metrics/{session_id}", response_model=SuccessResponse)
async def get_translation_quality_metrics(session_id: str):
    """
    Get quality metrics for a translation session
    """
    # In production, this would query the quality control agent
    quality_metrics = {
        "session_id": session_id,
        "overall_score": 0.87,
        "metrics": {
            "fluency": 0.91,
            "accuracy": 0.85,
            "adequacy": 0.89,
            "cultural_appropriateness": 0.83
        },
        "language_pair": {
            "source": "es",
            "target": "en"
        },
        "processing_stats": {
            "total_segments": 45,
            "high_confidence": 38,
            "medium_confidence": 6,
            "low_confidence": 1,
            "average_processing_time_ms": 156
        },
        "agent_assessments": {
            "translation_strategy": {
                "style_consistency": 0.94,
                "terminology_preservation": 0.88
            },
            "quality_control": {
                "error_detection": 0.92,
                "recommendation": "accept"
            }
        }
    }
    
    return SuccessResponse(
        message="Quality metrics retrieved",
        data=quality_metrics
    )


async def _perform_translation(
    text: str, 
    source_lang: str, 
    target_lang: str, 
    context: Optional[str] = None,
    style: Optional[str] = None
) -> str:
    """
    Perform actual translation (simplified for hackathon)
    In production, this would integrate with Google Cloud Translation API
    """
    # Simulate processing delay
    await asyncio.sleep(0.05)
    
    # Simple mock translation
    if source_lang == "es" and target_lang == "en":
        return f"[Translated from Spanish]: {text}"
    elif source_lang == "fr" and target_lang == "en":
        return f"[Translated from French]: {text}"
    elif source_lang == "auto" or source_lang == "en":
        return f"[English text]: {text}"
    else:
        return f"[Translated from {source_lang} to {target_lang}]: {text}"


async def _detect_text_language(text: str) -> dict:
    """
    Detect the language of input text (simplified for hackathon)
    In production, this would use Google Cloud Translation API
    """
    # Simulate processing delay
    await asyncio.sleep(0.02)
    
    # Simple language detection based on common words
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["the", "and", "this", "that", "with"]):
        detected = {"code": "en", "name": "English", "confidence": 0.95}
    elif any(word in text_lower for word in ["el", "la", "es", "con", "que"]):
        detected = {"code": "es", "name": "Spanish", "confidence": 0.92}
    elif any(word in text_lower for word in ["le", "la", "est", "avec", "que"]):
        detected = {"code": "fr", "name": "French", "confidence": 0.89}
    else:
        detected = {"code": "en", "name": "English", "confidence": 0.60}
    
    return {
        "detected_language": detected,
        "alternatives": [
            {"code": "en", "name": "English", "confidence": 0.95},
            {"code": "es", "name": "Spanish", "confidence": 0.03},
            {"code": "fr", "name": "French", "confidence": 0.02}
        ],
        "text_sample": text[:100] + "..." if len(text) > 100 else text
    } 