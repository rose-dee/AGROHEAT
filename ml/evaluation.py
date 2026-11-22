"""Metrik evaluasi regresi."""
import numpy as np
import pandas as pd


def regression_metrics(y_true, y_pred) -> dict:
    err = np.asarray(y_pred, float) - np.asarray(y_true, float)
    return {"mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2)))}


def per_batch_mae(test_predictions: pd.DataFrame, pred_col: str) -> pd.DataFrame:
    g = test_predictions.assign(abs_err=(test_predictions[pred_col] - test_predictions["actual"]).abs())
    return g.groupby("batch_id")["abs_err"].mean().rename("mae_seconds").reset_index()
