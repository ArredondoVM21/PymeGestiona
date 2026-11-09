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
    "Consulta rendiciones pendientes o reenviadas "
    "y registra la decisión administrativa."
)


empresa_id = st.session_state["empresa_id"]
administrador_id = st.session_state["usuario_id"]


def formatear_moneda(valor) -> str:
    try:
        numero = float(valor)
        return f"${numero:,.0f}".replace(",", ".")

    except (TypeError, ValueError):
        return "$0"


def formatear_fecha(valor) -> str:
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
        "No fue posible consultar las rendiciones."
    )

    st.code(str(error))
    st.stop()


st.metric(
    "Rendiciones pendientes o reenviadas",
    len(rendiciones),
)

st.divider()


if not rendiciones:
    st.success(
        "No existen rendiciones pendientes de revisión."
    )
    st.stop()


for rendicion in rendiciones:
    titulo = (
        f"Rendición #{rendicion['id']} · "
        f"{rendicion['proveedor']} · "
        f"{formatear_moneda(rendicion['monto_total'])} · "
        f"{rendicion['estado']}"
    )

    with st.expander(titulo):
        detalle_1, detalle_2 = st.columns(2)

        with detalle_1:
            st.write(
                f"**Trabajador ID:** "
                f"{rendicion['usuario_id']}"
            )

            st.write(
                f"**Tipo:** {rendicion['tipo_documento']}"
            )

            st.write(
                f"**RUT emisor:** {rendicion['rut_emisor']}"
            )

            st.write(
                f"**Proveedor:** {rendicion['proveedor']}"
            )

            st.write(
                f"**Folio:** {rendicion['folio']}"
            )

            st.write(
                f"**Categoría:** {rendicion['categoria']}"
            )

        with detalle_2:
            st.write(
                f"**Estado:** {rendicion['estado']}"
            )

            st.write(
                f"**Fecha documento:** "
                f"{rendicion['fecha_documento']}"
            )

            st.write(
                f"**Neto:** "
                f"{formatear_moneda(rendicion['monto_neto'])}"
            )

            st.write(
                f"**IVA:** "
                f"{formatear_moneda(rendicion['iva'])}"
            )

            st.write(
                f"**Total:** "
                f"{formatear_moneda(rendicion['monto_total'])}"
            )

            st.write(
                f"**Fecha envío:** "
                f"{formatear_fecha(rendicion['fecha_envio'])}"
            )

        if rendicion["estado"] == "Reenviada":
            st.info(
                "Esta rendición fue corregida por el trabajador "
                "después de un rechazo anterior."
            )

        if rendicion.get("descripcion"):
            st.write(
                f"**Descripción:** {rendicion['descripcion']}"
            )

        nivel = rendicion["nivel_riesgo"]

        if nivel == "Alto":
            st.error(f"Nivel de riesgo: {nivel}")

        elif nivel == "Medio":
            st.warning(f"Nivel de riesgo: {nivel}")

        else:
            st.success(f"Nivel de riesgo: {nivel}")

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

        try:
            neto = float(rendicion["monto_neto"])
            iva = float(rendicion["iva"])
            total = float(rendicion["monto_total"])

            if abs((neto + iva) - total) >= 1:
                st.warning(
                    "Los montos no son consistentes. "
                    f"Neto + IVA corresponde a "
                    f"{formatear_moneda(neto + iva)}."
                )

            else:
                st.success(
                    "Los montos neto, IVA y total son consistentes."
                )

        except (TypeError, ValueError):
            st.warning(
                "No fue posible comprobar los montos."
            )

        ruta_archivo = rendicion.get("archivo_url")

        if ruta_archivo:
            try:
                url = generar_url_comprobante(
                    ruta_archivo,
                    600,
                )

                if url:
                    st.link_button(
                        "📎 Abrir comprobante",
                        url,
                        use_container_width=True,
                    )

                    st.caption(
                        "Enlace válido durante 10 minutos."
                    )

            except Exception:
                st.warning(
                    "No fue posible abrir el comprobante."
                )

        else:
            st.error(
                "La rendición no tiene comprobante."
            )

        st.divider()

        with st.form(
            f"decision_{rendicion['id']}"
        ):
            st.subheader("Decisión administrativa")

            decision = st.radio(
                "Selecciona una decisión",
                [
                    "Aprobar",
                    "Rechazar",
                ],
                horizontal=True,
                key=f"decision_radio_{rendicion['id']}",
            )

            motivo = st.text_area(
                "Motivo del rechazo",
                max_chars=500,
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

        if guardar:
            if not confirmar:
                st.error(
                    "Debes confirmar la revisión."
                )

            elif (
                decision == "Rechazar"
                and not motivo.strip()
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
                    resolver_rendicion(
                        rendicion_id=rendicion["id"],
                        empresa_id=empresa_id,
                        administrador_id=administrador_id,
                        nuevo_estado=nuevo_estado,
                        motivo_rechazo=motivo,
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