# Technology Stack & Development Guide

## Backend Stack

- **Framework**: FastAPI (Python 3.x)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Task Queue**: Celery with Redis broker
- **Caching**: Redis
- **Audio Processing**: Faster-Whisper, librosa, pydub, noisereduce
- **LLM Integration**: Ollama (local inference)
- **Server**: Uvicorn ASGI server

### Key Backend Dependencies
```
fastapi, uvicorn, sqlalchemy, psycopg2-binary, alembic
faster-whisper, sounddevice, numpy, scipy, noisereduce
celery, redis, httpx, python-multipart, pydantic-settings
```

## Frontend Stack

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Desktop**: Electron
- **Styling**: Tailwind CSS 4.x
- **State Management**: React Query (@tanstack/react-query)
- **Audio Processing**: @ricky0123/vad-react, @shiguredo/rnnoise-wasm
- **UI Components**: Lucide React icons, Framer Motion animations
- **Package Manager**: Yarn (enforced via preinstall hook)

## Development Commands

### Full Stack Development
```bash
# Start entire development environment
./dev.sh

# This script:
# - Cleans up ports 8000, 5173
# - Starts Celery worker in background
# - Starts FastAPI server on port 8000
# - Starts Vite dev server + Electron on port 5173
```

### Backend Only
```bash
cd backend
source venv/bin/activate
./run_dev.sh

# Or manually:
celery -A app.celery_app worker --loglevel=error --pool=solo &
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Only
```bash
cd frontend
yarn dev              # Vite dev server only
yarn dev:electron     # Vite + Electron
yarn build            # Production build
yarn lint             # ESLint
```

### Database Management
```bash
cd backend
alembic upgrade head   # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

## Infrastructure

### Development Services
- **PostgreSQL**: Port 5432 (docker-compose)
- **Redis**: Port 6379 (docker-compose)
- **FastAPI**: Port 8000
- **Vite Dev Server**: Port 5173
- **Ollama**: Port 11434 (external service)

### Docker Compose
```bash
docker-compose up -d   # Start PostgreSQL + Redis
```

## Environment Configuration

Backend uses pydantic-settings with `.env` file support:
- `REDIS_HOST`, `REDIS_PORT` - Redis connection
- `OLLAMA_BASE_URL` - LLM service endpoint
- `LLM_MODEL` - Model name (default: llama3:8b)
- Database connection via SQLAlchemy URL

## Build & Deployment

- **Frontend**: `yarn build` creates production bundle in `dist/`
- **Backend**: Standard Python deployment with requirements.txt
- **Database**: Alembic handles schema migrations
- **Assets**: Audio files served from `temp/` directory with secure path validation