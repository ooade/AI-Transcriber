"""
Whisper.cpp auto-setup utility for Metal/CUDA acceleration.

Handles:
- Platform detection (macOS Metal, Linux/Windows CUDA)
- Binary location detection
- Pre-compiled binary download from GitHub releases
- Fallback compilation from source with optimal flags
- Model file auto-download from HuggingFace
"""

import os
import platform
import shutil
import subprocess
import urllib.request
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# Model size to ggml filename mapping
MODEL_MAP = {
    "tiny": "ggml-tiny.bin",
    "base": "ggml-base.bin",
    "small": "ggml-small.bin",
    "medium": "ggml-medium.bin",
    "large": "ggml-large-v3.bin",
    "large-v2": "ggml-large-v2.bin",
    "large-v3": "ggml-large-v3.bin",
}


def detect_platform() -> Tuple[str, bool, bool]:
    """
    Detect platform and acceleration capabilities.

    Returns:
        Tuple of (platform_name, has_metal, has_cuda)
    """
    system = platform.system()

    # Check for Metal (macOS)
    has_metal = system == "Darwin"

    # Check for CUDA (Linux/Windows with nvidia-smi)
    has_cuda = False
    if system in ("Linux", "Windows"):
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                timeout=5
            )
            has_cuda = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return system, has_metal, has_cuda


