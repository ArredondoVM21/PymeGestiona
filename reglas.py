from datetime import date


def validar_campos_obligatorios(datos: dict) -> list[str]:
    """
    R5: identifica campos obligatorios vacíos o inválidos.
    """
    campos_texto = {
        "tipo_documento": "Tipo de documento",
        "rut_emisor": "RUT del emisor",
        "proveedor": "Proveedor",
        "folio": "Folio",
        "fecha_documento": "Fecha del documento",
        "categoria": "Categoría",
    }

    faltantes = []

    for campo, nombre_visible in campos_texto.items():
        valor = datos.get(campo)

        if valor is None:
            faltantes.append(nombre_visible)

        elif isinstance(valor, str) and not valor.strip():
            faltantes.append(nombre_visible)

    monto_total = datos.get("monto_total")

    if monto_total is None or float(monto_total) <= 0:
        faltantes.append("Monto total")

    return faltantes


def evaluar_monto(
    monto_total: float,
    limite: float,
) -> dict | None:
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
    R3: alerta si el documento excede su antigüedad permitida
    o tiene una fecha futura.
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
            "mensaje": (
                "La fecha del documento no puede ser futura."
            ),
        }

    return None


def evaluar_archivo(
    archivo_cargado: bool,
) -> dict | None:
    """
    R4: bloquea una rendición sin documento de respaldo.
    """
    if not archivo_cargado:
        return {
            "codigo": "R4",
            "nivel": "Alto",
            "mensaje": (
                "La rendición no contiene un documento de respaldo."
            ),
        }

    return None


def evaluar_consistencia_montos(
    monto_neto: float,
    iva: float,
    monto_total: float,
) -> dict | None:
    """
    R6: comprueba que Neto + IVA sea igual al Total.

    Una diferencia igual o superior a $1 se considera inconsistente.
    """
    neto = float(monto_neto)
    monto_iva = float(iva)
    total_informado = float(monto_total)

    total_calculado = neto + monto_iva
    diferencia = abs(total_calculado - total_informado)

    if diferencia >= 1:
        return {
            "codigo": "R6",
            "nivel": "Alto",
            "mensaje": (
                f"El monto neto más el IVA corresponde a "
                f"${total_calculado:,.0f}, pero el total informado "
                f"es ${total_informado:,.0f}. "
                f"Diferencia detectada: ${diferencia:,.0f}."
            ),
        }

    return None


def determinar_nivel_riesgo(
    alertas: list[dict],
) -> str:
    """
    Calcula el nivel general según las alertas detectadas.
    """
    niveles = [
        alerta["nivel"]
        for alerta in alertas
    ]

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
    Ejecuta las reglas locales R2, R3, R4, R5 y R6.

    R1 se ejecuta consultando Supabase, porque requiere buscar
    documentos anteriores con igual RUT, tipo y folio.
    """
    alertas = []

    # R5: campos obligatorios.
    faltantes = validar_campos_obligatorios(datos)

    if faltantes:
        alertas.append(
            {
                "codigo": "R5",
                "nivel": "Alto",
                "mensaje": (
                    "Faltan campos obligatorios o válidos: "
                    + ", ".join(faltantes)
                    + "."
                ),
            }
        )

    # R2: monto superior al límite.
    if datos.get("monto_total") is not None:
        alerta_monto = evaluar_monto(
            monto_total=float(datos["monto_total"]),
            limite=float(limite),
        )

        if alerta_monto:
            alertas.append(alerta_monto)

    # R6: consistencia de Neto + IVA = Total.
    if (
        datos.get("monto_neto") is not None
        and datos.get("iva") is not None
        and datos.get("monto_total") is not None
    ):
        alerta_consistencia = evaluar_consistencia_montos(
            monto_neto=float(datos["monto_neto"]),
            iva=float(datos["iva"]),
            monto_total=float(datos["monto_total"]),
        )

        if alerta_consistencia:
            alertas.append(alerta_consistencia)

    # R3: antigüedad o fecha futura.
    if datos.get("fecha_documento"):
        alerta_fecha = evaluar_fecha(
            fecha_documento=datos["fecha_documento"],
            dias_maximos=dias_maximos,
        )

        if alerta_fecha:
            alertas.append(alerta_fecha)

    # R4: documento de respaldo.
    alerta_archivo = evaluar_archivo(archivo_cargado)

    if alerta_archivo:
        alertas.append(alerta_archivo)

    codigos_bloqueantes = {
        "R4",
        "R5",
        "R6",
    }

    puede_enviar = not any(
        alerta["codigo"] in codigos_bloqueantes
        for alerta in alertas
    )

    return {
        "alertas": alertas,
        "nivel_riesgo": determinar_nivel_riesgo(alertas),
        "puede_enviar": puede_enviar,
    }