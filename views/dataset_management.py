"""Halaman Dataset Management: unggah, validasi, bersihkan, impor, dan unduh dataset."""
import pandas as pd
import streamlit as st

import config
import ui
from database import db_manager as db
from services import dataset_service as ds, simulation


def render(mode):
    ui.page_header("Dataset Management", "Unggah CSV, validasi kualitas data, dan kelola sumber data")

    st.subheader("Sumber data di database")
    src = db.query_df("SELECT data_source, COUNT(DISTINCT batch_id) AS batch, COUNT(*) AS pembacaan "
                      "FROM readings GROUP BY data_source")
    if src.empty:
        st.caption("Belum ada data.")
    else:
        src["data_source"] = src["data_source"].map(config.DATA_SOURCES)
        st.dataframe(src.rename(columns={"data_source": "Sumber data"}), hide_index=True)
    ui.note("Data dari sumber berbeda tidak pernah digabung tanpa label sumber. Setiap batch & pembacaan membawa "
            "label sumbernya sendiri.")

    st.subheader("Data demo (simulasi)")
    c1, c2 = st.columns(2)
    if c1.button("Buat dataset demo (8 batch, berlabel Simulated Data)"):
        n = simulation.seed_demo_dataset(8)
        st.success(f"{n} batch simulasi dibuat." if n else "Dataset demo sudah ada.")
    if c2.button("Hapus semua data simulasi"):
        st.success(f"{db.delete_batches_by_source('simulation')} batch simulasi dihapus.")

    st.subheader("Unggah CSV")
    st.download_button("⬇ Template CSV", ds.template_csv(), "agroheat_template.csv", "text/csv")
    st.caption(f"Kolom wajib: {', '.join(ds.REQUIRED)}. Opsional: {', '.join(ds.OPTIONAL)}.")
    up = st.file_uploader("File CSV", type="csv")
    if up is not None:
        try:
            raw = pd.read_csv(up)
        except Exception as e:
            st.error(f"File tidak dapat dibaca: {e}")
            return
        st.session_state["ds_raw"] = raw
    raw = st.session_state.get("ds_raw")
    if raw is None:
        return

    st.write(f"**Ukuran:** {raw.shape[0]:,} baris × {raw.shape[1]} kolom")
    st.dataframe(raw.head(50), use_container_width=True)
    rep = ds.validate(raw)
    if rep["missing_cols"]:
        st.error(f"Kolom wajib hilang: {', '.join(rep['missing_cols'])}")
        return
    c = st.columns(4)
    with c[0]: ui.metric_card("Nilai kosong", sum(rep["nulls"].values()), str(rep["nulls"]) if rep["nulls"] else "tidak ada", "yellow" if rep["nulls"] else "green")
    with c[1]: ui.metric_card("Baris duplikat", rep["duplicates"], "batch_id + elapsed_seconds", "yellow" if rep["duplicates"] else "green")
    with c[2]: ui.metric_card("Non-numerik", sum(rep["non_numeric"].values()), str(rep["non_numeric"]) if rep["non_numeric"] else "tidak ada", "yellow" if rep["non_numeric"] else "green")
    with c[3]: ui.metric_card("Jenis bahan tak dikenal", len(rep["unknown_material"]), ", ".join(rep["unknown_material"]) or "tidak ada", "yellow" if rep["unknown_material"] else "green")

    cleaned = ds.clean(raw)
    st.write(f"**Setelah pembersihan:** {len(cleaned):,} baris, {cleaned['batch_id'].nunique()} batch")
    st.download_button("⬇ Download dataset bersih", cleaned.to_csv(index=False).encode("utf-8"), "agroheat_clean.csv", "text/csv")

    st.subheader("Impor ke database")
    source = st.selectbox("Label sumber dataset ini", list(config.DATA_SOURCES), format_func=config.DATA_SOURCES.get)
    if source == "simulation":
        st.warning("Dataset akan diberi label Simulated Data.")
    if st.button("Impor dataset bersih", type="primary"):
        res = ds.import_dataset(cleaned, source)
        st.success(f"{len(res['imported'])} batch diimpor.")
        if res["skipped"]:
            st.warning(f"Dilewati karena Batch ID sudah ada: {', '.join(res['skipped'])}")
