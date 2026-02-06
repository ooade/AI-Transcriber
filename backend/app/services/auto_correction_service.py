import logging
import uuid
import re
import json
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from ..core.llm import LlmClient
from ..models import CorrectedTranscript, Transcription
from ..core.prompts import build_auto_correction_prompt
from ..core.text_utils import clean_text
from datetime import datetime

logger = logging.getLogger(__name__)

from ..core.config import settings

class AutoCorrectionService:
    def __init__(self, db: Session, ollama_url: str = f"{settings.OLLAMA_BASE_URL}/api/generate", model: str = settings.LLM_MODEL):
        self.db = db
        self.llm = LlmClient(ollama_url, model)

    def _align_timestamps(self, raw_text: str, corrected_text: str, raw_timestamps: list) -> list:
        """
        Align word timestamps from raw text to corrected text using character-level alignment.
        Returns list of aligned timestamp dicts with 'start', 'end', 'word', 'probability'.
        """
        if not raw_timestamps:
            return []

        try:
            # Use a simple sequential assignment strategy:
            # Assign timestamps based on temporal order and word count proportions
            corrected_words = corrected_text.split()

            # If word counts are similar, use sequence matching
            if len(raw_timestamps) > 0 and len(corrected_words) > 0:
                # Ratio of corrected words to raw timestamps
                ratio = len(corrected_words) / len(raw_timestamps)

                aligned_ts = []
                ts_idx = 0

                for corrected_idx, corrected_word in enumerate(corrected_words):
                    # Determine which timestamp index this word should map to
                    # by using proportional distribution
                    expected_ts_idx = int(corrected_idx / ratio)

                    # Use the closest available timestamp
                    if expected_ts_idx < len(raw_timestamps):
                        ts = raw_timestamps[expected_ts_idx]
                        aligned_ts.append({
                            "start": ts.get("start"),
                            "end": ts.get("end"),
                            "word": corrected_word,
                            "probability": ts.get("probability", 1.0)
                        })

                logger.info(f"Aligned {len(aligned_ts)} words from {len(corrected_words)} corrected words using ratio {ratio:.2f}")
                return aligned_ts

            return []

        except Exception as e:
            logger.error(f"Error aligning timestamps: {e}")
            return []

    async def auto_correct(self, transcription_id: str, context_keywords: str = None) -> str:
        """
        Retrieves a raw transcription, sends it to the LLM for correction,
        and saves the result. Optionally uses context keywords for improved accuracy.
        """
        # 1. Fetch Transcription
        transcription = self.db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription or not transcription.raw_transcript:
            logger.error(f"Transcription {transcription_id} not found or missing raw transcript.")
            return ""

        raw_text = transcription.raw_transcript.content
        if len(raw_text.split()) < 5:
            logger.info("Transcript too short for auto-correction.")
            return ""

        # 2. Construct Prompt
        prompt = build_auto_correction_prompt(raw_text, context_keywords)

        # 3. Call LLM
        response_text = await self.llm.generate(
            prompt,
            json_mode=True
        )

        if not response_text:
             logger.warning("LLM returned empty or truncated response. Aborting Auto-Correction.")
             return ""

        # 4. Parse JSON Output
        cleaned_response = response_text.strip()

        # Try to find JSON object even if there's extra text
        json_start = cleaned_response.find('{')
        json_end = cleaned_response.rfind('}')

        if json_start != -1 and json_end != -1:
            cleaned_response = cleaned_response[json_start:json_end+1]

        try:
            data = json.loads(cleaned_response)
            corrected_text = data.get("corrected_text", "").strip()

            # Use robust text cleaning to remove triple quotes and other artifacts
            corrected_text = clean_text(corrected_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM in AutoCorrection: {e}")
            # Fallback: if it's not JSON, we try to use it as is but it's risky
            corrected_text = clean_text(response_text.strip())

        if not corrected_text or len(corrected_text) < len(raw_text) * 0.5:
             # Sanity check: if response is suspiciously short, abort
             logger.warning("Parsed text is empty or too short. Aborting Auto-Correction.")
             return ""

        # 4. Align timestamps
        raw_timestamps = transcription.raw_transcript.word_timestamps or []
        aligned_timestamps = self._align_timestamps(raw_text, corrected_text, raw_timestamps)

        # 5. Save Correction
        try:
             # Check for existing correction from 'auto_llm'
            existing = self.db.query(CorrectedTranscript).filter(
                CorrectedTranscript.transcription_id == transcription_id,
                CorrectedTranscript.correction_type == 'auto_llm'
            ).first()

            if existing:
                existing.content = corrected_text
                existing.word_timestamps = aligned_timestamps
                existing.corrected_at = datetime.utcnow()
            else:
                correction = CorrectedTranscript(
                    id=str(uuid.uuid4()),
                    transcription_id=transcription_id,
                    content=corrected_text,
                    word_timestamps=aligned_timestamps,
                    correction_type='auto_llm', # Special type for automated
                    corrected_at=datetime.utcnow()
                )
                self.db.add(correction)

            self.db.commit()
            logger.info(f"✅ Auto-Correction saved for {transcription_id}")
            return corrected_text

        except Exception as e:
            logger.error(f"Failed to save auto-correction: {e}")
            self.db.rollback()
            return ""
