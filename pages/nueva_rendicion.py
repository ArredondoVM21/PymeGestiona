from datetime import date

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    buscar_documento_duplicado,
    crear_rendicion,
    eliminar_comprobante,
    obtener_configuracion_empresa,
    registrar_auditoria,
    subir_comprobante,
)
from reglas import evaluar_reglas_locales
from ui import (
    checklist_reglas,
    encabezado,
    formatear_moneda,
    pie_pagina,
)


# =========================================================
# SEGURIDAD Y SESIÓN
# =========================================================

exigir_rol(["trabajador"])
mostrar_sidebar_usuario()

encabezado(
    "🧾",
    "Nueva rendición",
    "Registra los datos del documento, adjunta el respaldo y revisa "
    "las reglas antes de enviarlo.",
)

empresa_id = st.session_state["empresa_id"]
usuario_id = st.session_state["usuario_id"]

TASA_IVA = 0.19

TIPOS_DOCUMENTO = ["Boleta", "Factura", "Comprobante", "Otro"]

CATEGORIAS = [
    "Alimentación",
    "Transporte",
    "Alojamiento",
    "Materiales",
    "Servicios",
    "Combustible",
    "Otro",
]


# =========================================================
# CONFIGURACIÓN DE EMPRESA
# =========================================================

configuracion = obtener_configuracion_empresa(empresa_id)

if configuracion is None:
    st.error("No fue posible obtener la configuración de la empresa.")
    st.stop()

limite_rendicion = float(configuracion["limite_rendicion"])
dias_maximos = int(configuracion["dias_maximos_documento"])
nombre_empresa = configuracion.get("nombre_fantasia") or configuracion["razon_social"]

st.info(
    f"**{nombre_empresa}** · Límite por rendición: "
    f"**{formatear_moneda(limite_rendicion)}** · Antigüedad máxima: "
    f"**{dias_maximos} días**",
    icon="🏢",
)


# =========================================================
# PASO 1: DATOS DEL DOCUMENTO
# =========================================================

with st.container(border=True):
    st.markdown("#### 1 · Datos del documento")

    columna_1, columna_2 = st.columns(2)

    with columna_1:
        tipo_documento = st.selectbox("Tipo de documento *", TIPOS_DOCUMENTO)

        rut_emisor = st.text_input(
            "RUT del emisor *",
            placeholder="76.123.456-0",
            help="Se valida el dígito verificador (módulo 11).",
        )

        proveedor = st.text_input("Proveedor *", placeholder="Nombre del proveedor")

        folio = st.text_input("Folio *", placeholder="Número de documento")

    with columna_2:
        fecha_documento = st.date_input(
            "Fecha del documento *",
            value=date.today(),
            format="DD/MM/YYYY",
        )

        categoria = st.selectbox("Categoría *", CATEGORIAS)

        descripcion = st.text_area(
            "Descripción",
            placeholder="Describe el motivo del gasto",
            max_chars=500,
            height=122,
        )


# =========================================================
# PASO 2: MONTOS (SE CALCULAN EN VIVO)
# =========================================================

with st.container(border=True):
    st.markdown("#### 2 · Montos")

    modo_calculo = st.radio(
        "Forma de ingreso",
        ["Calcular IVA (19 %) y total desde el neto", "Ingresar manualmente"],
        horizontal=True,
        label_visibility="collapsed",
    )

    monto_1, monto_2, monto_3 = st.columns(3)

    if modo_calculo.startswith("Calcular"):
        with monto_1:
            monto_neto = st.number_input("Monto neto *", min_value=0, step=100, format="%d")

        iva = round(monto_neto * TASA_IVA)
        monto_total = monto_neto + iva

        with monto_2:
            st.metric("IVA (19 %)", formatear_moneda(iva))

        with monto_3:
            st.metric("Total", formatear_moneda(monto_total))

    else:
        with monto_1:
            monto_neto = st.number_input("Monto neto", min_value=0, step=100, format="%d")

        with monto_2:
            iva = st.number_input("IVA", min_value=0, step=100, format="%d")

        with monto_3:
            monto_total = st.number_input("Monto total *", min_value=0, step=100, format="%d")

        if monto_total and abs((monto_neto + iva) - monto_total) >= 1:
            st.caption(
                f"⚠️ Neto + IVA = {formatear_moneda(monto_neto + iva)}, "
                f"distinto del total informado ({formatear_moneda(monto_total)})."
            )

    if monto_total > limite_rendicion:
        st.caption(
            f"⚠️ El total supera el límite de {formatear_moneda(limite_rendicion)} "
            "(R2). Se puede enviar, pero quedará marcado para revisión."
        )


# =========================================================
# PASO 3: RESPALDO Y CONFIRMACIÓN
# =========================================================

