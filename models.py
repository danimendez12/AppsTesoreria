from dataclasses import dataclass, field

def pad_num(valor, largo):
    return str(valor).zfill(largo)

def pad_alpha(texto, largo):
    return str(texto).ljust(largo)[:largo] 

@dataclass
class Transaccion:
    encabezado:Encabezado
    registros:list[Registro]
    registroControl:RegistroControl

    def to_env(self):
        env = self.encabezado.to_env() + "\n"
        for registro in self.registros:
            env += registro.to_env() + "\n"
        env += self.registroControl.to_env()
        return env

@dataclass
class Encabezado:
    tipo:str
    num_cliente:str
    fecha:str
    num_transferencia_real:str
    num_transferencia_interna:str
    tipo_transaccion:str
    codigo_error:str
    total_transferencia:str
    tipo_cambio_compra_dia:str
    tipo_cambio_venta_dia:str
    campo_sin_uso:str

    def to_env(self):
        linea = (
            pad_num(self.tipo,1) +
            pad_num(self.num_cliente,10) +
            pad_num(self.fecha,8) +
            pad_num(self.num_transferencia_real,20) +
            pad_num(self.num_transferencia_interna,20) +
            pad_num(self.tipo_transaccion,2) +
            pad_num(self.codigo_error,2) +
            pad_num(self.total_transferencia,12) +
            pad_num(self.tipo_cambio_compra_dia,12) +
            pad_num(self.tipo_cambio_venta_dia,12) +
            pad_alpha(self.campo_sin_uso,11)
        )

        if len(linea) != 120:
            raise ValueError(
                f"Encabezado inválido: {len(linea)} caracteres"
            )

        return linea

@dataclass
class Registro:
    tipo:str = field(init=False)

    oficina_apertura:str=""
    producto:str=""
    moneda:str=""
    numero_de_cuenta:str=""
    digito_verificador:str=""
    numero_comprobante:str=""
    monto:str=""
    concepto_pago:str=""
    senal_aplicacion:str=""

    def to_env(self):

        linea = (
            pad_num(self.tipo,1) +
            pad_num(self.oficina_apertura,3) +
            pad_num(self.producto,3) +
            pad_num(self.moneda,2) +
            pad_num(self.numero_de_cuenta,6) +
            pad_num(self.digito_verificador,1) +
            pad_num(self.numero_comprobante,8) +
            pad_num(self.monto,12) +
            pad_alpha(self.concepto_pago,30) +
            pad_num(self.senal_aplicacion,2)
        )

        if len(linea) != 68:
            raise ValueError(
                f"Registro inválido: {len(linea)} caracteres"
            )

        return linea

@dataclass
class Debito(Registro):

    def __post_init__(self):
        self.tipo="2"

@dataclass
class Credito(Registro):

    def __post_init__(self):
        self.tipo="3"

@dataclass
class RegistroControl:
    tipo:str
    sumatoria_montos:str
    sumatoria_correlativos:str
    test_key:str
    monto_en_dolares:str
    monto_en_colones:str
    campo_sin_uso:str

    def to_env(self):
        linea = (
            pad_num(self.tipo,1) +
            pad_num(self.sumatoria_montos,12) +
            pad_num(self.sumatoria_correlativos,8) +
            pad_alpha(self.test_key,20) +
            pad_num(self.monto_en_dolares,12) +
            pad_num(self.monto_en_colones,12) +
            pad_alpha(self.campo_sin_uso,57)
        )

        if len(linea) != 120:
            raise ValueError(
                f"Registro Control inválido: {len(linea)} caracteres"
            )

        return linea


