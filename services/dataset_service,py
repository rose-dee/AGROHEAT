"""Validasi, pembersihan, dan impor dataset CSV (tanpa Streamlit agar mudah diuji)."""
from datetime import datetime, timedelta

import pandas as pd

import config
from database import db_manager as db

REQUIRED = ["batch_id", "material_type", "volume_ml", "initial_temperature", "target_temperature",
            "heating_condition", "elapsed_seconds", "temperature_c"]
OPTIONAL = ["material", "timestamp", "sensor_status"]
NUMERIC = ["volume_ml", "initial_temperature", "target_temperature", "elapsed_seconds", "temperature_c"]


def template_csv() -> str:
    ex = pd.DataFrame([["AIR-001", "Air", "Air", 500, 28, 70, "Tanpa pengadukan", 0, 28.1],
                       ["AIR-001", "Air", "Air", 500, 28, 70, "Tanpa pengadukan", 5, 28.9]],
                      columns=["batch_id", "material", "material_type", "volume_ml", "initial_temperature",
                               "target_temperature", "heating_condition", "elapsed_seconds", "temperature_c"])
    return ex.to_csv(index=False)


def validate(df: pd.DataFrame) -> dict:
    """Return laporan: kolom hilang, nilai kosong, duplikat, nilai non-numerik, jenis bahan tak dikenal."""
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    report = {"rows": len(df), "cols": df.shape[1], "missing_cols": missing_cols,
              "nulls": {}, "duplicates": 0, "non_numeric": {}, "unknown_material": []}
    if missing_cols:
        return report
    report["nulls"] = {c: int(df[c].isna().sum()) for c in REQUIRED if df[c].isna().any()}
    report["duplicates"] = int(df.duplicated(subset=["batch_id", "elapsed_seconds"]).sum())
    for c in NUMERIC:
        bad = int(pd.to_numeric(df[c], errors="coerce").isna().sum() - df[c].isna().sum())
        if bad:
            report["non_numeric"][c] = bad
    report["unknown_material"] = sorted(set(df["material_type"].dropna()) - set(config.MATERIAL_TYPES))
    return report


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Ubah ke numerik, buang baris kosong/duplikat pada kolom wajib, urutkan per batch."""
    out = df.copy()
    for c in NUMERIC:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=REQUIRED).drop_duplicates(subset=["batch_id", "elapsed_seconds"])
    out["batch_id"] = out["batch_id"].astype(str).str.strip()
    return out.sort_values(["batch_id", "elapsed_seconds"]).reset_index(drop=True)


def import_dataset(df: pd.DataFrame, source: str) -> dict:
    """Simpan dataset bersih ke database dengan label sumber. Batch yang sudah ada dilewati."""
    if source not in config.DATA_SOURCES:
        raise ValueError("Sumber data tidak valid.")
    df = clean(df)
    imported, skipped = [], []
    for bid, g in df.groupby("batch_id"):
        if db.get_batch(bid):
            skipped.append(bid)
            continue
        first = g.iloc[0]
        has_ts = "timestamp" in g.columns and g["timestamp"].notna().all()
        start = (pd.to_datetime(g["timestamp"].iloc[0]).to_pydatetime().replace(tzinfo=None) if has_ts
                 else datetime.now().replace(microsecond=0))
        reached = g[g["temperature_c"] >= first["target_temperature"]]
        db.create_batch({
            "batch_id": bid, "material": first.get("material", first["material_type"]) if "material" in g.columns
            and pd.notna(first.get("material")) else first["material_type"],
            "material_type": first["material_type"], "volume_ml": float(first["volume_ml"]),
            "initial_temperature": float(first["initial_temperature"]),
            "target_temperature": float(first["target_temperature"]),
            "heating_condition": first["heating_condition"], "data_source": source, "status": "Completed",
            "start_time": start.isoformat(timespec="seconds"),
            "end_time": (start + timedelta(seconds=float(g["elapsed_seconds"].max()))).isoformat(timespec="seconds"),
            "target_reached_seconds": None if reached.empty else float(reached["elapsed_seconds"].iloc[0]),
            "actual_duration_seconds": float(g["elapsed_seconds"].max()),
            "notes": f"Diimpor dari CSV ({config.DATA_SOURCES[source]})."})
        rows = []
        for _, r in g.iterrows():
            ts = (pd.to_datetime(r["timestamp"]).to_pydatetime().replace(tzinfo=None) if has_ts
                  else start + timedelta(seconds=float(r["elapsed_seconds"]))).isoformat(timespec="seconds")
            status = r["sensor_status"] if "sensor_status" in g.columns and pd.notna(r.get("sensor_status")) else "connected"
            rows.append((bid, ts, float(r["temperature_c"]), float(r["elapsed_seconds"]), status, source, ts))
        db.insert_readings_bulk(rows)
        imported.append(bid)
    return {"imported": imported, "skipped": skipped}
