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

echo "🚀 Starting HEAVY Transcription Worker (Queue: transcription)..."
echo "ℹ️  pool=solo, concurrency=1 (Safe for AI Models)"

# Consumer for the 'transcription' queue ONLY
# pool=solo is critical for macOS/PyTorch stability
celery -A app.celery_app worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=1 \
    --queues=transcription \
    --hostname=transcription_worker@%h
