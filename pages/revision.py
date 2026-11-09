import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario


st.set_page_config(
    page_title="Revisión administrativa",
    page_icon="✅",
    layout="wide",
)

exigir_rol(["administrador"])
mostrar_sidebar_usuario()

st.title("✅ Revisión administrativa")
st.info("Bandeja administrativa en construcción.")