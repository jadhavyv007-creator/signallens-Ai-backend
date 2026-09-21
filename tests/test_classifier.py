"""
Unit tests for Pure-NumPy Random Forest Model.
"""

import pytest
import numpy as np
from signalens.classifier import (
    RandomForestNP,
    CLASSES,
    generate_synthetic_signal,
)
from signalens.features import extract_11d_features
from signalens.analysis import get_model


def test_model_loading_and_prediction():
    model = get_model()
    assert model is not None
    assert len(model.classes) == len(CLASSES)

    # Test prediction on synthetic signals
    sample_rate = 44100
    for mod_name in ["AM", "FM", "CW", "NOISE"]:
        sig = generate_synthetic_signal(mod_name, n_samples=4096, sample_rate=sample_rate, snr_db=25.0)
        feats = extract_11d_features(sig, sample_rate)
        feat_vec = np.array([list(feats.values())])
        
        probs = model.predict_proba(feat_vec)[0]
        assert len(probs) == len(CLASSES)
        assert abs(np.sum(probs) - 1.0) < 1e-4
        pred_idx = np.argmax(probs)
        pred_label = model.classes[pred_idx]
        assert isinstance(pred_label, str)
