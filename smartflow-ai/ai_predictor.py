"""Local ML demonstration trained exclusively on reproducible synthetic runs."""
from functools import lru_cache

import numpy as np
import pandas as pd

OPERATIONS = ("Torna", "Freze", "Delik", "Montaj", "Paketleme")
PROCESS = "Süre (saat)"
SETUP = "Hazırlık (saat)"


def features(jobs):
    duration = pd.to_numeric(jobs[PROCESS], errors="raise").to_numpy(dtype=float)
    setup = pd.to_numeric(jobs[SETUP], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(duration).all() or not np.isfinite(setup).all():
        raise ValueError("Durations must be finite")
    if ((duration < .5) | (duration > 48) | (setup < 0) | (setup > 12)).any():
        raise ValueError("Demo supports processing 0.5–48 h and setup 0–12 h")
    if not jobs["Operasyon"].isin(OPERATIONS).all():
        raise ValueError("Unsupported operation")
    return np.column_stack([np.ones(len(jobs)), duration / 48, (duration / 48) ** 2, setup / 12, *[
        jobs["Operasyon"].eq(operation).to_numpy(dtype=float)
        for operation in OPERATIONS
    ]])


@lru_cache(maxsize=1)
def train_demo_model():
    rng = np.random.default_rng(42)
    count = 2400
    operation = rng.integers(0, len(OPERATIONS), count)
    duration = rng.uniform(.5, 48, count)
    setup = rng.uniform(0, 12, count)
    jobs = pd.DataFrame({"Operasyon": np.array(OPERATIONS)[operation], PROCESS: duration, SETUP: setup})
    # Invented simulator assumptions, not measurements from a factory.
    ratio = (np.array([1.14, 1.25, 1.08, 1.18, 1.04])[operation]
             + .012 * setup + .06 * (duration > 20)
             + rng.normal(0, .035, count))
    actual = duration * ratio
    shuffled = rng.permutation(count)
    train, test = shuffled[:1800], shuffled[1800:]
    x = features(jobs)
    # Ordinary least squares learns coefficients from the training subset only.
    coefficients = np.linalg.lstsq(x[train], ratio[train], rcond=None)[0]
    predicted = (x[test] @ coefficients) * duration[test]
    report = {
        "training_rows": len(train), "test_rows": len(test),
        "model_mae": float(np.abs(actual[test] - predicted).mean()),
        "baseline_mae": float(np.abs(actual[test] - duration[test]).mean()),
    }
    return coefficients, report


def predict_hours(jobs):
    x = features(jobs)
    if len(jobs) == 0:
        return np.array([], dtype=float)
    coefficients, _ = train_demo_model()
    return (x @ coefficients) * jobs[PROCESS].to_numpy(dtype=float)
