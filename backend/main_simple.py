"""
SpeakTogether Backend - Simplified Version for Testing
AI-Powered Real-Time Audio Captions & Translation System
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Simple response models
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
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except:
                self.disconnect(session_id)
    
    async def send_error(self, session_id: str, error: str):
        await self.send_to_session(session_id, {
            "type": "error",
            "message": error
        })

# Mock orchestrator for testing
class MockOrchestrator:
    def __init__(self):
        self.is_active = False
    
    async def initialize(self):
        self.is_active = True
        print("Mock orchestrator initialized")
    
    async def shutdown(self):
        self.is_active = False
        print("Mock orchestrator shutdown")
    
    async def process_audio_stream(self, audio_data: bytes, session_id: str):
        # Mock processing - just return a simple response
        return {
            "type": "transcription",
            "text": f"Mock transcription for session {session_id}",
            "timestamp": asyncio.get_event_loop().time(),
            "confidence": 0.95
        }
    
    async def get_agent_status(self, session_id: str):
        return {
            "agents": {
                "audio_context": {"status": "active", "processing": True},
                "translation": {"status": "ready", "processing": False},
                "quality_control": {"status": "monitoring", "processing": False},
                "voice_synthesis": {"status": "ready", "processing": False}
            },
            "session_id": session_id,
            "timestamp": asyncio.get_event_loop().time()
        }

# Global instances
connection_manager = SimpleConnectionManager()
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global orchestrator
    
    # Startup
    print("Starting SpeakTogether backend (simplified version)")
    try:
        orchestrator = MockOrchestrator()
        await orchestrator.initialize()
        print("Mock orchestrator initialized successfully")
    except Exception as e:
        print(f"Failed to initialize orchestrator: {e}")
        raise
    
    yield
    
    # Shutdown
    print("Shutting down SpeakTogether backend")
    if orchestrator:
        await orchestrator.shutdown()

# Create FastAPI app
app = FastAPI(
    title="SpeakTogether API (Simplified)",
    description="AI-Powered Real-Time Audio Captions & Translation System - Testing Version",
    version="0.1.0-simple",
    docs_url="/docs",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Simplified for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=SuccessResponse)
async def root():
    """Root endpoint"""
    return SuccessResponse(
        message="SpeakTogether API is running (simplified version)",
        data={
            "version": "0.1.0-simple",
            "status": "healthy",
            "agents_active": orchestrator.is_active if orchestrator else False
        }
    )

@app.get("/api/v1/health", response_model=SuccessResponse)
async def health_check():
    """Health check endpoint"""
    return SuccessResponse(
        message="Service is healthy",
        data={
            "status": "ok",
            "orchestrator": "active" if orchestrator and orchestrator.is_active else "inactive"
        }
    )

@app.websocket("/ws/audio-stream/{session_id}")
async def websocket_audio_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio streaming and processing"""
    await connection_manager.connect(websocket, session_id)
    print(f"WebSocket connected: {session_id}")
    
    try:
        while True:
            # Receive audio data from frontend
            data = await websocket.receive_bytes()
            print(f"Received {len(data)} bytes from {session_id}")
            
            # Process audio through mock orchestrator
            if orchestrator:
                result = await orchestrator.process_audio_stream(
                    audio_data=data,
                    session_id=session_id
                )
                
                # Send processed result back to frontend
                await connection_manager.send_to_session(session_id, result)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
        connection_manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for {session_id}: {e}")
        await connection_manager.send_error(session_id, str(e))

@app.websocket("/ws/agent-dashboard/{session_id}")
async def websocket_agent_dashboard(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent decision monitoring"""
    await connection_manager.connect(websocket, f"dashboard_{session_id}")
    print(f"Agent dashboard connected: {session_id}")
    
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
        print(f"Agent dashboard disconnected: {session_id}")
        connection_manager.disconnect(f"dashboard_{session_id}")
    except Exception as e:
        print(f"Agent dashboard error for {session_id}: {e}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            details=str(exc)
        ).dict()
    )

if __name__ == "__main__":
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 