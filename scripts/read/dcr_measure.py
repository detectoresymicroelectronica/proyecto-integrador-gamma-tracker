#!/usr/bin/env python3
"""
=============================================================================
  MEDICION DE CORRIENTE OSCURA (PROXY DCR) — UN SiPM POR CORRIDA
=============================================================================
  Proyecto: Gamma Tracker — Upgrade SiPM para matriz multipixel
  Basado en: iv_curve_sipm_complete.py (v2.0, campana 2026-08-10)
  Version: 1.0
  Fecha: 2026-08-24

  Dispositivo: onsemi MICROFC-60035-SMT (C-Series, 6x6 mm, ucell 35 um)
  Instrumento: Keithley 2450 SMU via USB (USBTMC)
  Configuracion: Config B (HI->catodo, LO->anodo, voltajes positivos)
  Termometro: Zotek ZT102 con sonda de temperatura

  Objetivo:
    Medir la corriente oscura de UN SiPM a sobrevoltaje fijo
    (V_ov = 2.5 V) como indicador relativo del dark count rate (DCR).

    Procedimiento por corrida:
    1. El operador conecta el SiPM al Keithley en oscuridad
    2. El script fija V_bias = V_br_individual + V_ov_target
    3. Espera estabilizacion (10 s)
    4. Toma N lecturas de corriente a NPLC = 1
    5. Guarda CSV individual inmediatamente
    6. Si hay mediciones previas en la carpeta, actualiza grafico comparativo

    Ejecutar UNA VEZ por cada SiPM. Repetir para los 10 dispositivos.

  Uso:
    python dcr_measure.py
    (el script pregunta cual dispositivo medir)

  Output por corrida:
    - datos_dcr/DCR_MFC60035_XX_YYYYMMDD_HHMMSS.csv  (datos individuales)
    - datos_dcr/DCR_comparison_YYYYMMDD.png            (grafico actualizado)

  ADVERTENCIA:
    Corriente maxima absoluta del MICROFC-60035-SMT: 20 mA.
    El compliance (100 uA) esta 200x por debajo de ese limite.
=============================================================================
"""

import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import csv
import time
import os
import sys
import glob
from datetime import datetime

# =============================================================================
#  PARAMETROS DEL DISPOSITIVO (MICROFC-60035-SMT)
# =============================================================================

DEVICE_MODEL    = "MICROFC-60035-SMT"
DEVICE_FAMILY   = "C-Series"
DEVICE_VENDOR   = "onsemi"
I_MAX_ABSOLUTE  = 20e-3  # Corriente maxima absoluta [A]

# =============================================================================
#  DISPOSITIVOS — V_br DE REFERENCIA
# =============================================================================
# V_br medidos el 11/08/2026 a 16 C (LOG 3, HITO 1)
# Config B: HI->catodo, LO->anodo, voltajes positivos para inversa

DEVICES = {
    # Batch 1 (Invoice 0871, STAN-2025)
    "01": {"vbr": 24.687, "batch": 1, "label": "MFC60035_01"},
    "02": {"vbr": 24.665, "batch": 1, "label": "MFC60035_02"},
    "03": {"vbr": 24.686, "batch": 1, "label": "MFC60035_03"},
    "04": {"vbr": 24.700, "batch": 1, "label": "MFC60035_04"},
    "05": {"vbr": 24.719, "batch": 1, "label": "MFC60035_05"},
    # Batch 2 (Invoice 0872, STAN-2025-02)
    "06": {"vbr": 24.566, "batch": 2, "label": "MFC60035_06"},
    "07": {"vbr": 24.581, "batch": 2, "label": "MFC60035_07"},
    "08": {"vbr": 24.545, "batch": 2, "label": "MFC60035_08"},
    "09": {"vbr": 24.529, "batch": 2, "label": "MFC60035_09"},
    "10": {"vbr": 24.531, "batch": 2, "label": "MFC60035_10"},
}

# =============================================================================
#  CONFIGURACION DE LA MEDICION
# =============================================================================

