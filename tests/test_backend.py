"""Uji backend (tanpa Streamlit): database, simulasi, ML, API ESP32, alarm.
Jalankan:  python tests/test_backend.py
Memakai database & folder model SEMENTARA, data asli tidak tersentuh."""
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

tmp = Path(tempfile.mkdtemp())
config.DB_PATH = tmp / "test.db"
config.MODEL_DIR = tmp / "models"

from database import db_manager as db
from ml import preprocessing as pp, train_model, predict
from services import api_service, simulation, sensor_service


def post(port, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/readings", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    db.init_db()
    assert db.table_counts()["system_settings"] == len(config.DEFAULT_SETTINGS)

    # --- ML belum siap saat data kosong: tidak boleh ada metrik palsu
    empty = pp.build_training_table(db.get_all_readings())
    ok, msg = train_model.check_readiness(empty)
    assert not ok, msg
    assert predict.load_meta() is None and not predict.model_ready()
    print("OK  data kosong -> model belum siap:", msg)

    # --- seed simulasi + training per-batch
    assert simulation.seed_demo_dataset(8) == 8
    assert simulation.seed_demo_dataset(8) == 0  # idempoten
    table = pp.build_training_table(db.get_all_readings())
    assert (table["remaining_seconds"] > 0).all() and set(table["data_source"]) == {"simulation"}
    meta = train_model.train_and_evaluate(table)
    assert set(meta["train_batches"]).isdisjoint(meta["test_batches"])
    print("OK  train/test per batch:", len(meta["train_batches"]), "/", len(meta["test_batches"]))
    for name, m in meta["results"].items():
        print(f"    {name}: MAE={m['mae']:.1f}s RMSE={m['rmse']:.1f}s")
    assert meta["includes_simulation"] and len(db.list_experiments()) == 2

    # --- prediksi di batch real_sensor (bukan simulasi) tetap terpisah
    db.create_batch({"batch_id": "SOY-001", "material": "Sari Kedelai", "material_type": "Sari Kedelai",
                     "volume_ml": 500, "initial_temperature": 28, "target_temperature": 70,
                     "heating_condition": "Tanpa pengadukan", "data_source": "real_sensor"})
    code, body = post_through_server({"batch_id": "SOY-001", "temperature_c": 30.0})
    assert code == 409, (code, body)            # batch masih Pending -> ditolak
    db.start_batch("SOY-001")
    code, body = post_through_server({"batch_id": "SOY-001", "temperature_c": 30.0, "elapsed_seconds": 5,
                                      "timestamp": "2026-11-18T10:00:00+07:00", "sensor_status": "connected"})
    assert code == 201, (code, body)
    assert post_through_server({"batch_id": "SOY-001", "temperature_c": -127})[0] == 400
    assert post_through_server({"batch_id": "NOPE", "temperature_c": 30})[0] == 404
    assert post_through_server({"temperature_c": 30})[0] == 400
    assert post_through_server({"batch_id": "SOY-001", "temperature_c": 31, "sensor_status": "bogus"})[0] == 400
    print("OK  validasi payload & penolakan batch tidak valid")

    # --- ML vs heuristik pada data real (hanya 2 titik: heuristik butuh laju)
    for t, T in [(65, 40), (125, 50)]:
        post_through_server({"batch_id": "SOY-001", "temperature_c": T, "elapsed_seconds": t})
    b, rd = db.get_batch("SOY-001"), db.get_readings("SOY-001")
    p, h = predict.predict_remaining(b, rd), predict.heuristic_remaining(b, rd)
    print("OK  prediksi ML:", None if p is None else round(p["seconds"]), "dtk | heuristik:", None if h is None else round(h), "dtk")

    # --- sensor lepas -> alarm Critical; target tercapai -> status & alarm
    post_through_server({"batch_id": "SOY-001", "sensor_status": "disconnected", "elapsed_seconds": 130})
    assert "Sensor tidak terdeteksi" in set(db.list_alerts("Active")["alert_type"])
    post_through_server({"batch_id": "SOY-001", "temperature_c": 71.0, "elapsed_seconds": 400})
    assert db.get_batch("LEMON-001")["status"] == "Target Reached"
    assert "Batch mencapai suhu target" in set(db.list_alerts()["alert_type"])
    db.end_batch("SOY-001")
    assert db.get_batch("SOY-001")["actual_duration_seconds"] == 400
    print("OK  alarm sensor/target + durasi aktual")

    # --- mode simulasi tick + pemisahan sumber
    db.create_batch({"batch_id": "SIM-LIVE", "material": "Air", "material_type": "Air", "volume_ml": 300,
                     "initial_temperature": 27, "target_temperature": 60, "heating_condition": "Tanpa pengadukan",
                     "data_source": "simulation"})
    db.start_batch("SIM-LIVE")
    last_real_before = db.latest_reading(source="real_sensor")["id"]
    for _ in range(300):
        if db.get_batch("SIM-LIVE")["status"] != "Heating":
            break
        simulation.simulate_tick("SIM-LIVE", 5)
    assert db.get_batch("SIM-LIVE")["status"] == "Target Reached"
    assert set(db.get_readings("SIM-LIVE")["data_source"]) == {"simulation"}
    # data simulasi tidak boleh dihitung sebagai data ESP32 (status koneksi hanya dari real_sensor)
    assert db.latest_reading(source="real_sensor")["id"] == last_real_before
    assert sensor_service.connection_status()["last_seen"] == db.latest_reading(source="real_sensor")["received_at"]
    print("OK  simulasi tidak mengubah status ESP32")
    print("\nSEMUA UJI LULUS")


def post_through_server(payload):
    return post(PORT, payload)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), api_service.Handler)
    PORT = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        main()
    finally:
        server.shutdown()
