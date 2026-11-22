"""Semua akses database SQLite ada di file ini (satu pintu)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

import config


def now_str() -> str:
    """Waktu lokal laptop, format ISO tanpa zona (konsisten di seluruh aplikasi)."""
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def get_conn():
    """Koneksi dengan commit/rollback otomatis."""
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Buat database + tabel jika belum ada, lalu isi pengaturan default."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as c:
        c.execute("PRAGMA journal_mode = WAL")  # Streamlit & API boleh akses bersamaan
        c.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))
        for k, v in config.DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO system_settings(key,value,updated_at) VALUES (?,?,?)",
                      (k, str(v), now_str()))


def query_df(sql: str, params=()) -> pd.DataFrame:
    with get_conn() as c:
        return pd.read_sql_query(sql, c, params=params)


# ---------------------------------------------------------------- settings
def get_settings() -> dict:
    rows = query_df("SELECT key, value FROM system_settings")
    stored = dict(zip(rows["key"], rows["value"]))
    out = {}
    for k, default in config.DEFAULT_SETTINGS.items():
        try:
            out[k] = type(default)(float(stored[k])) if k in stored else default
        except (ValueError, TypeError):
            out[k] = default
    return out


def set_settings(values: dict) -> None:
    with get_conn() as c:
        for k, v in values.items():
            c.execute("INSERT INTO system_settings(key,value,updated_at) VALUES (?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                      (k, str(v), now_str()))


# ----------------------------------------------------------------- batches
_BATCH_COLS = ["batch_id", "material", "material_type", "volume_ml", "initial_temperature",
               "target_temperature", "heating_condition", "data_source", "start_time", "end_time",
               "target_reached_seconds", "actual_duration_seconds", "status", "notes", "created_at"]


def create_batch(data: dict) -> None:
    row = {c: data.get(c) for c in _BATCH_COLS}
    row["status"] = row["status"] or "Pending"
    row["notes"] = row["notes"] or ""
    row["created_at"] = row["created_at"] or now_str()
    try:
        with get_conn() as c:
            c.execute(f"INSERT INTO batches ({','.join(_BATCH_COLS)}) "
                      f"VALUES ({','.join('?' * len(_BATCH_COLS))})", [row[k] for k in _BATCH_COLS])
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e) or "PRIMARY" in str(e):
            raise ValueError(f"Batch ID '{row['batch_id']}' sudah digunakan.") from e
        raise


def get_batch(batch_id: str):
    df = query_df("SELECT * FROM batches WHERE batch_id = ?", (batch_id,))
    return None if df.empty else df.iloc[0].to_dict()


def list_batches(status: str | None = None) -> pd.DataFrame:
    if status:
        return query_df("SELECT * FROM batches WHERE status=? ORDER BY created_at DESC", (status,))
    return query_df("SELECT * FROM batches ORDER BY created_at DESC")


def get_active_batch():
    """Batch yang sedang berjalan (Heating atau Target Reached tapi belum diakhiri)."""
    df = query_df("SELECT * FROM batches WHERE status IN ('Heating','Target Reached') "
                  "ORDER BY start_time DESC LIMIT 1")
    return None if df.empty else df.iloc[0].to_dict()


def start_batch(batch_id: str) -> None:
    b = get_batch(batch_id)
    if b is None:
        raise ValueError("Batch tidak ditemukan.")
    if b["status"] != "Pending":
        raise ValueError(f"Batch berstatus {b['status']}; hanya batch Pending yang bisa dimulai.")
    if get_active_batch() is not None:
        raise ValueError("Masih ada batch aktif. Akhiri batch tersebut sebelum memulai yang baru.")
    with get_conn() as c:
        c.execute("UPDATE batches SET status='Heating', start_time=? WHERE batch_id=?",
                  (now_str(), batch_id))


def mark_target_reached(batch_id: str, elapsed_seconds: float) -> None:
    with get_conn() as c:
        c.execute("UPDATE batches SET status='Target Reached', target_reached_seconds=? "
                  "WHERE batch_id=? AND status='Heating'", (elapsed_seconds, batch_id))


def end_batch(batch_id: str, status: str = "Completed") -> None:
    """Akhiri sesi. Durasi aktual = elapsed pembacaan terakhir (bukan jam dinding)."""
    if status not in ("Completed", "Cancelled"):
        raise ValueError("Status akhir harus Completed atau Cancelled.")
    last = query_df("SELECT MAX(elapsed_seconds) AS m FROM readings WHERE batch_id=?", (batch_id,))
    duration = last["m"].iloc[0]
    duration = None if pd.isna(duration) else float(duration)
    with get_conn() as c:
        c.execute("UPDATE batches SET status=?, end_time=?, actual_duration_seconds=? WHERE batch_id=?",
                  (status, now_str(), duration, batch_id))


def delete_batches_by_source(source: str) -> int:
    with get_conn() as c:
        cur = c.execute("DELETE FROM batches WHERE data_source=?", (source,))
        return cur.rowcount


# ---------------------------------------------------------------- readings
def insert_reading(batch_id, timestamp, temperature_c, elapsed_seconds, sensor_status, data_source):
    with get_conn() as c:
        c.execute("INSERT INTO readings(batch_id,timestamp,temperature_c,elapsed_seconds,"
                  "sensor_status,data_source,received_at) VALUES (?,?,?,?,?,?,?)",
                  (batch_id, timestamp, temperature_c, elapsed_seconds, sensor_status,
                   data_source, now_str()))


def insert_readings_bulk(rows: list) -> None:
    """rows: (batch_id,timestamp,temperature_c,elapsed_seconds,sensor_status,data_source,received_at)"""
    with get_conn() as c:
        c.executemany("INSERT INTO readings(batch_id,timestamp,temperature_c,elapsed_seconds,"
                      "sensor_status,data_source,received_at) VALUES (?,?,?,?,?,?,?)", rows)


def get_readings(batch_id: str) -> pd.DataFrame:
    return query_df("SELECT * FROM readings WHERE batch_id=? ORDER BY elapsed_seconds, id", (batch_id,))


def get_all_readings() -> pd.DataFrame:
    """Semua pembacaan digabung dengan metadata batch (dipakai History, ML, Analytics)."""
    return query_df("""
        SELECT r.id, r.timestamp, r.batch_id, b.material, b.material_type, b.volume_ml,
               b.initial_temperature, b.target_temperature, b.heating_condition,
               r.temperature_c, r.elapsed_seconds, r.sensor_status, r.data_source, r.received_at
        FROM readings r JOIN batches b ON b.batch_id = r.batch_id
        ORDER BY r.timestamp, r.id""")


def latest_reading(batch_id=None, source=None):
    sql, params, where = "SELECT * FROM readings", [], []
    if batch_id:
        where.append("batch_id=?"); params.append(batch_id)
    if source:
        where.append("data_source=?"); params.append(source)
    if where:
        sql += " WHERE " + " AND ".join(where)
    df = query_df(sql + " ORDER BY id DESC LIMIT 1", tuple(params))
    return None if df.empty else df.iloc[0].to_dict()


# ------------------------------------------------------------------ alerts
def add_alert(batch_id, alert_type, priority, message) -> bool:
    """Tambah alarm; dilewati jika alarm sejenis untuk batch ini masih Active."""
    dup = query_df("SELECT 1 FROM alerts WHERE batch_id IS ? AND alert_type=? AND status='Active'",
                   (batch_id, alert_type))
    if not dup.empty:
        return False
    with get_conn() as c:
        c.execute("INSERT INTO alerts(batch_id,timestamp,alert_type,priority,message) VALUES (?,?,?,?,?)",
                  (batch_id, now_str(), alert_type, priority, message))
    return True


def resolve_alerts(batch_id, alert_types: list) -> None:
    with get_conn() as c:
        for t in alert_types:
            c.execute("UPDATE alerts SET status='Resolved' WHERE batch_id=? AND alert_type=? "
                      "AND status='Active'", (batch_id, t))


def list_alerts(status: str | None = None) -> pd.DataFrame:
    sql = "SELECT * FROM alerts"
    params = ()
    if status:
        sql += " WHERE status=?"; params = (status,)
    return query_df(sql + " ORDER BY id DESC", params)


def set_alert_status(alert_id: int, status: str) -> None:
    with get_conn() as c:
        c.execute("UPDATE alerts SET status=? WHERE id=?", (status, int(alert_id)))


# ------------------------------------------------------------- experiments
def add_experiment(model_name, dataset_version, train_batch_count, test_batch_count, mae, rmse, notes=""):
    with get_conn() as c:
        c.execute("INSERT INTO model_experiments(model_name,training_date,dataset_version,"
                  "train_batch_count,test_batch_count,mae,rmse,notes) VALUES (?,?,?,?,?,?,?,?)",
                  (model_name, now_str(), dataset_version, train_batch_count, test_batch_count,
                   mae, rmse, notes))


def list_experiments() -> pd.DataFrame:
    return query_df("SELECT * FROM model_experiments ORDER BY experiment_id DESC")


def table_counts() -> dict:
    out = {}
    for t in ["batches", "readings", "alerts", "model_experiments", "system_settings"]:
        out[t] = int(query_df(f"SELECT COUNT(*) AS n FROM {t}")["n"].iloc[0])
    return out


def delete_batch(batch_id: str) -> None:
    """Hapus batch beserta pembacaan & alarmnya (ON DELETE CASCADE)."""
    with get_conn() as c:
        c.execute("DELETE FROM batches WHERE batch_id=?", (batch_id,))
