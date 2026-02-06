# AI Transcriber – Copilot Instructions

## Big-picture architecture

- Backend is FastAPI + Celery; frontend is React (Vite) packaged with Electron. Backend API lives in [backend/app/main.py](backend/app/main.py), Celery config in [backend/app/celery_app.py](backend/app/celery_app.py), and worker tasks in [backend/app/tasks.py](backend/app/tasks.py).
- Transcription pipeline: POST /transcribe saves a temp file and triggers a Celery chain (transcribe -> auto-correct -> summarize). See [backend/app/main.py](backend/app/main.py) and task chain in [backend/app/tasks.py](backend/app/tasks.py).
- Real-time updates: tasks publish Redis Pub/Sub events via the event service in [backend/app/services/event_service.py](backend/app/services/event_service.py). The frontend consumes SSE at /events and syncs React Query cache in [frontend/src/contexts/ServerEventsContext.tsx](frontend/src/contexts/ServerEventsContext.tsx).
- AI services: Whisper transcription is in [backend/app/services/transcription.py](backend/app/services/transcription.py). Summaries and context keywords use Ollama via [backend/app/core/llm.py](backend/app/core/llm.py) and prompts in [backend/app/core/prompts.py](backend/app/core/prompts.py). Ollama is optional; the system degrades to transcription-only.

## Data flow essentials

- Upload -> /transcribe -> Celery tasks -> DB persistence -> SSE -> UI. Persistence lives in [backend/app/services/persistence_service.py](backend/app/services/persistence_service.py) and models in [backend/app/models.py](backend/app/models.py).
- SSE payloads must include `task_id` (or `id`) and `message` for progress. See how the frontend updates the cache in [frontend/src/contexts/ServerEventsContext.tsx](frontend/src/contexts/ServerEventsContext.tsx).
- For long audio, chunked transcription is used (AudioChunker -> parallel chunk tasks -> merge). See [backend/app/tasks.py](backend/app/tasks.py).

## Developer workflows

- Full dev stack (backend + worker + Electron frontend): run [dev.sh](dev.sh).
- Backend API + worker (SQLite broker fallback): run [backend/run_dev.sh](backend/run_dev.sh). Worker-only: [backend/run_worker.sh](backend/run_worker.sh).
- Frontend dev: run the scripts in [frontend/package.json](frontend/package.json) (notably dev:electron).
- Services: Redis is required for SSE + Celery in normal mode. docker-compose provides Redis/Postgres in [docker-compose.yml](docker-compose.yml), but the backend defaults to SQLite in [backend/app/database.py](backend/app/database.py).

## Project-specific conventions

- Task progress is propagated through Redis Pub/Sub; when adding background tasks, publish events using the `app:task_<id>` channel with payloads that align with the frontend cache update logic in [frontend/src/contexts/ServerEventsContext.tsx](frontend/src/contexts/ServerEventsContext.tsx).
- Warm-up of Whisper happens both on API startup and worker startup (see [backend/app/main.py](backend/app/main.py) and [backend/app/tasks.py](backend/app/tasks.py)). Keep heavy model init in these locations.
- Caching for LLM context and hotwords is centralized in [backend/app/core/cache.py](backend/app/core/cache.py) with TTLs in [backend/app/core/config.py](backend/app/core/config.py). Prefer the `cached` decorator for LLM-related lookups.
- Frontend orchestration relies on `useTranscription` / `useTranscriptionTask` hooks in [frontend/src/hooks/useTranscription.ts](frontend/src/hooks/useTranscription.ts) and the Recording context in [frontend/src/contexts/RecordingContext.tsx](frontend/src/contexts/RecordingContext.tsx). Wire new UI flows into these patterns rather than ad-hoc fetch calls.

## Integration points

- API base URL is configured via VITE_API_URL in [frontend/src/config.ts](frontend/src/config.ts).
- Audio files are served from the temp directory via a secure endpoint in [backend/app/main.py](backend/app/main.py).
- LLM + context extraction is optional; see health state handling in [backend/app/services/health_service.py](backend/app/services/health_service.py) and LLM circuit breaker in [backend/app/core/llm.py](backend/app/core/llm.py).
