import shutil
import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ....core.config import settings
from ....services.health_service import SystemHealthService, ServiceStatus

# Create a logger (structlog will intercept this if configured)
logger = logging.getLogger(__name__)

router = APIRouter()
health_service = SystemHealthService()

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("en"),
    backend: str = Form("faster-whisper")
):
    """
    Handles file upload and triggers async transcription.

    Args:
        file: Audio file
        language: Language code (default: en)
        backend: Transcription backend (faster-whisper or whisper-cpp)

    Returns:
        task_id for polling
    """
    if health_service.transcriber_status != ServiceStatus.READY:
        raise HTTPException(status_code=503, detail="Transcriber service is initializing")

    # Hardcoded model enforcement (Principal Requirement)
    # UI can only select backend, not model.
    MODEL_SIZE = "large-v3"

    logger.info(f"Transcribe endpoint called with: backend={backend}, model={MODEL_SIZE}, language={language}")

    # Validate backend
    valid_backends = ["faster-whisper", "whisper-cpp"]
    if backend not in valid_backends:
        raise HTTPException(status_code=400, detail=f"Invalid backend. Must be one of: {valid_backends}")

    # File validation
    SUPPORTED_AUDIO_TYPES = [
        "audio/wav",
        "audio/mpeg",
        "audio/mp4",
        "audio/ogg",
        "audio/flac",
        "audio/x-m4a",
        "audio/webm",
    ]
    MAX_FILE_SIZE_MB = settings.MAX_FILE_SIZE_MB
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Check file content type
    if file.content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file.content_type}. Supported formats: WAV, MP3, M4A, OGG, FLAC, WebM",
        )

    # Check file size
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        file_size_mb = file.size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit. Your file is {file_size_mb:.1f}MB.",
        )

    # 1. Save uploaded file to temp
    filename = f"{uuid.uuid4()}_{file.filename}"
    upload_path = os.path.abspath(os.path.join("temp", filename))

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Verify file size after writing
    actual_size = os.path.getsize(upload_path)
    if actual_size > MAX_FILE_SIZE_BYTES:
        os.remove(upload_path)
        actual_size_mb = actual_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit. Your file is {actual_size_mb:.1f}MB.",
        )

    # 2. Convert WebM to WAV if needed (frontend sends WebM with .wav extension)
    try:
        from pydub import AudioSegment
        # Try to detect actual format and convert if needed
        audio = AudioSegment.from_file(upload_path)
        if not upload_path.endswith('.wav') or audio.frame_rate is None:
            # Convert to proper WAV
            wav_path = upload_path.rsplit('.', 1)[0] + '.wav'
            audio.export(wav_path, format='wav')
            # Remove original file if different
            if wav_path != upload_path:
                os.remove(upload_path)
                upload_path = wav_path
            logger.info(f"Converted audio to WAV format: {wav_path}")
    except Exception as e:
        logger.warning(f"Audio format detection/conversion failed: {e}")
        # Continue with original file, transcriber will handle it

    # 3. Trigger Task Chain (Transcription -> AutoCorrect -> Summary)
    from ....tasks import transcribe_audio_task, run_auto_correct_task, generate_summary_task

    # Define the post-processing workflow
    post_processing_workflow = run_auto_correct_task.s()

    logger.info(f"Dispatching task with args: [{upload_path}, {language}, {backend}, {MODEL_SIZE}]")

    task = transcribe_audio_task.apply_async(
        args=[upload_path, language, backend, MODEL_SIZE]
    )

    return {"task_id": task.id, "status": "PENDING"}

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Securely serve audio files from the temp directory."""
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join("temp", safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    from fastapi.responses import FileResponse
    return FileResponse(file_path)
