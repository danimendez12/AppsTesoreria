import openpyxl
import models

def cargar_registros(archivo_excel):
    registros = []
    df = openpyxl.load_workbook(archivo_excel)
    df1 = df.active
    sumatoriaMonto = 0
    sumatoriaCorrelativos = 0

    for row in df1.iter_rows(min_row=2, values_only=True):
        registro = models.Credito()
        carne = row[2]
        monto = float(row [7])
        banco = row [12]
        cuenta = str(row [13])
        if banco == "NO ASIGNADO":
            continue
        producto = cuenta[:3]
        moneda = cuenta[3:5]
        oficina = cuenta[5:8]
        numero_de_cuenta = cuenta[8:14]
        digito_verificador = cuenta[14]
        sumatoriaMonto += monto
        sumatoriaCorrelativos += int(numero_de_cuenta)
        registro.numero_de_cuenta = numero_de_cuenta
        registro.digito_verificador = digito_verificador
        registro.producto = producto
        registro.moneda = moneda
        registro.oficina_apertura = oficina
        monto_entero = int(round(monto * 100))
        registro.monto = str(monto_entero)
        registro.concepto_pago = f"CARNE: {carne}"
        registros.append(registro)
        print(oficina, producto, moneda, numero_de_cuenta, digito_verificador, monto_entero,registro.concepto_pago)
    return registros, sumatoriaMonto, sumatoriaCorrelativos