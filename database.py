import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def obtener_cliente_supabase() -> Client:
    """
    Crea una conexión reutilizable con Supabase.
    Las credenciales se leen desde Streamlit Secrets.
    """
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    return create_client(url, key)


def comprobar_conexion() -> dict:
    """
    Comprueba la conexión contando empresas y usuarios.
    """
    cliente = obtener_cliente_supabase()

    respuesta_empresas = (
        cliente.table("empresas")
        .select("id", count="exact")
        .limit(1)
        .execute()
    )

    respuesta_usuarios = (
        cliente.table("usuarios")
        .select("id", count="exact")
        .limit(1)
        .execute()
    )

    return {
        "empresas": respuesta_empresas.count or 0,
        "usuarios": respuesta_usuarios.count or 0,
    }