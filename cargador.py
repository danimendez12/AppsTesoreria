from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import openpyxl
import models

logger = logging.getLogger(__name__)


# ── Excepciones propias ───────────────────────────────────────────────────────

class CargadorError(Exception):
    """Error base del módulo."""


class ArchivoInvalidoError(CargadorError):
    """El archivo Excel no existe o no se puede abrir."""


class EstrategiaError(CargadorError):
    """Error de configuración de estrategia."""


# ── Configuración de la cuenta debitora ──────────────────────────────────────

@dataclass(frozen=True)
class CuentaDebito:
    """Datos fijos de la cuenta origen."""
    oficina_apertura: str   = "075"
    producto: str           = "100"
    moneda: str             = "01"
    numero_de_cuenta: str   = "006662"
    digito_verificador: str = "1"
    numero_comprobante: str = "00000001"
    id_unico: str           = "023232"
    id_clientes: str        = "000400004214500"
    cuenta_IBAN: str        = "CR41015107510010066624"


CUENTA_DEBITO = CuentaDebito()


# ── Estrategia de procesamiento ───────────────────────────────────────────────

class EstrategiaTransferencia(ABC):
    """Define cómo construir cada pieza del envío según el tipo (normal / SIN)."""

    @abstractmethod
    def construir_credito(self, monto: float, cuenta: str, carne: str, banco: str) -> models.BaseRecord | None:
        """Retorna un registro de crédito o None si la fila debe ignorarse."""

    @abstractmethod
    def construir_debito(self, nombre_archivo: str, sumatoria_monto: float) -> models.BaseRecord:
        """Retorna el registro de débito global."""

    @abstractmethod
    def construir_encabezado(self, sumatoria_monto: float, sumatoria_correlativos: int) -> models.BaseRecord:
        """Retorna el encabezado de la transacción."""

    @abstractmethod
    def construir_control(self, sumatoria_monto: float, sumatoria_correlativos: int) -> models.BaseRecord:
        """Retorna el registro de control."""

    # ── Helpers compartidos ───────────────────────────────────────────────────

    @staticmethod
    def _monto_entero(monto: float) -> int:
        return int(round(monto * 100))

    @staticmethod
    def validacion_fila(
        carne: str,
        identificacion: str,
        monto: float,
        banco: str,
        cuenta: str,
        estrategia: EstrategiaTransferencia,
    ) -> str | None:
        if not banco or banco.upper() == "NO ASIGNADO":
            return "Banco no asignado"
        if monto <= 0:
            return "Monto debe ser mayor a 0"
        if isinstance(estrategia, EstrategiaNormal) and (not cuenta or len(cuenta) != 15):
            return "Cuenta debe tener exactamente 15 dígitos"
        if isinstance(estrategia, EstrategiaSIN) and (not cuenta or len(cuenta) < 20):
            return "Cuenta IBAN debe tener al menos 20 caracteres"
        if not carne:
            return "Carné es obligatorio"
        if not identificacion:
            return "Identificación es obligatoria"
        return None


# ── Estrategia normal ─────────────────────────────────────────────────────────

