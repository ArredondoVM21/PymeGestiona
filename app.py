import time

import streamlit as st

from auth import (
    autenticar_usuario,
    cerrar_sesion,
    iniciar_sesion,
    inicializar_sesion,
    mostrar_sidebar_usuario,
    usuario_autenticado,
)
from database import (
    listar_rendiciones_usuario,
    resumen_rendiciones_empresa,
)
from ui import (
    aplicar_estilos,
    encabezado,
    formatear_moneda,
    kpis,
    marca_html,
    nav_activo_html,
    nav_seccion_html,
    ocultar_barra_lateral,
    pie_pagina,
    usuario_html,
)


# =========================================================
# CONFIGURACIÓN GLOBAL
# =========================================================

st.set_page_config(
    page_title="PymeGestiona",
    page_icon="📊",
    layout="wide",
    # "auto": abierta en el computador y cerrada en el celular.
    initial_sidebar_state="auto",
)

# Con st.navigation, app.py se ejecuta en cada página,
# por lo que los estilos quedan aplicados en todo el sistema.
aplicar_estilos()
inicializar_sesion()

# En el inicio de sesión no se muestra la barra lateral.
if not usuario_autenticado():
    ocultar_barra_lateral()


# =========================================================
# CONTROL DE INTENTOS DE INICIO DE SESIÓN
# =========================================================

MAX_INTENTOS_LOGIN = 5
SEGUNDOS_BLOQUEO_LOGIN = 300


def segundos_bloqueo_restantes() -> int:
    """
    Devuelve los segundos que faltan para desbloquear el login.
    """
    bloqueado_hasta = st.session_state.get("login_bloqueado_hasta", 0)
    return max(0, int(bloqueado_hasta - time.time()))


def registrar_intento_fallido() -> None:
    """
    Cuenta intentos fallidos y bloquea el formulario
    temporalmente al llegar al máximo.
    """
    intentos = st.session_state.get("login_intentos", 0) + 1
    st.session_state["login_intentos"] = intentos

    if intentos >= MAX_INTENTOS_LOGIN:
        st.session_state["login_bloqueado_hasta"] = (
            time.time() + SEGUNDOS_BLOQUEO_LOGIN
        )
        st.session_state["login_intentos"] = 0


# =========================================================
# INICIO DE SESIÓN
# =========================================================

def mostrar_login() -> None:
    """
    Formulario de acceso centrado, sin navegación interna.
    """
    _, centro, _ = st.columns([1, 1.6, 1])

    with centro:
        st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)

        encabezado(
            "📊",
            "PymeGestiona",
            "Gestión y control de rendiciones de gastos para PYMEs.",
        )

        with st.container(border=True):
            with st.form("formulario_login"):
                st.markdown("#### 🔐 Iniciar sesión")

                correo = st.text_input(
                    "Correo electrónico",
                    placeholder="usuario@pymegestiona.cl",
                )

                password = st.text_input(
                    "Contraseña",
                    type="password",
                    placeholder="Ingresa tu contraseña",
                )

                ingresar = st.form_submit_button(
                    "Ingresar",
                    type="primary",
                    use_container_width=True,
                )

            restantes = segundos_bloqueo_restantes()

            if ingresar and restantes > 0:
                st.error(
                    "Demasiados intentos fallidos. Espera "
                    f"{restantes // 60 + 1} minuto(s) antes de "
                    "volver a intentarlo."
                )

            elif ingresar:
                if not correo.strip() or not password:
                    st.warning("Debes ingresar el correo y la contraseña.")

                else:
                    try:
                        usuario = autenticar_usuario(correo, password)

                        if usuario is None:
                            registrar_intento_fallido()
                            st.error("Correo o contraseña incorrectos.")

                        else:
                            st.session_state["login_intentos"] = 0
                            iniciar_sesion(usuario)
                            st.rerun()

                    except Exception:
                        st.error(
                            "No fue posible validar el inicio de sesión. "
                            "Inténtalo nuevamente."
                        )

        with st.expander("Credenciales demostrativas"):
            st.markdown(
                """
                **Trabajador:** `trabajador@pymegestiona.cl` · `Demo1234!`

                **Administrador:** `admin@pymegestiona.cl` · `Admin1234!`

                Estas cuentas contienen exclusivamente datos demostrativos.
                """
            )

        st.caption("PymeGestiona © 2026 · Datos demostrativos")


# =========================================================
# PANEL PRINCIPAL
# =========================================================

def tarjeta_acceso(titulo: str, descripcion: str, pagina: str, icono: str) -> None:
    with st.container(border=True):
        st.markdown(f"#### {icono} {titulo}")
        st.caption(descripcion)
        st.page_link(pagina, label="Abrir", icon="➡️", use_container_width=True)


def mostrar_inicio() -> None:
    """
    Panel principal según el rol activo.
    """
    mostrar_sidebar_usuario()

    nombre = st.session_state["nombre"]
    rol = st.session_state["rol"]

    encabezado(
        "👋",
        f"Hola, {nombre.split()[0] if nombre else 'usuario'}",
        "Panel del trabajador" if rol == "trabajador" else "Panel administrativo",
    )

    if rol == "trabajador":
        mostrar_panel_trabajador()

    elif rol == "administrador":
        mostrar_panel_administrador()

    pie_pagina()


