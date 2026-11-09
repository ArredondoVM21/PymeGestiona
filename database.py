from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def obtener_cliente_supabase() -> Client:
    """
    Crea una conexión reutilizable con Supabase.

    Las credenciales reales se obtienen desde Streamlit Secrets.
    No deben escribirse directamente en este archivo.
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


def obtener_configuracion_empresa(
    empresa_id: int,
) -> dict | None:
    """
    Obtiene los parámetros configurados para una empresa activa.
    """
    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.table("empresas")
        .select(
            "id, razon_social, nombre_fantasia, "
            "limite_rendicion, dias_maximos_documento"
        )
        .eq("id", empresa_id)
        .eq("activa", True)
        .limit(1)
        .execute()
    )

    if not respuesta.data:
        return None

    return respuesta.data[0]


def buscar_documento_duplicado(
    empresa_id: int,
    rut_emisor: str,
    tipo_documento: str,
    folio: str,
) -> dict | None:
    """
    R1: busca una rendición con el mismo RUT, tipo y folio.
    """
    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.table("rendiciones")
        .select(
            "id, estado, proveedor, monto_total, fecha_creacion"
        )
        .eq("empresa_id", empresa_id)
        .eq("rut_emisor", rut_emisor.strip())
        .eq("tipo_documento", tipo_documento)
        .eq("folio", folio.strip())
        .limit(1)
        .execute()
    )

    if not respuesta.data:
        return None

    return respuesta.data[0]


def subir_comprobante(
    archivo,
    empresa_id: int,
    usuario_id: int,
) -> str:
    """
    Guarda un comprobante en el bucket privado comprobantes.

    Retorna la ruta interna del archivo almacenado.
    """
    cliente = obtener_cliente_supabase()

    extension = Path(archivo.name).suffix.lower()

    extensiones_permitidas = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".pdf",
    }

    if extension not in extensiones_permitidas:
        raise ValueError(
            "El tipo de archivo seleccionado no está permitido."
        )

    contenido = archivo.getvalue()

    limite_bytes = 5 * 1024 * 1024

    if len(contenido) > limite_bytes:
        raise ValueError(
            "El archivo supera el tamaño máximo permitido de 5 MB."
        )

    nombre_unico = (
        f"{datetime.now():%Y/%m}/"
        f"empresa_{empresa_id}/"
        f"usuario_{usuario_id}/"
        f"{uuid4().hex}{extension}"
    )

    opciones = {
        "content-type": archivo.type,
        "upsert": "false",
    }

    cliente.storage.from_("comprobantes").upload(
        path=nombre_unico,
        file=contenido,
        file_options=opciones,
    )

    return nombre_unico


def crear_rendicion(datos: dict) -> dict:
    """
    Inserta una rendición en Supabase y devuelve el registro creado.
    """
    cliente = obtener_cliente_supabase()

    datos_insertar = datos.copy()
    fecha_documento = datos_insertar.get("fecha_documento")

    if isinstance(fecha_documento, date):
        datos_insertar["fecha_documento"] = (
            fecha_documento.isoformat()
        )

    respuesta = (
        cliente.table("rendiciones")
        .insert(datos_insertar)
        .execute()
    )

    if not respuesta.data:
        raise RuntimeError(
            "Supabase no devolvió la rendición creada."
        )

    return respuesta.data[0]


def registrar_auditoria(
    empresa_id: int,
    rendicion_id: int,
    usuario_id: int,
    accion: str,
    estado_anterior: str | None,
    estado_nuevo: str | None,
    detalle: str,
) -> dict:
    """
    Registra una acción realizada sobre una rendición.
    """
    cliente = obtener_cliente_supabase()

    registro = {
        "empresa_id": empresa_id,
        "rendicion_id": rendicion_id,
        "usuario_id": usuario_id,
        "accion": accion,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "detalle": detalle,
    }

    respuesta = (
        cliente.table("auditoria")
        .insert(registro)
        .execute()
    )

    if not respuesta.data:
        raise RuntimeError(
            "No fue posible registrar la auditoría."
        )

    return respuesta.data[0]


def listar_rendiciones_usuario(
    empresa_id: int,
    usuario_id: int,
) -> list:
    """
    Lista las rendiciones pertenecientes al trabajador autenticado.
    """
    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.table("rendiciones")
        .select(
            "id, tipo_documento, rut_emisor, proveedor, folio, "
            "fecha_documento, categoria, descripcion, monto_neto, "
            "iva, monto_total, archivo_url, estado, nivel_riesgo, "
            "reglas_activadas, motivo_rechazo, fecha_creacion, "
            "fecha_envio, fecha_revision"
        )
        .eq("empresa_id", empresa_id)
        .eq("usuario_id", usuario_id)
        .order("fecha_creacion", desc=True)
        .execute()
    )

    return respuesta.data or []


def obtener_rendicion_usuario(
    rendicion_id: int,
    empresa_id: int,
    usuario_id: int,
) -> dict | None:
    """
    Obtiene una rendición específica perteneciente al trabajador.
    """
    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.table("rendiciones")
        .select("*")
        .eq("id", rendicion_id)
        .eq("empresa_id", empresa_id)
        .eq("usuario_id", usuario_id)
        .limit(1)
        .execute()
    )

    if not respuesta.data:
        return None

    return respuesta.data[0]


# =========================================================
# FUNCIONES ADMINISTRATIVAS
# =========================================================

def listar_rendiciones_pendientes(
    empresa_id: int,
) -> list:
    """
    Lista las rendiciones pendientes de una empresa.
    """
    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.table("rendiciones")
        .select(
            "id, empresa_id, usuario_id, tipo_documento, "
            "rut_emisor, proveedor, folio, fecha_documento, "
            "categoria, descripcion, monto_neto, iva, "
            "monto_total, archivo_url, estado, nivel_riesgo, "
            "reglas_activadas, fecha_envio"
        )
        .eq("empresa_id", empresa_id)
        .eq("estado", "Pendiente")
        .order("fecha_envio", desc=False)
        .execute()
    )

    return respuesta.data or []


def generar_url_comprobante(
    ruta_archivo: str,
    duracion_segundos: int = 600,
) -> str | None:
    """
    Genera una URL temporal para consultar un comprobante privado.
    """
    if not ruta_archivo:
        return None

    cliente = obtener_cliente_supabase()

    respuesta = (
        cliente.storage
        .from_("comprobantes")
        .create_signed_url(
            ruta_archivo,
            duracion_segundos,
        )
    )

    if not respuesta:
        return None

    if isinstance(respuesta, dict):
        return (
            respuesta.get("signedURL")
            or respuesta.get("signedUrl")
            or respuesta.get("signed_url")
        )

    # Compatibilidad con respuestas tipo objeto.
    return (
        getattr(respuesta, "signed_url", None)
        or getattr(respuesta, "signedURL", None)
    )


def resolver_rendicion(
    rendicion_id: int,
    empresa_id: int,
    administrador_id: int,
    nuevo_estado: str,
    motivo_rechazo: str | None = None,
) -> dict:
    """
    Aprueba o rechaza una rendición pendiente.

    Completa fecha_revision y revisada_por, y registra auditoría.
    """
    if nuevo_estado not in ["Aprobada", "Rechazada"]:
        raise ValueError(
            "El estado debe ser Aprobada o Rechazada."
        )

    motivo_limpio = (
        motivo_rechazo.strip()
        if motivo_rechazo
        else None
    )

    if (
        nuevo_estado == "Rechazada"
        and not motivo_limpio
    ):
        raise ValueError(
            "El motivo de rechazo es obligatorio."
        )

    cliente = obtener_cliente_supabase()

    consulta_actual = (
        cliente.table("rendiciones")
        .select("id, estado")
        .eq("id", rendicion_id)
        .eq("empresa_id", empresa_id)
        .limit(1)
        .execute()
    )

    if not consulta_actual.data:
        raise RuntimeError(
            "La rendición solicitada no existe."
        )

    estado_actual = consulta_actual.data[0]["estado"]

    if estado_actual != "Pendiente":
        raise RuntimeError(
            "La rendición ya fue revisada por otro usuario."
        )

    fecha_revision = datetime.now(
        timezone.utc
    ).isoformat()

    cambios = {
        "estado": nuevo_estado,
        "motivo_rechazo": (
            motivo_limpio
            if nuevo_estado == "Rechazada"
            else None
        ),
        "fecha_revision": fecha_revision,
        "revisada_por": administrador_id,
    }

    respuesta = (
        cliente.table("rendiciones")
        .update(cambios)
        .eq("id", rendicion_id)
        .eq("empresa_id", empresa_id)
        .eq("estado", "Pendiente")
        .execute()
    )

    if not respuesta.data:
        raise RuntimeError(
            "No fue posible actualizar la rendición. "
            "Es posible que ya haya sido revisada."
        )

    if nuevo_estado == "Aprobada":
        accion = "Rendición aprobada"
        detalle = (
            "La rendición fue aprobada por el administrador."
        )

    else:
        accion = "Rendición rechazada"
        detalle = (
            "La rendición fue rechazada. "
            f"Motivo: {motivo_limpio}"
        )

    registrar_auditoria(
        empresa_id=empresa_id,
        rendicion_id=rendicion_id,
        usuario_id=administrador_id,
        accion=accion,
        estado_anterior="Pendiente",
        estado_nuevo=nuevo_estado,
        detalle=detalle,
    )

    return respuesta.data[0]