with st.container(border=True):
    st.markdown("#### 3 · Documento de respaldo")

    archivo = st.file_uploader(
        "Comprobante *",
        type=["jpg", "jpeg", "png", "webp", "pdf"],
        help="Formatos JPG, PNG, WEBP o PDF. Tamaño máximo: 5 MB.",
    )

    if archivo is not None and archivo.type.startswith("image/"):
        st.image(archivo, caption="Vista previa del comprobante", width=260)

    aceptacion = st.checkbox(
        "Confirmo que los datos utilizados son demostrativos "
        "y no contienen información tributaria real."
    )


boton_1, boton_2 = st.columns(2)

with boton_1:
    revisar = st.button("🔍 Revisar reglas", use_container_width=True)

with boton_2:
    enviar = st.button("📤 Enviar a revisión", type="primary", use_container_width=True)


# =========================================================
# EVALUACIÓN DE REGLAS
# =========================================================

if revisar or enviar:
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

    evaluacion = evaluar_reglas_locales(
        datos=datos_evaluacion,
        limite=limite_rendicion,
        dias_maximos=dias_maximos,
        archivo_cargado=archivo is not None,
    )

    # R1: documento duplicado (requiere consultar Supabase).
    duplicado = None

    if rut_emisor.strip() and folio.strip():
        duplicado = buscar_documento_duplicado(
            empresa_id=empresa_id,
            rut_emisor=rut_emisor,
            tipo_documento=tipo_documento,
            folio=folio,
        )

    if duplicado:
        evaluacion["alertas"].append(
            {
                "codigo": "R1",
                "nivel": "Alto",
                "mensaje": (
                    f"Ya existe la rendición #{duplicado['id']} con el mismo RUT, "
                    f"tipo y folio (estado: {duplicado['estado']})."
                ),
            }
        )
        evaluacion["nivel_riesgo"] = "Alto"
        evaluacion["puede_enviar"] = False

    st.markdown("#### Resultado de la evaluación")
    checklist_reglas(evaluacion["alertas"])

    if evaluacion["puede_enviar"]:
        st.success(
            f"La rendición cumple las reglas obligatorias. "
            f"Nivel de riesgo: **{evaluacion['nivel_riesgo']}**."
        )

    else:
        st.error("Corrige las reglas marcadas con ⛔ antes de enviar.")

        if duplicado:
            st.info(
                "Si la rendición original fue rechazada, corrígela desde "
                "**Mis rendiciones** en lugar de crear una nueva.",
                icon="💡",
            )


# =========================================================
# ENVÍO
# =========================================================

if enviar and evaluacion["puede_enviar"]:
    if not aceptacion:
        st.error("Debes confirmar que estás utilizando datos demostrativos.")
        st.stop()

    ruta_archivo = None
    rendicion_creada = False

    try:
        with st.spinner("Guardando comprobante y rendición..."):
            # El comprobante se sube solo después de aprobar
            # todas las validaciones, incluida R1.
            ruta_archivo = subir_comprobante(
                archivo=archivo,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )

            nueva_rendicion = crear_rendicion(
                {
                    "empresa_id": empresa_id,
                    "usuario_id": usuario_id,
                    "tipo_documento": tipo_documento,
                    "rut_emisor": rut_emisor,
                    "proveedor": proveedor.strip(),
                    "folio": folio,
                    "fecha_documento": fecha_documento,
                    "categoria": categoria,
                    "descripcion": descripcion.strip(),
                    "monto_neto": float(monto_neto),
                    "iva": float(iva),
                    "monto_total": float(monto_total),
                    "archivo_url": ruta_archivo,
                    "estado": "Pendiente",
                    "nivel_riesgo": evaluacion["nivel_riesgo"],
                    "reglas_activadas": [
                        alerta["codigo"] for alerta in evaluacion["alertas"]
                    ],
                }
            )

            rendicion_creada = True

            registrar_auditoria(
                empresa_id=empresa_id,
                rendicion_id=nueva_rendicion["id"],
                usuario_id=usuario_id,
                accion="Envío de rendición",
                estado_anterior="Borrador",
                estado_nuevo="Pendiente",
                detalle="La rendición fue creada y enviada a revisión administrativa.",
            )

        st.success(f"Rendición #{nueva_rendicion['id']} enviada correctamente.", icon="✅")
        st.balloons()
        st.page_link("pages/mis_rendiciones.py", label="Ver mis rendiciones", icon="📋")

    except Exception as error:
        # Si la rendición no alcanzó a crearse, se elimina
        # el comprobante para no dejar archivos huérfanos.
        if not rendicion_creada:
            eliminar_comprobante(ruta_archivo)

        st.error("No fue posible guardar la rendición.")
        st.code(str(error))


pie_pagina()