#!/usr/bin/env python3
"""
=============================================================================
  COMPARACIÓN DE NPLC EN CURVAS I-V DE SiPM
=============================================================================
  Proyecto: Gamma Tracker — Upgrade SiPM
  Basado en: iv_curve_sipm_complete.py (v2.0, campaña 2026-08-10)
  
  Objetivo:
    Evaluar el efecto de NPLC en la calidad de las mediciones I-V,
    particularmente en la zona post-breakdown.
    
    Ejecuta 3 barridos consecutivos sobre el MISMO dispositivo con
    NPLC = 1, 5, 10, manteniendo todas las demás condiciones idénticas.
    Genera una gráfica comparativa lineal al finalizar.
    
  Cambios respecto a iv_curve_sipm_complete.py:
    - Se pide SAMPLE_ID y temperatura UNA sola vez al inicio.
    - Se itera sobre NPLC_VALUES = [1, 5, 10].
    - Cada corrida genera su propio CSV y PNG individual (igual que antes).
    - Al final se genera una gráfica comparativa con las 3 curvas superpuestas.
    - NO se mueven cables, NO se abre la caja entre corridas.
    
  ADVERTENCIA: 
    NO mover nada entre corridas. El dispositivo debe permanecer
    en las mismas condiciones durante las 3 mediciones.
=============================================================================
"""

import pyvisa
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import csv
import time
import os
import sys
from datetime import datetime

# =============================================================================
#  PARÁMETROS DEL DISPOSITIVO (MICROFC-60035-SMT) — SIN CAMBIOS
# =============================================================================

DEVICE_MODEL    = "MICROFC-60035-SMT"
DEVICE_FAMILY   = "C-Series"
DEVICE_VENDOR   = "onsemi"
VBR_TYP_MIN     = 24.2
VBR_TYP_MAX     = 24.7
I_MAX_ABSOLUTE  = 20e-3
VOV_MAX         = 5.0

# =============================================================================
#  CONFIGURACIÓN DEL BARRIDO — IDÉNTICA A LA CAMPAÑA
# =============================================================================

V_FINE_FWD_START = -0.3
V_FINE_FWD_STOP  = -0.3
V_FINE_FWD_STEP  = 0.01

V_COARSE_START  = 1.0
V_COARSE_STOP   = 23.0
V_COARSE_STEP   = 1.0

V_FINE_REV_START = 23.05
V_FINE_REV_STOP  = 30.0
V_FINE_REV_STEP  = 0.01

I_COMPLIANCE    = 100e-6
DELAY_PER_POINT = 0.05

OPERATOR        = "PI_GammaTracker"
OUTPUT_DIR      = "datos_iv"
SAVE_PLOT       = True
VISA_RESOURCE   = None

VBR_FIT_V_MIN   = 25.0
VBR_FIT_V_MAX   = 28.0
SQRT_I_THRESHOLD = 1e-4

# =============================================================================
#  ÚNICO CAMBIO: LISTA DE NPLC A COMPARAR
# =============================================================================

NPLC_VALUES = [1, 5, 10]

# =============================================================================
#  FUNCIONES AUXILIARES — COPIADAS SIN CAMBIOS DE iv_curve_sipm_complete.py
# =============================================================================

