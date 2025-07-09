# SpeakTogether Audio Processing Guide 🎤

This guide explains how to get started with the audio processing implementation in SpeakTogether.

## 🚀 Quick Start

### 1. Setup Audio Processing

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install audio dependencies
pip install pyaudio numpy scipy librosa

# Run audio processing tests
python test_audio_processing.py
```

### 2. Configure Google Cloud (Optional)

```bash
# Set up Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Or add to .env file
echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json" >> .env
echo "GOOGLE_CLOUD_PROJECT=your-project-id" >> .env
```

### 3. Test Audio Sources

```bash
# Test microphone capture
python -c "
import asyncio
from src.audio.capture import PyAudioCapture

async def test():
    capture = PyAudioCapture(audio_source='microphone')
    if await capture.initialize():
        print('Microphone ready!')
        await capture.cleanup()
    else:
        print('Microphone not available')

asyncio.run(test())
"

# Test system audio capture
python -c "
import asyncio
from src.audio.capture import PyAudioCapture

async def test():
    capture = PyAudioCapture(audio_source='system', channels=2)
    if await capture.initialize():
        print('System audio ready!')
        await capture.cleanup()
    else:
        print('System audio not available')

asyncio.run(test())
"
```

## 📊 Audio Processing Components

### 1. **Audio Capture** (`src/audio/capture.py`)

- **PyAudioCapture**: Main class for audio capture
- **Supports**: Microphone and system audio
- **Features**: Real-time streaming, device selection, quality monitoring

```python
from src.audio.capture import PyAudioCapture

# Microphone capture
mic_capture = PyAudioCapture(
    sample_rate=16000,
    channels=1,
    audio_source="microphone"
)

# System audio capture
system_capture = PyAudioCapture(
    sample_rate=16000,
    channels=2,
    audio_source="system"
)
```

### 2. **Stream Handler** (`src/audio/stream_handler.py`)

- **AudioStreamHandler**: Manages audio sessions and WebSocket integration
- **Features**: Session management, WebSocket callbacks, audio configuration

```python
from src.audio.stream_handler import AudioStreamHandler

handler = AudioStreamHandler()

# Start audio session
await handler.start_audio_session(
    session_id="my_session",
    websocket_callback=my_callback,
    audio_config={
        'audio_source': 'microphone',
        'sample_rate': 16000,
        'channels': 1
    }
)
```

### 3. **Google Cloud Client** (`src/google_cloud_client.py`)

- **GoogleCloudClient**: Speech-to-text, translation, and text-to-speech
- **Features**: Real-time streaming recognition, translation, voice synthesis

```python
from src.google_cloud_client import GoogleCloudClient

client = GoogleCloudClient(
    project_id="your-project",
    credentials_path="/path/to/credentials.json"
)

await client.initialize()

# Start streaming recognition
await client.start_streaming_recognition("session_id")

# Process audio chunks
result = await client.process_audio_chunk("session_id", audio_data)
```

## 🔧 Configuration Options

### Audio Source Configuration

```python
# Microphone configuration
microphone_config = {
    'audio_source': 'microphone',
    'sample_rate': 16000,
    'channels': 1,
    'chunk_size': 1024,
    'buffer_duration': 1.0
}

# System audio configuration
system_config = {
    'audio_source': 'system',
    'sample_rate': 16000,
    'channels': 2,        # Stereo for system audio
    'chunk_size': 1024,
    'buffer_duration': 1.0
}
```

### Language Configuration

```python
# Speech recognition languages
speech_languages = [
    'en-US',  # English (US)
    'es-ES',  # Spanish (Spain)
    'fr-FR',  # French (France)
    'de-DE',  # German (Germany)
    'ja-JP',  # Japanese (Japan)
    'zh-CN',  # Chinese (China)
    'ar-SA',  # Arabic (Saudi Arabia)
    'hi-IN',  # Hindi (India)
    'pt-BR'   # Portuguese (Brazil)
]

# Translation languages
translation_languages = [
    'en', 'es', 'fr', 'de', 'ja', 'zh', 'ar', 'hi', 'pt'
]
```

## 🎯 Usage Examples

### Basic Audio Capture

```python
import asyncio
from src.audio.capture import PyAudioCapture

async def basic_capture():
    capture = PyAudioCapture(audio_source="microphone")
    
    def audio_callback(audio_data, metrics):
        print(f"Audio chunk: {len(audio_data)} bytes")
        print(f"Volume: {metrics['volume_percent']:.1f}%")
    
    capture.set_audio_callback(audio_callback)
    
    await capture.initialize()
    await capture.start_capture()
    
    # Capture for 5 seconds
    await asyncio.sleep(5)
    
    await capture.stop_capture()
    await capture.cleanup()

asyncio.run(basic_capture())
```

### WebSocket Integration

```python
import asyncio
import json
from src.audio.stream_handler import AudioStreamHandler

