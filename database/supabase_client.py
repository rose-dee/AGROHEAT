
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    """Membuat koneksi Supabase untuk AGROHEAT."""

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    return create_client(url, key)


def test_connection():
    """Menguji koneksi ke Supabase."""

    try:
        supabase = get_supabase()
        response = supabase.table("profiles").select("id").limit(1).execute()

        return True, "Koneksi Supabase berhasil!"

    except Exception as e:
        return False, str(e)
