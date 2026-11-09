from datetime import datetime

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import listar_rendiciones_usuario


st.set_page_config(
    page_title="Mis rendiciones",
    page_icon="📋",
    layout="wide",
)

exigir_rol(["trabajador"])
mostrar_sidebar_usuario()

st.title("📋 Mis rendiciones")
st.write(
    "Consulta el estado, riesgo y observaciones "
    "de las rendiciones registradas."
)


empresa_id = st.session_state["empresa_id"]
usuario_id = st.session_state["usuario_id"]


def formatear_moneda(valor) -> str:
    """
    Convierte un valor numérico al formato monetario chileno.
    """
    try:
        numero = float(valor)
        return f"${numero:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def formatear_fecha(valor) -> str:
    """
    Convierte una fecha de Supabase a un formato legible.
    """
    if not valor:
        return "Sin información"

    try:
        fecha = datetime.fromisoformat(
            valor.replace("Z", "+00:00")
        )
        return fecha.strftime("%d-%m-%Y %H:%M")
    except (ValueError, AttributeError):
        return str(valor)


try:
    rendiciones = listar_rendiciones_usuario(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )

except Exception as error:
    st.error(
        "No fue posible consultar las rendiciones."
    )
    st.code(str(error))
    st.stop()


if not rendiciones:
    st.info(
        "Todavía no tienes rendiciones registradas."
    )

    st.page_link(
        "pages/nueva_rendicion.py",
        label="Crear una rendición",
        icon="🧾",
    )

    st.stop()


# =========================================================
# RESUMEN
# =========================================================

total_rendiciones = len(rendiciones)

pendientes = sum(
    1
    for rendicion in rendiciones
    if rendicion["estado"] == "Pendiente"
)

aprobadas = sum(
    1
    for rendicion in rendiciones
    if rendicion["estado"] == "Aprobada"
)

rechazadas = sum(
    1
    for rendicion in rendiciones
    if rendicion["estado"] == "Rechazada"
)


columna_1, columna_2, columna_3, columna_4 = st.columns(4)

with columna_1:
    st.metric(
        "Total",
        total_rendiciones,
    )

with columna_2:
    st.metric(
        "Pendientes",
        pendientes,
    )

with columna_3:
    st.metric(
        "Aprobadas",
        aprobadas,
    )

with columna_4:
    st.metric(
        "Rechazadas",
        rechazadas,
    )


st.divider()


# =========================================================
# FILTROS
# =========================================================

columna_filtro_1, columna_filtro_2 = st.columns(2)

with columna_filtro_1:
    filtro_estado = st.selectbox(
        "Filtrar por estado",
        [
            "Todos",
            "Borrador",
            "Pendiente",
            "Aprobada",
            "Rechazada",
            "Corregida",
            "Reenviada",
        ],
    )

with columna_filtro_2:
    filtro_riesgo = st.selectbox(
        "Filtrar por nivel de riesgo",
        [
            "Todos",
            "Bajo",
            "Medio",
            "Alto",
        ],
    )


rendiciones_filtradas = rendiciones

if filtro_estado != "Todos":
    rendiciones_filtradas = [
        rendicion
        for rendicion in rendiciones_filtradas
        if rendicion["estado"] == filtro_estado
    ]

if filtro_riesgo != "Todos":
    rendiciones_filtradas = [
        rendicion
        for rendicion in rendiciones_filtradas
        if rendicion["nivel_riesgo"] == filtro_riesgo
    ]


if not rendiciones_filtradas:
    st.warning(
        "No existen rendiciones que coincidan con los filtros."
    )
    st.stop()


# =========================================================
# LISTADO
# =========================================================

for rendicion in rendiciones_filtradas:
    titulo = (
        f"Rendición #{rendicion['id']} · "
        f"{rendicion['proveedor']} · "
        f"{formatear_moneda(rendicion['monto_total'])}"
    )

    with st.expander(titulo):
        columna_detalle_1, columna_detalle_2 = st.columns(2)

        with columna_detalle_1:
            st.write(
                f"**Estado:** {rendicion['estado']}"
            )

            st.write(
                f"**Nivel de riesgo:** "
                f"{rendicion['nivel_riesgo']}"
            )

            st.write(
                f"**Tipo de documento:** "
                f"{rendicion['tipo_documento']}"
            )

            st.write(
                f"**RUT del emisor:** "
                f"{rendicion['rut_emisor']}"
            )

            st.write(
                f"**Folio:** {rendicion['folio']}"
            )

            st.write(
                f"**Categoría:** {rendicion['categoria']}"
            )

        with columna_detalle_2:
            st.write(
                f"**Fecha del documento:** "
                f"{rendicion['fecha_documento']}"
            )

            st.write(
                f"**Monto neto:** "
                f"{formatear_moneda(rendicion['monto_neto'])}"
            )

            st.write(
                f"**IVA:** "
                f"{formatear_moneda(rendicion['iva'])}"
            )

            st.write(
                f"**Monto total:** "
                f"{formatear_moneda(rendicion['monto_total'])}"
            )

            st.write(
                f"**Fecha de envío:** "
                f"{formatear_fecha(rendicion['fecha_envio'])}"
            )

        descripcion = rendicion.get("descripcion")

        if descripcion:
            st.write(
                f"**Descripción:** {descripcion}"
            )

        reglas = rendicion.get("reglas_activadas") or []

        if reglas:
            st.warning(
                "**Reglas activadas:** "
                + ", ".join(reglas)
            )
        else:
            st.success(
                "La rendición no presenta reglas activadas."
            )

        motivo_rechazo = rendicion.get("motivo_rechazo")

        if motivo_rechazo:
            st.error(
                f"**Motivo del rechazo:** {motivo_rechazo}"
            )


st.divider()

st.page_link(
    "pages/nueva_rendicion.py",
    label="Registrar otra rendición",
    icon="🧾",
)