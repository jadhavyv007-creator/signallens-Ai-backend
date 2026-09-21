"""
Feature 13: RF Blind Source Separation (FastICA in Pure NumPy).
Zero runtime scipy / scikit-learn dependency.
Decomposes mixed RF signals into independent statistical source stems.
"""

from typing import Dict, Any, List
import warnings
import numpy as np


def separate_blind_sources(
    signal: np.ndarray, sample_rate: int, max_stems: int = 5, max_iter: int = 50, tol: float = 1e-4
) -> Dict[str, Any]:
    """
    Performs FastICA blind source separation on sub-band decomposed / time-delayed channels of the input signal.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        n = len(signal)
        real_sig = np.real(signal).astype(np.float64)

        # Construct multi-channel observation matrix using multi-tap delay embedding
        num_channels = min(max_stems, 5)
        delay_samples = max(4, sample_rate // 2000)
        
        rows = []
        for i in range(num_channels):
            start = i * delay_samples
            end = start + (n - (num_channels - 1) * delay_samples)
            rows.append(real_sig[start:end])
        
        X = np.array(rows, dtype=np.float64)  # shape (num_channels, n_samples)
        X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)
        X = np.clip(X, -10.0, 10.0)
        n_samples = X.shape[1]

        # 1. Centering & Standardizing
        X = X - np.mean(X, axis=1, keepdims=True)
        row_stds = np.std(X, axis=1, keepdims=True)
        row_stds[row_stds < 1e-6] = 1.0
        X = X / row_stds

        # 2. SVD-based Whitening
        U, S_vals, Vt = np.linalg.svd(X, full_matrices=False)
        S_vals = np.maximum(S_vals, 1e-6)
        X_white = np.sqrt(n_samples) * Vt[:num_channels, :]
        X_white = np.nan_to_num(X_white, nan=0.0, posinf=1.0, neginf=-1.0)

        # 3. FastICA fixed-point iteration with tanh contrast function
        W = np.random.randn(num_channels, num_channels)
        W = np.linalg.qr(W)[0]

        iterations = 0
        for iteration in range(max_iter):
            W_old = W.copy()
            
            # Matrix update: E[tanh(W * X) * X.T] - E[1 - tanh^2(W * X)] * W
            WX = W @ X_white
            g_WX = np.tanh(WX)
            g_prime = np.mean(1.0 - g_WX ** 2, axis=1, keepdims=True)
            W = (g_WX @ X_white.T) / n_samples - g_prime * W
            W = np.nan_to_num(W, nan=0.0, posinf=1.0, neginf=-1.0)
            
            # Symmetric orthogonalization
            cov_w = W @ W.T + 1e-5 * np.eye(num_channels)
            eig_w, eig_vec_w = np.linalg.eigh(cov_w)
            eig_w = np.maximum(eig_w, 1e-5)
            W = (eig_vec_w @ np.diag(1.0 / np.sqrt(eig_w)) @ eig_vec_w.T) @ W
            W = np.nan_to_num(W, nan=0.0, posinf=1.0, neginf=-1.0)

            # Check convergence
            lim = np.max(np.abs(np.abs(np.diag(W @ W_old.T)) - 1.0))
            iterations = iteration + 1
            if lim < tol:
                break

        # Recover independent source components S = W * X_white
        S = W @ X_white
        S = np.nan_to_num(S, nan=0.0, posinf=1.0, neginf=-1.0)

        # Label stems with informative descriptors
        stem_labels = ["Primary Carrier", "Telemetry Stream", "Interference / Jammer", "Transient Chirp", "Ambient Floor"]
        stems = []
        total_energy = np.sum(S ** 2) + 1e-12

        for i in range(num_channels):
            stem_sig = S[i]
            energy = np.sum(stem_sig ** 2)
            energy_ratio = float(round(energy / total_energy, 4))
            
            # Dominant frequency
            fft_mag = np.abs(np.fft.rfft(stem_sig[: min(4096, len(stem_sig))]))
            freqs = np.fft.rfftfreq(min(4096, len(stem_sig)), 1.0 / sample_rate)
            dom_freq = float(round(freqs[np.argmax(fft_mag)], 1))

            # Downsample waveform for UI transmission
            num_pts = min(128, len(stem_sig))
            indices = np.linspace(0, len(stem_sig) - 1, num_pts, dtype=int)
            downsampled_wf = [float(round(val, 4)) for val in stem_sig[indices]]

            stems.append({
                "stemIndex": i + 1,
                "label": stem_labels[i] if i < len(stem_labels) else f"Stem {i+1}",
                "energyRatio": energy_ratio,
                "dominantFreqHz": dom_freq,
                "waveformSamples": downsampled_wf,
            })

        return {
            "locked": False,
            "separatedStemsCount": len(stems),
            "stems": stems,
            "convergenceIterations": iterations,
        }
