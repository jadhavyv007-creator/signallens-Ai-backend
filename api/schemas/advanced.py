"""
Schemas for Advanced Suite A (Forensic Audio), Suite B (Aerospace Telemetry), and Suite C (Next-Gen EW) features.
Implements locked placeholders for tier upsells and full payload structures for unlocked features.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from api.schemas.signal import FileInfo, SignalMetrics, Visualizations, AIAnalysis


class LockedFeature(BaseModel):
    locked: bool = True
    required_tier: str = Field(alias="requiredTier")
    feature_name: str = Field(alias="featureName")
    message: str = Field(default="Upgrade tier to unlock this advanced intelligence module")
    note: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


# ── Suite A: Forensic Audio Pipeline ────────────────────────────────────

class CockpitPlayerResult(BaseModel):
    locked: bool = False
    raw_snr_db: float = Field(alias="rawSnrDb")
    denoised_snr_db: float = Field(alias="denoisedSnrDb")
    snr_improvement_db: float = Field(alias="snrImprovementDb")
    denoised_audio_b64: Optional[str] = Field(default=None, alias="denoisedAudioB64")

    model_config = ConfigDict(populate_by_name=True)


class EmitterFingerprint(BaseModel):
    locked: bool = False
    cfo_drift_ppm: float = Field(alias="cfoDriftPpm")
    iq_imbalance_phase_deg: float = Field(alias="iqImbalancePhaseDeg")
    iq_amplitude_imbalance_db: float = Field(alias="iqAmplitudeImbalanceDb")
    dc_offset_magnitude: float = Field(alias="dcOffsetMagnitude")
    matched_hardware_class: str = Field(alias="matchedHardwareClass")
    hardware_confidence: float = Field(alias="hardwareConfidence")

    model_config = ConfigDict(populate_by_name=True)


class SpectrogramLassoResult(BaseModel):
    locked: bool = False
    isolated_energy_pct: float = Field(alias="isolatedEnergyPct")
    snr_isolated_db: float = Field(alias="snrIsolatedDb")
    dominant_frequency_hz: float = Field(alias="dominantFrequencyHz")

    model_config = ConfigDict(populate_by_name=True)


class AntiSpoofResult(BaseModel):
    locked: bool = False
    authenticity_score: float = Field(alias="authenticityScore")  # 0 - 100%
    replay_artifact_detected: bool = Field(alias="replayArtifactDetected")
    spectral_continuity_score: float = Field(alias="spectralContinuityScore")
    disclosed_heuristic_note: str = Field(alias="disclosedHeuristicNote")

    model_config = ConfigDict(populate_by_name=True)


class LiveTranscriptResult(BaseModel):
    locked: bool = False
    demodulated_text: str = Field(alias="demodulatedText")
    protocol: str
    symbol_rate_wpm: float = Field(alias="symbolRateWpm")
    confidence: float

    model_config = ConfigDict(populate_by_name=True)


class PolarConstellationResult(BaseModel):
    locked: bool = False
    evm_rms_percent: float = Field(alias="evmRmsPercent")
    evm_peak_percent: float = Field(alias="evmPeakPercent")
    phase_jitter_degrees: float = Field(alias="phaseJitterDegrees")
    magnitude_error_db: float = Field(alias="magnitudeErrorDb")

    model_config = ConfigDict(populate_by_name=True)


# ── Suite B: Deep-Space & Aerospace Telemetry ────────────────────────────

class DopplerEstimate(BaseModel):
    locked: bool = False
    drift_rate_hz_per_sec: float = Field(alias="driftRateHzPerSec")
    center_shift_hz: float = Field(alias="centerShiftHz")
    estimated_velocity_km_per_sec: Optional[float] = Field(default=None, alias="estimatedVelocityKmPerSec")
    note: str

    model_config = ConfigDict(populate_by_name=True)


class SubNoiseExtractResult(BaseModel):
    locked: bool = False
    recovered_snr_db: float = Field(alias="recoveredSnrDb")
    snr_gain_db: float = Field(alias="snrGainDb")
    sub_noise_carrier_detected: bool = Field(alias="subNoiseCarrierDetected")
    confidence: float

    model_config = ConfigDict(populate_by_name=True)


class IonosphericResult(BaseModel):
    locked: bool = False
    group_delay_dispersion_proxy_ms: float = Field(alias="groupDelayDispersionProxyMs")
    scintillation_index_s4: float = Field(alias="scintillationIndexS4")
    estimated_hf_skip_distance_km: float = Field(alias="estimatedHfSkipDistanceKm")
    disclosed_proxy_note: str = Field(alias="disclosedProxyNote")

    model_config = ConfigDict(populate_by_name=True)


class ReceiverInput(BaseModel):
    receiver_id: str = Field(alias="receiverId")
    latitude: float
    longitude: float
    timestamp_utc: str = Field(alias="timestampUtc")

    model_config = ConfigDict(populate_by_name=True)


class TDoARequest(BaseModel):
    receivers: List[ReceiverInput]

    model_config = ConfigDict(populate_by_name=True)


class TDoAResult(BaseModel):
    locked: bool = False
    estimated_latitude: float = Field(alias="estimatedLatitude")
    estimated_longitude: float = Field(alias="estimatedLongitude")
    confidence_radius_km: float = Field(alias="confidenceRadiusKm")
    time_differences_ms: Dict[str, float] = Field(alias="timeDifferencesMs")

    model_config = ConfigDict(populate_by_name=True)


class ChirpDriftResult(BaseModel):
    locked: bool = False
    chirp_rate_hz_per_sec: float = Field(alias="chirpRateHzPerSec")
    time_bandwidth_product: float = Field(alias="timeBandwidthProduct")
    quadratic_phase_fit_r2: float = Field(alias="quadraticPhaseFitR2")
    branding_label: str = Field(alias="brandingLabel")

    model_config = ConfigDict(populate_by_name=True)


class EntropyResult(BaseModel):
    locked: bool = False
    shannon_entropy: float = Field(alias="shannonEntropy")  # 0.000 - 1.000
    entropy_variance: float = Field(alias="entropyVariance")
    spectral_kurtosis: float = Field(alias="spectralKurtosis")
    randomness_p_value: float = Field(alias="randomnessPValue")

    model_config = ConfigDict(populate_by_name=True)


# ── Suite C: Next-Gen EW & Sovereign Defense ─────────────────────────────

class BSSStem(BaseModel):
    stem_index: int = Field(alias="stemIndex")
    label: str
    energy_ratio: float = Field(alias="energyRatio")
    dominant_freq_hz: float = Field(alias="dominantFreqHz")
    waveform_samples: List[float] = Field(alias="waveformSamples")

    model_config = ConfigDict(populate_by_name=True)


class BSSResult(BaseModel):
    locked: bool = False
    separated_stems_count: int = Field(alias="separatedStemsCount")
    stems: List[BSSStem]
    convergence_iterations: int = Field(alias="convergenceIterations")

    model_config = ConfigDict(populate_by_name=True)


class StegoSnifferResult(BaseModel):
    locked: bool = False
    covert_channel_anomaly_flag: bool = Field(alias="covertChannelAnomalyFlag")
    residual_variance: float = Field(alias="residualVariance")
    statistical_anomaly_confidence: float = Field(alias="statisticalAnomalyConfidence")
    disclosed_caveat: str = Field(alias="disclosedCaveat")

    model_config = ConfigDict(populate_by_name=True)


class UAVMicroDopplerResult(BaseModel):
    locked: bool = False
    periodic_signature_detected: bool = Field(alias="periodicSignatureDetected")
    blade_passing_frequency_hz: Optional[float] = Field(default=None, alias="bladePassingFrequencyHz")
    estimated_rotor_rpm: Optional[float] = Field(default=None, alias="estimatedRotorRpm")
    blade_count_harmonic_peaks: int = Field(alias="bladeCountHarmonicPeaks")

    model_config = ConfigDict(populate_by_name=True)


class EntropyCollapseResult(BaseModel):
    locked: bool = False
    composite_anomaly_index: float = Field(alias="compositeAnomalyIndex")
    kurtosis_skewness_ratio: float = Field(alias="kurtosisSkewnessRatio")
    branding_label: str = Field(alias="brandingLabel")
    disclosed_methodology: str = Field(alias="disclosedMethodology")

    model_config = ConfigDict(populate_by_name=True)


class SymbolicDemodResult(BaseModel):
    locked: bool = False
    estimated_symbol_clock_baud: float = Field(alias="estimatedSymbolClockBaud")
    raw_hex_dump: str = Field(alias="rawHexDump")
    bitstream_preview: str = Field(alias="bitstreamPreview")
    disclosed_caveat: str = Field(alias="disclosedCaveat")

    model_config = ConfigDict(populate_by_name=True)


# ── Full Advanced Container ──────────────────────────────────────────────

class AdvancedFeaturesContainer(BaseModel):
    # Suite A (Cyber Pro)
    cockpit_player: Union[CockpitPlayerResult, LockedFeature] = Field(alias="cockpitPlayer")
    fingerprint: Union[EmitterFingerprint, LockedFeature] = Field(alias="fingerprint")
    lasso_isolator: Union[SpectrogramLassoResult, LockedFeature] = Field(alias="lassoisolator")
    anti_spoof: Union[AntiSpoofResult, LockedFeature] = Field(alias="antiSpoof")
    transcript: Union[LiveTranscriptResult, LockedFeature] = Field(alias="transcript")
    polar_constellation: Union[PolarConstellationResult, LockedFeature] = Field(alias="polarConstellation")

    # Suite B (Cyber Pro / Sovereign)
    doppler: Union[DopplerEstimate, LockedFeature] = Field(alias="doppler")
    sub_noise: Union[SubNoiseExtractResult, LockedFeature] = Field(alias="subNoise")
    ionosphere: Union[IonosphericResult, LockedFeature] = Field(alias="ionosphere")
    tdoa: Union[TDoAResult, LockedFeature] = Field(alias="tdoa")
    chirp: Union[ChirpDriftResult, LockedFeature] = Field(alias="chirp")
    entropy: Union[EntropyResult, LockedFeature] = Field(alias="entropy")

    # Suite C (Sovereign)
    bss: Union[BSSResult, LockedFeature] = Field(alias="bss")
    stego_sniffer: Union[StegoSnifferResult, LockedFeature] = Field(alias="stegoSniffer")
    uav_micro_doppler: Union[UAVMicroDopplerResult, LockedFeature] = Field(alias="uavMicroDoppler")
    entropy_collapse: Union[EntropyCollapseResult, LockedFeature] = Field(alias="entropyCollapse")
    symbolic_demod: Union[SymbolicDemodResult, LockedFeature] = Field(alias="symbolicDemod")

    model_config = ConfigDict(populate_by_name=True)


class FullSignalAnalysisResponse(BaseModel):
    file_info: FileInfo = Field(alias="fileInfo")
    metrics: SignalMetrics
    visualizations: Visualizations
    ai_analysis: AIAnalysis = Field(alias="aiAnalysis")
    report: str
    advanced: AdvancedFeaturesContainer

    model_config = ConfigDict(populate_by_name=True)
