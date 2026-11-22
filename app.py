"""AGROHEAT - titik masuk aplikasi.  Jalankan:  python -m streamlit run app.py"""
import streamlit as st

import config
import ui
from database import db_manager as db
from services import sensor_service
from views import (alerts, analytics, batch_management, data_history, dataset_management,
                   live_monitoring, machine_learning, overview, system_settings)

st.set_page_config(page_title="AGROHEAT", page_icon="🌿", layout="wide")
db.init_db()          # database & tabel dibuat otomatis
ui.inject_css()

PAGES = {
    "📊 Overview": overview,
    "🌡️ Live Monitoring": live_monitoring,
    "🧪 Batch Management": batch_management,
    "🗂️ Data History": data_history,
    "🤖 Machine Learning": machine_learning,
    "📈 Analytics": analytics,
    "🚨 Alerts": alerts,
    "📁 Dataset Management": dataset_management,
    "⚙️ System Settings": system_settings,
}

with st.sidebar:
    st.markdown(f'<div class="ah-brand">AGRO<span>HEAT</span></div>'
                f'<div class="ah-tag">{config.APP_TAGLINE}</div>', unsafe_allow_html=True)
    choice = st.radio("Navigasi", list(PAGES), label_visibility="collapsed")
    st.divider()
    mode = st.selectbox("Mode data", list(config.MODES), format_func=config.MODES.get, key="mode",
                        help="Menentukan sumber data untuk batch BARU dan perilaku Live Monitoring.")
    if mode == "simulation":
        st.caption("⚠️ Data simulasi — bukan data sensor nyata.")
    status = sensor_service.connection_status()
    st.caption(f"ESP32: **{status['esp32']}**")
    st.caption("Backend API: **aktif**" if status["api_online"] else "Backend API: **belum aktif**")

PAGES[choice].render(mode)
