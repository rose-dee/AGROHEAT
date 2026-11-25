"""Prediksi ML dan estimasi heuristik (dua hal berbeda, selalu diberi label terpisah)."""
import json

import joblib
import numpy as np
import pandas as pd

import config
from ml import preprocessing as pp
from ml.train_model import META_FILE, MODEL_FILES, TEST_PRED_FILE


def load_meta():
    p = config.MODEL_DIR / META_FILE
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def load_test_predictions():
    p = config.MODEL_DIR / TEST_PRED_FILE
    return pd.read_csv(p) if p.exists() else None


def model_ready() -> bool:
    meta = load_meta()
    return bool(meta) and (config.MODEL_DIR / MODEL_FILES[meta["best_model"]]).exists()


def predict_remaining(batch: dict, readings: pd.DataFrame):
    """Prediksi ML sisa detik menuju target. None jika model belum terlatih / data belum ada."""
    meta = load_meta()
    if not meta:
        return None
    path = config.MODEL_DIR / MODEL_FILES[meta["best_model"]]
    if not path.exists():
        return None
    row = pp.build_feature_row(batch, readings)
    if row is None:
        return None
    try:
        value = float(max(0.0, joblib.load(path).predict(row)[0]))
    except Exception:
        return None
    return {"seconds": value, "model": meta["best_model"]}


def heuristic_remaining(batch: dict, readings: pd.DataFrame):
    """Estimasi sederhana: sisa selisih suhu / laju kenaikan 60 detik terakhir. BUKAN Machine Learning."""
    row = pp.build_feature_row(batch, readings)
    if row is None:
        return None
    rate = float(row["temp_rise_rate_c_per_min"].iloc[0])
    gap = batch["target_temperature"] - float(row["current_temperature"].iloc[0])
    if gap <= 0 or rate <= 0.01 or np.isnan(rate):
        return None
    return gap / rate * 60.0
