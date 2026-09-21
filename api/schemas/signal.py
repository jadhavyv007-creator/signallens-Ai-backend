"""
Core Signal Analysis Pydantic models (matching frontend TypeScript types 1:1 with camelCase aliases).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class FileInfo(BaseModel):
    file_name: str = Field(alias="fileName")
    file_size_bytes: int = Field(alias="fileSizeBytes")
    duration_seconds: float = Field(alias="durationSeconds")
    sample_rate: int = Field(alias="sampleRate")
    num_channels: int = Field(alias="numChannels")
    format: str = Field(alias="format")
    is_iq: bool = Field(alias="isIq")
    storage_path: Optional[str] = Field(default=None, alias="storagePath")

    model_config = ConfigDict(populate_by_name=True)


class TimeDomainMetrics(BaseModel):
    rms: float
    peak: float
    crest_factor: float = Field(alias="crestFactor")
    zero_crossing_rate: float = Field(alias="zeroCrossingRate")
    dynamic_range_db: float = Field(alias="dynamicRangeDb")
    snr_db: float = Field(alias="snrDb")

    model_config = ConfigDict(populate_by_name=True)


class FrequencyDomainMetrics(BaseModel):
    center_frequency_hz: float = Field(alias="centerFrequencyHz")
    bandwidth_hz: float = Field(alias="bandwidthHz")
    spectral_centroid_hz: float = Field(alias="spectralCentroidHz")
    spectral_flatness: float = Field(alias="spectralFlatness")
    spectral_rolloff_hz: float = Field(alias="spectralRolloffHz")
    peak_frequency_hz: float = Field(alias="peakFrequencyHz")

    model_config = ConfigDict(populate_by_name=True)


class IQMetrics(BaseModel):
    phase_noise_rad: float = Field(alias="phaseNoiseRad")
    evm_percent: float = Field(alias="evmPercent")
    iq_imbalance_db: float = Field(alias="iqImbalanceDb")
    dc_offset_i: float = Field(alias="dcOffsetI")
    dc_offset_q: float = Field(alias="dcOffsetQ")

    model_config = ConfigDict(populate_by_name=True)


class SignalMetrics(BaseModel):
    time_domain: TimeDomainMetrics = Field(alias="timeDomain")
    frequency_domain: FrequencyDomainMetrics = Field(alias="frequencyDomain")
    iq_metrics: Optional[IQMetrics] = Field(default=None, alias="iqMetrics")
    shannon_entropy: float = Field(alias="shannonEntropy")

    model_config = ConfigDict(populate_by_name=True)


class WaveformPoint(BaseModel):
    time: float
    amplitude: float
    i_sample: Optional[float] = Field(default=None, alias="iSample")
    q_sample: Optional[float] = Field(default=None, alias="qSample")

    model_config = ConfigDict(populate_by_name=True)


class SpectrumPoint(BaseModel):
    frequency: float
    magnitude_db: float = Field(alias="magnitudeDb")

    model_config = ConfigDict(populate_by_name=True)


class PSDPoint(BaseModel):
    frequency: float
    power_db: float = Field(alias="powerDb")

    model_config = ConfigDict(populate_by_name=True)


class SpectrogramGrid(BaseModel):
    time_bins: List[float] = Field(alias="timeBins")
    freq_bins: List[float] = Field(alias="freqBins")
    matrix: List[List[float]] = Field(alias="matrix")  # 2D power in dB

    model_config = ConfigDict(populate_by_name=True)


class ConstellationPoint(BaseModel):
    i: float
    q: float

    model_config = ConfigDict(populate_by_name=True)


class Visualizations(BaseModel):
    waveform: List[WaveformPoint]
    fft_spectrum: List[SpectrumPoint] = Field(alias="fftSpectrum")
    welch_psd: List[PSDPoint] = Field(alias="welchPsd")
    spectrogram: SpectrogramGrid
    constellation: List[ConstellationPoint]

    model_config = ConfigDict(populate_by_name=True)


class ModulationClassScore(BaseModel):
    class_name: str = Field(alias="className")
    probability: float

    model_config = ConfigDict(populate_by_name=True)


class AIAnalysis(BaseModel):
    predicted_class: str = Field(alias="predictedClass")
    confidence: float
    is_anomaly: bool = Field(alias="isAnomaly")
    anomaly_score: float = Field(alias="anomalyScore")
    class_probabilities: List[ModulationClassScore] = Field(alias="classProbabilities")
    feature_vector_11d: Dict[str, float] = Field(alias="featureVector11d")

    model_config = ConfigDict(populate_by_name=True)


class CoreAnalysisResult(BaseModel):
    file_info: FileInfo = Field(alias="fileInfo")
    metrics: SignalMetrics
    visualizations: Visualizations
    ai_analysis: AIAnalysis = Field(alias="aiAnalysis")
    report: str

    model_config = ConfigDict(populate_by_name=True)
