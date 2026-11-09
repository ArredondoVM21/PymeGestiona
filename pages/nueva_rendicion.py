import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario


st.set_page_config(
    page_title="Nueva rendición",
    page_icon="🧾",
    layout="wide",
)

exigir_rol(["trabajador"])
mostrar_sidebar_usuario()

st.title("🧾 Nueva rendición")
st.info("Formulario de rendición en construcción.")