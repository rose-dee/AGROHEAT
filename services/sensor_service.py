"""Logika pembacaan sensor: validasi payload, penyimpanan, dan status koneksi.
Dipakai bersama oleh API (ESP32), input manual, dan simulasi."""
import json
import urllib.request
from datetime import datetime

import config
from database import db_manager as db
from services import alert_service

MAX_TEMP, MIN_TEMP = 125.0, -55.0   # rentang DS18B20
DISCONNECTED_VALUE = -127.0         # nilai yang dikembalikan library DS18B20 saat sensor lepas


def process_reading(batch_id, temperature_c, elapsed_seconds, sensor_status, data_source, timestamp=None):
    """Simpan satu pembacaan, update status batch jika target tercapai, lalu cek alarm."""
    batch = db.get_batch(batch_id)
    if batch is None:
        raise ValueError(f"Batch '{batch_id}' tidak ditemukan.")
    db.insert_reading(batch_id, timestamp or db.now_str(), temperature_c, elapsed_seconds,
                      sensor_status, data_source)
    if (batch["status"] == "Heating" and sensor_status == "connected"
            and temperature_c is not None and temperature_c >= batch["target_temperature"]):
        db.mark_target_reached(batch_id, elapsed_seconds)
    alert_service.evaluate_batch(batch_id)


def validate_payload(payload):
    """Validasi JSON dari ESP32. Return (data_bersih, daftar_error)."""
    errors = []
    if not isinstance(payload, dict):
        return None, ["Payload harus berupa objek JSON."]
    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id.strip():
        errors.append("batch_id wajib diisi (teks).")
    status = payload.get("sensor_status", "connected")
    if status not in config.SENSOR_STATUSES:
        errors.append(f"sensor_status harus salah satu dari {config.SENSOR_STATUSES}.")

    temp = payload.get("temperature_c")
    if temp is not None:
        if isinstance(temp, bool) or not isinstance(temp, (int, float)):
            errors.append("temperature_c harus berupa angka.")
        elif temp == DISCONNECTED_VALUE:
            errors.append("temperature_c = -127 menandakan sensor lepas; kirim sensor_status='disconnected' tanpa suhu.")
        elif not MIN_TEMP <= temp <= MAX_TEMP:
            errors.append(f"temperature_c di luar rentang DS18B20 ({MIN_TEMP} s.d. {MAX_TEMP}).")
    elif status == "connected":
        errors.append("temperature_c wajib ada jika sensor_status = 'connected'.")

    elapsed = payload.get("elapsed_seconds")
    if elapsed is not None and (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed < 0):
        errors.append("elapsed_seconds harus angka >= 0.")

    ts = payload.get("timestamp")
    ts_clean = None
    if ts is not None:
        try:
            parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)  # ke jam lokal laptop
            ts_clean = parsed.isoformat(timespec="seconds")
        except ValueError:
            errors.append("timestamp harus format ISO 8601.")
    if errors:
        return None, errors
    return {"batch_id": batch_id.strip(), "temperature_c": None if temp is None else float(temp),
            "elapsed_seconds": elapsed, "sensor_status": status, "timestamp": ts_clean}, []


def ingest_payload(payload):
    """Proses payload ESP32. Return (kode_http, respons_dict)."""
    data, errors = validate_payload(payload)
    if errors:
        return 400, {"ok": False, "errors": errors}
    batch = db.get_batch(data["batch_id"])
    if batch is None:
        return 404, {"ok": False, "errors": [f"Batch '{data['batch_id']}' tidak ditemukan."]}
    if batch["data_source"] != "real_sensor":
        return 409, {"ok": False, "errors": ["Batch ini bukan batch Real Sensor; data ditolak agar tidak tercampur."]}
    if batch["status"] not in ("Heating", "Target Reached"):
        return 409, {"ok": False, "errors": [f"Batch berstatus {batch['status']}; mulai batch di dashboard terlebih dahulu."]}
    elapsed = data["elapsed_seconds"]
    if elapsed is None:  # hitung dari waktu mulai batch bila ESP32 tidak mengirim
        elapsed = (datetime.now() - datetime.fromisoformat(batch["start_time"])).total_seconds()
    process_reading(data["batch_id"], data["temperature_c"], float(elapsed), data["sensor_status"],
                    "real_sensor", data["timestamp"])
    return 201, {"ok": True, "batch_id": data["batch_id"], "status": db.get_batch(data["batch_id"])["status"]}


# ------------------------------------------------------------- status koneksi
def api_online(port: int | None = None, timeout: float = 0.8) -> bool:
    """Cek apakah backend penerima data (api_service) benar-benar menjawab."""
    port = port or db.get_settings()["api_port"]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/health", timeout=timeout) as r:
            return json.loads(r.read().decode()).get("ok") is True
    except Exception:
        return False


def connection_status() -> dict:
    """Status ESP32 & sensor. ESP32 dianggap Online hanya jika ada data real_sensor yang baru masuk."""
    s = db.get_settings()
    last = db.latest_reading(source="real_sensor")
    out = {"api_online": api_online(), "esp32": "Belum pernah terhubung", "esp32_tone": "gray",
           "sensor": "Tidak diketahui", "sensor_tone": "gray", "last_seen": None}
    if last is None:
        return out
    age = (datetime.now() - datetime.fromisoformat(str(last["received_at"]))).total_seconds()
    out["last_seen"] = last["received_at"]
    out["age_seconds"] = age
    if age <= s["no_data_timeout_seconds"]:
        out["esp32"], out["esp32_tone"] = "Online", "green"
    else:
        out["esp32"], out["esp32_tone"] = f"Offline (data terakhir {age:.0f} dtk lalu)", "red"
    if last["sensor_status"] == "connected" and age <= s["no_data_timeout_seconds"]:
        out["sensor"], out["sensor_tone"] = "DS18B20 terbaca", "green"
    elif last["sensor_status"] != "connected":
        out["sensor"], out["sensor_tone"] = f"DS18B20 {last['sensor_status']}", "red"
    else:
        out["sensor"], out["sensor_tone"] = "Tidak ada data baru", "yellow"
    return out
