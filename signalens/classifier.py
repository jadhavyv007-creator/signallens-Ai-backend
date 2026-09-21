"""
Pure-NumPy Random Forest Classifier & Signal Classification Engine.
Zero runtime scikit-learn dependency.
"""

import json
import os
from typing import List, Dict, Any, Tuple, Optional
import numpy as np


CLASSES = ["AM", "FM", "BPSK", "QPSK", "16-QAM", "CW", "NOISE"]


class StandardScalerNP:
    """Pure NumPy implementation of feature standardization."""
    def __init__(self):
        self.mean: Optional[np.ndarray] = None
        self.scale: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray) -> "StandardScalerNP":
        self.mean = np.mean(X, axis=0)
        self.scale = np.std(X, axis=0)
        self.scale[self.scale < 1e-8] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean is None or self.scale is None:
            return X
        return (X - self.mean) / self.scale

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean": self.mean.tolist() if self.mean is not None else [],
            "scale": self.scale.tolist() if self.scale is not None else [],
        }

    def from_dict(self, data: Dict[str, Any]) -> "StandardScalerNP":
        self.mean = np.array(data.get("mean", []), dtype=np.float64)
        self.scale = np.array(data.get("scale", []), dtype=np.float64)
        return self


class DecisionNode:
    """Node in a Pure-NumPy Decision Tree."""
    def __init__(
        self,
        feature_idx: Optional[int] = None,
        threshold: Optional[float] = None,
        left: Optional["DecisionNode"] = None,
        right: Optional["DecisionNode"] = None,
        probabilities: Optional[np.ndarray] = None,
    ):
        self.feature_idx = feature_idx
        self.threshold = threshold
        self.left = left
        self.right = right
        self.probabilities = probabilities  # Leaf node distribution

    def is_leaf(self) -> bool:
        return self.probabilities is not None

    def to_dict(self) -> Dict[str, Any]:
        if self.is_leaf():
            return {"probabilities": self.probabilities.tolist()}
        return {
            "feature_idx": self.feature_idx,
            "threshold": self.threshold,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecisionNode":
        if "probabilities" in d and d["probabilities"] is not None:
            return cls(probabilities=np.array(d["probabilities"], dtype=np.float64))
        return cls(
            feature_idx=d["feature_idx"],
            threshold=d["threshold"],
            left=cls.from_dict(d["left"]) if d.get("left") else None,
            right=cls.from_dict(d.get("right")) if d.get("right") else None,
        )


class DecisionTreeNP:
    """Pure-NumPy Classification Decision Tree."""
    def __init__(self, max_depth: int = 8, min_samples_split: int = 4, max_features: Optional[int] = None):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.root: Optional[DecisionNode] = None

    def fit(self, X: np.ndarray, y: np.ndarray, num_classes: int) -> "DecisionTreeNP":
        self.root = self._build_tree(X, y, depth=0, num_classes=num_classes)
        return self

    def _gini(self, y: np.ndarray, num_classes: int) -> float:
        if len(y) == 0:
            return 0.0
        counts = np.bincount(y, minlength=num_classes)
        probs = counts / len(y)
        return 1.0 - np.sum(probs ** 2)

    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int, num_classes: int) -> DecisionNode:
        n_samples, n_features = X.shape
        counts = np.bincount(y, minlength=num_classes)
        probs = counts / max(1, n_samples)

        # Stopping conditions
        if (
            depth >= self.max_depth
            or n_samples < self.min_samples_split
            or np.max(probs) == 1.0
        ):
            return DecisionNode(probabilities=probs)

        # Feature subsampling (Random Forest random feature selection)
        feat_indices = np.arange(n_features)
        if self.max_features and self.max_features < n_features:
            feat_indices = np.random.choice(n_features, self.max_features, replace=False)

        best_gini = float("inf")
        best_feat = None
        best_thresh = None
        best_left_idx = None
        best_right_idx = None

        current_gini = self._gini(y, num_classes)

        for feat in feat_indices:
            thresholds = np.unique(X[:, feat])
            if len(thresholds) > 20:
                thresholds = np.percentile(thresholds, np.linspace(5, 95, 20))

            for thresh in thresholds:
                left_idx = np.where(X[:, feat] <= thresh)[0]
                right_idx = np.where(X[:, feat] > thresh)[0]

                if len(left_idx) == 0 or len(right_idx) == 0:
                    continue

                gini_left = self._gini(y[left_idx], num_classes)
                gini_right = self._gini(y[right_idx], num_classes)
                w_gini = (len(left_idx) * gini_left + len(right_idx) * gini_right) / n_samples

                if w_gini < best_gini:
                    best_gini = w_gini
                    best_feat = feat
                    best_thresh = thresh
                    best_left_idx = left_idx
                    best_right_idx = right_idx

        if best_feat is None or best_gini >= current_gini:
            return DecisionNode(probabilities=probs)

        left_node = self._build_tree(X[best_left_idx], y[best_left_idx], depth + 1, num_classes)
        right_node = self._build_tree(X[best_right_idx], y[best_right_idx], depth + 1, num_classes)

        return DecisionNode(
            feature_idx=int(best_feat),
            threshold=float(best_thresh),
            left=left_node,
            right=right_node,
        )

    def predict_proba_single(self, x: np.ndarray, node: DecisionNode) -> np.ndarray:
        if node.is_leaf():
            return node.probabilities
        if x[node.feature_idx] <= node.threshold:
            return self.predict_proba_single(x, node.left)
        return self.predict_proba_single(x, node.right)


