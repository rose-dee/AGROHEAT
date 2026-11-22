"""Uji asap halaman Streamlit memakai Streamlit/Plotly PALSU (mock).
Hanya mendeteksi error Python (nama salah, kolom hilang, dll). TIDAK menguji tampilan visual.
Jalankan:  python tests/smoke_views.py"""
import sys, tempfile, types
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

st = MagicMock(name="streamlit")


class Col:
    """Kolom/tab/container palsu: meneruskan semua pemanggilan widget ke streamlit palsu."""
    def __getattr__(self, name):
        return getattr(st, name)
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


st.columns.side_effect = lambda spec, **k: [Col() for _ in range(spec if isinstance(spec, int) else len(spec))]
st.tabs.side_effect = lambda labels: [Col() for _ in labels]
for _n in ("container", "form", "expander", "spinner", "sidebar"):
    getattr(st, _n).side_effect = lambda *a, **k: Col()
for fn in ("button", "form_submit_button", "toggle"):
    getattr(st, fn).return_value = False
st.selectbox.side_effect = lambda label, options, *a, **k: list(options)[0] if len(list(options)) else None
st.multiselect.side_effect = lambda *a, **k: k.get("default", [])
st.radio.side_effect = lambda label, options, *a, **k: list(options)[0]
st.text_input.side_effect = lambda label, value="", **k: value
st.number_input.side_effect = lambda label, mn=0, mx=0, val=0, *a, **k: val
st.date_input.side_effect = lambda label, value, **k: value
st.file_uploader.return_value = None
st.session_state = {}
st.fragment.side_effect = lambda fn, run_every=None: fn
sys.modules["streamlit"] = st
for name in ("plotly", "plotly.graph_objects", "plotly.express"):
    sys.modules[name] = MagicMock()

import config
tmp = Path(tempfile.mkdtemp())
config.DB_PATH, config.MODEL_DIR = tmp / "s.db", tmp / "m"

from database import db_manager as db
from ml import preprocessing as pp, train_model
from services import simulation
from views import (alerts, analytics, batch_management, data_history, dataset_management,
                   live_monitoring, machine_learning, overview, system_settings)

VIEWS = {"overview": overview, "live": live_monitoring, "batch": batch_management, "history": data_history,
         "ml": machine_learning, "analytics": analytics, "alerts": alerts, "dataset": dataset_management,
         "settings": system_settings}


def run_all(label):
    for mode in config.MODES:
        for name, v in VIEWS.items():
            try:
                v.render(mode)
            except Exception as e:
                print(f"GAGAL [{label}] {name} mode={mode}: {type(e).__name__}: {e}")
                raise
    print(f"OK  semua halaman ({label})")


db.init_db()
run_all("database kosong")
simulation.seed_demo_dataset(8)
train_model.train_and_evaluate(pp.build_training_table(db.get_all_readings()))
db.create_batch({"batch_id": "SIM-ACTIVE", "material": "Air", "material_type": "Air", "volume_ml": 400,
                 "initial_temperature": 27, "target_temperature": 65, "heating_condition": "Tanpa pengadukan",
                 "data_source": "simulation"})
db.start_batch("SIM-ACTIVE")
run_all("data demo + sesi aktif")
run_all("tick simulasi berikutnya")
print("SMOKE TEST LULUS")
