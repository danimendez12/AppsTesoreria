from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ── Utilidades de formateo ────────────────────────────────────────────────────

class Formatter:
    @staticmethod
    def num(valor, largo: int) -> str:
        return str(valor).zfill(largo)

    @staticmethod
    def alpha(texto, largo: int) -> str:
        return str(texto).ljust(largo)[:largo]


# ── Clase base abstracta ──────────────────────────────────────────────────────

class BaseRecord(ABC):
    """Contrato común para todos los registros del envío."""

    EXPECTED_LEN: int = 0   # cada subclase sobreescribe esto

    @abstractmethod
    def _build_line(self) -> str:
        """Construye la línea sin validar longitud."""

    def to_env(self) -> str:
        linea = self._build_line()
        if self.EXPECTED_LEN and len(linea) != self.EXPECTED_LEN:
            raise ValueError(
                f"{type(self).__name__} inválido: "
                f"esperado {self.EXPECTED_LEN}, obtenido {len(linea)} caracteres.\n{linea}"
            )
        return linea

    def __str__(self) -> str:
        return self.to_env()


# ── Encabezados ───────────────────────────────────────────────────────────────

@dataclass
class Encabezado(BaseRecord):
    EXPECTED_LEN = 68

    tipo: str
    num_cliente: str
    fecha: str
    num_transferencia_real: str
    num_transferencia_interna: str
    tipo_transaccion: str
    codigo_error: str
    total_transferencia: str
    tipo_cambio_compra_dia: str
    tipo_cambio_venta_dia: str
    campo_sin_uso: str

    def _build_line(self) -> str:
        f = Formatter
        return (
            f.num(self.tipo, 1) +
            f.num(self.num_cliente, 6) +
            f.num(self.fecha, 8) +
            f.num(self.num_transferencia_real, 6) +
            f.num(self.num_transferencia_interna, 6) +
            f.num(self.tipo_transaccion, 1) +
            f.num(self.codigo_error, 4) +
            f.num(self.total_transferencia, 12) +
            f.num(self.tipo_cambio_compra_dia, 7) +
            f.num(self.tipo_cambio_venta_dia, 7) +
            f.num(self.campo_sin_uso, 10)
        )


@dataclass
class EncabezadoSIN(BaseRecord):
    EXPECTED_LEN = 126

    tipo: str
    id_unica_cliente: str
    tipo_id_cliente: str
    id_cliente: str
    fecha: str
    numero_transferencia_real: str
    tipo_transaccion: str
    codigo_respuesta: str
    codigo_error: str
    monto_total_SFB: str
    monto_total_sin: str
    tipo_cambio_compra: str
    tipo_cambio_venta: str
    sumatoria_montos: str
    sumatoria_correlativos: str

    def _build_line(self) -> str:
        f = Formatter
        return (
            f.num(self.tipo, 1) +
            f.num(self.id_unica_cliente, 15) +
            f.num(self.tipo_id_cliente, 1) +
            f.num(self.id_cliente, 15) +
            f.num(self.fecha, 8) +
            f.num(self.numero_transferencia_real, 5) +
            f.num(self.tipo_transaccion, 1) +
            f.num(self.codigo_respuesta, 4) +
            f.num(self.codigo_error, 4) +
            f.num(self.monto_total_SFB, 16) +
            f.num(self.monto_total_sin, 16) +
            f.num(self.tipo_cambio_compra, 7) +
            f.num(self.tipo_cambio_venta, 7) +
            f.num(self.sumatoria_montos, 16) +
            f.num(self.sumatoria_correlativos, 10)
        )


# ── Registros estándar ────────────────────────────────────────────────────────

