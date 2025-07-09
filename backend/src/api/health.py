"""
Health Check API endpoints for SpeakTogether
Provides system health and status monitoring
"""

import time
import psutil
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from ..models.response import HealthResponse, SuccessResponse
from ..config import settings

router = APIRouter()

# Store startup time for uptime calculation
startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint
    Returns overall system health status
    """
    current_time = time.time()
    uptime_seconds = current_time - startup_time
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Determine overall health status
    health_status = "healthy"
    if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
        health_status = "degraded"
    
    return HealthResponse(
        status=health_status,
        version=settings.APP_VERSION,
        uptime=uptime_seconds,
        agents_status={
            "orchestrator": True,  # Would be actual status
            "audio_context": True,
            "translation_strategy": True,
            "quality_control": True,
            "voice_synthesis": True
        },
        active_sessions=0  # Would be actual count from connection manager
    )


@router.get("/health/detailed", response_model=SuccessResponse)
async def detailed_health():
    """
    Detailed health check with system metrics
    """
    current_time = time.time()
    uptime_seconds = current_time - startup_time
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Process information
    process = psutil.Process()
    process_memory = process.memory_info()
    
    health_data = {
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "uptime_seconds": uptime_seconds,
            "uptime_human": _format_uptime(uptime_seconds),
            "started_at": datetime.fromtimestamp(startup_time).isoformat()
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_mb": memory.total // (1024 * 1024),
                "available_mb": memory.available // (1024 * 1024),
                "percent_used": memory.percent
            },
            "disk": {
                "total_gb": disk.total // (1024 * 1024 * 1024),
                "free_gb": disk.free // (1024 * 1024 * 1024),
                "percent_used": disk.percent
            }
        },
        "process": {
            "pid": process.pid,
            "memory_rss_mb": process_memory.rss // (1024 * 1024),
            "memory_vms_mb": process_memory.vms // (1024 * 1024),
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads()
        },
        "agents": {
            "orchestrator": {
                "status": "active",
                "last_activity": datetime.now().isoformat()
            },
            "audio_context": {
                "status": "active",
                "processed_requests": 0
            },
            "translation_strategy": {
                "status": "active",
                "processed_requests": 0
            },
            "quality_control": {
                "status": "active",
                "processed_requests": 0
            },
            "voice_synthesis": {
                "status": "active", 
                "processed_requests": 0
            }
        },
        "configuration": {
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "max_concurrent_sessions": settings.MAX_CONCURRENT_SESSIONS,
            "agent_timeout": settings.AGENT_TIMEOUT
        }
    }
    
    return SuccessResponse(
        message="Detailed health check completed",
        data=health_data
    )


@router.get("/health/agents", response_model=SuccessResponse)
async def agents_health():
    """
    Health check specifically for AI agents
    """
    # In production, this would query actual agent status
    agents_data = {
        "master_orchestrator": {
            "status": "active",
            "response_time_ms": 150,
            "success_rate": 0.98,
            "last_decision": "2024-01-15T10:30:00Z"
        },
        "audio_context_agent": {
            "status": "active",
            "response_time_ms": 45,
            "accuracy": 0.92,
            "processed_samples": 1250
        },
        "translation_strategy_agent": {
            "status": "active",
            "response_time_ms": 80,
            "strategies_generated": 340,
            "confidence_avg": 0.89
        },
        "quality_control_agent": {
            "status": "active",
            "response_time_ms": 65,
            "validations_performed": 1180,
            "rejection_rate": 0.08
        },
        "voice_synthesis_agent": {
            "status": "active",
            "response_time_ms": 200,
            "voices_generated": 890,
            "synthesis_quality": 0.94
        }
    }
    
    return SuccessResponse(
        message="Agent health check completed",
        data=agents_data
    )


@router.get("/health/connections", response_model=SuccessResponse)
async def connections_health():
    """
    Health check for WebSocket connections
    """
    # In production, this would query the connection manager
    connections_data = {
        "total_connections": 0,
        "active_sessions": 0,
        "connection_types": {
            "audio_stream": 0,
            "agent_dashboard": 0
        },
        "average_session_duration": 0,
        "messages_sent": 0,
        "errors": 0,
        "last_cleanup": datetime.now().isoformat()
    }
    
    return SuccessResponse(
        message="Connections health check completed",
        data=connections_data
    )


def _format_uptime(uptime_seconds: float) -> str:
    """Format uptime in human-readable format"""
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s" 