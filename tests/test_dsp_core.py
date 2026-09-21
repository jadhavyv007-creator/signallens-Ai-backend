"""
Unit tests for Pure-NumPy Core DSP Algorithms.
"""

import pytest
import numpy as np
from signalens.preprocessing import preprocess_signal, remove_dc_offset
from signalens.features import (
    compute_time_domain_metrics,
    compute_spectral_metrics,
    compute_fft_spectrum,
    compute_welch_psd,
    compute_stft_spectrogram,
    compute_shannon_entropy,
    extract_11d_features,
)
from signalens.loaders import load_signal


def test_dc_removal_and_normalization():
    # Signal with large DC bias
    raw_sig = np.sin(2 * np.pi * 1000 * np.linspace(0, 1, 1000)) + 5.0
    cleaned = preprocess_signal(raw_sig)
    assert abs(np.mean(cleaned)) < 1e-4
    assert np.max(np.abs(cleaned)) <= 1.0


def test_time_domain_metrics():
    t = np.linspace(0, 1, 44100)
    sig = np.sin(2 * np.pi * 440 * t)  # Pure tone
    metrics = compute_time_domain_metrics(sig)
    assert "rms" in metrics
    assert "crestFactor" in metrics
    assert "zeroCrossingRate" in metrics
    assert metrics["rms"] > 0.6  # RMS of sine ~ 0.707


def test_welch_psd_and_fft():
    sample_rate = 44100
    t = np.linspace(0, 0.5, 22050)
    sig = np.sin(2 * np.pi * 2000 * t)
    
    freqs_fft, mag_db = compute_fft_spectrum(sig, sample_rate)
    assert len(freqs_fft) > 0
    peak_fft_freq = freqs_fft[np.argmax(mag_db)]
    assert abs(peak_fft_freq - 2000.0) < 50.0  # Peak within resolution

    freqs_psd, pwr_db = compute_welch_psd(sig, sample_rate)
    peak_psd_freq = freqs_psd[np.argmax(pwr_db)]
    assert abs(peak_psd_freq - 2000.0) < 50.0


def test_stft_spectrogram():
    sample_rate = 44100
    t = np.linspace(0, 0.2, 8820)
    sig = np.sin(2 * np.pi * 1000 * t)
    times, freqs, matrix = compute_stft_spectrogram(sig, sample_rate)
    assert len(times) > 0
    assert len(freqs) > 0
    assert len(matrix) == len(times)
    assert len(matrix[0]) == len(freqs)


def test_11d_feature_extraction():
    sample_rate = 44100
    t = np.linspace(0, 0.1, 4410)
    sig = np.sin(2 * np.pi * 1000 * t)
    feats = extract_11d_features(sig, sample_rate)
    assert len(feats) == 11
    assert "rms" in feats
    assert "shannonEntropy" in feats
    assert 0.0 <= feats["shannonEntropy"] <= 1.0
