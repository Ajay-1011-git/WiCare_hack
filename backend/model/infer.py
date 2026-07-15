"""Real ML inference for the sensing server.

Loads the deployed drift-detection classifier + CUSUM detector from this directory and
runs exactly one classify_window() + track_drift() per tick. There is one global
SessionState (single-process, matching the LiveState architecture in the FastAPI app --
no auth / multi-user here).

Pipeline per window (see acs_model_*_norm.json):
  1. map live reading -> training feature names (map_live_to_features)
  2. compute *_zbase  = z-score of each base feature vs THIS session's personal
     baseline (mean/std of the first `settle_windows` readings)
  3. compute *_delta  = current - previous reading
  4. assemble the vector in norm["feature_order"], z-normalize each entry with
     norm["per_source_zscore"]["cap:<feature>"], impute missing with norm["impute_fill"]
  5. model.predict_proba -> probability; classify_window() turns it into the anomaly block
  6. track_drift() feeds the probability into a CUSUM using manifest "cusum" params

WINDOWING NOTE: training used 180s aggregated windows over raw signal. This mock backend
already emits one aggregated reading per tick and has no raw signal to window, so each
tick's reading is treated AS one window's features directly. Real ESP32/MAX30102 hardware
would need a genuine 180s signal-aggregation stage before this module.
"""

import json
import math
import threading
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent


def _load_json(name):
    # json.load tolerates the NaN literals present in acs_manifest.json.
    with open(MODEL_DIR / name) as f:
        return json.load(f)


MANIFEST = _load_json("acs_manifest.json")
DEPLOYED = MANIFEST["deployed"]  # "B"
CUSUM_PARAMS = MANIFEST["cusum"]  # target, sigma, k, h

with warnings.catch_warnings():
    # Trained on scikit-learn 1.6.1; a newer runtime warns on unpickle. For
    # LogisticRegression the persisted state is just coef_/intercept_/classes_ and
    # predict_proba is a deterministic function of those, so the warning is benign.
    warnings.simplefilter("ignore")
    MODELS = {
        "A": joblib.load(MODEL_DIR / "acs_model_A.joblib"),
        "B": joblib.load(MODEL_DIR / "acs_model_B.joblib"),
    }
NORMS = {
    "A": _load_json("acs_model_A_norm.json"),
    "B": _load_json("acs_model_B_norm.json"),
}

# The mock feed represents CAP-style aggregated windows, and "cap" is the only source
# Model B's norm file carries (Model A also has "sleep_edf"). Use it for both.
SOURCE_PREFIX = "cap"

# Base features that carry *_zbase and *_delta variants (sleep_onset_latency does not).
_DERIVED = [
    "breathing_rate_bpm",
    "breathing_var",
    "motion_index",
    "sleep_fragmentation_index",
    "heart_rate_bpm",
]

# Personal-baseline std floor per feature. The mock emits very smooth readings, so the
# std of the first `settle_windows` calibration readings can be near-zero -- which makes
# *_zbase = (value - mean)/std hypersensitive, so ordinary normal-mode wander produces
# wild probability swings and false CUSUM alarms. Flooring the std to a realistic
# within-subject spread keeps zbase in the range the model saw in training. Real 180s
# hardware windows would have natural variance and would not need this.
_STD_FLOOR = {
    "breathing_rate_bpm": 1.0,
    "breathing_var": 0.5,
    "motion_index": 0.06,
    "sleep_fragmentation_index": 0.03,
    "heart_rate_bpm": 5.0,
}


def map_live_to_features(reading: dict) -> dict:
    """Explicit map from the live response shape to training feature names. The live
    payload nests breathing under breathing_rate_bpm.{value,variability}; training used
    flat breathing_rate_bpm / breathing_var. Keep this mapping explicit -- it is the
    easiest place to introduce a silent bug."""
    br = reading["breathing_rate_bpm"]
    return {
        "breathing_rate_bpm": br["value"],
        "breathing_var": br["variability"],
        "motion_index": reading["motion_index"],
        "sleep_fragmentation_index": reading["sleep_fragmentation_index"],
        "sleep_onset_latency": reading["sleep_onset_latency"],
        "heart_rate_bpm": reading.get("heart_rate_bpm"),
    }


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


