"""Halaman Live Monitoring: pemantauan suhu real-time batch aktif."""
from datetime import datetime

import streamlit as st

import ui
from database import db_manager as db
from ml import predict
from services import alert_service, sensor_service, simulation


def _dashboard_notifications(batch_id):
    alerts = db.list_alerts()

    if alerts.empty:
        return

    current = alerts[
        (alerts["batch_id"] == batch_id)
        & (alerts["status"].isin(["Active", "Acknowledged"]))
    ].head(5)

    if current.empty:
        return

    notified_ids = st.session_state.setdefault(
        "agroheat_notified_alert_ids", set()
    )

    st.markdown("#### 🔔 Notifikasi proses")

    for _, alert in current.iterrows():
        alert_id = int(alert["id"])

        if alert["priority"] == "Critical":
            icon = "🚨"
        elif alert["priority"] == "Warning":
            icon = "⚠️"
        else:
            icon = "ℹ️"

        st.warning(
            f"**{icon} {alert['alert_type']}**\n\n"
            f"{alert['message']}"
        )

        if alert_id not in notified_ids:
            st.toast(
                f"{alert['alert_type']}: {alert['message']}",
                icon=icon,
            )
            notified_ids.add(alert_id)


def _live_panel(mode):
    """Bagian yang menyegarkan diri secara berkala (st.fragment)."""
    s = db.get_settings()
    b = db.get_active_batch()
    if b is None:
        ui.empty_state("Tidak ada sesi aktif. Pilih batch Pending lalu klik **Mulai sesi**.")
        return
    # Simulasi hanya berjalan bila mode Demo DAN batch memang batch simulasi.
    if mode == "simulation" and b["data_source"] == "simulation" and b["status"] == "Heating":
        simulation.simulate_tick(b["batch_id"], int(s["simulation_speed"]))
        b = db.get_batch(b["batch_id"])

    # Evaluasi alarm untuk semua mode.
    alert_service.evaluate_batch(b["batch_id"]) 
    
    # cek alarm "data tidak masuk"
    readings = db.get_readings(b["batch_id"])
    valid = readings.dropna(subset=["temperature_c"])
    last = readings.iloc[-1] if not readings.empty else None

    st.markdown(f"**Batch `{b['batch_id']}`** — {b['material']} · {b['volume_ml']:.0f} mL · "
                f"{b['heating_condition']} &nbsp; Sumber data: {ui.source_badge(b['data_source'])}",
                unsafe_allow_html=True)
    if b["data_source"] != mode:
        st.warning(f"Batch ini bersumber **{b['data_source']}**, sedangkan mode saat ini **{mode}**. "
                   "Data hanya akan masuk sesuai sumber batch.")
    _dashboard_notifications(b["batch_id"])

    ml = predict.predict_remaining(b, readings)
    heur = predict.heuristic_remaining(b, readings)
    if b["status"] == "Target Reached":
        eta, eta_sub, tone = "Tercapai", f"pada detik ke-{b['target_reached_seconds']:.0f}", "green"
    elif ml:
        eta, eta_sub, tone = ui.fmt_duration(ml["seconds"]), f"Prediksi ML ({ml['model']})", "green"
    elif heur:
        eta, eta_sub, tone = ui.fmt_duration(heur), "Heuristik — BUKAN ML (model belum terlatih)", "yellow"
    else:
        eta, eta_sub, tone = "—", "Belum ada estimasi (data kurang / model belum terlatih)", "gray"

    sensor_ok = last is not None and last["sensor_status"] == "connected"
    c = st.columns(5)
    with c[0]: ui.metric_card("Suhu aktual", f"{valid['temperature_c'].iloc[-1]:.1f} °C" if not valid.empty else "—")
    with c[1]: ui.metric_card("Suhu target", f"{b['target_temperature']:.1f} °C", "", "gray")
    with c[2]: ui.metric_card("Waktu tersisa", eta, eta_sub, tone)
    with c[3]: ui.metric_card("Durasi berjalan", ui.fmt_duration(readings["elapsed_seconds"].max() if not readings.empty else None), "", "gray")
    with c[4]: ui.metric_card("Status proses", b["status"], "Sensor OK" if sensor_ok else "Sensor: tidak ada/bermasalah",
                              "green" if sensor_ok else "red")
    if not readings.empty:
        st.plotly_chart(ui.temp_chart(readings, b["target_temperature"]), use_container_width=True)
        st.caption(f"Pembacaan terakhir diterima: {last['received_at']} · total {len(readings)} titik data")
    else:
        ui.empty_state("Menunggu pembacaan pertama...")
    if b["data_source"] == "real_sensor":
        conn = sensor_service.connection_status()
        st.caption(f"ESP32: {conn['esp32']} · Backend API: {'aktif' if conn['api_online'] else 'belum aktif'}")


def render(mode):
    ui.page_header("Live Monitoring", "Pantau suhu, estimasi waktu menuju target, dan status sensor")
    s = db.get_settings()
    active = db.get_active_batch()

    with st.container(border=True):
        if active is None:
            pend = db.list_batches("Pending")
            if pend.empty:
                st.info("Belum ada batch Pending. Buat batch di **Batch Management**.")
            else:
                c1, c2 = st.columns([3, 1])
                bid = c1.selectbox("Batch yang akan dimulai", pend["batch_id"].tolist())
                c2.write(""); c2.write("")
                if c2.button("▶ Mulai sesi", type="primary", use_container_width=True):
                    try:
                        db.start_batch(bid)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        else:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"Sesi berjalan: **{active['batch_id']}** ({active['status']})")
            if c2.button("■ Akhiri sesi", type="primary", use_container_width=True):
                db.end_batch(active["batch_id"], "Completed"); st.rerun()
            if c3.button("✕ Batalkan", use_container_width=True):
                db.end_batch(active["batch_id"], "Cancelled"); st.rerun()

    if mode == "real_sensor" and not sensor_service.api_online():
        st.warning("Backend penerima data ESP32 belum aktif. Jalankan `python run_api.py` di terminal terpisah.")

    interval = float(max(2, s["reading_interval_seconds"]))
    live = st.fragment(_live_panel, run_every=None if mode == "manual" else interval)
    live(mode)

    if mode == "manual" and active is not None:
        st.subheader("Input suhu manual")
        if active["data_source"] != "manual":
            st.warning("Batch aktif bukan batch Manual Input; input manual dinonaktifkan agar data tidak tercampur.")
        else:
            with st.form("manual_reading", clear_on_submit=True):
                temp = st.number_input("Suhu terukur (°C)", -10.0, 125.0, float(active["initial_temperature"]), 0.1)
                if st.form_submit_button("Simpan pembacaan"):
                    elapsed = (datetime.now() - datetime.fromisoformat(active["start_time"])).total_seconds()
                    sensor_service.process_reading(active["batch_id"], temp, elapsed, "connected", "manual")
                    st.rerun()
