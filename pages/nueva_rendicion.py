from datetime import date

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    buscar_documento_duplicado,
    crear_rendicion,
    obtener_configuracion_empresa,
    registrar_auditoria,
    subir_comprobante,
)
from reglas import evaluar_reglas_locales


st.set_page_config(
    page_title="Nueva rendición",
    page_icon="🧾",
    layout="wide",
)


# Solo trabajadores autenticados pueden acceder.
exigir_rol(["trabajador"])
mostrar_sidebar_usuario()


st.title("🧾 Nueva rendición")
st.write(
    "Registra los datos del documento y adjunta el comprobante."
)


empresa_id = st.session_state["empresa_id"]
usuario_id = st.session_state["usuario_id"]


# Obtener parámetros de la empresa desde Supabase.
configuracion = obtener_configuracion_empresa(empresa_id)

if configuracion is None:
    st.error(
        "No fue posible obtener la configuración de la empresa."
    )
    st.stop()


limite_rendicion = float(
    configuracion["limite_rendicion"]
)

dias_maximos = int(
    configuracion["dias_maximos_documento"]
)


with st.expander("Parámetros aplicados"):
    nombre_empresa = (
        configuracion.get("nombre_fantasia")
        or configuracion["razon_social"]
    )

    st.write(
        f"**Empresa:** {nombre_empresa}"
    )

    st.write(
        f"**Límite de rendición:** "
        f"${limite_rendicion:,.0f}"
    )

    st.write(
        f"**Antigüedad máxima del documento:** "
        f"{dias_maximos} días"
    )


# =========================================================
# FORMULARIO DE RENDICIÓN
# =========================================================

with st.form(
    "formulario_rendicion",
    clear_on_submit=False,
):
    st.subheader("Datos del documento")

    columna_1, columna_2 = st.columns(2)

    with columna_1:
        tipo_documento = st.selectbox(
            "Tipo de documento *",
            [
                "Boleta",
                "Factura",
                "Comprobante",
                "Otro",
            ],
        )

        rut_emisor = st.text_input(
            "RUT del emisor *",
            placeholder="76.123.456-7",
        )

        proveedor = st.text_input(
            "Proveedor *",
            placeholder="Nombre del proveedor",
        )

        folio = st.text_input(
            "Folio *",
            placeholder="Número de documento",
        )

    with columna_2:
        fecha_documento = st.date_input(
            "Fecha del documento *",
            value=date.today(),
        )

        categoria = st.selectbox(
            "Categoría *",
            [
                "Alimentación",
                "Transporte",
                "Alojamiento",
                "Materiales",
                "Servicios",
                "Combustible",
                "Otro",
            ],
        )

        descripcion = st.text_area(
            "Descripción",
            placeholder="Describe el motivo del gasto",
            max_chars=500,
        )

    st.subheader("Montos")

    monto_1, monto_2, monto_3 = st.columns(3)

    with monto_1:
        monto_neto = st.number_input(
            "Monto neto",
            min_value=0,
            step=100,
            format="%d",
        )

    with monto_2:
        iva = st.number_input(
            "IVA",
            min_value=0,
            step=100,
            format="%d",
        )

    with monto_3:
        monto_total = st.number_input(
            "Monto total *",
            min_value=0,
            step=100,
            format="%d",
        )

    calcular_total = st.checkbox(
        "Calcular total automáticamente como Neto + IVA"
    )

    archivo = st.file_uploader(
        "Documento de respaldo *",
        type=["jpg", "jpeg", "png", "webp", "pdf"],
        help="Tamaño máximo permitido: 5 MB.",
    )

    aceptacion = st.checkbox(
        "Confirmo que los datos utilizados son demostrativos "
        "y no contienen información tributaria real."
    )

    enviar = st.form_submit_button(
        "Evaluar y enviar a revisión",
        type="primary",
        use_container_width=True,
    )


# =========================================================
# EVALUACIÓN Y ENVÍO
# =========================================================