V_OV_TARGET     = 2.5    # Sobrevoltaje objetivo [V]
N_SAMPLES       = 100    # Lecturas por dispositivo
STABILIZE_TIME  = 10.0   # Tiempo de estabilizacion [s]
NPLC            = 1.0    # 1 PLC = 20 ms a 50 Hz
I_COMPLIANCE    = 100e-6 # 100 uA
DELAY_PER_POINT = 0.0    # Sin delay adicional entre lecturas (NPLC ya limita)

# --- Archivos ---
OPERATOR        = "PI_GammaTracker"
OUTPUT_DIR      = "datos_dcr"
VISA_RESOURCE   = None   # None = autodetectar

# =============================================================================
#  FUNCIONES AUXILIARES
# =============================================================================

def find_keithley_2450(rm):
    """
    Busca automaticamente un Keithley 2450 entre los recursos VISA.
    """
    resources = rm.list_resources()
    print(f"  Recursos VISA detectados: {resources}")
    if len(resources) == 0:
        return None
    for res in resources:
        try:
            inst = rm.open_resource(res)
            inst.timeout = 5000
            idn = inst.query("*IDN?").strip()
            print(f"    {res} -> {idn}")
            inst.close()
            if "2450" in idn or "MODEL 2450" in idn.upper():
                return res
        except Exception as e:
            print(f"    {res} -> Error: {e}")
    return None


def setup_keithley(inst, v_bias, i_compliance, nplc):
    """
    Configura el Keithley 2450 para medicion de corriente a bias fijo.
    Config B: HI->catodo, LO->anodo, voltajes positivos para inversa.
    Lectura: :READ? (no reconfigura funcion de sensado — ver LOG 1).
    """
    inst.write("*RST")
    inst.write("*CLS")
    time.sleep(1)

    inst.write(":SOUR:FUNC VOLT")
    inst.write(":SENS:FUNC 'CURR'")

    # Rango de voltaje
    if v_bias <= 20:
        inst.write(":SOUR:VOLT:RANG 20")
    else:
        inst.write(":SOUR:VOLT:RANG 200")

    inst.write(":SENS:CURR:RANG:AUTO ON")
    inst.write(f":SOUR:VOLT:ILIM {i_compliance}")
    inst.write(f":SENS:CURR:NPLC {nplc}")
    inst.write(":SOUR:VOLT:RANG:AUTO OFF")
    inst.write(":SOUR:VOLT 0")
    inst.write(":ROUT:TERM FRON")
    inst.write(":SENS:CURR:RSEN OFF")

    print(f"\n  --- Configuracion del instrumento ---")
    print(f"  Fuente: VOLTAJE (rango {'20 V' if v_bias <= 20 else '200 V'})")
    print(f"  Medicion: CORRIENTE (autorange)")
    print(f"  Compliance: {i_compliance*1e6:.1f} uA")
    print(f"  NPLC: {nplc}")
    print(f"  Terminales: FRONTALES (banana jacks)")
    print(f"  Sensing: 2-wire")
    print(f"  Config: B (HI->catodo, LO->anodo, V positivos)")
    print(f"  Lectura: :READ?")


def select_device():
    """
    Muestra la lista de dispositivos y pide al operador que elija uno.
    Retorna: (device_num, device_info) o (None, None) si cancela.
    """
    print("\n  Dispositivos disponibles:")
    print(f"  {'#':>4} {'Dispositivo':<15} {'Batch':>5} {'V_br [V]':>10} "
          f"{'V_bias [V]':>10}")
    print(f"  {'-'*50}")

    for num in sorted(DEVICES.keys()):
        info = DEVICES[num]
        v_bias = info['vbr'] + V_OV_TARGET
        print(f"  {num:>4} {info['label']:<15} {info['batch']:>5} "
              f"{info['vbr']:>10.4f} {v_bias:>10.4f}")

    print()
    choice = input("  Numero del dispositivo a medir (01-10, o 'q' para salir): ").strip()

    if choice.lower() == 'q':
        return None, None

    # Aceptar con o sin cero adelante
    num = choice.zfill(2)
    if num not in DEVICES:
        print(f"  Dispositivo '{choice}' no encontrado.")
        return None, None

    return num, DEVICES[num]