async def websocket_example():
    handler = AudioStreamHandler()
    
    async def websocket_callback(message):
        print(f"WebSocket message: {json.dumps(message, indent=2)}")
    
    # Start session
    success = await handler.start_audio_session(
        session_id="websocket_test",
        websocket_callback=websocket_callback,
        audio_config={
            'audio_source': 'microphone',
            'sample_rate': 16000,
            'channels': 1
        }
    )
    
    if success:
        print("Session started successfully!")
        await asyncio.sleep(5)  # Run for 5 seconds
        await handler.stop_audio_session("websocket_test")
    else:
        print("Failed to start session")

asyncio.run(websocket_example())
```

### Speech-to-Text Integration

```python
import asyncio
from src.google_cloud_client import GoogleCloudClient
from src.audio.capture import PyAudioCapture

async def speech_to_text_example():
    # Initialize Google Cloud client
    client = GoogleCloudClient()
    await client.initialize()
    
    # Start streaming recognition
    session_id = "speech_test"
    await client.start_streaming_recognition(session_id, language_code="en-US")
    
    # Initialize audio capture
    capture = PyAudioCapture(audio_source="microphone")
    
    async def process_audio(audio_data, metrics):
        # Send audio to Google Cloud
        result = await client.process_audio_chunk(session_id, audio_data)
        if result:
            print(f"Transcript: {result['transcript']}")
            print(f"Confidence: {result['confidence']:.2f}")
    
    capture.set_audio_callback(process_audio)
    
    # Start capture
    await capture.initialize()
    await capture.start_capture()
    
    # Run for 10 seconds
    await asyncio.sleep(10)
    
    # Stop everything
    await capture.stop_capture()
    await capture.cleanup()
    await client.stop_streaming_recognition(session_id)
    await client.cleanup()

asyncio.run(speech_to_text_example())
```

## 🛠️ Troubleshooting

### Common Issues

1. **PyAudio Installation Failed**
   ```bash
   # macOS
   brew install portaudio
   pip install pyaudio
   
   # Ubuntu/Debian
   sudo apt-get install portaudio19-dev
   pip install pyaudio
   
   # Windows
   pip install pipwin
   pipwin install pyaudio
   ```

2. **No Audio Devices Found**
   ```python
   # Check available devices
   from src.audio.capture import PyAudioCapture
   
   capture = PyAudioCapture()
   await capture.initialize()
   device_info = capture._get_device_info()
   print(f"Input devices: {device_info['input_devices']}")
   ```

3. **System Audio Not Available**
   - Windows: Enable "Stereo Mix" in recording devices
   - macOS: Use third-party software like Soundflower or BlackHole
   - Linux: Configure PulseAudio loopback

4. **Google Cloud Authentication**
   ```bash
   # Set up service account
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   
   # Or use application default credentials
   gcloud auth application-default login
   ```

### Performance Optimization

1. **Reduce Latency**
   ```python
   # Use smaller chunk sizes
   config = {
       'chunk_size': 512,  # Smaller chunks = lower latency
       'buffer_duration': 0.5  # Shorter buffer = faster processing
   }
   ```

2. **Improve Quality**
   ```python
   # Use higher sample rate
   config = {
       'sample_rate': 44100,  # Higher quality
       'channels': 2  # Stereo for better quality
   }
   ```

3. **Handle Errors Gracefully**
   ```python
   try:
       await capture.start_capture()
   except Exception as e:
       print(f"Capture failed: {e}")
       # Fallback to different configuration
   ```

## 📚 API Reference

### PyAudioCapture

```python
class PyAudioCapture:
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024, 
                 audio_source="microphone", device_index=None)
    
    async def initialize() -> bool
    async def start_capture() -> bool
    async def stop_capture()
    async def cleanup()
    
    def set_audio_callback(self, callback)
    def get_stats() -> Dict[str, Any]
```

### AudioStreamHandler

```python
class AudioStreamHandler:
    async def start_audio_session(self, session_id, websocket_callback, 
                                 audio_config=None) -> bool
    async def stop_audio_session(self, session_id) -> bool
    async def get_session_status(self, session_id) -> Dict[str, Any]
    async def list_active_sessions() -> Dict[str, Any]
```

### GoogleCloudClient

```python
class GoogleCloudClient:
    def __init__(self, project_id=None, credentials_path=None)
    
    async def initialize() -> bool
    async def start_streaming_recognition(self, session_id, language_code="en-US") -> bool
    async def process_audio_chunk(self, session_id, audio_data) -> Optional[Dict]
    async def stop_streaming_recognition(self, session_id) -> Dict[str, Any]
    
    async def translate_text(self, text, target_language="en") -> Dict[str, Any]
    async def synthesize_speech(self, text, language_code="en-US") -> Optional[bytes]
```

## 🔄 Next Steps

1. **Run Tests**: Use `python test_audio_processing.py` to validate setup
2. **Configure Sources**: Set up microphone and system audio
3. **Add Google Cloud**: Configure credentials for speech-to-text
4. **Test Integration**: Try the full pipeline with real audio
5. **Optimize Performance**: Adjust settings for your use case

## 🎉 You're Ready!

The audio processing system is now set up and ready to use. You can:

- ✅ Capture audio from microphone or system
- ✅ Stream audio data via WebSocket
- ✅ Process speech-to-text with Google Cloud
- ✅ Translate text in real-time
- ✅ Monitor audio quality and performance

Start with the test script to validate everything works, then integrate with your application! 