# Google Cloud Setup for SpeakTogether

This guide helps you set up Google Cloud integration for real speech-to-text, translation, and text-to-speech capabilities.

## Prerequisites

1. **Google Cloud Account**: Sign up at [cloud.google.com](https://cloud.google.com)
2. **Google Cloud Project**: Create a new project or use existing one
3. **Billing Enabled**: Required for Speech, Translation, and Text-to-Speech APIs

## Step-by-Step Setup

### 1. Create Google Cloud Project

```bash
# Install Google Cloud CLI (if not already installed)
# Visit: https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Create new project (optional)
gcloud projects create speaktogether-app --name="SpeakTogether App"

# Set current project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
# Enable Speech-to-Text API
gcloud services enable speech.googleapis.com

# Enable Translation API
gcloud services enable translate.googleapis.com

# Enable Text-to-Speech API
gcloud services enable texttospeech.googleapis.com
```

### 3. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create speaktogether-service \
    --description="Service account for SpeakTogether app" \
    --display-name="SpeakTogether Service"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:speaktogether-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:speaktogether-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/translate.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:speaktogether-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/texttospeech.client"
```

### 4. Download Service Account Key

```bash
# Create and download service account key
gcloud iam service-accounts keys create credentials.json \
    --iam-account=speaktogether-service@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Move to secure location
mkdir -p backend/credentials
mv credentials.json backend/credentials/
```

### 5. Environment Configuration

Create `backend/.env` file:

```bash
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=./credentials/credentials.json
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID

# Optional: Regional settings
GOOGLE_CLOUD_REGION=us-central1
```

### 6. Verify Setup

Test your configuration:

```bash
cd backend
source venv/bin/activate

# Test Google Cloud integration
python test_google_cloud.py
```

## Configuration Options

### Speech-to-Text Settings

In `backend/src/google_cloud_client.py`, you can customize:

```python
config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,  # Match PyAudio settings
    language_code="en-US",    # Default language
    enable_automatic_punctuation=True,
    enable_word_time_offsets=True,
    model="latest_long"       # Best accuracy for longer audio
)
```

### Translation Settings

```python
# Auto-detect source language
source_language = "auto"

# Target language for translation
target_language = "en"

# Formal vs casual translation
# (Currently using Google's default style)
```

## Security Best Practices

1. **Never commit credentials.json** to version control
2. **Use environment variables** for all sensitive data
3. **Limit service account permissions** to required roles only
4. **Rotate service account keys** regularly
5. **Monitor API usage** and set up billing alerts

## API Quotas and Limits

### Speech-to-Text
- **Free tier**: 60 minutes/month
- **Paid tier**: $0.006 per 15 seconds
- **Rate limit**: 1000 requests/minute

### Translation
- **Free tier**: 500,000 characters/month
- **Paid tier**: $20 per 1M characters
- **Rate limit**: 100 requests/100 seconds

### Text-to-Speech
- **Free tier**: 1M characters/month
- **Paid tier**: $4 per 1M characters
- **Rate limit**: 1000 requests/minute

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   # Check credentials path
   echo $GOOGLE_APPLICATION_CREDENTIALS
   
   # Verify file exists and is readable
   ls -la backend/credentials/credentials.json
   ```

2. **API Not Enabled**
   ```bash
   # List enabled APIs
   gcloud services list --enabled
   
   # Enable missing APIs
   gcloud services enable speech.googleapis.com
   ```

3. **Permission Denied**
   ```bash
   # Check service account permissions
   gcloud projects get-iam-policy YOUR_PROJECT_ID
   ```

4. **Quota Exceeded**
   - Monitor usage in Google Cloud Console
   - Check billing account is active
   - Consider upgrading to paid tier

### Debug Mode

Enable detailed logging:

```python
# In backend/src/google_cloud_client.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Cost Optimization

1. **Use regional endpoints** when possible
2. **Implement smart buffering** to reduce API calls
3. **Cache translation results** for repeated text
4. **Set up billing alerts** at $5, $20, $50
5. **Monitor usage patterns** and optimize accordingly

## Integration Status

The SpeakTogether app will automatically:

✅ **Detect Google Cloud availability** on startup  
✅ **Fall back to mock services** if credentials are missing  
✅ **Use real PyAudio capture** with real Google Cloud processing  
✅ **Combine real audio + real transcription** for optimal results  
✅ **Display service status** in version endpoint  

Check integration status:
```bash
curl http://localhost:8000/api/version
```

Expected response with Google Cloud enabled:
```json
{
  "version": "0.3.0-unified",
  "service": "SpeakTogether Unified API",
  "status": "running",
  "features": {
    "pyaudio_available": true,
    "google_cloud_available": true,
    "real_audio_capture": true,
    "real_transcription": true,
    "real_translation": true
  }
}
``` 