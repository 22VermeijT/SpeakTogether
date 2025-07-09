"""
Audio Stream Handler for SpeakTogether
Manages PyAudio capture sessions and WebSocket integration
"""

import asyncio
import json
import time
from typing import Dict, Optional, Any
import structlog
import threading

from .capture import PyAudioCapture

logger = structlog.get_logger()


class AudioStreamHandler:
    """
    Manages audio capture sessions for WebSocket clients
    Integrates PyAudio capture with real-time streaming
    """
    
    def __init__(self):
        """Initialize the audio stream handler"""
        self.active_captures: Dict[str, PyAudioCapture] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'total_audio_bytes': 0,
            'total_chunks_processed': 0
        }
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info("Audio stream handler initialized")
    
    async def start_audio_session(
        self, 
        session_id: str, 
        websocket_callback: callable,
        audio_config: Dict[str, Any] = None
    ) -> bool:
        """
        Start audio capture for a session
        
        Args:
            session_id: Unique session identifier
            websocket_callback: Function to send audio data via WebSocket
            audio_config: Optional audio configuration overrides
        
        Returns:
            bool: True if capture started successfully
        """
        if session_id in self.active_captures:
            logger.warning("Audio session already exists", session_id=session_id)
            print(f"🎤 SESSION DEBUG: Session {session_id} already exists")
            return True
        
        print(f"🎤 SESSION DEBUG: Starting new audio session for {session_id}")
        
        try:
            # Store the main event loop reference at session start
            try:
                self._main_loop = asyncio.get_running_loop()
                print(f"🎤 SESSION DEBUG: Got running event loop")
            except RuntimeError:
                self._main_loop = asyncio.get_event_loop()
                print(f"🎤 SESSION DEBUG: Got default event loop")
            
            # Create audio config
            config = self._create_audio_config(audio_config)
            print(f"🎤 SESSION DEBUG: Created config: {config}")
            
            # Create PyAudio capture instance
            capture = PyAudioCapture(
                sample_rate=config['sample_rate'],
                channels=config['channels'],
                chunk_size=config['chunk_size'],
                buffer_duration_seconds=config['buffer_duration'],
                audio_source=config['audio_source'],
                device_index=config.get('device_index')
            )
            
            # Set up callback for audio data with proper event loop handling
            def audio_callback(audio_data: bytes, metrics: Dict[str, Any]):
                print(f"🎤 CALLBACK DEBUG: Audio callback called! Data: {len(audio_data)} bytes, Volume: {metrics.get('volume_percent', 0):.1f}%")
                # Use thread-safe approach for asyncio from PyAudio thread
                try:
                    # Validate inputs
                    if not audio_data or not metrics:
                        logger.warning("Invalid audio data or metrics in callback", 
                                     session_id=session_id)
                        print(f"🎤 CALLBACK DEBUG: Invalid audio data or metrics")
                        return
                    
                    # Check if we have a valid event loop reference
                    if self._main_loop and not self._main_loop.is_closed():
                        # Schedule the coroutine on the main event loop from PyAudio thread
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                self._handle_audio_data(session_id, audio_data, metrics, websocket_callback),
                                self._main_loop
                            )
                            # Don't wait for result to avoid blocking PyAudio thread
                            logger.debug("Audio callback scheduled successfully", 
                                       session_id=session_id,
                                       thread=threading.current_thread().name,
                                       audio_bytes=len(audio_data))
                        except RuntimeError as e:
                            if "cannot schedule" in str(e).lower():
                                logger.error("Event loop closed, cannot schedule audio callback", 
                                           session_id=session_id)
                            else:
                                logger.error("Runtime error in audio callback", 
                                           session_id=session_id, 
                                           error=str(e))
                    else:
                        logger.warning("Main event loop not available for audio callback", 
                                     session_id=session_id,
                                     loop_available=self._main_loop is not None,
                                     loop_closed=self._main_loop.is_closed() if self._main_loop else "N/A")
                except Exception as e:
                    logger.error("Error scheduling audio callback", 
                               session_id=session_id, 
                               thread=threading.current_thread().name,
                               error=str(e),
                               error_type=type(e).__name__)
            
            capture.set_audio_callback(audio_callback)
            
            # Initialize and start capture
            print(f"🎤 SESSION DEBUG: Initializing PyAudio capture...")
            if await capture.initialize():
                print(f"🎤 SESSION DEBUG: PyAudio initialized successfully, starting capture...")
                if await capture.start_capture():
                    print(f"🎤 SESSION DEBUG: PyAudio capture started successfully!")
                    # Store capture instance and metadata
                    self.active_captures[session_id] = capture
                    self.session_metadata[session_id] = {
                        'started_at': time.time(),
                        'config': config,
                        'total_chunks': 0,
                        'total_bytes': 0,
                        'websocket_callback': websocket_callback
                    }
                    
                    # Update stats
                    self.stats['total_sessions'] += 1
                    self.stats['active_sessions'] = len(self.active_captures)
                    
                    logger.info("Audio session started", 
                               session_id=session_id,
                               config=config)
                    
                    # Send confirmation to client
                    await websocket_callback({
                        'type': 'audio_session_started',
                        'session_id': session_id,
                        'config': config,
                        'timestamp': time.time()
                    })
                    
                    return True
                else:
                    await capture.cleanup()
            
            logger.error("Failed to start audio capture", session_id=session_id)
            return False
            
        except Exception as e:
            logger.error("Error starting audio session", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def stop_audio_session(self, session_id: str) -> bool:
        """
        Stop audio capture for a session
        
        Args:
            session_id: Session to stop
            
        Returns:
            bool: True if stopped successfully
        """
        if session_id not in self.active_captures:
            logger.warning("Audio session not found", session_id=session_id)
            return False
        
        try:
            capture = self.active_captures[session_id]
            metadata = self.session_metadata[session_id]
            
            # Stop capture
            await capture.stop_capture()
            await capture.cleanup()
            
            # Get final stats
            session_duration = time.time() - metadata['started_at']
            capture_stats = capture.get_stats()
            
            # Send session ended notification
            websocket_callback = metadata['websocket_callback']
            await websocket_callback({
                'type': 'audio_session_ended',
                'session_id': session_id,
                'duration_seconds': session_duration,
                'stats': capture_stats,
                'timestamp': time.time()
            })
            
            # Remove from active sessions
            del self.active_captures[session_id]
            del self.session_metadata[session_id]
            
            # Update stats
            self.stats['active_sessions'] = len(self.active_captures)
            self.stats['total_audio_bytes'] += capture_stats['total_bytes']
            self.stats['total_chunks_processed'] += capture_stats['total_chunks']
            
            logger.info("Audio session stopped", 
                       session_id=session_id,
                       duration=session_duration,
                       final_stats=capture_stats)
            
            return True
            
        except Exception as e:
            logger.error("Error stopping audio session", 
                        session_id=session_id, 
                        error=str(e))
            return False
    
    async def _handle_audio_data(
        self, 
        session_id: str, 
        audio_data: bytes, 
        metrics: Dict[str, Any],
        websocket_callback: callable
    ):
        """
        Handle audio data from PyAudio capture
        
        Args:
            session_id: Session ID
            audio_data: Raw audio bytes
            metrics: Audio quality metrics
            websocket_callback: WebSocket callback function
        """
        try:
            # Update session metadata
            if session_id in self.session_metadata:
                metadata = self.session_metadata[session_id]
                metadata['total_chunks'] += 1
                metadata['total_bytes'] += len(audio_data)
            
            # Create message for WebSocket
            message = {
                'type': 'audio_chunk',
                'session_id': session_id,
                'audio_data': {
                    'size_bytes': len(audio_data),
                    'timestamp': metrics['timestamp'],
                    'duration_seconds': metrics['duration_seconds'],
                    'sample_rate': metrics['sample_rate'],
                    'channels': metrics['channels']
                },
                'audio_metrics': {
                    'volume_db': metrics['volume_db'],
                    'volume_percent': metrics['volume_percent'],
                    'rms': metrics['rms']
                },
                'timestamp': time.time()
            }
            
            # Send audio data via WebSocket
            await websocket_callback(message)
            
            # Log audio processing
            logger.debug("Audio chunk processed", 
                        session_id=session_id,
                        bytes=len(audio_data),
                        volume_percent=metrics['volume_percent'])
            
        except Exception as e:
            logger.error("Error handling audio data", 
                        session_id=session_id, 
                        error=str(e))
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a session"""
        if session_id not in self.active_captures:
            return None
        
        capture = self.active_captures[session_id]
        metadata = self.session_metadata[session_id]
        
        current_time = time.time()
        session_duration = current_time - metadata['started_at']
        
        return {
            'session_id': session_id,
            'is_active': capture.is_capturing,
            'started_at': metadata['started_at'],
            'duration_seconds': session_duration,
            'config': metadata['config'],
            'capture_stats': capture.get_stats(),
            'session_stats': {
                'total_chunks': metadata['total_chunks'],
                'total_bytes': metadata['total_bytes']
            }
        }
    
    async def list_active_sessions(self) -> Dict[str, Any]:
        """List all active audio sessions"""
        sessions = {}
        
        for session_id in self.active_captures:
            session_status = await self.get_session_status(session_id)
            if session_status:
                sessions[session_id] = session_status
        
        return {
            'active_sessions': sessions,
            'total_active': len(sessions),
            'global_stats': self.stats
        }
    
    async def stop_all_sessions(self):
        """Stop all active audio sessions"""
        logger.info("Stopping all audio sessions", 
                   active_count=len(self.active_captures))
        
        # Create list of session IDs to avoid modifying dict during iteration
        session_ids = list(self.active_captures.keys())
        
        for session_id in session_ids:
            await self.stop_audio_session(session_id)
        
        logger.info("All audio sessions stopped")
    
    def _create_audio_config(self, custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create audio configuration with defaults and custom overrides"""
        config = {
            'sample_rate': 16000,
            'channels': 1,
            'chunk_size': 1024,
            'buffer_duration': 1.0,
            'audio_source': 'microphone',  # Default to microphone
            'device_index': None,  # Auto-select device
            'format': 'int16'
        }
        
        # Apply custom overrides
        if custom_config:
            config.update(custom_config)
        
        # Validate audio source
        if config['audio_source'] not in ['microphone', 'system']:
            logger.warning("Invalid audio source, falling back to microphone", 
                         source=config['audio_source'])
            config['audio_source'] = 'microphone'
        
        # Adjust channels for system audio (usually stereo)
        if config['audio_source'] == 'system' and config['channels'] == 1:
            config['channels'] = 2  # System audio is typically stereo
            logger.info("Adjusted channels for system audio", channels=2)
        
        return config
    
    async def handle_websocket_message(
        self, 
        session_id: str, 
        message: Dict[str, Any],
        websocket_callback: callable
    ) -> bool:
        """
        Handle WebSocket message for audio control
        
        Args:
            session_id: Session ID
            message: WebSocket message
            websocket_callback: WebSocket callback function
            
        Returns:
            bool: True if message was handled
        """
        try:
            message_type = message.get('type')
            print(f"🎤 HANDLER DEBUG: Processing message type: {message_type}")
            
            if message_type == 'start_audio_capture' or message_type == 'start_capture':
                print(f"🎤 HANDLER DEBUG: Starting audio capture for session {session_id}")
                # Start audio capture (handle both message types)
                audio_config = message.get('config', {}) or message.get('audio_config', {})
                print(f"🎤 HANDLER DEBUG: Audio config: {audio_config}")
                result = await self.start_audio_session(
                    session_id, 
                    websocket_callback, 
                    audio_config
                )
                print(f"🎤 HANDLER DEBUG: Start session result: {result}")
                return result
            
            elif message_type == 'stop_audio_capture' or message_type == 'stop_capture':
                # Stop audio capture (handle both message types)
                return await self.stop_audio_session(session_id)
            
            elif message_type == 'get_audio_status':
                # Get session status
                status = await self.get_session_status(session_id)
                await websocket_callback({
                    'type': 'audio_status',
                    'session_id': session_id,
                    'status': status,
                    'timestamp': time.time()
                })
                return True
            
            elif message_type == 'get_audio_devices':
                # Get available audio devices
                if session_id in self.active_captures:
                    capture = self.active_captures[session_id]
                    device_info = capture._get_device_info()
                    await websocket_callback({
                        'type': 'audio_devices',
                        'session_id': session_id,
                        'devices': device_info,
                        'timestamp': time.time()
                    })
                    return True
            
            else:
                logger.warning("Unknown audio message type", 
                              session_id=session_id, 
                              message_type=message_type)
                return False
            
        except Exception as e:
            logger.error("Error handling WebSocket message", 
                        session_id=session_id, 
                        error=str(e))
            
            # Send error response
            await websocket_callback({
                'type': 'error',
                'session_id': session_id,
                'message': f"Audio handler error: {str(e)}",
                'timestamp': time.time()
            })
            
            return False
    
    async def cleanup(self):
        """Clean up all resources"""
        await self.stop_all_sessions()
        logger.info("Audio stream handler cleaned up") 