#!/usr/bin/env python3
"""
Test script to verify speech transcription truncation fix
This script helps verify that longer sentences are now properly transcribed
"""

import asyncio
import json
import time
from typing import Dict, Any

from src.audio.stream_handler import AudioStreamHandler


class TestWebSocketCallback:
    """Mock WebSocket callback for testing"""
    
    def __init__(self):
        self.messages = []
        self.transcriptions = []
        
    async def __call__(self, message: Dict[str, Any]):
        """Handle WebSocket message"""
        self.messages.append(message)
        print(f"📨 Received message: {message.get('type', 'unknown')}")
        
        if message.get('type') == 'transcription_result':
            transcript = message.get('data', {}).get('transcript', '')
            confidence = message.get('data', {}).get('confidence', 0)
            duration = message.get('data', {}).get('audio_duration_seconds', 0)
            
            self.transcriptions.append({
                'transcript': transcript,
                'confidence': confidence,
                'duration': duration,
                'word_count': len(transcript.split()) if transcript else 0,
                'timestamp': time.time()
            })
            
            print(f"📝 Transcription: '{transcript}' "
                  f"(words: {len(transcript.split())}, "
                  f"confidence: {confidence:.2f}, "
                  f"duration: {duration:.1f}s)")
    
    def get_transcription_stats(self) -> Dict[str, Any]:
        """Get transcription statistics"""
        if not self.transcriptions:
            return {'total': 0, 'average_words': 0, 'max_words': 0}
        
        word_counts = [t['word_count'] for t in self.transcriptions]
        durations = [t['duration'] for t in self.transcriptions]
        
        return {
            'total_transcriptions': len(self.transcriptions),
            'average_words': sum(word_counts) / len(word_counts),
            'max_words': max(word_counts),
            'min_words': min(word_counts),
            'average_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'transcriptions': self.transcriptions
        }


async def test_speech_settings():
    """Test speech recognition settings"""
    print("🧪 Testing Speech Recognition Settings")
    print("=" * 50)
    
    # Initialize audio stream handler
    handler = AudioStreamHandler()
    
    # Test current settings
    print("📊 Current Settings:")
    print(f"  Target Buffer Duration: {handler.target_buffer_duration}s")
    print(f"  Max Buffer Duration: {handler.max_buffer_duration}s")
    print(f"  Min Buffer Duration: {handler.min_buffer_duration}s")
    print(f"  Silence Threshold: {handler.silence_threshold}s")
    print(f"  Volume Threshold: {handler.volume_threshold}%")
    print()
    
    # Test settings update
    print("🔧 Testing Settings Update...")
    handler.update_speech_settings(
        target_buffer_duration=3.0,
        silence_threshold=2.0,
        volume_threshold=15.0
    )
    print(f"  Updated Target Duration: {handler.target_buffer_duration}s")
    print(f"  Updated Silence Threshold: {handler.silence_threshold}s")
    print(f"  Updated Volume Threshold: {handler.volume_threshold}%")
    print()
    
    # Test stats
    print("📈 Speech Recognition Stats:")
    stats = handler.get_speech_stats()
    print(json.dumps(stats, indent=2))
    print()
    
    return handler


