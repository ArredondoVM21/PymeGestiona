import html

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    generar_url_comprobante,
    listar_rendiciones_pendientes,
    resolver_rendicion,
)
from ui import (
    badge_estado,
    badge_validacion,
    checklist_codigos,
    encabezado,
    ficha,
    formatear_fecha,
    formatear_moneda,
    kpis,
    mostrar_badges,
    pie_pagina,
)


exigir_rol(["administrador"])
mostrar_sidebar_usuario()

encabezado(
    "✅",
    "Revisión de rendiciones",
    "Rendiciones pendientes o reenviadas. Abre una para ver el comprobante y decidir.",
)

empresa_id = st.session_state["empresa_id"]
administrador_id = st.session_state["usuario_id"]

EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".webp")

MOTIVOS_FRECUENTES = [
    "El comprobante no se lee con claridad.",
    "El monto no coincide con el comprobante.",
    "El gasto no corresponde a una actividad de la empresa.",
    "Falta la factura a nombre de la empresa.",
]

# Ventana emergente: st.dialog en versiones nuevas,
# st.experimental_dialog en algunas anteriores.
DIALOGO = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)

# Mensaje guardado antes de st.rerun() para que no se pierda.
if "mensaje_exito" in st.session_state:
    st.success(st.session_state.pop("mensaje_exito"), icon="✅")


def validacion(rendicion: dict) -> str:
    """
    Cumple = sin reglas activadas. En riesgo = con alertas
    (las bloqueantes nunca llegan a esta bandeja).
    """
    return "riesgo" if rendicion.get("reglas_activadas") else "cumple"


def nombre_trabajador(rendicion: dict) -> str:
    trabajador = rendicion.get("trabajador") or {}
    return trabajador.get("nombre", f"Usuario #{rendicion['usuario_id']}")


# =========================================================
# PANEL DE REVISIÓN (se abre en la ventana emergente)
# =========================================================

def panel_revision(rendicion: dict) -> None:
    rid = rendicion["id"]

    mostrar_badges(
        badge_validacion(validacion(rendicion)),
        badge_estado(rendicion["estado"]),
    )

    if rendicion["estado"] == "Reenviada":
        st.info("El trabajador corrigió esta rendición después de un rechazo.", icon="🔁")

    columna_comprobante, columna_datos = st.columns([1, 1.3])

    with columna_comprobante:
        ruta_archivo = rendicion.get("archivo_url")

        if not ruta_archivo:
            st.error("Sin comprobante adjunto.")

        else:
            try:
                url = generar_url_comprobante(ruta_archivo, 600)

                if url and ruta_archivo.lower().endswith(EXTENSIONES_IMAGEN):
                    st.image(url)

                if url:
                    st.link_button("📎 Abrir comprobante", url, use_container_width=True)

            except Exception:
                st.warning("No fue posible abrir el comprobante.")

    with columna_datos:
        ficha(
            [
                ("Trabajador", nombre_trabajador(rendicion)),
                ("Enviada", formatear_fecha(rendicion["fecha_envio"])),
                ("Documento", f"{rendicion['tipo_documento']} N° {rendicion['folio']}"),
                ("Fecha", formatear_fecha(rendicion["fecha_documento"], con_hora=False)),
                ("RUT emisor", rendicion["rut_emisor"]),
                ("Categoría", rendicion["categoria"]),
                ("Neto", formatear_moneda(rendicion["monto_neto"])),
                ("IVA", formatear_moneda(rendicion["iva"])),
            ]
        )
        st.metric("Total", formatear_moneda(rendicion["monto_total"]))

        if rendicion.get("descripcion"):
            st.caption(f"📝 {rendicion['descripcion']}")

    st.markdown("##### Validación R1–R6")
    checklist_codigos(rendicion.get("reglas_activadas") or [])

    st.divider()
    st.markdown("##### Decisión")

    decision = st.radio(
        "Decisión",
        ["✅ Aprobar", "❌ Rechazar"],
        index=None,
        horizontal=True,
        label_visibility="collapsed",
        key=f"decision_{rid}",
    )

    motivo = ""

    if decision == "❌ Rechazar":
        sugerido = st.selectbox(
            "Motivo frecuente (opcional)",
            MOTIVOS_FRECUENTES,
            index=None,
            placeholder="Elige uno o escribe el tuyo abajo",
            key=f"sugerido_{rid}",
        )

        detalle = st.text_area(
            "Motivo del rechazo",
            max_chars=500,
            placeholder="Explica qué debe corregir el trabajador.",
            key=f"motivo_{rid}",
        )

        motivo = " ".join(parte for parte in [sugerido or "", detalle.strip()] if parte)

        if len(motivo) < 10:
            st.caption(":red[El motivo es obligatorio (mínimo 10 caracteres).]")

    confirmar = st.checkbox(
        "Revisé los datos y el comprobante.",
        key=f"confirmar_{rid}",
    )

    puede_guardar = (
        confirmar
        and decision is not None
        and (decision == "✅ Aprobar" or len(motivo) >= 10)
    )

    etiqueta = (
        "Elige una decisión" if decision is None
        else f"Aprobar {formatear_moneda(rendicion['monto_total'])}" if decision == "✅ Aprobar"
        else "Rechazar con motivo"
    )

    if st.button(etiqueta, type="primary", use_container_width=True, disabled=not puede_guardar, key=f"guardar_{rid}"):
        nuevo_estado = "Aprobada" if decision == "✅ Aprobar" else "Rechazada"
        guardado = False

        try:
            resolver_rendicion(
                rendicion_id=rid,
                empresa_id=empresa_id,
                administrador_id=administrador_id,
                nuevo_estado=nuevo_estado,
                motivo_rechazo=motivo,
            )
            guardado = True

        except Exception as error:
            st.error("No fue posible guardar la decisión.")
            st.code(str(error))

        # st.rerun() fuera del try: cierra la ventana y recarga la bandeja.
        if guardado:
            st.session_state["mensaje_exito"] = f"Rendición #{rid} {nuevo_estado.lower()}."
            st.session_state.pop("revisando", None)
            st.rerun()