if enviar:
    # Calcula el total cuando el usuario marca la opción.
    if calcular_total:
        monto_total = monto_neto + iva

    datos_evaluacion = {
        "tipo_documento": tipo_documento,
        "rut_emisor": rut_emisor.strip(),
        "proveedor": proveedor.strip(),
        "folio": folio.strip(),
        "fecha_documento": fecha_documento,
        "categoria": categoria,
        "monto_total": float(monto_total),
    }

    # Ejecutar reglas locales R2, R3, R4 y R5.
    evaluacion = evaluar_reglas_locales(
        datos=datos_evaluacion,
        limite=limite_rendicion,
        dias_maximos=dias_maximos,
        archivo_cargado=archivo is not None,
    )

    # Ejecutar R1 consultando documentos existentes en Supabase.
    duplicado = None

    if (
        rut_emisor.strip()
        and folio.strip()
        and tipo_documento
    ):
        duplicado = buscar_documento_duplicado(
            empresa_id=empresa_id,
            rut_emisor=rut_emisor.strip(),
            tipo_documento=tipo_documento,
            folio=folio.strip(),
        )

    if duplicado:
        evaluacion["alertas"].append(
            {
                "codigo": "R1",
                "nivel": "Alto",
                "mensaje": (
                    "Existe otra rendición con el mismo RUT, "
                    "tipo de documento y folio. "
                    f"Rendición encontrada: #{duplicado['id']}."
                ),
            }
        )

        evaluacion["nivel_riesgo"] = "Alto"

    # Mostrar resultados.
    st.subheader("Resultado de la evaluación")

    if evaluacion["alertas"]:
        for alerta in evaluacion["alertas"]:
            mensaje = (
                f"**{alerta['codigo']} - "
                f"Riesgo {alerta['nivel']}:** "
                f"{alerta['mensaje']}"
            )

            if alerta["nivel"] == "Alto":
                st.error(mensaje)
            else:
                st.warning(mensaje)

    else:
        st.success(
            "No se detectaron alertas en la evaluación."
        )

    # Validación de datos demostrativos.
    if not aceptacion:
        st.error(
            "Debes confirmar que estás utilizando "
            "datos exclusivamente demostrativos."
        )
        st.stop()

    # R4 o R5 impiden el envío.
    if not evaluacion["puede_enviar"]:
        st.error(
            "La rendición no puede enviarse hasta corregir "
            "las alertas obligatorias R4 o R5."
        )
        st.stop()

    # Si existe duplicado, se advierte pero se permite registrar
    # para que el administrador pueda revisarlo.
    if duplicado:
        st.warning(
            "La rendición será enviada con riesgo alto debido "
            "a la posible duplicidad detectada."
        )

    try:
        with st.spinner(
            "Guardando comprobante y rendición..."
        ):
            # Cargar archivo en Supabase Storage.
            ruta_archivo = subir_comprobante(
                archivo=archivo,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )

            reglas_activadas = [
                alerta["codigo"]
                for alerta in evaluacion["alertas"]
            ]

            # Crear rendición.
            # fecha_envio NO se envía desde Python.
            # Supabase la completa automáticamente con now().
            nueva_rendicion = crear_rendicion(
                {
                    "empresa_id": empresa_id,
                    "usuario_id": usuario_id,
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
                    "estado": "Pendiente",
                    "nivel_riesgo": evaluacion[
                        "nivel_riesgo"
                    ],
                    "reglas_activadas": reglas_activadas,
                }
            )

            # Registrar auditoría.
            registrar_auditoria(
                empresa_id=empresa_id,
                rendicion_id=nueva_rendicion["id"],
                usuario_id=usuario_id,
                accion="Envío de rendición",
                estado_anterior="Borrador",
                estado_nuevo="Pendiente",
                detalle=(
                    "La rendición fue creada y enviada "
                    "a revisión administrativa."
                ),
            )

        st.success(
            f"Rendición #{nueva_rendicion['id']} "
            "enviada correctamente."
        )

        st.page_link(
            "pages/mis_rendiciones.py",
            label="Ver mis rendiciones",
            icon="📋",
        )

    except Exception as error:
        st.error(
            "No fue posible guardar la rendición."
        )

        st.code(str(error))