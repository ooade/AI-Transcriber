#!/usr/bin/env python3
"""
Standalone CLI tool for transcribing and summarizing audio files.
Usage: python transcribe_cli.py <audio_file> [--summarize] [--language en]
"""

import asyncio
import argparse
import sys
import os
import subprocess
import shlex
import shutil
import urllib.request
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.transcription import MaxAccuracyTranscriber
from app.core.llm import LlmClient
from app.core.config import settings
from app.core.prompts import ADAPTIVE_SUMMARY_SYSTEM_PROMPT, build_summary_prompt
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def download_whisper_cpp_model(model_size: str) -> Optional[Path]:
    """
    Auto-download whisper.cpp model from HuggingFace if not found locally.
    Mimics faster-whisper's auto-download behavior.
    """
    model_map = {
        "tiny": "ggml-tiny.bin",
        "base": "ggml-base.bin",
        "small": "ggml-small.bin",
        "medium": "ggml-medium.bin",
        "large": "ggml-large-v3.bin",
        "large-v2": "ggml-large-v2.bin",
        "large-v3": "ggml-large-v3.bin",
    }

    model_filename = model_map.get(model_size, "ggml-large-v3.bin")
    cache_dir = Path.home() / ".cache" / "whisper.cpp"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / model_filename

    # Check if already exists
    if model_path.exists():
        logger.info(f"✅ Model found: {model_path}")
        return model_path

    # Download from HuggingFace
    logger.info(f"📥 Downloading {model_filename} from HuggingFace...")
    url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{model_filename}"

    try:
        def _show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100) if total_size > 0 else 0
            downloaded_mb = downloaded / 1024 / 1024
            total_mb = total_size / 1024 / 1024
            if block_num % 50 == 0 or downloaded >= total_size:  # Update every ~50 blocks
                logger.info(f"   Progress: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")

        urllib.request.urlretrieve(url, model_path, reporthook=_show_progress)

        # Verify downloaded file
        if model_path.exists() and model_path.stat().st_size > 1024 * 1024:  # At least 1 MB
            logger.info(f"✅ Downloaded successfully: {model_path} ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")
            return model_path
        else:
            logger.error(f"❌ Download failed or file too small: {model_path}")
            model_path.unlink(missing_ok=True)
            return None

    except Exception as e:
        logger.error(f"❌ Failed to download model: {e}")
        model_path.unlink(missing_ok=True)
        return None


