"""
Signal Processing and Feature Extraction in Pure NumPy.
Zero runtime scipy / scikit-learn dependency.
"""

from typing import Dict, Any, Tuple, List
import numpy as np


def compute_time_domain_metrics(signal: np.ndarray) -> Dict[str, float]:
    """Computes time-domain statistical metrics."""
    mag = np.abs(signal)
    rms = float(np.sqrt(np.mean(mag ** 2))) + 1e-12
    peak = float(np.max(mag))
    crest_factor = float(peak / rms)
    
    # Zero crossing rate (on real part)
    real_sig = np.real(signal)
    signs = np.sign(real_sig)
    zero_crossings = np.sum(np.abs(np.diff(signs)) > 0)
    zcr = float(zero_crossings / max(1, len(real_sig) - 1))
    
    # Dynamic range
    min_nonzero = np.min(mag[mag > 1e-6]) if np.any(mag > 1e-6) else 1e-6
    dynamic_range_db = float(20 * np.log10(max(peak, 1e-6) / min_nonzero))
    
    # SNR estimation via signal-to-noise floor heuristic
    sorted_pwr = np.sort(mag ** 2)
    noise_est = np.mean(sorted_pwr[: max(1, len(sorted_pwr) // 10)]) + 1e-12
    sig_est = np.mean(sorted_pwr[-(len(sorted_pwr) // 4):]) + 1e-12
    snr_db = float(10 * np.log10(sig_est / noise_est))

    return {
        "rms": float(round(rms, 6)),
        "peak": float(round(peak, 6)),
        "crestFactor": float(round(crest_factor, 4)),
        "zeroCrossingRate": float(round(zcr, 6)),
        "dynamicRangeDb": float(round(dynamic_range_db, 2)),
        "snrDb": float(round(snr_db, 2)),
    }


def compute_fft_spectrum(
    signal: np.ndarray, sample_rate: int, max_points: int = 512
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes FFT magnitude spectrum in dB.
    Returns: (frequencies_hz, magnitude_db)
    """
    n = len(signal)
    # Apply Hann window
    window = 0.5 * (1 - np.cos(2 * np.pi * np.arange(n) / (n - 1)))
    windowed = signal * window
    
    fft_vals = np.fft.fft(windowed)
    mag = np.abs(fft_vals) / n
    mag_db = 20 * np.log10(np.maximum(mag, 1e-9))
    
    if np.iscomplexobj(signal):
        # Full -fs/2 to +fs/2
        mag_db_shifted = np.fft.fftshift(mag_db)
        freqs = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / sample_rate))
    else:
        # Half spectrum 0 to fs/2
        half_n = n // 2
        mag_db_shifted = mag_db[:half_n]
        freqs = np.fft.fftfreq(n, 1.0 / sample_rate)[:half_n]

    # Downsample if needed for visualization payload
    if len(freqs) > max_points:
        indices = np.linspace(0, len(freqs) - 1, max_points, dtype=int)
        freqs = freqs[indices]
        mag_db_shifted = mag_db_shifted[indices]

    return freqs, mag_db_shifted


def compute_welch_psd(
    signal: np.ndarray,
    sample_rate: int,
    nperseg: int = 1024,
    noverlap: int = 512,
    max_points: int = 512,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes Welch Power Spectral Density using pure NumPy.
    Averages periodograms across overlapping Hann-windowed segments.
    """
    n = len(signal)
    if n < nperseg:
        nperseg = max(64, 2 ** int(np.floor(np.log2(n))))
        noverlap = nperseg // 2

    step = nperseg - noverlap
    num_segments = (n - noverlap) // step
    if num_segments < 1:
        num_segments = 1
        nperseg = n
        step = n

    window = 0.5 * (1 - np.cos(2 * np.pi * np.arange(nperseg) / (nperseg - 1)))
    win_pwr = np.sum(window ** 2)

    psd_accum = np.zeros(nperseg if np.iscomplexobj(signal) else nperseg // 2, dtype=np.float64)

    for i in range(num_segments):
        start = i * step
        seg = signal[start : start + nperseg]
        if len(seg) < nperseg:
            break
        w_seg = seg * window
        fft_seg = np.fft.fft(w_seg)
        pwr = (np.abs(fft_seg) ** 2) / (sample_rate * win_pwr)
        
        if np.iscomplexobj(signal):
            psd_accum += np.fft.fftshift(pwr)
        else:
            psd_accum += pwr[: nperseg // 2] * 2.0

    psd_avg = psd_accum / max(1, num_segments)
    psd_db = 10 * np.log10(np.maximum(psd_avg, 1e-12))

    if np.iscomplexobj(signal):
        freqs = np.fft.fftshift(np.fft.fftfreq(nperseg, 1.0 / sample_rate))
    else:
        freqs = np.fft.fftfreq(nperseg, 1.0 / sample_rate)[: nperseg // 2]

    if len(freqs) > max_points:
        idx = np.linspace(0, len(freqs) - 1, max_points, dtype=int)
        freqs = freqs[idx]
        psd_db = psd_db[idx]

    return freqs, psd_db


def compute_stft_spectrogram(
    signal: np.ndarray,
    sample_rate: int,
    n_fft: int = 512,
    hop_length: int = 256,
    max_time_bins: int = 128,
    max_freq_bins: int = 128,
) -> Tuple[List[float], List[float], List[List[float]]]:
    """
    Computes Short-Time Fourier Transform (STFT) Spectrogram in pure NumPy.
    Returns: (time_bins_seconds, freq_bins_hz, 2d_power_db_grid)
    """
    n = len(signal)
    if n < n_fft:
        n_fft = max(32, 2 ** int(np.floor(np.log2(n))))
        hop_length = n_fft // 2

    window = 0.5 * (1 - np.cos(2 * np.pi * np.arange(n_fft) / (n_fft - 1)))
    
    num_hops = (n - n_fft) // hop_length + 1
    if num_hops <= 0:
        num_hops = 1
        hop_length = 1

    spectrogram_frames = []
    times = []

    for i in range(num_hops):
        start = i * hop_length
        frame = signal[start : start + n_fft]
        if len(frame) < n_fft:
            break
        w_frame = frame * window
        spec = np.abs(np.fft.fft(w_frame))
        
        if np.iscomplexobj(signal):
            spec_shifted = np.fft.fftshift(spec)
        else:
            spec_shifted = spec[: n_fft // 2]

        spec_db = 20 * np.log10(np.maximum(spec_shifted, 1e-6))
        spectrogram_frames.append(spec_db)
        times.append(float(start / sample_rate))

    if not spectrogram_frames:
        return [0.0], [0.0], [[0.0]]

    matrix = np.array(spectrogram_frames)  # shape: (time, freq)

    if np.iscomplexobj(signal):
        freqs = np.fft.fftshift(np.fft.fftfreq(n_fft, 1.0 / sample_rate))
    else:
        freqs = np.fft.fftfreq(n_fft, 1.0 / sample_rate)[: n_fft // 2]

    # Downsample time and frequency dimensions if necessary
    t_idx = np.linspace(0, matrix.shape[0] - 1, min(max_time_bins, matrix.shape[0]), dtype=int)
    f_idx = np.linspace(0, matrix.shape[1] - 1, min(max_freq_bins, matrix.shape[1]), dtype=int)

    reduced_matrix = matrix[t_idx][:, f_idx]
    reduced_times = [float(times[i]) for i in t_idx]
    reduced_freqs = [float(freqs[i]) for i in f_idx]

    return reduced_times, reduced_freqs, reduced_matrix.tolist()


def compute_iq_metrics(signal: np.ndarray) -> Dict[str, float]:
    """Computes I/Q constellation and hardware impairment metrics."""
    i_samples = np.real(signal)
    q_samples = np.imag(signal)
    
    # Phase & DC
    phase = np.angle(signal)
    phase_noise = float(np.std(np.unwrap(phase)))
    dc_i = float(np.mean(i_samples))
    dc_q = float(np.mean(q_samples))
    
    # Amplitude imbalance
    i_pwr = np.mean(i_samples ** 2) + 1e-12
    q_pwr = np.mean(q_samples ** 2) + 1e-12
    iq_imbalance_db = float(10 * np.log10(i_pwr / q_pwr))
    
    # EVM estimation against nearest 4-QAM / BPSK reference grid
    mag = np.abs(signal) + 1e-12
    norm_sig = signal / np.mean(mag)
    # Ideal QPSK constellation points
    ref_points = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)
    # Distance to nearest constellation point
    dists = np.min(np.abs(norm_sig[:, None] - ref_points[None, :]), axis=1)
    evm_pct = float(np.sqrt(np.mean(dists ** 2)) * 100.0)

    return {
        "phaseNoiseRad": float(round(phase_noise, 4)),
        "evmPercent": float(round(min(evm_pct, 100.0), 2)),
        "iqImbalanceDb": float(round(iq_imbalance_db, 3)),
        "dcOffsetI": float(round(dc_i, 6)),
        "dcOffsetQ": float(round(dc_q, 6)),
    }


def compute_spectral_metrics(
    signal: np.ndarray, sample_rate: int
) -> Dict[str, float]:
    """Computes frequency domain statistical metrics."""
    n = len(signal)
    fft_mag = np.abs(np.fft.rfft(np.real(signal))) + 1e-12
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    
    pwr = fft_mag ** 2
    total_pwr = np.sum(pwr) + 1e-12
    
    # Spectral Centroid
    centroid = float(np.sum(freqs * pwr) / total_pwr)
    
    # Spectral Spread / Bandwidth
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * pwr) / total_pwr))
    
    # Spectral Flatness (geometric mean / arithmetic mean)
    geo_mean = np.exp(np.mean(np.log(pwr + 1e-12)))
    arith_mean = np.mean(pwr)
    flatness = float(min(1.0, max(0.0, geo_mean / (arith_mean + 1e-12))))
    
    # Spectral Rolloff (85% energy point)
    cum_pwr = np.cumsum(pwr)
    rolloff_idx = np.where(cum_pwr >= 0.85 * total_pwr)[0]
    rolloff = float(freqs[rolloff_idx[0]]) if len(rolloff_idx) > 0 else float(freqs[-1])
    
    # Peak / Center Frequency
    peak_idx = int(np.argmax(pwr))
    peak_freq = float(freqs[peak_idx])

    return {
        "centerFrequencyHz": float(round(centroid, 1)),
        "bandwidthHz": float(round(bandwidth, 1)),
        "spectralCentroidHz": float(round(centroid, 1)),
        "spectralFlatness": float(round(flatness, 4)),
        "spectralRolloffHz": float(round(rolloff, 1)),
        "peakFrequencyHz": float(round(peak_freq, 1)),
    }


def compute_shannon_entropy(signal: np.ndarray, num_bins: int = 64) -> float:
    """Computes normalized Shannon entropy of signal amplitude distribution [0.0 - 1.0]."""
    mag = np.abs(signal)
    hist, _ = np.histogram(mag, bins=num_bins, density=True)
    hist = hist[hist > 1e-12]
    # Normalize probabilities
    p = hist / np.sum(hist)
    entropy = -np.sum(p * np.log2(p))
    max_entropy = np.log2(num_bins)
    normalized_entropy = float(entropy / max_entropy)
    return float(round(min(1.0, max(0.0, normalized_entropy)), 4))


def extract_11d_features(signal: np.ndarray, sample_rate: int) -> Dict[str, float]:
    """
    Extracts the 11-dimensional feature vector for modulation classification.
    1. RMS
    2. Crest Factor
    3. Zero Crossing Rate
    4. Spectral Centroid
    5. Spectral Bandwidth
    6. Spectral Flatness
    7. Spectral Rolloff
    8. Phase Variance
    9. Amplitude Variance
    10. Kurtosis
    11. Shannon Entropy
    """
    mag = np.abs(signal)
    time_m = compute_time_domain_metrics(signal)
    spec_m = compute_spectral_metrics(signal, sample_rate)
    
    # Phase variance
    phase = np.angle(signal) if np.iscomplexobj(signal) else np.angle(signal + 1j * np.gradient(signal))
    phase_var = float(np.var(np.unwrap(phase)))
    
    # Amplitude variance
    amp_var = float(np.var(mag))
    
    # Kurtosis
    mean_mag = np.mean(mag)
    std_mag = np.std(mag) + 1e-12
    kurt = float(np.mean(((mag - mean_mag) / std_mag) ** 4))
    
    # Shannon entropy
    entropy = compute_shannon_entropy(signal)

    return {
        "rms": time_m["rms"],
        "crestFactor": time_m["crestFactor"],
        "zeroCrossingRate": time_m["zeroCrossingRate"],
        "spectralCentroid": spec_m["spectralCentroidHz"],
        "spectralBandwidth": spec_m["bandwidthHz"],
        "spectralFlatness": spec_m["spectralFlatness"],
        "spectralRolloff": spec_m["spectralRolloffHz"],
        "phaseVariance": float(round(phase_var, 4)),
        "amplitudeVariance": float(round(amp_var, 4)),
        "kurtosis": float(round(kurt, 4)),
        "shannonEntropy": entropy,
    }
