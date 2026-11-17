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
from reglas import (
    LIMITES,
    MONTO_MAXIMO,
    evaluar_reglas_locales,
    validar_folio,
    validar_rut,
)
from ui import (
    campo_monto,
    checklist_reglas,
    encabezado,
    formatear_moneda,
    pasos,
    pie_pagina,
    resumen_documento,
)


# =========================================================
# SEGURIDAD Y SESIÓN
# =========================================================

exigir_rol(["trabajador"])
mostrar_sidebar_usuario()

empresa_id = st.session_state["empresa_id"]
usuario_id = st.session_state["usuario_id"]

TASA_IVA = 0.19

TIPOS_DOCUMENTO = ["Boleta", "Factura", "Comprobante", "Otro"]

CATEGORIAS = [
    ("Materiales", "🧱"),
    ("Combustible", "⛽"),
    ("Transporte", "🚚"),
    ("Alimentación", "🍽️"),
    ("Alojamiento", "🛏️"),
    ("Servicios", "🔧"),
    ("Otro", "📦"),
]

NOMBRES_PASOS = ["Comprobante", "Datos", "Categoría", "Confirmar"]

SUBTITULOS = [
    "Saca una foto a la boleta o factura, o sube el archivo.",
    "Revisa y completa los datos del documento.",
    "Elige en qué se gastó.",
    "Revisa el resumen y envíala a revisión.",
]


class ArchivoGuardado:
    """
    Copia del archivo subido. Streamlit borra el archivo del cargador
    cuando se cambia de paso, por eso se guarda aquí con los mismos
    atributos que usa subir_comprobante (name, type y getvalue()).
    """

    def __init__(self, nombre: str, tipo: str, contenido: bytes):
        self.name = nombre
        self.type = tipo
        self._contenido = contenido

    def getvalue(self) -> bytes:
        return self._contenido


def borrador_vacio() -> dict:
    return {
        "tipo_documento": "Boleta",
        "rut_emisor": "",
        "proveedor": "",
        "folio": "",
        "fecha_documento": date.today(),
        "monto_neto": 0,
        "iva": 0,
        "monto_total": 0,
        "iva_automatico": True,
        "categoria": None,
        "descripcion": "",
        "archivo": None,
    }


def limpiar_campos() -> None:
    """
    Borra los valores de los campos del asistente (claves nr_*).
    """
    for clave in [c for c in st.session_state.keys() if str(c).startswith("nr_")]:
        del st.session_state[clave]


def reiniciar() -> None:
    st.session_state["borrador"] = borrador_vacio()
    st.session_state["paso"] = 0
    limpiar_campos()


def ir_a(paso: int) -> None:
    st.session_state["paso"] = paso
    st.rerun()


def sembrar(clave: str, campo: str) -> None:
    """
    Carga en un campo el valor guardado en el borrador. Así los datos
    se conservan al avanzar y retroceder entre pasos.
    """
    if clave not in st.session_state:
        st.session_state[clave] = borrador[campo]


if "borrador" not in st.session_state:
    reiniciar()

borrador = st.session_state["borrador"]
paso = st.session_state["paso"]


# =========================================================
# CONFIGURACIÓN DE EMPRESA
# =========================================================

configuracion = obtener_configuracion_empresa(empresa_id)

if configuracion is None:
    st.error("No fue posible obtener la configuración de la empresa.")
    st.stop()

limite_rendicion = float(configuracion["limite_rendicion"])
dias_maximos = int(configuracion["dias_maximos_documento"])


# =========================================================
# PANTALLA DE ÉXITO
# =========================================================

if "rendicion_enviada" in st.session_state:
    enviada = st.session_state["rendicion_enviada"]

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    encabezado(
        "✅",
        f"Rendición #{enviada['id']} enviada",
        f"{formatear_moneda(enviada['total'])} · {enviada['proveedor']}. "
        "Quedó pendiente de revisión administrativa.",
    )

    if enviada["reglas"]:
        st.warning(
            "Se envió marcada para revisión por: " + ", ".join(enviada["reglas"]) + ".",
            icon="⚠️",
        )

    if st.button("🧾 Registrar otra rendición", type="primary", use_container_width=True):
        del st.session_state["rendicion_enviada"]
        st.rerun()

    st.page_link("pages/mis_rendiciones.py", label="Ver mis rendiciones", icon="📋")
    pie_pagina()
    st.stop()


