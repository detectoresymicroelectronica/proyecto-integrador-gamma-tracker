#!/usr/bin/env python3
"""
Test rapido de conexion VISA al Keithley 2450.
Ejecutar para verificar que el instrumento responde.
"""
import pyvisa

rm = pyvisa.ResourceManager('@py')
resources = rm.list_resources()
print(f"Recursos VISA detectados: {resources}")

if len(resources) == 0:
    print("No se encontraron recursos. Verificar USB y driver.")
else:
    for res in resources:
        try:
            inst = rm.open_resource(res)
            inst.timeout = 5000
            idn = inst.query("*IDN?").strip()
            print(f"  {res} -> {idn}")
            inst.close()
        except Exception as e:
            print(f"  {res} -> Error: {e}")

rm.close()
