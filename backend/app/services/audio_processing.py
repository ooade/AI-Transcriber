import os
import logging
import noisereduce as nr
import librosa
import soundfile as sf
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preprocess_audio(input_path: str, output_path: str = None) -> str:
    """
    Enhance audio file quality before transcription.
    Applies noise reduction and normalization.
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_processed.wav"

    logger.info(f"Preprocessing audio: {input_path}")

    try:
        # Load audio (librosa loads as float32)
        y, sr = librosa.load(input_path, sr=16000)

        # 1. Noise Reduction using stationary noise assumption
        y_denoised = nr.reduce_noise(y=y, sr=sr, stationary=True)

        # 2. Peak Normalization
        max_val = np.max(np.abs(y_denoised))
        if max_val > 0:
            y_normalized = y_denoised / max_val
        else:
            y_normalized = y_denoised

        # Save processed file
        sf.write(output_path, y_normalized, sr)

        logger.info(f"Audio preprocessed and saved to {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        return input_path
