"""
Feature 14: Physical Layer Steganography & Covert Channel Sniffer.
Detects statistical anomalies in sub-noise floor phase/amplitude residuals.
Pure NumPy implementation.
"""

from typing import Dict, Any
import numpy as np


def detect_steganography_anomaly(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Analyzes high-order statistical moments of sub-noise floor residuals to flag potential covert channels.
    """
    mag = np.abs(signal)
    
    # 1. High-pass filter / residual extraction
    diff_sig = np.diff(mag)
    residual = diff_sig - np.mean(diff_sig)
    
    # 2. Residual variance and skewness
    res_var = float(np.var(residual))
    res_std = float(np.std(residual)) + 1e-12
    skewness = float(abs(np.mean((residual / res_std) ** 3)))
    kurtosis = float(np.mean((residual / res_std) ** 4))
    
    # Normal Gaussian residual has kurtosis ~ 3.0 and skewness ~ 0.0
    kurtosis_excess = abs(kurtosis - 3.0)
    
    # Anomaly flag if excess kurtosis or skewness exceeds threshold
    anomaly_flag = bool(kurtosis_excess > 1.8 or skewness > 0.85)
    confidence = float(round(min(0.97, max(0.55, (kurtosis_excess / 4.0) * 0.4 + (skewness / 2.0) * 0.4 + 0.5)), 4))

    return {
        "locked": False,
        "covertChannelAnomalyFlag": anomaly_flag,
        "residualVariance": float(round(res_var, 6)),
        "statisticalAnomalyConfidence": confidence,
        "disclosedCaveat": (
            "Flag indicates statistical deviation in sub-noise residual moments. "
            "False positives are possible with non-stationary multipath channels."
        ),
    }
