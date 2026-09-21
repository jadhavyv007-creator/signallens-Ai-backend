"""
Feature 15: Drone / UAV Micro-Doppler Blade Radar Signature Profiler.
Extracts periodic sideband modulations from rotating reflectors (propellers) and estimates rotor RPM in pure NumPy.
"""

from typing import Dict, Any, Optional
import numpy as np


def analyze_uav_microdoppler(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Performs cepstral / envelope spectrum peak-picking to identify rotor blade modulation harmonics.
    """
    mag = np.abs(signal)
    n = len(mag)
    
    # 1. Envelope spectrum to detect periodic modulations
    env = mag - np.mean(mag)
    fft_env = np.abs(np.fft.rfft(env))
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

    # Search in drone blade passing frequency range (10 Hz to 600 Hz -> 600 to 36,000 RPM)
    mask = (freqs >= 10.0) & (freqs <= 600.0)
    if not np.any(mask):
        return {
            "locked": False,
            "periodicSignatureDetected": False,
            "bladePassingFrequencyHz": None,
            "estimatedRotorRpm": None,
            "bladeCountHarmonicPeaks": 0,
        }

    search_freqs = freqs[mask]
    search_spec = fft_env[mask]

    # Peak detection
    peak_idx = int(np.argmax(search_spec))
    peak_val = search_spec[peak_idx]
    mean_noise = np.mean(search_spec) + 1e-12
    peak_prominence = peak_val / mean_noise

    # Check for periodic harmonics (2x, 3x peak frequency)
    dom_freq = float(search_freqs[peak_idx])
    harmonic_count = 0
    if peak_prominence > 4.5:
        for h in [2, 3]:
            h_freq = dom_freq * h
            if h_freq <= 600.0:
                h_idx = np.argmin(np.abs(search_freqs - h_freq))
                if search_spec[h_idx] > 2.0 * mean_noise:
                    harmonic_count += 1

    signature_detected = bool(peak_prominence > 4.5 and harmonic_count >= 1)

    if signature_detected:
        # Assuming typical 2-blade or 3-blade drone propeller
        # RPM = (BPF / num_blades) * 60
        rpm_est = float(round((dom_freq / 2.0) * 60.0, 1))
        bpf_hz = float(round(dom_freq, 1))
    else:
        rpm_est = None
        bpf_hz = None

    return {
        "locked": False,
        "periodicSignatureDetected": signature_detected,
        "bladePassingFrequencyHz": bpf_hz,
        "estimatedRotorRpm": rpm_est,
        "bladeCountHarmonicPeaks": harmonic_count + 1 if signature_detected else 0,
    }
