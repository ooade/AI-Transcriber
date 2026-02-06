import os
import asyncio
import platform
from pathlib import Path
from .celery_app import celery_app
from .services.transcription import MaxAccuracyTranscriber, WhisperCppTranscriber
from .services.error_analysis_service import ErrorAnalysisService
from .services.data_prep_service import TrainingDataService
from .services.persistence_service import PersistenceService
from .services.cleanup_service import CleanupService
from .services.auto_correction_service import AutoCorrectionService
from .services.event_service import event_service
from .services.whisper_cpp_setup import setup_whisper_cpp
from .services.speaker_diarization_service import (
    SpeakerDiarizationService,
    merge_speaker_segments_with_transcript,
)
from .services.speaker_service import SpeakerService
from .database import SessionLocal
from .core.config import settings
from .core.text_utils import parse_summary
import logging

logger = logging.getLogger(__name__)


class TranscriberCache:
    """
    Cache for transcriber instances supporting multiple backends and model sizes.
    Allows per-request backend/model selection while avoiding repeated model loading.
    """

    def __init__(self):
        self._cache = {}
        self._whisper_cpp_available = False
        self._whisper_cpp_binary = None
        self._has_metal = False
        self._has_cuda = False

    def initialize(self):
        """Initialize the cache and preload configured models."""
        logger.info("🔧 Initializing TranscriberCache...")
        logger.info(f"WHISPER_CPP_AUTO_SETUP={settings.WHISPER_CPP_AUTO_SETUP}, WHISPER_CPP_PATH={settings.WHISPER_CPP_PATH}")

        # Check whisper.cpp availability
        # First check if manually configured path exists
        if settings.WHISPER_CPP_PATH:
            import platform
            from pathlib import Path
            binary_path = Path(settings.WHISPER_CPP_PATH)
            if binary_path.exists() and os.access(binary_path, os.X_OK):
                logger.info(f"✅ Found whisper.cpp binary at configured path: {binary_path}")
                self._whisper_cpp_available = True
                self._whisper_cpp_binary = str(binary_path)
                self._has_metal = platform.system() == "Darwin"
                self._has_cuda = False
                # Check for nvidia-smi for CUDA
                try:
                    import subprocess
                    result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
                    self._has_cuda = result.returncode == 0
                except:
                    pass
                accel = "Metal" if self._has_metal else ("CUDA" if self._has_cuda else "CPU")
                logger.info(f"✅ whisper.cpp available with {accel} acceleration")
            else:
                logger.warning(f"⚠️  Configured WHISPER_CPP_PATH not found or not executable: {settings.WHISPER_CPP_PATH}")

        # Fall back to auto-setup if not manually configured
        elif settings.WHISPER_CPP_AUTO_SETUP:
            try:
                binary_path, has_metal, has_cuda = setup_whisper_cpp()
                if binary_path:
                    self._whisper_cpp_available = True
                    self._whisper_cpp_binary = str(binary_path)
                    self._has_metal = has_metal
                    self._has_cuda = has_cuda
                    accel = "Metal" if has_metal else ("CUDA" if has_cuda else "CPU")
                    logger.info(f"✅ whisper.cpp available with {accel} acceleration")
                else:
                    logger.warning("⚠️  whisper.cpp setup failed, only faster-whisper will be available")
            except Exception as e:
                logger.warning(f"⚠️  whisper.cpp setup error: {e}. Only faster-whisper will be available")

        # Preload configured models
        preload_models = [m.strip() for m in settings.PRELOAD_MODELS.split(",") if m.strip()]
        for model_size in preload_models:
            # Preload faster-whisper
            try:
                self.get_transcriber("faster-whisper", model_size)
                logger.info(f"✅ Preloaded faster-whisper/{model_size}")
            except Exception as e:
                logger.error(f"❌ Failed to preload faster-whisper/{model_size}: {e}")

            # Preload whisper.cpp if available
            if self._whisper_cpp_available:
                try:
                    self.get_transcriber("whisper-cpp", model_size)
                    logger.info(f"✅ Preloaded whisper-cpp/{model_size}")
                except Exception as e:
                    logger.error(f"❌ Failed to preload whisper-cpp/{model_size}: {e}")

        logger.info("✅ TranscriberCache initialization complete")

    def get_transcriber(self, backend: str = "faster-whisper", model_size: str = "large-v3"):
        """
        Get or create transcriber for specified backend and model size.

        Args:
            backend: "faster-whisper" or "whisper-cpp"
            model_size: Model size (tiny, base, small, medium, large-v3)

        Returns:
            Transcriber instance (MaxAccuracyTranscriber or WhisperCppTranscriber)
        """
        cache_key = f"{backend}:{model_size}"

        if cache_key not in self._cache:
            logger.info(f"Creating new transcriber: {cache_key}")

            if backend == "faster-whisper":
                transcriber = MaxAccuracyTranscriber(model_size=model_size)
                transcriber.warm_up()
                self._cache[cache_key] = transcriber

            elif backend == "whisper-cpp":
                if not self._whisper_cpp_available:
                    logger.warning(f"whisper-cpp not available, falling back to faster-whisper/{model_size}")
                    return self.get_transcriber("faster-whisper", model_size)

                transcriber = WhisperCppTranscriber(
                    model_size=model_size,
                    whisper_cpp_path=self._whisper_cpp_binary,
                    auto_setup=False  # Already set up
                )
                transcriber.warm_up()
                self._cache[cache_key] = transcriber

            else:
                raise ValueError(f"Unknown backend: {backend}")

        return self._cache[cache_key]

    def is_backend_available(self, backend: str) -> bool:
        """Check if a backend is available."""
        if backend == "faster-whisper":
            return True
        elif backend == "whisper-cpp":
            return self._whisper_cpp_available
        return False

    def get_available_backends(self):
        """Get list of available backends with their capabilities."""
        # Parse enabled backends from settings
        enabled_backends = [b.strip().lower() for b in settings.ENABLED_BACKENDS.split(",") if b.strip()]

        backends = {}

        # Include faster-whisper if enabled
        if "faster-whisper" in enabled_backends:
            backends["faster-whisper"] = {
                "available": True,
                "acceleration": "CPU/CUDA",
                "models": ["tiny", "base", "small", "medium", "large-v3"]
            }

        # Include whisper-cpp if enabled
        if "whisper-cpp" in enabled_backends:
            if self._whisper_cpp_available:
                accel = "Metal" if self._has_metal else ("CUDA" if self._has_cuda else "CPU")
                backends["whisper-cpp"] = {
                    "available": True,
                    "acceleration": accel,
                    "models": ["tiny", "base", "small", "medium", "large-v3"]
                }
            else:
                # whisper-cpp not initialized - show as unavailable with hint
                backends["whisper-cpp"] = {
                    "available": False,
                    "acceleration": "CPU/Metal/CUDA (disabled - enable in .env)",
                    "models": ["tiny", "base", "small", "medium", "large-v3"]
                }

        return backends


