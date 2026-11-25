
import streamlit as st
from database.supabase_client import get_supabase


def register_user(email, password, full_name):
    try:
        supabase = get_supabase()

        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                }
            }
        })

        return True, "Registrasi berhasil. Periksa email untuk verifikasi."

    except Exception as e:
        return False, str(e)


def login_user(email, password):
    try:
        supabase = get_supabase()

        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        session = response.session

        if not session:
            return False, "Login belum menghasilkan sesi. Periksa verifikasi email."

        st.session_state["supabase_access_token"] = session.access_token
        st.session_state["supabase_refresh_token"] = session.refresh_token
        st.session_state["supabase_user_id"] = response.user.id

        return True, "Login berhasil!"

    except Exception as e:
        return False, str(e)


def logout_user():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    finally:
        st.session_state.pop("supabase_access_token", None)
        st.session_state.pop("supabase_refresh_token", None)
        st.session_state.pop("supabase_user_id", None)
