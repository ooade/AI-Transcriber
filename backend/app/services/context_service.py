import logging
import re
import hashlib
from typing import Optional
from ..core.llm import LlmClient
from ..core.cache import cached
from ..core.config import settings
from ..core.prompts import build_context_extraction_prompt

logger = logging.getLogger(__name__)

class ContextService:
    def __init__(self, ollama_url: str = f"{settings.OLLAMA_BASE_URL}/api/generate", model: str = settings.LLM_MODEL):
        # Use shared LLM Client
        self.llm = LlmClient(ollama_url, model)

    async def check_connection(self):
        return await self.llm.check_connection()

    @cached(
        ttl=settings.TTL_LLM_CONTEXT,
        key_builder=lambda self, transcript: f"llm_context:{hashlib.md5(transcript.encode()).hexdigest()}"
    )
    async def extract_context_keywords(self, transcript: str) -> str:
        """
        Sends the transcript to Ollama to extract contextually relevant keywords.
        """
        if not transcript or len(transcript.split()) < 5:
            return ""

        prompt = build_context_extraction_prompt(transcript)

        try:
            # Delegate to LlmClient
            raw_keywords = await self.llm.generate(prompt)

            if not raw_keywords:
                return ""

            # Cleanup logic
            cleaned = re.sub(r'^(here are|keywords|list|analysis).*?:', '', raw_keywords, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r'^\s*[\*\-\d\.]+\s+', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.replace('\n', ', ')
            cleaned = re.sub(r',\s*,', ',', cleaned)

            logger.info(f"Ollama context: {cleaned[:50]}...")
            return cleaned

        except Exception as e:
            logger.error(f"Context extraction failed: {e}")
            return ""