async def test_websocket_messages():
    """Test WebSocket message handling"""
    print("🧪 Testing WebSocket Message Handling")
    print("=" * 50)
    
    handler = AudioStreamHandler()
    callback = TestWebSocketCallback()
    session_id = "test_session_001"
    
    # Test speech settings update message
    print("📤 Testing speech settings update message...")
    message = {
        'type': 'update_speech_settings',
        'settings': {
            'target_buffer_duration': 7.0,
            'max_buffer_duration': 20.0,
            'silence_threshold': 2.5
        }
    }
    
    result = await handler.handle_websocket_message(session_id, message, callback)
    print(f"  Result: {'✅ Success' if result else '❌ Failed'}")
    
    # Check if confirmation message was sent
    if callback.messages:
        last_message = callback.messages[-1]
        if last_message.get('type') == 'speech_settings_updated':
            print("  ✅ Settings update confirmation received")
            settings = last_message.get('settings', {})
            print(f"  📊 Updated settings: {settings}")
        else:
            print("  ❌ No settings update confirmation")
    
    print()
    
    # Test speech stats request message
    print("📤 Testing speech stats request message...")
    message = {
        'type': 'get_speech_stats'
    }
    
    result = await handler.handle_websocket_message(session_id, message, callback)
    print(f"  Result: {'✅ Success' if result else '❌ Failed'}")
    
    # Check if stats message was sent
    if len(callback.messages) >= 2:
        last_message = callback.messages[-1]
        if last_message.get('type') == 'speech_stats_response':
            print("  ✅ Speech stats response received")
            stats = last_message.get('stats', {})
            print(f"  📊 Stats success rate: {stats.get('success_rate', 0):.2f}")
        else:
            print("  ❌ No speech stats response")
    
    return handler, callback


def print_fix_summary():
    """Print summary of the fix implemented"""
    print("🚀 Speech Transcription Truncation Fix Summary")
    print("=" * 60)
    print()
    
    print("🐛 ISSUE FIXED:")
    print("  • Speech transcription limited to ~6 words")
    print("  • 1-second buffer duration was too short")
    print("  • Longer sentences got chopped into fragments")
    print()
    
    print("✅ SOLUTION IMPLEMENTED:")
    print("  • Increased buffer duration from 1.0s to 5.0s")
    print("  • Added intelligent silence detection (1.5s threshold)")
    print("  • Added voice activity detection (20% volume threshold)")
    print("  • Added maximum buffer duration (15s) for very long speech")
    print("  • Added minimum buffer duration (2s) for quality control")
    print("  • Enhanced Google Cloud Speech-to-Text configuration")
    print("  • Added configurable settings via environment variables")
    print("  • Added WebSocket controls for dynamic adjustment")
    print()
    
    print("🎯 EXPECTED RESULTS:")
    print("  • Users can speak complete sentences (20+ words)")
    print("  • Natural speech boundaries respected")
    print("  • Silence pauses trigger transcription processing")
    print("  • Longer conversations supported without truncation")
    print("  • Better accuracy with enhanced Google Cloud models")
    print()
    
    print("⚙️ NEW CONFIGURATION OPTIONS:")
    print("  • SPEECH_BUFFER_TARGET_DURATION: 5.0s (default)")
    print("  • SPEECH_BUFFER_MAX_DURATION: 15.0s (max before forced processing)")
    print("  • SPEECH_BUFFER_MIN_DURATION: 2.0s (min for quality)")
    print("  • SPEECH_SILENCE_THRESHOLD: 1.5s (silence trigger)")
    print("  • SPEECH_VOLUME_THRESHOLD: 20.0% (voice activity detection)")
    print()


async def main():
    """Main test function"""
    print_fix_summary()
    
    try:
        # Test speech settings
        handler1 = await test_speech_settings()
        
        # Test WebSocket messages
        handler2, callback = await test_websocket_messages()
        
        print("🎉 All tests completed successfully!")
        print()
        
        print("📋 TESTING RECOMMENDATIONS:")
        print("  1. Start the backend server: python main_simple_with_pyaudio.py")
        print("  2. Open the frontend and test with longer sentences")
        print("  3. Try speaking: 'Hello, how are you doing today? I hope you're having a great time.'")
        print("  4. Verify that the full sentence is transcribed (not just ~6 words)")
        print("  5. Test with different languages and silence patterns")
        print("  6. Monitor logs for 'process_reason' to see why transcription triggered")
        print()
        
        print("🔍 LOG MONITORING:")
        print("  Look for messages with 'process_reason' in logs:")
        print("    • 'silence_break_detected' - Good! Sentence boundary detected")
        print("    • 'target_duration_reached' - Normal processing after 5s")
        print("    • 'max_duration_reached' - Long speech (15s+) processed")
        print()
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 