class TranscribeAndSummarizeCLI:
    def __init__(
        self,
        model_size: str,
        device: Optional[str],
        compute_type: Optional[str],
        max_concurrency: int,
        transcribe_options: dict,
        warm_up_transcriber: bool,
        warm_up_llm: bool,
        backend: str,
        whisper_cpp_path: Optional[str],
        whisper_cpp_model: Optional[str],
        whisper_cpp_threads: Optional[int],
        whisper_cpp_args: Optional[str],
    ):
        self.backend = backend
        self.transcriber = None
        if self.backend == "faster-whisper":
            self.transcriber = MaxAccuracyTranscriber(
                model_size=model_size,
                device=device,
                compute_type=compute_type,
                max_concurrency=max_concurrency,
            )
        self.llm = LlmClient()
        self.transcribe_options = transcribe_options
        self.warm_up_transcriber = warm_up_transcriber
        self.warm_up_llm = warm_up_llm
        self.whisper_cpp_path = whisper_cpp_path
        self.whisper_cpp_model = whisper_cpp_model
        self.whisper_cpp_threads = whisper_cpp_threads
        self.whisper_cpp_args = whisper_cpp_args

    async def warm_up(self):
        """Warm up models before processing."""
        if self.backend == "faster-whisper" and self.warm_up_transcriber and self.transcriber:
            logger.info("🔧 Warming up transcriber...")
            self.transcriber.warm_up()
        elif self.backend == "whisper-cpp" and self.warm_up_transcriber:
            logger.info("🔧 Warm-up skipped for whisper.cpp backend (no model preload).")

        if self.warm_up_llm and not self.llm.circuit_open:
            logger.info("🔧 Warming up LLM...")
            await self.llm.check_connection()

    async def transcribe(self, audio_path: str, language: str = None, initial_prompt: str = None) -> dict:
        """Transcribe audio file."""
        logger.info(f"📝 Transcribing: {audio_path}")
        if self.backend == "whisper-cpp":
            return await self._transcribe_whisper_cpp(audio_path, language, initial_prompt)

        if not self.transcriber:
            raise RuntimeError("Transcriber is not initialized.")

        result = await self.transcriber.transcribe(
            audio_path,
            language=language,
            initial_prompt=initial_prompt,
            **self.transcribe_options,
        )
        return result

    async def _transcribe_whisper_cpp(self, audio_path: str, language: str = None, initial_prompt: str = None) -> dict:
        """Transcribe using whisper.cpp (Metal-enabled build)."""
        if not self.whisper_cpp_path or not self.whisper_cpp_model:
            raise RuntimeError("whisper.cpp backend requires --whisper-cpp-path and --whisper-cpp-model.")

        # Always convert to standard WAV format for whisper.cpp compatibility
        logger.info("🔄 Converting audio to standard WAV format for whisper.cpp...")
        converted_path = f"/tmp/whisper_converted_{Path(audio_path).stem}.wav"
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

        # Log the converted file size
        converted_size = Path(converted_path).stat().st_size / 1024 / 1024
        logger.info(f"✅ Audio converted: {converted_size:.1f} MB")

        cmd = [self.whisper_cpp_path, "-m", self.whisper_cpp_model, "-f", converted_path]

        if language:
            cmd += ["-l", language]
        if initial_prompt:
            cmd += ["-p", initial_prompt]
        if self.whisper_cpp_threads:
            cmd += ["-t", str(self.whisper_cpp_threads)]
        if self.whisper_cpp_args:
            cmd += shlex.split(self.whisper_cpp_args)

        logger.info(f"🚀 Running whisper.cpp on Metal GPU...")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Run whisper.cpp (can take 30-60 seconds for long audio)
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=600,  # 10 minute timeout for long audio
        )

        if result.returncode != 0:
            logger.error(f"whisper.cpp failed: {result.stderr.strip()}")
            raise RuntimeError("whisper.cpp transcription failed. See logs for details.")

        # whisper.cpp outputs transcript to stdout in VTT format
        logger.info(f"📊 whisper.cpp output: stdout={len(result.stdout)} bytes, stderr={len(result.stderr)} bytes")
        transcript_text = result.stdout.strip()
        if transcript_text:
            # Extract text from VTT format: whisper.cpp outputs "[HH:MM:SS.mmm --> HH:MM:SS.mmm]   text"
            # We need to extract the text part after the timestamp
            lines = []
            for line in transcript_text.split("\n"):
                line = line.strip()
                # Skip empty lines and headers
                if not line or line.startswith("WEBVTT"):
                    continue

                # Lines with timestamps are in format: [HH:MM:SS.mmm --> HH:MM:SS.mmm]   text
                # We need to extract the text after the closing bracket
                if "-->" in line and line.startswith("["):
                    # Find the closing bracket
                    bracket_end = line.find("]")
                    if bracket_end >= 0:
                        text = line[bracket_end + 1:].strip()
                        if text:
                            lines.append(text)
                # Skip other lines (shouldn't happen with whisper.cpp output)

            logger.info(f"✅ Extracted {len(lines)} text segments from {len(transcript_text.split(chr(10)))} total lines")
            if lines:
                transcript_text = " ".join(lines)
            else:
                logger.warning(f"⚠️  No lines could be parsed. Full stdout length: {len(result.stdout)}")
                transcript_text = ""

        if not transcript_text:
            logger.warning("⚠️  whisper.cpp returned empty output.")

        # Cleanup temp file
        if Path(converted_path).exists():
            Path(converted_path).unlink()

        return {"text": transcript_text}

    async def summarize(self, text: str) -> dict:
        """
        Summarize transcribed text.
        Returns a dict with: summary, meeting_type, full_response, reason (optional)
        """
        def error_response(reason: str):
            return {
                "summary": None,
                "meeting_type": "Unknown",
                "full_response": None,
                "reason": reason
            }

        if not text or len(text.split()) < 20:
            logger.warning("⚠️  Text too short for summarization (< 20 words)")
            return error_response("text too short")

        if self.llm.circuit_open:
            logger.warning("⚠️  LLM is unavailable. Skipping summarization.")
            return error_response("LLM unavailable")

        logger.info("✨ Generating summary...")

        try:
            prompt = build_summary_prompt(text)
            full_prompt = f"{ADAPTIVE_SUMMARY_SYSTEM_PROMPT}\n\n{prompt}"

            response_text = await self.llm.generate(full_prompt, json_mode=False)

            if not response_text:
                logger.warning("⚠️  LLM returned empty summary")
                return error_response("empty response")

            # Try to parse JSON if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-3]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:-3]

            try:
                data = json.loads(cleaned_response)
                summary_content = data.get("summary", "")
                meeting_type = data.get("meeting_type", "General")
                return {
                    "summary": summary_content,
                    "meeting_type": meeting_type,
                    "full_response": data,
                    "reason": None
                }
            except json.JSONDecodeError:
                # Fallback to raw text
                return {
                    "summary": response_text,
                    "meeting_type": "Unknown",
                    "full_response": None,
                    "reason": "json parse failed"
                }

        except Exception as e:
            logger.error(f"❌ Summarization failed: {e}")
            return error_response(str(e))

    async def auto_correct(self, text: str) -> dict:
        """Auto-correct transcript for punctuation/casing/grammar."""
        if not text or len(text.split()) < 5:
            logger.warning("⚠️  Text too short for auto-correction (< 5 words)")
            return {"corrected": None, "reason": "text too short"}

        if self.llm.circuit_open:
            logger.warning("⚠️  LLM is unavailable. Skipping auto-correction.")
            return {"corrected": None, "reason": "LLM unavailable"}

        # Use the same prompt as the backend auto-correction service
        prompt = (
            "You are a professional editor. Correct the following transcription for:\n"
            "1. Punctuation and Capitalization\n"
            "2. Spelling errors (especially technical terms)\n"
            "3. Grammar (without changing the meaning)\n\n"
            "CRITICAL RULES:\n"
            "- Do NOT summarize. Return the FULL corrected text.\n"
            "- Do NOT leave any comments or preamble (like 'Here is the corrected text:').\n"
            "- Maintain the original speaker's tone and intent.\n\n"
            f"Original Text:\n{text}"
        )

        try:
            response_text = await self.llm.generate(prompt, json_mode=False)
            if not response_text:
                logger.warning("⚠️  LLM returned empty auto-correction")
                return {"corrected": None, "reason": "empty response"}

            # Sanity check: if response is suspiciously short, abort
            if len(response_text) < len(text) * 0.5:
                logger.warning("⚠️  LLM returned truncated response. Using original text.")
                return {"corrected": None, "reason": "truncated response"}

            # Remove common chatty prefixes if LLM ignored rules
            import re
            clean_text = re.sub(r'^(Here is|Sure|I have corrected|Corrected transcription).*?:\n', '', response_text, flags=re.IGNORECASE|re.DOTALL).strip()

            return {"corrected": clean_text}
        except Exception as e:
            logger.error(f"❌ Auto-correction failed: {e}")
            return {"corrected": None, "reason": str(e)}

    async def run(
        self,
        audio_path: str,
        summarize: bool = False,
        language: str = None,
        output_dir: Optional[str] = None,
        auto_correct: bool = True,
    ):
        """Main CLI flow."""
        # Validate file
        if not Path(audio_path).exists():
            logger.error(f"❌ File not found: {audio_path}")
            return False

        # Warm up
        await self.warm_up()

        # Transcribe
        try:
            transcript_result = await self.transcribe(audio_path, language=language)
            full_text = transcript_result.get("text", "")

            if auto_correct:
                logger.info("✍️  Auto-correcting transcript...")
                correction_result = await self.auto_correct(full_text)
                corrected_text = correction_result.get("corrected")
                if corrected_text:
                    full_text = corrected_text
                else:
                    reason = correction_result.get("reason", "unknown")
                    logger.warning(f"⚠️  Auto-correction skipped ({reason})")

            audio_path_obj = Path(audio_path)
            resolved_output_dir = Path(output_dir) if output_dir else audio_path_obj.parent
            resolved_output_dir.mkdir(parents=True, exist_ok=True)
            transcript_md_path = resolved_output_dir / f"{audio_path_obj.stem}.transcript.md"

            logger.info("\n" + "="*80)
            logger.info("📄 TRANSCRIPT")
            logger.info("="*80)
            print(full_text)

            transcript_md_content = f"# Transcript\n\n{full_text}\n"
            transcript_md_path.write_text(transcript_md_content, encoding="utf-8")
            logger.info(f"💾 Transcript saved to {transcript_md_path}")

            # Optionally summarize
            if summarize:
                summary_result = await self.summarize(full_text)

                if summary_result.get("summary"):
                    logger.info("\n" + "="*80)
                    logger.info("📋 SUMMARY")
                    if summary_result.get("meeting_type"):
                        logger.info(f"Meeting Type: {summary_result['meeting_type']}")
                    logger.info("="*80)
                    print(summary_result["summary"])

                    summary_md_path = resolved_output_dir / f"{audio_path_obj.stem}.summary.md"
                    meeting_type = summary_result.get("meeting_type") or "Unknown"
                    summary_md_content = (
                        f"# Summary\n\n"
                        f"**Meeting Type:** {meeting_type}\n\n"
                        f"{summary_result['summary']}\n"
                    )
                    summary_md_path.write_text(summary_md_content, encoding="utf-8")
                    logger.info(f"💾 Summary saved to {summary_md_path}")
                else:
                    reason = summary_result.get("reason", "unknown")
                    logger.warning(f"⚠️  Summary unavailable ({reason})")

            return True

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(
        description="Transcribe and optionally summarize audio files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcribe_cli.py audio.wav
  python transcribe_cli.py audio.wav --summarize
  python transcribe_cli.py audio.wav --language es --summarize
        """
    )

    parser.add_argument("audio_file", help="Path to audio file to transcribe")
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Generate a summary after transcription (requires Ollama)"
    )
    parser.add_argument(
        "--no-auto-correct",
        action="store_true",
        help="Disable auto-correction (punctuation/casing/grammar)."
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Language code (e.g., en, es, fr, de). Auto-detect if not specified."
    )
    parser.add_argument(
        "--backend",
        default="faster-whisper",
        choices=["faster-whisper", "whisper-cpp"],
        help="Transcription backend to use."
    )
    parser.add_argument(
        "--use-metal",
        action="store_true",
        help="Use Metal-accelerated whisper.cpp backend (macOS only)."
    )
    parser.add_argument(
        "--model-size",
        default="large-v3",
        help="Whisper model size (tiny, base, small, medium, large-v3). Larger = higher quality."
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Device to run on (cpu, cuda). Defaults to auto."
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        help="Compute type (int8, int8_float16, float16). Defaults to auto."
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=10,
        help="Beam size (higher = more accurate, slower)."
    )
    parser.add_argument(
        "--best-of",
        type=int,
        default=10,
        help="Number of candidates to evaluate (higher = more accurate, slower)."
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (0.0 = deterministic)."
    )
    parser.add_argument(
        "--no-word-timestamps",
        action="store_true",
        help="Disable word-level timestamps (faster)."
    )
    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable VAD filtering (may be faster but less accurate segmentation)."
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=2,
        help="Max concurrent transcription tasks (CLI uses 1, but keeps same defaults)."
    )
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Skip model warm-up to start faster."
    )
    parser.add_argument(
        "--skip-llm-warmup",
        action="store_true",
        help="Skip LLM connectivity check before summarization."
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write .md outputs (defaults to the audio file's folder)."
    )
    parser.add_argument(
        "--whisper-cpp-path",
        default=None,
        help="(Advanced) Path to whisper.cpp binary. Auto-detected if not specified."
    )
    parser.add_argument(
        "--whisper-cpp-model",
        default=None,
        help="(Advanced) Path to whisper.cpp model file. Auto-detected if not specified."
    )

    args = parser.parse_args()

    # Auto-setup Metal backend if requested
    if args.use_metal:
        args.backend = "whisper-cpp"
        if not args.whisper_cpp_path:
            args.whisper_cpp_path = shutil.which("whisper.cpp") or shutil.which("main")
            if not args.whisper_cpp_path:
                # Check common install locations
                for candidate in [
                    Path.home() / "whisper.cpp",  # Installed in home directory
                    Path("/usr/local/bin/whisper.cpp"),
                    Path("./main"),
                    Path("./whisper.cpp"),
                ]:
                    if candidate.exists():
                        args.whisper_cpp_path = str(candidate)
                        break
        if not args.whisper_cpp_model:
            # Map model_size to ggml model filename
            model_map = {
                "tiny": "ggml-tiny.bin",
                "base": "ggml-base.bin",
                "small": "ggml-small.bin",
                "medium": "ggml-medium.bin",
                "large": "ggml-large.bin",
                "large-v2": "ggml-large-v2.bin",
                "large-v3": "ggml-large-v3.bin",
            }
            model_filename = model_map.get(args.model_size, "ggml-large-v3.bin")

            # First check existing locations
            candidates = [
                Path.home() / ".cache" / "whisper.cpp" / model_filename,
                Path.home() / ".cache" / "whisper.cpp" / model_filename.replace(".bin", ".gguf"),
                Path.home() / ".cache" / "whisper-models" / model_filename,
                Path.home() / ".cache" / "whisper-models" / model_filename.replace(".bin", ".gguf"),
                Path("./models") / model_filename,
                Path("./models") / model_filename.replace(".bin", ".gguf"),
            ]
            for candidate in candidates:
                if candidate.exists():
                    args.whisper_cpp_model = str(candidate)
                    break

            # If not found, auto-download (like faster-whisper)
            if not args.whisper_cpp_model:
                logger.info(f"Model not found locally. Attempting auto-download...")
                downloaded_path = download_whisper_cpp_model(args.model_size)
                if downloaded_path:
                    args.whisper_cpp_model = str(downloaded_path)

        if not args.whisper_cpp_path or not args.whisper_cpp_model:
            logger.error("❌ Metal backend requires whisper.cpp binary and model.")
            if not args.whisper_cpp_path:
                logger.error("   whisper.cpp not found. Install from: https://github.com/ggerganov/whisper.cpp")
            if not args.whisper_cpp_model:
                logger.error(f"   Model not found for size '{args.model_size}'. Download to ~/.cache/whisper.cpp/ or ./models/")
            sys.exit(1)
        logger.info(f"✅ Metal backend: {args.whisper_cpp_path}")
        logger.info(f"✅ Model (size: {args.model_size}): {args.whisper_cpp_model}")

    transcribe_options = {
        "beam_size": args.beam_size,
        "best_of": args.best_of,
        "temperature": args.temperature,
        "word_timestamps": not args.no_word_timestamps,
        "vad_filter": not args.no_vad,
    }

    auto_correct_enabled = not args.no_auto_correct
    warm_up_llm = (not args.skip_llm_warmup) and (args.summarize or auto_correct_enabled)

    cli = TranscribeAndSummarizeCLI(
        model_size=args.model_size,
        device=args.device,
        compute_type=args.compute_type,
        max_concurrency=args.max_concurrency,
        transcribe_options=transcribe_options,
        warm_up_transcriber=not args.skip_warmup,
        warm_up_llm=warm_up_llm,
        backend=args.backend,
        whisper_cpp_path=args.whisper_cpp_path,
        whisper_cpp_model=args.whisper_cpp_model,
        whisper_cpp_threads=None,
        whisper_cpp_args=None,
    )
    success = await cli.run(
        args.audio_file,
        summarize=args.summarize,
        language=args.language,
        output_dir=args.output_dir,
        auto_correct=auto_correct_enabled,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️  Interrupted by user")
        sys.exit(0)
