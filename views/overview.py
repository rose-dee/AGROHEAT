"""Halaman Overview: ringkasan seluruh sistem."""
import pandas as pd
import streamlit as st

import ui
from database import db_manager as db
from ml import predict
from services import sensor_service


def render(mode):
    ui.page_header("Overview", "Ringkasan batch, koneksi perangkat, dan proses pemanasan terbaru")
    batches = db.list_batches()
    counts = db.table_counts()
    done = int(batches["status"].isin(["Completed", "Target Reached"]).sum()) if not batches.empty else 0
    conn = sensor_service.connection_status()

    c = st.columns(5)
    with c[0]: ui.metric_card("Total batch", counts["batches"])
    with c[1]: ui.metric_card("Total pengukuran", f"{counts['readings']:,}")
    with c[2]: ui.metric_card("Batch selesai", done, "Completed + Target Reached")
    with c[3]: ui.metric_card("ESP32", conn["esp32"].split(" (")[0], conn["esp32"] if "(" in conn["esp32"] else "", conn["esp32_tone"])
    with c[4]: ui.metric_card("Sensor DS18B20", conn["sensor"], "", conn["sensor_tone"])
    st.write("")

    active = db.get_active_batch()
    if active is None:
        ui.empty_state("Tidak ada batch aktif. Buat dan mulai batch di menu **Batch Management**.")
        readings, batch_for_chart = pd.DataFrame(), None
        if not batches.empty:
            batch_for_chart = batches.iloc[0].to_dict()
            readings = db.get_readings(batch_for_chart["batch_id"])
    else:
        batch_for_chart, readings = active, db.get_readings(active["batch_id"])
        valid = readings.dropna(subset=["temperature_c"])
        actual = f"{valid['temperature_c'].iloc[-1]:.1f} °C" if not valid.empty else "—"
        duration = readings["elapsed_seconds"].max() if not readings.empty else None
        ml = predict.predict_remaining(active, readings)
        heur = predict.heuristic_remaining(active, readings)
        if active["status"] == "Target Reached":
            eta, eta_sub = "Tercapai", ""
        elif ml:
            eta, eta_sub = ui.fmt_duration(ml["seconds"]), f"Prediksi ML ({ml['model']})"
        elif heur:
            eta, eta_sub = ui.fmt_duration(heur), "Heuristik — bukan ML (model belum terlatih)"
        else:
            eta, eta_sub = "—", "Belum ada estimasi"
        st.markdown(f"**Batch aktif:** `{active['batch_id']}` — {active['material']} · "
                    f"{active['volume_ml']:.0f} mL &nbsp; {ui.source_badge(active['data_source'])}",
                    unsafe_allow_html=True)
        c = st.columns(4)
        with c[0]: ui.metric_card("Suhu aktual", actual)
        with c[1]: ui.metric_card("Suhu target", f"{active['target_temperature']:.1f} °C", "", "gray")
        with c[2]: ui.metric_card("Estimasi waktu tersisa", eta, eta_sub, "yellow" if not ml else "green")
        with c[3]: ui.metric_card("Durasi pemanasan", ui.fmt_duration(duration), active["status"], "gray")

    if batch_for_chart is not None and not readings.empty:
        label = "aktif" if active else "terakhir"
        st.plotly_chart(ui.temp_chart(readings, batch_for_chart["target_temperature"],
                                      f"Perkembangan suhu — batch {label}: {batch_for_chart['batch_id']}"),
                        use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Aktivitas terbaru")
        if batches.empty:
            ui.empty_state("Belum ada batch.")
        else:
            show = batches.head(6)[["batch_id", "material", "status", "data_source", "created_at"]]
            st.dataframe(show, hide_index=True, use_container_width=True)
    with right:
        st.subheader("Alarm terbaru")
        al = db.list_alerts().head(6)
        if al.empty:
            ui.empty_state("Belum ada alarm.")
        else:
            st.dataframe(al[["timestamp", "batch_id", "alert_type", "priority", "status"]],
                         hide_index=True, use_container_width=True)
