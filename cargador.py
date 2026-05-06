# cargador.py
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass, field
import os

import openpyxl
import models


# ── Configuración de la cuenta debitora ──────────────────────────────────────

@dataclass(frozen=True)
class CuentaDebito:
    """Datos fijos de la cuenta origen. Cambiá los valores acá si cambian."""
    oficina_apertura: str = "075"
    producto: str       = "100"
    moneda: str         = "01"
    numero_de_cuenta: str = "006662"
    digito_verificador: str = "1"
    numero_comprobante: str = "00000001"
    id_cliente: str     = "023232"   
    cuenta_IBAN: str = "CR00000000000000000000"       # usado también en encabezado


CUENTA_DEBITO = CuentaDebito()


# ── Estrategia de procesamiento ───────────────────────────────────────────────

class EstrategiaTransferencia(ABC):
    """Define cómo construir cada pieza del envío según el tipo (normal / SIN)."""

    @abstractmethod
    def construir_credito(self, row: tuple) -> models.BaseRecord | None:
        """Retorna un registro de crédito o None si la fila debe ignorarse."""

    @abstractmethod
    def construir_debito(
        self,
        nombre_archivo: str,
        sumatoria_monto: float,
    ) -> models.BaseRecord:
        """Retorna el registro de débito global."""

    @abstractmethod
    def construir_encabezado(self,
                             sumatoria_monto: float,
                             sumatoria_correlativos: int) -> models.BaseRecord:
        """Retorna el encabezado de la transacción."""

    @abstractmethod
    def construir_control(
        self,
        sumatoria_monto: float,
        sumatoria_correlativos: int,
    ) -> models.BaseRecord:
        """Retorna el registro de control."""

    # ── Helpers compartidos ───────────────────────────────────────────────────

    @staticmethod
    def _monto_entero(monto: float) -> int:
        return int(round(monto * 100))

    @staticmethod
    def _fila_invalida(banco: str, monto: float) -> bool:
        return banco == "NO ASIGNADO" or monto <= 0


# ── Estrategia normal ─────────────────────────────────────────────────────────

class EstrategiaNormal(EstrategiaTransferencia):

    def construir_credito(self, row: tuple) -> models.Credito | None:
        banco  = row[4]
        monto  = float(row[3])
        if self._fila_invalida(banco, monto):
            return None

        cuenta = str(row[5])
        carne  = str(row[0])

        registro = models.Credito(
            producto           = cuenta[:3],
            moneda             = cuenta[3:5],
            oficina_apertura   = cuenta[5:8],
            numero_de_cuenta   = cuenta[8:14],
            digito_verificador = cuenta[14],
            numero_comprobante = carne[2:10],
            monto              = str(self._monto_entero(monto)),
            concepto_pago      = f"CARNE: {carne}",
        )
        return registro

    def construir_debito(
        self,
        nombre_archivo: str,
        sumatoria_monto: float,
    ) -> models.Debito:
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

    def construir_encabezado(self,
                             sumatoria_monto: float,
                             sumatoria_correlativos: int
                             ) -> models.Encabezado:
        return models.Encabezado(
            tipo                     = "1",
            num_cliente              = CUENTA_DEBITO.id_cliente,
            fecha                    = datetime.now().strftime("%d%m%Y"),
            num_transferencia_real   = "000000",
            num_transferencia_interna= "000000",
            tipo_transaccion         = "1",
            codigo_error             = "0000",
            total_transferencia      = "000000000000",
            tipo_cambio_compra_dia   = "000000",
            tipo_cambio_venta_dia    = "0000000",
            campo_sin_uso            = "",
        )

    def construir_control(
        self,
        sumatoria_monto: float,
        sumatoria_correlativos: int,
    ) -> models.RegistroControl:
        return models.RegistroControl(
            tipo                  = "4",
            sumatoria_montos      = str(self._monto_entero(sumatoria_monto)),
            sumatoria_correlativos= str(sumatoria_correlativos),
            test_key              = "",
            monto_en_dolares      = "",
            monto_en_colones      = "",
            campo_sin_uso         = "",
        )


# ── Estrategia SIN ────────────────────────────────────────────────────────────

