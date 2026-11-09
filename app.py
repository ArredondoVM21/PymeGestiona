import streamlit as st

from auth import (
    autenticar_usuario,
    cerrar_sesion,
    iniciar_sesion,
    inicializar_sesion,
    usuario_autenticado,
)
from database import comprobar_conexion


st.set_page_config(
    page_title="PymeGestiona",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


inicializar_sesion()


def mostrar_login() -> None:
    st.title("📊 PymeGestiona")
    st.subheader("Sistema de gestión y control de rendiciones")

    st.success("Prototipo funcional desplegado en la nube")

    with st.form("formulario_login"):
        st.subheader("🔐 Inicio de sesión")

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

    if ingresar:
        if not correo.strip() or not password:
            st.warning("Debes ingresar el correo y la contraseña.")
            return

        try:
            usuario = autenticar_usuario(correo, password)

            if usuario is None:
                st.error("Correo o contraseña incorrectos.")
                return

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
            **Trabajador**

            - Correo: `trabajador@pymegestiona.cl`
            - Contraseña: `Demo1234!`

            **Administrador**

            - Correo: `admin@pymegestiona.cl`
            - Contraseña: `Admin1234!`

            Estas cuentas contienen exclusivamente datos demostrativos.
            """
        )


def mostrar_inicio() -> None:
    with st.sidebar:
        st.header("Sesión activa")
        st.write(f"**Usuario:** {st.session_state['nombre']}")
        st.write(
            f"**Rol:** {st.session_state['rol'].capitalize()}"
        )

        if st.button(
            "Cerrar sesión",
            type="secondary",
            use_container_width=True,
        ):
            cerrar_sesion()

    st.title("📊 PymeGestiona")

    st.success(
        f"Bienvenido/a, {st.session_state['nombre']}."
    )

    try:
        estado_db = comprobar_conexion()

        st.caption(
            f"Supabase conectado: "
            f"{estado_db['empresas']} empresa y "
            f"{estado_db['usuarios']} usuarios."
        )

    except Exception:
        st.warning(
            "La sesión está activa, pero no fue posible comprobar "
            "el estado general de la base de datos."
        )

    st.divider()

    if st.session_state["rol"] == "trabajador":
        st.subheader("Panel del trabajador")

        columna_1, columna_2 = st.columns(2)

        with columna_1:
            st.info(
                """
                **Nueva rendición**

                Registra una boleta, factura o comprobante para
                enviarlo a revisión.
                """
            )

            st.page_link(
                "pages/nueva_rendicion.py",
                label="Crear nueva rendición",
                icon="🧾",
            )

        with columna_2:
            st.info(
                """
                **Mis rendiciones**

                Consulta el estado, observaciones y alertas de tus
                rendiciones.
                """
            )

            st.page_link(
                "pages/mis_rendiciones.py",
                label="Consultar mis rendiciones",
                icon="📋",
            )

    elif st.session_state["rol"] == "administrador":
        st.subheader("Panel administrativo")

        columna_1, columna_2 = st.columns(2)

        with columna_1:
            st.info(
                """
                **Revisión administrativa**

                Consulta rendiciones pendientes y registra una
                decisión.
                """
            )

            st.page_link(
                "pages/revision.py",
                label="Revisar rendiciones",
                icon="✅",
            )

        with columna_2:
            st.info(
                """
                **Trazabilidad**

                Consulta los cambios de estado y las acciones
                registradas.
                """
            )

            st.page_link(
                "pages/trazabilidad.py",
                label="Consultar trazabilidad",
                icon="🔎",
            )

    st.divider()

    st.caption(
        "PymeGestiona · Prototipo académico · "
        "Datos exclusivamente demostrativos"
    )


if usuario_autenticado():
    mostrar_inicio()
else:
    mostrar_login()