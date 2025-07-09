# SpeakTogether 🌍

AI-Powered Real-Time Audio Captions & Translation Desktop Application

## 🚀 Quick Start (Hackathon Ready!)

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Cloud Account with ADK access
- System audio permissions

### Setup (5 minutes)
```bash
# 1. Clone and setup Python backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup environment variables
cp .env.example .env
# Edit .env with your Google Cloud credentials

# 3. Setup Electron frontend
cd ../frontend
npm install

# 4. Start the application
cd ../
./scripts/run-dev.sh
```

## 🏗️ Architecture

- **Frontend**: Electron app (system audio capture + UI)
- **Backend**: Python FastAPI + Google ADK agents
- **Communication**: WebSocket streaming + REST API
- **AI**: Google Cloud Speech-to-Text, Translation, TTS

## 🤖 Agent System (Google ADK)

1. **Audio Context Agent** - Analyzes source & quality
2. **Translation Strategy Agent** - Context-aware style decisions  
3. **Quality Control Agent** - Accuracy monitoring
4. **Voice Synthesis Agent** - Natural dubbing
5. **Master Orchestrator** - Coordinates all agents

## 📁 Project Structure

```
SpeakTogether/
├── backend/              # Python FastAPI + ADK agents
├── frontend/             # Electron desktop app
├── scripts/              # Development and deployment scripts
├── docs/                 # Additional documentation
└── config/               # Configuration files
```

## 🎯 Core Features

- ✅ Real-time system audio capture
- ✅ Multi-agent decision-making (visible to users)
- ✅ Context-aware translations (formal vs casual)
- ✅ Voice dubbing with speaker matching
- ✅ Accessibility-focused design

## 🏆 Hackathon Goals

Built for Google-sponsored AI competition to showcase:
- Google ADK multi-agent framework
- Practical cultural bridge application
- Real-time AI processing pipeline
- User-friendly accessibility technology

---

**Making every conversation accessible to everyone, everywhere.** 🌟