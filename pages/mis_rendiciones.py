from datetime import date

import streamlit as st

from auth import exigir_rol, mostrar_sidebar_usuario
from database import (
    actualizar_y_reenviar_rendicion,
    buscar_documento_duplicado_excluyendo,
    eliminar_comprobante,
    generar_url_comprobante,
    listar_rendiciones_usuario,
    obtener_configuracion_empresa,
    subir_comprobante,
)
from reglas import evaluar_reglas_locales
from ui import (
    ICONOS_ESTADO,
    badge_estado,
    badge_riesgo,
    checklist_reglas,
    encabezado,
    ficha,
    formatear_fecha,
    formatear_moneda,
    kpis,
    mostrar_badges,
    pie_pagina,
    reglas_activadas,
)


exigir_rol(["trabajador"])
mostrar_sidebar_usuario()

encabezado(
    "📋",
    "Mis rendiciones",
    "Consulta el estado, el riesgo y las observaciones de tus rendiciones.",
)

empresa_id = st.session_state["empresa_id"]
usuario_id = st.session_state["usuario_id"]

# Mensaje guardado antes de st.rerun() para que no se pierda.
if "mensaje_exito" in st.session_state:
    st.success(st.session_state.pop("mensaje_exito"), icon="✅")

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


def convertir_fecha(valor) -> date:
    try:
        return date.fromisoformat(str(valor)[:10])

    except (ValueError, TypeError):
        return date.today()


# =========================================================
# CONSULTA
# =========================================================

try:
    rendiciones = listar_rendiciones_usuario(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )

except Exception as error:
    st.error("No fue posible consultar las rendiciones.")
    st.code(str(error))
    st.stop()

if not rendiciones:
    st.info("Todavía no tienes rendiciones registradas.", icon="📭")
    st.page_link("pages/nueva_rendicion.py", label="Crear una rendición", icon="🧾")
    st.stop()


# =========================================================
# RESUMEN
# =========================================================

estados = [rendicion["estado"] for rendicion in rendiciones]

kpis(
    [
        ("Total", len(rendiciones)),
        ("En revisión", estados.count("Pendiente") + estados.count("Reenviada")),
        ("Aprobadas", estados.count("Aprobada")),
        ("Por corregir", estados.count("Rechazada")),
    ]
)

st.write("")


# =========================================================
# FILTROS
# =========================================================

filtro_1, filtro_2, filtro_3 = st.columns([1, 1, 1.4])

with filtro_1:
    filtro_estado = st.selectbox(
        "Estado",
        ["Todos", "Pendiente", "Reenviada", "Aprobada", "Rechazada"],
    )

with filtro_2:
    filtro_riesgo = st.selectbox("Nivel de riesgo", ["Todos", "Bajo", "Medio", "Alto"])

with filtro_3:
    busqueda = st.text_input("Buscar", placeholder="Proveedor o folio")

rendiciones_filtradas = [
    rendicion
    for rendicion in rendiciones
    if (filtro_estado == "Todos" or rendicion["estado"] == filtro_estado)
    and (filtro_riesgo == "Todos" or rendicion["nivel_riesgo"] == filtro_riesgo)
    and (
        not busqueda.strip()
        or busqueda.strip().lower() in str(rendicion["proveedor"]).lower()
        or busqueda.strip().lower() in str(rendicion["folio"]).lower()
    )
]

if not rendiciones_filtradas:
    st.warning("No existen rendiciones que coincidan con los filtros.")
    st.stop()

st.caption(f"Mostrando {len(rendiciones_filtradas)} de {len(rendiciones)} rendiciones.")


# =========================================================
# CONFIGURACIÓN PARA CORRECCIONES
# =========================================================

configuracion = obtener_configuracion_empresa(empresa_id)

if configuracion:
    limite_rendicion = float(configuracion["limite_rendicion"])
    dias_maximos = int(configuracion["dias_maximos_documento"])

else:
    limite_rendicion = 100000
    dias_maximos = 30


# =========================================================
# LISTADO
# =========================================================

