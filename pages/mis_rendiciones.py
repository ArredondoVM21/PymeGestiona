import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario


st.set_page_config(
    page_title="Mis rendiciones",
    page_icon="📋",
    layout="wide",
)

exigir_rol(["trabajador"])
mostrar_sidebar_usuario()

st.title("📋 Mis rendiciones")
st.info("Consulta de rendiciones en construcción.")