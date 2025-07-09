"""
SpeakTogether Backend (Real Audio Version)
FastAPI backend with PyAudio real-time audio capture integration
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any
import structlog

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import our audio modules
from src.audio import PyAudioCapture, AudioStreamHandler

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Pydantic models
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Dict[str, Any] = {}

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: str = ""

# Simple connection manager for WebSockets
class SimpleConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("WebSocket connected", session_id=session_id)
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("WebSocket disconnected", session_id=session_id)
    
    async def send_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
                return True
            except Exception as e:
                logger.error("Failed to send message", session_id=session_id, error=str(e))
                self.disconnect(session_id)
                return False
        return False
    
    async def send_error(self, session_id: str, error: str):
        await self.send_to_session(session_id, {
            "type": "error",
            "message": error,
            "timestamp": time.time()
        })

# Enhanced mock orchestrator with real audio processing
class MockOrchestrator:
    def __init__(self):
        self.is_active = False
        self.audio_handler: AudioStreamHandler = None
        self.logger = structlog.get_logger(__name__)
        
        # Add Google Cloud integration flag
        self.google_cloud_enabled = False
        try:
            # Check if Google Cloud credentials are available
            import os
            if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and os.getenv('GOOGLE_CLOUD_PROJECT'):
                self.google_cloud_enabled = True
                self.logger.info("Google Cloud integration enabled")
            else:
                self.logger.info("Google Cloud integration disabled - credentials not found")
        except Exception as e:
            self.logger.warning("Google Cloud integration check failed", error=str(e))

    async def initialize(self):
        """Initialize the orchestrator with audio handler"""
        self.is_active = True
        self.audio_handler = AudioStreamHandler()
        logger.info("Mock orchestrator with PyAudio initialized")
    
    async def shutdown(self):
        """Shutdown orchestrator and clean up audio resources"""
        self.is_active = False
        if self.audio_handler:
            await self.audio_handler.cleanup()
        logger.info("Mock orchestrator shutdown")
    
    async def process_audio_chunk(self, session_id: str, audio_info: Dict[str, Any]):
        """
        Process real audio chunk information
        This replaces the old process_audio_stream method
        """
        # Mock transcription based on real audio
        volume_percent = audio_info.get('audio_metrics', {}).get('volume_percent', 0)
        
        # Simulate speech detection based on volume
        if volume_percent > 10:  # Some audio detected
            transcription_text = f"[Audio detected: {volume_percent:.1f}% volume]"
            confidence = min(0.95, volume_percent / 100.0 + 0.5)
        else:
            transcription_text = "[Silence]"
            confidence = 0.1
        
        return {
            "type": "transcription",
            "text": transcription_text,
            "timestamp": time.time(),
            "confidence": confidence,
            "audio_info": audio_info
        }
    
    async def get_agent_status(self, session_id: str):
        """Get status of all AI agents"""
        audio_session_active = False
        if self.audio_handler:
            status = await self.audio_handler.get_session_status(session_id)
            audio_session_active = status is not None and status.get('is_active', False)
        
        return {
            "agents": {
                "audio_context": {
                    "status": "active" if audio_session_active else "ready", 
                    "processing": audio_session_active
                },
                "translation": {"status": "ready", "processing": False},
                "quality_control": {"status": "monitoring", "processing": False},
                "voice_synthesis": {"status": "ready", "processing": False}
            },
            "session_id": session_id,
            "timestamp": time.time()
        }

    async def process_with_google_cloud(self, audio_data: bytes, session_id: str) -> Dict[str, Any]:
        """Process audio using real Google Cloud APIs if available"""
        try:
            if not self.google_cloud_enabled:
                return await self.process_audio_mock(audio_data, session_id)
            
            # Import Google Cloud client
            from src.google_cloud_client import GoogleCloudClient
            
            # Initialize client if not already done
            if not hasattr(self, 'google_client'):
                self.google_client = GoogleCloudClient()
                await self.google_client.initialize()
                self.logger.info("Google Cloud client initialized")
            
            # Process with real Google Cloud Speech-to-Text
            speech_result = await self.google_client.speech_to_text(audio_data)
            
            if speech_result['success'] and speech_result['transcript'].strip():
                # If we have a successful transcription, optionally translate
                translation_result = None
                
                # Simple auto-translation logic - translate if not English
                detected_lang = speech_result.get('language', 'en-US')
                if not detected_lang.startswith('en'):
                    translation_result = await self.google_client.translate_text(
                        text=speech_result['transcript'],
                        target_language='en',
                        source_language='auto'
                    )
                
                return {
                    "session_id": session_id,
                    "transcript": speech_result['transcript'],
                    "translation": translation_result['translation'] if translation_result and translation_result['success'] else None,
                    "confidence": speech_result['confidence'],
                    "language_detected": speech_result['language'],
                    "processing_time_ms": 0,  # Will be calculated by caller
                    "agent_decisions": {
                        "google_cloud": True,
                        "speech_success": speech_result['success'],
                        "translation_attempted": translation_result is not None,
                        "translation_success": translation_result and translation_result['success'] if translation_result else False
                    },
                    "service_type": "google_cloud_real"
                }
            else:
                # Fall back to mock if no speech detected
                return await self.process_audio_mock(audio_data, session_id)
                
        except Exception as e:
            self.logger.error("Google Cloud processing failed, falling back to mock", 
                            session_id=session_id, error=str(e))
            return await self.process_audio_mock(audio_data, session_id)

    async def process_audio_stream(self, audio_data: bytes, session_id: str = None) -> Dict[str, Any]:
        """Enhanced audio processing with Google Cloud integration"""
        if session_id is None:
            session_id = f"session_{int(time.time())}"
            
        start_time = time.time()
        
        try:
            # Try Google Cloud processing first if available, otherwise use mock
            result = await self.process_with_google_cloud(audio_data, session_id)
            
            processing_time = int((time.time() - start_time) * 1000)
            result["processing_time_ms"] = processing_time
            
            self.logger.info("Audio processed successfully", 
                           session_id=session_id,
                           service=result.get("service_type", "unknown"),
                           transcript_length=len(result.get("transcript", "")),
                           confidence=result.get("confidence", 0),
                           processing_time=processing_time)
            
            return result
            
        except Exception as e:
            self.logger.error("Audio processing failed", session_id=session_id, error=str(e))
            return self._create_error_result(session_id, str(e))

# Global instances
connection_manager = SimpleConnectionManager()
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global orchestrator
    
    # Startup
    logger.info("Starting SpeakTogether backend with PyAudio support")
    try:
        orchestrator = MockOrchestrator()
        await orchestrator.initialize()
        logger.info("PyAudio orchestrator initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize orchestrator", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down SpeakTogether backend")
    if orchestrator:
        await orchestrator.shutdown()

# Create FastAPI app
app = FastAPI(
    title="SpeakTogether API (PyAudio)",
    description="AI-Powered Real-Time Audio Captions & Translation System - With Real Audio Capture",
    version="0.2.0-pyaudio",
    docs_url="/docs",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=SuccessResponse)
async def root():
    """Root endpoint"""
    return SuccessResponse(
        message="SpeakTogether API is running with PyAudio support",
        data={
            "version": "0.2.0-pyaudio",
            "status": "healthy",
            "agents_active": orchestrator.is_active if orchestrator else False,
            "pyaudio_available": True
        }
    )

@app.get("/api/v1/health", response_model=SuccessResponse)
async def health_check():
    """Health check endpoint"""
    audio_stats = {}
    if orchestrator and orchestrator.audio_handler:
        sessions = await orchestrator.audio_handler.list_active_sessions()
        audio_stats = sessions.get('global_stats', {})
    
    return SuccessResponse(
        message="Service is healthy",
        data={
            "status": "ok",
            "orchestrator": "active" if orchestrator and orchestrator.is_active else "inactive",
            "audio_stats": audio_stats
        }
    )

@app.websocket("/ws/audio-stream/{session_id}")
async def websocket_audio_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio streaming with PyAudio"""
    await connection_manager.connect(websocket, session_id)
    
    # Create WebSocket callback for audio handler
    async def websocket_callback(message: dict):
        return await connection_manager.send_to_session(session_id, message)
    
    try:
        while True:
            # Receive message from frontend
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
            except json.JSONDecodeError:
                await connection_manager.send_error(session_id, "Invalid JSON message")
                continue
            
            logger.info("Received WebSocket message", 
                       session_id=session_id, 
                       message_type=message.get('type'))
            
            print(f"🎤 DEBUG: Received message: {message}")  # Debug output
            
            # Handle audio control messages
            if orchestrator and orchestrator.audio_handler:
                print(f"🎤 DEBUG: Passing to audio handler: {message.get('type')}")
                # Handle audio-specific messages
                handled = await orchestrator.audio_handler.handle_websocket_message(
                    session_id, message, websocket_callback
                )
                print(f"🎤 DEBUG: Audio handler result: {handled}")
                if handled:
                    continue
            
            # Handle other message types
            message_type = message.get('type')
            
            if message_type == 'start_capture':
                # Start audio capture using PyAudio
                if orchestrator and orchestrator.audio_handler:
                    
                    # Create custom callback for audio data processing
                    async def audio_processing_callback(audio_message: dict):
                        # Process audio chunk through orchestrator
                        if audio_message.get('type') == 'audio_chunk':
                            result = await orchestrator.process_audio_chunk(
                                session_id, audio_message
                            )
                            # Send transcription result
                            await websocket_callback(result)
                        
                        # Also send the original audio message
                        await websocket_callback(audio_message)
                    
                    # Start audio session
                    success = await orchestrator.audio_handler.start_audio_session(
                        session_id, 
                        audio_processing_callback,
                        message.get('audio_config', {})
                    )
                    
                    if not success:
                        await connection_manager.send_error(
                            session_id, 
                            "Failed to start audio capture"
                        )
                else:
                    await connection_manager.send_error(
                        session_id, 
                        "Audio handler not available"
                    )
            
            elif message_type == 'stop_capture':
                # Stop audio capture
                if orchestrator and orchestrator.audio_handler:
                    await orchestrator.audio_handler.stop_audio_session(session_id)
            
            elif message_type == 'ping':
                # Respond to ping
                await websocket_callback({
                    'type': 'pong',
                    'timestamp': time.time()
                })
            
            else:
                logger.warning("Unknown message type", 
                              session_id=session_id, 
                              message_type=message_type)
                await connection_manager.send_error(
                    session_id, 
                    f"Unknown message type: {message_type}"
                )
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
        # Stop audio session if active
        if orchestrator and orchestrator.audio_handler:
            await orchestrator.audio_handler.stop_audio_session(session_id)
        connection_manager.disconnect(session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        await connection_manager.send_error(session_id, f"Server error: {str(e)}")

@app.websocket("/ws/agent-dashboard/{session_id}")
async def websocket_agent_dashboard(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent decision monitoring"""
    await connection_manager.connect(websocket, f"dashboard_{session_id}")
    
    try:
        while True:
            # Send agent status updates
            if orchestrator:
                agent_status = await orchestrator.get_agent_status(session_id)
                await connection_manager.send_to_session(
                    f"dashboard_{session_id}", 
                    agent_status
                )
            
            await asyncio.sleep(1)  # Update every second
            
    except WebSocketDisconnect:
        logger.info("Agent dashboard disconnected", session_id=session_id)
        connection_manager.disconnect(f"dashboard_{session_id}")
    except Exception as e:
        logger.error("Agent dashboard error", session_id=session_id, error=str(e))

@app.get("/api/v1/audio/sessions")
async def get_audio_sessions():
    """Get information about active audio sessions"""
    if orchestrator and orchestrator.audio_handler:
        sessions = await orchestrator.audio_handler.list_active_sessions()
        return SuccessResponse(
            message="Audio sessions retrieved",
            data=sessions
        )
    else:
        return ErrorResponse(
            message="Audio handler not available",
            details="Orchestrator or audio handler not initialized"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            details=str(exc)
        ).dict()
    )

@app.get("/api/version")
async def get_version():
    """Get API version and service status"""
    try:
        # Check Google Cloud status
        google_cloud_status = False
        if hasattr(orchestrator, 'google_cloud_enabled'):
            google_cloud_status = orchestrator.google_cloud_enabled
            
        # Check PyAudio status  
        pyaudio_status = False
        try:
            import pyaudio
            pyaudio_status = True
        except ImportError:
            pyaudio_status = False
            
        return {
            "version": "0.3.0-unified", 
            "service": "SpeakTogether Unified API",
            "status": "running",
            "features": {
                "pyaudio_available": pyaudio_status,
                "google_cloud_available": google_cloud_status,
                "real_audio_capture": pyaudio_status,
                "real_transcription": google_cloud_status,
                "real_translation": google_cloud_status
            },
            "audio_devices": await get_audio_devices() if pyaudio_status else []
        }
    except Exception as e:
        return {
            "version": "0.3.0-unified",
            "service": "SpeakTogether Unified API", 
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Print PyAudio availability
    try:
        from src.audio.capture import PYAUDIO_AVAILABLE
        if PYAUDIO_AVAILABLE:
            print("✅ PyAudio is available - real audio capture enabled")
        else:
            print("❌ PyAudio not available - install with: pip install pyaudio")
    except ImportError:
        print("❌ Audio modules not found")
    
    uvicorn.run(
        "main_simple_with_pyaudio:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 