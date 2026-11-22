"""Halaman System Settings: ambang alarm, koneksi ESP32, status database."""
import socket

import streamlit as st

import config
import ui
from database import db_manager as db
from services import sensor_service


def _laptop_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # tidak mengirim data; hanya menentukan antarmuka aktif
            return s.getsockname()[0]
    except OSError:
        return "tidak terdeteksi"


def render(mode):
    ui.page_header("System Settings", "Ambang peringatan, koneksi ESP32, dan status database")
    s = db.get_settings()
    with st.form("settings"):
        c1, c2 = st.columns(2)
        default_target = c1.number_input("Target suhu default (°C)", 1.0, 120.0, float(s["default_target_temp"]), 0.5)
        max_temp = c2.number_input("Batas suhu maksimum (°C)", 1.0, 125.0, float(s["max_temperature"]), 0.5)
        timeout = c1.number_input("Batas waktu tanpa data sensor (detik)", 5, 3600, int(s["no_data_timeout_seconds"]))
        slow = c2.number_input("Batas pemanasan lambat (°C/menit)", 0.0, 20.0, float(s["slow_heating_c_per_min"]), 0.1)
        interval = c1.number_input("Interval pembacaan (detik)", 1, 600, int(s["reading_interval_seconds"]))
        speed = c2.number_input("Kecepatan simulasi (x)", 1, 60, int(s["simulation_speed"]), help="Hanya untuk mode demo")
        port = c1.number_input("Port backend API", 1024, 65535, int(s["api_port"]))
        if st.form_submit_button("Simpan pengaturan", type="primary"):
            if default_target > max_temp:
                st.error("Target default tidak boleh melebihi batas suhu maksimum.")
            else:
                db.set_settings({"default_target_temp": default_target, "max_temperature": max_temp,
                                 "no_data_timeout_seconds": timeout, "slow_heating_c_per_min": slow,
                                 "reading_interval_seconds": interval, "simulation_speed": speed, "api_port": port})
                st.success("Pengaturan disimpan.")

    st.subheader("Koneksi ESP32")
    conn = sensor_service.connection_status()
    ip = _laptop_ip()
    c = st.columns(3)
    with c[0]: ui.metric_card("Backend API", "Aktif" if conn["api_online"] else "Belum aktif", "python run_api.py", "green" if conn["api_online"] else "red")
    with c[1]: ui.metric_card("ESP32", conn["esp32"].split(" (")[0], f"data terakhir: {conn['last_seen'] or '—'}", conn["esp32_tone"])
    with c[2]: ui.metric_card("IP laptop (terdeteksi)", ip, "pastikan satu Wi-Fi dengan ESP32", "gray")
    st.code(f"POST http://{ip}:{int(s['api_port'])}/api/readings\nGET  http://{ip}:{int(s['api_port'])}/api/batches/active", language="text")
    st.caption("Masukkan alamat di atas ke firmware ESP32 (esp32/agroheat_esp32.ino). Izinkan Python di Windows Firewall (jaringan Private).")

    st.subheader("Status database")
    st.write(f"Lokasi: `{config.DB_PATH}` · Ukuran: {config.DB_PATH.stat().st_size / 1024:.1f} KB")
    st.dataframe([{"Tabel": k, "Jumlah baris": v} for k, v in db.table_counts().items()], hide_index=True)
