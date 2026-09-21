import streamlit as st
from st_supabase_connection import SupabaseConnection

conn = st.connection("supabase", type=SupabaseConnection)
rows = conn.table("users").select("*").execute()
st.write(rows)