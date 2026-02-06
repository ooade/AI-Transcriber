"""Schemas package for data validation and serialization."""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Literal
from datetime import datetime


class TranscribeRequest(BaseModel):
    """Request schema for transcription with backend selection."""
    backend: Literal["faster-whisper", "whisper-cpp"] = "faster-whisper"
    model_size: Literal["tiny", "base", "small", "medium", "large-v3"] = "large-v3"
    language: str = "en"

    @validator("backend")
    def validate_backend(cls, v):
        valid_backends = ["faster-whisper", "whisper-cpp"]
        if v not in valid_backends:
            raise ValueError(f"Backend must be one of {valid_backends}")
        return v

    @validator("model_size")
    def validate_model_size(cls, v):
        valid_sizes = ["tiny", "base", "small", "medium", "large-v3"]
        if v not in valid_sizes:
            raise ValueError(f"Model size must be one of {valid_sizes}")
        return v


class TranscriptionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    text: str
    duration: float
    language: str
    language_probability: float
    segments: Optional[List[Any]] = None
    summary: Optional[str] = None
    summary_model: Optional[str] = None
    meeting_type: Optional[str] = None

class MeetingSummaryResponse(BaseModel):
    id: str
    content: str
    model_used: Optional[str]
    meeting_type: Optional[str]
    created_at: datetime

class CorrectionRequest(BaseModel):
    content: str = Field(..., min_length=1)
    correction_type: Optional[str] = "full_edit"

class TitleUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class HistoryItem(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: datetime
    duration_seconds: Optional[float]
    language: str
    preview: Optional[str] = None
    summary: Optional[str] = None
    meeting_type: Optional[str] = None

    class Config:
        from_attributes = True

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

class InsightData(BaseModel):
    total_errors: int
    by_type: dict
    frequent_errors: List[dict]
    average_wer: float
