#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    # Kill all child processes (the backend)
    pkill -P $$
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

echo "🚀 Starting AI Transcriber Dev Environment..."

# 1. Kill duplicate services
echo "🧹 Cleaning up ports and workers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
pkill -f "celery worker" 2>/dev/null

# 2. Start Backend & Celery
echo "📦 Starting Backend & Worker..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Error: Backend virtual environment not found in ./backend/venv"
    exit 1
fi

# Run Celery Worker in background
echo "🐝 Starting Celery Worker..."
celery -A app.celery_app worker --pool=threads --loglevel=info --concurrency=2 &
WORKER_PID=$!

# Run uvicorn in the background
echo "🚀 Starting API Server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a moment
sleep 3

# 3. Start Frontend
echo "🖥️  Starting Frontend (Electron + Vite)..."
cd frontend
yarn dev:electron
cleanup
