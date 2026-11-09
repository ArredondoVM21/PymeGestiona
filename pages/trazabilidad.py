import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario


st.set_page_config(
    page_title="Trazabilidad",
    page_icon="🔎",
    layout="wide",
)

exigir_rol(["administrador"])
mostrar_sidebar_usuario()

st.title("🔎 Trazabilidad")
st.info("Registro de trazabilidad en construcción.")