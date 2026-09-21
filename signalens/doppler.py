"""
Feature 7: Doppler Shift & Orbital Velocity Estimator.
Measures carrier frequency drift over time (Hz/s) and computes velocity when carrier frequency is provided.
Pure NumPy implementation.
"""

from typing import Dict, Any, Optional
import numpy as np

SPEED_OF_LIGHT_KM_S = 299792.458  # km/s


def estimate_doppler_drift(
    signal: np.ndarray, sample_rate: int, nominal_carrier_hz: Optional[float] = None
) -> Dict[str, Any]:
    """
    Estimates Doppler drift rate (Hz/s) via instantaneous frequency regression.
    If nominal_carrier_hz is provided, calculates radial velocity in km/s.
    """
    n = len(signal)
    seg_size = min(1024, n // 8) if n >= 2048 else n // 2
    if seg_size < 128:
        return {
            "locked": False,
            "driftRateHzPerSec": 0.0,
            "centerShiftHz": 0.0,
            "estimatedVelocityKmPerSec": None,
            "note": "Signal too short for Doppler tracking",
        }

    num_segs = n // seg_size
    times = []
    freq_peaks = []

    for i in range(num_segs):
        seg = signal[i * seg_size : (i + 1) * seg_size]
        w = 0.5 * (1 - np.cos(2 * np.pi * np.arange(len(seg)) / (len(seg) - 1)))
        fft_mag = np.abs(np.fft.rfft(np.real(seg * w)))
        freqs = np.fft.rfftfreq(len(seg), 1.0 / sample_rate)
        
        peak_idx = np.argmax(fft_mag)
        freq_peaks.append(freqs[peak_idx])
        times.append((i * seg_size + seg_size / 2) / sample_rate)

    times = np.array(times)
    freq_peaks = np.array(freq_peaks)

    # Linear regression for drift rate (df/dt)
    if len(times) > 1:
        slope, intercept = np.polyfit(times, freq_peaks, 1)
        drift_rate_hz_s = float(slope)
        center_shift = float(freq_peaks[-1] - freq_peaks[0])
    else:
        drift_rate_hz_s = 0.0
        center_shift = 0.0

    # Calculate velocity only if nominal carrier is provided
    velocity_km_s = None
    if nominal_carrier_hz and nominal_carrier_hz > 0:
        velocity_km_s = float(round((center_shift / nominal_carrier_hz) * SPEED_OF_LIGHT_KM_S, 3))
        note = f"Velocity calculated using nominal carrier {nominal_carrier_hz / 1e6:.3f} MHz"
    else:
        note = "estimatedVelocityKmPerSec requires user-supplied carrierFreqHz input; drift rate computed from time-domain track"

    return {
        "locked": False,
        "driftRateHzPerSec": float(round(drift_rate_hz_s, 2)),
        "centerShiftHz": float(round(center_shift, 2)),
        "estimatedVelocityKmPerSec": velocity_km_s,
        "note": note,
    }
