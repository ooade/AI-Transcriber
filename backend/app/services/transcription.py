import os
import logging
import asyncio
import subprocess
import shlex
from pathlib import Path
from typing import Optional
# import torch (removed to avoid dependency)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from faster_whisper import WhisperModel
from .whisper_cpp_setup import download_whisper_cpp_model, setup_whisper_cpp, verify_whisper_cpp

# Global cache for whisper.cpp model paths to avoid re-downloading
_WHISPER_CPP_MODEL_CACHE = {}

class MaxAccuracyTranscriber:
    def __init__(self, model_size="large-v3", device=None, compute_type=None, max_concurrency=2):
        from ..core.config import settings
        self.model_size = model_size
        self.device = device or ("cpu")
        self.compute_type = compute_type or ("float16" if self.device == "cuda" else "int8")
        self._model = None
        self.max_concurrency = max_concurrency
        self._semaphore = None # Lazily initialized
        # Load performance tuning settings
        self.beam_size = settings.TRANSCRIBE_BEAM_SIZE
        self.best_of = settings.TRANSCRIBE_BEST_OF
        self.temperature = settings.TRANSCRIBE_TEMPERATURE

    def warm_up(self):
        """Pre-loads the model into memory to eliminate cold-start latency."""
        logger.info("⚡ Warming up WhisperModel...")
        self._get_model()
        logger.info("✅ Warm-up complete")

    def _get_model(self):
        if self._model is None:
            logger.info(f"Loading WhisperModel: {self.model_size} on {self.device} with {self.compute_type}")
            try:
                # We initialize here to avoid blocking module import or worker startup
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    local_files_only=False # Let it download once if needed
                )
                logger.info("Successfully loaded WhisperModel")
            except Exception as e:
                logger.error(f"Failed to load WhisperModel: {e}")
                raise e
        return self._model

    async def transcribe(
        self,
        audio_path: str,
        language: str = None,
        initial_prompt: str = None,
        beam_size: int = None,
        best_of: int = None,
        temperature: float = None,
        word_timestamps: bool = True,
        vad_filter: bool = True,
        vad_parameters: dict = None,
    ):
        """
        Transcribe audio with maximum accuracy settings.
        Thread-safe and concurrency-limited to prevent CPU starvation.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)

        # Use instance defaults if not provided
        beam_size = beam_size or self.beam_size
        best_of = best_of or self.best_of
        temperature = temperature if temperature is not None else self.temperature

        async with self._semaphore:
            logger.info(f"Starting transcription for {audio_path} (Slot acquired)")
            if initial_prompt:
                 logger.info(f"Using initial prompt: {initial_prompt}")

            try:
                # Offload blocking model call to thread
                result = await asyncio.to_thread(
                    self._transcribe_blocking,
                    audio_path,
                    language,
                    initial_prompt,
                    beam_size,
                    best_of,
                    temperature,
                    word_timestamps,
                    vad_filter,
                    vad_parameters,
                )
                logger.info("Transcription completed successfully")
                return result

            except Exception as e:
                logger.error(f"Error during transcription: {e}")
                raise e

    def _transcribe_blocking(
        self,
        audio_path: str,
        language: str = None,
        initial_prompt: str = None,
        beam_size: int = 10,
        best_of: int = 10,
        temperature: float = 0.0,
        word_timestamps: bool = True,
        vad_filter: bool = True,
        vad_parameters: dict = None,
    ):
        """Internal blocking transcription method."""
        from ..core.config import settings
        model = self._get_model()
        if vad_parameters is None:
            vad_parameters = dict(
                min_silence_duration_ms=settings.VAD_MIN_SILENCE_DURATION_MS,
                min_speech_duration_ms=settings.VAD_MIN_SPEECH_DURATION_MS
            )

        segments, info = model.transcribe(
            audio_path,
            beam_size=beam_size,
            best_of=best_of,
            temperature=temperature,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters,
            condition_on_previous_text=True,
            initial_prompt=initial_prompt,
            language=language
        )

        result_segments = []
        full_text = []

        for segment in segments:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": [{
                    "start": word.start,
                    "end": word.end,
                    "word": word.word,
                    "probability": word.probability
                } for word in segment.words] if segment.words else []
            }
            result_segments.append(segment_dict)
            full_text.append(segment.text)

        # Try to get duration from info, fallback to ffprobe if missing
        duration = getattr(info, "duration", 0.0)
        if duration <= 0:
            # Fallback to ffprobe
            try:
                abs_audio_path = os.path.abspath(audio_path)
                cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", abs_audio_path]
                logger.info(f"Running duration fallback: {' '.join(cmd)}")
                dur_res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                duration = float(dur_res.stdout.strip())
                logger.info(f"✅ Duration detected via ffprobe: {duration}")
            except Exception as e:
                logger.warning(f"⚠️ Could not determine duration for {audio_path}: {e}")
                duration = 0.0

        return {
            "text": " ".join(full_text).strip(),
            "segments": result_segments,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": duration
        }


class WhisperCppTranscriber:
    """
    Whisper.cpp transcriber with Metal/CUDA acceleration support.
    Uses subprocess to call whisper.cpp binary for faster inference.
    """

    def __init__(self, model_size="large-v3", whisper_cpp_path: Optional[str] = None,
                 auto_setup: bool = True, max_concurrency: int = 2):
        self.model_size = model_size
        self.whisper_cpp_path = whisper_cpp_path
        self.auto_setup = auto_setup
        self.max_concurrency = max_concurrency
        self._semaphore = None # Lazily initialized
        self._binary_path: Optional[Path] = None
        self._model_path: Optional[Path] = None
        self._has_metal = False
        self._has_cuda = False
        self._initialized = False

    def warm_up(self):
        """Initialize whisper.cpp binary and download model if needed."""
        if self._initialized:
            return

        logger.info("⚡ Warming up whisper.cpp...")

        # Setup binary
        if self.whisper_cpp_path:
            self._binary_path = Path(self.whisper_cpp_path)
            if not self._binary_path.exists():
                raise FileNotFoundError(f"Whisper.cpp binary not found: {self.whisper_cpp_path}")
        elif self.auto_setup:
            binary_path, has_metal, has_cuda = setup_whisper_cpp()
            if not binary_path:
                raise RuntimeError("Failed to setup whisper.cpp. Set WHISPER_CPP_PATH or disable auto-setup.")
            self._binary_path = binary_path
            self._has_metal = has_metal
            self._has_cuda = has_cuda
        else:
            raise RuntimeError("whisper.cpp path not provided and auto-setup is disabled")

        # Verify binary works
        if not verify_whisper_cpp(self._binary_path):
            raise RuntimeError(f"whisper.cpp binary verification failed: {self._binary_path}")

        # Download model (with caching to avoid re-downloading)
        global _WHISPER_CPP_MODEL_CACHE
        if self.model_size in _WHISPER_CPP_MODEL_CACHE:
            self._model_path = _WHISPER_CPP_MODEL_CACHE[self.model_size]
            logger.info(f"✅ Using cached model path: {self._model_path}")
        else:
            self._model_path = download_whisper_cpp_model(self.model_size)
            if not self._model_path:
                raise RuntimeError(f"Failed to download whisper.cpp model: {self.model_size}")
            _WHISPER_CPP_MODEL_CACHE[self.model_size] = self._model_path

        self._initialized = True
        accel = "Metal" if self._has_metal else ("CUDA" if self._has_cuda else "CPU")
        logger.info(f"✅ whisper.cpp ready: {accel} acceleration, model: {self.model_size}")

    async def transcribe(
        self,
        audio_path: str,
        language: str = None,
        initial_prompt: str = None,
        beam_size: int = 10,
        best_of: int = 10,
        temperature: float = 0.0,
        word_timestamps: bool = True,
        vad_filter: bool = True,
        vad_parameters: dict = None,
    ):
        """
        Transcribe audio using whisper.cpp.
        Thread-safe and concurrency-limited.

        Note: whisper.cpp doesn't support all parameters from faster-whisper,
        so some are ignored (beam_size, best_of, word_timestamps, vad_filter).
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Ensure initialized
        if not self._initialized:
            self.warm_up()

        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)

        async with self._semaphore:
            logger.info(f"Starting whisper.cpp transcription for {audio_path}")

            try:
                # Convert audio to standard WAV format for whisper.cpp compatibility
                converted_path = await self._convert_audio(audio_path)

                # Run whisper.cpp
                result = await self._transcribe_with_whisper_cpp(
                    converted_path, language, initial_prompt
                )

                # Cleanup temp file
                if converted_path != audio_path:
                    Path(converted_path).unlink(missing_ok=True)

                logger.info("whisper.cpp transcription completed successfully")
                return result

            except Exception as e:
                logger.error(f"Error during whisper.cpp transcription: {e}")
                raise e

    async def _convert_audio(self, audio_path: str, force: bool = False) -> str:
        """Convert audio to standard WAV format for whisper.cpp.

        Args:
            audio_path: Path to audio file
            force: If True, always convert. If False, check format first.

        Returns:
            Path to converted audio file (may be original if already correct format)
        """
        from ..core.config import settings
        audio_path_obj = Path(audio_path)

        # Check if conversion is needed (unless forced or always-convert enabled)
        if not force and not settings.AUDIO_CONVERT_ALWAYS:
            # Check if file is already in correct format (WAV, 16kHz, mono)
            try:
                check_cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=codec_name,sample_rate,channels",
                    "-of", "csv=p=0", audio_path
                ]
                result = await asyncio.to_thread(
                    subprocess.run,
                    check_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(",")
                    if len(parts) >= 3:
                        codec, sample_rate, channels = parts[0], int(parts[1]), int(parts[2])
                        # If already correct format, return original path (saves ~10-30 seconds)
                        if codec == "pcm_s16le" and sample_rate == 16000 and channels == 1:
                            logger.info(f"✅ Audio already in correct format, skipping conversion")
                            return audio_path
            except Exception as e:
                logger.debug(f"Could not check audio format: {e}, will convert")

        # Conversion needed
        converted_path = f"/tmp/whisper_converted_{audio_path_obj.stem}.wav"
        logger.info(f"Converting audio to WAV 16kHz mono...")

        ffmpeg_cmd = [
            "ffmpeg", "-i", audio_path,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            "-y", converted_path
        ]

        result = await asyncio.to_thread(
            subprocess.run,
            ffmpeg_cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr.strip()}")
            raise RuntimeError("Audio conversion failed. Ensure ffmpeg is installed.")

        return converted_path

    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
        )
        try:
            return float(result.stdout.strip())
        except (ValueError, TypeError):
            logger.warning(f"Could not determine duration for {audio_path}")
            return 0.0

    async def _transcribe_with_whisper_cpp(
        self, audio_path: str, language: Optional[str], initial_prompt: Optional[str]
    ) -> dict:
        """Run whisper.cpp binary and parse output."""
        # Get duration first
        duration = await self._get_audio_duration(audio_path)

        # Build command with proper escaping
        cmd = [str(self._binary_path), "-m", str(self._model_path), "-f", audio_path]

        if language:
            cmd += ["-l", language]
        if initial_prompt:
            # Properly escape initial prompt to avoid shell interpretation issues
            cmd += ["-p", str(initial_prompt)]

        # Add threading for performance (use all cores)
        # Note: On some ARM builds, -t flag may cause parsing issues, so we'll retry without it
        import multiprocessing
        thread_count = max(1, multiprocessing.cpu_count())
        cmd_with_threads = cmd + ["-t", str(int(thread_count))]
        cmd_without_threads = cmd.copy()

        logger.info(f"Running whisper.cpp with {thread_count} threads: {' '.join(cmd_with_threads[:5])}...")

        # Try with threads first
        result = await self._run_whisper_cpp(cmd_with_threads)

        # If it fails with invalid_argument error, retry without threads (ARM workaround)
        if (result.returncode != 0 and
            ("invalid_argument" in result.stderr.lower() or "stoi" in result.stderr.lower())):
            logger.warning("⚠️  whisper.cpp -t flag failed (ARM issue?). Retrying without thread flag...")
            result = await self._run_whisper_cpp(cmd_without_threads)

        if result.returncode != 0:
            stderr_msg = result.stderr.strip()
            logger.error(f"whisper.cpp failed with code {result.returncode}: {stderr_msg[:500]}")
            raise RuntimeError(f"whisper.cpp transcription failed: {stderr_msg[:200]}")

        # Parse VTT output
        transcript_text = self._parse_vtt_output(result.stdout)

        if not transcript_text:
            logger.warning("whisper.cpp returned empty output")

        # Return in same format as MaxAccuracyTranscriber for compatibility
        return {
            "text": transcript_text,
            "segments": [],  # whisper.cpp doesn't provide detailed segments easily
            "language": language or "en",
            "language_probability": 1.0,
            "duration": duration,
        }

    async def _run_whisper_cpp(self, cmd: list) -> subprocess.CompletedProcess:
        """Helper to run whisper.cpp with proper error handling."""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"whisper.cpp transcription timed out (600s)")
            raise RuntimeError("whisper.cpp transcription timed out")
        except Exception as e:
            logger.error(f"whisper.cpp subprocess error: {e}")
            raise RuntimeError(f"whisper.cpp transcription failed: {e}")

        # Parse VTT output
        transcript_text = self._parse_vtt_output(result.stdout)

        if not transcript_text:
            logger.warning("whisper.cpp returned empty output")

        # Return in same format as MaxAccuracyTranscriber for compatibility
        return {
            "text": transcript_text,
            "segments": [],  # whisper.cpp doesn't provide detailed segments easily
            "language": language or "en",
            "language_probability": 1.0,
            "duration": duration,
        }

    def _parse_vtt_output(self, vtt_output: str) -> str:
        """Extract text from whisper.cpp VTT format output."""
        lines = []
        for line in vtt_output.split("\n"):
            line = line.strip()

            # Skip empty lines and headers
            if not line or line.startswith("WEBVTT"):
                continue

            # Lines with timestamps: [HH:MM:SS.mmm --> HH:MM:SS.mmm]   text
            if "-->" in line and line.startswith("["):
                bracket_end = line.find("]")
                if bracket_end >= 0:
                    text = line[bracket_end + 1:].strip()
                    if text:
                        lines.append(text)

        return " ".join(lines)
