from datetime import datetime

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import listar_auditoria_empresa


st.set_page_config(
    page_title="Trazabilidad",
    page_icon="🔎",
    layout="wide",
)

exigir_rol(["administrador"])
mostrar_sidebar_usuario()

st.title("🔎 Trazabilidad")

st.write(
    "Consulta el historial de acciones realizadas sobre "
    "las rendiciones de la empresa."
)


empresa_id = st.session_state["empresa_id"]


def formatear_moneda(valor) -> str:
    """
    Convierte un número al formato monetario chileno.
    """
    try:
        numero = float(valor)
        return f"${numero:,.0f}".replace(",", ".")

    except (TypeError, ValueError):
        return "$0"


def formatear_fecha(valor) -> str:
    """
    Convierte una fecha ISO de Supabase a formato legible.
    """
    if not valor:
        return "Sin información"

    try:
        fecha = datetime.fromisoformat(
            valor.replace("Z", "+00:00")
        )

        return fecha.strftime("%d-%m-%Y %H:%M:%S")

    except (ValueError, AttributeError):
        return str(valor)


def etiqueta_transicion(evento: dict) -> str:
    """
    Construye una descripción breve del cambio de estado.
    """
    anterior = evento.get("estado_anterior")
    nuevo = evento.get("estado_nuevo")

    if anterior and nuevo:
        return f"{anterior} → {nuevo}"

    if nuevo:
        return f"Nuevo estado: {nuevo}"

    return "Sin cambio de estado"


try:
    eventos = listar_auditoria_empresa(
        empresa_id=empresa_id,
    )

except Exception as error:
    st.error(
        "No fue posible consultar el historial de trazabilidad."
    )

    st.code(str(error))
    st.stop()


# =========================================================
# RESUMEN
# =========================================================

total_eventos = len(eventos)

envios = sum(
    1
    for evento in eventos
    if evento.get("estado_nuevo") == "Pendiente"
)

aprobaciones = sum(
    1
    for evento in eventos
    if evento.get("estado_nuevo") == "Aprobada"
)

rechazos = sum(
    1
    for evento in eventos
    if evento.get("estado_nuevo") == "Rechazada"
)


columna_1, columna_2, columna_3, columna_4 = st.columns(4)

with columna_1:
    st.metric(
        "Eventos",
        total_eventos,
    )

with columna_2:
    st.metric(
        "Envíos",
        envios,
    )

with columna_3:
    st.metric(
        "Aprobaciones",
        aprobaciones,
    )

with columna_4:
    st.metric(
        "Rechazos",
        rechazos,
    )


st.divider()


if not eventos:
    st.info(
        "Todavía no existen eventos de trazabilidad."
    )
    st.stop()


# =========================================================
# FILTROS
# =========================================================

rendiciones_disponibles = sorted(
    {
        evento["rendicion_id"]
        for evento in eventos
        if evento.get("rendicion_id") is not None
    }
)

acciones_disponibles = sorted(
    {
        evento["accion"]
        for evento in eventos
        if evento.get("accion")
    }
)


columna_filtro_1, columna_filtro_2 = st.columns(2)

with columna_filtro_1:
    filtro_rendicion = st.selectbox(
        "Filtrar por rendición",
        ["Todas"]
        + [
            f"Rendición #{rendicion_id}"
            for rendicion_id in rendiciones_disponibles
        ],
    )

with columna_filtro_2:
    filtro_accion = st.selectbox(
        "Filtrar por acción",
        ["Todas"] + acciones_disponibles,
    )


eventos_filtrados = eventos

if filtro_rendicion != "Todas":
    rendicion_id_seleccionada = int(
        filtro_rendicion.replace("Rendición #", "")
    )

    eventos_filtrados = [
        evento
        for evento in eventos_filtrados
        if evento.get("rendicion_id")
        == rendicion_id_seleccionada
    ]

if filtro_accion != "Todas":
    eventos_filtrados = [
        evento
        for evento in eventos_filtrados
        if evento.get("accion") == filtro_accion
    ]


if not eventos_filtrados:
    st.warning(
        "No existen eventos que coincidan con los filtros."
    )
    st.stop()


# =========================================================
# HISTORIAL
# =========================================================

for evento in eventos_filtrados:
    usuario = evento.get("usuario") or {}
    rendicion = evento.get("rendicion") or {}

    nombre_usuario = usuario.get(
        "nombre",
        "Usuario no disponible",
    )

    rol_usuario = usuario.get(
        "rol",
        "sin rol",
    ).capitalize()

    proveedor = rendicion.get(
        "proveedor",
        "Proveedor no disponible",
    )

    folio = rendicion.get(
        "folio",
        "Sin folio",
    )

    titulo = (
        f"{formatear_fecha(evento['fecha_accion'])} · "
        f"Rendición #{evento.get('rendicion_id')} · "
        f"{evento['accion']}"
    )

    with st.expander(titulo):
        columna_evento_1, columna_evento_2 = st.columns(2)

        with columna_evento_1:
            st.write(
                f"**Acción:** {evento['accion']}"
            )

            st.write(
                f"**Transición:** "
                f"{etiqueta_transicion(evento)}"
            )

            st.write(
                f"**Fecha:** "
                f"{formatear_fecha(evento['fecha_accion'])}"
            )

            st.write(
                f"**Usuario responsable:** {nombre_usuario}"
            )

            st.write(
                f"**Rol:** {rol_usuario}"
            )

        with columna_evento_2:
            st.write(
                f"**Rendición:** "
                f"#{evento.get('rendicion_id')}"
            )

            st.write(
                f"**Proveedor:** {proveedor}"
            )

            st.write(
                f"**Folio:** {folio}"
            )

            st.write(
                f"**Tipo:** "
                f"{rendicion.get('tipo_documento', 'Sin información')}"
            )

            st.write(
                f"**Monto total:** "
                f"{formatear_moneda(rendicion.get('monto_total'))}"
            )

            st.write(
                f"**Estado actual:** "
                f"{rendicion.get('estado', 'Sin información')}"
            )

        detalle = evento.get("detalle")

        if detalle:
            st.info(
                f"**Detalle:** {detalle}"
            )

        estado_nuevo = evento.get("estado_nuevo")

        if estado_nuevo == "Aprobada":
            st.success(
                "Resultado final: rendición aprobada."
            )

        elif estado_nuevo == "Rechazada":
            st.error(
                "Resultado final: rendición rechazada."
            )

        elif estado_nuevo == "Pendiente":
            st.warning(
                "La rendición fue enviada a revisión."
            )


st.divider()

st.caption(
    "El historial registra usuario, rol, fecha, acción, "
    "transición de estado y detalle asociado."
)