"""Halaman Analytics: perbandingan antarbatch."""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import config
import ui
from database import db_manager as db
from ml import predict
from ml.evaluation import per_batch_mae


def render(mode):
    ui.page_header("Analytics", "Perbandingan hasil pemanasan antarbatch")
    batches = db.list_batches()
    batches = batches[batches["status"] != "Pending"] if not batches.empty else batches
    if batches.empty:
        ui.empty_state("Belum ada batch yang berjalan/selesai untuk dianalisis.")
        return
    sel = st.multiselect("Batch yang dibandingkan", batches["batch_id"].tolist(), default=batches["batch_id"].tolist()[:5])
    if not sel:
        ui.empty_state("Pilih minimal satu batch.")
        return
    b = batches[batches["batch_id"].isin(sel)].copy()
    b["Sumber"] = b["data_source"].map(config.DATA_SOURCES)
    if b["data_source"].nunique() > 1:
        st.warning("Batch dari sumber data berbeda sedang dibandingkan. Perhatikan kolom/legenda Sumber.")

    fig = go.Figure()
    for bid in sel:
        r = db.get_readings(bid).dropna(subset=["temperature_c"])
        src = config.DATA_SOURCES[b[b["batch_id"] == bid]["data_source"].iloc[0]]
        fig.add_trace(go.Scatter(x=r["elapsed_seconds"], y=r["temperature_c"], mode="lines", name=f"{bid} ({src})"))
    fig.update_layout(title="Kurva suhu antarbatch", xaxis_title="Elapsed (detik)", yaxis_title="Suhu (°C)")
    st.plotly_chart(ui.style_fig(fig, 420), use_container_width=True)

    b["Waktu ke target (dtk)"] = b["target_reached_seconds"]
    b["Durasi aktual (dtk)"] = b["actual_duration_seconds"]
    c1, c2 = st.columns(2)
    dur = b.melt(id_vars="batch_id", value_vars=["Waktu ke target (dtk)", "Durasi aktual (dtk)"], var_name="Ukuran", value_name="detik")
    c1.plotly_chart(ui.style_fig(px.bar(dur, x="batch_id", y="detik", color="Ukuran", barmode="group",
                                        title="Perbandingan durasi pemanasan",
                                        color_discrete_sequence=[config.COLORS["green"], config.COLORS["gray"]])), use_container_width=True)
    temps = b.melt(id_vars="batch_id", value_vars=["initial_temperature", "target_temperature"], var_name="Jenis", value_name="°C")
    c2.plotly_chart(ui.style_fig(px.bar(temps, x="batch_id", y="°C", color="Jenis", barmode="group",
                                        title="Suhu awal vs target",
                                        color_discrete_sequence=[config.COLORS["yellow"], config.COLORS["red"]])), use_container_width=True)

    done = b.dropna(subset=["target_reached_seconds"])
    c3, c4 = st.columns(2)
    if done.empty:
        c3.info("Belum ada batch yang mencapai target untuk perbandingan bahan/volume.")
    else:
        mat = done.groupby("material_type")["target_reached_seconds"].mean().reset_index()
        c3.plotly_chart(ui.style_fig(px.bar(mat, x="material_type", y="target_reached_seconds", title="Rata-rata waktu ke target per bahan",
                                            color_discrete_sequence=[config.COLORS["green"]])), use_container_width=True)
        c4.plotly_chart(ui.style_fig(px.scatter(done, x="volume_ml", y="target_reached_seconds", color="material_type",
                                                hover_name="batch_id", title="Volume vs waktu ke target")), use_container_width=True)

    st.subheader("Prediksi vs aktual per batch uji")
    preds = predict.load_test_predictions()
    meta = predict.load_meta()
    if preds is None or meta is None:
        st.info("Model belum terlatih — perbandingan prediksi vs aktual belum tersedia.")
    else:
        col = "pred_lr" if meta["best_model"] == "Linear Regression" else "pred_rf"
        pb = per_batch_mae(preds, col)
        st.caption(f"Hanya batch UJI (tidak dipakai melatih). Model: {meta['best_model']}.")
        st.dataframe(pb.rename(columns={"mae_seconds": "MAE (detik)"}).round(1), hide_index=True)

    st.subheader("Ringkasan percobaan")
    cols = ["batch_id", "material_type", "volume_ml", "initial_temperature", "target_temperature", "heating_condition",
            "Waktu ke target (dtk)", "Durasi aktual (dtk)", "status", "Sumber"]
    st.dataframe(b[cols], hide_index=True, use_container_width=True)
