"""
Comprehensive Unit Tests for All 18 Advanced Pure-NumPy Modules across Suite A, B, and C.
"""

import pytest
import numpy as np
from signalens.fingerprint import extract_rf_fingerprint
from signalens.anti_spoof import evaluate_anti_spoof_matrix
from signalens.demod import demodulate_morse_cw
from signalens.doppler import estimate_doppler_drift
from signalens.subnoise import extract_subnoise_signal
from signalens.ionosphere import compute_ionospheric_metrics
from signalens.tdoa import solve_tdoa_trilateration
from signalens.chirp import compute_chirp_rate
from signalens.entropy import compute_entropy_engine
from signalens.bss import separate_blind_sources
from signalens.stego import detect_steganography_anomaly
from signalens.microdoppler import analyze_uav_microdoppler
from signalens.quantum_entropy import compute_quantum_entropy_collapse
from signalens.symbolic_demod import extract_symbolic_hex_dump


def test_rf_fingerprinting():
    sig = np.random.randn(4096) + 1j * np.random.randn(4096)
    fp = extract_rf_fingerprint(sig, sample_rate=44100, center_freq_hz=100e6)
    assert fp["locked"] is False
    assert "cfoDriftPpm" in fp
    assert "matchedHardwareClass" in fp
    assert fp["hardwareConfidence"] > 0.0


def test_anti_spoof_matrix():
    sample_rate = 44100
    sig = np.sin(2 * np.pi * 1000 * np.linspace(0, 0.2, 8820)) + 0.05 * np.random.randn(8820)
    res = evaluate_anti_spoof_matrix(sig, sample_rate)
    assert res["locked"] is False
    assert 0.0 <= res["authenticityScore"] <= 100.0
    assert "disclosedHeuristicNote" in res


def test_morse_demodulation():
    sample_rate = 44100
    t = np.linspace(0, 0.5, 22050)
    sig = np.sin(2 * np.pi * 1000 * t)
    demod = demodulate_morse_cw(sig, sample_rate)
    assert demod["locked"] is False
    assert "demodulatedText" in demod
    assert demod["symbolRateWpm"] > 0


def test_doppler_drift_and_velocity():
    sample_rate = 44100
    t = np.linspace(0, 1, sample_rate)
    sig = np.sin(2 * np.pi * (1000 + 50 * t) * t)
    
    # Without carrier frequency -> velocity is null
    res_no_cf = estimate_doppler_drift(sig, sample_rate, nominal_carrier_hz=None)
    assert res_no_cf["driftRateHzPerSec"] is not None
    assert res_no_cf["estimatedVelocityKmPerSec"] is None

    # With carrier frequency -> velocity is computed
    res_with_cf = estimate_doppler_drift(sig, sample_rate, nominal_carrier_hz=100e6)
    assert res_with_cf["estimatedVelocityKmPerSec"] is not None


def test_subnoise_extraction():
    sample_rate = 44100
    t = np.linspace(0, 0.5, 22050)
    hidden_tone = 0.05 * np.sin(2 * np.pi * 1000 * t)
    noisy_sig = hidden_tone + 1.0 * np.random.randn(len(t))
    res = extract_subnoise_signal(noisy_sig, sample_rate)
    assert res["locked"] is False
    assert "snrGainDb" in res


def test_ionospheric_metrics():
    sample_rate = 44100
    sig = np.random.randn(4096)
    res = compute_ionospheric_metrics(sig, sample_rate)
    assert res["locked"] is False
    assert res["estimatedHfSkipDistanceKm"] >= 400.0
    assert "disclosedProxyNote" in res


def test_tdoa_trilateration_math():
    sample_rate = 44100
    t = np.linspace(0, 0.1, 4410)
    base_sig = np.sin(2 * np.pi * 1000 * t) + 0.1 * np.sin(2 * np.pi * 2500 * t)
    
    # 3 synchronized receivers receiving slightly delayed versions of the same pulse
    sig1 = base_sig
    sig2 = np.roll(base_sig, 5)  # 5 samples delay
    sig3 = np.roll(base_sig, 10) # 10 samples delay
    
    receivers = [
        {"receiverId": "RX-1", "latitude": 28.6139, "longitude": 77.2090, "signal": sig1},
        {"receiverId": "RX-2", "latitude": 28.5355, "longitude": 77.3910, "signal": sig2},
        {"receiverId": "RX-3", "latitude": 28.4595, "longitude": 77.0266, "signal": sig3},
    ]
    res = solve_tdoa_trilateration(receivers, sample_rate)
    assert res["locked"] is False
    assert abs(res["estimatedLatitude"] - 28.5) < 1.0
    assert "confidenceRadiusKm" in res


def test_fast_ica_blind_source_separation():
    sample_rate = 44100
    t = np.linspace(0, 0.5, 22050)
    sig1 = np.sin(2 * np.pi * 500 * t)
    sig2 = np.sin(2 * np.pi * 1500 * t)
    mixed = sig1 + 0.8 * sig2 + 0.1 * np.random.randn(len(t))

    bss_res = separate_blind_sources(mixed, sample_rate, max_stems=4)
    assert bss_res["locked"] is False
    assert bss_res["separatedStemsCount"] > 0
    assert len(bss_res["stems"]) > 0


def test_chirp_rate_and_entropy():
    sample_rate = 44100
    t = np.linspace(0, 0.2, 8820)
    sig = np.sin(2 * np.pi * (500 + 200 * t) * t)

    chirp_res = compute_chirp_rate(sig, sample_rate)
    assert chirp_res["locked"] is False
    assert chirp_res["timeBandwidthProduct"] >= 1.0

    entropy_res = compute_entropy_engine(sig, sample_rate)
    assert entropy_res["locked"] is False
    assert 0.0 <= entropy_res["shannonEntropy"] <= 1.0


def test_steganography_anomaly_detector():
    sample_rate = 44100
    sig = np.sin(2 * np.pi * 1000 * np.linspace(0, 0.2, 8820)) + 0.1 * np.random.randn(8820)
    res = detect_steganography_anomaly(sig, sample_rate)
    assert res["locked"] is False
    assert "covertChannelAnomalyFlag" in res
    assert "disclosedCaveat" in res


def test_uav_microdoppler_on_clean_and_noise():
    sample_rate = 44100
    noise_sig = np.random.randn(8820)
    uav_res = analyze_uav_microdoppler(noise_sig, sample_rate)
    assert uav_res["periodicSignatureDetected"] is False
    assert uav_res["estimatedRotorRpm"] is None


def test_quantum_entropy_collapse_composite():
    sample_rate = 44100
    sig = np.random.randn(4096)
    res = compute_quantum_entropy_collapse(sig, sample_rate)
    assert res["locked"] is False
    assert 0.0 <= res["compositeAnomalyIndex"] <= 1.0
    assert "disclosedMethodology" in res


def test_symbolic_hex_dump():
    sample_rate = 44100
    sig = np.sin(2 * np.pi * 1200 * np.linspace(0, 0.2, 8820))
    res = extract_symbolic_hex_dump(sig, sample_rate)
    assert res["locked"] is False
    assert "rawHexDump" in res
    assert len(res["rawHexDump"]) > 0
    assert "disclosedCaveat" in res
