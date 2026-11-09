import streamlit as st
from database import comprobar_conexion

# Configuración general de la aplicación
st.set_page_config(
    page_title="PymeGestiona",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Encabezado principal
st.title("📊 PymeGestiona")

st.subheader("Sistema de gestión y control de rendiciones")

st.success("Prototipo funcional desplegado correctamente")
try:
    estado_db = comprobar_conexion()

    st.success("Conexión con Supabase establecida correctamente.")

    st.caption(
        f"Base de datos disponible: "
        f"{estado_db['empresas']} empresa y "
        f"{estado_db['usuarios']} usuarios."
    )

except Exception as error:
    st.error("No fue posible conectar con Supabase.")
    st.code(str(error))

# Descripción del prototipo
st.markdown(
    """
    **PymeGestiona** es un prototipo orientado a apoyar el registro,
    revisión y control de rendiciones de gastos realizadas por trabajadores
    de pequeñas y medianas empresas.

    Esta versión permite validar progresivamente:

    - Inicio de sesión según rol.
    - Registro de rendiciones.
    - Carga de documentos de respaldo.
    - Aplicación de reglas de negocio.
    - Revisión administrativa.
    - Aprobación o rechazo de rendiciones.
    - Registro de trazabilidad.
    """
)


st.divider()


# Información de la versión
columna_1, columna_2, columna_3 = st.columns(3)

with columna_1:
    st.metric(
        label="Versión del prototipo",
        value="0.1.0",
    )

with columna_2:
    st.metric(
        label="Estado",
        value="En desarrollo",
    )

with columna_3:
    st.metric(
        label="Ambiente",
        value="Demostración",
    )


st.divider()


# Alcance académico
st.info(
    """
    Esta implementación corresponde a un prototipo académico destinado a
    validar el flujo principal de la solución. La arquitectura productiva
    propuesta será desarrollada en una etapa posterior.
    """
)


# Pie de página
st.caption(
    "PymeGestiona · Prototipo académico · Datos exclusivamente demostrativos"
)