import bcrypt
import streamlit as st

from database import obtener_cliente_supabase


def inicializar_sesion() -> None:
    """
    Crea las variables de sesión necesarias cuando la aplicación inicia.
    """
    valores_iniciales = {
        "autenticado": False,
        "usuario_id": None,
        "empresa_id": None,
        "nombre": None,
        "correo": None,
        "rol": None,
    }

    for clave, valor in valores_iniciales.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def verificar_password(password_ingresada: str, password_hash: str) -> bool:
    """
    Compara la contraseña ingresada con el hash almacenado en Supabase.
    """
    try:
        return bcrypt.checkpw(
            password_ingresada.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def autenticar_usuario(correo: str, password: str) -> dict | None:
    """
    Busca un usuario activo y verifica su contraseña.
    Retorna sus datos si la autenticación es correcta.
    """
    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.table("usuarios")
        .select(
            "id, empresa_id, nombre, correo, password_hash, rol, activo"
        )
        .eq("correo", correo.strip().lower())
        .eq("activo", True)
        .limit(1)
        .execute()
    )

    if not respuesta.data:
        return None

    usuario = respuesta.data[0]

    if not verificar_password(password, usuario["password_hash"]):
        return None

    # No devolvemos el hash al resto de la aplicación.
    usuario.pop("password_hash", None)

    return usuario


def iniciar_sesion(usuario: dict) -> None:
    """
    Guarda los datos del usuario autenticado en la sesión de Streamlit.
    """
    st.session_state["autenticado"] = True
    st.session_state["usuario_id"] = usuario["id"]
    st.session_state["empresa_id"] = usuario["empresa_id"]
    st.session_state["nombre"] = usuario["nombre"]
    st.session_state["correo"] = usuario["correo"]
    st.session_state["rol"] = usuario["rol"]


def cerrar_sesion() -> None:
    """
    Elimina los datos del usuario y reinicia la aplicación.
    """
    claves = [
        "autenticado",
        "usuario_id",
        "empresa_id",
        "nombre",
        "correo",
        "rol",
    ]

    for clave in claves:
        st.session_state.pop(clave, None)

    inicializar_sesion()
    st.rerun()


def usuario_autenticado() -> bool:
    return bool(st.session_state.get("autenticado", False))


def exigir_autenticacion() -> None:
    """
    Detiene una página si no existe una sesión válida.
    """
    inicializar_sesion()

    if not usuario_autenticado():
        st.warning("Debes iniciar sesión para acceder a este módulo.")
        st.page_link("app.py", label="Ir al inicio de sesión", icon="🔐")
        st.stop()


def exigir_rol(roles_permitidos: list[str]) -> None:
    """
    Detiene la página si el usuario no tiene un rol autorizado.
    """
    exigir_autenticacion()

    rol_actual = st.session_state.get("rol")

    if rol_actual not in roles_permitidos:
        st.error("No tienes permisos para acceder a este módulo.")
        st.stop()


def mostrar_sidebar_usuario() -> None:
    """
    Muestra información básica de la sesión y el cierre de sesión.
    """
    if usuario_autenticado():
        with st.sidebar:
            st.divider()
            st.write(f"**Usuario:** {st.session_state['nombre']}")
            st.write(f"**Rol:** {st.session_state['rol'].capitalize()}")

            if st.button(
                "Cerrar sesión",
                type="secondary",
                use_container_width=True,
            ):
                cerrar_sesion()