class EstrategiaNormal(EstrategiaTransferencia):

    def construir_credito(self, monto: float, cuenta: str, carne: str, banco: str) -> models.Credito:
        monto = float(monto)
        cuenta = str(cuenta)
        carne = str(carne)
        banco = str(banco)

        return models.Credito(
            producto           = cuenta[:3],
            moneda             = cuenta[3:5],
            oficina_apertura   = cuenta[5:8],
            numero_de_cuenta   = cuenta[8:14],
            digito_verificador = cuenta[14],
            numero_comprobante = carne[2:10],
            monto              = str(self._monto_entero(monto)),
            concepto_pago      = f"CARNE: {carne}",
        )

    def construir_debito(self, nombre_archivo: str, sumatoria_monto: float) -> models.Debito:
        c = CUENTA_DEBITO
        fecha = datetime.now().strftime("%d/%m/%Y")
        return models.Debito(
            oficina_apertura   = c.oficina_apertura,
            producto           = c.producto,
            moneda             = c.moneda,
            numero_de_cuenta   = c.numero_de_cuenta,
            digito_verificador = c.digito_verificador,
            numero_comprobante = c.numero_comprobante,
            monto              = str(self._monto_entero(sumatoria_monto)),
            concepto_pago      = f"{nombre_archivo}{fecha}",
        )

    def construir_encabezado(self, sumatoria_monto: float, sumatoria_correlativos: int) -> models.Encabezado:
        return models.Encabezado(
            tipo                      = "1",
            num_cliente               = CUENTA_DEBITO.id_unico,
            fecha                     = datetime.now().strftime("%d%m%Y"),
            num_transferencia_real    = "000000",
            num_transferencia_interna = "000000",
            tipo_transaccion          = "1",
            codigo_error              = "0000",
            total_transferencia       = "000000000000",
            tipo_cambio_compra_dia    = "000000",
            tipo_cambio_venta_dia     = "0000000",
            campo_sin_uso             = "",
        )

    def construir_control(self, sumatoria_monto: float, sumatoria_correlativos: int) -> models.RegistroControl:
        return models.RegistroControl(
            tipo                   = "4",
            sumatoria_montos       = str(self._monto_entero(sumatoria_monto)),
            sumatoria_correlativos = str(sumatoria_correlativos),
            test_key               = "",
            monto_en_dolares       = "",
            monto_en_colones       = "",
            campo_sin_uso          = "",
        )


# ── Estrategia SIN ────────────────────────────────────────────────────────────

class EstrategiaSIN(EstrategiaTransferencia):
    """
    CORRECCIÓN: `_num_linea` era un atributo de clase con `field()` (sintaxis de
    dataclass), lo que causaba un AttributeError en tiempo de ejecución.
    Se mueve al `__init__` como atributo de instancia.
    """

    def __init__(self) -> None:
        self._num_linea: int = 2

    def _next_linea(self) -> str:
        val = self._num_linea
        self._num_linea += 1
        return str(val)

    def construir_credito(self, monto: float, cuenta: str, carne: str, banco: str) -> models.RegistroCreditoSIN | None:
        monto = float(monto)
        iban = str(cuenta).strip()
        banco = str(banco).strip()

        if iban.upper().startswith("CR"):
            iban = iban[2:]

        carne_str = str(carne)
        concepto = f"CARNE: {carne_str}"

        # El banco se determina por el prefijo del IBAN (posiciones 2-5 tras quitar "CR")
        # BN = Banco Nacional → código de banco "02"
        # Para generalizar, tipo "1" = mismo banco, "2" = interbancario
        if banco == "BN" or banco == "Banco Nacional" or banco == "BNCR": tipo = "1"
        else: tipo = "2"  

        return models.RegistroCreditoSIN(
            num_linea            = self._next_linea(),
            tipo_procesamiento   = tipo,
            numero_cuenta_iban   = iban,
            numero_comprobante   = carne_str[2:10],
            monto                = str(self._monto_entero(monto)),
            moneda               = "01",
            concepto             = concepto,
            estado_registro      = "00",
            tipo_id_beneficiario = "2",
            id_beneficiario      = carne_str,
            detalle_especial     = concepto,
        )

    def construir_debito(self, nombre_archivo: str, sumatoria_monto: float) -> models.RegistroDebitoSIN:
        c = CUENTA_DEBITO
        iban_debito = c.cuenta_IBAN
        if iban_debito.upper().startswith("CR"):
            iban_debito = iban_debito[2:]
        fecha = datetime.now().strftime("%d/%m/%Y")

        return models.RegistroDebitoSIN(
            num_linea            = "1",
            tipo_procesamiento   = "1",
            numero_cuenta_iban   = iban_debito,
            numero_comprobante   = c.numero_comprobante,
            monto                = str(self._monto_entero(sumatoria_monto)),
            moneda               = "01",
            concepto             = f"{nombre_archivo}{fecha}",
            estado_registro      = "00",
            tipo_id_beneficiario = "",
            id_beneficiario      = "",
            detalle_especial     = "",
        )

    def construir_encabezado(self, sumatoria_monto: float, sumatoria_correlativos: int) -> models.EncabezadoSIN:
        c = CUENTA_DEBITO
        return models.EncabezadoSIN(
            tipo                      = "1",
            id_unica_cliente          = c.id_unico,
            tipo_id_cliente           = "0",
            id_cliente                = c.id_clientes,
            fecha                     = datetime.now().strftime("%d%m%Y"),
            numero_transferencia_real = "00000",
            tipo_transaccion          = "1",
            codigo_respuesta          = "0000",
            codigo_error              = "0000",
            monto_total_SFB           = "0000000000000000",
            monto_total_sin           = "0000000000000000",
            tipo_cambio_compra        = "0000000",
            tipo_cambio_venta         = "0000000",
            sumatoria_montos          = str(self._monto_entero(sumatoria_monto)).zfill(16),
            sumatoria_correlativos    = str(sumatoria_correlativos).zfill(10),
        )

    def construir_control(self, sumatoria_monto: float, sumatoria_correlativos: int) -> models.RegistroControlSIN:
        return models.RegistroControlSIN(testkey="")


