"""Backend HTTP penerima data ESP32 (proses terpisah dari Streamlit).
Hanya memakai pustaka standar Python (tanpa Flask/FastAPI) agar instalasi ringan.

Endpoint:
  GET  /health              -> cek server hidup
  GET  /api/batches/active  -> batch aktif (dipakai ESP32 untuk tahu batch_id)
  POST /api/readings        -> terima 1 pembacaan suhu (JSON)
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
from database import db_manager as db
from services import sensor_service


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "service": "agroheat-api"})
        elif self.path == "/api/batches/active":
            b = db.get_active_batch()
            if b is None or b["data_source"] != "real_sensor":
                self._send(200, {"active": False})
            else:
                self._send(200, {"active": True, "batch_id": b["batch_id"],
                                 "target_temperature": b["target_temperature"],
                                 "status": b["status"],
                                 "interval_seconds": db.get_settings()["reading_interval_seconds"]})
        else:
            self._send(404, {"ok": False, "errors": ["Endpoint tidak ditemukan."]})

    def do_POST(self):
        if self.path != "/api/readings":
            return self._send(404, {"ok": False, "errors": ["Endpoint tidak ditemukan."]})
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"ok": False, "errors": ["Body bukan JSON yang valid."]})
        try:
            code, body = sensor_service.ingest_payload(payload)
        except Exception as e:  # jangan biarkan server mati karena satu request
            code, body = 500, {"ok": False, "errors": [f"Kesalahan server: {e}"]}
        self._send(code, body)

    def log_message(self, fmt, *args):  # log ringkas
        print(f"[API] {self.address_string()} - {fmt % args}")


def run_server(host: str = config.API_HOST, port: int | None = None):
    db.init_db()
    port = port or db.get_settings()["api_port"]
    server = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"AGROHEAT API aktif di http://{host}:{port}  (Ctrl+C untuk berhenti)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()
