"""
Real-time PyAudio Capture for SpeakTogether
Handles microphone input and system audio capture with proper threading and buffering
"""

import asyncio
import threading
import time
import queue
from typing import Optional, Callable, Dict, Any, List
import structlog

try:
    import pyaudio
    import numpy as np
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None
    np = None

logger = structlog.get_logger()


class PyAudioCapture:
    """
    Real-time audio capture using PyAudio with asyncio integration
    Supports both microphone input and system audio capture
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        audio_format: int = None,
        buffer_duration_seconds: float = 1.0,
        audio_source: str = "microphone",  # "microphone" or "system"
        device_index: Optional[int] = None
    ):
        """
        Initialize PyAudio capture
        
        Args:
            sample_rate: Audio sample rate (16kHz for speech recognition)
            channels: Number of audio channels (1 for mono, 2 for stereo)
            chunk_size: Size of audio chunks to read
            audio_format: PyAudio format (defaults to paInt16)
            buffer_duration_seconds: How long to buffer before sending
            audio_source: "microphone" or "system" audio capture
            device_index: Specific device to use (None for default)
        """
        if not PYAUDIO_AVAILABLE:
            raise ImportError(
                "PyAudio is not available. Install with: pip install pyaudio\n"
                "On macOS: brew install portaudio && pip install pyaudio\n"
                "On Ubuntu: apt-get install portaudio19-dev && pip install pyaudio"
            )
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format or (pyaudio.paInt16 if PYAUDIO_AVAILABLE else 16)
        self.buffer_duration = buffer_duration_seconds
        self.audio_source = audio_source
        self.device_index = device_index
        
        # Calculate buffer size in chunks
        self.buffer_chunks = int(
            (sample_rate * buffer_duration_seconds) / chunk_size
        )
        
        # PyAudio instances
        self.py_audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        
        # Threading and state
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None
        self.audio_queue = queue.Queue(maxsize=self.buffer_chunks * 2)
        
        # Callbacks
        self.audio_callback: Optional[Callable[[bytes, Dict[str, Any]], None]] = None
        
        # Stats
        self.stats = {
            'total_chunks': 0,
            'total_bytes': 0,
            'buffer_overruns': 0,
            'capture_errors': 0,
            'start_time': None,
            'last_chunk_time': None
        }
        
        logger.info("PyAudio capture initialized", 
                   sample_rate=sample_rate,
                   channels=channels,
                   chunk_size=chunk_size,
                   audio_source=audio_source,
                   buffer_chunks=self.buffer_chunks)
    
    async def initialize(self) -> bool:
        """Initialize PyAudio and discover audio devices"""
        try:
            self.py_audio = pyaudio.PyAudio()
            
            # Get device info
            device_info = self._get_device_info()
            logger.info("Audio devices discovered", devices=device_info)
            
            # Auto-select device if not specified
            if self.device_index is None:
                self.device_index = self._get_default_device_index()
                logger.info("Auto-selected device", 
                           device_index=self.device_index, 
                           source=self.audio_source)
            
            return True
            
        except Exception as e:
            logger.error("Failed to initialize PyAudio", error=str(e))
            return False
    
    def _get_default_device_index(self) -> int:
        """Get default device index based on audio source"""
        if not PYAUDIO_AVAILABLE or not self.py_audio:
            return 0
            
        try:
            if self.audio_source == "microphone":
                return self.py_audio.get_default_input_device_info()['index']
            elif self.audio_source == "system":
                # For system audio, we need to find a suitable output device
                # This is platform-specific and may require special configuration
                return self._find_system_audio_device()
            else:
                return self.py_audio.get_default_input_device_info()['index']
        except Exception as e:
            logger.warning("Failed to get default device, using fallback", error=str(e))
            return 0
    
    def _find_system_audio_device(self) -> int:
        """Find a suitable device for system audio capture"""
        if not PYAUDIO_AVAILABLE or not self.py_audio:
            return 0
            
        try:
            # Look for devices that support system audio capture
            # This is platform-specific implementation
            device_count = self.py_audio.get_device_count()
            
            for i in range(device_count):
                device_info = self.py_audio.get_device_info_by_index(i)
                device_name = device_info['name'].lower()
                
                # Look for system audio devices (platform-specific)
                if any(keyword in device_name for keyword in [
                    'stereo mix', 'what u hear', 'loopback', 'system audio',
                    'speaker', 'headphone', 'output'
                ]):
                    if device_info['maxInputChannels'] > 0:
                        logger.info("Found system audio device", 
                                   device=device_info['name'], 
                                   index=i)
                        return i
            
            # Fallback to default input if no system audio device found
            logger.warning("No system audio device found, using default input")
            return self.py_audio.get_default_input_device_info()['index']
            
        except Exception as e:
            logger.error("Error finding system audio device", error=str(e))
            return 0
    
    def set_audio_callback(self, callback: Callable[[bytes, Dict[str, Any]], None]):
        """Set callback function for audio data"""
        self.audio_callback = callback
    
    async def start_capture(self) -> bool:
        """Start audio capture in background thread"""
        if self.is_capturing:
            logger.warning("Audio capture already running")
            return True
        
        if not self.py_audio:
            if not await self.initialize():
                return False
        
        try:
            # Get device info for validation
            device_info = self.py_audio.get_device_info_by_index(self.device_index)
            logger.info("Starting capture on device", 
                       device=device_info['name'],
                       index=self.device_index,
                       source=self.audio_source)
            
            # Adjust channels based on device capabilities
            max_channels = device_info['maxInputChannels']
            if self.channels > max_channels:
                logger.warning("Reducing channels to device maximum", 
                              requested=self.channels, 
                              maximum=max_channels)
                self.channels = max_channels
            
            # Open audio stream
            self.stream = self.py_audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
                start=False
            )
            
            # Clear stats
            self.stats['start_time'] = time.time()
            self.stats['total_chunks'] = 0
            self.stats['total_bytes'] = 0
            self.stats['buffer_overruns'] = 0
            self.stats['capture_errors'] = 0
            
            # Start capture thread
            self.is_capturing = True
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name=f"PyAudioCapture-{self.audio_source}"
            )
            self.capture_thread.start()
            
            # Start the stream
            self.stream.start_stream()
            
            logger.info("Audio capture started successfully", 
                       source=self.audio_source,
                       device=device_info['name'])
            return True
            
        except Exception as e:
            logger.error("Failed to start audio capture", error=str(e))
            self.stats['capture_errors'] += 1
            await self.stop_capture()
            return False
    
    async def stop_capture(self):
        """Stop audio capture and cleanup resources"""
        logger.info("Stopping audio capture")
        
        self.is_capturing = False
        
        # Stop and close stream
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                logger.error("Error stopping audio stream", error=str(e))
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
            if self.capture_thread.is_alive():
                logger.warning("Capture thread did not stop cleanly")
        
        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("Audio capture stopped", stats=self.get_stats())
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio stream callback - runs in audio thread"""
        if status:
            logger.warning("Audio callback status", status=status)
        
        # Add to queue for processing
        try:
            self.audio_queue.put_nowait({
                'data': in_data,
                'frame_count': frame_count,
                'timestamp': time.time()
            })
        except queue.Full:
            self.stats['buffer_overruns'] += 1
            logger.warning("Audio buffer overrun - dropping audio chunk")
        
        return (None, pyaudio.paContinue)
    
    def _capture_loop(self):
        """Main capture loop - processes audio chunks"""
        logger.info("Audio capture loop started")
        audio_buffer = []
        buffer_size = 0
        
        while self.is_capturing:
            try:
                # Get audio chunk from queue
                try:
                    chunk_data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                audio_chunk = chunk_data['data']
                chunk_timestamp = chunk_data['timestamp']
                
                # Update stats
                self.stats['total_chunks'] += 1
                self.stats['total_bytes'] += len(audio_chunk)
                self.stats['last_chunk_time'] = chunk_timestamp
                
                # Add to buffer
                audio_buffer.append(audio_chunk)
                buffer_size += len(audio_chunk)
                
                # Check if we have enough audio to send
                if len(audio_buffer) >= self.buffer_chunks:
                    # Combine chunks
                    combined_audio = b''.join(audio_buffer)
                    
                    # Calculate audio metrics
                    audio_metrics = self._calculate_audio_metrics(
                        combined_audio, chunk_timestamp
                    )
                    
                    # Send to callback if available
                    if self.audio_callback:
                        try:
                            self.audio_callback(combined_audio, audio_metrics)
                        except Exception as e:
                            logger.error("Error in audio callback", error=str(e))
                    
                    # Reset buffer
                    audio_buffer = []
                    buffer_size = 0
                
            except Exception as e:
                logger.error("Error in capture loop", error=str(e))
                self.stats['capture_errors'] += 1
        
        logger.info("Audio capture loop ended")
    
    def _calculate_audio_metrics(self, audio_data: bytes, timestamp: float) -> Dict[str, Any]:
        """Calculate audio quality metrics"""
        try:
            # Convert to numpy array for analysis
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate volume (RMS)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            volume_db = 20 * np.log10(rms + 1e-6)  # Avoid log(0)
            
            # Normalize volume to 0-100 scale
            volume_normalized = max(0, min(100, (volume_db + 60) * 100 / 60))
            
            return {
                'timestamp': float(timestamp),
                'duration_seconds': float(len(audio_data) / (self.sample_rate * self.channels * 2)),
                'sample_rate': int(self.sample_rate),
                'channels': int(self.channels),
                'bytes': int(len(audio_data)),
                'volume_db': float(volume_db),
                'volume_percent': float(volume_normalized),
                'rms': float(rms)
            }
            
        except Exception as e:
            logger.error("Error calculating audio metrics", error=str(e))
            return {
                'timestamp': float(timestamp),
                'duration_seconds': float(len(audio_data) / (self.sample_rate * self.channels * 2)),
                'sample_rate': int(self.sample_rate),
                'channels': int(self.channels),
                'bytes': int(len(audio_data)),
                'volume_db': -60.0,
                'volume_percent': 0.0,
                'rms': 0.0
            }
    
    def _get_device_info(self) -> Dict[str, Any]:
        """Get information about available audio devices"""
        devices = {
            'input_devices': [],
            'output_devices': [],
            'system_audio_available': False
        }
        
        if not self.py_audio:
            return devices
        
        try:
            device_count = self.py_audio.get_device_count()
            
            for i in range(device_count):
                device_info = self.py_audio.get_device_info_by_index(i)
                
                device_data = {
                    'index': i,
                    'name': device_info['name'],
                    'max_input_channels': device_info['maxInputChannels'],
                    'max_output_channels': device_info['maxOutputChannels'],
                    'default_sample_rate': device_info['defaultSampleRate'],
                    'host_api': device_info['hostApi']
                }
                
                # Categorize devices
                if device_info['maxInputChannels'] > 0:
                    devices['input_devices'].append(device_data)
                    
                    # Check if this might be a system audio device
                    device_name = device_info['name'].lower()
                    if any(keyword in device_name for keyword in [
                        'stereo mix', 'what u hear', 'loopback', 'system audio'
                    ]):
                        devices['system_audio_available'] = True
                
                if device_info['maxOutputChannels'] > 0:
                    devices['output_devices'].append(device_data)
            
            # Add default device indicators
            try:
                default_input = self.py_audio.get_default_input_device_info()
                default_output = self.py_audio.get_default_output_device_info()
                
                devices['default_input_index'] = default_input['index']
                devices['default_output_index'] = default_output['index']
                
            except Exception as e:
                logger.warning("Could not get default devices", error=str(e))
            
            return devices
            
        except Exception as e:
            logger.error("Error getting device info", error=str(e))
            return devices

    @staticmethod
    def get_available_audio_sources() -> List[str]:
        """Get list of available audio sources"""
        sources = ["microphone"]
        
        # Check if system audio is available (platform-specific)
        try:
            temp_audio = pyaudio.PyAudio()
            device_count = temp_audio.get_device_count()
            
            for i in range(device_count):
                device_info = temp_audio.get_device_info_by_index(i)
                device_name = device_info['name'].lower()
                
                if any(keyword in device_name for keyword in [
                    'stereo mix', 'what u hear', 'loopback', 'system audio'
                ]):
                    sources.append("system")
                    break
            
            temp_audio.terminate()
            
        except Exception as e:
            logger.warning("Could not check system audio availability", error=str(e))
        
        return sources
    
    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        current_time = time.time()
        start_time = self.stats['start_time']
        
        duration = current_time - start_time if start_time else 0
        
        return {
            'is_capturing': self.is_capturing,
            'total_chunks': self.stats['total_chunks'],
            'total_bytes': self.stats['total_bytes'],
            'buffer_overruns': self.stats['buffer_overruns'],
            'capture_errors': self.stats['capture_errors'],
            'duration_seconds': duration,
            'bytes_per_second': self.stats['total_bytes'] / duration if duration > 0 else 0,
            'last_chunk_time': self.stats['last_chunk_time'],
            'queue_size': self.audio_queue.qsize(),
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_size': self.chunk_size
        }
    
    async def cleanup(self):
        """Clean up PyAudio resources"""
        await self.stop_capture()
        
        if self.py_audio:
            self.py_audio.terminate()
            self.py_audio = None
        
        logger.info("PyAudio capture cleaned up")
    
    def __del__(self):
        """Destructor - ensure cleanup"""
        if hasattr(self, 'py_audio') and self.py_audio:
            try:
                self.py_audio.terminate()
            except:
                pass 