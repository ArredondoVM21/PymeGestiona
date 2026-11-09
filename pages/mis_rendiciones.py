from datetime import date, datetime

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    actualizar_y_reenviar_rendicion,
    buscar_documento_duplicado_excluyendo,
    listar_rendiciones_usuario,
    obtener_configuracion_empresa,
    subir_comprobante,
)
from reglas import evaluar_reglas_locales


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


def convertir_fecha(valor) -> date:
    try:
        return date.fromisoformat(str(valor)[:10])

    except (ValueError, TypeError):
        return date.today()


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
    if rendicion["estado"] in ["Pendiente", "Reenviada"]
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
    st.metric("Total", total_rendiciones)

with columna_2:
    st.metric("Pendientes", pendientes)

with columna_3:
    st.metric("Aprobadas", aprobadas)

with columna_4:
    st.metric("Rechazadas", rechazadas)


st.divider()


# =========================================================
# FILTROS
# =========================================================

filtro_1, filtro_2 = st.columns(2)

with filtro_1:
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

with filtro_2:
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
# CONFIGURACIÓN PARA CORRECCIONES
# =========================================================

configuracion = obtener_configuracion_empresa(empresa_id)

if configuracion:
    limite_rendicion = float(
        configuracion["limite_rendicion"]
    )

    dias_maximos = int(
        configuracion["dias_maximos_documento"]
    )

else:
    limite_rendicion = 100000
    dias_maximos = 30


categorias = [
    "Alimentación",
    "Transporte",
    "Alojamiento",
    "Materiales",
    "Servicios",
    "Combustible",
    "Otro",
]

tipos_documento = [
    "Boleta",
    "Factura",
    "Comprobante",
    "Otro",
]


# =========================================================
# LISTADO
# =========================================================

