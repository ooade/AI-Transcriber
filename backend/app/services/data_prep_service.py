from pydub import AudioSegment
import os
import logging
import uuid
from sqlalchemy.orm import Session
from ..models import Transcription, TrainingSample, TranscriptionError

logger = logging.getLogger(__name__)

class TrainingDataService:
    def __init__(self, db: Session, samples_dir: str = "temp/training_samples"):
        self.db = db
        self.samples_dir = samples_dir
        os.makedirs(self.samples_dir, exist_ok=True)

    def prepare_samples_for_transcription(self, transcription_id: str):
        """
        Processes all errors for a transcription and generates .wav slices.
        """
        transcription = self.db.query(Transcription).filter(Transcription.id == transcription_id).first()
        if not transcription or not os.path.exists(transcription.audio_file_path):
            logger.error(f"Cannot find audio for transcription {transcription_id}")
            return

        # Load full audio
        try:
            audio = AudioSegment.from_wav(transcription.audio_file_path)
        except Exception as e:
            logger.error(f"Error loading audio {transcription.audio_file_path}: {e}")
            return

        errors = self.db.query(TranscriptionError).filter(
            TranscriptionError.transcription_id == transcription_id
        ).all()

        samples_created = 0
        for error in errors:
            # We want a 2-4s slice around the error for context
            # error.predicted_start_time is in seconds
            start_ms = max(0, (error.predicted_start_time - 1.0) * 1000)
            end_ms = min(len(audio), (error.predicted_end_time + 1.0) * 1000)

            # Slice and Export
            segment = audio[start_ms:end_ms]
            sample_filename = f"sample_{error.id}.wav"
            sample_path = os.path.join(self.samples_dir, sample_filename)

            try:
                segment.export(sample_path, format="wav")

                # Create TrainingSample record
                sample = TrainingSample(
                    id=str(uuid.uuid4()),
                    audio_segment_path=sample_path,
                    ground_truth_text=error.correct_text,
                    source_transcription_id=transcription_id,
                    audio_quality="high" # Placeholder
                )
                self.db.add(sample)
                samples_created += 1
            except Exception as e:
                logger.error(f"Failed to export sample for error {error.id}: {e}")

        self.db.commit()
        logger.info(f"Generated {samples_created} training samples for {transcription_id}")
        return samples_created
