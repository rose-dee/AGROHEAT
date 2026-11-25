
"""AGROHEAT - Smart Food Heating Monitoring System."""

import streamlit as st

import config
import ui

from database import db_manager as db
from services import sensor_service
from services.auth_service import register_user, login_user, logout_user

from views import (
    alerts,
    analytics,
    batch_management,
    data_history,
    dataset_management,
    live_monitoring,
    machine_learning,
    overview,
    system_settings,
)


# ==========================================
# KONFIGURASI APLIKASI
# ==========================================

st.set_page_config(
    page_title="AGROHEAT",
    page_icon="🌿",
    layout="wide"
)

# Database SQLite lama tetap dipertahankan sementara.
db.init_db()
ui.inject_css()


# ==========================================
# HALAMAN LOGIN DAN REGISTRASI
# ==========================================

def authentication_page():

    st.markdown(
        """
        <div class="ah-brand" style="text-align:center; font-size:42px;">
            AGRO<span>HEAT</span>
        </div>
        <div style="text-align:center; margin-bottom:30px;">
            Smart Food Heating Monitoring System
        </div>
        """,
        unsafe_allow_html=True
    )

    _, center, _ = st.columns([1, 1.5, 1])

    with center:

        login_tab, register_tab = st.tabs(
            ["Login", "Registrasi"]
        )

        # ----------------------------------
        # LOGIN
        # ----------------------------------

        with login_tab:

            st.subheader("Selamat Datang!")

            with st.form("login_form"):

                email = st.text_input(
                    "Email",
                    placeholder="nama@email.com"
                )

                password = st.text_input(
                    "Password",
                    type="password"
                )

                submit_login = st.form_submit_button(
                    "Login",
                    use_container_width=True
                )

            if submit_login:

                if not email or not password:
                    st.warning("Email dan password wajib diisi.")

                else:
                    with st.spinner("Memeriksa akun..."):

                        success, message = login_user(
                            email.strip(),
                            password
                        )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        # ----------------------------------
        # REGISTRASI
        # ----------------------------------

        with register_tab:

            st.subheader("Buat Akun AGROHEAT")

            with st.form("register_form"):

                full_name = st.text_input(
                    "Nama lengkap",
                    placeholder="Nama kamu"
                )

                email = st.text_input(
                    "Email",
                    placeholder="nama@email.com"
                )

                password = st.text_input(
                    "Password",
                    type="password"
                )

                confirm_password = st.text_input(
                    "Konfirmasi password",
                    type="password"
                )

                submit_register = st.form_submit_button(
                    "Daftar Akun",
                    use_container_width=True
                )

            if submit_register:

                if not full_name or not email or not password:
                    st.warning("Semua kolom wajib diisi.")

                elif password != confirm_password:
                    st.error("Konfirmasi password tidak cocok.")

                elif len(password) < 8:
                    st.error("Password minimal 8 karakter.")

                else:
                    with st.spinner("Membuat akun..."):

                        success, message = register_user(
                            email.strip(),
                            password,
                            full_name.strip()
                        )

                    if success:
                        st.success(message)
                        st.info(
                            "Setelah memverifikasi email, "
                            "silakan login."
                        )
                    else:
                        st.error(message)


# ==========================================
# PEMERIKSAAN AUTENTIKASI
# ==========================================

if not st.session_state.get("supabase_user_id"):

    authentication_page()
    st.stop()


# ==========================================
# HALAMAN UTAMA AGROHEAT
# ==========================================

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

    st.markdown(
        f'<div class="ah-brand">AGRO<span>HEAT</span></div>'
        f'<div class="ah-tag">{config.APP_TAGLINE}</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.caption("Akun pengguna")
    st.caption(
        st.session_state.get("supabase_user_id", "")
    )

    if st.button("Logout", use_container_width=True):

        logout_user()
        st.rerun()

    st.divider()

    choice = st.radio(
        "Navigasi",
        list(PAGES),
        label_visibility="collapsed"
    )

    st.divider()

    mode = st.selectbox(
        "Mode data",
        list(config.MODES),
        format_func=config.MODES.get,
        key="mode",
        help=(
            "Menentukan sumber data untuk batch BARU "
            "dan perilaku Live Monitoring."
        )
    )

    if mode == "simulation":
        st.caption("⚠️ Data simulasi — bukan data sensor nyata.")

    status = sensor_service.connection_status()

    st.caption(f"ESP32: **{status['esp32']}**")

    st.caption(
        "Backend API: **aktif**"
        if status["api_online"]
        else "Backend API: **belum aktif**"
    )


PAGES[choice].render(mode)
