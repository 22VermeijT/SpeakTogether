"""
Audio processing module for SpeakTogether
Real-time audio capture and streaming
"""

from .capture import PyAudioCapture
from .stream_handler import AudioStreamHandler

__all__ = ['PyAudioCapture', 'AudioStreamHandler'] 