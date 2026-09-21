"""
Feature 11: Multi-Carrier Chirp Rate & Frequency Drift Analysis.
Measures chirp rate alpha (Hz/s) via instantaneous frequency regression and computes time-bandwidth product.
Pure NumPy implementation.
"""

from typing import Dict, Any
import numpy as np


def compute_chirp_rate(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Extracts chirp rate (Hz/s) and time-bandwidth product.
    Honest branding label applied per PRD Section 18.2.
    """
    n = len(signal)
    duration = n / sample_rate

    # Instantaneous phase via Hilbert transform approximation
    if np.iscomplexobj(signal):
        inst_phase = np.unwrap(np.angle(signal))
    else:
        # Analytic signal in frequency domain
        fft_sig = np.fft.fft(signal)
        h = np.zeros(n)
        if n % 2 == 0:
            h[0] = h[n // 2] = 1
            h[1 : n // 2] = 2
        else:
            h[0] = 1
            h[1 : (n + 1) // 2] = 2
        analytic = np.fft.ifft(fft_sig * h)
        inst_phase = np.unwrap(np.angle(analytic))

    t = np.arange(n) / sample_rate

    # Quadratic polynomial fit to phase: phi(t) = c0 + 2*pi*f0*t + pi*alpha*t^2
    # alpha = 2 * p[0] / pi
    if n > 10:
        poly = np.polyfit(t, inst_phase, 2)
        chirp_rate_hz_s = float((2.0 * poly[0]) / np.pi)
        
        # Fit goodness (R^2)
        fit_phase = np.polyval(poly, t)
        ss_tot = np.sum((inst_phase - np.mean(inst_phase)) ** 2) + 1e-12
        ss_res = np.sum((inst_phase - fit_phase) ** 2)
        r2 = float(max(0.0, min(1.0, 1.0 - (ss_res / ss_tot))))
    else:
        chirp_rate_hz_s = 0.0
        r2 = 1.0

    # Total bandwidth swept
    bandwidth = abs(chirp_rate_hz_s * duration)
    tb_product = float(max(1.0, bandwidth * duration))

    return {
        "locked": False,
        "chirpRateHzPerSec": float(round(chirp_rate_hz_s, 2)),
        "timeBandwidthProduct": float(round(tb_product, 2)),
        "quadraticPhaseFitR2": float(round(r2, 4)),
        "brandingLabel": "Chirp Rate & Drift Signature",
    }
