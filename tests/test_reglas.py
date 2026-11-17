from datetime import date, timedelta

import pytest

from reglas import (
    validar_campos_obligatorios,
    evaluar_monto,
    evaluar_fecha,
    evaluar_archivo,
    evaluar_consistencia_montos,
    evaluar_reglas_locales,
    determinar_nivel_riesgo,
    normalizar_rut,
    normalizar_folio,
    validar_rut,
    validar_folio,
    MONTO_MAXIMO,
)


# =========================================================
# DATOS DE PRUEBA
# =========================================================

LIMITE = 200000
DIAS_MAXIMOS = 30


def datos_validos(**cambios) -> dict:
    """
    Rendición válida que no activa ninguna regla.
    Cada prueba modifica solo el campo que quiere evaluar.
    """
    datos = {
        "tipo_documento": "Boleta",
        "rut_emisor": "76.123.456-0",
        "proveedor": "Ferretería Demo",
        "folio": "123",
        "fecha_documento": date.today(),
        "categoria": "Materiales",
        "monto_neto": 100000,
        "iva": 19000,
        "monto_total": 119000,
    }
    datos.update(cambios)
    return datos


def evaluar(datos: dict, archivo_cargado: bool = True) -> dict:
    return evaluar_reglas_locales(
        datos=datos,
        limite=LIMITE,
        dias_maximos=DIAS_MAXIMOS,
        archivo_cargado=archivo_cargado,
    )


def codigos(resultado: dict) -> set[str]:
    return {alerta["codigo"] for alerta in resultado["alertas"]}


# =========================================================
# R1: NORMALIZACIÓN DE RUT Y FOLIO
# =========================================================

@pytest.mark.parametrize(
    "entrada",
    ["76.123.456-0", "76123456-0", "761234560", " 76.123.456 - 0 "],
)
def test_r1_rut_con_distinto_formato_se_normaliza_igual(entrada):
    assert normalizar_rut(entrada) == "76123456-0"


def test_r1_rut_con_k_minuscula_se_normaliza_en_mayuscula():
    assert normalizar_rut("10.000.013-k") == "10000013-K"


@pytest.mark.parametrize("entrada", ["123", "000123", " 00123 "])
def test_r1_folio_con_ceros_a_la_izquierda_se_normaliza(entrada):
    assert normalizar_folio(entrada) == "123"


def test_r1_folio_solo_ceros_se_conserva():
    assert normalizar_folio("000") == "0"


# =========================================================
# VALIDACIÓN DE RUT (MÓDULO 11)
# =========================================================

@pytest.mark.parametrize(
    "rut",
    ["12.345.678-5", "11.111.111-1", "76.123.456-0", "10.000.013-K"],
)
def test_rut_valido(rut):
    assert validar_rut(rut) is True


@pytest.mark.parametrize(
    "rut",
    ["12.345.678-9", "76.123.456-7", "abc", "1-9", ""],
)
def test_rut_invalido(rut):
    assert validar_rut(rut) is False


# =========================================================
# R2: MONTO SOBRE EL LÍMITE
# =========================================================

def test_r2_monto_dentro_del_limite():
    assert evaluar_monto(100000, LIMITE) is None


def test_r2_monto_igual_al_limite_no_alerta():
    assert evaluar_monto(LIMITE, LIMITE) is None


def test_r2_monto_supera_el_limite():
    resultado = evaluar_monto(250000, LIMITE)
    assert resultado["codigo"] == "R2"
    assert resultado["nivel"] == "Medio"


# =========================================================
# R3: ANTIGÜEDAD Y FECHA FUTURA
# =========================================================

def test_r3_fecha_actual_valida():
    assert evaluar_fecha(date.today(), DIAS_MAXIMOS) is None


def test_r3_fecha_en_el_limite_es_valida():
    fecha = date.today() - timedelta(days=DIAS_MAXIMOS)
    assert evaluar_fecha(fecha, DIAS_MAXIMOS) is None


def test_r3_fecha_supera_antiguedad():
    fecha = date.today() - timedelta(days=DIAS_MAXIMOS + 1)
    resultado = evaluar_fecha(fecha, DIAS_MAXIMOS)
    assert resultado["nivel"] == "Medio"


def test_r3_fecha_futura_es_riesgo_alto():
    fecha = date.today() + timedelta(days=1)
    resultado = evaluar_fecha(fecha, DIAS_MAXIMOS)
    assert resultado["codigo"] == "R3"
    assert resultado["nivel"] == "Alto"


# =========================================================
# R4: COMPROBANTE
# =========================================================

def test_r4_comprobante_adjuntado():
    assert evaluar_archivo(True) is None


def test_r4_sin_comprobante():
    assert evaluar_archivo(False)["codigo"] == "R4"


