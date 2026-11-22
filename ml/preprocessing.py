"""Pembentukan fitur & label ML.

Label (remaining_seconds) = waktu aktual saat suhu PERTAMA KALI >= suhu target
dikurangi elapsed pembacaan tersebut. Label hanya berasal dari data pengukuran,
tidak pernah dari prediksi model. Batch yang tidak pernah mencapai target dibuang.
Setiap fitur hanya memakai data masa lalu/sekarang (tidak ada kebocoran dari masa depan).
"""
import numpy as np
import pandas as pd

NUMERIC_FEATURES = ["current_temperature", "initial_temperature", "target_temperature",
                    "elapsed_seconds", "temp_rise_rate_c_per_min", "volume_ml"]
CATEGORICAL_FEATURES = ["material_type", "heating_condition"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "remaining_seconds"
RATE_WINDOW_SECONDS = 60.0


def compute_rise_rate(elapsed: np.ndarray, temp: np.ndarray, window: float = RATE_WINDOW_SECONDS) -> np.ndarray:
    """Laju kenaikan suhu (°C/menit) dari jendela `window` detik ke belakang saja."""
    rate = np.zeros(len(elapsed))
    idx = np.searchsorted(elapsed, elapsed - window, side="left")
    for i in range(len(elapsed)):
        j = idx[i]
        dt = elapsed[i] - elapsed[j]
        if dt > 0:
            rate[i] = (temp[i] - temp[j]) / dt * 60.0
    return rate


def build_training_table(readings: pd.DataFrame) -> pd.DataFrame:
    """Ubah tabel pembacaan (hasil db.get_all_readings) menjadi tabel fitur + label."""
    cols = ["batch_id", "data_source"] + FEATURES + [TARGET]
    if readings.empty:
        return pd.DataFrame(columns=cols)
    df = readings[(readings["sensor_status"] == "connected")].dropna(subset=["temperature_c"])
    parts = []
    for batch_id, g in df.groupby("batch_id"):
        g = g.sort_values("elapsed_seconds").reset_index(drop=True)
        reached = g[g["temperature_c"] >= g["target_temperature"].iloc[0]]
        if reached.empty:
            continue  # tidak ada label aktual -> batch tidak dipakai
        t_reach = float(reached["elapsed_seconds"].iloc[0])
        e = g["elapsed_seconds"].to_numpy(float)
        t = g["temperature_c"].to_numpy(float)
        feat = pd.DataFrame({
            "batch_id": batch_id,
            "data_source": g["data_source"],
            "current_temperature": t,
            "initial_temperature": g["initial_temperature"],
            "target_temperature": g["target_temperature"],
            "elapsed_seconds": e,
            "temp_rise_rate_c_per_min": compute_rise_rate(e, t),
            "volume_ml": g["volume_ml"],
            "material_type": g["material_type"],
            "heating_condition": g["heating_condition"],
            TARGET: t_reach - e,
        })
        parts.append(feat[feat["elapsed_seconds"] < t_reach])
    return pd.concat(parts, ignore_index=True)[cols] if parts else pd.DataFrame(columns=cols)


def build_feature_row(batch: dict, readings: pd.DataFrame):
    """Fitur untuk pembacaan terakhir sebuah batch (inferensi). None jika belum ada data valid."""
    d = readings[readings["sensor_status"] == "connected"].dropna(subset=["temperature_c"])
    d = d.sort_values("elapsed_seconds")
    if d.empty:
        return None
    e = d["elapsed_seconds"].to_numpy(float)
    t = d["temperature_c"].to_numpy(float)
    return pd.DataFrame([{
        "current_temperature": t[-1],
        "initial_temperature": batch["initial_temperature"],
        "target_temperature": batch["target_temperature"],
        "elapsed_seconds": e[-1],
        "temp_rise_rate_c_per_min": compute_rise_rate(e, t)[-1],
        "volume_ml": batch["volume_ml"],
        "material_type": batch["material_type"],
        "heating_condition": batch["heating_condition"],
    }])[FEATURES]