def abrir_revision(rendicion: dict) -> None:
    if DIALOGO is not None:
        DIALOGO(f"Rendición #{rendicion['id']} · {rendicion['proveedor']}", width="large")(panel_revision)(rendicion)

    else:
        # Respaldo para versiones sin ventanas emergentes.
        st.session_state["revisando"] = rendicion["id"]
        st.rerun()


# =========================================================
# CONSULTA E INDICADORES
# =========================================================

try:
    rendiciones = listar_rendiciones_pendientes(empresa_id=empresa_id)

except Exception as error:
    st.error("No fue posible consultar las rendiciones.")
    st.code(str(error))
    st.stop()

en_riesgo = [r for r in rendiciones if validacion(r) == "riesgo"]

kpis(
    [
        ("Por revisar", len(rendiciones), "Pendientes y reenviadas"),
        ("Cumplen", len(rendiciones) - len(en_riesgo), "Sin alertas", "verde"),
        ("En riesgo", len(en_riesgo), "Con alertas R2 o R3", "ambar"),
        ("Monto por revisar", formatear_moneda(sum(float(r["monto_total"] or 0) for r in rendiciones)), "Total pendiente"),
    ]
)

if not rendiciones:
    st.success("No hay rendiciones pendientes. ¡Todo al día!", icon="🎉")
    pie_pagina()
    st.stop()


# Respaldo sin ventanas emergentes: el panel se muestra arriba de la lista.
if DIALOGO is None and st.session_state.get("revisando"):
    seleccionada = next((r for r in rendiciones if r["id"] == st.session_state["revisando"]), None)

    if seleccionada:
        with st.container(border=True):
            if st.button("✕ Cerrar revisión"):
                st.session_state.pop("revisando", None)
                st.rerun()

            panel_revision(seleccionada)


# =========================================================
# FILTROS Y ORDEN
# =========================================================

filtro_1, filtro_2 = st.columns([1.3, 1])

with filtro_1:
    filtro = st.radio(
        "Mostrar",
        [
            f"Todas ({len(rendiciones)})",
            f"Cumple ({len(rendiciones) - len(en_riesgo)})",
            f"En riesgo ({len(en_riesgo)})",
        ],
        horizontal=True,
    )

with filtro_2:
    orden = st.selectbox(
        "Ordenar por",
        ["Más antiguas primero", "En riesgo primero", "Mayor monto primero"],
    )

if filtro.startswith("Cumple"):
    rendiciones = [r for r in rendiciones if validacion(r) == "cumple"]

elif filtro.startswith("En riesgo"):
    rendiciones = en_riesgo

if orden == "En riesgo primero":
    rendiciones = sorted(rendiciones, key=lambda r: validacion(r) != "riesgo")

elif orden == "Mayor monto primero":
    rendiciones = sorted(rendiciones, key=lambda r: float(r["monto_total"] or 0), reverse=True)

if not rendiciones:
    st.info("No hay rendiciones con este filtro.")


# =========================================================
# BANDEJA
# =========================================================

for rendicion in rendiciones:
    with st.container(border=True):
        columna_info, columna_monto, columna_accion = st.columns([3, 1.6, 1])

        with columna_info:
            reglas = rendicion.get("reglas_activadas") or []
            st.markdown(
                f'<div class="pg-fila"><b>#{rendicion["id"]} · {html.escape(rendicion["proveedor"])}</b><br>'
                f"<small>{html.escape(nombre_trabajador(rendicion))} · "
                f"{html.escape(rendicion['tipo_documento'])} N° {html.escape(str(rendicion['folio']))} · "
                f"{formatear_fecha(rendicion['fecha_documento'], con_hora=False)}"
                f"{' · 🔁 Reenviada' if rendicion['estado'] == 'Reenviada' else ''}"
                f"{' · Reglas: ' + ', '.join(reglas) if reglas else ''}</small></div>",
                unsafe_allow_html=True,
            )

        with columna_monto:
            st.markdown(
                f'<div class="pg-monto">{formatear_moneda(rendicion["monto_total"])}</div>'
                f"{badge_validacion(validacion(rendicion))}",
                unsafe_allow_html=True,
            )

        with columna_accion:
            if st.button("Revisar →", key=f"abrir_{rendicion['id']}", use_container_width=True):
                abrir_revision(rendicion)


st.caption("🟢 Cumple: sin alertas · 🟠 En riesgo: alertas R2 (monto) o R3 (antigüedad) que no bloquean el envío.")

pie_pagina()