# =========================================================
# ENCABEZADO Y PROGRESO
# =========================================================

encabezado("🧾", "Nueva rendición", SUBTITULOS[paso])
pasos(paso, NOMBRES_PASOS)


# =========================================================
# PASO 1: COMPROBANTE
# =========================================================

if paso == 0:
    with st.container(border=True):
        st.markdown("#### 📸 Foto o archivo del comprobante")
        st.caption(
            "En el celular puedes usar la cámara. Apoya la boleta sobre una "
            "superficie plana y con luz: deben leerse el folio, la fecha y el total."
        )

        archivo = st.file_uploader(
            "Comprobante",
            type=["jpg", "jpeg", "png", "webp", "pdf"],
            label_visibility="collapsed",
            key="nr_archivo",
        )

        if archivo is not None:
            borrador["archivo"] = ArchivoGuardado(
                archivo.name,
                archivo.type,
                archivo.getvalue(),
            )

        if borrador["archivo"] is not None:
            if borrador["archivo"].type.startswith("image/"):
                st.image(borrador["archivo"].getvalue(), width=240)

            else:
                st.caption(f"📄 {borrador['archivo'].name}")

            st.success("Comprobante listo.", icon="✅")

    if st.button(
        "Continuar →",
        type="primary",
        use_container_width=True,
        disabled=borrador["archivo"] is None,
    ):
        ir_a(1)


# =========================================================
# PASO 2: DATOS DEL DOCUMENTO
# =========================================================

elif paso == 1:
    for clave, campo in [
        ("nr_tipo", "tipo_documento"),
        ("nr_rut", "rut_emisor"),
        ("nr_proveedor", "proveedor"),
        ("nr_folio", "folio"),
        ("nr_fecha", "fecha_documento"),
        ("nr_iva_auto", "iva_automatico"),
    ]:
        sembrar(clave, campo)

    with st.container(border=True):
        st.markdown("#### 📄 Documento")

        tipo_documento = st.radio("Tipo de documento", TIPOS_DOCUMENTO, horizontal=True, key="nr_tipo")

        rut_emisor = st.text_input(
            "RUT del emisor",
            placeholder="76.123.456-0",
            max_chars=LIMITES["rut_emisor"],
            key="nr_rut",
        )

        if rut_emisor.strip():
            if validar_rut(rut_emisor):
                st.caption("✅ RUT válido")

            else:
                st.caption(":red[⛔ El dígito verificador no corresponde a este RUT.]")

        proveedor = st.text_input(
            "Proveedor",
            placeholder="Nombre o razón social",
            max_chars=LIMITES["proveedor"],
            key="nr_proveedor",
        )

        columna_1, columna_2 = st.columns(2)

        with columna_1:
            folio = st.text_input(
                "Folio",
                placeholder="N° del documento",
                max_chars=LIMITES["folio"],
                help="Boletas y facturas: solo números, hasta 10 dígitos (formato SII).",
                key="nr_folio",
            )

            error_folio = validar_folio(folio, tipo_documento)

            if error_folio:
                st.caption(f":red[⛔ {error_folio}]")

        with columna_2:
            fecha_documento = st.date_input(
                "Fecha del documento",
                max_value=date.today(),
                format="DD/MM/YYYY",
                key="nr_fecha",
            )

    with st.container(border=True):
        st.markdown("#### 💰 Montos")

        iva_automatico = st.toggle("Calcular IVA (19 %) y total desde el neto", key="nr_iva_auto")

        monto_neto = campo_monto("Monto neto", "nr_neto", borrador["monto_neto"])
        montos_invalidos = monto_neto is None
        monto_neto = monto_neto or 0

        if iva_automatico:
            iva = round(monto_neto * TASA_IVA)
            monto_total = monto_neto + iva

            # Deja listos los valores por si se cambia a ingreso manual.
            st.session_state["nr_iva"] = str(iva)
            st.session_state["nr_total"] = str(monto_total)

            columna_iva, columna_total = st.columns(2)
            columna_iva.metric("IVA (19 %)", formatear_moneda(iva))
            columna_total.metric("Total", formatear_moneda(monto_total))

        else:
            columna_iva, columna_total = st.columns(2)

            with columna_iva:
                iva = campo_monto("IVA", "nr_iva", borrador["iva"])

            with columna_total:
                monto_total = campo_monto("Total", "nr_total", borrador["monto_total"])

            montos_invalidos = montos_invalidos or iva is None or monto_total is None
            iva = iva or 0
            monto_total = monto_total or 0

        if monto_total > limite_rendicion:
            st.caption(
                f":orange[⚠️ Supera el límite de {formatear_moneda(limite_rendicion)} (R2). "
                "Se puede enviar, pero quedará marcada para revisión.]"
            )

    # Validación en vivo de lo mínimo para continuar
    pendientes = []

    if not validar_rut(rut_emisor):
        pendientes.append("RUT válido")

    if not proveedor.strip():
        pendientes.append("proveedor")

    if not folio.strip():
        pendientes.append("folio")

    elif error_folio:
        pendientes.append("folio válido")

    if montos_invalidos:
        pendientes.append("montos solo con números")

    elif monto_total <= 0:
        pendientes.append("total mayor a $0")

    elif monto_total > MONTO_MAXIMO:
        pendientes.append("total de hasta $999.999.999")

    elif abs((monto_neto + iva) - monto_total) >= 1:
        pendientes.append("neto + IVA igual al total")

    if pendientes:
        st.caption("Para continuar falta: " + ", ".join(pendientes) + ".")

    def guardar_datos() -> None:
        borrador.update(
            {
                "tipo_documento": tipo_documento,
                "rut_emisor": rut_emisor.strip(),
                "proveedor": proveedor.strip(),
                "folio": folio.strip(),
                "fecha_documento": fecha_documento,
                "monto_neto": int(monto_neto),
                "iva": int(iva),
                "monto_total": int(monto_total),
                "iva_automatico": iva_automatico,
            }
        )

    atras, continuar = st.columns(2)

    with atras:
        if st.button("← Atrás", use_container_width=True):
            guardar_datos()
            ir_a(0)

    with continuar:
        if st.button("Continuar →", type="primary", use_container_width=True, disabled=bool(pendientes)):
            guardar_datos()
            ir_a(2)


