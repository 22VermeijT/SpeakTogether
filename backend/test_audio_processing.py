#!/usr/bin/env python3
"""
Test script for SpeakTogether audio processing pipeline
Tests system audio capture, speech-to-text, and WebSocket streaming
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.audio.capture import PyAudioCapture
from src.audio.stream_handler import AudioStreamHandler
from src.google_cloud_client import GoogleCloudClient
from src.config import settings
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def test_audio_capture():
    """Test PyAudio capture functionality"""
    print("🎤 Testing PyAudio Capture...")
    
    try:
        # Test microphone capture
        print("  📱 Testing microphone capture...")
        mic_capture = PyAudioCapture(
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            audio_source="microphone"
        )
        
        if await mic_capture.initialize():
            print("  ✅ Microphone capture initialized")
            
            # Test device info
            device_info = mic_capture._get_device_info()
            print(f"  📊 Found {len(device_info['input_devices'])} input devices")
            print(f"  📊 System audio available: {device_info['system_audio_available']}")
            
            await mic_capture.cleanup()
        else:
            print("  ❌ Failed to initialize microphone capture")
            
        # Test system audio capture
        print("  🔊 Testing system audio capture...")
        system_capture = PyAudioCapture(
            sample_rate=16000,
            channels=2,
            chunk_size=1024,
            audio_source="system"
        )
        
        if await system_capture.initialize():
            print("  ✅ System audio capture initialized")
            await system_capture.cleanup()
        else:
            print("  ⚠️ System audio capture not available (this is normal on some systems)")
            
    except Exception as e:
        print(f"  ❌ Audio capture test failed: {e}")
        return False
        
    return True


async def test_stream_handler():
    """Test AudioStreamHandler functionality"""
    print("🌊 Testing Audio Stream Handler...")
    
    try:
        handler = AudioStreamHandler()
        
        # Mock WebSocket callback
        received_messages = []
        
        async def mock_websocket_callback(message):
            received_messages.append(message)
            print(f"  📨 WebSocket message: {message.get('type', 'unknown')}")
        
        # Test session creation
        session_id = "test_session_123"
        
        # Test with microphone
        print("  🎙️ Testing microphone session...")
        success = await handler.start_audio_session(
            session_id=session_id,
            websocket_callback=mock_websocket_callback,
            audio_config={
                'audio_source': 'microphone',
                'sample_rate': 16000,
                'channels': 1
            }
        )
        
        if success:
            print("  ✅ Microphone session started")
            
            # Wait a bit to capture some audio
            await asyncio.sleep(2)
            
            # Check session status
            status = await handler.get_session_status(session_id)
            if status:
                print(f"  📊 Session status: {status}")
            
            # Stop session
            await handler.stop_audio_session(session_id)
            print("  ✅ Microphone session stopped")
        else:
            print("  ❌ Failed to start microphone session")
            
        # Test with system audio
        print("  🔊 Testing system audio session...")
        success = await handler.start_audio_session(
            session_id=session_id + "_system",
            websocket_callback=mock_websocket_callback,
            audio_config={
                'audio_source': 'system',
                'sample_rate': 16000,
                'channels': 2
            }
        )
        
        if success:
            print("  ✅ System audio session started")
            await asyncio.sleep(2)
            await handler.stop_audio_session(session_id + "_system")
            print("  ✅ System audio session stopped")
        else:
            print("  ⚠️ System audio session not available")
            
        print(f"  📊 Total messages received: {len(received_messages)}")
        
    except Exception as e:
        print(f"  ❌ Stream handler test failed: {e}")
        return False
        
    return True


async def test_google_cloud_client():
    """Test Google Cloud client functionality"""
    print("☁️ Testing Google Cloud Client...")
    
    try:
        # Check if credentials are available
        if not hasattr(settings, 'ADK_API_KEY') or not settings.ADK_API_KEY:
            print("  ⚠️ Google Cloud credentials not configured, skipping test")
            return True
            
        client = GoogleCloudClient(
            project_id=getattr(settings, 'ADK_PROJECT_ID', None) or "",
            credentials_path=getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None) or ""
        )
        
        # Test initialization
        if await client.initialize():
            print("  ✅ Google Cloud client initialized")
            
            # Test supported languages
            languages = await client.get_supported_languages()
            if languages:
                print(f"  📊 Supported languages: {len(languages.get('translation_languages', []))}")
            
            # Test text translation
            translation_result = await client.translate_text(
                text="Hello, how are you?",
                target_language="es"
            )
            
            if translation_result.get('success'):
                print(f"  ✅ Translation test: '{translation_result['translated_text']}'")
            else:
                print(f"  ❌ Translation failed: {translation_result.get('error', 'Unknown error')}")
            
            # Test streaming recognition setup
            session_id = "test_speech_session"
            if await client.start_streaming_recognition(session_id):
                print("  ✅ Streaming recognition session started")
                
                # Test with dummy audio data
                dummy_audio = b'\x00' * 1024  # Silence
                result = await client.process_audio_chunk(session_id, dummy_audio)
                if result:
                    print(f"  📊 Speech recognition result: {result}")
                
                # Stop session
                stats = await client.stop_streaming_recognition(session_id)
                print(f"  ✅ Streaming session stopped: {stats}")
            else:
                print("  ❌ Failed to start streaming recognition")
                
            await client.cleanup()
            
        else:
            print("  ❌ Failed to initialize Google Cloud client")
            return False
            
    except Exception as e:
        print(f"  ❌ Google Cloud client test failed: {e}")
        return False
        
    return True


async def test_integration():
    """Test full integration of audio processing pipeline"""
    print("🔧 Testing Full Integration...")
    
    try:
        # Initialize components
        handler = AudioStreamHandler()
        
        # Test with mock Google Cloud client
        results = []
        
        async def integration_callback(message):
            results.append(message)
            print(f"  🔄 Integration message: {message.get('type', 'unknown')}")
        
        # Start audio session
        session_id = "integration_test"
        success = await handler.start_audio_session(
            session_id=session_id,
            websocket_callback=integration_callback,
            audio_config={
                'audio_source': 'microphone',
                'sample_rate': 16000,
                'channels': 1,
                'source_language': 'en',
                'target_language': 'es'
            }
        )
        
        if success:
            print("  ✅ Integration session started")
            
            # Let it run for a few seconds
            await asyncio.sleep(3)
            
            # Stop session
            await handler.stop_audio_session(session_id)
            print("  ✅ Integration session stopped")
            
            print(f"  📊 Total integration messages: {len(results)}")
            
        else:
            print("  ❌ Failed to start integration session")
            return False
            
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False
        
    return True


async def main():
    """Run all audio processing tests"""
    print("🚀 SpeakTogether Audio Processing Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Audio Capture
    result = await test_audio_capture()
    test_results.append(("Audio Capture", result))
    
    # Test 2: Stream Handler
    result = await test_stream_handler()
    test_results.append(("Stream Handler", result))
    
    # Test 3: Google Cloud Client
    result = await test_google_cloud_client()
    test_results.append(("Google Cloud Client", result))
    
    # Test 4: Integration
    result = await test_integration()
    test_results.append(("Full Integration", result))
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:20} - {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 All tests passed! Audio processing is ready.")
    else:
        print("⚠️ Some tests failed. Check the implementation.")
    
    return passed == len(test_results)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1) 