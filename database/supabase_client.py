
import streamlit as st
from supabase import create_client


def get_supabase():
    """Membuat koneksi Supabase untuk sesi pengguna."""

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    client = create_client(url, key)

    access_token = st.session_state.get("supabase_access_token")
    refresh_token = st.session_state.get("supabase_refresh_token")

    if access_token and refresh_token:
        try:
            client.auth.set_session(access_token, refresh_token)
        except Exception:
            st.session_state.pop("supabase_access_token", None)
            st.session_state.pop("supabase_refresh_token", None)
            st.session_state.pop("supabase_user_id", None)

    return client


def test_connection():
    try:
        supabase = get_supabase()
        supabase.table("profiles").select("id").limit(1).execute()

        return True, "Koneksi Supabase berhasil!"

    except Exception as e:
        return False, str(e)
