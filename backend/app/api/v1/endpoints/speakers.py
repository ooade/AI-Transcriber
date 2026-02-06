import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .... import schemas
from ....database import get_db
from ....services.event_service import event_service
from ....services.speaker_service import SpeakerService
from ....schemas.speaker import (
    SpeakerResponse,
    SpeakerListResponse,
    SpeakerUpdate,
    TranscriptWithSpeakersResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/transcriptions/{transcription_id}/speakers",
    response_model=SpeakerListResponse,
    tags=["speakers"],
    summary="Get speakers for a transcription",
)
async def get_speakers(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve all detected speakers for a transcription with their statistics.

    Returns speaker labels, LLM-extracted names, speaking duration, and segment counts.
    """
    try:
        speakers = SpeakerService.get_speakers_by_transcription(db, transcription_id)

        return SpeakerListResponse(
            speakers=[SpeakerResponse.model_validate(s) for s in speakers],
            total_speakers=len(speakers),
        )
    except Exception as e:
        logger.error(f"Failed to get speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/transcriptions/{transcription_id}/speakers/{speaker_id}/rename",
    response_model=SpeakerResponse,
    tags=["speakers"],
    summary="Rename a speaker",
)
async def rename_speaker(
    transcription_id: str,
    speaker_id: str,
    update_data: SpeakerUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a speaker's name (typically after LLM extraction for user refinement).

    Validates that the speaker belongs to the specified transcription.
    """
    try:
        # Verify speaker exists and belongs to transcription
        speaker = SpeakerService.get_speaker_by_id(db, speaker_id)
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")

        if speaker.transcription_id != transcription_id:
            raise HTTPException(
                status_code=403,
                detail="Speaker does not belong to this transcription"
            )

        # Update speaker
        updated_speaker = SpeakerService.update_speaker(db, speaker_id, update_data)

        # Publish update event for SSE
        event_service.publish_event(
            channel=f"app:transcription_{transcription_id}",
            event_type="speaker_updated",
            payload={
                "speaker_id": speaker_id,
                "speaker_name": updated_speaker.speaker_name,
                "message": f"Renamed {updated_speaker.speaker_label} to {updated_speaker.speaker_name}",
            },
        )

        return SpeakerResponse.model_validate(updated_speaker)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/transcriptions/{transcription_id}/transcript/with-speakers",
    response_model=TranscriptWithSpeakersResponse,
    tags=["speakers"],
    summary="Get transcript with speaker information",
)
async def get_transcript_with_speakers(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve complete transcript with speaker labels and statistics.

    Includes speaker names, segment timing, and confidence scores.
    """
    try:
        result = SpeakerService.get_transcript_with_speakers(db, transcription_id)

        if not result:
            raise HTTPException(status_code=404, detail="Transcription not found")

        return TranscriptWithSpeakersResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transcript with speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/transcriptions/{transcription_id}/speakers/{speaker_id}",
    response_model=SpeakerResponse,
    tags=["speakers"],
    summary="Get speaker details",
)
async def get_speaker_details(
    transcription_id: str,
    speaker_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a specific speaker.
    """
    try:
        speaker = SpeakerService.get_speaker_by_id(db, speaker_id)

        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")

        if speaker.transcription_id != transcription_id:
            raise HTTPException(
                status_code=403,
                detail="Speaker does not belong to this transcription"
            )

        return SpeakerResponse.model_validate(speaker)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get speaker details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
