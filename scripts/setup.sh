#!/bin/bash

# SpeakTogether Initial Setup Script
# Prepares the development environment for the first time

set -e

echo "🌍 SpeakTogether - Initial Setup"
echo "================================"
echo "AI-Powered Real-Time Audio Captions & Translation"
echo ""

# Check if running from project root
if [ ! -f "README.md" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
echo "🔍 Checking system requirements..."

# Check Python
if ! command_exists python3; then
    echo "❌ Python 3.9+ is required"
    echo "   Please install Python 3.9 or later from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION found"

# Check Node.js
if ! command_exists node; then
    echo "❌ Node.js 18+ is required"
    echo "   Please install Node.js 18 or later from https://nodejs.org"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js $NODE_VERSION found"

# Check npm
if ! command_exists npm; then
    echo "❌ npm is required (usually comes with Node.js)"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo "✅ npm $NPM_VERSION found"

echo ""
echo "📦 Setting up project dependencies..."

# Setup backend
echo ""
echo "🐍 Setting up Python backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "✅ Python virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Create environment file
echo "⚙️  Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo ""
    echo "⚠️  IMPORTANT: Please edit backend/.env with your Google Cloud credentials:"
    echo "   - GOOGLE_APPLICATION_CREDENTIALS: Path to your service account key"
    echo "   - GOOGLE_CLOUD_PROJECT: Your GCP project ID"
    echo "   - ADK_API_KEY: Your Google ADK API key"
    echo "   - ADK_PROJECT_ID: Your ADK project ID"
    echo ""
else
    echo "✅ Environment file already exists"
fi

# Setup frontend
echo ""
echo "⚡ Setting up Electron frontend..."
cd ../frontend

# Install Node.js dependencies
echo "📥 Installing Node.js dependencies..."
npm install

# Create logs directory
echo "📁 Creating directories..."
cd ..
mkdir -p logs
mkdir -p config

echo ""
echo "✨ Setup Complete!"
echo "=================="
echo ""
echo "🎯 Next Steps:"
echo ""
echo "1. 🔑 Configure Google Cloud credentials:"
echo "   • Edit backend/.env with your Google Cloud project details"
echo "   • Download service account key from Google Cloud Console"
echo "   • Enable required APIs: Speech-to-Text, Translation, Text-to-Speech"
echo ""
echo "2. 🚀 Start the development environment:"
echo "   ./scripts/run-dev.sh"
echo ""
echo "3. 🧪 Test the application:"
echo "   • Backend API: http://localhost:8000/docs"
echo "   • Electron app will open automatically"
echo ""
echo "📚 For more information:"
echo "   • Read README.md for detailed instructions"
echo "   • Check docs/ directory for additional documentation"
echo ""
echo "🎉 Ready for hackathon development!"
echo ""

# Make run script executable
chmod +x scripts/run-dev.sh

echo "✅ All scripts are now executable"
echo ""
echo "Happy coding! 🚀" 