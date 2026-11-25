"""Alarm berbasis aturan. Hanya memantau suhu & kelancaran data -
BUKAN penilaian keamanan pangan atau keberhasilan pasteurisasi."""
from datetime import datetime

import pandas as pd

from database import db_manager as db

# Jenis alarm
OVER_TEMP = "Suhu melebihi batas"
SLOW_HEATING = "Pemanasan terlalu lambat"
SENSOR_MISSING = "Sensor tidak terdeteksi"
NO_DATA = "Data sensor tidak masuk"
TARGET_REACHED = "Batch mencapai suhu target"

AUTO_RESOLVE = [SLOW_HEATING, SENSOR_MISSING, NO_DATA]  # hilang otomatis jika kondisi pulih


def _rate_c_per_min(df: pd.DataFrame, window_s: float = 120.0):
    """Laju kenaikan suhu (°C/menit) pada jendela waktu terakhir; None jika data kurang."""
    d = df.dropna(subset=["temperature_c"])
    if len(d) < 2:
        return None
    last = d.iloc[-1]
    past = d[d["elapsed_seconds"] <= last["elapsed_seconds"] - window_s]
    if past.empty:
        return None  # belum cukup lama untuk dinilai
    ref = past.iloc[-1]
    dt = last["elapsed_seconds"] - ref["elapsed_seconds"]
    return (last["temperature_c"] - ref["temperature_c"]) / dt * 60.0


def evaluate_batch(batch_id: str) -> None:
    """Evaluasi semua aturan untuk satu batch. Aman dipanggil berulang."""
    b = db.get_batch(batch_id)
    if b is None:
        return
    s = db.get_settings()
    df = db.get_readings(batch_id)
    last = None if df.empty else df.iloc[-1]
    running = b["status"] == "Heating"

    if last is not None:
        temp = last["temperature_c"]
        # 1) Suhu melebihi batas
        if pd.notna(temp) and temp > s["max_temperature"]:
            db.add_alert(batch_id, OVER_TEMP, "Critical",
                         f"Suhu {temp:.1f} °C melebihi batas {s['max_temperature']:.1f} °C.")
        # 2) Sensor tidak terdeteksi
        if last["sensor_status"] != "connected" or pd.isna(temp):
            db.add_alert(batch_id, SENSOR_MISSING, "Critical",
                         f"Status sensor: {last['sensor_status']}.")
        else:
            db.resolve_alerts(batch_id, [SENSOR_MISSING])
        # 3) Pemanasan lambat
        if running and pd.notna(temp) and temp < b["target_temperature"]:
            rate = _rate_c_per_min(df)
            if rate is not None and rate < s["slow_heating_c_per_min"]:
                db.add_alert(batch_id, SLOW_HEATING, "Warning",
                             f"Laju kenaikan {rate:.2f} °C/menit di bawah batas "
                             f"{s['slow_heating_c_per_min']:.2f} °C/menit.")
            elif rate is not None:
                db.resolve_alerts(batch_id, [SLOW_HEATING])

    # 4) Data tidak masuk (tidak dievaluasi untuk data simulasi/manual)
    if running and b["data_source"] == "real_sensor":
        ref_time = last["received_at"] if last is not None else b["start_time"]
        if ref_time:
            gap = (datetime.now() - datetime.fromisoformat(str(ref_time))).total_seconds()
            if gap > s["no_data_timeout_seconds"]:
                db.add_alert(batch_id, NO_DATA, "Warning",
                             f"Tidak ada data selama {gap:.0f} detik "
                             f"(batas {s['no_data_timeout_seconds']} detik).")
            else:
                db.resolve_alerts(batch_id, [NO_DATA])

    # 5) Target tercapai
    if b["status"] == "Target Reached":
        db.add_alert(batch_id, TARGET_REACHED, "Info",
                     f"Batch mencapai suhu target {b['target_temperature']:.1f} °C "
                     f"pada detik ke-{b['target_reached_seconds']:.0f}.")
