# Project Structure & Organization

## Root Directory Layout

```
├── backend/           # Python FastAPI application
├── frontend/          # React + Electron application  
├── .kiro/            # Kiro AI assistant configuration
├── .agent/           # Agent-specific rules and guidelines
├── dev.sh            # Full-stack development startup script
└── docker-compose.yml # PostgreSQL + Redis services
```

## Backend Structure (`backend/`)

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # SQLAlchemy database setup
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── tasks.py             # Celery background tasks
│   ├── celery_app.py        # Celery application configuration
│   ├── core/
│   │   ├── config.py        # Application settings (pydantic-settings)
│   │   ├── cache.py         # Redis caching utilities
│   │   ├── llm.py           # LLM integration (Ollama)
│   │   └── prompts.py       # LLM prompt templates
│   └── services/            # Business logic services
│       ├── transcription.py      # Audio-to-text processing
│       ├── audio_processing.py   # Audio preprocessing
│       ├── context_service.py    # LLM context management
│       ├── accuracy_service.py   # Transcription quality metrics
│       ├── auto_correction_service.py  # LLM-based error correction
│       ├── summarizer_service.py      # Meeting summarization
│       ├── persistence_service.py     # Database operations
│       ├── event_service.py           # Server-sent events
│       └── health_service.py          # System status monitoring
├── alembic/                 # Database migrations
├── temp/                    # Temporary audio file storage
├── requirements.txt         # Python dependencies
├── run_dev.sh              # Backend development script
└── transcriber.db          # SQLite database (development)
```

## Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── main.tsx                    # React application entry point
│   ├── App.tsx                     # Main application component
│   ├── config.ts                   # Frontend configuration
│   ├── components/
│   │   ├── AudioRecorder.tsx       # Recording interface
│   │   ├── TranscriptEditor.tsx    # Text editing and correction
│   │   ├── HistoryView.tsx         # Session history browser
│   │   ├── InsightsView.tsx        # Analytics dashboard
│   │   ├── SystemStatusBanner.tsx  # Health status display
│   │   ├── common/                 # Shared UI components
│   │   ├── layout/                 # Layout components
│   │   ├── ui/                     # Base UI components
│   │   └── visualizations/         # Data visualization components
│   ├── pages/
│   │   ├── RecorderPage.tsx        # Main recording interface
│   │   ├── HistoryPage.tsx         # Session management
│   │   └── EditorPage.tsx          # Transcript editing
│   ├── contexts/
│   │   ├── RecordingContext.tsx    # Recording state management
│   │   └── ServerEventsContext.tsx # SSE connection management
│   ├── hooks/
│   │   ├── useTranscription.ts     # Transcription API integration
│   │   └── useSystemStatus.ts      # Health monitoring
│   ├── workers/
│   │   └── audio.worker.ts         # Web Worker for audio processing
│   └── utils/                      # Utility functions
├── electron/                       # Electron main process
├── public/                         # Static assets
├── package.json                    # Dependencies and scripts
└── vite.config.ts                  # Vite build configuration
```

## Key Architectural Patterns

### Backend Patterns
- **Service Layer**: Business logic isolated in `services/` directory
- **Repository Pattern**: Database operations in `persistence_service.py`
- **Task Queue**: Long-running operations handled by Celery tasks
- **Event Streaming**: Server-sent events for real-time updates
- **Health Monitoring**: Centralized system status in `health_service.py`

### Frontend Patterns
- **Context Providers**: Global state management for recording and events
- **Custom Hooks**: API integration and state management
- **Page Components**: Route-level components in `pages/`
- **Compound Components**: Complex UI broken into focused components
- **Web Workers**: Audio processing offloaded from main thread

### File Naming Conventions
- **Backend**: Snake_case for Python files and functions
- **Frontend**: PascalCase for React components, camelCase for utilities
- **Services**: Descriptive names ending in `_service.py`
- **Components**: Descriptive names with `.tsx` extension
- **Hooks**: Prefixed with `use` (e.g., `useTranscription.ts`)

### Import Organization
- **Backend**: Relative imports within app, absolute for external packages
- **Frontend**: Relative imports for local files, absolute for node_modules
- **Services**: Import from `services/` directory, not direct file paths