from datetime import datetime

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    generar_url_comprobante,
    listar_rendiciones_pendientes,
    resolver_rendicion,
)


st.set_page_config(
    page_title="Revisión administrativa",
    page_icon="✅",
    layout="wide",
)

exigir_rol(["administrador"])
mostrar_sidebar_usuario()

st.title("✅ Revisión administrativa")

st.write(
    "Consulta las rendiciones pendientes, revisa los datos "
    "y registra una decisión administrativa."
)


empresa_id = st.session_state["empresa_id"]
administrador_id = st.session_state["usuario_id"]


def formatear_moneda(valor) -> str:
    """
    Convierte un valor al formato monetario chileno.
    """
    try:
        numero = float(valor)
        return f"${numero:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def formatear_fecha(valor) -> str:
    """
    Convierte una fecha ISO de Supabase a un formato legible.
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
    rendiciones = listar_rendiciones_pendientes(
        empresa_id=empresa_id,
    )

except Exception as error:
    st.error(
        "No fue posible consultar las rendiciones pendientes."
    )
    st.code(str(error))
    st.stop()


# =========================================================
# RESUMEN
# =========================================================

st.metric(
    "Rendiciones pendientes",
    len(rendiciones),
)

st.divider()


if not rendiciones:
    st.success(
        "No existen rendiciones pendientes de revisión."
    )
    st.stop()


# =========================================================
# LISTADO
# =========================================================

for rendicion in rendiciones:
    titulo = (
        f"Rendición #{rendicion['id']} · "
        f"{rendicion['proveedor']} · "
        f"{formatear_moneda(rendicion['monto_total'])} · "
        f"Riesgo {rendicion['nivel_riesgo']}"
    )

    with st.expander(titulo):
        detalle_1, detalle_2 = st.columns(2)

        with detalle_1:
            st.write(
                f"**Trabajador ID:** "
                f"{rendicion['usuario_id']}"
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
                f"**Proveedor:** "
                f"{rendicion['proveedor']}"
            )

            st.write(
                f"**Folio:** "
                f"{rendicion['folio']}"
            )

            st.write(
                f"**Categoría:** "
                f"{rendicion['categoria']}"
            )

        with detalle_2:
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
                f"**Estado:** "
                f"{rendicion['estado']}"
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

        # =================================================
        # RESULTADO DE RIESGO
        # =================================================

        nivel_riesgo = rendicion["nivel_riesgo"]

        if nivel_riesgo == "Alto":
            st.error(
                f"Nivel de riesgo: {nivel_riesgo}"
            )

        elif nivel_riesgo == "Medio":
            st.warning(
                f"Nivel de riesgo: {nivel_riesgo}"
            )

        else:
            st.success(
                f"Nivel de riesgo: {nivel_riesgo}"
            )

        reglas = rendicion.get("reglas_activadas") or []

        if reglas:
            st.warning(
                "**Reglas activadas:** "
                + ", ".join(reglas)
            )

        else:
            st.info(
                "La rendición no presenta reglas activadas."
            )

        # =================================================
        # VALIDACIÓN DE MONTOS
        # =================================================

        try:
            neto = float(rendicion["monto_neto"])
            iva = float(rendicion["iva"])
            total = float(rendicion["monto_total"])

            diferencia = abs((neto + iva) - total)

            if diferencia > 0:
                st.warning(
                    "Los montos presentan una diferencia: "
                    f"Neto + IVA corresponde a "
                    f"{formatear_moneda(neto + iva)}, "
                    f"pero el total informado es "
                    f"{formatear_moneda(total)}."
                )

            else:
                st.success(
                    "Los montos neto, IVA y total son consistentes."
                )

        except (TypeError, ValueError):
            st.warning(
                "No fue posible comprobar la consistencia "
                "de los montos."
            )

        # =================================================
        # COMPROBANTE
        # =================================================

        ruta_archivo = rendicion.get("archivo_url")

        if ruta_archivo:
            try:
                url_comprobante = generar_url_comprobante(
                    ruta_archivo=ruta_archivo,
                    duracion_segundos=600,
                )

                if url_comprobante:
                    st.link_button(
                        "📎 Abrir comprobante",
                        url_comprobante,
                        use_container_width=True,
                    )

                    st.caption(
                        "El enlace del comprobante será válido "
                        "durante 10 minutos."
                    )

                else:
                    st.warning(
                        "No fue posible generar el enlace "
                        "del comprobante."
                    )

            except Exception:
                st.warning(
                    "El comprobante existe, pero no fue posible "
                    "generar su enlace temporal."
                )

        else:
            st.error(
                "La rendición no tiene un comprobante asociado."
            )

        st.divider()

        # =================================================
        # DECISIÓN
        # =================================================

        with st.form(
            f"decision_rendicion_{rendicion['id']}"
        ):
            st.subheader("Decisión administrativa")

            decision = st.radio(
                "Selecciona una decisión",
                [
                    "Aprobar",
                    "Rechazar",
                ],
                horizontal=True,
                key=f"decision_{rendicion['id']}",
            )

            motivo_rechazo = st.text_area(
                "Motivo del rechazo",
                placeholder=(
                    "Este campo es obligatorio si seleccionas "
                    "Rechazar."
                ),
                max_chars=500,
                key=f"motivo_{rendicion['id']}",
            )

            confirmar = st.checkbox(
                "Confirmo que revisé los datos y el comprobante.",
                key=f"confirmacion_{rendicion['id']}",
            )

            guardar_decision = st.form_submit_button(
                "Guardar decisión",
                type="primary",
                use_container_width=True,
            )

        if guardar_decision:
            if not confirmar:
                st.error(
                    "Debes confirmar que revisaste "
                    "la rendición y el comprobante."
                )

            elif (
                decision == "Rechazar"
                and not motivo_rechazo.strip()
            ):
                st.error(
                    "Debes indicar el motivo del rechazo."
                )

            else:
                nuevo_estado = (
                    "Aprobada"
                    if decision == "Aprobar"
                    else "Rechazada"
                )

                try:
                    with st.spinner(
                        "Guardando la decisión..."
                    ):
                        resolver_rendicion(
                            rendicion_id=rendicion["id"],
                            empresa_id=empresa_id,
                            administrador_id=administrador_id,
                            nuevo_estado=nuevo_estado,
                            motivo_rechazo=motivo_rechazo,
                        )

                    st.success(
                        f"Rendición #{rendicion['id']} "
                        f"{nuevo_estado.lower()} correctamente."
                    )

                    st.rerun()

                except Exception as error:
                    st.error(
                        "No fue posible guardar la decisión."
                    )

                    st.code(str(error))