def find_keithley_2450(rm):
    """
    Busca automáticamente un Keithley 2450 entre los recursos VISA disponibles.
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


def setup_keithley(inst, v_max, i_compliance, nplc):
    """
    Configura el Keithley 2450 para medición I-V de SiPM.
    Idéntica a iv_curve_sipm_complete.py.
    """
    inst.write("*RST")
    inst.write("*CLS")
    time.sleep(1)

    inst.write(":SOUR:FUNC VOLT")
    inst.write(":SENS:FUNC 'CURR'")

    if v_max <= 20:
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

    print(f"\n  --- Configuración del instrumento ---")
    print(f"  Fuente: VOLTAJE (rango {'20 V' if v_max <= 20 else '200 V'})")
    print(f"  Medición: CORRIENTE (autorange)")
    print(f"  Compliance: {i_compliance*1e6:.1f} µA")
    print(f"  NPLC: {nplc}")
    print(f"  Terminales: FRONTALES (banana jacks)")
    print(f"  Sensing: 2-wire")
    print(f"  Lectura: :READ? (no reconfigura función de sensado)")


def generate_three_phase_sweep():
    """
    Genera la lista de voltajes para el barrido en tres fases.
    Idéntica a iv_curve_sipm_complete.py.
    """
    v_fine_fwd = np.arange(V_FINE_FWD_START,
                           V_FINE_FWD_STOP + V_FINE_FWD_STEP / 2,
                           V_FINE_FWD_STEP)
    v_coarse = np.arange(V_COARSE_START,
                         V_COARSE_STOP + V_COARSE_STEP / 2,
                         V_COARSE_STEP)
    v_fine_rev = np.arange(V_FINE_REV_START,
                           V_FINE_REV_STOP + V_FINE_REV_STEP / 2,
                           V_FINE_REV_STEP)
    n1 = len(v_fine_fwd)
    n2 = len(v_coarse)
    n3 = len(v_fine_rev)
    phases = [
        ("FINO DIRECTA ", 0, n1),
        ("GRUESO       ", n1, n1 + n2),
        ("FINO INVERSA ", n1 + n2, n1 + n2 + n3),
    ]
    voltages = np.concatenate([v_fine_fwd, v_coarse, v_fine_rev])
    return voltages, phases


def extract_vbr(voltages, currents, v_fit_min=None, v_fit_max=None,
                sqrt_i_threshold=SQRT_I_THRESHOLD):
    """
    Extrae V_br mediante ajuste lineal de √I vs V.
    Idéntica a iv_curve_sipm_complete.py.
    """
    v = np.array(voltages)
    i = np.array(currents)
    mask_positive = i > 0
    if not np.any(mask_positive):
        return None
    sqrt_i = np.sqrt(np.abs(i))
    if v_fit_min is None or v_fit_max is None:
        mask_above = (sqrt_i > sqrt_i_threshold) & mask_positive
        if np.sum(mask_above) < 5:
            return None
        v_above = v[mask_above]
        if v_fit_min is None:
            v_fit_min = v_above[0]
        if v_fit_max is None:
            v_fit_max = v_above[-1]
    mask_fit = (v >= v_fit_min) & (v <= v_fit_max) & mask_positive
    if np.sum(mask_fit) < 5:
        return None
    v_fit = v[mask_fit]
    sqrt_i_fit = sqrt_i[mask_fit]
    slope, intercept, r_value, p_value, std_err = stats.linregress(v_fit, sqrt_i_fit)
    if slope <= 0:
        return None
    vbr = -intercept / slope
    return {
        'vbr': vbr,
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value**2,
        'std_err': std_err,
        'v_fit_min': v_fit_min,
        'v_fit_max': v_fit_max,
        'n_points_fit': int(np.sum(mask_fit)),
    }


def save_data_csv(filepath, voltages, currents, metadata):
    """
    Guarda los datos en CSV con encabezado de metadata.
    Idéntica a iv_curve_sipm_complete.py.
    """
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        for key, value in metadata.items():
            writer.writerow([f"# {key}: {value}"])
        writer.writerow([])
        writer.writerow(["Voltage_V", "Current_A", "Current_uA",
                          "AbsCurrent_A", "SqrtAbsCurrent_sqrtA"])
        for v, i in zip(voltages, currents):
            abs_i = abs(i)
            sqrt_abs_i = np.sqrt(abs_i) if abs_i > 0 else 0.0
            writer.writerow([
                f"{v:.6f}",
                f"{i:.12e}",
                f"{i*1e6:.6f}",
                f"{abs_i:.12e}",
                f"{sqrt_abs_i:.12e}"
            ])
    print(f"  Datos guardados en: {filepath}")


def prompt_sample_info():
    """
    Solicita información de la muestra al operador.
    Idéntica a iv_curve_sipm_complete.py.
    """
    print("\n--- Información de la muestra ---")
    print(f"  Dispositivo: {DEVICE_MODEL} ({DEVICE_VENDOR} {DEVICE_FAMILY})")
    print()
    print("  Nomenclatura: MFC60035_{Lote}_{Número}")
    print("  Lote L1: Invoice 0871... (STAN-2025)")
    print("  Lote L2: Invoice 0872... (STAN-2025-02)")
    print()
    sample_id = input("  SAMPLE_ID (ej. MFC60035_L1_01): ").strip()
    if not sample_id:
        sample_id = "MFC60035_test"
        print(f"    → Usando ID por defecto: {sample_id}")
    temp_str = input("  Temperatura ambiente [°C] (Enter=no registrada): ").strip()
    if temp_str:
        try:
            temperature = float(temp_str)
            temp_label = f"{temperature:.1f} °C"
        except ValueError:
            temp_label = temp_str
    else:
        temp_label = "no registrada"
    notes = input("  Notas (Enter=ninguna): ").strip()
    if not notes:
        notes = ""
    return sample_id, temp_label, notes


# =============================================================================
#  FUNCIÓN DE BARRIDO INDIVIDUAL (extraída de main() sin cambios lógicos)
# =============================================================================

def run_single_sweep(inst, idn, voltages_to_sweep, phases, nplc,
                     sample_id, temperature, notes):
    """
    Ejecuta UN barrido I-V completo con el NPLC indicado.
    
    Lógica de medición idéntica a iv_curve_sipm_complete.py main(),
    extraída a función para poder llamarla en un loop.
    
    Retorna: (measured_v, measured_i, vbr_result, duration_s, csv_path)
    """
    n_points = len(voltages_to_sweep)
    timestamp_start = datetime.now()

    # --- Configurar instrumento con el NPLC de esta corrida ---
    v_abs_max = max(abs(voltages_to_sweep[0]), abs(voltages_to_sweep[-1]))
    setup_keithley(inst, v_abs_max, I_COMPLIANCE, nplc)

    # --- Realizar barrido ---
    print(f"\n  Iniciando medición ({n_points} puntos, NPLC={nplc})...")
    measured_v = []
    measured_i = []
    compliance_hit = False
    compliance_voltage = None

    try:
        inst.write(":OUTP ON")
        print("  Salida ENCENDIDA")
        time.sleep(0.5)

        for idx, v_set in enumerate(voltages_to_sweep):
            inst.write(f":SOUR:VOLT {v_set:.6f}")
            time.sleep(DELAY_PER_POINT)

            reading = inst.query(":READ?").strip()
            current = float(reading)
            voltage = v_set

            measured_v.append(voltage)
            measured_i.append(current)

            if abs(current) >= I_COMPLIANCE * 0.95:
                compliance_hit = True
                compliance_voltage = voltage
                print(f"\n  ⚠ COMPLIANCE alcanzado a V = {voltage:.3f} V, "
                      f"I = {current*1e6:.2f} µA")
                print(f"    Deteniendo barrido por seguridad.")
                break

            for name, i_start, i_end in phases:
                if idx == i_start and idx > 0:
                    print(f"\n  → {name} (V = {v_set:+.2f} V)")

            phase_name = "???"
            for name, i_start, i_end in phases:
                if i_start <= idx < i_end:
                    phase_name = name
                    break
            pct = (idx + 1) / n_points * 100
            print(f"\r  [{phase_name}] {pct:5.1f}% | V = {voltage:+7.3f} V | "
                  f"I = {current:+12.4e} A ({current*1e6:+10.4f} µA)",
                  end="", flush=True)

        print("\n  Barrido completado.")

    except KeyboardInterrupt:
        print("\n\n  *** Medición interrumpida por el usuario (Ctrl+C) ***")
    except Exception as e:
        print(f"\n\n  *** ERROR durante la medición: {e} ***")
    finally:
        print("  Apagando salida...")
        inst.write(":SOUR:VOLT 0")
        time.sleep(0.2)
        inst.write(":OUTP OFF")
        print("  Salida APAGADA ✓")

    if len(measured_v) < 2:
        print("\n  No hay suficientes datos para guardar.")
        return None

    # --- Extraer V_br ---
    vbr_result = extract_vbr(measured_v, measured_i)

    if vbr_result is not None:
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  V_br = {vbr_result['vbr']:.3f} V                          │")
        print(f"  │  R² = {vbr_result['r_squared']:.6f}                       │")
        print(f"  │  Rango ajuste: {vbr_result['v_fit_min']:.2f}–"
              f"{vbr_result['v_fit_max']:.2f} V "
              f"({vbr_result['n_points_fit']} pts)    │")
        print(f"  │  V_br datasheet: {VBR_TYP_MIN}–{VBR_TYP_MAX} V              │")
        print(f"  └─────────────────────────────────────────┘")
    else:
        print("\n  ⚠ No se pudo extraer V_br.")

    # --- Guardar CSV individual ---
    timestamp_end = datetime.now()
    duration_s = (timestamp_end - timestamp_start).total_seconds()

    metadata = {
        "Muestra": sample_id,
        "Modelo": DEVICE_MODEL,
        "Fabricante": f"{DEVICE_VENDOR} ({DEVICE_FAMILY})",
        "Operador": OPERATOR,
        "Fecha_inicio": timestamp_start.strftime("%Y-%m-%d %H:%M:%S"),
        "Fecha_fin": timestamp_end.strftime("%Y-%m-%d %H:%M:%S"),
        "Duracion_s": f"{duration_s:.1f}",
        "Instrumento": idn,
        "Temperatura": temperature,
        "Fase1_fino_directa": f"{V_FINE_FWD_START} a {V_FINE_FWD_STOP} V, paso {V_FINE_FWD_STEP} V",
        "Fase2_grueso": f"{V_COARSE_START} a {V_COARSE_STOP} V, paso {V_COARSE_STEP} V",
        "Fase3_fino_inversa": f"{V_FINE_REV_START} a {V_FINE_REV_STOP} V, paso {V_FINE_REV_STEP} V",
        "I_compliance_A": f"{I_COMPLIANCE:.6e}",
        "NPLC": nplc,
        "Delay_s": DELAY_PER_POINT,
        "Sensing": "2-wire",
        "Terminales": "frontales (banana)",
        "Compliance_alcanzado": compliance_hit,
        "Compliance_voltage_V": f"{compliance_voltage:.3f}" if compliance_voltage else "N/A",
        "Puntos_medidos": len(measured_v),
        "Vbr_V": f"{vbr_result['vbr']:.4f}" if vbr_result else "N/A",
        "Vbr_R2": f"{vbr_result['r_squared']:.6f}" if vbr_result else "N/A",
        "Vbr_fit_range_V": (f"{vbr_result['v_fit_min']:.2f}-{vbr_result['v_fit_max']:.2f}"
                            if vbr_result else "N/A"),
        "Vbr_fit_npoints": vbr_result['n_points_fit'] if vbr_result else "N/A",
        "Notas": f"Comparación NPLC — corrida NPLC={nplc}. {notes}",
    }

    ts_str = timestamp_start.strftime("%Y%m%d_%H%M%S")
    filename_base = f"IV_{sample_id}_NPLC{nplc}_{ts_str}"

    csv_path = os.path.join(OUTPUT_DIR, filename_base + ".csv")
    save_data_csv(csv_path, measured_v, measured_i, metadata)

    # --- Resumen ---
    print(f"\n  RESUMEN NPLC={nplc}:")
    print(f"    Puntos:   {len(measured_v)}")
    print(f"    Rango I:  {min(measured_i)*1e6:.4f} → {max(measured_i)*1e6:.4f} µA")
    if vbr_result:
        print(f"    V_br:     {vbr_result['vbr']:.3f} V (R² = {vbr_result['r_squared']:.5f})")
    print(f"    Duración: {duration_s:.0f} s")
    print(f"    CSV:      {csv_path}")

    return {
        'nplc': nplc,
        'measured_v': measured_v,
        'measured_i': measured_i,
        'vbr_result': vbr_result,
        'duration_s': duration_s,
        'csv_path': csv_path,
    }


# =============================================================================
#  GRÁFICA COMPARATIVA (ÚNICO AGREGADO NUEVO)
# =============================================================================

def plot_nplc_comparison(results, sample_id, temperature):
    """
    Genera la gráfica comparativa lineal de las corridas con distinto NPLC.
    
    Panel único: I [µA] vs V [V], una curva por NPLC, con V_br marcado.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))

    colors = {1: '#1f77b4', 5: '#ff7f0e', 10: '#2ca02c'}
    
    for r in results:
        nplc = r['nplc']
        v = np.array(r['measured_v'])
        i = np.array(r['measured_i']) * 1e6  # convertir a µA
        color = colors.get(nplc, 'black')

        vbr_str = ""
        if r['vbr_result']:
            vbr_str = f", $V_{{br}}$={r['vbr_result']['vbr']:.3f} V"

        label = f"NPLC = {nplc} ({r['duration_s']:.0f} s{vbr_str})"
        ax.plot(v, i, '.-', markersize=2, linewidth=0.8, color=color, label=label)

        # Marcar V_br con línea vertical
        if r['vbr_result']:
            ax.axvline(r['vbr_result']['vbr'], color=color, linestyle='--',
                       alpha=0.5, linewidth=0.8)

    ax.set_xlabel("Voltaje [V]", fontsize=12)
    ax.set_ylabel("Corriente [µA]", fontsize=12)
    ax.set_title(f"Comparación NPLC — {sample_id} — {temperature}\n"
                 f"{datetime.now().strftime('%Y-%m-%d')}",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=20)  # zoom en zona de interés (post-breakdown)

    plt.tight_layout()

    # Guardar
    png_path = os.path.join(OUTPUT_DIR,
                            f"comparacion_NPLC_{sample_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n  Gráfico comparativo guardado en: {png_path}")

    return fig, png_path