class EstrategiaSIN(EstrategiaTransferencia):

    # num_linea se incrementa por cada registro SIN
    _contador_linea: int = field(default=1)

    def __init__(self):
        self._num_linea = 2

    def _next_linea(self) -> str:
        val = self._num_linea
        self._num_linea += 1
        return str(val)

    def construir_credito(self, row: tuple) -> models.RegistroCreditoSIN | None:
        banco = row[4]
        monto = float(row[3])
        if self._fila_invalida(banco, monto):
            return None

        iban  = str(row[5])   # misma columna, formato CR21...
        carne = str(row[0])
        cedula = str(row[1])
        concepto = str(row[6]) if len(row) > 6 and row[6] else f"CARNE: {carne}"
        detalle_especial = str(row[8]) if len(row) > 8 and row[8] else concepto
        if banco == "BN": tipo = "1"
        else: tipo = "2"

        return models.RegistroCreditoSIN(
            num_linea            = self._next_linea(),
            tipo_procesamiento   = tipo,
            numero_cuenta_iban   = iban,
            numero_comprobante   = carne[2:10],
            monto                = str(self._monto_entero(monto)),
            moneda               = "01",
            concepto             = concepto,
            estado_registro      = "00",
            tipo_id_beneficiario = "2",
            id_beneficiario      = cedula,
            detalle_especial     = detalle_especial,
        )

    def construir_debito(
        self,
        nombre_archivo: str,
        sumatoria_monto: float,
    ) -> models.RegistroDebitoSIN:
        c = CUENTA_DEBITO
        # SIN usa IBAN para débito; el 006662 se embebe en el IBAN de tu institución
        # Ajustá iban_debito si tenés el IBAN completo de esa cuenta
        iban_debito = c.cuenta_IBAN.zfill(22)
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

    def construir_encabezado(self,
                             sumatoria_monto: float,
                             sumatoria_correlativos: int
                             ) -> models.EncabezadoSIN:
        c = CUENTA_DEBITO
        return models.EncabezadoSIN(
            tipo                     = "1",
            id_unica_cliente         = c.id_cliente,
            tipo_id_cliente          = "0",
            id_cliente               = c.id_cliente,
            fecha                    = datetime.now().strftime("%d%m%Y"),
            numero_transferencia_real= "00000",
            tipo_transaccion         = "1",
            codigo_respuesta         = "0000",
            codigo_error             = "0000",
            monto_total_SFB          = "0000000000000000",
            monto_total_sin          = "0000000000000000",
            tipo_cambio_compra       = "0000000",
            tipo_cambio_venta        = "0000000",
            sumatoria_montos         = "0000000000000000",
            sumatoria_correlativos   = "0000000000",
        )

    def construir_control(
        self,
        sumatoria_monto: float,
        sumatoria_correlativos: int,
    ) -> models.RegistroControlSIN:
        return models.RegistroControlSIN(testkey="")


# ── Cargador principal ────────────────────────────────────────────────────────

def _ordenar_tabla(tabla, key_col: int = 0):
    filas = list(tabla.iter_rows(min_row=2, values_only=True))
    filas.sort(key=lambda x: x[key_col])
    tabla.delete_rows(2, tabla.max_row)
    for fila in filas:
        tabla.append(fila)
    return tabla


def cargar_registros(
    archivo_excel: str,
    estrategia: EstrategiaTransferencia,
) -> tuple[list, float, int]:
    """
    Lee el Excel y construye los registros usando la estrategia indicada.
    Retorna (registros, sumatoria_monto, sumatoria_correlativos).
    """
    nombre = os.path.splitext(os.path.basename(archivo_excel))[0]
    wb = openpyxl.load_workbook(archivo_excel)
    hoja = _ordenar_tabla(wb.active, key_col=1 if estrategia.__class__ == EstrategiaSIN else 0)  # ordena por IBAN para SIN, por banco para normal

    creditos            = []
    sumatoria_monto     = 0.0
    sumatoria_correlativos = 0

    for row in hoja.iter_rows(min_row=2, values_only=True):
        registro = estrategia.construir_credito(row)
        if registro is None:
            continue

        monto  = float(row[3])
        cuenta = str(row[5])
        numero_de_cuenta = cuenta[8:14]   # para normal; SIN lo ignora en sumatoria

        sumatoria_monto        += monto
        sumatoria_correlativos += int(numero_de_cuenta) if numero_de_cuenta.isdigit() else 0
        creditos.append(registro)

    debito = estrategia.construir_debito(nombre, sumatoria_monto)

    # El débito también suma (igual que antes)
    sumatoria_monto        += float(sumatoria_monto)   # duplica como en el original
    sumatoria_correlativos += int(CUENTA_DEBITO.numero_de_cuenta)

    registros = [debito] + creditos
    return registros, sumatoria_monto, sumatoria_correlativos


def generar_txt(
    suma_monto: float,
    suma_corr: int,
    estrategia: EstrategiaTransferencia,
    registros: list[models.BaseRecord],
) -> str:
    """Punto de entrada único: recibe el archivo y la estrategia, retorna el string listo."""

    transaccion = models.Transaccion(
        encabezado      = estrategia.construir_encabezado(suma_monto, suma_corr),
        registros       = registros,
        registro_control= estrategia.construir_control(suma_monto, suma_corr),
    )
    return transaccion.to_env()