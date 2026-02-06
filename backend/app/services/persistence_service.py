from sqlalchemy.orm import Session
from ..models import Transcription, RawTranscript, CorrectedTranscript, Speaker, TranscriptionSegment
from ..core.text_utils import clean_text
import uuid
import json
from datetime import datetime
from typing import Optional, Dict

class PersistenceService:
    def __init__(self, db: Session):
        self.db = db

    def get_friendly_title(self, date: datetime) -> str:
        """Generates a title like Meeting@Today, Meeting@Yesterday, or Meeting@Date."""
        now = datetime.utcnow()
        diff = now.date() - date.date()

        if diff.days == 0:
            friendly_date = "Today"
        elif diff.days == 1:
            friendly_date = "Yesterday"
        else:
            friendly_date = date.strftime("%d/%m/%Y")

        return f"Meeting@{friendly_date}"

    def save_transcription(self, result: dict, audio_path: str, speakers: Optional[Dict[str, str]] = None):
        """
        Saves the transcription result and metadata to the database.
        Optionally saves speaker data if provided.
        """
        transcription_id = str(uuid.uuid4())

        # 1. Create Transcription record
        new_transcription = Transcription(
            id=transcription_id,
            title=self.get_friendly_title(datetime.utcnow()),
            audio_file_path=audio_path,
            duration_seconds=result.get("duration"),
            language=result.get("language")
        )
        self.db.add(new_transcription)

        # 2. Create RawTranscript record
        # result["segments"] contains the word-level timestamps if requested
        content = result.get("text", "")

        # Clean the raw transcript to remove triple quotes and other artifacts
        content = clean_text(content)

        # Extract word timestamps if they exist
        word_timestamps = []
        if "segments" in result:
            for segment in result["segments"]:
                if "words" in segment:
                    word_timestamps.extend(segment["words"])

        raw_transcript = RawTranscript(
            id=str(uuid.uuid4()),
            transcription_id=transcription_id,
            content=content,
            word_timestamps=word_timestamps
        )
        self.db.add(raw_transcript)

        # 3. Create/Update Speaker records
        # Logic: We must create Speaker records for ALL unique labels found in segments,
        # even if we don't have human names for them yet.
        unique_labels = set()
        if "segments" in result:
             for s in result["segments"]:
                 if "speaker" in s:
                     unique_labels.add(s["speaker"])

        # Merge with keys from speakers arg if present (though unlikely in new flow)
        if speakers:
            unique_labels.update(speakers.keys())

        speaker_map = {} # label -> Speaker object

        for label in unique_labels:
            # Check if name is provided in the optional speakers map
            name = speakers.get(label) if speakers else None

            # Create Speaker record
            speaker = Speaker(
                id=str(uuid.uuid4()),
                transcription_id=transcription_id,
                speaker_label=label,
                speaker_name=name, # Might be None, that's fine (deferred naming)
                total_duration=0.0,
                segment_count=0
            )
            self.db.add(speaker)
            speaker_map[label] = speaker

        self.db.flush()  # Flush to get IDs

        # 4. Create TranscriptionSegment records with speaker info
        segments = result.get("segments", [])
        for segment in segments:
            speaker_label = segment.get("speaker", "Unknown")
            # Now we are guaranteed to have a speaker_id if the label exists
            speaker_obj = speaker_map.get(speaker_label)
            speaker_id = speaker_obj.id if speaker_obj else None

            trans_segment = TranscriptionSegment(
                id=str(uuid.uuid4()),
                transcription_id=transcription_id,
                speaker_id=speaker_id,
                text=segment.get("text", ""),
                start_time=segment.get("start", 0),
                end_time=segment.get("end", 0),
                confidence=segment.get("confidence")
            )
            self.db.add(trans_segment)

        self.db.commit()

        # 5. Update speaker stats after all segments saved
        if speaker_map:
            for label, speaker in speaker_map.items():
                # Calculate stats from segments
                speaker_segments = self.db.query(TranscriptionSegment).filter(
                    TranscriptionSegment.speaker_id == speaker.id
                ).all()

                if speaker_segments:
                    speaker.total_duration = sum(s.end_time - s.start_time for s in speaker_segments)
                    speaker.segment_count = len(speaker_segments)

            self.db.commit()

        self.db.refresh(new_transcription)
        return new_transcription

    def update_speaker_names(self, transcription_id: str, speaker_names_map: Dict[str, str]):
        """
        Updates speaker names for a transcription.
        """
        try:
            # Fetch existing speakers for this transcription
            db_speakers = self.db.query(Speaker).filter(
                Speaker.transcription_id == transcription_id
            ).all()

            updates = 0
            for spk in db_speakers:
                if spk.speaker_label in speaker_names_map:
                    spk.speaker_name = speaker_names_map[spk.speaker_label]
                    updates += 1

            if updates > 0:
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise e

    def get_history(self, limit: int = 20):
        """
        Returns a list of recent transcriptions.
        """
        return self.db.query(Transcription).order_by(Transcription.created_at.desc()).limit(limit).all()

    def get_transcription_details(self, transcription_id: str):
        """
        Returns full transcription details including the raw transcript.
        """
        return self.db.query(Transcription).filter(Transcription.id == transcription_id).first()

    def add_correction(self, transcription_id: str, content: str, correction_type: str = "full_edit"):
        """
        Saves a corrected version of the transcript.
        """
        correction = CorrectedTranscript(
            id=str(uuid.uuid4()),
            transcription_id=transcription_id,
            content=content,
            correction_type=correction_type,
            corrected_at=datetime.utcnow()
        )
        self.db.add(correction)
        self.db.commit()
        self.db.refresh(correction)
        return correction

    def update_title(self, transcription_id: str, title: str):
        """Updates the title of a transcription."""
        item = self.db.query(Transcription).filter(Transcription.id == transcription_id).first()
        if item:
            item.title = title
            self.db.commit()
            self.db.refresh(item)
        return item
