# AI Transcriber Product Overview

AI Transcriber is a real-time audio transcription application with intelligent post-processing capabilities. The system provides high-accuracy speech-to-text conversion with automatic error correction, contextual understanding, and meeting summarization.

## Core Features

- **Real-time Audio Recording**: Browser-based audio capture with noise reduction
- **High-Accuracy Transcription**: Uses Faster-Whisper for speech-to-text conversion
- **Intelligent Post-Processing**: Automatic error correction using LLM context
- **Meeting Summarization**: AI-powered content analysis and key point extraction
- **Session Management**: Persistent storage with correction history and analytics
- **Multi-Modal Interface**: Electron desktop app with web-based UI

## Architecture

The application follows a microservices architecture with:
- **Frontend**: React + TypeScript + Electron desktop application
- **Backend**: FastAPI-based REST API with async task processing
- **Processing Pipeline**: Celery-based background jobs for transcription and analysis
- **Storage**: PostgreSQL for persistence, Redis for caching and task queues
- **AI Services**: Faster-Whisper for transcription, Ollama for LLM processing

## Target Use Cases

- Meeting transcription and summarization
- Interview recording and analysis
- Lecture and presentation capture
- Voice memo processing with intelligent organization