# =========================================================
# PASO 3: CATEGORÍA
# =========================================================

elif paso == 2:
    sembrar("nr_descripcion", "descripcion")

    columnas = st.columns(2)

    for indice, (nombre, emoji) in enumerate(CATEGORIAS):
        with columnas[indice % 2]:
            if st.button(
                f"{emoji}  {nombre}",
                key=f"nr_categoria_{nombre}",
                type="primary" if borrador["categoria"] == nombre else "secondary",
                use_container_width=True,
            ):
                borrador["categoria"] = nombre
                st.rerun()

    descripcion = st.text_area(
        "Descripción (opcional)",
        max_chars=LIMITES["descripcion"],
        placeholder="Ej.: materiales para la mantención en obra Vicuña.",
        key="nr_descripcion",
    )

    atras, continuar = st.columns(2)

    with atras:
        if st.button("← Atrás", use_container_width=True):
            borrador["descripcion"] = descripcion.strip()
            ir_a(1)

    with continuar:
        if st.button(
            "Continuar →",
            type="primary",
            use_container_width=True,
            disabled=borrador["categoria"] is None,
        ):
            borrador["descripcion"] = descripcion.strip()
            ir_a(3)


# =========================================================
# PASO 4: CONFIRMAR Y ENVIAR
# =========================================================

