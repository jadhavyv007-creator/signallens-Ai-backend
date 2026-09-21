"""
Signal Preprocessing in Pure NumPy.
"""

from typing import Tuple
import numpy as np


def remove_dc_offset(signal: np.ndarray) -> np.ndarray:
    """Removes DC component from real or complex baseband signal."""
    if np.iscomplexobj(signal):
        i_clean = np.real(signal) - np.mean(np.real(signal))
        q_clean = np.imag(signal) - np.mean(np.imag(signal))
        return i_clean + 1j * q_clean
    return signal - np.mean(signal)


def normalize_power(signal: np.ndarray, target_power: float = 1.0) -> np.ndarray:
    """Normalizes average signal power to target value."""
    current_power = np.mean(np.abs(signal) ** 2)
    if current_power > 1e-12:
        scale = np.sqrt(target_power / current_power)
        return signal * scale
    return signal


def normalize_peak(signal: np.ndarray, target_peak: float = 1.0) -> np.ndarray:
    """Normalizes peak amplitude to target value."""
    peak = np.max(np.abs(signal))
    if peak > 1e-12:
        return signal * (target_peak / peak)
    return signal


def preprocess_signal(signal: np.ndarray) -> np.ndarray:
    """Complete preprocessing pipeline: DC removal + peak normalization."""
    no_dc = remove_dc_offset(signal)
    return normalize_peak(no_dc)