for rendicion in rendiciones_filtradas:
    icono = ICONOS_ESTADO.get(rendicion["estado"], "•")

    titulo = (
        f"{icono} #{rendicion['id']} · {rendicion['proveedor']} · "
        f"{formatear_moneda(rendicion['monto_total'])} · {rendicion['estado']}"
    )

    # Las rechazadas se abren por defecto porque requieren acción.
    with st.expander(titulo, expanded=rendicion["estado"] == "Rechazada"):
        mostrar_badges(
            badge_estado(rendicion["estado"]),
            badge_riesgo(rendicion["nivel_riesgo"]),
        )

        ficha(
            [
                ("Tipo", rendicion["tipo_documento"]),
                ("Fecha del documento", formatear_fecha(rendicion["fecha_documento"], con_hora=False)),
                ("RUT emisor", rendicion["rut_emisor"]),
                ("Folio", rendicion["folio"]),
                ("Categoría", rendicion["categoria"]),
                ("Enviada", formatear_fecha(rendicion["fecha_envio"])),
                ("Neto", formatear_moneda(rendicion["monto_neto"])),
                ("IVA", formatear_moneda(rendicion["iva"])),
                ("Total", formatear_moneda(rendicion["monto_total"])),
                ("Revisada", formatear_fecha(rendicion.get("fecha_revision"))),
            ]
        )

        if rendicion.get("descripcion"):
            st.caption(f"📝 {rendicion['descripcion']}")

        reglas_activadas(rendicion.get("reglas_activadas") or [])

        if rendicion.get("motivo_rechazo"):
            st.error(f"**Motivo del rechazo:** {rendicion['motivo_rechazo']}", icon="❌")

        if rendicion.get("archivo_url"):
            try:
                url = generar_url_comprobante(rendicion["archivo_url"], 600)

                if url:
                    st.link_button("📎 Ver comprobante", url)

            except Exception:
                st.caption("No fue posible generar el enlace del comprobante.")

        # =================================================
        # CORREGIR Y REENVIAR
        # =================================================

        if rendicion["estado"] != "Rechazada":
            continue

        st.divider()
        st.markdown("#### ✏️ Corregir y reenviar")
        st.caption(
            "Corrige los datos observados. Al reenviar, el sistema vuelve a "
            "ejecutar las reglas R1 a R6 y conserva el mismo número de rendición."
        )

        tipo_actual = rendicion["tipo_documento"]
        categoria_actual = rendicion["categoria"]

        with st.form(f"corregir_{rendicion['id']}"):
            correccion_1, correccion_2 = st.columns(2)

            with correccion_1:
                tipo_documento = st.selectbox(
                    "Tipo de documento",
                    TIPOS_DOCUMENTO,
                    index=TIPOS_DOCUMENTO.index(tipo_actual) if tipo_actual in TIPOS_DOCUMENTO else 0,
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
                    value=convertir_fecha(rendicion["fecha_documento"]),
                    format="DD/MM/YYYY",
                    key=f"fecha_{rendicion['id']}",
                )

                categoria = st.selectbox(
                    "Categoría",
                    CATEGORIAS,
                    index=CATEGORIAS.index(categoria_actual) if categoria_actual in CATEGORIAS else 0,
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
                    value=int(float(rendicion["monto_neto"])),
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
                    value=int(float(rendicion["monto_total"])),
                    step=100,
                    key=f"total_{rendicion['id']}",
                )

            calcular_automaticamente = st.checkbox(
                "Calcular total automáticamente como Neto + IVA",
                key=f"calcular_{rendicion['id']}",
            )

            archivo_nuevo = st.file_uploader(
                "Nuevo comprobante (opcional)",
                type=["jpg", "jpeg", "png", "webp", "pdf"],
                help="Si no adjuntas uno nuevo, se conserva el comprobante anterior.",
                key=f"archivo_{rendicion['id']}",
            )

            confirmar = st.checkbox(
                "Confirmo que revisé y corregí la rendición.",
                key=f"confirmar_{rendicion['id']}",
            )

            reenviar = st.form_submit_button(
                "🔁 Corregir y reenviar",
                type="primary",
                use_container_width=True,
            )

        if not reenviar:
            continue

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

        evaluacion = evaluar_reglas_locales(
            datos=datos_evaluacion,
            limite=limite_rendicion,
            dias_maximos=dias_maximos,
            archivo_cargado=bool(archivo_nuevo or rendicion.get("archivo_url")),
        )

        duplicado = buscar_documento_duplicado_excluyendo(
            empresa_id=empresa_id,
            rut_emisor=rut_emisor,
            tipo_documento=tipo_documento,
            folio=folio,
            rendicion_excluida_id=rendicion["id"],
        )

        if duplicado:
            evaluacion["alertas"].append(
                {
                    "codigo": "R1",
                    "nivel": "Alto",
                    "mensaje": (
                        f"Ya existe la rendición #{duplicado['id']} con el "
                        "mismo RUT, tipo y folio."
                    ),
                }
            )
            evaluacion["nivel_riesgo"] = "Alto"
            evaluacion["puede_enviar"] = False

        if not confirmar:
            st.error("Debes confirmar que corregiste la rendición.")
            continue

        if not evaluacion["puede_enviar"]:
            checklist_reglas(evaluacion["alertas"])
            st.error("No es posible reenviar hasta corregir las reglas marcadas con ⛔.")
            continue

        archivo_subido = None

        try:
            ruta_archivo = rendicion.get("archivo_url")

            if archivo_nuevo:
                ruta_archivo = subir_comprobante(
                    archivo=archivo_nuevo,
                    empresa_id=empresa_id,
                    usuario_id=usuario_id,
                )
                archivo_subido = ruta_archivo

            actualizar_y_reenviar_rendicion(
                rendicion_id=rendicion["id"],
                empresa_id=empresa_id,
                usuario_id=usuario_id,
                datos_actualizados={
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
                    "nivel_riesgo": evaluacion["nivel_riesgo"],
                    "reglas_activadas": [
                        alerta["codigo"] for alerta in evaluacion["alertas"]
                    ],
                },
            )

            st.session_state["mensaje_exito"] = (
                f"Rendición #{rendicion['id']} corregida y reenviada a revisión."
            )
            st.rerun()

        except Exception as error:
            # Elimina el nuevo comprobante si la corrección no se guardó.
            eliminar_comprobante(archivo_subido)

            st.error("No fue posible corregir y reenviar.")
            st.code(str(error))


st.divider()
st.page_link("pages/nueva_rendicion.py", label="Registrar otra rendición", icon="🧾")
pie_pagina()