# =============================================================================
#  MEDICION
# =============================================================================

def measure_dark_current(inst, v_bias, n_samples, stabilize_time):
    """
    Mide la corriente oscura a un voltaje de bias fijo.

    1. Setear V_bias
    2. Encender salida
    3. Esperar stabilize_time segundos
    4. Tomar n_samples lecturas con :READ?
    5. Apagar salida (SIEMPRE, incluso si hay error)

    Retorna: dict con i_mean, i_std, readings, n_samples, compliance_hit
             o None si hubo error fatal.
    """
    readings = []
    compliance_hit = False

    try:
        # Setear voltaje y encender
        inst.write(f":SOUR:VOLT {v_bias:.6f}")
        inst.write(":OUTP ON")
        print(f"  Salida ENCENDIDA a {v_bias:.3f} V")

        # Estabilizacion
        print(f"  Esperando {stabilize_time:.0f} s de estabilizacion", end="", flush=True)
        # Mostrar cuenta regresiva
        for sec in range(int(stabilize_time)):
            time.sleep(1)
            remaining = int(stabilize_time) - sec - 1
            if remaining % 2 == 0:
                print(".", end="", flush=True)
        print(" OK")

        # Tomar lecturas
        print(f"  Tomando {n_samples} lecturas: ", end="", flush=True)
        for i in range(n_samples):
            reading_str = inst.query(":READ?").strip()
            current = float(reading_str)
            readings.append(current)

            # Verificar compliance
            if abs(current) >= I_COMPLIANCE * 0.95:
                compliance_hit = True
                print(f"\n  !! COMPLIANCE alcanzado: I = {current*1e6:.2f} uA")
                print(f"     Abortando lecturas.")
                break

            # Progreso cada 10 lecturas
            if (i + 1) % 10 == 0:
                print(f"{i+1}", end=" ", flush=True)

        print("OK")

    except KeyboardInterrupt:
        print(f"\n  *** Medicion interrumpida (Ctrl+C) ***")
    except Exception as e:
        print(f"\n  *** ERROR durante la medicion: {e} ***")
    finally:
        # SIEMPRE apagar salida
        inst.write(":SOUR:VOLT 0")
        time.sleep(0.2)
        inst.write(":OUTP OFF")
        print(f"  Salida APAGADA")

    if len(readings) == 0:
        return None

    readings_arr = np.array(readings)
    i_mean = np.mean(readings_arr)
    i_std = np.std(readings_arr, ddof=1)  # ddof=1: estimador insesgado

    return {
        'i_mean': i_mean,
        'i_std': i_std,
        'readings': readings_arr,
        'n_samples': len(readings),
        'compliance_hit': compliance_hit,
    }


# =============================================================================
#  GUARDADO
# =============================================================================

