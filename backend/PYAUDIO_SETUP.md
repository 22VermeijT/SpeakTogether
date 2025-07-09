# PyAudio Setup Guide for SpeakTogether

This guide provides platform-specific instructions for installing PyAudio, which is required for real-time audio capture in SpeakTogether.

## 🍎 macOS Installation

### Option 1: Using Homebrew (Recommended)
```bash
# Install PortAudio system dependency
brew install portaudio

# Install PyAudio in your virtual environment
source venv/bin/activate
pip install pyaudio
```

### Option 2: Using MacPorts
```bash
# Install PortAudio
sudo port install portaudio

# Install PyAudio
pip install pyaudio
```

### Troubleshooting macOS
If you encounter compilation errors:
```bash
# Try with specific include/library paths
pip install --global-option='build_ext' \
    --global-option='-I/opt/homebrew/include' \
    --global-option='-L/opt/homebrew/lib' \
    pyaudio
```

## 🐧 Linux (Ubuntu/Debian) Installation

### Install System Dependencies
```bash
# Update package list
sudo apt-get update

# Install PortAudio development files
sudo apt-get install portaudio19-dev python3-dev

# Install PyAudio
pip install pyaudio
```

### For CentOS/RHEL/Fedora
```bash
# Install development tools and PortAudio
sudo yum install gcc gcc-c++ portaudio-devel python3-devel
# OR for newer versions:
sudo dnf install gcc gcc-c++ portaudio-devel python3-devel

# Install PyAudio
pip install pyaudio
```

## 🪟 Windows Installation

### Option 1: Using pip (Usually works)
```cmd
pip install pyaudio
```

### Option 2: Pre-compiled Wheel
If pip installation fails, download a pre-compiled wheel:
```cmd
# Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# Download appropriate .whl file for your Python version
pip install PyAudio-0.2.11-cp39-cp39-win_amd64.whl
```

### Option 3: Using Conda
```cmd
conda install pyaudio
```

## 🔧 Verification

After installation, verify PyAudio works:

```python
import pyaudio

# Create PyAudio instance
p = pyaudio.PyAudio()

# List audio devices
print("Available audio devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f"  {i}: {info['name']} ({info['maxInputChannels']} channels)")

# Clean up
p.terminate()
print("PyAudio is working correctly!")
```

## 🚨 Common Issues and Solutions

### Permission Errors on macOS
```bash
# Grant microphone permission to Terminal/iTerm2
# System Preferences > Security & Privacy > Privacy > Microphone
# Check the box for your terminal application
```

### Audio Device Access Issues
```python
# Test microphone access with minimal code
import pyaudio
import numpy as np

def test_microphone():
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        print("Recording for 2 seconds...")
        for _ in range(32):  # 2 seconds at 16kHz/1024
            data = stream.read(1024)
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.sqrt(np.mean(audio_data**2))
            print(f"Volume: {volume:.0f}")
        
        stream.stop_stream()
        stream.close()
        
    finally:
        p.terminate()

if __name__ == "__main__":
    test_microphone()
```

### PyAudio Compilation Errors

#### On macOS with M1/M2 chips:
```bash
# Set architecture for Homebrew
export ARCHFLAGS="-arch arm64"
pip install pyaudio
```

#### General compilation issues:
```bash
# Clean pip cache and retry
pip cache purge
pip install --no-cache-dir pyaudio
```

## 🎯 SpeakTogether Integration

Once PyAudio is installed, you can run the real audio version:

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Install all dependencies (including PyAudio)
pip install -r requirements.txt

# Run the PyAudio-enabled backend
python main_simple_with_pyaudio.py
```

## 📊 Audio Configuration

The SpeakTogether PyAudio implementation uses these default settings:
- **Sample Rate**: 16kHz (optimal for speech recognition)
- **Channels**: 1 (mono)
- **Format**: 16-bit PCM
- **Chunk Size**: 1024 samples
- **Buffer Duration**: 1.0 seconds

These can be customized in the frontend when starting audio capture:

```javascript
audioSocket.send(JSON.stringify({
  type: 'start_capture',
  session_id: sessionId,
  audio_config: {
    sample_rate: 16000,    // Can be 8000, 16000, 22050, 44100
    channels: 1,           // 1 for mono, 2 for stereo
    chunk_size: 1024,      // Smaller = lower latency, higher CPU
    buffer_duration: 1.0   // Seconds to buffer before processing
  }
}))
```

## 🧪 Testing Your Setup

Run this test script to verify everything works:

```bash
# In the backend directory
python -c "
from src.audio.capture import PyAudioCapture
import asyncio

async def test():
    capture = PyAudioCapture()
    if await capture.initialize():
        print('✅ PyAudio initialized successfully')
        devices = capture._get_device_info()
        print(f'📱 Found {len(devices.get(\"available_devices\", []))} input devices')
    else:
        print('❌ PyAudio initialization failed')

asyncio.run(test())
"
```

## 💡 Production Deployment

For production deployment:

1. **Use system packages** when possible (apt, yum, brew)
2. **Test audio permissions** on the target platform
3. **Monitor resource usage** - audio capture can be CPU intensive
4. **Handle device disconnection** gracefully
5. **Configure proper buffer sizes** for your latency requirements

## 📞 Support

If you encounter issues:

1. Check the console output for specific error messages
2. Verify microphone permissions are granted
3. Test with the minimal PyAudio examples above
4. Check that your audio device is not in use by other applications

For SpeakTogether-specific issues, check the backend logs:
```bash
# Run with debug logging
python main_simple_with_pyaudio.py --log-level debug
``` 