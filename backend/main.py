"""
SpeakTogether Backend - Main Application Entry Point
AI-Powered Real-Time Audio Captions & Translation System
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List

import structlog
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.agents.orchestrator import MasterOrchestrator
from src.websocket.connection_manager import ConnectionManager
from src.api import audio, translation, health
from src.models.response import ErrorResponse, SuccessResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
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
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global instances
connection_manager = ConnectionManager()
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global orchestrator
    
    # Startup
    logger.info("Starting SpeakTogether backend", version=settings.APP_VERSION)
    try:
        orchestrator = MasterOrchestrator()
        await orchestrator.initialize()
        logger.info("Orchestrator initialized successfully")
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
    title="SpeakTogether API",
    description="AI-Powered Real-Time Audio Captions & Translation System",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(audio.router, prefix="/api/v1", tags=["audio"])
app.include_router(translation.router, prefix="/api/v1", tags=["translation"])

@app.websocket("/ws/audio-stream/{session_id}")
async def websocket_audio_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio streaming and processing"""
    await connection_manager.connect(websocket, session_id)
    logger.info("WebSocket connected", session_id=session_id)
    
    try:
        while True:
            # Receive audio data from frontend
            data = await websocket.receive_bytes()
            
            # Process audio through agent orchestrator
            if orchestrator:
                result = await orchestrator.process_audio_stream(
                    audio_data=data,
                    session_id=session_id
                )
                
                # Send processed result back to frontend
                await connection_manager.send_to_session(session_id, result)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
        connection_manager.disconnect(session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        await connection_manager.send_error(session_id, str(e))

@app.websocket("/ws/agent-dashboard/{session_id}")
async def websocket_agent_dashboard(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent decision monitoring"""
    await connection_manager.connect(websocket, f"dashboard_{session_id}")
    logger.info("Agent dashboard connected", session_id=session_id)
    
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

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", 
                path=str(request.url), 
                method=request.method,
                error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            details=str(exc) if settings.DEBUG else "An unexpected error occurred"
        ).dict()
    )

@app.get("/", response_model=SuccessResponse)
async def root():
    """Root endpoint"""
    return SuccessResponse(
        message="SpeakTogether API is running",
        data={
            "version": settings.APP_VERSION,
            "status": "healthy",
            "agents_active": orchestrator.is_active if orchestrator else False
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    ) 