def save_measurement_csv(filepath, device_num, device_info, result,
                          temperature, v_bias, idn, notes, timestamp):
    """
    Guarda los datos de UNA medicion DCR: metadata + lecturas individuales.

    NOTA: las lineas de metadata se escriben con f.write() (no csv.writer)
    para evitar que csv.writer entrecomille lineas con comas (ej: IDN del
    instrumento), lo cual rompe el parser de load_previous_measurements().
    """
    with open(filepath, 'w', newline='') as f:
        # Metadata — texto plano, sin csv.writer
        f.write(f"# Experimento: Corriente oscura (proxy DCR) a V_ov fijo\n")
        f.write(f"# Dispositivo: {device_info['label']}\n")
        f.write(f"# Modelo: {DEVICE_MODEL} ({DEVICE_VENDOR} {DEVICE_FAMILY})\n")
        f.write(f"# Batch: {device_info['batch']}\n")
        f.write(f"# V_br_ref_V: {device_info['vbr']:.4f}\n")
        f.write(f"# V_br_ref_fecha: 11/08/2026 a 16 C (LOG 3)\n")
        f.write(f"# V_ov_target_V: {V_OV_TARGET:.1f}\n")
        f.write(f"# V_bias_V: {v_bias:.4f}\n")
        f.write(f"# Config: B (HI->catodo, LO->anodo, V positivos)\n")
        f.write(f"# I_dark_mean_A: {result['i_mean']:.12e}\n")
        f.write(f"# I_dark_std_A: {result['i_std']:.12e}\n")
        f.write(f"# I_dark_mean_nA: {result['i_mean']*1e9:.4f}\n")
        f.write(f"# I_dark_std_nA: {result['i_std']*1e9:.4f}\n")
        f.write(f"# N_samples: {result['n_samples']}\n")
        f.write(f"# Compliance_hit: {result['compliance_hit']}\n")
        f.write(f"# NPLC: {NPLC}\n")
        f.write(f"# Stabilize_time_s: {STABILIZE_TIME}\n")
        f.write(f"# I_compliance_A: {I_COMPLIANCE:.6e}\n")
        f.write(f"# Temperatura_C: {temperature}\n")
        f.write(f"# Instrumento: {idn}\n")
        f.write(f"# Operador: {OPERATOR}\n")
        f.write(f"# Fecha: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Notas: {notes if notes else 'N/A'}\n")
        f.write(f"\n")

        # Datos: lecturas individuales (csv.writer solo para la tabla)
        writer = csv.writer(f)
        writer.writerow(["reading_idx", "current_A", "current_nA", "current_uA"])
        for idx, reading in enumerate(result['readings']):
            writer.writerow([
                idx,
                f"{reading:.12e}",
                f"{reading*1e9:.4f}",
                f"{reading*1e6:.6f}",
            ])

    print(f"  CSV guardado: {filepath}")


# =============================================================================
#  GRAFICO COMPARATIVO (lee CSVs previos de la carpeta)
# =============================================================================

def load_previous_measurements(output_dir):
    """
    Busca todos los CSVs de mediciones DCR en la carpeta de salida.
    Lee la metadata de cada uno para armar la tabla comparativa.

    Retorna: lista de dicts con device_id, batch, vbr, vbias, i_mean, i_std, etc.
    """
    pattern = os.path.join(output_dir, "DCR_MFC60035_*.csv")
    csv_files = glob.glob(pattern)

    measurements = []
    for csv_path in csv_files:
        meta = {}
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                # csv.writer puede haber entrecomillado lineas con comas
                # (ej: IDN del instrumento). Quitar comillas externas.
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                if line.startswith("# "):
                    # Parsear "# Key: Value"
                    parts = line[2:].split(": ", 1)
                    if len(parts) == 2:
                        meta[parts[0].strip()] = parts[1].strip()
                elif not line.startswith("#") and line != "":
                    break  # fin de metadata

        try:
            measurements.append({
                'device_id': meta.get('Dispositivo', '??'),
                'batch': int(meta.get('Batch', 0)),
                'vbr': float(meta.get('V_br_ref_V', 0)),
                'v_bias': float(meta.get('V_bias_V', 0)),
                'i_mean': float(meta.get('I_dark_mean_A', 0)),
                'i_std': float(meta.get('I_dark_std_A', 0)),
                'i_mean_nA': float(meta.get('I_dark_mean_nA', 0)),
                'i_std_nA': float(meta.get('I_dark_std_nA', 0)),
                'temperature': meta.get('Temperatura_C', '?'),
                'compliance_hit': meta.get('Compliance_hit', 'False') == 'True',
                'csv_path': csv_path,
            })
        except (ValueError, KeyError) as e:
            print(f"  !! Error leyendo {csv_path}: {e}, salteando.")

    return measurements


