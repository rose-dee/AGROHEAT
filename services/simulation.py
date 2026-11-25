"""Data SIMULASI untuk mode demo. Semua data yang dihasilkan diberi data_source='simulation'.
Ini model pemanasan sederhana (Newton) - BUKAN data sensor nyata."""
from datetime import datetime, timedelta

import numpy as np

from database import db_manager as db
from services import sensor_service


def _tau(volume_ml, condition, material_type, factor=1.0):
    tau = 0.9 * volume_ml * factor
    if condition == "Dengan pengadukan":
        tau *= 0.85
    if material_type != "Air":
        tau *= 1.04
    return tau


def model_temperature(batch: dict, elapsed: float, factor: float = 1.0) -> float:
    t_inf = batch["target_temperature"] + 30.0  # suhu "asimtotik" pemanas simulasi
    tau = _tau(batch["volume_ml"], batch["heating_condition"], batch["material_type"], factor)
    t0 = batch["initial_temperature"]
    return t_inf - (t_inf - t0) * float(np.exp(-elapsed / tau))


def simulate_tick(batch_id: str, multiplier: int = 1) -> None:
    """Tambah satu pembacaan simulasi. Waktu simulasi maju sebesar interval x multiplier."""
    b = db.get_batch(batch_id)
    s = db.get_settings()
    last = db.latest_reading(batch_id)
    elapsed = 0.0 if last is None else float(last["elapsed_seconds"]) + s["reading_interval_seconds"] * multiplier
    temp = model_temperature(b, elapsed) + float(np.random.default_rng().normal(0, 0.12))
    ts = (datetime.fromisoformat(b["start_time"]) + timedelta(seconds=elapsed)).isoformat(timespec="seconds")
    sensor_service.process_reading(batch_id, round(temp, 2), elapsed, "connected", "simulation", ts)


def seed_demo_dataset(n_batches: int = 8, seed: int = 42) -> int:
    """Buat beberapa batch simulasi selesai (berlabel Simulated Data). Return jumlah batch baru."""
    rng = np.random.default_rng(seed)
    materials = ["Air", "Sari Lemon", "Sari Buah Lainnya"]
    volumes = [250, 300, 400, 500, 600, 750, 350, 450]
    targets = [60, 65, 70, 75, 80, 70, 65, 75]
    created = 0
    for i in range(n_batches):
        batch_id = f"SIM-DEMO-{i + 1:03d}"
        if db.get_batch(batch_id):
            continue
        mtype = materials[i % 3]
        b = {"batch_id": batch_id, "material": "Air" if mtype == "Air" else mtype,
             "material_type": mtype, "volume_ml": volumes[i % len(volumes)],
             "initial_temperature": float(rng.uniform(25, 31)),
             "target_temperature": float(targets[i % len(targets)]),
             "heating_condition": "Dengan pengadukan" if i % 2 else "Tanpa pengadukan",
             "data_source": "simulation", "notes": "Data SIMULASI untuk demo - bukan data sensor nyata."}
        start = datetime.now().replace(microsecond=0) - timedelta(days=n_batches - i, hours=1)
        factor = float(rng.uniform(0.92, 1.08))
        rows, t, reached = [], 0.0, None
        while True:
            temp = model_temperature(b, t, factor) + float(rng.normal(0, 0.12))
            ts = (start + timedelta(seconds=t)).isoformat(timespec="seconds")
            rows.append((batch_id, ts, round(temp, 2), t, "connected", "simulation", ts))
            if reached is None and temp >= b["target_temperature"]:
                reached = t
            if reached is not None and t >= reached + 30:
                break
            t += 5.0
        b.update({"status": "Completed", "start_time": start.isoformat(timespec="seconds"),
                  "end_time": (start + timedelta(seconds=t)).isoformat(timespec="seconds"),
                  "target_reached_seconds": reached, "actual_duration_seconds": t})
        db.create_batch(b)
        db.insert_readings_bulk(rows)
        created += 1
    return created