for rendicion in rendiciones_filtradas:
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
                f"**Estado:** {rendicion['estado']}"
            )

            st.write(
                f"**Nivel de riesgo:** "
                f"{rendicion['nivel_riesgo']}"
            )

            st.write(
                f"**Tipo:** {rendicion['tipo_documento']}"
            )

            st.write(
                f"**RUT emisor:** {rendicion['rut_emisor']}"
            )

            st.write(
                f"**Folio:** {rendicion['folio']}"
            )

            st.write(
                f"**Categoría:** {rendicion['categoria']}"
            )

        with detalle_2:
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
                f"**Fecha de envío:** "
                f"{formatear_fecha(rendicion['fecha_envio'])}"
            )

        if rendicion.get("descripcion"):
            st.write(
                f"**Descripción:** {rendicion['descripcion']}"
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

        # =================================================
        # CORREGIR Y REENVIAR
        # =================================================

        if rendicion["estado"] == "Rechazada":
            st.divider()
            st.subheader("✏️ Corregir y reenviar")

            st.info(
                "Corrige los datos observados por el administrador. "
                "El sistema volverá a ejecutar R1-R6."
            )

            tipo_actual = rendicion["tipo_documento"]

            indice_tipo = (
                tipos_documento.index(tipo_actual)
                if tipo_actual in tipos_documento
                else 0
            )

            categoria_actual = rendicion["categoria"]

            indice_categoria = (
                categorias.index(categoria_actual)
                if categoria_actual in categorias
                else 0
            )

            with st.form(
                f"corregir_{rendicion['id']}"
            ):
                correccion_1, correccion_2 = st.columns(2)

                with correccion_1:
                    tipo_documento = st.selectbox(
                        "Tipo de documento",
                        tipos_documento,
                        index=indice_tipo,
                        key=f"tipo_{rendicion['id']}",
                    )

                    rut_emisor = st.text_input(
                        "RUT del emisor",
                        value=rendicion["rut_emisor"],
                        key=f"rut_{rendicion['id']}",
                    )

                    proveedor = st.text_input(
                        "Proveedor",
                        value=rendicion["proveedor"],
                        key=f"proveedor_{rendicion['id']}",
                    )

                    folio = st.text_input(
                        "Folio",
                        value=rendicion["folio"],
                        key=f"folio_{rendicion['id']}",
                    )

                with correccion_2:
                    fecha_documento = st.date_input(
                        "Fecha del documento",
                        value=convertir_fecha(
                            rendicion["fecha_documento"]
                        ),
                        key=f"fecha_{rendicion['id']}",
                    )

                    categoria = st.selectbox(
                        "Categoría",
                        categorias,
                        index=indice_categoria,
                        key=f"categoria_{rendicion['id']}",
                    )

                    descripcion = st.text_area(
                        "Descripción",
                        value=rendicion.get("descripcion") or "",
                        max_chars=500,
                        key=f"descripcion_{rendicion['id']}",
                    )

                monto_1, monto_2, monto_3 = st.columns(3)

                with monto_1:
                    monto_neto = st.number_input(
                        "Monto neto",
                        min_value=0,
                        value=int(
                            float(rendicion["monto_neto"])
                        ),
                        step=100,
                        key=f"neto_{rendicion['id']}",
                    )

                with monto_2:
                    iva = st.number_input(
                        "IVA",
                        min_value=0,
                        value=int(float(rendicion["iva"])),
                        step=100,
                        key=f"iva_{rendicion['id']}",
                    )

                with monto_3:
                    monto_total = st.number_input(
                        "Monto total",
                        min_value=0,
                        value=int(
                            float(rendicion["monto_total"])
                        ),
                        step=100,
                        key=f"total_{rendicion['id']}",
                    )

                calcular_automaticamente = st.checkbox(
                    "Calcular total automáticamente como Neto + IVA",
                    key=f"calcular_{rendicion['id']}",
                )

                archivo_nuevo = st.file_uploader(
                    "Nuevo comprobante opcional",
                    type=[
                        "jpg",
                        "jpeg",
                        "png",
                        "webp",
                        "pdf",
                    ],
                    key=f"archivo_{rendicion['id']}",
                )

                st.caption(
                    "Si no adjuntas un nuevo archivo, se conservará "
                    "el comprobante anterior."
                )

                confirmar = st.checkbox(
                    "Confirmo que revisé y corregí la rendición.",
                    key=f"confirmar_{rendicion['id']}",
                )

                reenviar = st.form_submit_button(
                    "Corregir y reenviar",
                    type="primary",
                    use_container_width=True,
                )

            if reenviar:
                if calcular_automaticamente:
                    monto_total = monto_neto + iva

                datos_evaluacion = {
                    "tipo_documento": tipo_documento,
                    "rut_emisor": rut_emisor.strip(),
                    "proveedor": proveedor.strip(),
                    "folio": folio.strip(),
                    "fecha_documento": fecha_documento,
                    "categoria": categoria,
                    "monto_neto": float(monto_neto),
                    "iva": float(iva),
                    "monto_total": float(monto_total),
                }

                existe_respaldo = bool(
                    archivo_nuevo
                    or rendicion.get("archivo_url")
                )

                evaluacion = evaluar_reglas_locales(
                    datos=datos_evaluacion,
                    limite=limite_rendicion,
                    dias_maximos=dias_maximos,
                    archivo_cargado=existe_respaldo,
                )

                duplicado = (
                    buscar_documento_duplicado_excluyendo(
                        empresa_id=empresa_id,
                        rut_emisor=rut_emisor.strip(),
                        tipo_documento=tipo_documento,
                        folio=folio.strip(),
                        rendicion_excluida_id=rendicion["id"],
                    )
                )

                if duplicado:
                    evaluacion["alertas"].append(
                        {
                            "codigo": "R1",
                            "nivel": "Alto",
                            "mensaje": (
                                "Existe otra rendición con el mismo "
                                "RUT, tipo y folio. "
                                f"Rendición #{duplicado['id']}."
                            ),
                        }
                    )

                    evaluacion["nivel_riesgo"] = "Alto"
                    evaluacion["puede_enviar"] = False

                if not confirmar:
                    st.error(
                        "Debes confirmar que corregiste la rendición."
                    )
                    st.stop()

                if not evaluacion["puede_enviar"]:
                    for alerta in evaluacion["alertas"]:
                        st.error(
                            f"{alerta['codigo']}: "
                            f"{alerta['mensaje']}"
                        )

                    st.error(
                        "No es posible reenviar hasta corregir "
                        "R1, R4, R5 o R6."
                    )
                    st.stop()

                try:
                    ruta_archivo = rendicion.get("archivo_url")

                    if archivo_nuevo:
                        ruta_archivo = subir_comprobante(
                            archivo=archivo_nuevo,
                            empresa_id=empresa_id,
                            usuario_id=usuario_id,
                        )

                    reglas_activadas = [
                        alerta["codigo"]
                        for alerta in evaluacion["alertas"]
                    ]

                    actualizar_y_reenviar_rendicion(
                        rendicion_id=rendicion["id"],
                        empresa_id=empresa_id,
                        usuario_id=usuario_id,
                        datos_actualizados={
                            "tipo_documento": tipo_documento,
                            "rut_emisor": rut_emisor.strip(),
                            "proveedor": proveedor.strip(),
                            "folio": folio.strip(),
                            "fecha_documento": fecha_documento,
                            "categoria": categoria,
                            "descripcion": descripcion.strip(),
                            "monto_neto": float(monto_neto),
                            "iva": float(iva),
                            "monto_total": float(monto_total),
                            "archivo_url": ruta_archivo,
                            "nivel_riesgo": evaluacion[
                                "nivel_riesgo"
                            ],
                            "reglas_activadas": reglas_activadas,
                        },
                    )

                    st.success(
                        f"Rendición #{rendicion['id']} "
                        "corregida y reenviada correctamente."
                    )

                    st.rerun()

                except Exception as error:
                    st.error(
                        "No fue posible corregir y reenviar."
                    )

                    st.code(str(error))


st.divider()

st.page_link(
    "pages/nueva_rendicion.py",
    label="Registrar otra rendición",
    icon="🧾",
)