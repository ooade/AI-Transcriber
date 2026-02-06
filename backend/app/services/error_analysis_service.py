import difflib
import logging
import uuid
from sqlalchemy.orm import Session
from ..models import TranscriptionError, RawTranscript

logger = logging.getLogger(__name__)

class ErrorAnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_correction(self, transcription_id: str, corrected_content: str):
        """
        Compares the raw transcript with the corrected content and stores errors.
        """
        # 1. Fetch raw transcript
        raw_transcript = self.db.query(RawTranscript).filter(
            RawTranscript.transcription_id == transcription_id
        ).first()

        if not raw_transcript:
            logger.warning(f"No raw transcript found for {transcription_id}")
            return []

        # 2. Tokenize (simple split for now)
        raw_words = [w["word"].strip() for w in raw_transcript.word_timestamps]
        corrected_words = corrected_content.split()

        matcher = difflib.SequenceMatcher(None, raw_words, corrected_words)
        errors = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            # tag can be 'replace', 'delete', 'insert', 'equal'
            if tag == 'equal':
                continue

            # Context for better debugging/training
            context_before = " ".join(raw_words[max(0, i1-5):i1])
            context_after = " ".join(raw_words[i2:min(len(raw_words), i2+5)])

            if tag == 'replace' or tag == 'delete':
                # Map back to timestamps
                start_time = raw_transcript.word_timestamps[i1]["start"]
                end_time = raw_transcript.word_timestamps[i2-1]["end"]

                error = TranscriptionError(
                    id=str(uuid.uuid4()),
                    transcription_id=transcription_id,
                    error_type=tag,
                    predicted_text=" ".join(raw_words[i1:i2]),
                    correct_text=" ".join(corrected_words[j1:j2]),
                    predicted_start_time=start_time,
                    predicted_end_time=end_time,
                    context_before=context_before,
                    context_after=context_after
                )
                self.db.add(error)
                errors.append(error)

            elif tag == 'insert':
                # For insertions, the "time" is between words
                # If at start, time is 0. If at end, time is the end of last word.
                # Otherwise, it's between i1-1 and i1
                if i1 == 0:
                    time_pos = 0.0
                else:
                    time_pos = raw_transcript.word_timestamps[i1-1]["end"]

                error = TranscriptionError(
                    id=str(uuid.uuid4()),
                    transcription_id=transcription_id,
                    error_type=tag,
                    predicted_text="",
                    correct_text=" ".join(corrected_words[j1:j2]),
                    predicted_start_time=time_pos,
                    predicted_end_time=time_pos,
                    context_before=context_before,
                    context_after=context_after
                )
                self.db.add(error)
                errors.append(error)

        self.db.commit()
        logger.info(f"Analyzed {transcription_id}: found {len(errors)} errors.")
        return errors