elif paso == 3:
    datos_evaluacion = {
        "tipo_documento": borrador["tipo_documento"],
        "rut_emisor": borrador["rut_emisor"],
        "proveedor": borrador["proveedor"],
        "folio": borrador["folio"],
        "fecha_documento": borrador["fecha_documento"],
        "categoria": borrador["categoria"],
        "monto_neto": float(borrador["monto_neto"]),
        "iva": float(borrador["iva"]),
        "monto_total": float(borrador["monto_total"]),
    }

    evaluacion = evaluar_reglas_locales(
        datos=datos_evaluacion,
        limite=limite_rendicion,
        dias_maximos=dias_maximos,
        archivo_cargado=borrador["archivo"] is not None,
    )

    # R1: documento duplicado (requiere consultar Supabase).
    try:
        duplicado = buscar_documento_duplicado(
            empresa_id=empresa_id,
            rut_emisor=borrador["rut_emisor"],
            tipo_documento=borrador["tipo_documento"],
            folio=borrador["folio"],
        )

    except Exception:
        duplicado = None
        st.warning("No fue posible comprobar duplicados (R1). Inténtalo nuevamente.")

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

    resumen_documento(
        tipo=borrador["tipo_documento"],
        folio=borrador["folio"],
        fecha=borrador["fecha_documento"].strftime("%d-%m-%Y"),
        proveedor=borrador["proveedor"],
        categoria=borrador["categoria"],
        total=borrador["monto_total"],
    )

    editar_1, editar_2 = st.columns(2)

    with editar_1:
        if st.button("✏️ Editar datos", use_container_width=True):
            ir_a(1)

    with editar_2:
        if st.button("✏️ Cambiar categoría", use_container_width=True):
            ir_a(2)

    st.markdown("#### Validación automática")
    checklist_reglas(evaluacion["alertas"])

    if not evaluacion["puede_enviar"]:
        st.error("Corrige las reglas marcadas con ⛔ antes de enviar.")

        if duplicado:
            st.info(
                "Si la rendición original fue rechazada, corrígela desde "
                "**Mis rendiciones** en lugar de crear una nueva.",
                icon="💡",
            )

    elif evaluacion["alertas"]:
        st.warning("Se puede enviar, pero quedará marcada para revisión.", icon="⚠️")

    else:
        st.success("Todo en orden.", icon="✅")

    aceptacion = st.checkbox(
        "Confirmo que los datos son demostrativos y no contienen "
        "información tributaria real.",
        key="nr_aceptacion",
    )

    atras, enviar_columna = st.columns(2)

    with atras:
        if st.button("← Atrás", use_container_width=True):
            ir_a(2)

    with enviar_columna:
        enviar = st.button(
            f"📤 Enviar · {formatear_moneda(borrador['monto_total'])}",
            type="primary",
            use_container_width=True,
            disabled=not evaluacion["puede_enviar"],
        )

    if enviar:
        if not aceptacion:
            st.error("Debes confirmar que estás utilizando datos demostrativos.")
            st.stop()

        ruta_archivo = None
        rendicion_creada = False

        try:
            with st.spinner("Guardando comprobante y rendición..."):
                ruta_archivo = subir_comprobante(
                    archivo=borrador["archivo"],
                    empresa_id=empresa_id,
                    usuario_id=usuario_id,
                )

                nueva_rendicion = crear_rendicion(
                    {
                        "empresa_id": empresa_id,
                        "usuario_id": usuario_id,
                        "tipo_documento": borrador["tipo_documento"],
                        "rut_emisor": borrador["rut_emisor"],
                        "proveedor": borrador["proveedor"],
                        "folio": borrador["folio"],
                        "fecha_documento": borrador["fecha_documento"],
                        "categoria": borrador["categoria"],
                        "descripcion": borrador["descripcion"],
                        "monto_neto": float(borrador["monto_neto"]),
                        "iva": float(borrador["iva"]),
                        "monto_total": float(borrador["monto_total"]),
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

            st.session_state["rendicion_enviada"] = {
                "id": nueva_rendicion["id"],
                "total": borrador["monto_total"],
                "proveedor": borrador["proveedor"],
                "reglas": [alerta["codigo"] for alerta in evaluacion["alertas"]],
            }

        except Exception as error:
            # Si la rendición no alcanzó a crearse, se elimina
            # el comprobante para no dejar archivos huérfanos.
            if not rendicion_creada:
                eliminar_comprobante(ruta_archivo)

            st.error("No fue posible guardar la rendición.")
            st.code(str(error))

        # st.rerun() va fuera del try para que no lo capture el except.
        if "rendicion_enviada" in st.session_state:
            reiniciar()
            st.rerun()


pie_pagina()