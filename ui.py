"""
Componentes visuales compartidos por todas las pantallas.

Estilo inspirado en software moderno (Linear / Vercel): fondos claros,
bordes finos, colores solo para comunicar estado y diseño adaptable
al celular.
"""

import html
from datetime import datetime

import streamlit as st


# =========================================================
# CATÁLOGOS
# =========================================================

NOMBRES_REGLAS = {
    "R1": "Documento duplicado",
    "R2": "Monto sobre el límite",
    "R3": "Antigüedad o fecha futura",
    "R4": "Comprobante adjunto",
    "R5": "Datos obligatorios y RUT",
    "R6": "Neto + IVA = Total",
}

REGLAS_BLOQUEANTES = {"R1", "R4", "R5", "R6"}

COLORES_ESTADO = {
    "Pendiente": ("#92400E", "#FEF3C7"),
    "Reenviada": ("#1E40AF", "#DBEAFE"),
    "Aprobada": ("#065F46", "#D1FAE5"),
    "Rechazada": ("#991B1B", "#FEE2E2"),
}

COLORES_RIESGO = {
    "Bajo": ("#065F46", "#D1FAE5"),
    "Medio": ("#92400E", "#FEF3C7"),
    "Alto": ("#991B1B", "#FEE2E2"),
}

ICONOS_ESTADO = {
    "Pendiente": "🕒",
    "Reenviada": "🔁",
    "Aprobada": "✅",
    "Rechazada": "❌",
}

# Estado visual para el administrador: Cumple / En riesgo / Rechazado / Aprobado
VALIDACION = {
    "cumple": ("✓ Cumple", "#065F46", "#D1FAE5"),
    "riesgo": ("! En riesgo", "#92400E", "#FEF3C7"),
    "rechazado": ("✕ Rechazado", "#991B1B", "#FEE2E2"),
    "aprobado": ("✓ Aprobado", "#3F3F46", "#F4F4F5"),
}


# =========================================================
# ESTILOS
# =========================================================

