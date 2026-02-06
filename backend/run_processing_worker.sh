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

echo "🚀 Starting FAST Processing Worker (Queues: processing, maintenance)..."
echo "ℹ️  pool=threads, concurrency=4 (Efficient for I/O)"

# consumer for fast queues + BEAT scheduler
celery -A app.celery_app worker \
    --loglevel=info \
    --pool=threads \
    --concurrency=4 \
    --queues=processing,maintenance,celery \
    --hostname=processing_worker@%h \
    --beat