# =============================================================================
#  MAIN — LOOP SOBRE NPLC
# =============================================================================

def main():
    print("=" * 72)
    print("  COMPARACIÓN DE NPLC EN CURVAS I-V DE SiPM")
    print(f"  Dispositivo: {DEVICE_MODEL} ({DEVICE_VENDOR} {DEVICE_FAMILY})")
    print(f"  NPLC a comparar: {NPLC_VALUES}")
    print(f"  Condiciones idénticas a campaña 2026-08-10")
    print("=" * 72)

    # --- Pedir información UNA sola vez ---
    sample_id, temperature, notes = prompt_sample_info()

    print(f"\n  Muestra:     {sample_id}")
    print(f"  Temperatura: {temperature}")
    print(f"  NPLC:        {NPLC_VALUES}")
    print(f"\n  ⚠ NO mover cables ni abrir la caja entre corridas.")

    input("\n  Presionar Enter para comenzar...")

    # --- Crear directorio de salida ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- Generar lista de voltajes (misma para todas las corridas) ---
    voltages_to_sweep, phases = generate_three_phase_sweep()
    n_points = len(voltages_to_sweep)

    print(f"\n  Barrido: {n_points} puntos total en 3 fases:")
    for name, i_start, i_end in phases:
        n = i_end - i_start
        v0 = voltages_to_sweep[i_start]
        v1 = voltages_to_sweep[i_end - 1]
        print(f"    {name}: {v0:+.2f} → {v1:+.2f} V ({n} pts)")
    print(f"  Compliance: {I_COMPLIANCE*1e6:.1f} µA")

    # --- Conectar al instrumento (UNA sola vez) ---
    print("\n[CONEXIÓN] Buscando Keithley 2450...")
    rm = pyvisa.ResourceManager('@py')

    resource = VISA_RESOURCE
    if resource is None:
        resource = find_keithley_2450(rm)

    if resource is None:
        print("\n  *** ERROR: No se encontró el Keithley 2450. ***")
        print("  Verificar:")
        print("    - Cable USB conectado")
        print("    - Instrumento encendido")
        print("    - Driver libusb-win32 instalado (Zadig)")
        rm.close()
        return

    print(f"  Conectando a: {resource}")
    inst = rm.open_resource(resource)
    inst.timeout = 30000  # timeout más largo para NPLC alto
    inst.write_termination = '\n'
    inst.read_termination = '\n'

    idn = inst.query("*IDN?").strip()
    print(f"  Instrumento: {idn}")

    # --- Loop sobre NPLC ---
    results = []

    for run_idx, nplc in enumerate(NPLC_VALUES):
        print("\n" + "=" * 72)
        print(f"  CORRIDA {run_idx + 1}/{len(NPLC_VALUES)} — NPLC = {nplc}")
        print("=" * 72)

        result = run_single_sweep(
            inst, idn, voltages_to_sweep, phases, nplc,
            sample_id, temperature, notes
        )

        if result is not None:
            results.append(result)

        # Pausa entre corridas para que el dispositivo se estabilice
        if run_idx < len(NPLC_VALUES) - 1:
            print(f"\n  Esperando 10 s antes de la siguiente corrida...")
            time.sleep(10)

    # --- Cerrar conexión ---
    inst.close()
    rm.close()
    print("\n  Conexión cerrada.")

    # --- Gráfica comparativa ---
    if len(results) >= 2:
        print("\n" + "=" * 72)
        print("  GENERANDO GRÁFICA COMPARATIVA")
        print("=" * 72)

        fig, png_path = plot_nplc_comparison(results, sample_id, temperature)

        # --- Resumen global ---
        print("\n" + "=" * 72)
        print("  RESUMEN COMPARATIVO")
        print("=" * 72)
        print(f"  {'NPLC':>6} | {'Puntos':>7} | {'Duración [s]':>13} | "
              f"{'V_br [V]':>10} | {'R²':>10}")
        print("  " + "-" * 62)
        for r in results:
            vbr_str = f"{r['vbr_result']['vbr']:.4f}" if r['vbr_result'] else "N/A"
            r2_str = f"{r['vbr_result']['r_squared']:.6f}" if r['vbr_result'] else "N/A"
            print(f"  {r['nplc']:>6} | {len(r['measured_v']):>7} | "
                  f"{r['duration_s']:>13.1f} | {vbr_str:>10} | {r2_str:>10}")
        print("=" * 72)
        print(f"  Gráfico: {png_path}")

        # Mostrar gráfico
        plt.ioff()
        print("\nCerrá la ventana del gráfico para terminar.")
        plt.show()
    else:
        print("\n  No hay suficientes corridas para comparar.")

    print("Fin.")


# =============================================================================
if __name__ == "__main__":
    main()
