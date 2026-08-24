#!/usr/bin/env python3
"""
=============================================================================
  DRIFT TEMPORAL DE CORRIENTE OSCURA — MONITOREO CONTINUO
=============================================================================
  Proyecto: Gamma Tracker — Upgrade SiPM para matriz multipixel
  Basado en: dcr_measure.py (v1.1)
  Version: 1.0
  Fecha: 2026-08-24

  Dispositivo: onsemi MICROFC-60035-SMT (C-Series, 6x6 mm, ucell 35 um)
  Instrumento: Keithley 2450 SMU via USB (USBTMC)
  Configuracion: Config B (HI->catodo, LO->anodo, voltajes positivos)

  Objetivo:
    Monitorear la corriente oscura de un SiPM durante ~45 min a V_ov fijo
    para evaluar estabilidad temporal, settling y posibles derivas termicas.

    Muestreo: una lectura cada ~2 s con :READ?
    Parada segura: Ctrl+C en cualquier momento guarda los datos adquiridos.

  Uso:
    python drift_temporal.py

  Output:
    - datos_drift/DRIFT_MFC60035_XX_YYYYMMDD_HHMMSS.csv
    - datos_drift/DRIFT_MFC60035_XX_YYYYMMDD_HHMMSS.png

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
from datetime import datetime

# =============================================================================
#  DISPOSITIVOS — V_br DE REFERENCIA
# =============================================================================
# V_br medidos el 11/08/2026 a 16 C (LOG 3, HITO 1)

DEVICES = {
    "01": {"vbr": 24.687, "batch": 1, "label": "MFC60035_01"},
    "02": {"vbr": 24.665, "batch": 1, "label": "MFC60035_02"},
    "03": {"vbr": 24.686, "batch": 1, "label": "MFC60035_03"},
    "04": {"vbr": 24.700, "batch": 1, "label": "MFC60035_04"},
    "05": {"vbr": 24.719, "batch": 1, "label": "MFC60035_05"},
    "06": {"vbr": 24.566, "batch": 2, "label": "MFC60035_06"},
    "07": {"vbr": 24.581, "batch": 2, "label": "MFC60035_07"},
    "08": {"vbr": 24.545, "batch": 2, "label": "MFC60035_08"},
    "09": {"vbr": 24.529, "batch": 2, "label": "MFC60035_09"},
    "10": {"vbr": 24.531, "batch": 2, "label": "MFC60035_10"},
}

# =============================================================================
#  CONFIGURACION
# =============================================================================

V_OV_TARGET     = 2.5       # Sobrevoltaje objetivo [V]
DURATION_MIN    = 45        # Duracion total [min]
SAMPLE_INTERVAL = 2.0       # Intervalo entre lecturas [s]
STABILIZE_TIME  = 10.0      # Estabilizacion inicial [s]
NPLC            = 1.0       # 1 PLC = 20 ms a 50 Hz
I_COMPLIANCE    = 100e-6    # 100 uA
OPERATOR        = "PI_GammaTracker"
OUTPUT_DIR      = "datos_drift"


# =============================================================================
#  FUNCIONES
# =============================================================================

def find_keithley_2450(rm):
    """Busca automaticamente un Keithley 2450 entre los recursos VISA."""
    resources = rm.list_resources()
    print(f"  Recursos VISA detectados: {resources}")
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
    """Configura el Keithley 2450 para medicion de corriente a bias fijo."""
    inst.write("*RST")
    inst.write("*CLS")
    time.sleep(1)

    inst.write(":SOUR:FUNC VOLT")
    inst.write(":SENS:FUNC 'CURR'")

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


def select_device():
    """Muestra la lista de dispositivos y pide al operador que elija uno."""
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
    choice = input("  Dispositivo a monitorear (01-10, o 'q'): ").strip()
    if choice.lower() == 'q':
        return None, None
    num = choice.zfill(2)
    if num not in DEVICES:
        print(f"  Dispositivo '{choice}' no encontrado.")
        return None, None
    return num, DEVICES[num]


# =============================================================================
#  MAIN
# =============================================================================

def main():
    print("=" * 72)
    print("  DRIFT TEMPORAL — CORRIENTE OSCURA vs TIEMPO")
    print(f"  MICROFC-60035-SMT | V_ov = {V_OV_TARGET:.1f} V | "
          f"{DURATION_MIN} min | muestreo cada {SAMPLE_INTERVAL:.0f} s")
    print("=" * 72)

    # --- Elegir dispositivo ---
    device_num, device_info = select_device()
    if device_num is None:
        return

    v_bias = device_info['vbr'] + V_OV_TARGET
    print(f"\n  {device_info['label']} (Batch {device_info['batch']})")
    print(f"  V_br = {device_info['vbr']:.4f} V | V_bias = {v_bias:.4f} V")

    # --- Temperatura ---
    temp_str = input("\n  Temperatura ambiente [C] (Zotek ZT102): ").strip()
    if not temp_str:
        temp_str = "no registrada"

    notes = input("  Notas (Enter=ninguna): ").strip()

    # --- Confirmar ---
    n_expected = int(DURATION_MIN * 60 / SAMPLE_INTERVAL)
    print(f"\n  CONFIGURACION:")
    print(f"    Duracion:   {DURATION_MIN} min ({DURATION_MIN*60} s)")
    print(f"    Muestreo:   cada {SAMPLE_INTERVAL:.0f} s")
    print(f"    Lecturas:   ~{n_expected} esperadas")
    print(f"    Ctrl+C para parar y guardar lo que haya.")

    input(f"\n  Enter para iniciar monitoreo de {device_info['label']}...")

    # --- Directorio ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- Conectar ---
    print("\n[1/3] Conectando al Keithley 2450...")
    rm = pyvisa.ResourceManager('@py')
    resource = find_keithley_2450(rm)

    if resource is None:
        print("  *** ERROR: No se encontro el Keithley 2450. ***")
        rm.close()
        return

    inst = rm.open_resource(resource)
    inst.timeout = 30000
    inst.write_termination = '\n'
    inst.read_termination = '\n'
    idn = inst.query("*IDN?").strip()
    print(f"  Instrumento: {idn}")

    # --- Configurar ---
    print("\n[2/3] Configurando...")
    setup_keithley(inst, v_bias, I_COMPLIANCE, NPLC)

    # --- Medir (loop principal) ---
    print(f"\n[3/3] Iniciando monitoreo ({DURATION_MIN} min)...")

    timestamps_s = []   # tiempo relativo [s]
    currents_A = []     # corriente [A]
    compliance_hit = False
    stopped_by_user = False

    try:
        # Encender salida
        inst.write(f":SOUR:VOLT {v_bias:.6f}")
        inst.write(":OUTP ON")
        print(f"  Salida ENCENDIDA a {v_bias:.3f} V")

        # Estabilizacion
        print(f"  Estabilizando {STABILIZE_TIME:.0f} s", end="", flush=True)
        for _ in range(int(STABILIZE_TIME)):
            time.sleep(1)
            print(".", end="", flush=True)
        print(" OK")

        t_start = time.time()
        t_end = t_start + DURATION_MIN * 60
        sample_idx = 0

        print(f"\n  {'Tiempo':>8}  {'I [nA]':>10}  {'Δ medio':>10}  Progreso")
        print(f"  {'-'*55}")

        while time.time() < t_end:
            t_sample_start = time.time()

            # Leer corriente
            reading_str = inst.query(":READ?").strip()
            current = float(reading_str)
            t_rel = time.time() - t_start

            timestamps_s.append(t_rel)
            currents_A.append(current)
            sample_idx += 1

            # Compliance check
            if abs(current) >= I_COMPLIANCE * 0.95:
                compliance_hit = True
                print(f"\n  !! COMPLIANCE alcanzado: {current*1e6:.2f} uA — abortando")
                break

            # Progreso cada 30 s (~15 lecturas)
            if sample_idx == 1 or sample_idx % 15 == 0:
                elapsed_min = t_rel / 60
                remaining_min = DURATION_MIN - elapsed_min
                mean_so_far = np.mean(currents_A) * 1e9
                delta = (current * 1e9 - mean_so_far)
                pct = elapsed_min / DURATION_MIN * 100
                bar_len = int(pct / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"  {elapsed_min:>6.1f}m  {current*1e9:>9.2f}  "
                      f"{delta:>+8.2f}  {bar} {pct:.0f}% ({remaining_min:.0f}m rest)")

        print(f"\n  Monitoreo finalizado: {sample_idx} lecturas en "
              f"{timestamps_s[-1]/60:.1f} min")

    except KeyboardInterrupt:
        stopped_by_user = True
        elapsed = timestamps_s[-1] if timestamps_s else 0
        print(f"\n\n  *** Ctrl+C — monitoreo detenido ({len(timestamps_s)} lecturas, "
              f"{elapsed/60:.1f} min) ***")

    except Exception as e:
        print(f"\n  *** ERROR: {e} ***")

    finally:
        inst.write(":SOUR:VOLT 0")
        time.sleep(0.2)
        inst.write(":OUTP OFF")
        print(f"  Salida APAGADA")
        inst.close()
        rm.close()
        print(f"  Conexion cerrada.")

    # --- Verificar datos ---
    if len(timestamps_s) < 2:
        print("  Menos de 2 lecturas — nada que guardar.")
        return

    currents_arr = np.array(currents_A)
    timestamps_arr = np.array(timestamps_s)

    # --- Estadísticas ---
    i_mean = np.mean(currents_arr)
    i_std = np.std(currents_arr, ddof=1)
    i_min = np.min(currents_arr)
    i_max = np.max(currents_arr)

    # Drift: pendiente por regresion lineal
    slope, intercept = np.polyfit(timestamps_arr, currents_arr * 1e9, 1)
    drift_total_nA = slope * timestamps_arr[-1]
    drift_pct = drift_total_nA / (i_mean * 1e9) * 100

    print(f"\n  ==========================================")
    print(f"  {device_info['label']} — Drift temporal")
    print(f"  I_dark = {i_mean*1e9:.2f} ± {i_std*1e9:.2f} nA")
    print(f"  Rango:   {i_min*1e9:.2f} – {i_max*1e9:.2f} nA")
    print(f"  Drift:   {slope:.4f} nA/s = {slope*60:.2f} nA/min")
    print(f"           {drift_total_nA:.1f} nA total ({drift_pct:.2f}%)")
    print(f"  N = {len(timestamps_s)} lecturas en {timestamps_arr[-1]/60:.1f} min")
    if stopped_by_user:
        print(f"  (Detenido por Ctrl+C)")
    print(f"  ==========================================")

    # --- Guardar CSV ---
    timestamp = datetime.now()
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
    base_name = f"DRIFT_{device_info['label']}_{ts_str}"
    csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")

    with open(csv_path, 'w', newline='') as f:
        f.write(f"# Experimento: Drift temporal de corriente oscura\n")
        f.write(f"# Dispositivo: {device_info['label']}\n")
        f.write(f"# Modelo: MICROFC-60035-SMT (onsemi C-Series)\n")
        f.write(f"# Batch: {device_info['batch']}\n")
        f.write(f"# V_br_ref_V: {device_info['vbr']:.4f}\n")
        f.write(f"# V_ov_target_V: {V_OV_TARGET:.1f}\n")
        f.write(f"# V_bias_V: {v_bias:.4f}\n")
        f.write(f"# Config: B (HI->catodo, LO->anodo, V positivos)\n")
        f.write(f"# I_dark_mean_A: {i_mean:.12e}\n")
        f.write(f"# I_dark_std_A: {i_std:.12e}\n")
        f.write(f"# I_dark_mean_nA: {i_mean*1e9:.4f}\n")
        f.write(f"# I_dark_std_nA: {i_std*1e9:.4f}\n")
        f.write(f"# Drift_nA_per_min: {slope*60:.4f}\n")
        f.write(f"# Drift_total_nA: {drift_total_nA:.2f}\n")
        f.write(f"# Drift_total_pct: {drift_pct:.4f}\n")
        f.write(f"# Duration_min: {timestamps_arr[-1]/60:.2f}\n")
        f.write(f"# N_samples: {len(timestamps_s)}\n")
        f.write(f"# Sample_interval_s: {SAMPLE_INTERVAL}\n")
        f.write(f"# Stabilize_time_s: {STABILIZE_TIME}\n")
        f.write(f"# NPLC: {NPLC}\n")
        f.write(f"# I_compliance_A: {I_COMPLIANCE:.6e}\n")
        f.write(f"# Compliance_hit: {compliance_hit}\n")
        f.write(f"# Stopped_by_user: {stopped_by_user}\n")
        f.write(f"# Temperatura_C: {temp_str}\n")
        f.write(f"# Instrumento: {idn}\n")
        f.write(f"# Operador: {OPERATOR}\n")
        f.write(f"# Fecha: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Notas: {notes if notes else 'N/A'}\n")
        f.write(f"\n")

        writer = csv.writer(f)
        writer.writerow(["time_s", "time_min", "current_A", "current_nA"])
        for t, i in zip(timestamps_arr, currents_arr):
            writer.writerow([f"{t:.3f}", f"{t/60:.4f}", f"{i:.12e}", f"{i*1e9:.4f}"])

    print(f"\n  CSV guardado: {csv_path}")

    # --- Gráfico ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     sharex=True)

    time_min = timestamps_arr / 60

    # Panel superior: corriente vs tiempo
    ax1.plot(time_min, currents_arr * 1e9, '.', color='#2196F3',
             markersize=2, alpha=0.6, label='Lecturas')

    # Media móvil (ventana 60 s = ~30 puntos)
    window = min(30, len(currents_arr) // 5)
    if window >= 3:
        kernel = np.ones(window) / window
        smoothed = np.convolve(currents_arr * 1e9, kernel, mode='valid')
        t_smooth = time_min[(window-1)//2 : (window-1)//2 + len(smoothed)]
        ax1.plot(t_smooth, smoothed, '-', color='#F44336', linewidth=1.5,
                 label=f'Media móvil ({window} pts)')

    # Línea de tendencia
    fit_line = slope * timestamps_arr + intercept
    ax1.plot(time_min, fit_line, '--', color='#333333', linewidth=1,
             label=f'Tendencia: {slope*60:+.2f} nA/min ({drift_pct:+.2f}%)')

    ax1.axhline(i_mean * 1e9, color='#999999', linestyle=':', linewidth=0.8)
    ax1.set_ylabel("Corriente oscura [nA]", fontsize=12)
    ax1.set_title(f"Drift temporal — {device_info['label']} (B{device_info['batch']})\n"
                  f"V_ov = {V_OV_TARGET:.1f} V | T = {temp_str} C | "
                  f"{timestamp.strftime('%Y-%m-%d')}",
                  fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9, loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Panel inferior: residuos (desviación de la tendencia)
    residuals = currents_arr * 1e9 - fit_line
    ax2.plot(time_min, residuals, '.', color='#FF9800', markersize=2, alpha=0.6)
    ax2.axhline(0, color='#333333', linewidth=0.8)
    ax2.axhline(+i_std * 1e9, color='#999999', linestyle='--', linewidth=0.5)
    ax2.axhline(-i_std * 1e9, color='#999999', linestyle='--', linewidth=0.5)
    ax2.set_xlabel("Tiempo [min]", fontsize=12)
    ax2.set_ylabel("Residuo [nA]", fontsize=12)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    png_path = os.path.join(OUTPUT_DIR, f"{base_name}.png")
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"  Gráfico guardado: {png_path}")

    print(f"\nCerrá la ventana del gráfico para terminar.")
    plt.show()


if __name__ == "__main__":
    main()
