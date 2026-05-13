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
    id_unico: str     = "023232"   
    id_clientes: str       = "000400004214500"
    cuenta_IBAN: str = "CR41015107510010066624"       # usado también en encabezado


CUENTA_DEBITO = CuentaDebito()


# ── Estrategia de procesamiento ───────────────────────────────────────────────

class EstrategiaTransferencia(ABC):
    """Define cómo construir cada pieza del envío según el tipo (normal / SIN)."""

    @abstractmethod
    def construir_credito(self, monto: float, cuenta: str, carne: str) -> models.BaseRecord | None:
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
    def _normalizar_cuenta(cuenta: str) -> str:
        if cuenta is None:
            return ""
        return str(cuenta).replace("-","").replace(" ","").strip()

    @staticmethod
    def validacion_fila(carne: str, identificacion: str, monto: float, banco: str, cuenta:str , estrategia: EstrategiaTransferencia) -> str | None:
        if banco == "NO ASIGNADO" or banco == "":
            return "Banco no asignado"
        if monto <= 0:
            return "Monto debe ser mayor a 0"
        if (estrategia.__class__ == EstrategiaNormal and (not cuenta or len(cuenta) != 15)) :
            return "Cuenta debe tener al menos 15 dígitos"
        elif (estrategia.__class__ == EstrategiaSIN and (not cuenta or len(cuenta) < 20)):
            return "Cuenta IBAN debe tener al menos 20 caracteres"
        if not carne:
            return "Carné es obligatorio"
        if not identificacion:
            return "Identificación es obligatoria"
        return None
    
    


# ── Estrategia normal ─────────────────────────────────────────────────────────

class EstrategiaNormal(EstrategiaTransferencia):
    def construir_credito(self, monto, cuenta, carne) -> models.Credito:
        monto  = float(monto)


        cuenta = self._normalizar_cuenta(cuenta)
        carne  = str(carne)

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
            num_cliente              = CUENTA_DEBITO.id_unico,
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

    def construir_credito(self, monto, cuenta, carne) -> models.RegistroCreditoSIN | None:
        banco = "BN"  # Placeholder value, replace with actual logic if needed
        monto = float(monto)

        iban = str(cuenta).strip()

        if iban.upper().startswith("CR"):
            iban = iban[2:]   # misma columna, formato CR21...
        cedula = str(cuenta)  # Placeholder value, replace with actual logic if needed
        concepto = str(carne) if len(carne) == 10 else f"CARNE: {carne}"
        detalle_especial = concepto
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

    def construir_encabezado(self,
                             sumatoria_monto: float,
                             sumatoria_correlativos: int
                             ) -> models.EncabezadoSIN:
        c = CUENTA_DEBITO
        return models.EncabezadoSIN(
            tipo                     = "1",
            id_unica_cliente         = c.id_unico,
            tipo_id_cliente          = "0",
            id_cliente               = c.id_clientes,
            fecha                    = datetime.now().strftime("%d%m%Y"),
            numero_transferencia_real= "00000",
            tipo_transaccion         = "1",
            codigo_respuesta         = "0000",
            codigo_error             = "0000",
            monto_total_SFB          = "0000000000000000",
            monto_total_sin          = "0000000000000000",
            tipo_cambio_compra       = "0000000",
            tipo_cambio_venta        = "0000000",
            sumatoria_montos         = str(sumatoria_monto).zfill(16),
            sumatoria_correlativos   = str(sumatoria_correlativos).zfill(10),
        )

    def construir_control(
        self,
        sumatoria_monto: float,
        sumatoria_correlativos: int,
    ) -> models.RegistroControlSIN:
        return models.RegistroControlSIN(testkey="")


# ── Cargador principal ────────────────────────────────────────────────────────
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

    filas_con_indice = [
        (i + 2, fila)
        for i, fila in enumerate(filas)
    ]

    filas_con_indice.sort(key=lambda x: _safe_key(x[1][key_col]))

    tabla.delete_rows(2, tabla.max_row)

    for _, fila in filas_con_indice:
        tabla.append(fila)

    return tabla, filas_con_indice


def cargar_registros(
    archivo_excel: str,
    estrategia: EstrategiaTransferencia,
    tipo_pago: int,
) -> tuple[list, float, int, dict[int, str]]:
    """
    Lee el Excel y construye los registros usando la estrategia indicada.
    Retorna:
    (
        registros,
        sumatoria_monto,
        sumatoria_correlativos,
        errores
    )
    """

    nombre = os.path.splitext(
        os.path.basename(archivo_excel)
    )[0]

    wb = openpyxl.load_workbook(archivo_excel)


    key_col = 3 if isinstance(estrategia, EstrategiaSIN) else 2

    hoja, filas_con_indice = _ordenar_tabla(
        wb.active,
        key_col=key_col
    )

    columna_carnet = 2 if tipo_pago == 1 else 5
    columna_identificacion = 3 if tipo_pago == 1 else 4
    columna_monto = 7 if tipo_pago == 1 else 8
    columna_banco = 12 if tipo_pago==1 else 6
    columna_cuenta = 13 if tipo_pago==1 else 7
    creditos = []
    sumatoria_monto = 0.0
    sumatoria_correlativos = 0
    errores = {}

    for num_fila_original, row in filas_con_indice:

        if (row[columna_identificacion] is None and row[columna_carnet] is None) or row[columna_monto] is None or row[columna_banco] is None or row[columna_cuenta] is None:
            continue

        try:
            carne = int(row[columna_carnet])
            identificacion = str(row[columna_identificacion])
            monto = float(row[columna_monto])
            banco = str(row[columna_banco])
            cuenta = str(row[columna_cuenta])

        except (ValueError, TypeError) as e:
            errores[num_fila_original] = f"Error al convertir datos: {e}"
            continue

        error = EstrategiaTransferencia.validacion_fila(
            str(carne),
            str(identificacion),
            monto,
            banco,
            cuenta,
            estrategia
        )

        if error:
            errores[num_fila_original] = error
            continue

        registro = estrategia.construir_credito(monto, cuenta, carne)

        if registro is None:
            continue

        numero_de_cuenta = cuenta[8:14]

        sumatoria_monto += monto

        sumatoria_correlativos += (
            int(numero_de_cuenta)
            if numero_de_cuenta.isdigit()
            else 0
        )

        creditos.append(registro)

    debito = estrategia.construir_debito(
        nombre,
        sumatoria_monto
    )

    # El débito también suma
    sumatoria_monto += float(sumatoria_monto)

    sumatoria_correlativos += int(
        CUENTA_DEBITO.numero_de_cuenta
    )

    registros = [debito] + creditos

    return (
        registros,
        sumatoria_monto,
        sumatoria_correlativos,
        errores
    )


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