class RandomForestNP:
    """Pure-NumPy Random Forest Classifier."""
    def __init__(
        self,
        n_estimators: int = 25,
        max_depth: int = 8,
        min_samples_split: int = 4,
        classes: List[str] = CLASSES,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.classes = classes
        self.trees: List[DecisionTreeNP] = []
        self.scaler = StandardScalerNP()

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestNP":
        X_scaled = self.scaler.fit_transform(X)
        n_samples = len(X)
        num_classes = len(self.classes)
        max_features = max(1, int(np.sqrt(X.shape[1])))

        self.trees = []
        for _ in range(self.n_estimators):
            # Bootstrap sample
            boot_idx = np.random.choice(n_samples, n_samples, replace=True)
            tree = DecisionTreeNP(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                max_features=max_features,
            )
            tree.fit(X_scaled[boot_idx], y[boot_idx], num_classes=num_classes)
            self.trees.append(tree)

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        all_probs = []
        for x in X_scaled:
            tree_probs = [tree.predict_proba_single(x, tree.root) for tree in self.trees]
            avg_prob = np.mean(tree_probs, axis=0)
            all_probs.append(avg_prob)
        return np.array(all_probs)

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

    def save_json(self, file_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        data = {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "classes": self.classes,
            "scaler": self.scaler.to_dict(),
            "trees": [tree.root.to_dict() for tree in self.trees if tree.root],
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_json(cls, file_path: str) -> "RandomForestNP":
        with open(file_path, "r") as f:
            data = json.load(f)
        rf = cls(
            n_estimators=data["n_estimators"],
            max_depth=data["max_depth"],
            min_samples_split=data["min_samples_split"],
            classes=data["classes"],
        )
        rf.scaler.from_dict(data["scaler"])
        rf.trees = []
        for tree_dict in data["trees"]:
            tree = DecisionTreeNP()
            tree.root = DecisionNode.from_dict(tree_dict)
            rf.trees.append(tree)
        return rf


# Synthetic Signal Generators for RF Training & Testing
def generate_synthetic_signal(
    mod_type: str, n_samples: int = 4096, sample_rate: int = 44100, snr_db: float = 20.0
) -> np.ndarray:
    """Generates synthetic modulated RF/audio signal."""
    t = np.arange(n_samples) / sample_rate
    carrier_freq = 3000.0

    if mod_type == "AM":
        msg = 0.5 * np.sin(2 * np.pi * 300 * t) + 0.3 * np.cos(2 * np.pi * 700 * t)
        carrier = np.cos(2 * np.pi * carrier_freq * t)
        sig = (1.0 + msg) * carrier

    elif mod_type == "FM":
        msg = np.sin(2 * np.pi * 250 * t)
        freq_dev = 1500.0
        phase = 2 * np.pi * carrier_freq * t + (freq_dev / 250.0) * np.sin(2 * np.pi * 250 * t)
        sig = np.cos(phase)

    elif mod_type == "BPSK":
        bits = np.random.choice([1, -1], size=n_samples // 64)
        symbols = np.repeat(bits, 64)[:n_samples]
        sig = symbols * np.cos(2 * np.pi * carrier_freq * t)

    elif mod_type == "QPSK":
        symbols_i = np.repeat(np.random.choice([1, -1], size=n_samples // 64), 64)[:n_samples]
        symbols_q = np.repeat(np.random.choice([1, -1], size=n_samples // 64), 64)[:n_samples]
        sig = (symbols_i + 1j * symbols_q) * np.exp(1j * 2 * np.pi * carrier_freq * t)

    elif mod_type == "16-QAM":
        levels = [-3, -1, 1, 3]
        symbols_i = np.repeat(np.random.choice(levels, size=n_samples // 64), 64)[:n_samples]
        symbols_q = np.repeat(np.random.choice(levels, size=n_samples // 64), 64)[:n_samples]
        sig = (symbols_i + 1j * symbols_q) / np.sqrt(10) * np.exp(1j * 2 * np.pi * carrier_freq * t)

    elif mod_type == "CW":
        # Continuous Wave / Morse pulse
        envelope = (np.sin(2 * np.pi * 4 * t) > 0).astype(float)
        sig = envelope * np.cos(2 * np.pi * 1000 * t)

    elif mod_type == "NOISE":
        sig = np.random.randn(n_samples)

    else:
        sig = np.cos(2 * np.pi * 1000 * t)

    # Add Gaussian noise
    sig_pwr = np.mean(np.abs(sig) ** 2) + 1e-12
    noise_pwr = sig_pwr / (10.0 ** (snr_db / 10.0))
    noise = np.random.randn(n_samples) * np.sqrt(noise_pwr)
    if np.iscomplexobj(sig):
        noise = noise + 1j * np.random.randn(n_samples) * np.sqrt(noise_pwr)

    return sig + noise