@dataclass
class Registro(BaseRecord):
    EXPECTED_LEN = 68

    oficina_apertura: str = ""
    producto: str = ""
    moneda: str = ""
    numero_de_cuenta: str = ""
    digito_verificador: str = ""
    numero_comprobante: str = ""
    monto: str = ""
    concepto_pago: str = ""
    senal_aplicacion: str = ""

    # Subclases definen su tipo; None fuerza error si se instancia Registro directamente
    _tipo: str = field(init=False, default=None)

    def _build_line(self) -> str:
        if self._tipo is None:
            raise TypeError("No instancies Registro directamente; usá Debito o Credito.")
        f = Formatter
        return (
            f.num(self._tipo, 1) +
            f.num(self.oficina_apertura, 3) +
            f.num(self.producto, 3) +
            f.num(self.moneda, 2) +
            f.num(self.numero_de_cuenta, 6) +
            f.num(self.digito_verificador, 1) +
            f.num(self.numero_comprobante, 8) +
            f.num(self.monto, 12) +
            f.alpha(self.concepto_pago, 30) +
            f.num(self.senal_aplicacion, 2)
        )


@dataclass
class Debito(Registro):
    def __post_init__(self):
        self._tipo = "2"


@dataclass
class Credito(Registro):
    def __post_init__(self):
        self._tipo = "3"


# ── Registros SIN ─────────────────────────────────────────────────────────────

@dataclass
class RegistroSIN(BaseRecord):
    """Campos comunes a débito y crédito SIN."""
    num_linea: str
    tipo_procesamiento: str
    numero_cuenta_iban: str
    numero_comprobante: str
    monto: str
    moneda: str
    concepto: str
    estado_registro: str
    tipo_id_beneficiario: str
    id_beneficiario: str
    detalle_especial: str

    _tipo: str = field(init=False, default=None)

    def _campos_comunes(self) -> str:
        f = Formatter
        return (
            f.num(self._tipo, 1) +
            f.num(self.num_linea, 5) +
            f.num(self.tipo_procesamiento, 1) +
            f.num(self.numero_cuenta_iban, 22) +
            f.num(self.numero_comprobante, 8) +
            f.num(self.monto, 15) +
            f.num(self.moneda, 2) +
            f.alpha(self.concepto, 45) +
            f.num(self.estado_registro, 2)
        )

    def _build_line(self) -> str:
        raise NotImplementedError


@dataclass
class RegistroDebitoSIN(RegistroSIN):
    EXPECTED_LEN = 101

    def __post_init__(self):
        self._tipo = "2"

    def _build_line(self) -> str:
        return self._campos_comunes()


@dataclass
class RegistroCreditoSIN(RegistroSIN):
    EXPECTED_LEN = 137

    def __post_init__(self):
        self._tipo = "3"

    def _build_line(self) -> str:
        f = Formatter
        return (
            self._campos_comunes() +
            f.num(self.tipo_id_beneficiario, 1) +
            f.num(self.id_beneficiario, 15) +
            f.alpha(self.detalle_especial, 20)
        )


# ── Registros de control ──────────────────────────────────────────────────────

@dataclass
class RegistroControl(BaseRecord):
    EXPECTED_LEN = 68

    tipo: str
    sumatoria_montos: str
    sumatoria_correlativos: str
    test_key: str
    monto_en_dolares: str
    monto_en_colones: str
    campo_sin_uso: str

    def _build_line(self) -> str:
        f = Formatter
        return (
            f.num(self.tipo, 1) +
            f.num(self.sumatoria_montos, 15) +
            f.num(self.sumatoria_correlativos, 10) +
            f.num(self.test_key, 10) +
            f.num(self.monto_en_dolares, 12) +
            f.num(self.monto_en_colones, 12) +
            f.num(self.campo_sin_uso, 8)
        )


@dataclass
class RegistroControlSIN(BaseRecord):
    testkey: str

    def _build_line(self) -> str:
        return self.testkey


# ── Transacción ───────────────────────────────────────────────────────────────

@dataclass
class Transaccion:
    encabezado: BaseRecord
    registros: list[BaseRecord]
    registro_control: BaseRecord

    def to_env(self) -> str:
        lineas = [self.encabezado.to_env()]
        lineas += [r.to_env() for r in self.registros]
        lineas.append(self.registro_control.to_env())
        return "\n".join(lineas)

    def __str__(self) -> str:
        return self.to_env()