class SessionState:
    """Per-session inference state: personal-baseline buffer, previous reading (for
    deltas), running CUSUM, and a rolling event log. One global instance lives in this
    module (see SESSION)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.settle_windows = NORMS[DEPLOYED]["settle_windows"]
        self.baseline_buffer = []  # first settle_windows base-feature dicts
        self.baseline = None  # {feature: (mean, std)} once settled
        self.prev = None  # previous base-feature dict, for *_delta
        self.cusum_s = 0.0
        self.alert_latched = False  # latches until reset() -- never auto-resets
        self.drift_started = False
        self.n_windows = 0
        self.events = []
        self._log("Session started — calibrating baseline")

    # -- event log -------------------------------------------------------------
    def _log(self, desc: str, alert: bool = False) -> None:
        self.events.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "desc": desc,
                "alertCls": "alert" if alert else "",
            }
        )
        self.events = self.events[-8:]

    # -- baseline / derived features ------------------------------------------
    def _settle(self) -> None:
        self.baseline = {}
        for f in _DERIVED:
            vals = [b[f] for b in self.baseline_buffer if not _is_missing(b.get(f))]
            if len(vals) >= 2:
                mean = float(np.mean(vals))
                std = float(np.std(vals, ddof=1))
            elif vals:
                mean, std = float(vals[0]), 0.0
            else:
                mean, std = 0.0, 0.0
            # Floor the std so degenerate near-zero calibration variance doesn't make
            # zbase hypersensitive (see _STD_FLOOR).
            std = max(std, _STD_FLOOR.get(f, 0.0))
            self.baseline[f] = (mean, std)
        self._log("Baseline calibrated")

    def _compute_derived(self, base: dict):
        zbase, delta = {}, {}
        for f in _DERIVED:
            v = base.get(f)
            if self.prev is not None and not _is_missing(v) and not _is_missing(self.prev.get(f)):
                delta[f] = v - self.prev[f]
            else:
                delta[f] = None
            if self.baseline is not None and not _is_missing(v):
                mean, std = self.baseline[f]
                zbase[f] = (v - mean) / std if std and std > 0 else None
            else:
                zbase[f] = None
        return zbase, delta

    @staticmethod
    def _raw_feature(feat: str, base: dict, zbase: dict, delta: dict):
        if feat.endswith("_zbase"):
            return zbase.get(feat[: -len("_zbase")])
        if feat.endswith("_delta"):
            return delta.get(feat[: -len("_delta")])
        return base.get(feat)

    def _vector(self, model_key: str, base: dict, zbase: dict, delta: dict) -> np.ndarray:
        norm = NORMS[model_key]
        zscore = norm["per_source_zscore"]
        impute = norm["impute_fill"]
        vec = []
        for feat in norm["feature_order"]:
            raw = self._raw_feature(feat, base, zbase, delta)
            if _is_missing(raw):
                vec.append(impute[feat])
                continue
            mean, std = zscore[f"{SOURCE_PREFIX}:{feat}"]
            if std and std > 0 and not math.isnan(std):
                vec.append((raw - mean) / std)
            else:
                vec.append(impute[feat])
        return np.array(vec, dtype=float).reshape(1, -1)

    # -- inference -------------------------------------------------------------
    @staticmethod
    def _contributions(model, norm, X):
        # LogisticRegression: contribution to the log-odds = coef_i * x_i (normalized).
        coef = np.asarray(model.coef_).ravel()
        x = X.ravel()
        pairs = sorted(
            zip(norm["feature_order"], coef * x), key=lambda p: abs(p[1]), reverse=True
        )
        return [{"feature": f, "contribution": round(float(c), 4)} for f, c in pairs[:5]]

    def classify_window(self, features: dict) -> dict:
        """Classify one window's mapped features. Uses Model A instead of the deployed
        model whenever heart_rate_bpm is missing (A does not depend on HR)."""
        model_key = "A" if _is_missing(features.get("heart_rate_bpm")) else DEPLOYED
        zbase, delta = self._compute_derived(features)
        X = self._vector(model_key, features, zbase, delta)
        model, norm = MODELS[model_key], NORMS[model_key]
        proba = float(model.predict_proba(X)[0, 1])
        threshold = norm["operating_threshold"]
        return {
            "score": round(proba * 100, 1),
            "threshold": int(round(threshold * 100)),
            "flagged": bool(proba >= threshold),
            "verdict": "Requires clinical review" if proba >= threshold else "Healthy",
            "method": "ml_model",
            "model_used": model_key,
            "contributions": self._contributions(model, norm, X),
            "_proba": proba,
        }

    def track_drift(self, probability: float) -> dict:
        """One-sided upper CUSUM on the probability stream, using manifest cusum params.
        The alert latches true until reset() -- it never auto-resets."""
        target, k, h = CUSUM_PARAMS["target"], CUSUM_PARAMS["k"], CUSUM_PARAMS["h"]
        self.cusum_s = max(0.0, self.cusum_s + (probability - target - k))
        if self.cusum_s > h and not self.alert_latched:
            self.alert_latched = True
            self._log("Drift alert fired", alert=True)
        return {"drift_score": round(self.cusum_s, 4), "alert": bool(self.alert_latched)}

    # -- per-tick entry point --------------------------------------------------
    def process(self, reading: dict) -> dict:
        base = map_live_to_features(reading)
        with self.lock:
            self.n_windows += 1
            anomaly = self.classify_window(base)
            drift = self.track_drift(anomaly["_proba"])

            # Update baseline buffer / prev AFTER classifying, so the current window uses
            # the prior baseline (first settle_windows windows calibrate it).
            if self.baseline is None:
                self.baseline_buffer.append(base)
                if len(self.baseline_buffer) >= self.settle_windows:
                    self._settle()
            self.prev = base

            return {
                "anomaly": {k: v for k, v in anomaly.items() if not k.startswith("_")},
                "drift": drift,
                "events": list(self.events),
                "model_used": anomaly["model_used"],
                "calibrating": self.baseline is None,
            }

    def mark_drift_started(self) -> None:
        with self.lock:
            if not self.drift_started:
                self.drift_started = True
                self._log("Drift mode started")


# --- module-global session + thin wrappers -----------------------------------
SESSION = SessionState()


def process(reading: dict) -> dict:
    return SESSION.process(reading)


def mark_drift_started() -> None:
    SESSION.mark_drift_started()


def reset() -> None:
    """Fresh session: new baseline buffer, CUSUM back to 0, alert un-latched."""
    global SESSION
    SESSION = SessionState()


def model_card() -> dict:
    """Deployed-model metrics + cusum params, for the health endpoint / README."""
    dep = MANIFEST[f"model_{DEPLOYED}"]
    return {
        "deployed": DEPLOYED,
        "auc": dep["auc"],
        "recall": dep["recall"],
        "precision": dep["precision"],
        "f1": dep["f1"],
        "cusum": CUSUM_PARAMS,
        "normal_class": MANIFEST["normal_class"],
        "flagged_class": MANIFEST["flagged_class"],
    }
