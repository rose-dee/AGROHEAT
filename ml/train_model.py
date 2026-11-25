"""Pelatihan & evaluasi: Linear Regression (baseline) vs Random Forest.
Pembagian train/test dilakukan PER BATCH agar tidak ada kebocoran antarbaris."""
import hashlib
import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

import config
from database import db_manager as db
from ml import preprocessing as pp
from ml.evaluation import regression_metrics

MODEL_FILES = {"Linear Regression": "linear_regression.joblib", "Random Forest": "random_forest.joblib"}
META_FILE = "model_meta.json"
TEST_PRED_FILE = "test_predictions.csv"


def check_readiness(table: pd.DataFrame) -> tuple[bool, str]:
    """Apakah data cukup untuk dilatih? Jika tidak, jangan latih (dan jangan tampilkan metrik)."""
    n_batches = table["batch_id"].nunique() if not table.empty else 0
    n_rows = len(table)
    if n_batches < config.MIN_TOTAL_BATCHES:
        return False, (f"Model belum siap dilatih: baru {n_batches} batch berlabel, "
                       f"minimal {config.MIN_TOTAL_BATCHES} (batch yang mencapai suhu target).")
    if n_rows < config.MIN_TOTAL_ROWS:
        return False, f"Model belum siap dilatih: baru {n_rows} baris, minimal {config.MIN_TOTAL_ROWS}."
    return True, f"Data cukup: {n_batches} batch, {n_rows} baris berlabel."


def split_by_batch(batch_ids, test_fraction=config.TEST_FRACTION, seed=config.RANDOM_STATE):
    ids = np.array(sorted(batch_ids))
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    n_test = max(1, int(round(len(ids) * test_fraction)))
    n_test = min(n_test, len(ids) - 3)  # sisakan minimal 3 batch latih
    return sorted(ids[n_test:]), sorted(ids[:n_test])



def _make_models() -> dict:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    cat = ("cat", OneHotEncoder(handle_unknown="ignore"), pp.CATEGORICAL_FEATURES)
    lr = Pipeline([("prep", ColumnTransformer([("num", StandardScaler(), pp.NUMERIC_FEATURES), cat])),
                   ("model", LinearRegression())])
    rf = Pipeline([("prep", ColumnTransformer([("num", "passthrough", pp.NUMERIC_FEATURES), cat])),
                   ("model", RandomForestRegressor(n_estimators=200, min_samples_leaf=3,
                                                   random_state=config.RANDOM_STATE, n_jobs=-1))])
    return {"Linear Regression": lr, "Random Forest": rf}



def train_and_evaluate(table: pd.DataFrame, notes: str = "") -> dict:
    ok, msg = check_readiness(table)
    if not ok:
        raise ValueError(msg)
    train_ids, test_ids = split_by_batch(table["batch_id"].unique())
    train = table[table["batch_id"].isin(train_ids)]
    test = table[table["batch_id"].isin(test_ids)]
    assert set(train_ids).isdisjoint(test_ids)  # jaminan tidak ada batch yang sama di train & test

    sources = sorted(table["data_source"].unique())
    version = "ds-" + hashlib.sha1("|".join(sorted(table["batch_id"].unique())).encode()).hexdigest()[:8]
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)

    preds = pd.DataFrame({"batch_id": test["batch_id"].values,
                          "elapsed_seconds": test["elapsed_seconds"].values,
                          "actual": test[pp.TARGET].values})
    results = {}
    for name, model in _make_models().items():
        model.fit(train[pp.FEATURES], train[pp.TARGET])
        pred = np.clip(model.predict(test[pp.FEATURES]), 0, None)
        results[name] = regression_metrics(test[pp.TARGET], pred)
        col = "pred_lr" if name == "Linear Regression" else "pred_rf"
        preds[col] = pred
        joblib.dump(model, config.MODEL_DIR / MODEL_FILES[name])
        db.add_experiment(name, version, len(train_ids), len(test_ids),
                          results[name]["mae"], results[name]["rmse"],
                          f"sumber data: {', '.join(sources)}. {notes}".strip())

    best = min(results, key=lambda k: results[k]["rmse"])
    meta = {"trained_at": datetime.now().isoformat(timespec="seconds"), "dataset_version": version,
            "sources": sources, "includes_simulation": "simulation" in sources,
            "train_batches": train_ids, "test_batches": test_ids,
            "n_train_rows": int(len(train)), "n_test_rows": int(len(test)),
            "features": pp.FEATURES, "results": results, "best_model": best}
    (config.MODEL_DIR / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    preds.to_csv(config.MODEL_DIR / TEST_PRED_FILE, index=False)
    return meta