def plot_dcr_comparison(measurements, output_dir):
    """
    Genera grafico de barras horizontales de I_dark para todos los
    dispositivos medidos hasta ahora. Se actualiza con cada nueva medicion.
    """
    if len(measurements) < 2:
        print(f"  Solo {len(measurements)} medicion(es), se necesitan >=2 para comparar.")
        return None

    # Ordenar por I_dark (menor a mayor)
    measurements.sort(key=lambda m: m['i_mean'])

    n = len(measurements)
    y_pos = np.arange(n)

    means = [m['i_mean_nA'] for m in measurements]
    stds = [m['i_std_nA'] for m in measurements]
    batches = [m['batch'] for m in measurements]

    # Colores por batch
    batch_colors = {1: '#2196F3', 2: '#FF9800'}
    colors = [batch_colors.get(b, '#999999') for b in batches]

    fig, ax = plt.subplots(1, 1, figsize=(12, max(5, n * 0.65)))

    ax.barh(y_pos, means, xerr=stds, align='center',
            color=colors, alpha=0.85, edgecolor='white',
            linewidth=0.5, capsize=3, ecolor='#555555')

    # Labels
    labels = []
    for rank, m in enumerate(measurements, 1):
        batch_str = f"B{m['batch']}"
        labels.append(f"#{rank} {m['device_id']} ({batch_str})")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10, fontfamily='monospace')

    # Anotaciones
    x_margin = max(means) * 0.02 if max(means) > 0 else 1
    for i, (mean_val, std_val) in enumerate(zip(means, stds)):
        ax.text(mean_val + std_val + x_margin, i,
                f"{mean_val:.1f} +/- {std_val:.1f} nA",
                va='center', ha='left', fontsize=9, color='#333333')

    temp_str = measurements[0]['temperature']
    ax.set_xlabel("Corriente oscura [nA]", fontsize=12)
    ax.set_title(f"Corriente oscura (proxy DCR) a V_ov = {V_OV_TARGET:.1f} V\n"
                 f"MICROFC-60035-SMT — T = {temp_str} C — "
                 f"{datetime.now().strftime('%Y-%m-%d')} "
                 f"({n} de {len(DEVICES)} dispositivos)",
                 fontsize=13, fontweight='bold')
    ax.grid(True, axis='x', alpha=0.3)

    # Leyenda
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=batch_colors[1], alpha=0.85, label='Batch 1'),
        Patch(facecolor=batch_colors[2], alpha=0.85, label='Batch 2'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    ax.invert_yaxis()
    ax.set_xlim(right=max(means) * 1.5 if max(means) > 0 else 10)

    plt.tight_layout()

    # Guardar (sobreescribe el anterior — siempre el mas reciente)
    date_str = datetime.now().strftime("%Y%m%d")
    png_path = os.path.join(output_dir, f"DCR_comparison_{date_str}.png")
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"  Grafico comparativo guardado/actualizado: {png_path}")

    return png_path


# =============================================================================
#  MAIN
# =============================================================================

