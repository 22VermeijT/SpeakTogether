"""
WebSocket Connection Manager for SpeakTogether
Manages real-time connections for audio streaming and agent dashboard
"""

import asyncio
import json
import time
from typing import Dict, Set, Any
import structlog

from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication
    Handles audio streaming and agent dashboard connections
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}
        self.connection_stats = {
            'total_connections': 0,
            'active_sessions': 0,
            'messages_sent': 0,
            'errors': 0
        }
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            self.connection_metadata[session_id] = {
                'connected_at': time.time(),
                'last_activity': time.time(),
                'message_count': 0,
                'connection_type': self._determine_connection_type(session_id)
            }
            
            self.connection_stats['total_connections'] += 1
            self.connection_stats['active_sessions'] = len(self.active_connections)
            
            logger.info("WebSocket connection established", 
                       session_id=session_id,
                       total_active=len(self.active_connections))
            
        except Exception as e:
            logger.error("Error establishing WebSocket connection", 
                        session_id=session_id, error=str(e))
            raise
    
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection"""
        try:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                
            if session_id in self.connection_metadata:
                metadata = self.connection_metadata[session_id]
                connection_duration = time.time() - metadata['connected_at']
                
                logger.info("WebSocket connection closed", 
                           session_id=session_id,
                           duration_seconds=connection_duration,
                           messages_sent=metadata['message_count'])
                
                del self.connection_metadata[session_id]
            
            self.connection_stats['active_sessions'] = len(self.active_connections)
            
        except Exception as e:
            logger.error("Error disconnecting WebSocket", 
                        session_id=session_id, error=str(e))
    
    async def send_to_session(self, session_id: str, data: Any):
        """Send data to a specific session"""
        try:
            if session_id not in self.active_connections:
                logger.warning("Attempted to send to inactive session", session_id=session_id)
                return False
            
            websocket = self.active_connections[session_id]
            
            # Prepare message
            message = self._prepare_message(data)
            
            # Send message
            await websocket.send_text(message)
            
            # Update stats
            self._update_activity(session_id)
            self.connection_stats['messages_sent'] += 1
            
            logger.debug("Message sent to session", 
                        session_id=session_id, 
                        message_size=len(message))
            
            return True
            
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during send", session_id=session_id)
            self.disconnect(session_id)
            return False
            
        except Exception as e:
            logger.error("Error sending message to session", 
                        session_id=session_id, error=str(e))
            self.connection_stats['errors'] += 1
            return False
    
    async def send_to_all(self, data: Any, exclude_sessions: Set[str] = None):
        """Send data to all active sessions"""
        exclude_sessions = exclude_sessions or set()
        message = self._prepare_message(data)
        
        disconnected_sessions = []
        
        for session_id, websocket in self.active_connections.items():
            if session_id in exclude_sessions:
                continue
                
            try:
                await websocket.send_text(message)
                self._update_activity(session_id)
                self.connection_stats['messages_sent'] += 1
                
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected during broadcast", session_id=session_id)
                disconnected_sessions.append(session_id)
                
            except Exception as e:
                logger.error("Error broadcasting to session", 
                            session_id=session_id, error=str(e))
                self.connection_stats['errors'] += 1
        
        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
            self.disconnect(session_id)
        
        logger.info("Broadcast message sent", 
                   total_sessions=len(self.active_connections),
                   excluded=len(exclude_sessions),
                   disconnected=len(disconnected_sessions))
    
    async def send_error(self, session_id: str, error_message: str, error_code: str = None):
        """Send error message to a session"""
        error_data = {
            'type': 'error',
            'session_id': session_id,
            'timestamp': time.time(),
            'data': {
                'message': error_message,
                'error_code': error_code,
                'session_id': session_id
            }
        }
        
        await self.send_to_session(session_id, error_data)
        
        logger.error("Error sent to session", 
                    session_id=session_id, 
                    error_message=error_message,
                    error_code=error_code)
    
    async def ping_all(self):
        """Send ping to all connections to keep them alive"""
        ping_data = {
            'type': 'ping',
            'timestamp': time.time(),
            'data': {'message': 'ping'}
        }
        
        await self.send_to_all(ping_data)
        logger.debug("Ping sent to all connections", active_count=len(self.active_connections))
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a specific session"""
        if session_id not in self.connection_metadata:
            return {}
        
        metadata = self.connection_metadata[session_id]
        current_time = time.time()
        
        return {
            'session_id': session_id,
            'connected': session_id in self.active_connections,
            'connected_at': metadata['connected_at'],
            'connection_duration': current_time - metadata['connected_at'],
            'last_activity': metadata['last_activity'],
            'idle_time': current_time - metadata['last_activity'],
            'message_count': metadata['message_count'],
            'connection_type': metadata['connection_type']
        }
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active sessions"""
        return {
            session_id: self.get_session_info(session_id)
            for session_id in self.active_connections.keys()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        current_time = time.time()
        
        # Calculate additional stats
        if self.active_connections:
            avg_connection_duration = sum(
                current_time - metadata['connected_at']
                for metadata in self.connection_metadata.values()
            ) / len(self.active_connections)
            
            total_messages = sum(
                metadata['message_count']
                for metadata in self.connection_metadata.values()
            )
        else:
            avg_connection_duration = 0
            total_messages = 0
        
        return {
            **self.connection_stats,
            'average_connection_duration': avg_connection_duration,
            'total_messages_received': total_messages,
            'connection_types': self._get_connection_type_stats()
        }
    
    def _prepare_message(self, data: Any) -> str:
        """Prepare data for WebSocket transmission"""
        if isinstance(data, str):
            return data
        
        try:
            return json.dumps(data, default=str)
        except Exception as e:
            logger.error("Error serializing message data", error=str(e))
            return json.dumps({
                'type': 'error',
                'message': 'Error serializing data',
                'timestamp': time.time()
            })
    
    def _update_activity(self, session_id: str):
        """Update last activity timestamp for a session"""
        if session_id in self.connection_metadata:
            self.connection_metadata[session_id]['last_activity'] = time.time()
            self.connection_metadata[session_id]['message_count'] += 1
    
    def _determine_connection_type(self, session_id: str) -> str:
        """Determine the type of connection based on session ID"""
        if session_id.startswith('dashboard_'):
            return 'agent_dashboard'
        else:
            return 'audio_stream'
    
    def _get_connection_type_stats(self) -> Dict[str, int]:
        """Get statistics by connection type"""
        stats = {}
        for metadata in self.connection_metadata.values():
            connection_type = metadata['connection_type']
            stats[connection_type] = stats.get(connection_type, 0) + 1
        return stats
    
    async def cleanup_idle_connections(self, idle_timeout: int = 300):
        """Clean up connections that have been idle for too long"""
        current_time = time.time()
        idle_sessions = []
        
        for session_id, metadata in self.connection_metadata.items():
            if current_time - metadata['last_activity'] > idle_timeout:
                idle_sessions.append(session_id)
        
        for session_id in idle_sessions:
            logger.info("Cleaning up idle connection", 
                       session_id=session_id,
                       idle_time=current_time - self.connection_metadata[session_id]['last_activity'])
            
            try:
                if session_id in self.active_connections:
                    await self.active_connections[session_id].close()
            except Exception as e:
                logger.error("Error closing idle connection", 
                            session_id=session_id, error=str(e))
            finally:
                self.disconnect(session_id)
        
        if idle_sessions:
            logger.info("Idle connection cleanup completed", 
                       cleaned_up=len(idle_sessions),
                       remaining=len(self.active_connections)) 