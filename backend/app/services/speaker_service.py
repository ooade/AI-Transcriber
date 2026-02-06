import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Speaker, TranscriptionSegment, Transcription
from ..schemas.speaker import SpeakerCreate, SpeakerUpdate, SpeakerResponse

logger = logging.getLogger(__name__)


class SpeakerService:
    """Service layer for speaker management."""

    @staticmethod
    def create_speaker(db: Session, speaker: SpeakerCreate) -> Speaker:
        """Create a new speaker record."""
        db_speaker = Speaker(**speaker.model_dump())
        db.add(db_speaker)
        db.commit()
        db.refresh(db_speaker)
        logger.info(f"Created speaker: {db_speaker.id} ({db_speaker.speaker_label})")
        return db_speaker

    @staticmethod
    def create_speakers_batch(
        db: Session,
        transcription_id: str,
        speaker_names_map: Dict[str, str]
    ) -> List[Speaker]:
        """
        Batch create speakers from LLM-extracted names.

        Args:
            db: Database session
            transcription_id: ID of transcription
            speaker_names_map: Mapping like {"Speaker 1": "Alice", "Speaker 2": "Bob"}

        Returns:
            List of created Speaker objects
        """
        speakers = []
        for speaker_label, speaker_name in speaker_names_map.items():
            speaker = SpeakerCreate(
                transcription_id=transcription_id,
                speaker_label=speaker_label,
                speaker_name=speaker_name,
            )
            db_speaker = Speaker(**speaker.model_dump())
            db.add(db_speaker)
            speakers.append(db_speaker)

        db.commit()
        for speaker in speakers:
            db.refresh(speaker)

        logger.info(f"Created {len(speakers)} speakers for transcription {transcription_id}")
        return speakers

    @staticmethod
    def get_speakers_by_transcription(
        db: Session,
        transcription_id: str
    ) -> List[Speaker]:
        """Get all speakers for a transcription."""
        speakers = db.query(Speaker).filter(
            Speaker.transcription_id == transcription_id
        ).all()
        return speakers

    @staticmethod
    def get_speaker_by_id(db: Session, speaker_id: str) -> Optional[Speaker]:
        """Get a specific speaker."""
        return db.query(Speaker).filter(Speaker.id == speaker_id).first()

    @staticmethod
    def update_speaker(
        db: Session,
        speaker_id: str,
        update_data: SpeakerUpdate
    ) -> Optional[Speaker]:
        """Update speaker (primarily for renaming)."""
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if not speaker:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(speaker, key, value)

        db.commit()
        db.refresh(speaker)
        logger.info(f"Updated speaker {speaker_id}: {update_dict}")
        return speaker

    @staticmethod
    def calculate_speaker_stats(db: Session, speaker_id: str) -> Tuple[float, int]:
        """
        Calculate total duration and segment count for a speaker.

        Returns:
            Tuple of (total_duration, segment_count)
        """
        result = db.query(
            func.sum(
                TranscriptionSegment.end_time - TranscriptionSegment.start_time
            ).label("total_duration"),
            func.count(TranscriptionSegment.id).label("segment_count")
        ).filter(
            TranscriptionSegment.speaker_id == speaker_id
        ).first()

        total_duration = float(result.total_duration) if result.total_duration else 0.0
        segment_count = result.segment_count if result.segment_count else 0

        return total_duration, segment_count

    @staticmethod
    def update_speaker_stats(db: Session, speaker_id: str) -> Speaker:
        """Update speaker duration and segment count from segments."""
        total_duration, segment_count = SpeakerService.calculate_speaker_stats(db, speaker_id)

        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if speaker:
            speaker.total_duration = total_duration
            speaker.segment_count = segment_count
            db.commit()
            db.refresh(speaker)
            logger.info(
                f"Updated speaker stats: {speaker_id} "
                f"({total_duration:.1f}s, {segment_count} segments)"
            )

        return speaker

    @staticmethod
    def delete_speakers_by_transcription(db: Session, transcription_id: str) -> int:
        """Delete all speakers for a transcription."""
        count = db.query(Speaker).filter(
            Speaker.transcription_id == transcription_id
        ).delete()
        db.commit()
        logger.info(f"Deleted {count} speakers for transcription {transcription_id}")
        return count

    @staticmethod
    def get_transcript_with_speakers(
        db: Session,
        transcription_id: str
    ) -> Optional[Dict]:
        """
        Get complete transcript with speaker information.

        Returns:
            Dict with segments and speakers
        """
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            return None

        # Get all segments with speaker info
        segments = db.query(TranscriptionSegment).filter(
            TranscriptionSegment.transcription_id == transcription_id
        ).order_by(TranscriptionSegment.start_time).all()

        # Get speakers
        speakers = db.query(Speaker).filter(
            Speaker.transcription_id == transcription_id
        ).all()

        # Build response with speaker labels
        segment_responses = []
        total_duration = 0.0

        for segment in segments:
            speaker_label = None
            speaker_name = None

            if segment.speaker_id:
                speaker = next((s for s in speakers if s.id == segment.speaker_id), None)
                if speaker:
                    speaker_label = speaker.speaker_label
                    speaker_name = speaker.speaker_name

            segment_duration = segment.end_time - segment.start_time
            total_duration += segment_duration

            segment_responses.append({
                "id": segment.id,
                "text": segment.text,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "speaker_label": speaker_label,
                "speaker_name": speaker_name,
                "confidence": segment.confidence,
            })

        return {
            "segments": segment_responses,
            "speakers": [
                {
                    "id": s.id,
                    "speaker_label": s.speaker_label,
                    "speaker_name": s.speaker_name,
                    "total_duration": s.total_duration,
                    "segment_count": s.segment_count,
                }
                for s in speakers
            ],
            "total_duration": total_duration,
            "speaker_count": len(speakers),
        }
