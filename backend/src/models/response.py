"""
Response models for SpeakTogether API
Standardized response formats for REST and WebSocket communication
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ResponseStatus(str, Enum):
    """Response status enumeration"""
    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"
    PARTIAL = "partial"


class BaseResponse(BaseModel):
    """Base response model"""
    status: ResponseStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    message: str


class SuccessResponse(BaseResponse):
    """Success response model"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseResponse):
    """Error response model"""
    status: ResponseStatus = ResponseStatus.ERROR
    error_code: Optional[str] = None
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    uptime: float
    agents_status: Dict[str, bool]
    active_sessions: int


class AudioProcessingResult(BaseModel):
    """Audio processing result from agents"""
    session_id: str
    transcript: Optional[str] = None
    translation: Optional[str] = None
    confidence: float
    language_detected: Optional[str] = None
    processing_time_ms: int
    agent_decisions: Dict[str, Any]


class AgentDecision(BaseModel):
    """Individual agent decision information"""
    agent_name: str
    decision: str
    confidence: float
    reasoning: str
    processing_time_ms: int
    metadata: Optional[Dict[str, Any]] = None


class AgentStatus(BaseModel):
    """Real-time agent status for dashboard"""
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    agents: Dict[str, AgentDecision]
    overall_confidence: float
    current_context: str
    processing_pipeline: List[str]


class TranslationRequest(BaseModel):
    """Translation request model"""
    text: str
    source_language: str = "auto"
    target_language: str = "en"
    context: Optional[str] = None
    style: Optional[str] = "neutral"  # formal, casual, neutral


class TranslationResponse(BaseModel):
    """Translation response model"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    style_applied: str
    processing_time_ms: int


class AudioContextInfo(BaseModel):
    """Audio context information from Audio Context Agent"""
    source_type: str  # zoom, youtube, spotify, system
    audio_quality: float  # 0-1 scale
    speaker_count: int
    noise_level: float
    priority: str  # high, medium, low
    recommended_processing: str


class VoiceSynthesisRequest(BaseModel):
    """Voice synthesis request"""
    text: str
    target_language: str
    voice_characteristics: Optional[Dict[str, str]] = None  # gender, age, accent
    emotion: Optional[str] = "neutral"
    speed: float = 1.0


class VoiceSynthesisResponse(BaseModel):
    """Voice synthesis response"""
    audio_data: bytes
    duration_seconds: float
    voice_used: str
    synthesis_time_ms: int


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str  # audio_result, agent_status, error, ping
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Union[
        AudioProcessingResult,
        AgentStatus,
        ErrorResponse,
        Dict[str, Any]
    ]


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    user_preferences: Dict[str, Any]
    active_languages: List[str]
    start_time: datetime
    last_activity: datetime
    processing_stats: Dict[str, Any] 