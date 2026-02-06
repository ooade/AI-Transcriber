# AI Transcriber

An intelligent transcription and analysis tool that leverages OpenAI's Whisper for speech-to-text conversion, with automatic correction, summarization, and speaker diarization capabilities.

## Features

- **Speech-to-Text Transcription**: Uses OpenAI's Whisper model to accurately convert audio to text
- **Auto-Correction**: Automatically corrects transcription errors and improves accuracy
- **Summarization**: Generates concise summaries of transcribed content using LLM capabilities
- **Speaker Diarization**: Identifies and labels different speakers in multi-speaker audio
- **Real-Time Updates**: Provides live progress updates via Server-Sent Events (SSE)
- **Audio Chunking**: Handles long audio files by processing them in parallel chunks
- **Context Extraction**: Extracts keywords and context from transcriptions
- **Persistent Storage**: Saves transcriptions and analysis results to a database

## Technology Stack

**Backend**:

- FastAPI (REST API)
- Celery (distributed task queue)
- Redis/SQLite (message broker and persistence)
- Whisper (speech recognition)
- Ollama (local LLM support)

**Frontend**:

- React (UI framework)
- Vite (build tool)
- Electron (desktop application)
- TypeScript
- React Query (state management)

## Quick Start

### Full Stack (Backend + Worker + Electron Frontend)

```bash
./dev.sh
```

### Backend API + Worker Only

```bash
cd backend
./run_dev.sh
```

### Frontend Development

```bash
cd frontend
npm run dev:electron
```

### Docker

#### Using Docker Compose (with Redis and PostgreSQL)

```bash
docker-compose up
```

This starts:

- Redis (port 6379) - message broker for Celery
- PostgreSQL (port 5432) - main database
- Backend API and worker services

#### Building Individual Docker Images

```bash
# Backend
cd backend
docker build -t ai-transcriber-backend .

# Frontend
cd frontend
docker build -t ai-transcriber-frontend .
```

#### Running Containers

```bash
# Backend API
docker run -p 8000:8000 ai-transcriber-backend

# Frontend
docker run -p 5173:5173 ai-transcriber-frontend
```

## Project Structure

- `backend/` - FastAPI application, Celery tasks, and services
- `frontend/` - React/Vite frontend with Electron wrapper
- `docker-compose.yml` - Docker services (Redis, PostgreSQL)

## ⚠️ Important Notice

**This project was developed through rapid iteration ("vibe coding") and should NOT be deployed to production without thorough code review.**

Before production deployment, ensure:

- [ ] Complete code review of all modules
- [ ] Security audit of API endpoints and authentication
- [ ] Load testing and performance optimization
- [ ] Comprehensive unit and integration tests
- [ ] Error handling and logging improvements
- [ ] Database migration and backup strategies
- [ ] Documentation of all environment variables and dependencies
- [ ] Proper secret management (API keys, database credentials)

## Development

For detailed architecture information, see [.github/copilot-instructions.md](.github/copilot-instructions.md).

## Services

The system uses several background services:

- **Transcription Service**: Handles Whisper-based speech recognition
- **Auto-Correction Service**: Improves transcription accuracy
- **Summarization Service**: Generates summaries using LLMs
- **Speaker Diarization Service**: Identifies speakers in audio
- **Event Service**: Publishes real-time progress updates
