from pydantic import BaseModel, Field
from typing import List, Optional


class SpeakerBase(BaseModel):
    speaker_label: str = Field(..., description="Auto-generated speaker label (e.g., 'Speaker 1')")
    speaker_name: Optional[str] = Field(None, description="Human-readable speaker name from LLM or user edit")
    total_duration: float = Field(default=0.0, description="Total speaking time in seconds")
    segment_count: int = Field(default=0, description="Number of segments for this speaker")


class SpeakerCreate(SpeakerBase):
    transcription_id: str


class SpeakerUpdate(BaseModel):
    speaker_name: Optional[str] = Field(None, description="New speaker name")


class SpeakerResponse(SpeakerBase):
    id: str
    transcription_id: str

    class Config:
        from_attributes = True


class SpeakerListResponse(BaseModel):
    speakers: List[SpeakerResponse]
    total_speakers: int


class TranscriptSegmentBase(BaseModel):
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None


class TranscriptSegmentResponse(TranscriptSegmentBase):
    id: str
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None
    speaker_name: Optional[str] = None

    class Config:
        from_attributes = True


class TranscriptWithSpeakersResponse(BaseModel):
    segments: List[TranscriptSegmentResponse]
    speakers: List[SpeakerResponse]
    total_duration: float
    speaker_count: int
