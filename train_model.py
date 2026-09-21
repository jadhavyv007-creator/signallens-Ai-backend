"""
Model training script for SignalLens AI.
Trains a pure-NumPy Random Forest classifier across synthetic modulation schemes
and serializes weights to models/rf_classifier.json.
Zero scipy / scikit-learn dependency.
"""

import os
import time
import numpy as np
from signalens.classifier import RandomForestNP, CLASSES, generate_synthetic_signal
from signalens.features import extract_11d_features


def build_training_dataset(samples_per_class: int = 120, sample_rate: int = 44100):
    print(f"📡 Generating synthetic training dataset ({samples_per_class} per class)...")
    X = []
    y = []

    for class_idx, class_name in enumerate(CLASSES):
        for _ in range(samples_per_class):
            snr = np.random.uniform(5.0, 30.0)
            length = np.random.choice([2048, 4096, 8192])
            sig = generate_synthetic_signal(class_name, n_samples=length, sample_rate=sample_rate, snr_db=snr)
            feats = extract_11d_features(sig, sample_rate)
            feat_vec = list(feats.values())
            X.append(feat_vec)
            y.append(class_idx)

    return np.array(X, dtype=np.float64), np.array(y, dtype=np.int64)


def main():
    start_time = time.time()
    sample_rate = 44100
    X, y = build_training_dataset(samples_per_class=100, sample_rate=sample_rate)

    # Train / Test split (80 / 20)
    n_samples = len(X)
    indices = np.random.permutation(n_samples)
    split = int(0.8 * n_samples)
    train_idx, test_idx = indices[:split], indices[split:]

    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    print(f"🌲 Training Pure-NumPy Random Forest on {len(X_train)} samples...")
    rf = RandomForestNP(n_estimators=30, max_depth=8, min_samples_split=4, classes=CLASSES)
    rf.fit(X_train, y_train)

    # Evaluate on test set
    preds = rf.predict(X_test)
    accuracy = float(np.mean(preds == y_test) * 100.0)
    print(f"✅ Training completed in {time.time() - start_time:.2f}s | Test Accuracy: {accuracy:.2f}%")

    model_path = os.path.join(os.path.dirname(__file__), "models", "rf_classifier.json")
    rf.save_json(model_path)
    print(f"💾 Model serialized to {model_path}")


if __name__ == "__main__":
    main()
