import httpx
import logging
import asyncio
import re
import traceback
from typing import Optional, Dict, Any, List
from ..services.health_service import SystemHealthService, ServiceStatus
from .cache import cached
import hashlib

from .config import settings

logger = logging.getLogger(__name__)

class LlmClient:
    """
    Generic client for interacting with Ollama (or compatible LLMs).
    Includes Circuit Breaker pattern and Health Monitoring.
    """
    def __init__(self, ollama_url: str = f"{settings.OLLAMA_BASE_URL}/api/generate", model: str = settings.LLM_MODEL):
        self.ollama_url = ollama_url
        self.model = model
        self.health = SystemHealthService()

        # Circuit Breaker Configuration
        self.circuit_open = False
        self.consecutive_failures = 0
        self.max_failures = 2
        self.probe_interval_seconds = 30

        # Check initially
        self.health.set_llm_status(ServiceStatus.INITIALIZING)
        logger.info(f"LlmClient initialized for model {model}")

    async def check_connection(self):
        """Probes Ollama to see if it's reachable and the model is loaded."""
        logger.info(f"🔍 Starting Ollama connection check to {self.ollama_url}")
        try:
            async with httpx.AsyncClient() as client:
                # Check tags to verify service is up
                logger.info(f"📡 Attempting httpx GET to {self.ollama_url.replace('/api/generate', '/api/tags')}")
                response = await client.get(self.ollama_url.replace("/api/generate", "/api/tags"), timeout=5.0)
                logger.info(f"✅ Received response with status {response.status_code}")
                if response.status_code == 200:
                    models_data = response.json()
                    model_names = [m.get("name") for m in models_data.get("models", [])]

                    if any(self.model in m for m in model_names):
                        logger.info(f"✅ Found model {self.model}")
                        self._reset_circuit()
                        return True
                    else:
                        logger.warning(f"⚠️ Model {self.model} not found in {model_names}")
                        self.health.set_llm_status(ServiceStatus.UNAVAILABLE, f"Model {self.model} missing")
                        return False
                else:
                    logger.warning(f"⚠️ Ollama returned status {response.status_code}")
                    self._trip_circuit(f"Ollama returned {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"❌ Ollama connection EXCEPTION: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._trip_circuit(f"Connection failed: {str(e)}")
            return False

    def _trip_circuit(self, reason: str):
        if not self.circuit_open:
            logger.warning(f"⚠️ Circuit Breaker TRIPPED: {reason}")
            self.circuit_open = True
            self.health.set_llm_status(ServiceStatus.UNAVAILABLE, reason)
            # Start background healer
            asyncio.create_task(self._monitor_recovery())

    def _reset_circuit(self):
        if self.circuit_open:
            logger.info("✅ Circuit Breaker RESET: Ollama is back online.")
        self.circuit_open = False
        self.consecutive_failures = 0
        self.health.set_llm_status(ServiceStatus.READY)

    async def _monitor_recovery(self):
        """Background loop that probes the service until it recovers."""
        logger.info("🚑 Starting background recovery monitor for Ollama...")
        while self.circuit_open:
            await asyncio.sleep(self.probe_interval_seconds)
            logger.debug("🚑 Probing Ollama for recovery...")
            if await self.check_connection():
                break
        logger.info("🚑 Recovery monitor stopped.")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False, timeout: float = 120.0) -> Optional[str]:
        """
        Generic generation method with circuit breaker check.
        """
        if self.circuit_open:
            logger.warning("Attempted generation while circuit open")
            return None

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        if system_prompt:
            payload["system"] = system_prompt

        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ollama_url,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    self._reset_circuit()
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.max_failures:
                        self._trip_circuit(f"Ollama error {response.status_code}")
                    return None

        except Exception as e:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.max_failures:
                self._trip_circuit(f"Connection failure: {str(e)}")
            logger.error(f"LLM Generation failed: {e}")
            return None
