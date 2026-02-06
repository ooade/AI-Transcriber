from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .... import schemas
from ....database import get_db
from ....services.persistence_service import PersistenceService
from ....tasks import run_feedback_loop_task, generate_summary_task
from ....core.text_utils import clean_text, extract_transcript_only, parse_summary

router = APIRouter()


@router.get("/history", response_model=List[schemas.HistoryItem])
async def get_history(db: Session = Depends(get_db)):
    persistence = PersistenceService(db)
    items = persistence.get_history()

    response = []
    for item in items:
        # Determine best text for preview
        preview_text = ""
        if item.corrected_transcripts:
            # Get latest correction
            latest = sorted(item.corrected_transcripts, key=lambda x: x.corrected_at, reverse=True)[0]
            preview_text = extract_transcript_only(clean_text(latest.content))
        elif item.raw_transcript:
            preview_text = extract_transcript_only(clean_text(item.raw_transcript.content))

        # Parse summary if available
        summary_data = parse_summary(item.summary.content) if item.summary else {"summary": None, "meeting_type": None}

        response.append({
            "id": item.id,
            "title": item.title or persistence.get_friendly_title(item.created_at),
            "created_at": item.created_at,
            "duration_seconds": item.duration_seconds,
            "language": item.language,
            "preview": preview_text[:300] + "..." if len(preview_text) > 300 else preview_text,
            "summary": summary_data["summary"],
            "meeting_type": summary_data["meeting_type"]
        })
    return response

@router.get("/transcriptions/{transcription_id}")
async def get_transcription(transcription_id: str, db: Session = Depends(get_db)):
    persistence = PersistenceService(db)
    item = persistence.get_transcription_details(transcription_id)
    if not item:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Prioritize corrected transcript, fall back to raw transcript
    if item.corrected_transcripts:
        latest_corrected = sorted(item.corrected_transcripts, key=lambda x: x.corrected_at, reverse=True)[0]
        transcript_text = extract_transcript_only(clean_text(latest_corrected.content))
        # Use aligned timestamps from corrected transcript, fall back to empty if not available
        word_timestamps = latest_corrected.word_timestamps or []
    elif item.raw_transcript:
        transcript_text = extract_transcript_only(clean_text(item.raw_transcript.content))
        word_timestamps = item.raw_transcript.word_timestamps or []
    else:
        transcript_text = ""
        word_timestamps = []

    # Parse summary if available
    summary_data = parse_summary(item.summary.content) if item.summary else {"summary": None, "meeting_type": None}

    # Include raw transcript in response
    return {
        "id": item.id,
        "title": item.title or persistence.get_friendly_title(item.created_at),
        "created_at": item.created_at,
        "audio_file_path": item.audio_file_path,
        "duration_seconds": item.duration_seconds,
        "language": item.language,
        "text": transcript_text,
        "word_timestamps": word_timestamps,
        "corrections": [
            {"content": extract_transcript_only(clean_text(c.content)), "corrected_at": c.corrected_at}
            for c in item.corrected_transcripts
        ],
        "summary": summary_data["summary"],
        "meeting_type": summary_data["meeting_type"],
        "summary_model": item.summary.model_used if item.summary else None
    }

@router.patch("/transcriptions/{transcription_id}/correct")
async def correct_transcription(transcription_id: str, request: schemas.CorrectionRequest, db: Session = Depends(get_db)):
    persistence = PersistenceService(db)

    correction = persistence.add_correction(transcription_id, request.content, request.correction_type)

    # PHASE 4: Background Feedback Loop
    run_feedback_loop_task.delay(transcription_id, request.content)

    return correction

@router.patch("/transcriptions/{transcription_id}/title")
async def update_transcription_title(transcription_id: str, request: schemas.TitleUpdateRequest, db: Session = Depends(get_db)):
    persistence = PersistenceService(db)
    item = persistence.update_title(transcription_id, request.title)
    if not item:
        raise HTTPException(status_code=404, detail="Transcription not found")
    return {"status": "success", "title": item.title}

@router.post("/transcriptions/{transcription_id}/summarize")
async def generate_summary_manual(transcription_id: str, db: Session = Depends(get_db)):
    """Manually trigger summary generation for a transcription."""
    persistence = PersistenceService(db)
    item = persistence.get_transcription_details(transcription_id)
    if not item:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Determine best text to summarize
    text = ""
    if item.corrected_transcripts:
        latest = sorted(item.corrected_transcripts, key=lambda x: x.corrected_at, reverse=True)[0]
        text = latest.content
    elif item.raw_transcript:
        text = item.raw_transcript.content

    if not text:
         raise HTTPException(status_code=400, detail="No transcript text available to summarize")

    # Trigger with optimized payload
    payload = {
        "id": transcription_id,
        "text": text
    }
    generate_summary_task.delay(payload)

    return {"status": "triggered", "message": "Summary generation started in background"}
