import logging
import hashlib
from typing import List, Dict, Optional
import torch
from pyannote.audio import Pipeline

from ..core.cache import cached
from ..core.config import settings
from ..core.llm import LlmClient
from ..services.health_service import SystemHealthService, ServiceStatus
from ..core.prompts import build_speaker_identification_prompt

logger = logging.getLogger(__name__)


class SpeakerDiarizationService:
    """
    Speaker identification and diarization service.
    - Segments audio by speaker using pyannote.audio
    - Extracts speaker names from conversation using LLM
    - Handles graceful degradation if LLM unavailable
    """

    def __init__(self, huggingface_token: Optional[str] = None):
        self.pipeline = None
        self.huggingface_token = huggingface_token
        self.llm = LlmClient()  # Shared LLM client with circuit breaker
        self.health = SystemHealthService()
        self._initialized = False
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def warm_up(self):
        """Load diarization model on startup (similar to Whisper warmup pattern)."""
        if self._initialized:
            return

        try:
            logger.info(f"Loading speaker diarization model on {self._device}...")

            # Authenticate with HuggingFace Hub
            if self.huggingface_token:
                try:
                    from huggingface_hub import login
                    login(token=self.huggingface_token)
                    logger.info("✅ Authenticated with HuggingFace Hub")
                except ImportError:
                    logger.warning("huggingface_hub not installed, skipping login")
                except Exception as e:
                    logger.warning(f"Failed to login to HuggingFace Hub: {e}")

            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )
            self.pipeline.to(torch.device(self._device))
            self._initialized = True
            self.health.set_speaker_diarization_status(ServiceStatus.READY)
            logger.info("✅ Speaker diarization model loaded")
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            self._initialized = False
            self.health.set_speaker_diarization_status(ServiceStatus.UNAVAILABLE, str(e))

    async def diarize(self, audio_path: str) -> List[Dict]:
        """
        Identify speakers and their time segments in audio.

        Returns:
            List of speaker segments: [
                {"speaker": "Speaker 1", "start": 0.0, "end": 5.2},
                {"speaker": "Speaker 2", "start": 5.2, "end": 12.1},
                ...
            ]
        """
        if not self._initialized:
            self.warm_up()

        if not self._initialized:
            logger.warning("⚠️ Diarization service not available, skipping speaker detection")
            return []

        try:
            logger.info(f"Diarizing speakers in {audio_path}...")
            diarization = self.pipeline(audio_path)

            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "speaker": speaker,
                    "start": float(turn.start),
                    "end": float(turn.end),
                })

            unique_speakers = len(set(s["speaker"] for s in segments))
            logger.info(f"✅ Identified {unique_speakers} speaker(s) in {len(segments)} segments")
            return segments

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return []

    @cached(
        ttl=settings.TTL_LLM_CONTEXT,
        key_builder=lambda self, transcript, speaker_count:
            f"speaker_names:{hashlib.md5(f'{transcript[:500]}_{speaker_count}'.encode()).hexdigest()}"
    )
    async def extract_speaker_names_from_transcript(
        self,
        transcript: str,
        speaker_count: int
    ) -> Dict[str, str]:
        """
        Use LLM to identify and name speakers from conversation content.
        Results are cached for 24 hours.

        Args:
            transcript: Full transcript with speaker labels
            speaker_count: Number of detected speakers

        Returns:
            Mapping like {"Speaker 1": "Alice", "Speaker 2": "Bob"}
            Falls back to speaker labels if LLM unavailable or extraction fails.
        """
        if speaker_count == 0:
            return {}

        # Check if LLM is available
        llm_available = await self.llm.check_connection()
        if not llm_available:
            logger.warning("⚠️ LLM unavailable, using generic speaker labels")
            return {f"Speaker {i}": f"Speaker {i}" for i in range(1, speaker_count + 1)}

        prompt = build_speaker_identification_prompt(transcript, speaker_count)

        try:
            logger.info("🔍 Extracting speaker names from transcript...")
            response = await self.llm.generate(prompt)

            if not response:
                logger.warning("⚠️ LLM returned empty response")
                return {}

            # Parse JSON response
            import json
            cleaned_response = response.strip()

            # Remove markdown code blocks if present
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-3]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:-3]

            names_map = json.loads(cleaned_response)

            # Validate response
            if not isinstance(names_map, dict):
                logger.warning(f"⚠️ Invalid response format: {type(names_map)}")
                return {}

            logger.info(f"✅ Extracted speaker names: {names_map}")
            return names_map

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse LLM response as JSON: {e}")
            return {}
        except Exception as e:
            logger.warning(f"⚠️ Speaker name extraction failed: {e}")
            return {}


def merge_speaker_segments_with_transcript(
    transcript_segments: List[Dict],
    speaker_segments: List[Dict]
) -> List[Dict]:
    """
    Merge Whisper segments with speaker diarization data.
    Aligns transcript text with speaker labels based on timing.

    Args:
        transcript_segments: Whisper output with timing
        speaker_segments: Speaker diarization segments

    Returns:
        Merged segments with speaker labels
    """
    merged = []

    for trans_seg in transcript_segments:
        trans_start = trans_seg.get("start", 0)
        trans_end = trans_seg.get("end", 0)
        text = trans_seg.get("text", "")

        # Find overlapping speaker segment
        speaker = "Unknown"
        for spk_seg in speaker_segments:
            spk_start = spk_seg["start"]
            spk_end = spk_seg["end"]

            # Check for time overlap
            overlap_start = max(trans_start, spk_start)
            overlap_end = min(trans_end, spk_end)

            if overlap_start < overlap_end:
                speaker = spk_seg["speaker"]
                break

        merged.append({
            **trans_seg,
            "speaker": speaker,
        })

    return merged
