"""Halaman Machine Learning: pelatihan, evaluasi, dan keterbatasan model."""
import plotly.graph_objects as go
import streamlit as st

import config
import ui
from database import db_manager as db
from ml import predict, preprocessing as pp, train_model


def render(mode):
    ui.page_header("Machine Learning", "Prediksi sisa waktu (detik) menuju suhu target — Linear Regression vs Random Forest")
    table = pp.build_training_table(db.get_all_readings())

    st.subheader("1. Kesiapan data")
    if table.empty:
        st.warning("Belum ada batch yang mencapai suhu target, sehingga belum ada label aktual.")
    else:
        summ = table.groupby("data_source").agg(batch=("batch_id", "nunique"), baris=("batch_id", "size")).reset_index()
        summ["data_source"] = summ["data_source"].map(config.DATA_SOURCES)
        st.dataframe(summ.rename(columns={"data_source": "Sumber data"}), hide_index=True)
    st.caption("Label `remaining_seconds` dihitung dari waktu AKTUAL saat suhu pertama kali mencapai target — "
               "bukan dari prediksi model. Batch yang tidak pernah mencapai target tidak dipakai.")

    sources = st.multiselect("Sumber data untuk pelatihan", list(config.DATA_SOURCES), format_func=config.DATA_SOURCES.get,
                             default=[k for k in table["data_source"].unique() if k != "simulation"] if not table.empty else [])
    chosen = table[table["data_source"].isin(sources)] if not table.empty else table
    ok, msg = train_model.check_readiness(chosen)
    (st.success if ok else st.warning)(msg)
    if "simulation" in sources:
        st.error("Data SIMULASI ikut dipakai. Hasil hanya untuk uji alur sistem, TIDAK mencerminkan performa pada sensor nyata.")
    if len(sources) > 1:
        st.info("Beberapa sumber data digabung. Pastikan ini disengaja; setiap sumber tetap tercatat pada eksperimen.")

    if st.button("🚀 Latih & evaluasi model", type="primary", disabled=not ok):
        with st.spinner("Melatih model..."):
            try:
                train_model.train_and_evaluate(chosen)
                st.success("Pelatihan selesai.")
            except ValueError as e:
                st.error(str(e))

    meta = predict.load_meta()
    st.subheader("2. Hasil model")
    if not meta:
        st.info("Model belum terlatih — tidak ada metrik atau prediksi ML yang ditampilkan.")
    else:
        if meta["includes_simulation"]:
            st.error("⚠ Model/metrik di bawah dilatih dengan data yang mengandung SIMULASI.")
        c = st.columns(4)
        with c[0]: ui.metric_card("Data latih", f"{meta['n_train_rows']:,}", "baris", "gray")
        with c[1]: ui.metric_card("Batch latih / uji", f"{len(meta['train_batches'])} / {len(meta['test_batches'])}", "dibagi per batch", "gray")
        with c[2]: ui.metric_card("Model terpilih", meta["best_model"], "RMSE uji terendah", "green")
        with c[3]: ui.metric_card("Versi dataset", meta["dataset_version"], meta["trained_at"], "gray")

        res = meta["results"]
        st.dataframe([{"Model": k, "MAE (detik)": round(v["mae"], 1), "RMSE (detik)": round(v["rmse"], 1)}
                      for k, v in res.items()], hide_index=True, use_container_width=True)

        preds = predict.load_test_predictions()
        if preds is not None and not preds.empty:
            model_col = st.radio("Model untuk grafik", ["Linear Regression", "Random Forest"], horizontal=True)
            col = "pred_lr" if model_col == "Linear Regression" else "pred_rf"
            lim = float(max(preds["actual"].max(), preds[col].max()))
            g1, g2 = st.columns(2)
            fig = go.Figure(go.Scatter(x=preds["actual"], y=preds[col], mode="markers", name="Prediksi",
                                       marker=dict(color=config.COLORS["green"], opacity=.6)))
            fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", name="Ideal", line=dict(dash="dash", color="gray")))
            fig.update_layout(title="Actual vs Predicted (batch uji)", xaxis_title="Aktual (detik)", yaxis_title="Prediksi (detik)")
            g1.plotly_chart(ui.style_fig(fig), use_container_width=True)
            err = preds[col] - preds["actual"]
            fig2 = go.Figure(go.Scatter(x=preds["elapsed_seconds"], y=err, mode="markers", name="Error",
                                        marker=dict(color=config.COLORS["yellow"], opacity=.6)))
            fig2.add_hline(y=0, line_color="gray")
            fig2.update_layout(title="Error (prediksi − aktual) terhadap elapsed", xaxis_title="Elapsed (detik)", yaxis_title="Error (detik)")
            g2.plotly_chart(ui.style_fig(fig2), use_container_width=True)

            bid = st.selectbox("Bandingkan per batch uji", sorted(preds["batch_id"].unique()))
            p = preds[preds["batch_id"] == bid].sort_values("elapsed_seconds")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=p["elapsed_seconds"], y=p["actual"], name="Aktual", line=dict(color=config.COLORS["ink"])))
            fig3.add_trace(go.Scatter(x=p["elapsed_seconds"], y=p[col], name=model_col, line=dict(color=config.COLORS["green"])))
            fig3.update_layout(title=f"Sisa waktu: aktual vs prediksi — {bid}", xaxis_title="Elapsed (detik)", yaxis_title="Sisa waktu (detik)")
            st.plotly_chart(ui.style_fig(fig3), use_container_width=True)

    st.subheader("3. Riwayat eksperimen")
    exp = db.list_experiments()
    if exp.empty:
        st.caption("Belum ada eksperimen.")
    else:
        st.dataframe(exp, hide_index=True, use_container_width=True)

    st.subheader("Keterbatasan model")
    ui.note("• Jumlah batch kecil membuat metrik tidak stabil (satu batch uji bisa mengubah MAE/RMSE secara besar). "
            "• Model hanya valid untuk rentang bahan, volume, dan kondisi pemanasan yang ada di data latih. "
            "• Random Forest tidak dapat mengekstrapolasi di luar rentang data latih. "
            "• Pemilihan model memakai data uji yang sama dengan pelaporan, sehingga cenderung optimistis. "
            "• Prediksi adalah estimasi waktu menuju suhu target — bukan penilaian keamanan pangan atau pasteurisasi.")
