#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found! Please create one in ./backend/venv"
    exit 1
fi

# Environment logic
export USE_SQLITE_BROKER=true

# 1. Start Celery Worker in background
echo "👷 Starting Background Worker..."
celery -A app.celery_app worker --loglevel=error --pool=solo > temp/worker.log 2>&1 &
WORKER_PID=$!

# 2. Setup cleanup trap
cleanup() {
    echo "🛑 Shutting down processes..."
    kill $WORKER_PID
    exit
}
trap cleanup SIGINT SIGTERM

# 3. Start API Server
echo "🚀 Starting API Server (at http://localhost:8000)..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