def mostrar_panel_trabajador() -> None:
    try:
        rendiciones = listar_rendiciones_usuario(
            empresa_id=st.session_state["empresa_id"],
            usuario_id=st.session_state["usuario_id"],
        )

        estados = [rendicion["estado"] for rendicion in rendiciones]

        kpis(
            [
                ("Rendiciones", len(rendiciones)),
                ("En revisión", estados.count("Pendiente") + estados.count("Reenviada")),
                ("Aprobadas", estados.count("Aprobada")),
                ("Por corregir", estados.count("Rechazada")),
            ]
        )

        if estados.count("Rechazada"):
            st.warning(
                f"Tienes {estados.count('Rechazada')} rendición(es) "
                "rechazada(s) para corregir en **Mis rendiciones**.",
                icon="✏️",
            )

    except Exception:
        st.warning("No fue posible cargar el resumen de tus rendiciones.")

    st.write("")
    columna_1, columna_2 = st.columns(2)

    with columna_1:
        tarjeta_acceso(
            "Nueva rendición",
            "Registra una boleta, factura o comprobante y envíalo a revisión.",
            "pages/nueva_rendicion.py",
            "🧾",
        )

    with columna_2:
        tarjeta_acceso(
            "Mis rendiciones",
            "Consulta estados, observaciones y correcciones pendientes.",
            "pages/mis_rendiciones.py",
            "📋",
        )


def mostrar_panel_administrador() -> None:
    try:
        rendiciones = resumen_rendiciones_empresa(
            empresa_id=st.session_state["empresa_id"],
        )

        por_revisar = [
            r for r in rendiciones if r["estado"] in ["Pendiente", "Reenviada"]
        ]
        alto_riesgo = [r for r in por_revisar if r["nivel_riesgo"] == "Alto"]
        monto_aprobado = sum(
            float(r["monto_total"] or 0)
            for r in rendiciones
            if r["estado"] == "Aprobada"
        )

        kpis(
            [
                ("Por revisar", len(por_revisar)),
                ("Riesgo alto por revisar", len(alto_riesgo)),
                ("Total rendiciones", len(rendiciones)),
                ("Monto aprobado", formatear_moneda(monto_aprobado)),
            ]
        )

        if por_revisar:
            st.info(
                f"Hay {len(por_revisar)} rendición(es) esperando tu decisión.",
                icon="📥",
            )

    except Exception:
        st.warning("No fue posible cargar el resumen de la empresa.")

    st.write("")
    columna_1, columna_2 = st.columns(2)

    with columna_1:
        tarjeta_acceso(
            "Revisión administrativa",
            "Revisa rendiciones pendientes o reenviadas y registra una decisión.",
            "pages/revision.py",
            "✅",
        )

    with columna_2:
        tarjeta_acceso(
            "Trazabilidad",
            "Consulta cambios de estado, responsables y acciones registradas.",
            "pages/trazabilidad.py",
            "🔎",
        )


# =========================================================
# BARRA LATERAL
# =========================================================

def mostrar_barra_lateral(secciones: dict, pagina_actual) -> None:
    """
    Marca, tarjeta del usuario, menú por secciones con la página
    activa destacada y botón para cerrar sesión.
    """
    with st.sidebar:
        st.markdown(
            marca_html()
            + usuario_html(st.session_state.get("nombre"), st.session_state.get("rol")),
            unsafe_allow_html=True,
        )

        for seccion, paginas in secciones.items():
            st.markdown(nav_seccion_html(seccion), unsafe_allow_html=True)

            for pagina in paginas:
                if pagina.title == pagina_actual.title:
                    st.markdown(nav_activo_html(pagina.icon, pagina.title), unsafe_allow_html=True)

                else:
                    st.page_link(pagina, label=pagina.title, icon=pagina.icon)

        st.divider()

        if st.button("Cerrar sesión", icon="🚪", use_container_width=True):
            cerrar_sesion()


# =========================================================
# DEFINICIÓN DE PÁGINAS
# =========================================================

pagina_login = st.Page(mostrar_login, title="Iniciar sesión", icon="🔐", default=True)
pagina_inicio = st.Page(mostrar_inicio, title="Inicio", icon="🏠", default=True)
pagina_nueva_rendicion = st.Page("pages/nueva_rendicion.py", title="Nueva rendición", icon="🧾")
pagina_mis_rendiciones = st.Page("pages/mis_rendiciones.py", title="Mis rendiciones", icon="📋")
pagina_revision = st.Page("pages/revision.py", title="Revisión administrativa", icon="✅")
pagina_trazabilidad = st.Page("pages/trazabilidad.py", title="Trazabilidad", icon="🔎")


# =========================================================
# NAVEGACIÓN DINÁMICA SEGÚN ROL
# =========================================================

if not usuario_autenticado():
    navegacion = st.navigation([pagina_login], position="hidden")

else:
    rol_actual = st.session_state.get("rol")

    if rol_actual == "trabajador":
        paginas_disponibles = {
            "General": [pagina_inicio],
            "Rendiciones": [pagina_nueva_rendicion, pagina_mis_rendiciones],
        }

    elif rol_actual == "administrador":
        paginas_disponibles = {
            "General": [pagina_inicio],
            "Administración": [pagina_revision, pagina_trazabilidad],
        }

    else:
        st.error("La cuenta no tiene un rol válido configurado.")

        if st.button("Cerrar sesión", use_container_width=True):
            cerrar_sesion()

        st.stop()

    # El menú propio reemplaza al de Streamlit para poder darle estilo.
    navegacion = st.navigation(paginas_disponibles, position="hidden")
    mostrar_barra_lateral(paginas_disponibles, navegacion)


navegacion.run()