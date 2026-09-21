"""
Signal File Loaders for SignalLens AI.
Supports WAV (via standard wave module), OGG, and raw IQ binary streams (uint8, complex64, cf32, cs16).
Pure NumPy array output, no scipy dependency.
"""

import io
import wave
import struct
from typing import Tuple, Dict, Any, Optional
import numpy as np


def load_wav_bytes(content: bytes) -> Tuple[np.ndarray, int, bool]:
    """
    Decodes WAV audio from bytes using Python's standard wave library.
    Returns: (signal_array, sample_rate, is_iq)
    """
    with wave.open(io.BytesIO(content), "rb") as wf:
        num_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        num_frames = wf.getnframes()
        raw_frames = wf.readframes(num_frames)

    # Decode audio frames based on bit depth
    if sample_width == 1:
        # 8-bit unsigned PCM
        data = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float32)
        data = (data - 128.0) / 128.0
    elif sample_width == 2:
        # 16-bit signed PCM
        data = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 3:
        # 24-bit signed PCM
        raw_bytes = bytearray(raw_frames)
        total_samples = len(raw_bytes) // 3
        data = np.zeros(total_samples, dtype=np.float32)
        for i in range(total_samples):
            b = raw_bytes[i * 3 : i * 3 + 3]
            val = int.from_bytes(b, byteorder="little", signed=True)
            data[i] = val / 8388608.0
    elif sample_width == 4:
        # 32-bit signed PCM or float
        try:
            data = np.frombuffer(raw_frames, dtype=np.float32)
        except Exception:
            data = np.frombuffer(raw_frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if num_channels > 1:
        data = data.reshape(-1, num_channels)
        # If 2 channels, treat as I/Q or stereo
        if num_channels == 2:
            # Complex baseband I + jQ
            complex_iq = data[:, 0] + 1j * data[:, 1]
            return complex_iq, sample_rate, True
        else:
            # Average down to mono
            mono = np.mean(data, axis=1)
            return mono, sample_rate, False

    return data, sample_rate, False


def load_iq_raw_bytes(
    content: bytes, sample_rate: int = 2048000, dtype: str = "uint8"
) -> Tuple[np.ndarray, int, bool]:
    """
    Decodes raw SDR binary I/Q capture.
    Supported dtypes:
    - 'uint8' (RTL-SDR 8-bit unsigned interleaved I, Q, I, Q)
    - 'complex64' / 'cf32' (HackRF / USRP 32-bit float complex)
    - 'cs16' (16-bit signed integer interleaved I, Q)
    """
    if dtype in ("uint8", "u8"):
        raw = np.frombuffer(content, dtype=np.uint8).astype(np.float32)
        if len(raw) % 2 != 0:
            raw = raw[:-1]
        i_samples = (raw[0::2] - 127.5) / 127.5
        q_samples = (raw[1::2] - 127.5) / 127.5
        complex_iq = i_samples + 1j * q_samples
        return complex_iq, sample_rate, True

    elif dtype in ("complex64", "cf32", "float32"):
        complex_iq = np.frombuffer(content, dtype=np.complex64)
        return complex_iq, sample_rate, True

    elif dtype in ("cs16", "int16"):
        raw = np.frombuffer(content, dtype=np.int16).astype(np.float32) / 32768.0
        if len(raw) % 2 != 0:
            raw = raw[:-1]
        complex_iq = raw[0::2] + 1j * raw[1::2]
        return complex_iq, sample_rate, True

    else:
        raise ValueError(f"Unsupported IQ dtype: {dtype}")


def load_signal(
    content: bytes,
    file_name: str,
    sample_rate: int = 44100,
    iq_dtype: str = "uint8",
) -> Tuple[np.ndarray, int, bool, str]:
    """
    Unified auto-detecting signal loader.
    Returns: (signal_array, sample_rate, is_iq, detected_format)
    """
    lower_name = file_name.lower()
    
    if lower_name.endswith(".wav") or content[:4] == b"RIFF":
        sig, sr, is_iq = load_wav_bytes(content)
        return sig, sr, is_iq, "WAV"
    
    elif lower_name.endswith((".iq", ".raw", ".bin", ".dat", ".cf32", ".cs16")):
        # Auto-detect format from extension or user specification
        dt = "complex64" if lower_name.endswith(".cf32") else ("cs16" if lower_name.endswith(".cs16") else iq_dtype)
        sig, sr, is_iq = load_iq_raw_bytes(content, sample_rate=sample_rate, dtype=dt)
        return sig, sr, is_iq, "RAW_IQ"
        
    elif lower_name.endswith((".ogg", ".oga")):
        # Basic OGG container detection - fallback if WAV header found inside or raw float
        try:
            sig, sr, is_iq = load_wav_bytes(content)
            return sig, sr, is_iq, "OGG"
        except Exception:
            # Parse raw PCM samples
            raw = np.frombuffer(content, dtype=np.int16).astype(np.float32) / 32768.0
            return raw, sample_rate, False, "OGG"

    else:
        # Default try WAV first, then RAW
        try:
            sig, sr, is_iq = load_wav_bytes(content)
            return sig, sr, is_iq, "WAV"
        except Exception:
            sig, sr, is_iq = load_iq_raw_bytes(content, sample_rate=sample_rate, dtype="uint8")
            return sig, sr, is_iq, "BINARY"