# ── Helpers internos ──────────────────────────────────────────────────────────

def _safe_key(val):
    if val is None:
        return (True, 0)
    try:
        return (False, int(val))
    except (ValueError, TypeError):
        return (False, str(val))


def _ordenar_tabla(tabla, key_col: int = 0):
    filas = [
        fila
        for fila in tabla.iter_rows(min_row=2, values_only=True)
        if any(celda is not None and str(celda).strip() != "" for celda in fila)
    ]

    filas_con_indice = [(i + 2, fila) for i, fila in enumerate(filas)]
    filas_con_indice.sort(key=lambda x: _safe_key(x[1][key_col]))

    tabla.delete_rows(2, tabla.max_row)
    for _, fila in filas_con_indice:
        tabla.append(fila)

    return tabla, filas_con_indice


def normalizar_cuenta(cuenta) -> str:
    if cuenta is None:
        return ""
    return str(cuenta).replace("-", "").replace(" ", "").strip()


# ── Cargador principal ────────────────────────────────────────────────────────

def cargar_registros(
    archivo_excel: str,
    estrategia: EstrategiaTransferencia,
    tipo_pago: int,
) -> tuple[list, float, int, dict[int, str]]:
    """
    Lee el Excel y construye los registros usando la estrategia indicada.

    Retorna:
        (registros, sumatoria_monto, sumatoria_correlativos, errores)

    Lanza:
        ArchivoInvalidoError  – si el archivo no existe o no se puede abrir.
        EstrategiaError       – si `tipo_pago` no es 1 ni 2.
        CargadorError         – para cualquier otro error irrecuperable.
    """

    # ── Validaciones previas ──────────────────────────────────────────────────
    if not os.path.isfile(archivo_excel):
        raise ArchivoInvalidoError(f"El archivo no existe: {archivo_excel!r}")

    if tipo_pago not in (1, 2):
        raise EstrategiaError(f"tipo_pago debe ser 1 o 2, se recibió: {tipo_pago!r}")

    nombre = os.path.splitext(os.path.basename(archivo_excel))[0]

    try:
        wb = openpyxl.load_workbook(archivo_excel)
    except Exception as exc:
        raise ArchivoInvalidoError(f"No se pudo abrir el archivo Excel: {exc}") from exc

    # ── Índices de columna (base-0) ───────────────────────────────────────────
    if tipo_pago == 1:
        columna_carnet         = 2
        columna_identificacion = 3
        columna_monto          = 7
        columna_banco          = 12
        columna_cuenta         = 13
        key_col                = 2
    else:
        columna_carnet         = 5
        columna_identificacion = 4
        columna_monto          = 10
        columna_banco          = 8
        columna_cuenta         = 9
        key_col                = 3 if isinstance(estrategia, EstrategiaSIN) else 2

    try:
        hoja, filas_con_indice = _ordenar_tabla(wb.active, key_col=key_col)
    except Exception as exc:
        raise CargadorError(f"Error al ordenar la hoja de trabajo: {exc}") from exc

    creditos: list = []
    sumatoria_monto: float = 0.0
    sumatoria_correlativos: int = 0
    errores: dict[int, str] = {}

    for num_fila_original, row in filas_con_indice:
        # Saltar filas completamente vacías en columnas clave
        if (
            row[columna_identificacion] is None
            and row[columna_carnet] is None
        ) or row[columna_monto] is None or row[columna_banco] is None or row[columna_cuenta] is None:
            continue

        

        # ── Conversión de tipos ───────────────────────────────────────────────
        try:
            carne          = str(row[columna_carnet])
            identificacion = str(row[columna_identificacion]).strip()
            monto          = float(row[columna_monto])
            banco          = str(row[columna_banco]).strip()
            cuenta         = normalizar_cuenta(row[columna_cuenta])
        except (ValueError, TypeError) as exc:
            errores[num_fila_original] = f"Error al convertir datos: {exc},{row}"
            logger.warning("Fila %d descartada por error de conversión: %s", num_fila_original, exc)
            continue

        banco_normalizado = banco.strip().lower()
        es_bncr = banco_normalizado in ("bncr", "banco nacional", "bn")

        if isinstance(estrategia, EstrategiaNormal) and not es_bncr:
            logger.info("Fila %d descartada: %s", num_fila_original, "Banco no es BNCR para EstrategiaNormal")
            continue

        if isinstance(estrategia, EstrategiaSIN) and es_bncr:
            logger.info("Fila %d descartada: %s", num_fila_original, "Banco es BNCR para EstrategiaSIN")
            continue
        # ── Validación de negocio ─────────────────────────────────────────────
        error = EstrategiaTransferencia.validacion_fila(
            str(carne), identificacion, monto, banco, cuenta, estrategia
        )
        if error:
            errores[num_fila_original] = error
            logger.info("Fila %d descartada: %s", num_fila_original, error)
            continue

        # ── Construcción del crédito ──────────────────────────────────────────
        try:
            registro = estrategia.construir_credito(monto, cuenta, carne,banco)
        except Exception as exc:
            errores[num_fila_original] = f"Error al construir crédito: {exc}"
            logger.exception("Fila %d – error inesperado al construir crédito", num_fila_original)
            continue

        if registro is None:
            continue

        numero_de_cuenta = cuenta[8:14]
        sumatoria_monto += monto
        sumatoria_correlativos += int(numero_de_cuenta) if numero_de_cuenta.isdigit() else 0

        creditos.append(registro)

    if not creditos:
        logger.warning("No se generó ningún crédito válido. Errores: %s", errores)

    # ── Registro de débito ────────────────────────────────────────────────────
    try:
        debito = estrategia.construir_debito(nombre, sumatoria_monto)
    except Exception as exc:
        raise CargadorError(f"Error al construir el débito: {exc}") from exc

    
    sumatoria_monto += sumatoria_monto        
    # sumatoria_monto_total = sumatoria_monto + sumatoria_monto_debito
    # Como el débito tiene el mismo monto que la suma de créditos, el total es el doble.

    sumatoria_correlativos += int(CUENTA_DEBITO.numero_de_cuenta)

    registros = [debito] + creditos

    return registros, sumatoria_monto, sumatoria_correlativos, errores


# ── Generador de TXT ──────────────────────────────────────────────────────────

def generar_txt(
    suma_monto: float,
    suma_corr: int,
    estrategia: EstrategiaTransferencia,
    registros: list[models.BaseRecord],
) -> str:
    """Recibe los datos ya procesados y retorna el string listo para enviar."""

    try:
        encabezado = estrategia.construir_encabezado(suma_monto, suma_corr)
        control    = estrategia.construir_control(suma_monto, suma_corr)
    except Exception as exc:
        raise CargadorError(f"Error al construir encabezado/control: {exc}") from exc

    transaccion = models.Transaccion(
        encabezado       = encabezado,
        registros        = registros,
        registro_control = control,
    )

    try:
        return transaccion.to_env()
    except Exception as exc:
        raise CargadorError(f"Error al serializar la transacción: {exc}") from exc