def main():
    print("=" * 72)
    print("  MEDICION DE CORRIENTE OSCURA (PROXY DCR) — UN SiPM")
    print(f"  {DEVICE_MODEL} ({DEVICE_VENDOR} {DEVICE_FAMILY})")
    print(f"  V_ov = {V_OV_TARGET:.1f} V | {N_SAMPLES} lecturas | "
          f"{STABILIZE_TIME:.0f} s estabilizacion")
    print(f"  Config B: HI->catodo, LO->anodo, V positivos")
    print("=" * 72)

    # --- Elegir dispositivo ---
    device_num, device_info = select_device()
    if device_num is None:
        return

    v_bias = device_info['vbr'] + V_OV_TARGET

    print(f"\n  Dispositivo seleccionado: {device_info['label']}")
    print(f"  Batch:   {device_info['batch']}")
    print(f"  V_br:    {device_info['vbr']:.4f} V (ref: 11/08, 16 C)")
    print(f"  V_bias:  {v_bias:.4f} V (= V_br + {V_OV_TARGET:.1f} V)")

    # --- Temperatura ---
    temp_str = input("\n  Temperatura ambiente [C] (Zotek ZT102): ").strip()
    if not temp_str:
        temp_str = "no registrada"

    # --- Notas ---
    notes = input("  Notas (Enter=ninguna): ").strip()

    # --- Confirmar condiciones ---
    print(f"\n  VERIFICAR ANTES DE MEDIR:")
    print(f"    - {device_info['label']} conectado al Keithley")
    print(f"    - HI (rojo) -> catodo (pin 3)")
    print(f"    - LO (negro) -> anodo (pin 1)")
    print(f"    - Cubierta opaca colocada (OSCURIDAD)")
    print(f"    - Keithley encendido y cable USB conectado")

    input(f"\n  Presionar Enter para medir {device_info['label']}...")

    # --- Crear directorio ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- Conectar al instrumento ---
    print("\n[1/4] Buscando Keithley 2450...")
    rm = pyvisa.ResourceManager('@py')

    resource = VISA_RESOURCE
    if resource is None:
        resource = find_keithley_2450(rm)

    if resource is None:
        print("\n  *** ERROR: No se encontro el Keithley 2450. ***")
        print("  Verificar USB, instrumento encendido, driver Zadig.")
        rm.close()
        return

    inst = rm.open_resource(resource)
    inst.timeout = 30000
    inst.write_termination = '\n'
    inst.read_termination = '\n'

    idn = inst.query("*IDN?").strip()
    print(f"  Instrumento: {idn}")

    # --- Configurar ---
    print("\n[2/4] Configurando instrumento...")
    setup_keithley(inst, v_bias, I_COMPLIANCE, NPLC)

    # --- Medir ---
    print(f"\n[3/4] Midiendo {device_info['label']}...")
    timestamp = datetime.now()
    result = measure_dark_current(inst, v_bias, N_SAMPLES, STABILIZE_TIME)

    # --- Cerrar conexion ---
    inst.close()
    rm.close()
    print("  Conexion cerrada.")

    if result is None:
        print("\n  No se obtuvieron lecturas. Fin.")
        return

    # --- Resultado ---
    print(f"\n  ==========================================")
    print(f"  {device_info['label']} (Batch {device_info['batch']})")
    print(f"  I_dark = {result['i_mean']*1e9:.2f} +/- {result['i_std']*1e9:.2f} nA")
    print(f"         = {result['i_mean']*1e6:.4f} +/- {result['i_std']*1e6:.4f} uA")
    print(f"  V_bias = {v_bias:.4f} V | V_ov = {V_OV_TARGET:.1f} V")
    print(f"  N = {result['n_samples']} lecturas")
    if result['compliance_hit']:
        print(f"  !! COMPLIANCE ALCANZADO — dato posiblemente no confiable")
    print(f"  ==========================================")

    # --- Guardar CSV ---
    print(f"\n[4/4] Guardando datos...")
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
    csv_filename = f"DCR_{device_info['label']}_{ts_str}.csv"
    csv_path = os.path.join(OUTPUT_DIR, csv_filename)

    save_measurement_csv(csv_path, device_num, device_info, result,
                          temp_str, v_bias, idn, notes, timestamp)

    # --- Buscar mediciones previas y actualizar grafico ---
    print(f"\n  Buscando mediciones DCR previas en {OUTPUT_DIR}/...")
    all_measurements = load_previous_measurements(OUTPUT_DIR)
    print(f"  Encontradas: {len(all_measurements)} mediciones")

    png_path = plot_dcr_comparison(all_measurements, OUTPUT_DIR)

    # --- Resumen final ---
    print("\n" + "=" * 72)
    print(f"  LISTO: {device_info['label']} medido y guardado")
    print(f"  CSV:      {csv_path}")
    if png_path:
        print(f"  Grafico:  {png_path}")
    print(f"  Progreso: {len(all_measurements)}/{len(DEVICES)} dispositivos")

    remaining = [num for num in sorted(DEVICES.keys())
                 if not any(m['device_id'] == DEVICES[num]['label']
                           for m in all_measurements)]
    if remaining:
        print(f"  Faltan:   {', '.join(DEVICES[n]['label'] for n in remaining)}")
    else:
        print(f"  TODOS LOS DISPOSITIVOS MEDIDOS")

    print("=" * 72)

    # --- Mostrar grafico si hay ---
    if png_path and len(all_measurements) >= 2:
        plt.ioff()
        print("\nCerra la ventana del grafico para terminar.")
        plt.show()

    print("Fin. Ejecutar de nuevo para el siguiente dispositivo.")


# =============================================================================
if __name__ == "__main__":
    main()
