import logging
import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.llm import LlmClient
from ..models import Transcription, MeetingSummary
from ..core.config import settings
from ..core.prompts import ADAPTIVE_SUMMARY_SYSTEM_PROMPT, build_summary_prompt

logger = logging.getLogger(__name__)

class SummarizerService:
    def __init__(self, db: Session, ollama_url: str = f"{settings.OLLAMA_BASE_URL}/api/generate", model: str = settings.LLM_MODEL):
        self.db = db
        self.llm = LlmClient(ollama_url, model)

    def _sanitize_json_response(self, text: str) -> str:
        """
        Robustly sanitizes LLM output to extract a valid JSON block.
        Handles:
        - Markdown code blocks
        - Extra preamble/epilogue text
        - Common triple-quote hallucination inside JSON values
        """
        import re

        # 1. Extract content between first { and last }
        text = text.strip()
        json_start = text.find('{')
        json_end = text.rfind('}')

        if json_start == -1 or json_end == -1:
            return text

        json_str = text[json_start : json_end + 1]

        # 2. Handle triple quotes (hallucinated as multi-line strings in JSON)
        # This is the "Principal" way: handle it before json.loads
        if '"""' in json_str:
            # Replace triple quotes with standard escaped quotes and handle newlines
            def fix_triple_quotes(match):
                inner = match.group(1)
                inner = inner.replace('\\', '\\\\').replace('"', '\\"')
                inner = inner.replace('\n', '\\n')
                return f'"{inner}"'

            json_str = re.sub(r'"""(.*?)"""', fix_triple_quotes, json_str, flags=re.DOTALL)

        return json_str

    async def generate_summary(self, transcription_id: str, text: str = None) -> dict:
        """
        Generates a summary for the given transcription using a single-pass LLM call.
        Returns the summary object (or None on failure).
        """
        # Defensive Check: If ID is a dict (InterfaceError), extract the real ID
        if isinstance(transcription_id, dict):
             transcription_id = transcription_id.get("id")

        if not transcription_id:
             logger.error("generate_summary called with missing transcription_id")
             return None

        # 1. Fetch Text (if not provided)
        text_to_summarize = text
        if not text_to_summarize:
            # Fallback to DB fetch
            transcription = self.db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()

            if not transcription:
                logger.error(f"Transcription {transcription_id} not found.")
                return None

            # Use corrected text if available, otherwise raw
            if transcription.corrected_transcripts:
                latest = sorted(transcription.corrected_transcripts, key=lambda x: x.corrected_at, reverse=True)[0]
                text_to_summarize = latest.content
            elif transcription.raw_transcript:
                text_to_summarize = transcription.raw_transcript.content

        if not text_to_summarize or len(text_to_summarize.split()) < 20:
            logger.info("Transcript too short for summarization.")
            return None

        # 2. Optimized "Single-Pass" Summarization
        try:
            logger.info(f"Generating summary for {transcription_id} (Single Pass)...")

            # Construct the prompt using the centralized config
            prompt = build_summary_prompt(text_to_summarize)

            # Call LLM with the System Prompt enforced
            response_text = await self.llm.generate(
                prompt,
                system_prompt=ADAPTIVE_SUMMARY_SYSTEM_PROMPT,
                json_mode=True,
                timeout=180.0  # 3 minutes for longer transcripts
            )

            if not response_text:
                logger.warning("LLM returned empty summary.")
                return None

            # 3. Parse JSON Output
            cleaned_response = self._sanitize_json_response(response_text)

            try:
                data = json.loads(cleaned_response)
                summary_content = data.get("summary", "").strip()
                meeting_type = data.get("meeting_type", "General Meeting")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from LLM: {e}")
                logger.debug(f"LLM response was: {response_text[:500]}")
                # Fallback: use response as-is if parsing fails
                summary_content = response_text
                meeting_type = "Unknown"

            # 4. Save Summary
            existing = self.db.query(MeetingSummary).filter(
                MeetingSummary.transcription_id == transcription_id
            ).first()

            if existing:
                existing.content = summary_content
                existing.created_at = datetime.utcnow()
                existing.model_used = settings.LLM_MODEL
                existing.meeting_type = meeting_type
            else:
                new_summary = MeetingSummary(
                    id=str(uuid.uuid4()),
                    transcription_id=transcription_id,
                    content=summary_content,
                    model_used=settings.LLM_MODEL,
                    meeting_type=meeting_type,
                    created_at=datetime.utcnow()
                )
                self.db.add(new_summary)

            self.db.commit()
            logger.info(f"✅ Summary ({meeting_type}) saved for {transcription_id}")
            return {"status": "success", "type": meeting_type, "content": summary_content}

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            self.db.rollback()

            # Save failure state to stop frontend polling
            try:
                # Re-check if existing to avoid race condition constraint errors
                existing = self.db.query(MeetingSummary).filter(
                    MeetingSummary.transcription_id == transcription_id
                ).first()

                if not existing:
                    error_summary = MeetingSummary(
                        id=str(uuid.uuid4()),
                        transcription_id=transcription_id,
                        content="Summary generation failed. Please try again later.",
                        model_used="error",
                        meeting_type="Error",
                        created_at=datetime.utcnow()
                    )
                    self.db.add(error_summary)
                    self.db.commit()
                    logger.info(f"Saved error state for transcription {transcription_id}")
            except Exception as db_e:
                logger.error(f"Failed to save error state: {db_e}")
                self.db.rollback()

            return None
