"""Halaman Data History: riwayat seluruh pengukuran."""
import pandas as pd
import streamlit as st

import config
import ui
from database import db_manager as db


def render(mode):
    ui.page_header("Data History", "Riwayat pengukuran semua batch — filter, tinjau, dan unduh")
    df = db.get_all_readings()
    if df.empty:
        ui.empty_state("Belum ada data pengukuran.")
        return
    df["ts"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce")

    c1, c2, c3 = st.columns(3)
    sel_batches = c1.multiselect("Batch", sorted(df["batch_id"].unique()))
    sel_mat = c2.multiselect("Bahan", sorted(df["material"].unique()))
    sel_src = c3.multiselect("Sumber data", list(config.DATA_SOURCES), format_func=config.DATA_SOURCES.get)
    c4, c5 = st.columns([2, 1])
    dmin, dmax = df["ts"].min().date(), df["ts"].max().date()
    dates = c4.date_input("Rentang tanggal", (dmin, dmax), min_value=dmin, max_value=dmax)
    query = c5.text_input("Cari batch", placeholder="mis. LEMON")

    f = df
    if sel_batches: f = f[f["batch_id"].isin(sel_batches)]
    if sel_mat: f = f[f["material"].isin(sel_mat)]
    if sel_src: f = f[f["data_source"].isin(sel_src)]
    if query: f = f[f["batch_id"].str.contains(query, case=False, na=False)]
    if isinstance(dates, tuple) and len(dates) == 2:
        f = f[(f["ts"].dt.date >= dates[0]) & (f["ts"].dt.date <= dates[1])]

    st.caption(f"{len(f):,} dari {len(df):,} baris")
    raw = st.toggle("Tampilkan data mentah (semua kolom)")
    if raw:
        view = f.drop(columns=["ts"])
    else:
        view = f.rename(columns={"timestamp": "Timestamp", "batch_id": "Batch ID", "material": "Nama bahan",
                                 "temperature_c": "Suhu aktual (°C)", "elapsed_seconds": "Elapsed (detik)",
                                 "sensor_status": "Status sensor", "data_source": "Data source"})[
            ["Timestamp", "Batch ID", "Nama bahan", "Suhu aktual (°C)", "Elapsed (detik)", "Status sensor", "Data source"]]
    st.dataframe(view, hide_index=True, use_container_width=True, height=360)
    st.download_button("⬇ Download CSV (hasil filter)", f.drop(columns=["ts"]).to_csv(index=False).encode("utf-8"),
                       "agroheat_readings.csv", "text/csv")

    if not f.empty:
        st.subheader("Detail grafik batch")
        bid = st.selectbox("Batch", sorted(f["batch_id"].unique()))
        g = f[f["batch_id"] == bid]
        st.plotly_chart(ui.temp_chart(g, float(g["target_temperature"].iloc[0]), f"Batch {bid}"),
                        use_container_width=True)
