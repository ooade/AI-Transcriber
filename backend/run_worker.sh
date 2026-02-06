#!/bin/bash

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found! Please create one in ./backend/venv"
    exit 1
fi

echo "================================================================"
echo "  🚀 AI Transcriber Worker Launcher"
echo "================================================================"

if [ "$1" == "transcription" ]; then
    ./run_transcription_worker.sh
    exit 0
elif [ "$1" == "processing" ]; then
    ./run_processing_worker.sh
    exit 0
fi

echo "Which worker specific would you like to run?"
echo "  1) Transcription Worker (Heavy, pool=solo)"
echo "  2) Processing Worker (Fast, pool=threads)"
echo "  3) Run BOTH (Dev Mode - 2 windows needed)"
echo ""
read -p "Select option [1-3]: " option

case $option in
    1) ./run_transcription_worker.sh ;;
    2) ./run_processing_worker.sh ;;
    3)
        echo "Starting both workers in background..."
        ./run_transcription_worker.sh > transcription.log 2>&1 &
        echo "Started Transcription Worker (PID: $!)"
        ./run_processing_worker.sh > processing.log 2>&1 &
        echo "Started Processing Worker (PID: $!)"
        echo "Workers running in background. Tail logs with: tail -f *.log"
        ;;
    *) echo "Invalid option"; exit 1 ;;
esac