def aplicar_estilos() -> None:
    """
    Inyecta los estilos globales. Se llama una vez desde app.py.
    """
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1100px;}
        h1, h2, h3, h4 {letter-spacing: -0.01em;}
        [data-testid="stHeaderActionElements"] {display: none;}

        /* Botones más altos: fáciles de tocar con el pulgar */
        .stButton > button, .stFormSubmitButton > button,
        .stDownloadButton > button, .stLinkButton > a {
            min-height: 2.75rem; border-radius: 10px; font-weight: 500;
        }
        div[data-testid="stExpander"] details {border-radius: 12px; background: #FFFFFF;}

        /* Encabezado */
        .pg-encabezado {margin-bottom: 1.1rem;}
        .pg-encabezado h1 {font-size: 1.8rem; margin: 0; padding: 0; font-weight: 700;}
        .pg-encabezado p {color: #52525B; margin: .25rem 0 0 0;}

        /* Etiquetas */
        .pg-badge {
            display: inline-block; padding: .14rem .6rem; border-radius: 999px;
            font-size: .78rem; font-weight: 600; line-height: 1.45; white-space: nowrap;
        }

        /* Indicadores: 4 columnas en escritorio, 2 en celular */
        .pg-kpis {
            display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .75rem; margin: .2rem 0 1.1rem 0;
        }
        .pg-kpi {
            background: #FFFFFF; border: 1px solid #E4E4E7; border-radius: 12px;
            padding: .85rem 1rem; box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .pg-kpi span {font-size: .8rem; color: #71717A;}
        .pg-kpi strong {
            display: block; font-size: 1.6rem; font-weight: 650; color: #09090B;
            font-variant-numeric: tabular-nums; margin-top: .15rem;
        }
        .pg-kpi small {color: #71717A; font-size: .75rem;}
        .pg-kpi.ambar {border-color: #FCD34D; background: #FFFBEB;}
        .pg-kpi.verde {border-color: #A7F3D0; background: #F0FDF4;}

        /* Ficha de datos */
        .pg-ficha {
            display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: .6rem 1.5rem; margin: .4rem 0 .8rem 0;
        }
        .pg-ficha div span {
            display: block; font-size: .72rem; color: #71717A;
            text-transform: uppercase; letter-spacing: .03em;
        }
        .pg-ficha div strong {font-weight: 600; color: #09090B; overflow-wrap: anywhere;}

        /* Lista de reglas */
        .pg-regla {
            display: flex; gap: .55rem; align-items: flex-start;
            padding: .5rem .75rem; border-radius: 9px; border: 1px solid transparent;
            margin-bottom: .35rem; font-size: .9rem; line-height: 1.35;
        }
        .pg-regla.ok {background: #F0FDF4; color: #14532D; border-color: #DCFCE7;}
        .pg-regla.medio {background: #FFFBEB; color: #78350F; border-color: #FDE68A;}
        .pg-regla.alto {background: #FEF2F2; color: #7F1D1D; border-color: #FECACA;}
        .pg-regla code {background: transparent; color: inherit; opacity: .7; font-size: .75rem;}

        /* Pasos del asistente */
        .pg-pasos {
            display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .45rem; margin: 0 0 1.2rem 0;
        }
        .pg-paso div {height: 5px; border-radius: 99px; background: #E4E4E7;}
        .pg-paso.hecho div, .pg-paso.activo div {background: #1D4ED8;}
        .pg-paso span {display: block; font-size: .75rem; color: #A1A1AA; margin-top: .35rem;}
        .pg-paso.hecho span {color: #52525B;}
        .pg-paso.activo span {color: #09090B; font-weight: 600;}

        /* Resumen de la rendición */
        .pg-resumen {
            display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start;
            background: #FFFFFF; border: 1px solid #E4E4E7; border-radius: 14px;
            padding: 1rem 1.1rem; margin-bottom: .8rem;
        }
        .pg-resumen small {color: #71717A; display: block;}
        .pg-resumen b {font-size: 1.05rem; display: block; margin: .1rem 0;}
        .pg-resumen .monto {font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap;}

        /* Filas de la bandeja de revisión */
        .pg-fila b {color: #09090B;}
        .pg-fila small {color: #71717A;}
        .pg-monto {font-size: 1.1rem; font-weight: 650; font-variant-numeric: tabular-nums;}

        /* Línea de tiempo */
        .pg-evento {border-left: 3px solid #D4D4D8; padding: .1rem 0 .8rem 1rem; margin-left: .4rem;}
        .pg-evento small {color: #71717A;}

        /* Celular */
        @media (max-width: 640px) {
            .block-container {padding: 1.1rem .85rem 5rem .85rem;}
            .pg-encabezado h1 {font-size: 1.45rem;}
            .pg-kpis {grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem;}
            .pg-kpi {padding: .7rem .8rem;}
            .pg-kpi strong {font-size: 1.3rem;}
            .pg-resumen .monto {font-size: 1.3rem;}
            .stButton > button, .stFormSubmitButton > button {min-height: 3rem;}
            input, textarea {font-size: 16px !important;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# FORMATOS
# =========================================================

def formatear_moneda(valor) -> str:
    """
    Formato monetario chileno: $119.000
    """
    try:
        return f"${float(valor):,.0f}".replace(",", ".")

    except (TypeError, ValueError):
        return "$0"


def formatear_fecha(valor, con_hora: bool = True) -> str:
    """
    Convierte fechas ISO de Supabase a dd-mm-aaaa (hh:mm).
    """
    if not valor:
        return "Sin información"

    try:
        fecha = datetime.fromisoformat(
            str(valor).replace("Z", "+00:00")
        )

        formato = "%d-%m-%Y %H:%M" if con_hora else "%d-%m-%Y"
        return fecha.strftime(formato)

    except ValueError:
        return str(valor)


# =========================================================
# COMPONENTES
# =========================================================

def encabezado(icono: str, titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f"""
        <div class="pg-encabezado">
            <h1>{icono} {html.escape(titulo)}</h1>
            <p>{html.escape(subtitulo)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _badge(texto: str, colores: tuple[str, str]) -> str:
    color, fondo = colores
    return (
        f'<span class="pg-badge" style="color:{color};'
        f'background:{fondo};">{html.escape(str(texto))}</span>'
    )


def badge_estado(estado: str) -> str:
    icono = ICONOS_ESTADO.get(estado, "•")
    colores = COLORES_ESTADO.get(estado, ("#3F3F46", "#F4F4F5"))
    return _badge(f"{icono} {estado}", colores)


def badge_riesgo(riesgo: str) -> str:
    colores = COLORES_RIESGO.get(riesgo, ("#3F3F46", "#F4F4F5"))
    return _badge(f"Riesgo {riesgo}", colores)


def badge_validacion(clave: str) -> str:
    """
    Etiqueta Cumple / En riesgo / Rechazado / Aprobado.
    """
    texto, color, fondo = VALIDACION.get(clave, VALIDACION["cumple"])
    return _badge(texto, (color, fondo))


def mostrar_badges(*badges: str) -> None:
    st.markdown(" ".join(badges), unsafe_allow_html=True)


def ficha(campos: list[tuple[str, str]]) -> None:
    """
    Muestra pares etiqueta / valor en una grilla de dos columnas.
    Los valores se escapan para evitar inyección de HTML.
    """
    celdas = "".join(
        f"<div><span>{html.escape(etiqueta)}</span>"
        f"<strong>{html.escape(str(valor))}</strong></div>"
        for etiqueta, valor in campos
    )

    st.markdown(
        f'<div class="pg-ficha">{celdas}</div>',
        unsafe_allow_html=True,
    )


def kpis(indicadores: list[tuple]) -> None:
    """
    Fila de indicadores. Cada uno es (etiqueta, valor),
    (etiqueta, valor, detalle) o (etiqueta, valor, detalle, tono),
    con tono "ambar" o "verde".
    """
    tarjetas = []

    for indicador in indicadores:
        etiqueta, valor = indicador[0], indicador[1]
        detalle = indicador[2] if len(indicador) > 2 else ""
        tono = indicador[3] if len(indicador) > 3 else ""

        tarjetas.append(
            f'<div class="pg-kpi {tono}"><span>{html.escape(str(etiqueta))}</span>'
            f"<strong>{html.escape(str(valor))}</strong>"
            f"<small>{html.escape(str(detalle))}</small></div>"
        )

    st.markdown(
        f'<div class="pg-kpis">{"".join(tarjetas)}</div>',
        unsafe_allow_html=True,
    )


def pasos(actual: int, nombres: list[str]) -> None:
    """
    Barra de progreso del asistente de nueva rendición.
    """
    partes = []

    for indice, nombre in enumerate(nombres):
        clase = "hecho" if indice < actual else "activo" if indice == actual else ""
        partes.append(
            f'<div class="pg-paso {clase}"><div></div>'
            f"<span>{indice + 1}. {html.escape(nombre)}</span></div>"
        )

    st.markdown(
        f'<div class="pg-pasos">{"".join(partes)}</div>',
        unsafe_allow_html=True,
    )


def resumen_documento(
    tipo: str,
    folio: str,
    fecha: str,
    proveedor: str,
    categoria: str,
    total,
) -> None:
    """
    Tarjeta de resumen antes de enviar la rendición.
    """
    st.markdown(
        f"""
        <div class="pg-resumen">
            <div>
                <small>{html.escape(tipo)} N° {html.escape(folio)} · {html.escape(fecha)}</small>
                <b>{html.escape(proveedor)}</b>
                <small>{html.escape(categoria or "Sin categoría")}</small>
            </div>
            <div class="monto">{formatear_moneda(total)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _regla_html(codigo: str, nombre: str, clase: str, icono: str, texto: str) -> str:
    return (
        f'<div class="pg-regla {clase}"><span>{icono}</span><div>'
        f"<code>{codigo}</code> <b>{html.escape(nombre)}</b>"
        f"{'<br>' + html.escape(texto) if texto else ''}</div></div>"
    )


def checklist_reglas(alertas: list[dict]) -> None:
    """
    Muestra R1 a R6 con su resultado, incluidas las que se cumplen.
    """
    por_codigo = {alerta["codigo"]: alerta for alerta in alertas}
    filas = []

    for codigo, nombre in NOMBRES_REGLAS.items():
        alerta = por_codigo.get(codigo)

        if alerta is None:
            filas.append(_regla_html(codigo, nombre, "ok", "✅", ""))

        elif codigo in REGLAS_BLOQUEANTES:
            filas.append(_regla_html(codigo, nombre, "alto", "⛔", alerta["mensaje"]))

        else:
            filas.append(_regla_html(codigo, nombre, "medio", "⚠️", alerta["mensaje"]))

    st.markdown("".join(filas), unsafe_allow_html=True)


def checklist_codigos(codigos: list[str]) -> None:
    """
    Igual que checklist_reglas, pero a partir de los códigos
    guardados en una rendición ya enviada.
    """
    filas = []

    for codigo, nombre in NOMBRES_REGLAS.items():
        if codigo not in codigos:
            filas.append(_regla_html(codigo, nombre, "ok", "✅", ""))

        elif codigo in REGLAS_BLOQUEANTES:
            filas.append(_regla_html(codigo, nombre, "alto", "⛔", "Regla activada."))

        else:
            filas.append(_regla_html(codigo, nombre, "medio", "⚠️", "Requiere atención del revisor."))

    st.markdown("".join(filas), unsafe_allow_html=True)


def reglas_activadas(codigos: list[str]) -> None:
    """
    Lista las reglas registradas en una rendición ya enviada.
    """
    if not codigos:
        st.success("Sin reglas activadas.", icon="✅")
        return

    detalle = " · ".join(
        f"{codigo} ({NOMBRES_REGLAS.get(codigo, 'Regla')})"
        for codigo in codigos
    )
    st.warning(f"**Reglas activadas:** {detalle}", icon="⚠️")


def pie_pagina() -> None:
    st.divider()
    st.caption(
        "PymeGestiona · Prototipo académico INACAP · "
        "Datos exclusivamente demostrativos"
    )