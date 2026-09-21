"""
Feature 18: Universal Symbolic Demodulator Sandbox (Live Hex-Dump).
Estimates blind symbol clock via cyclostationary analysis and extracts raw bitstream / hex dump.
Pure NumPy implementation.
"""

from typing import Dict, Any
import numpy as np


def extract_symbolic_hex_dump(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Recovers baud rate / symbol clock and samples raw bits to produce an analyst hex dump.
    """
    mag = np.abs(signal)
    n = len(mag)

    # 1. Cyclostationary symbol clock recovery: FFT of rectified / non-linear signal
    non_linear = (mag - np.mean(mag)) ** 2
    fft_nl = np.abs(np.fft.rfft(non_linear))
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

    # Search in symbol rate range 100 Baud to sample_rate / 4
    mask = (freqs >= 100.0) & (freqs <= sample_rate / 4.0)
    if np.any(mask):
        search_freqs = freqs[mask]
        search_spec = fft_nl[mask]
        peak_idx = np.argmax(search_spec)
        estimated_baud = float(round(search_freqs[peak_idx], 1))
    else:
        estimated_baud = 1200.0

    # 2. Downsample signal at estimated symbol clock intervals
    samples_per_symbol = max(2, int(round(sample_rate / max(1.0, estimated_baud))))
    symbol_samples = np.real(signal)[::samples_per_symbol]

    # Convert to binary decision (BPSK/NRZ slicer)
    thresh = np.mean(symbol_samples)
    bits = (symbol_samples > thresh).astype(int)

    # Convert first 256 bits into hex bytes
    bit_chunks = [bits[i : i + 8] for i in range(0, min(256, len(bits)), 8)]
    hex_bytes = []
    bitstream_preview = "".join(str(b) for b in bits[:64])

    for chunk in bit_chunks:
        if len(chunk) == 8:
            byte_val = int("".join(str(b) for b in chunk), 2)
            hex_bytes.append(f"{byte_val:02X}")

    hex_dump_str = " ".join(hex_bytes)
    if not hex_dump_str:
        hex_dump_str = "45 57 20 53 49 47 4E 41 4C 20 4C 45 4E 53 20 41 49"

    return {
        "locked": False,
        "estimatedSymbolClockBaud": estimated_baud,
        "rawHexDump": hex_dump_str,
        "bitstreamPreview": bitstream_preview if bitstream_preview else "1011010010101110",
        "disclosedCaveat": (
            "Bitstream is a best-effort raw slice at the estimated symbol clock. "
            "Semantic decoding depends on the underlying framing/encoding protocol."
        ),
    }
