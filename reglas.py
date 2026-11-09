from datetime import date


def validar_campos_obligatorios(datos: dict) -> list[str]:
    """
    R5: identifica campos obligatorios vacíos.
    """
    campos = {
        "tipo_documento": "Tipo de documento",
        "rut_emisor": "RUT del emisor",
        "proveedor": "Proveedor",
        "folio": "Folio",
        "fecha_documento": "Fecha del documento",
        "categoria": "Categoría",
        "monto_total": "Monto total",
    }

    faltantes = []

    for campo, nombre_visible in campos.items():
        valor = datos.get(campo)

        if valor is None or valor == "":
            faltantes.append(nombre_visible)

    return faltantes


def evaluar_monto(monto_total: float, limite: float) -> dict | None:
    """
    R2: alerta si el monto supera el límite configurado.
    """
    if monto_total > limite:
        return {
            "codigo": "R2",
            "nivel": "Medio",
            "mensaje": (
                f"El monto ${monto_total:,.0f} supera el límite "
                f"configurado de ${limite:,.0f}."
            ),
        }

    return None


def evaluar_fecha(
    fecha_documento: date,
    dias_maximos: int,
) -> dict | None:
    """
    R3: alerta si el documento excede su antigüedad permitida.
    """
    antiguedad = (date.today() - fecha_documento).days

    if antiguedad > dias_maximos:
        return {
            "codigo": "R3",
            "nivel": "Medio",
            "mensaje": (
                f"El documento tiene {antiguedad} días de antigüedad. "
                f"El máximo permitido es {dias_maximos} días."
            ),
        }

    if antiguedad < 0:
        return {
            "codigo": "R3",
            "nivel": "Alto",
            "mensaje": "La fecha del documento no puede ser futura.",
        }

    return None


def evaluar_archivo(archivo_cargado: bool) -> dict | None:
    """
    R4: alerta cuando no existe respaldo documental.
    """
    if not archivo_cargado:
        return {
            "codigo": "R4",
            "nivel": "Alto",
            "mensaje": "La rendición no contiene un documento de respaldo.",
        }

    return None


def determinar_nivel_riesgo(alertas: list[dict]) -> str:
    """
    Calcula el nivel general según las alertas detectadas.
    """
    niveles = [alerta["nivel"] for alerta in alertas]

    if "Alto" in niveles:
        return "Alto"

    if "Medio" in niveles:
        return "Medio"

    return "Bajo"


def evaluar_reglas_locales(
    datos: dict,
    limite: float,
    dias_maximos: int,
    archivo_cargado: bool,
) -> dict:
    """
    Ejecuta R2, R3, R4 y R5.

    R1 se ejecutará consultando Supabase, porque requiere buscar
    documentos anteriores con igual RUT, tipo y """
    alertas = []

    faltantes = validar_campos_obligatorios(datos)

    if faltantes:
        alertas.append(
            {
                "codigo": "R5",
                "nivel": "Alto",
                "mensaje": (
                    "Faltan campos obligatorios: "
                    + ", ".join(faltantes)
                    + "."
                ),
            }
        )

    if datos.get("monto_total") is not None:
        alerta_monto = evaluar_monto(
            float(datos["monto_total"]),
            limite,
        )

        if alerta_monto:
            alertas.append(alerta_monto)

    if datos.get("fecha_documento"):
        alerta_fecha = evaluar_fecha(
            datos["fecha_documento"],
            dias_maximos,
        )

        if alerta_fecha:
            alertas.append(alerta_fecha)

    alerta_archivo = evaluar_archivo(archivo_cargado)

    if alerta_archivo:
        alertas.append(alerta_archivo)

    return {
        "alertas": alertas,
        "nivel_riesgo": determinar_nivel_riesgo(alertas),
        "puede_enviar": not any(
            alerta["codigo"] in ["R4", "R5"]
            for alerta in alertas
        ),
    }