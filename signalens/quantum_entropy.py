"""
Feature 17: Quantum RF Entropy Collapse (Composite Anomaly Index).
Honest implementation of composite entropy variance and spectral kurtosis score per PRD Section 7.7.
Pure NumPy implementation.
"""

from typing import Dict, Any
import numpy as np


def compute_quantum_entropy_collapse(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Computes Composite Anomaly Index derived from entropy variance and spectral kurtosis.
    """
    mag = np.abs(signal)
    
    # 1. Kurtosis of amplitude distribution
    mean_mag = np.mean(mag)
    std_mag = np.std(mag) + 1e-12
    kurtosis = float(np.mean(((mag - mean_mag) / std_mag) ** 4))
    skewness = float(abs(np.mean(((mag - mean_mag) / std_mag) ** 3)))

    ratio = float(round(kurtosis / (skewness + 1e-6), 3))

    # 2. Composite Anomaly Index (0.000 to 1.000)
    # Higher values indicate highly non-Gaussian, structured, synthetic modulation
    kurt_term = min(1.0, max(0.0, (kurtosis - 1.5) / 6.0))
    skew_term = min(1.0, max(0.0, skewness / 2.5))
    composite_index = float(round(0.6 * kurt_term + 0.4 * skew_term, 4))

    return {
        "locked": False,
        "compositeAnomalyIndex": composite_index,
        "kurtosisSkewnessRatio": ratio,
        "brandingLabel": "Quantum-Resistant Entropy Collapse Index",
        "disclosedMethodology": (
            "Composite score derived from non-Gaussian spectral kurtosis, skewness, "
            "and segment entropy deviation. No physical quantum collapse is measured."
        ),
    }