# Initialize cache and preload models
# Initialize cache and preload models
transcriber_cache = TranscriberCache()

from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize resources when a worker process starts."""
    logger.info("👷 Worker process initialized. Setting up backends...")
    try:
        transcriber_cache.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize transcriber cache: {e}")

# Initialize speaker diarization service (lazy load on first use)
speaker_service = None

def get_speaker_service():
    """Lazy initialize speaker diarization service."""
    global speaker_service
    if speaker_service is None:
        speaker_service = SpeakerDiarizationService(
            huggingface_token=os.getenv("HUGGINGFACE_TOKEN")
        )
    return speaker_service

# Legacy support: keep reference to default transcriber
# REFACTOR: Avoid eager loading. Tasks should use cache directly.
transcriber = None

@celery_app.task(
    bind=True,
    name="app.tasks.transcribe_audio_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,
    max_retries=3
)
def transcribe_audio_task(self, audio_path: str, language: str = "en", backend: str = "faster-whisper", model_size: str = "large-v3"):
    """Background task for high-accuracy transcription."""
    logger.info(f"Starting transcription for {audio_path} (backend: {backend}, model: {model_size})")
    logger.info(f"Task arguments - audio_path: {audio_path}, language: {language}, backend: {backend}, model_size: {model_size}")

    # Push Progress Event
    event_service.publish_event(
        channel=f"app:task_{self.request.id}",
        event_type="task_progress",
        payload={"task_id": self.request.id, "stage": "preprocessing", "message": "Preparing audio..."}
    )

    try:
        # Context/hotwords from previous recordings are disabled
        initial_prompt = None

        # Get the appropriate transcriber from cache
        transcriber = transcriber_cache.get_transcriber(backend, model_size)

        # Since transcription is CPU/GPU intensive, we run it directly in the worker
        # The transcribe method is async to support concurrency limits, so we run it synchronously here

        # Run Transcription and Diarization in PARALLEL
        # This is the biggest performance win - doing both heavy tasks at once.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Initialize variables to prevent UnboundLocalError
        speaker_segments = []
        speaker_names_map = {}

        try:
            # --- PASS 1: Context Extraction (Fast) ---
            from .services.context_service import ContextService
            context_keywords = ""

            if not settings.SKIP_CONTEXT_EXTRACTION:
                # Push Progress Event
                event_service.publish_event(
                    channel=f"app:task_{self.request.id}",
                    event_type="task_progress",
                    payload={"task_id": self.request.id, "stage": "scanning", "message": "Global Context Scan..."}
                )

                try:
                    # Use tiny model for speed
                    logger.info("⚡️ Pass 1: Running fast transcription for context...")
                    pre_transcriber = transcriber_cache.get_transcriber(backend, "tiny")

                    # Run via event loop since we're in a synchronous worker task
                    pre_result = loop.run_until_complete(pre_transcriber.transcribe(audio_path, language))
                    if not isinstance(pre_result, dict):
                        logger.warning(f"⚠️ Pre-transcription returned non-dict: {type(pre_result)}")
                        pre_text = ""
                    else:
                        pre_text = pre_result.get("text", "")

                    if pre_text and len(pre_text.split()) > settings.CONTEXT_MIN_SPEECH_LENGTH:
                        context_service = ContextService()
                        context_keywords = loop.run_until_complete(context_service.extract_context_keywords(pre_text))
                        # Ensure context_keywords is a string
                        if context_keywords and isinstance(context_keywords, str):
                            logger.info(f"✅ Extracted context for biasing: {context_keywords[:80]}...")

                            # Update progress
                            event_service.publish_event(
                                 channel=f"app:task_{self.request.id}",
                                 event_type="context_extracted",
                                 payload={"task_id": self.request.id, "keywords": context_keywords}
                            )
                except Exception as e:
                    logger.warning(f"⚠️ Context scan failed (non-blocking): {e}")
                    context_keywords = ""  # Reset to empty string on error
            else:
                logger.info("⏭️  Context extraction disabled via SKIP_CONTEXT_EXTRACTION")

            # --- PASS 2: Main Transcription (High Accuracy) ---
            event_service.publish_event(
                channel=f"app:task_{self.request.id}",
                event_type="task_progress",
                payload={"task_id": self.request.id, "stage": "transcribing", "message": "Listening & Diarizing..."}
            )

            # Use derived context as initial prompt
            final_prompt = initial_prompt
            if context_keywords and isinstance(context_keywords, str) and len(context_keywords.strip()) > 0:
                # Whisper prompt format: "Keywords: word, word, word."
                final_prompt = f"Keywords: {context_keywords}"

            # Define tasks
            transcription_coro = transcriber.transcribe(audio_path, language, initial_prompt=final_prompt)

            # Diarization is optional/graceful failure
            async def safe_diarize():
                try:
                    spk_service = get_speaker_service()
                    return await spk_service.diarize(audio_path)
                except Exception as e:
                    logger.warning(f"⚠️ Speaker detection failed (non-blocking): {e}")
                    return []

            diarization_coro = safe_diarize()

            # Run parallel
            logger.info("🚀 Starting PARALLEL transcription and diarization...")
            results = loop.run_until_complete(
                asyncio.gather(transcription_coro, diarization_coro)
            )

            result = results[0]
            if context_keywords:
                result["context_keywords"] = context_keywords

            speaker_segments = results[1]

        finally:
            loop.close()

            if speaker_segments:
                # Merge speaker info with transcript
                merged_segments = merge_speaker_segments_with_transcript(
                    result.get("segments", []),
                    speaker_segments
                )
                result["segments"] = merged_segments

                # Report generic speaker count
                speaker_count = len(set(s["speaker"] for s in speaker_segments))
                logger.info(f"Diarization complete. Found {speaker_count} generic speakers (naming deferred).")



        # Save to DB
        db = SessionLocal()
        try:
            persistence = PersistenceService(db)
            # Speakers will be identified and updated in a later task
            item = persistence.save_transcription(result, audio_path, speakers=None)

            # CRITICAL: Commit immediately to ensure transcription is persisted in DB
            # This ensures data is available in history even if downstream tasks fail
            db.commit()
            logger.info(f"✅ Transcription {item.id} persisted to database")

            # CRITICAL FIX: Add DB ID to result for downstream tasks
            result["id"] = item.id

            # Trigger Auto-Correction (Background)
            # Chain: Main STT -> Auto-Correct (using extracted context)
            logger.info(f"Triggering auto-correction pipeline for {item.id}")
            # The auto-correction task is now exclusively triggered from here
            # to avoid double-triggering from the API endpoint.
            run_auto_correct_task.delay(result)

            # Extract context keywords ASYNC (Decoupled)
            # Instead of waiting here, we launch a background task or let the auto-correct task handle it
            if result.get("text") and len(result.get("text", "").split()) >= 10:
                # We'll let the auto-correct task handle extraction if needed,
                # or trigger a dedicated extraction task here if we want to separate concerns.
                # for now, we skip the blocking call.
                pass

            # Publish Event
            # Ensure we publish to the Celery Task ID channel so the frontend receives it
            # Note: Failure to publish event should not fail the whole task
            try:
                event_service.publish_event(
                    channel=f"app:task_{self.request.id}",
                    event_type="transcription_complete",
                    payload={
                        "id": result["id"],
                        "task_id": self.request.id,
                        "status": "SUCCESS",
                        "text": result.get("text", ""),
                        "duration_seconds": result.get("duration", 0)
                    }
                )
            except Exception as event_error:
                logger.warning(f"⚠️ Failed to publish transcription_complete event: {event_error}")
                # Continue - event publication failure should not fail the task

            return result
        except Exception as db_error:
            logger.error(f"❌ Failed to save transcription to database: {db_error}")
            db.rollback()
            raise  # Re-raise to trigger retry
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Transcription task failed (attempt {self.request.retries + 1}/{self.max_retries}): {e}")

        # Publish failure event
        event_service.publish_event(
            channel=f"app:task_{self.request.id}",
            event_type="task_failed",
            payload={
                "task_id": self.request.id,
                "status": "FAILED",
                "error": str(e),
                "attempt": self.request.retries + 1,
                "max_retries": self.max_retries
            }
        )

        # Retry with exponential backoff (Celery handles this automatically with retry_backoff=True)
        # Raises Retry exception which Celery catches
        raise self.retry(exc=e, countdown=2 ** self.request.retries)  # 2s, 4s, 8s

@celery_app.task(
    name="app.tasks.run_auto_correct_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=2
)
def run_auto_correct_task(result: dict):
    """
    Orchestrates the Self-Improvement Loop.
    Accepts the result dict from transcription task (chain-compatible).
    """
    # Robust Input Handling: Accept str (ID) or dict (Result)
    transcription_id = None
    if isinstance(result, str):
        transcription_id = result
        # If we only got the ID, we might need to recreate the result dict structure for the next task
        result = {"id": transcription_id}
    elif isinstance(result, dict):
        transcription_id = result.get("id")
        # Handle nested ID bug if it sneaks in
        if isinstance(transcription_id, dict):
            transcription_id = transcription_id.get("id")

    if not transcription_id:
        logger.warning(f"Auto-correct task received invalid result: {result}")
        return result

    logger.info(f"Starting Auto-Correction Pipeline for {transcription_id}")
    db = SessionLocal()
    try:
        # 1. Auto-Correct with context keywords from this recording
        auto_service = AutoCorrectionService(db)
        context_keywords = result.get("context_keywords")
        if context_keywords:
            logger.info(f"Using on-the-fly context keywords for correction: {context_keywords[:80]}...")
        corrected_text = asyncio.run(auto_service.auto_correct(transcription_id, context_keywords))

        if corrected_text:
            # Side Effects (Not part of the main chain result structure, but triggered)
            run_feedback_loop_task.delay(transcription_id, corrected_text)

            result["auto_correct_status"] = "complete"
        # Propagate root_task_id to keep the event channel consistent
        root_task_id = result.get("root_task_id")

        # Optimization: Pass text to next task
        result["corrected_text"] = corrected_text

        # Manual Chaining: Trigger Speaker Ident Task explicitly
        # Optimization: Create a clean, minimal payload to avoid serialization issues with large segment data
        summary_payload = {
            "id": transcription_id,
            "corrected_text": result.get("corrected_text"),
            "text": result.get("text"),
            "root_task_id": root_task_id,
            "segments": result.get("segments", []) # Pass segments for speaker ID
        }

        logger.info(f"Triggering Speaker Ident Task for {transcription_id}")
        run_speaker_ident_task.delay(summary_payload)

    finally:
        db.close()

@celery_app.task(
    name="app.tasks.run_speaker_ident_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2
)
def run_speaker_ident_task(result: dict):
    """
    Background task to identify speaker names from text context.
    Chained after auto_correct_task.
    """
    # Robust Input Handling
    transcription_id = None
    if isinstance(result, str):
        transcription_id = result
        result = {"id": transcription_id}
    elif isinstance(result, dict):
        transcription_id = result.get("id")
        if isinstance(transcription_id, dict):
             transcription_id = transcription_id.get("id")

    if not transcription_id:
        logger.warning(f"Speaker ident task received invalid result")
        return result

    logger.info(f"Starting Speaker Name Resolution for {transcription_id}")

    # Push Progress Event
    root_task_id = result.get("root_task_id")
    channel_id = root_task_id if root_task_id else transcription_id
    event_service.publish_event(
        channel=f"app:task_{channel_id}",
        event_type="task_progress",
        payload={"task_id": channel_id, "id": transcription_id, "stage": "identifying_speakers", "message": "Analyzing Conversation Details..."}
    )

    db = SessionLocal()
    try:
        # Get latest data including segments
        persistence = PersistenceService(db)
        # Note: We really need the segments here. If they aren't in `result`, we should fetch from DB.
        # Ideally `result` carries them through the chain.
        # For robustness, let's fetch the transcription to get the latest state if needed,
        # but usage of passed `result` is preferred for chain performance.

        # Prefer corrected text for best name extraction
        text_to_analyze = result.get("corrected_text") or result.get("text", "")

        # Get speaker count from segments in result, or fetch?
        # Let's trust the result segments first
        segments = result.get("segments", [])
        if not segments:
             # Fallback: fetch from DB? (Omitted for speed, assuming chain integrity)
             pass

        speaker_count = len(set(s.get("speaker") for s in segments if s.get("speaker")))

        if speaker_count > 1 and text_to_analyze:
             spk_service = get_speaker_service()

             # Run sync in worker
             speaker_names_map = asyncio.run(
                 spk_service.extract_speaker_names_from_transcript(text_to_analyze, speaker_count)
             )

             if speaker_names_map:
                 logger.info(f"✅ Resolved speaker names: {speaker_names_map}")

                 # 1. Update segments in result
                 for segment in segments:
                     speaker_label = segment.get("speaker", "Unknown")
                     # Update both speaker_name and speaker if desired,
                     # but standard is to keep label in 'speaker' and name in 'speaker_name'
                     segment["speaker_name"] = speaker_names_map.get(speaker_label, speaker_label)

                 # 2. Persist updates
                 persistence.update_speaker_names(transcription_id, speaker_names_map)

                 # 3. Publish Event
                 event_service.publish_event(
                    channel=f"app:task_{channel_id}",
                    event_type="speakers_identified",
                    payload={
                        "task_id": channel_id,
                        "id": transcription_id,
                        "message": f"Identified {len(speaker_names_map)} speaker(s)",
                        "speakers": speaker_names_map,
                    },
                )

                 # Update result with modified segments
                 result["segments"] = segments

    except Exception as e:
        logger.error(f"Speaker identification failed: {e}")
        # Non-blocking failure, continue to summary

    finally:
        db.close()

    # Chain to Summary
    generate_summary_task.delay(result)
    return result


@celery_app.task(
    bind=True,
    name="app.tasks.generate_summary_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=2
)
def generate_summary_task(self, result: dict):
    """
    Background task to generate meeting summary.
    Chained after auto_correct_task.
    """
    # Robust Input Handling
    transcription_id = None
    transcript_text = None
    root_task_id = None

    if isinstance(result, str):
        transcription_id = result
        # If input is just a string, we don't have the text payload, so set result as dict for consistency return
        result = {"id": transcription_id}
    elif isinstance(result, dict):
        transcription_id = result.get("id")
        # Defensive: Handle InterfaceError where result is passed as nested dict
        if isinstance(transcription_id, dict):
             transcription_id = transcription_id.get("id")

        # Extract text optimizations
        transcript_text = result.get("corrected_text") or result.get("text")
        root_task_id = result.get("root_task_id")

    if not transcription_id:
        logger.warning("Generate summary task received missing ID")
        return result

    logger.info(f"Starting summarization task for {transcription_id}")

    # Push Progress Event
    # Use root_task_id for the channel if available (Consistent UI Tracking)
    # Fallback to transcription_id if this task was triggered independently
    channel_id = root_task_id if root_task_id else transcription_id

    event_service.publish_event(
        channel=f"app:task_{channel_id}",
        event_type="task_progress",
        payload={
            "task_id": self.request.id,
            "id": transcription_id,
            "stage": "summarizing",
            "message": "AI is Summarizing..."
        }
    )
    db = SessionLocal()
    from .services.summarizer_service import SummarizerService

    try:
        service = SummarizerService(db)

        # Optimization: Use text from previous task if available
        # Prefer corrected text, fall back to "text" (raw) if present in result
        transcript_text = result.get("corrected_text") or result.get("text")

        summary_result = asyncio.run(service.generate_summary(transcription_id, text=transcript_text))

        if summary_result:
            result["summary_status"] = "complete"
            result["meeting_type"] = summary_result.get("type", "Unknown")

            # Parse summary before publishing (same logic as REST endpoint)
            parsed = parse_summary(summary_result.get("content"))

            # Publish Event (non-blocking failure)
            try:
                event_service.publish_event(
                    channel=f"app:task_{channel_id}",
                    event_type="summary_complete",
                    payload={
                        "task_id": self.request.id,
                        "id": transcription_id,
                        "summary": parsed.get("summary"),
                        "meeting_type": parsed.get("meeting_type"),
                        "message": "Summary complete"
                    }
                )
            except Exception as event_error:
                logger.warning(f"⚠️ Failed to publish summary_complete event: {event_error}")
        else:
            result["summary_status"] = "failed"
            logger.warning(f"Summary service returned None for {transcription_id}")

        return result

    except Exception as e:
        logger.error(f"Summarization task failed: {e}", exc_info=True)
        result["summary_status"] = "failed"

        if transcription_id:
            # Publish failure event (non-blocking)
            try:
                event_service.publish_event(
                    channel=f"app:task_{root_task_id if root_task_id else transcription_id}",
                    event_type="summary_failed",
                    payload={
                        "task_id": self.request.id,
                        "id": transcription_id,
                        "error": str(e),
                        "message": f"Summary failed: {str(e)}"
                    }
                )
            except Exception as event_error:
                logger.warning(f"⚠️ Failed to publish summary_failed event: {event_error}")

        return result
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.run_feedback_loop_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=2
)
def run_feedback_loop_task(self, transcription_id: str, content: str):
    """Background task for error analysis and audio slicing."""
    logger.info(f"Starting feedback loop for {transcription_id}")

    db = SessionLocal()
    try:
        error_service = ErrorAnalysisService(db)
        data_prep = TrainingDataService(db)

        # 1. Find errors
        error_service.analyze_correction(transcription_id, content)
        # 2. Slice audio for training
        data_prep.prepare_samples_for_transcription(transcription_id)

        return {"status": "complete", "transcription_id": transcription_id}
    except Exception as e:
        logger.error(f"Feedback loop task failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(
    name="app.tasks.clean_stale_audio_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=1  # Lower retry count for maintenance task
)
def clean_stale_audio_task():
    """Periodic task to clean up old audio files."""
    logger.info("Starting stale audio cleanup...")
    try:
        cleanup = CleanupService(max_age_hours=24)
        count = cleanup.clean_stale_files()
        logger.info(f"Cleanup completed: {count} files deleted")
        return {"status": "complete", "files_deleted": count}
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        # Don't raise - cleanup failures shouldn't break other tasks
        return {"status": "failed", "error": str(e)}

@celery_app.task(
    name="app.tasks.broadcast_queue_stats_task",
    ignore_result=True
)
def broadcast_queue_stats_task():
    """
    Periodic task to fetch queue stats and broadcast via SSE.
    """
    try:
        from .services.queue_service import QueueService
        stats = QueueService.get_queue_stats()

        if stats:
            event_service.publish_event(
                channel="queue_update",
                event_type="queue_update",
                payload=stats
            )
    except Exception as e:
        logger.error(f"Failed to broadcast queue stats: {e}")

@celery_app.task(
    name="app.tasks.extract_context_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2
)
def extract_context_task(result: dict):
    """
    Background task to extract context keywords.
    Runs parallel to UI updates.
    """
    # Robust Input Handling
    transcription_id = None
    if isinstance(result, str):
        transcription_id = result
        result = {"id": transcription_id}
    elif isinstance(result, dict):
        transcription_id = result.get("id")
        if isinstance(transcription_id, dict):
             transcription_id = transcription_id.get("id")

    if not transcription_id:
        return result

    logger.info(f"Starting context extraction for {transcription_id}")

    # Check if we have text
    text = result.get("text", "")
    if not text or len(text.split()) < 10:
        logger.info("Transcript too short for context extraction")
        # Proceed to next steps without context
        # We need to trigger auto-correct even if context is empty
        run_auto_correct_task.delay(result)
        return result

    try:
        from .services.context_service import ContextService
        context_service = ContextService()

        # This is where the long LLM call happens
        context_keywords = asyncio.run(context_service.extract_context_keywords(text))

        if context_keywords:
            logger.info(f"✅ Extracted context: {context_keywords[:50]}...")
            result["context_keywords"] = context_keywords

        # Continue the chain
        run_auto_correct_task.delay(result)
        return result

    except Exception as e:
        logger.error(f"Context extraction failed: {e}")
        # Continue chain even if extraction fails
        run_auto_correct_task.delay(result)
        return result
