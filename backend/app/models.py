import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, TIMESTAMP, JSON, ForeignKey, Boolean, Integer, Text, Index
from sqlalchemy.orm import relationship
from .database import Base

class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    user_id = Column(String, default=lambda: str(uuid.uuid4())) # Placeholder
    audio_file_path = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    duration_seconds = Column(Float)
    language = Column(String, default="en")

    raw_transcript = relationship("RawTranscript", back_populates="transcription", uselist=False)
    corrected_transcripts = relationship("CorrectedTranscript", back_populates="transcription")
    summary = relationship("MeetingSummary", back_populates="transcription", uselist=False)
    errors = relationship("TranscriptionError", back_populates="transcription")
    speakers = relationship("Speaker", back_populates="transcription", cascade="all, delete-orphan")
    segments = relationship("TranscriptionSegment", back_populates="transcription", cascade="all, delete-orphan")

class RawTranscript(Base):
    __tablename__ = "raw_transcripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"))
    content = Column(Text, nullable=False)
    word_timestamps = Column(JSON)
    confidence_scores = Column(JSON)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    transcription = relationship("Transcription", back_populates="raw_transcript")

class CorrectedTranscript(Base):
    __tablename__ = "corrected_transcripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"))
    content = Column(Text, nullable=False)
    word_timestamps = Column(JSON)  # Aligned word timestamps from raw transcript
    corrected_at = Column(TIMESTAMP, default=datetime.utcnow)
    correction_type = Column(String) # 'full_edit', 'word_fix', 'phrase_fix'

    transcription = relationship("Transcription", back_populates="corrected_transcripts")

class TranscriptionError(Base):
    __tablename__ = "transcription_errors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"))
    error_type = Column(String) # 'substitution', 'deletion', 'insertion'
    predicted_text = Column(Text)
    correct_text = Column(Text)
    predicted_start_time = Column(Float)
    predicted_end_time = Column(Float)
    context_before = Column(Text)
    context_after = Column(Text)
    audio_quality_score = Column(Float)
    background_noise_level = Column(Float)
    speaker_id = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    transcription = relationship("Transcription", back_populates="errors")

class TrainingSample(Base):
    __tablename__ = "training_samples"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    audio_segment_path = Column(String)
    ground_truth_text = Column(Text)
    audio_quality = Column(String)
    has_background_noise = Column(Boolean)
    speaker_accent = Column(String)
    times_used_in_training = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP)
    source_transcription_id = Column(String, ForeignKey("transcriptions.id"))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"))
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    model_used = Column(String)
    meeting_type = Column(String) # e.g., "Daily Standup", "Strategic Review"

    transcription = relationship("Transcription", back_populates="summary")


class Speaker(Base):
    """Detected speaker in a transcription."""
    __tablename__ = "speakers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"), nullable=False, index=True)
    speaker_label = Column(String)  # "Speaker 1", "Speaker 2", etc.
    speaker_name = Column(String, nullable=True)  # LLM-extracted or user-assigned name
    total_duration = Column(Float, default=0.0)  # Total speaking time in seconds
    segment_count = Column(Integer, default=0)  # Number of speech segments
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    transcription = relationship("Transcription", back_populates="speakers")


class TranscriptionSegment(Base):
    """Transcript segment with speaker information."""
    __tablename__ = "transcription_segments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"), nullable=False, index=True)
    speaker_id = Column(String, ForeignKey("speakers.id"), nullable=True, index=True)
    text = Column(Text)
    start_time = Column(Float)
    end_time = Column(Float)
    confidence = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    transcription = relationship("Transcription", back_populates="segments")
    speaker = relationship("Speaker")