def find_existing_binary() -> Optional[Path]:
    """
    Search common locations for existing whisper.cpp binary.

    Returns:
        Path to binary if found, None otherwise
    """
    # Check in PATH
    for binary_name in ["whisper.cpp", "main"]:
        path = shutil.which(binary_name)
        if path:
            return Path(path)

    # Check common install locations
    candidates = [
        Path.home() / ".local" / "bin" / "whisper.cpp",
        Path.home() / ".local" / "bin" / "main",
        Path("/usr/local/bin/whisper.cpp"),
        Path("/usr/local/bin/main"),
        Path.home() / "whisper.cpp" / "main",
        Path.home() / "whisper.cpp" / "whisper.cpp",
        Path("/tmp/whisper.cpp/main"),
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            # Verify it's executable
            if os.access(candidate, os.X_OK):
                return candidate

    return None


def download_precompiled_binary(cache_dir: Path) -> Optional[Path]:
    """
    Attempt to download pre-compiled whisper.cpp binary from GitHub releases.

    Note: This is a placeholder - whisper.cpp doesn't provide pre-built binaries.
    We'll compile from source instead.

    Returns:
        Path to downloaded binary if successful, None otherwise
    """
    # whisper.cpp doesn't provide pre-compiled binaries in releases
    # Users need to compile from source
    logger.info("Pre-compiled binaries not available. Will compile from source.")
    return None


def compile_from_source(cache_dir: Path, has_metal: bool, has_cuda: bool) -> Optional[Path]:
    """
    Clone and compile whisper.cpp from source with optimal flags.

    Args:
        cache_dir: Directory to build in
        has_metal: Whether Metal acceleration is available
        has_cuda: Whether CUDA acceleration is available

    Returns:
        Path to compiled binary if successful, None otherwise
    """
    repo_dir = cache_dir / "whisper.cpp"

    # Check if already compiled, prioritizing whisper-cli
    candidate_binary_paths = [
        repo_dir / "build" / "bin" / "whisper-cli",  # New CMake build location, new name
        repo_dir / "build" / "bin" / "main",         # New CMake build location, old name
        repo_dir / "main",                           # Old Makefile build location
    ]

    for path in candidate_binary_paths:
        if path.exists() and os.access(path, os.X_OK):
            logger.info(f"✅ Found existing compiled binary: {path}")
            return path

    try:
        # Clone repository if not exists
        if not repo_dir.exists():
            logger.info("📦 Cloning whisper.cpp repository...")
            result = subprocess.run(
                ["git", "clone", "https://github.com/ggerganov/whisper.cpp.git", str(repo_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(f"Failed to clone repository: {result.stderr}")
                return None
            logger.info("✅ Clone completed, verifying repository...")

        # Verify Makefile exists
        makefile = repo_dir / "Makefile"
        if not makefile.exists():
            logger.error(f"Makefile not found at {makefile}")
            return None

        # Build with appropriate flags
        logger.info("🔨 Compiling whisper.cpp (this may take 2-5 minutes)...")

        # First try clean make to avoid CMake issues
        logger.info("   Running 'make clean'...")
        result_clean = subprocess.run(
            ["make", "-C", str(repo_dir), "clean"],
            capture_output=True,
            timeout=60,
        )
        logger.debug(f"   make clean exit code: {result_clean.returncode}")

        make_cmd = ["make", "-C", str(repo_dir), "-j4"]
        env = os.environ.copy()

        if has_metal:
            logger.info("   Using Metal acceleration (automatic on macOS)...")
            # Metal is auto-detected by whisper.cpp Makefile on macOS
            # Disable OpenMP to avoid CMake deprecation issues
            env["WHISPER_NO_OPENMP"] = "1"
        elif has_cuda:
            logger.info("   Using CUDA acceleration flags...")
            # Set CUDA flags
            env["WHISPER_CUDA"] = "1"
            env["WHISPER_NO_OPENMP"] = "1"

        logger.debug(f"   Running make from: {repo_dir}")
        logger.debug(f"   Makefile exists: {(repo_dir / 'Makefile').exists()}")

        result = subprocess.run(
            make_cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
            cwd=str(repo_dir),  # Set working directory for make
        )

        if result.returncode != 0:
            logger.error(f"Compilation failed: {result.stderr}")
            logger.debug(f"Make stdout: {result.stdout}")
            # Try fallback without OpenMP flags
            if has_metal or has_cuda:
                logger.info("⚠️  Retrying without OpenMP...")
                env_fallback = os.environ.copy()
                env_fallback["WHISPER_NO_OPENMP"] = "1"
                result = subprocess.run(
                    make_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env_fallback,
                    cwd=str(repo_dir),
                )
                if result.returncode != 0:
                    logger.error(f"Compilation still failed: {result.stderr}")
                    logger.debug(f"Make stdout: {result.stdout}")
                    return None
            else:
                return None

        # Verify binary was created (check both old and newer cmake locations)
        # Also check for whisper-cli (newer versions)
        cli_binary_path = repo_dir / "build" / "bin" / "whisper-cli"

        if cli_binary_path.exists() and os.access(cli_binary_path, os.X_OK):
            logger.info(f"✅ Successfully compiled: {cli_binary_path}")
            return cli_binary_path
        elif cmake_binary_path.exists() and os.access(cmake_binary_path, os.X_OK):
            logger.info(f"✅ Successfully compiled: {cmake_binary_path}")
            return cmake_binary_path
        elif binary_path.exists() and os.access(binary_path, os.X_OK):
            logger.info(f"✅ Successfully compiled: {binary_path}")
            return binary_path
        else:
            logger.error(f"Binary not found after compilation (checked {cli_binary_path}, {cmake_binary_path}, {binary_path})")
            return None

    except subprocess.TimeoutExpired:
        logger.error("Compilation timed out")
        return None
    except Exception as e:
        logger.error(f"Compilation error: {e}")
        return None


def download_whisper_cpp_model(model_size: str, cache_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Auto-download whisper.cpp ggml model from HuggingFace.

    Args:
        model_size: Model size (tiny, base, small, medium, large-v3)
        cache_dir: Optional cache directory (defaults to ~/.cache/whisper.cpp)

    Returns:
        Path to downloaded model if successful, None otherwise
    """
    if cache_dir is None:
        # Use /app/temp since system user home might be /nonexistent
        cache_dir = Path("/app/temp/.cache/whisper.cpp")

    cache_dir.mkdir(parents=True, exist_ok=True)

    model_filename = MODEL_MAP.get(model_size, "ggml-large-v3.bin")
    model_path = cache_dir / model_filename

    # Check if already exists
    if model_path.exists() and model_path.stat().st_size > 1024 * 1024:
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
            if block_num % 50 == 0 or downloaded >= total_size:
                logger.info(f"   Progress: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")

        urllib.request.urlretrieve(url, model_path, reporthook=_show_progress)

        # Verify downloaded file
        if model_path.exists() and model_path.stat().st_size > 1024 * 1024:
            logger.info(f"✅ Downloaded: {model_path} ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")
            return model_path
        else:
            logger.error(f"Download failed or file too small: {model_path}")
            model_path.unlink(missing_ok=True)
            return None

    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        model_path.unlink(missing_ok=True)
        return None


def setup_whisper_cpp(force_compile: bool = False) -> Tuple[Optional[Path], bool, bool]:
    """
    Main setup function: detects platform, finds/compiles binary.

    Args:
        force_compile: If True, compile from source even if binary exists

    Returns:
        Tuple of (binary_path, has_metal, has_cuda)
    """
    system, has_metal, has_cuda = detect_platform()
    logger.info(f"Platform: {system}, Metal: {has_metal}, CUDA: {has_cuda}")

    # Try to find existing binary first
    if not force_compile:
        binary_path = find_existing_binary()
        if binary_path:
            logger.info(f"✅ Found existing whisper.cpp: {binary_path}")
            return binary_path, has_metal, has_cuda

    # Set up cache directory
    # Use /app/temp since system user home might be /nonexistent
    cache_dir = Path("/app/temp/.cache/whisper.cpp")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Try pre-compiled binary (currently returns None)
    binary_path = download_precompiled_binary(cache_dir)
    if binary_path:
        return binary_path, has_metal, has_cuda

    # Compile from source
    logger.info("🔧 No binary found. Compiling from source...")
    binary_path = compile_from_source(cache_dir, has_metal, has_cuda)

    if binary_path:
        return binary_path, has_metal, has_cuda

    logger.error("❌ Failed to set up whisper.cpp binary")
    return None, has_metal, has_cuda


def verify_whisper_cpp(binary_path: Path) -> bool:
    """
    Verify whisper.cpp binary works by running --help.

    Args:
        binary_path: Path to whisper.cpp binary

    Returns:
        True if binary is functional
    """
    try:
        result = subprocess.run(
            [str(binary_path), "--help"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        # Check if help output contains expected content or deprecation warning
        help_output = (result.stdout + result.stderr).lower()
        logger.info(f"Binary verification output: {help_output}, Code: {result.returncode}")
        return (
            "usage" in help_output
            or "options" in help_output
            or "deprecated" in help_output
            or result.returncode == 0
        )
    except Exception as e:
        logger.error(f"Binary verification failed: {e}")
        return False
