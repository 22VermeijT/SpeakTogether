#!/bin/bash

# SpeakTogether Development Setup Script
# Starts both backend Python server and Electron frontend

set -e

echo "🚀 Starting SpeakTogether Development Environment"
echo "=============================================="

# Check if running from project root
if [ ! -f "README.md" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

echo "✅ All dependencies found"

# Setup backend
echo ""
echo "🐍 Setting up Python backend..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Check for environment file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env || echo "⚠️  Please create .env file manually with your Google Cloud credentials"
fi

# Start backend server in background
echo "🚀 Starting FastAPI backend server..."
uvicorn main:app --host localhost --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Setup frontend
echo ""
echo "⚡ Setting up Electron frontend..."
cd ../frontend

# Install Node.js dependencies
if [ ! -d "node_modules" ]; then
    echo "📥 Installing Node.js dependencies..."
    npm install
fi

# Start frontend
echo "🚀 Starting Electron application..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

echo ""
echo "✨ SpeakTogether is now running!"
echo "================================"
echo "🌐 Backend API: http://localhost:8000"
echo "🖥️  Frontend: Electron app should open automatically"
echo "📊 API Documentation: http://localhost:8000/docs"
echo ""
echo "💡 Tips:"
echo "   - Use Cmd/Ctrl+D to open the Agent Dashboard"
echo "   - Check backend logs in this terminal"
echo "   - Use Cmd/Ctrl+C to stop both services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down SpeakTogether..."
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "electron" 2>/dev/null || true
    
    echo "✅ Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Keep script running and show logs
echo "📋 Backend logs (Ctrl+C to stop):"
echo "=================================="

# Wait for processes to finish
wait 