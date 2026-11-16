"""
Componentes visuales compartidos por todas las pantallas.
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
    "R4": "Sin comprobante",
    "R5": "Campos obligatorios o RUT inválido",
    "R6": "Neto + IVA distinto del total",
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
        .block-container {padding-top: 2rem; max-width: 1150px;}
        h1, h2, h3 {letter-spacing: -0.01em;}

        .pg-encabezado {margin-bottom: 1.2rem;}
        .pg-encabezado h1 {font-size: 1.9rem; margin: 0; padding: 0;}
        .pg-encabezado p {color: #475569; margin: .25rem 0 0 0;}

        .pg-badge {
            display: inline-block; padding: .15rem .6rem;
            border-radius: 999px; font-size: .78rem;
            font-weight: 600; line-height: 1.4; white-space: nowrap;
        }

        .pg-ficha {
            display: grid; grid-template-columns: repeat(2, 1fr);
            gap: .6rem 1.5rem; margin: .4rem 0 .8rem 0;
        }
        .pg-ficha div span {
            display: block; font-size: .75rem; color: #64748B;
            text-transform: uppercase; letter-spacing: .03em;
        }
        .pg-ficha div strong {font-weight: 600; color: #0F172A;}

        .pg-kpi {
            background: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 12px; padding: .9rem 1rem;
        }
        .pg-kpi span {font-size: .8rem; color: #64748B;}
        .pg-kpi strong {display: block; font-size: 1.7rem; color: #0F172A;}

        .pg-regla {
            display: flex; gap: .6rem; align-items: center;
            padding: .45rem .7rem; border-radius: 8px;
            margin-bottom: .35rem; font-size: .92rem;
        }
        .pg-regla.ok {background: #F0FDF4; color: #14532D;}
        .pg-regla.medio {background: #FFFBEB; color: #78350F;}
        .pg-regla.alto {background: #FEF2F2; color: #7F1D1D;}

        .pg-evento {
            border-left: 3px solid #CBD5E1; padding: .1rem 0 .8rem 1rem;
            margin-left: .4rem;
        }
        .pg-evento small {color: #64748B;}

        div[data-testid="stExpander"] {
            background: #FFFFFF; border-radius: 12px;
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
    colores = COLORES_ESTADO.get(estado, ("#334155", "#E2E8F0"))
    return _badge(f"{icono} {estado}", colores)


def badge_riesgo(riesgo: str) -> str:
    colores = COLORES_RIESGO.get(riesgo, ("#334155", "#E2E8F0"))
    return _badge(f"Riesgo {riesgo}", colores)


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


def kpis(indicadores: list[tuple[str, object]]) -> None:
    """
    Fila de indicadores con el mismo estilo en todo el sistema.
    """
    columnas = st.columns(len(indicadores))

    for columna, (etiqueta, valor) in zip(columnas, indicadores):
        with columna:
            st.markdown(
                f'<div class="pg-kpi"><span>{html.escape(etiqueta)}'
                f"</span><strong>{html.escape(str(valor))}</strong></div>",
                unsafe_allow_html=True,
            )


def checklist_reglas(alertas: list[dict]) -> None:
    """
    Muestra R1 a R6 con su resultado, incluidas las que se cumplen.
    """
    por_codigo = {alerta["codigo"]: alerta for alerta in alertas}

    for codigo, nombre in NOMBRES_REGLAS.items():
        alerta = por_codigo.get(codigo)

        if alerta is None:
            clase, icono, texto = "ok", "✅", "Cumple"

        elif codigo in REGLAS_BLOQUEANTES:
            clase, icono, texto = "alto", "⛔", alerta["mensaje"]

        else:
            clase, icono, texto = "medio", "⚠️", alerta["mensaje"]

        st.markdown(
            f'<div class="pg-regla {clase}">{icono} '
            f"<b>{codigo} · {html.escape(nombre)}:</b> "
            f"{html.escape(texto)}</div>",
            unsafe_allow_html=True,
        )


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