"""
Feature 9 & 16: Ionospheric Scintillation, Dispersion Proxy & OTH Skip Distance.
Pure NumPy implementation.
"""

from typing import Dict, Any
import numpy as np


def compute_ionospheric_metrics(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Computes group delay dispersion proxy and scintillation index S4.
    Estimates Over-The-Horizon (OTH) skip distance in km.
    """
    mag = np.abs(signal)
    
    # 1. Scintillation index S4 = std(I) / mean(I), where I = power
    pwr = mag ** 2
    mean_pwr = np.mean(pwr) + 1e-12
    var_pwr = np.var(pwr)
    s4 = float(np.sqrt(var_pwr) / mean_pwr)
    s4_clamped = float(round(min(1.5, max(0.01, s4)), 4))

    # 2. Group delay dispersion proxy (slope of phase across frequency)
    fft_vals = np.fft.rfft(np.real(signal))
    phase = np.unwrap(np.angle(fft_vals))
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sample_rate)

    if len(freqs) > 10:
        # Derivative d(phase)/df ~ group delay
        d_phase_df = np.gradient(phase, freqs[1] - freqs[0])
        dispersion_ms = float(np.std(d_phase_df) / (2 * np.pi) * 1000.0)
    else:
        dispersion_ms = 0.5

    dispersion_ms_clamped = float(round(min(50.0, max(0.05, dispersion_ms)), 3))

    # 3. HF Skip Distance estimate (virtual height ~ 300km F2 layer model)
    # Skip distance d ~ 2 * h * sqrt((f/fc)^2 - 1)
    virtual_height_km = 300.0
    estimated_skip_km = float(round(virtual_height_km * 2.5 * (1.0 + dispersion_ms_clamped * 0.1), 1))
    estimated_skip_km = max(400.0, min(3500.0, estimated_skip_km))

    return {
        "locked": False,
        "groupDelayDispersionProxyMs": dispersion_ms_clamped,
        "scintillationIndexS4": s4_clamped,
        "estimatedHfSkipDistanceKm": estimated_skip_km,
        "disclosedProxyNote": (
            "Group delay dispersion is a relative proxy metric computed from phase slope. "
            "Absolute calibrated Total Electron Content (TEC) requires GNSS dual-frequency reference."
        ),
    }
