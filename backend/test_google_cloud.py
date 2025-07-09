"""
Test script to verify Google Cloud integration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from src.google_cloud_client import GoogleCloudClient


async def test_google_cloud_integration():
    """Test Google Cloud APIs"""
    
    print("🔍 Testing Google Cloud Integration...")
    print("=" * 50)
    
    # Check environment variables
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    
    print(f"📁 Credentials path: {creds_path}")
    print(f"🆔 Project ID: {project_id}")
    
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set")
        return False
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    print("✅ Environment variables look good")
    
    try:
        # Initialize Google Cloud client
        print("\n🚀 Initializing Google Cloud client...")
        client = GoogleCloudClient()
        await client.initialize()
        print("✅ Google Cloud client initialized successfully")
        
        # Test language detection
        print("\n🔤 Testing language detection...")
        test_text = "Hello, how are you today?"
        lang_result = await client.detect_language(test_text)
        
        if lang_result['success']:
            detected = lang_result['detected_language']
            print(f"✅ Language detected: {detected['name']} (confidence: {detected['confidence']:.2f})")
        else:
            print(f"❌ Language detection failed: {lang_result.get('error', 'Unknown error')}")
        
        # Test translation
        print("\n🌐 Testing translation...")
        translate_result = await client.translate_text(
            text="Hello world",
            target_language="es",
            source_language="en"
        )
        
        if translate_result['success']:
            print(f"✅ Translation successful: '{translate_result['translation']}'")
        else:
            print(f"❌ Translation failed: {translate_result.get('error', 'Unknown error')}")
        
        # Test text-to-speech
        print("\n🔊 Testing text-to-speech...")
        tts_result = await client.text_to_speech(
            text="Hello, this is a test of the text to speech system.",
            voice_name="en-US-Neural2-C"
        )
        
        if tts_result['success']:
            print(f"✅ Text-to-speech successful: {tts_result['duration_seconds']:.1f}s audio generated")
        else:
            print(f"❌ Text-to-speech failed: {tts_result.get('error', 'Unknown error')}")
        
        print("\n🎉 All Google Cloud APIs are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Google Cloud integration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the test
    success = asyncio.run(test_google_cloud_integration())
    
    if success:
        print("\n✅ Google Cloud integration is ready to use!")
        print("🚀 You can now run the SpeakTogether app with real Google Cloud APIs")
    else:
        print("\n❌ Google Cloud integration failed")
        print("🔧 Please check your credentials and try again") 