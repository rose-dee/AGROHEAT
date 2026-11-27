"""Halaman Batch Management: buat, mulai, akhiri, dan lihat detail batch."""
import re

import streamlit as st

import config
import ui
from database import db_manager as db


def _suggest_id(material_type: str) -> str:
    prefix = {
        "Air": "AIR",
        "Sari Kedelai": "SOY",
        "Sari Buah Lainnya": "JUICE",
        "Custom": "CUSTOM"
    }.get(material_type, "CUSTOM")

    return f"{prefix}-001"


def _create_tab(mode):
    s = db.get_settings()
    st.caption(f"Sumber data batch baru mengikuti mode saat ini: **{config.MODES[mode]}** "
               f"({config.DATA_SOURCES[mode]}).")
    mtype = st.selectbox("Jenis bahan", config.MATERIAL_TYPES, key="bm_type")
    with st.form("new_batch"):
        c1, c2 = st.columns(2)
        batch_id = c1.text_input("Batch ID", value=_suggest_id(mtype), help="Huruf, angka, - dan _")
        name = c2.text_input("Nama bahan", value="" if mtype == "Custom" else mtype)
        c3, c4, c5 = st.columns(3)
        volume = c3.number_input("Volume (mL)", 1.0, 20000.0, 500.0, 10.0)
        t0 = c4.number_input("Suhu awal (°C)", -5.0, 100.0, 28.0, 0.5)
        target = c5.number_input("Suhu target (°C)", 0.0, 120.0, float(s["default_target_temp"]), 0.5)
        cond = st.selectbox("Kondisi pemanasan", config.HEATING_CONDITIONS)
        notes = st.text_area("Catatan percobaan")
        if st.form_submit_button("Buat batch", type="primary"):
            errors = []
            if not re.fullmatch(r"[A-Za-z0-9_\-]{2,40}", batch_id.strip()):
                errors.append("Batch ID harus 2–40 karakter (huruf, angka, - atau _).")
            if not name.strip():
                errors.append("Nama bahan wajib diisi.")
            if target <= t0:
                errors.append("Suhu target harus lebih tinggi dari suhu awal.")
            if target > s["max_temperature"]:
                errors.append(f"Suhu target melebihi batas maksimum sistem ({s['max_temperature']:.0f} °C).")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    db.create_batch({"batch_id": batch_id.strip(), "material": name.strip(), "material_type": mtype,
                                     "volume_ml": volume, "initial_temperature": t0, "target_temperature": target,
                                     "heating_condition": cond, "data_source": mode, "notes": notes})
                    st.success(f"Batch {batch_id.strip()} dibuat (status Pending).")
                except ValueError as e:
                    st.error(str(e))


def _list_tab():
    df = db.list_batches()
    if df.empty:
        ui.empty_state("Belum ada batch.")
        return
    show = df.copy()
    show["data_source"] = show["data_source"].map(config.DATA_SOURCES)
    st.dataframe(show.drop(columns=["notes"]), hide_index=True, use_container_width=True)
    bid = st.selectbox("Kontrol batch", df["batch_id"].tolist(), key="bm_ctl")
    b = db.get_batch(bid)
    c = st.columns(4)
    if b["status"] == "Pending":
        if c[0].button("▶ Mulai", type="primary"):
            try:
                db.start_batch(bid); st.rerun()
            except ValueError as e:
                st.error(str(e))
        if c[1].button("🗑 Hapus batch"):
            db.delete_batch(bid); st.rerun()
    elif b["status"] in ("Heating", "Target Reached"):
        if c[0].button("■ Akhiri", type="primary"):
            db.end_batch(bid, "Completed"); st.rerun()
        if c[1].button("✕ Batalkan"):
            db.end_batch(bid, "Cancelled"); st.rerun()
    else:
        if c[0].button("🗑 Hapus batch"):
            db.delete_batch(bid); st.rerun()
        st.caption("Batch yang sudah selesai/dibatalkan tidak dapat dimulai ulang.")


def _detail_tab():
    df = db.list_batches()
    if df.empty:
        ui.empty_state("Belum ada batch.")
        return
    bid = st.selectbox("Pilih batch", df["batch_id"].tolist(), key="bm_detail")
    b = db.get_batch(bid)
    st.markdown(f"{ui.source_badge(b['data_source'])} &nbsp; Status: **{b['status']}**", unsafe_allow_html=True)
    c = st.columns(4)
    with c[0]: ui.metric_card("Volume", f"{b['volume_ml']:.0f} mL", b["material"], "gray")
    with c[1]: ui.metric_card("Suhu awal → target", f"{b['initial_temperature']:.1f} → {b['target_temperature']:.1f} °C", "", "gray")
    with c[2]: ui.metric_card("Waktu mencapai target", ui.fmt_duration(b["target_reached_seconds"]), "", "green")
    with c[3]: ui.metric_card("Durasi aktual", ui.fmt_duration(b["actual_duration_seconds"]), "", "gray")
    st.write(f"**Mulai:** {b['start_time'] or '—'} · **Selesai:** {b['end_time'] or '—'} · "
             f"**Kondisi:** {b['heating_condition']}")
    if b["notes"]:
        st.write(f"**Catatan:** {b['notes']}")
    r = db.get_readings(bid)
    if not r.empty:
        st.plotly_chart(ui.temp_chart(r, b["target_temperature"], f"Kurva pemanasan {bid}"), use_container_width=True)


def render(mode):
    ui.page_header("Batch Management", "Kelola sesi pemanasan: buat, mulai, akhiri, dan tinjau")
    t1, t2, t3 = st.tabs(["Buat batch", "Daftar & kontrol", "Detail batch"])
    with t1: _create_tab(mode)
    with t2: _list_tab()
    with t3: _detail_tab()
