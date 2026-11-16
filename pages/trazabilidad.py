import csv
import html
import io

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import listar_auditoria_empresa
from ui import (
    badge_estado,
    encabezado,
    formatear_fecha,
    formatear_moneda,
    kpis,
    pie_pagina,
)


exigir_rol(["administrador"])
mostrar_sidebar_usuario()

encabezado(
    "🔎",
    "Trazabilidad",
    "Historial de acciones sobre las rendiciones: quién, cuándo y qué cambió.",
)

empresa_id = st.session_state["empresa_id"]


def transicion(evento: dict) -> str:
    anterior = evento.get("estado_anterior")
    nuevo = evento.get("estado_nuevo")

    if anterior and nuevo:
        return f"{anterior} → {nuevo}"

    return nuevo or "Sin cambio de estado"


# =========================================================
# CONSULTA
# =========================================================

try:
    eventos = listar_auditoria_empresa(empresa_id=empresa_id)

except Exception as error:
    st.error("No fue posible consultar el historial de trazabilidad.")
    st.code(str(error))
    st.stop()

nuevos = [evento.get("estado_nuevo") for evento in eventos]

kpis(
    [
        ("Eventos", len(eventos)),
        ("Envíos", nuevos.count("Pendiente")),
        ("Aprobaciones", nuevos.count("Aprobada")),
        ("Rechazos", nuevos.count("Rechazada")),
    ]
)

st.write("")

if not eventos:
    st.info("Todavía no existen eventos de trazabilidad.", icon="📭")
    pie_pagina()
    st.stop()


# =========================================================
# FILTROS
# =========================================================

rendiciones_ids = sorted(
    {e["rendicion_id"] for e in eventos if e.get("rendicion_id") is not None},
    reverse=True,
)
acciones = sorted({e["accion"] for e in eventos if e.get("accion")})

filtro_1, filtro_2 = st.columns(2)

with filtro_1:
    filtro_rendicion = st.selectbox(
        "Rendición",
        ["Todas"] + [f"#{rendicion_id}" for rendicion_id in rendiciones_ids],
    )

with filtro_2:
    filtro_accion = st.selectbox("Acción", ["Todas"] + acciones)

eventos_filtrados = [
    evento
    for evento in eventos
    if (filtro_rendicion == "Todas" or f"#{evento.get('rendicion_id')}" == filtro_rendicion)
    and (filtro_accion == "Todas" or evento.get("accion") == filtro_accion)
]

if not eventos_filtrados:
    st.warning("No existen eventos que coincidan con los filtros.")
    st.stop()


# =========================================================
# VISTAS
# =========================================================

vista_linea, vista_tabla = st.tabs(["🕒 Línea de tiempo", "📄 Tabla"])

with vista_linea:
    # Agrupa los eventos por rendición y los muestra en orden cronológico.
    por_rendicion: dict = {}

    for evento in eventos_filtrados:
        por_rendicion.setdefault(evento.get("rendicion_id"), []).append(evento)

    for rendicion_id, eventos_rendicion in por_rendicion.items():
        rendicion = eventos_rendicion[0].get("rendicion") or {}

        with st.container(border=True):
            cabecera, estado = st.columns([3, 1])

            with cabecera:
                st.markdown(
                    f"**Rendición #{rendicion_id}** · "
                    f"{rendicion.get('proveedor', 'Proveedor no disponible')} · "
                    f"Folio {rendicion.get('folio', '—')} · "
                    f"{formatear_moneda(rendicion.get('monto_total'))}"
                )

            with estado:
                if rendicion.get("estado"):
                    st.markdown(badge_estado(rendicion["estado"]), unsafe_allow_html=True)

            for evento in sorted(eventos_rendicion, key=lambda e: e["fecha_accion"]):
                usuario = evento.get("usuario") or {}
                responsable = usuario.get("nombre", "Usuario no disponible")
                rol = str(usuario.get("rol", "sin rol")).capitalize()

                st.markdown(
                    f"""
                    <div class="pg-evento">
                        <b>{html.escape(evento['accion'])}</b>
                        · {html.escape(transicion(evento))}<br>
                        <small>{formatear_fecha(evento['fecha_accion'])} ·
                        {html.escape(responsable)} ({html.escape(rol)})</small><br>
                        <small>{html.escape(evento.get('detalle') or '')}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

with vista_tabla:
    filas = [
        {
            "Fecha": formatear_fecha(evento["fecha_accion"]),
            "Rendición": f"#{evento.get('rendicion_id')}",
            "Acción": evento["accion"],
            "Transición": transicion(evento),
            "Responsable": (evento.get("usuario") or {}).get("nombre", ""),
            "Rol": str((evento.get("usuario") or {}).get("rol", "")).capitalize(),
            "Detalle": evento.get("detalle") or "",
        }
        for evento in eventos_filtrados
    ]

    st.dataframe(filas, hide_index=True, use_container_width=True)

    # Exportación simple del historial filtrado.
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=list(filas[0].keys()), delimiter=";")
    escritor.writeheader()
    escritor.writerows(filas)

    st.download_button(
        "⬇️ Descargar historial (CSV)",
        data=salida.getvalue().encode("utf-8-sig"),
        file_name="trazabilidad_pymegestiona.csv",
        mime="text/csv",
    )


pie_pagina()