# =========================================================
# R5: CAMPOS OBLIGATORIOS
# =========================================================

def test_r5_datos_completos_no_faltan_campos():
    assert validar_campos_obligatorios(datos_validos()) == []


def test_r5_detecta_campos_obligatorios_vacios():
    assert len(validar_campos_obligatorios({})) > 0


def test_r5_detecta_texto_solo_con_espacios():
    faltantes = validar_campos_obligatorios(datos_validos(proveedor="   "))
    assert "Proveedor" in faltantes


def test_r5_monto_cero_no_es_valido():
    faltantes = validar_campos_obligatorios(datos_validos(monto_total=0))
    assert "Monto total" in faltantes


def test_r5_rut_con_digito_verificador_invalido():
    faltantes = validar_campos_obligatorios(
        datos_validos(rut_emisor="76.123.456-7")
    )
    assert any("RUT" in campo for campo in faltantes)


# =========================================================
# R6: CONSISTENCIA DE MONTOS
# =========================================================

def test_r6_montos_consistentes():
    assert evaluar_consistencia_montos(100000, 19000, 119000) is None


def test_r6_diferencia_menor_a_un_peso_se_tolera():
    assert evaluar_consistencia_montos(100000, 19000, 119000.5) is None


def test_r6_montos_inconsistentes():
    resultado = evaluar_consistencia_montos(100000, 19000, 90000)
    assert resultado["codigo"] == "R6"


# =========================================================
# EVALUACIÓN COMPLETA Y NIVEL DE RIESGO
# =========================================================

def test_rendicion_valida_puede_enviarse_con_riesgo_bajo():
    resultado = evaluar(datos_validos())
    assert resultado["alertas"] == []
    assert resultado["nivel_riesgo"] == "Bajo"
    assert resultado["puede_enviar"] is True


def test_r2_no_bloquea_el_envio():
    resultado = evaluar(
        datos_validos(monto_neto=210084, iva=39916, monto_total=250000)
    )
    assert codigos(resultado) == {"R2"}
    assert resultado["nivel_riesgo"] == "Medio"
    assert resultado["puede_enviar"] is True


@pytest.mark.parametrize(
    "datos, archivo, regla",
    [
        (datos_validos(), False, "R4"),
        (datos_validos(proveedor=""), True, "R5"),
        (datos_validos(monto_total=90000), True, "R6"),
    ],
)
def test_reglas_bloqueantes_impiden_el_envio(datos, archivo, regla):
    resultado = evaluar(datos, archivo_cargado=archivo)
    assert regla in codigos(resultado)
    assert resultado["nivel_riesgo"] == "Alto"
    assert resultado["puede_enviar"] is False


def test_nivel_de_riesgo_toma_el_mayor():
    alertas = [{"nivel": "Medio"}, {"nivel": "Alto"}]
    assert determinar_nivel_riesgo(alertas) == "Alto"


# =========================================================
# LÍMITES DE CAMPOS (formato SII y OWASP)
# =========================================================

@pytest.mark.parametrize("folio", ["1", "48211", "9999999999"])
def test_folio_numerico_valido_en_boletas_y_facturas(folio):
    assert validar_folio(folio, "Boleta") is None
    assert validar_folio(folio, "Factura") is None


@pytest.mark.parametrize("folio", ["2e21321rtdq2q", "ABC-12", "12.345"])
def test_folio_con_letras_no_valido_en_boleta(folio):
    assert validar_folio(folio, "Boleta") is not None


def test_folio_de_mas_de_10_digitos_no_valido():
    assert validar_folio("12345678901", "Factura") is not None


def test_folio_cero_no_valido():
    assert validar_folio("0000", "Boleta") is not None


def test_comprobante_acepta_folio_alfanumerico():
    assert validar_folio("DEMO-R6-001", "Comprobante") is None


def test_comprobante_rechaza_folio_de_mas_de_20_caracteres():
    assert validar_folio("X" * 21, "Otro") is not None


def test_r5_bloquea_folio_invalido():
    faltantes = validar_campos_obligatorios(datos_validos(folio="2e21321rtdq2q"))
    assert any("Folio" in campo for campo in faltantes)


def test_r5_bloquea_proveedor_de_mas_de_100_caracteres():
    faltantes = validar_campos_obligatorios(datos_validos(proveedor="A" * 101))
    assert any("Proveedor" in campo for campo in faltantes)


def test_r5_bloquea_monto_sobre_el_maximo():
    faltantes = validar_campos_obligatorios(
        datos_validos(monto_neto=MONTO_MAXIMO, iva=1, monto_total=MONTO_MAXIMO + 1)
    )
    assert any("máximo" in campo for campo in faltantes)