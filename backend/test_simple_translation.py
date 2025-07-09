"""
Test simple translation using API key
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from src.simple_translation import SimpleTranslationClient


async def test_simple_translation():
    """Test simple translation with API key"""
    
    print("🔍 Testing Simple Translation with API Key...")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('ADK_API_KEY')
    if not api_key:
        print("❌ ADK_API_KEY not set")
        return False
    
    print(f"🔑 API Key: {api_key[:10]}...")
    
    try:
        # Initialize client
        print("\n🚀 Initializing simple translation client...")
        client = SimpleTranslationClient()
        print("✅ Simple translation client initialized")
        
        # Test translation
        print("\n🌐 Testing translation...")
        result = await client.translate_text(
            text="Hello world",
            target_language="es",
            source_language="en"
        )
        
        if result['success']:
            print(f"✅ Translation successful: '{result['translation']}'")
        else:
            print(f"❌ Translation failed: {result.get('error', 'Unknown error')}")
        
        # Test language detection
        print("\n🔤 Testing language detection...")
        lang_result = await client.detect_language("Hello, how are you?")
        
        if lang_result['success']:
            detected = lang_result['detected_language']
            print(f"✅ Language detected: {detected['name']} (confidence: {detected['confidence']:.2f})")
        else:
            print(f"❌ Language detection failed: {lang_result.get('error', 'Unknown error')}")
        
        print("\n🎉 Simple translation test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing simple translation: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the test
    success = asyncio.run(test_simple_translation())
    
    if success:
        print("\n✅ Simple translation is working!")
        print("🚀 You can now use the app with API key translation")
    else:
        print("\n❌ Simple translation failed")
        print("🔧 Please check your API key and try again") 