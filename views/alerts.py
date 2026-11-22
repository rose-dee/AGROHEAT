"""Halaman Alerts: daftar, tindak lanjut, dan riwayat alarm."""
import streamlit as st

import ui
from database import db_manager as db
from services import alert_service

ICON = {"Critical": "🔴", "Warning": "🟡", "Info": "🟢"}


def render(mode):
    ui.page_header("Alerts", "Peringatan berbasis aturan untuk suhu dan kelancaran data")
    ui.note("Alarm hanya memantau suhu dan aliran data. Sistem ini <b>tidak</b> menilai keamanan pangan "
            "atau keberhasilan pasteurisasi.")
    st.write("")
    b = db.get_active_batch()
    if b and st.button("🔄 Evaluasi aturan untuk batch aktif"):
        alert_service.evaluate_batch(b["batch_id"]); st.rerun()

    tab1, tab2 = st.tabs(["Alarm aktif", "Riwayat alarm"])
    with tab1:
        al = db.list_alerts()
        al = al[al["status"].isin(["Active", "Acknowledged"])] if not al.empty else al
        if al.empty:
            ui.empty_state("Tidak ada alarm aktif.")
        for _, r in al.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([5, 2])
                c1.markdown(f"{ICON[r['priority']]} **{r['alert_type']}** — `{r['batch_id']}` · {r['priority']} · {r['status']}  \n"
                            f"{r['message']}  \n<small>{r['timestamp']}</small>", unsafe_allow_html=True)
                if r["status"] == "Active" and c2.button("Acknowledge", key=f"ack{r['id']}"):
                    db.set_alert_status(r["id"], "Acknowledged"); st.rerun()
                if c2.button("Selesai", key=f"res{r['id']}"):
                    db.set_alert_status(r["id"], "Resolved"); st.rerun()
    with tab2:
        hist = db.list_alerts()
        if hist.empty:
            ui.empty_state("Belum ada riwayat alarm.")
        else:
            c1, c2 = st.columns(2)
            pr = c1.multiselect("Prioritas", ["Critical", "Warning", "Info"])
            ty = c2.multiselect("Jenis", sorted(hist["alert_type"].unique()))
            if pr: hist = hist[hist["priority"].isin(pr)]
            if ty: hist = hist[hist["alert_type"].isin(ty)]
            st.dataframe(hist.rename(columns={"timestamp": "Timestamp", "batch_id": "Batch ID", "alert_type": "Jenis",
                                              "priority": "Prioritas", "message": "Pesan", "status": "Status"}),
                         hide_index=True, use_container_width=True)
