"""Konfigurasi global AGROHEAT. Ubah nilai di sini jika perlu."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "agroheat.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
MODEL_DIR = BASE_DIR / "models"

APP_NAME = "AGROHEAT"
APP_TAGLINE = "Smart Food Heating Monitoring System"

# Backend penerima data ESP32 (proses terpisah dari Streamlit)
API_HOST = "0.0.0.0"
API_PORT = 8000

MATERIAL_TYPES = ["Air", "Sari Kedelai", "Sari Buah Lainnya", "Custom"]
HEATING_CONDITIONS = ["Tanpa pengadukan", "Dengan pengadukan", "Lainnya"]
BATCH_STATUSES = ["Pending", "Heating", "Target Reached", "Completed", "Cancelled"]
SENSOR_STATUSES = ["connected", "disconnected", "error"]

# Kunci = nilai di database, nilai = label tampilan
DATA_SOURCES = {
    "real_sensor": "Real Sensor Data",
    "public_dataset": "Public Research Dataset",
    "manual": "Manual Input",
    "simulation": "Simulated Data",
}
MODES = {
    "simulation": "Demo / Simulation",
    "real_sensor": "Real Sensor",
    "manual": "Manual Input",
}

# Nilai awal pengaturan (disimpan di tabel system_settings)
DEFAULT_SETTINGS = {
    "default_target_temp": 70.0,
    "max_temperature": 95.0,
    "no_data_timeout_seconds": 30,
    "slow_heating_c_per_min": 0.5,
    "reading_interval_seconds": 5,
    "simulation_speed": 5,
    "api_port": API_PORT,
}

# Syarat minimum data sebelum model boleh dilatih
MIN_TOTAL_BATCHES = 4      # minimal 3 batch latih + 1 batch uji
MIN_TOTAL_ROWS = 40
TEST_FRACTION = 0.25
RANDOM_STATE = 42

# Palet warna identitas visual AgroHeat
COLORS = {
    "green_dark": "#14532d",
    "green": "#16a34a",
    "green_soft": "#dcfce7",
    "yellow": "#d97706",
    "yellow_soft": "#fef3c7",
    "red": "#dc2626",
    "red_soft": "#fee2e2",
    "gray": "#64748b",
    "gray_soft": "#f1f5f9",
    "ink": "#0f172a",
}
