import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    generar_url_comprobante,
    listar_rendiciones_pendientes,
    resolver_rendicion,
)
from ui import (
    badge_estado,
    badge_riesgo,
    encabezado,
    ficha,
    formatear_fecha,
    formatear_moneda,
    kpis,
    mostrar_badges,
    pie_pagina,
    reglas_activadas,
)


exigir_rol(["administrador"])
mostrar_sidebar_usuario()

encabezado(
    "✅",
    "Revisión administrativa",
    "Revisa las rendiciones pendientes o reenviadas y registra tu decisión.",
)

empresa_id = st.session_state["empresa_id"]
administrador_id = st.session_state["usuario_id"]

EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".webp")
ORDEN_RIESGO = {"Alto": 0, "Medio": 1, "Bajo": 2}

# Mensaje guardado antes de st.rerun() para que no se pierda.
if "mensaje_exito" in st.session_state:
    st.success(st.session_state.pop("mensaje_exito"), icon="✅")


# =========================================================
# CONSULTA
# =========================================================

try:
    rendiciones = listar_rendiciones_pendientes(empresa_id=empresa_id)

except Exception as error:
    st.error("No fue posible consultar las rendiciones.")
    st.code(str(error))
    st.stop()

riesgos = [rendicion["nivel_riesgo"] for rendicion in rendiciones]

kpis(
    [
        ("Por revisar", len(rendiciones)),
        ("Riesgo alto", riesgos.count("Alto")),
        ("Riesgo medio", riesgos.count("Medio")),
        ("Reenviadas", sum(1 for r in rendiciones if r["estado"] == "Reenviada")),
    ]
)

st.write("")

if not rendiciones:
    st.success("No hay rendiciones pendientes de revisión. ¡Todo al día!", icon="🎉")
    pie_pagina()
    st.stop()


# =========================================================
# ORDEN
# =========================================================

orden = st.radio(
    "Ordenar por",
    ["Más antiguas primero", "Mayor riesgo primero", "Mayor monto primero"],
    horizontal=True,
)

if orden == "Mayor riesgo primero":
    rendiciones.sort(key=lambda r: ORDEN_RIESGO.get(r["nivel_riesgo"], 3))

elif orden == "Mayor monto primero":
    rendiciones.sort(key=lambda r: float(r["monto_total"] or 0), reverse=True)


# =========================================================
# LISTADO
# =========================================================

for rendicion in rendiciones:
    trabajador = rendicion.get("trabajador") or {}
    nombre_trabajador = trabajador.get("nombre", f"Usuario #{rendicion['usuario_id']}")

    icono_riesgo = {"Alto": "🔴", "Medio": "🟠", "Bajo": "🟢"}.get(rendicion["nivel_riesgo"], "⚪")

    titulo = (
        f"{icono_riesgo} #{rendicion['id']} · {rendicion['proveedor']} · "
        f"{formatear_moneda(rendicion['monto_total'])} · {nombre_trabajador}"
    )

    with st.expander(titulo):
        mostrar_badges(
            badge_estado(rendicion["estado"]),
            badge_riesgo(rendicion["nivel_riesgo"]),
        )

        if rendicion["estado"] == "Reenviada":
            st.info(
                "El trabajador corrigió esta rendición después de un rechazo anterior.",
                icon="🔁",
            )

        detalle, comprobante = st.columns([1.4, 1])

        with detalle:
            ficha(
                [
                    ("Trabajador", nombre_trabajador),
                    ("Enviada", formatear_fecha(rendicion["fecha_envio"])),
                    ("Tipo", rendicion["tipo_documento"]),
                    ("Fecha del documento", formatear_fecha(rendicion["fecha_documento"], con_hora=False)),
                    ("RUT emisor", rendicion["rut_emisor"]),
                    ("Folio", rendicion["folio"]),
                    ("Proveedor", rendicion["proveedor"]),
                    ("Categoría", rendicion["categoria"]),
                    ("Neto", formatear_moneda(rendicion["monto_neto"])),
                    ("IVA", formatear_moneda(rendicion["iva"])),
                    ("Total", formatear_moneda(rendicion["monto_total"])),
                ]
            )

            if rendicion.get("descripcion"):
                st.caption(f"📝 {rendicion['descripcion']}")

            reglas_activadas(rendicion.get("reglas_activadas") or [])

            try:
                neto = float(rendicion["monto_neto"])
                iva = float(rendicion["iva"])
                total = float(rendicion["monto_total"])

                if abs((neto + iva) - total) >= 1:
                    st.warning(
                        f"Neto + IVA = {formatear_moneda(neto + iva)}, "
                        "distinto del total informado."
                    )

            except (TypeError, ValueError):
                st.warning("No fue posible comprobar los montos.")

        with comprobante:
            ruta_archivo = rendicion.get("archivo_url")

            if not ruta_archivo:
                st.error("La rendición no tiene comprobante.")

            else:
                try:
                    url = generar_url_comprobante(ruta_archivo, 600)

                    if url and ruta_archivo.lower().endswith(EXTENSIONES_IMAGEN):
                        st.image(url, caption="Comprobante")

                    if url:
                        st.link_button("📎 Abrir en otra pestaña", url, use_container_width=True)
                        st.caption("Enlace válido durante 10 minutos.")

                except Exception:
                    st.warning("No fue posible abrir el comprobante.")

        # =================================================
        # DECISIÓN
        # =================================================

        with st.form(f"decision_{rendicion['id']}"):
            st.markdown("#### Decisión administrativa")

            decision = st.radio(
                "Decisión",
                ["Aprobar", "Rechazar"],
                horizontal=True,
                key=f"decision_radio_{rendicion['id']}",
            )

            motivo = st.text_area(
                "Motivo del rechazo (obligatorio si rechazas)",
                max_chars=500,
                placeholder="Ej.: el total no coincide con el comprobante adjunto.",
                key=f"motivo_{rendicion['id']}",
            )

            confirmar = st.checkbox(
                "Confirmo que revisé los datos y el comprobante.",
                key=f"confirmar_{rendicion['id']}",
            )

            guardar = st.form_submit_button(
                "Guardar decisión",
                type="primary",
                use_container_width=True,
            )

        if not guardar:
            continue

        if not confirmar:
            st.error("Debes confirmar la revisión.")

        elif decision == "Rechazar" and not motivo.strip():
            st.error("Debes indicar el motivo del rechazo.")

        else:
            nuevo_estado = "Aprobada" if decision == "Aprobar" else "Rechazada"

            try:
                resolver_rendicion(
                    rendicion_id=rendicion["id"],
                    empresa_id=empresa_id,
                    administrador_id=administrador_id,
                    nuevo_estado=nuevo_estado,
                    motivo_rechazo=motivo,
                )

                st.session_state["mensaje_exito"] = (
                    f"Rendición #{rendicion['id']} {nuevo_estado.lower()} correctamente."
                )
                st.rerun()

            except Exception as error:
                st.error("No fue posible guardar la decisión.")
                st.code(str(error))


pie_pagina()