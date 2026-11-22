
import streamlit as st
from database.supabase_client import test_connection

st.set_page_config(page_title="Supabase Test")

st.title("AGROHEAT - Supabase Connection Test")

if st.button("Test Supabase Connection"):
    success, message = test_connection()

    if success:
        st.success(message)
    else:
        st.error(message)
