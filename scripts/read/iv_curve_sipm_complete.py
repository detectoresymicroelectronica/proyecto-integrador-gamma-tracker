#!/usr/bin/env python3
"""
=============================================================================
  MEDICIÓN DE CURVAS I-V PARA SiPM — CAMPAÑA DE CARACTERIZACIÓN
=============================================================================
  Proyecto: Gamma Tracker — Upgrade SiPM para matriz multipixel
  Basado en: iv_curve_sipm.py (2026-08-03, validación de setup)
  Versión: 2.0 (campaña de dispersión V_br)
  
  Dispositivo: onsemi MICROFC-60035-SMT (C-Series, 6×6 mm, µcell 35 µm)
  Instrumento: Keithley 2450 SMU vía USB (USBTMC)
  
  Cambios respecto a v1.0:
    - Barrido en dos fases (grueso + fino) según protocolo de caracterización
    - Gráfico en tiempo real con 3 paneles: I-V lineal, I-V log, √I vs V
    - Estimación automática de V_br por ajuste lineal de √I vs V
    - Metadata extendida (temperatura, lote, modelo, compliance efectivo)
    - Configuración interactiva de SAMPLE_ID al inicio
    - Parámetros preconfigurados para MICROFC-60035-SMT
    
  Uso:
    python iv_curve_sipm.py
    (el script pregunta SAMPLE_ID y temperatura al arrancar)
    
  Setup requerido:
    - Python 3.11+ (Anaconda base)
    - Librerías: pyvisa, pyvisa-py, pyusb, matplotlib, numpy, scipy
    - Driver: libusb-win32 (instalado con Zadig)
    - Keithley 2450 conectado por USB
    
  ADVERTENCIA: 
    Corriente máxima absoluta del MICROFC-60035-SMT: 20 mA.
    El compliance por defecto (100 µA) está 200× por debajo de ese límite.
    NO subir el compliance sin justificación.
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
#  PARÁMETROS DEL DISPOSITIVO (MICROFC-60035-SMT)
# =============================================================================

DEVICE_MODEL    = "MICROFC-60035-SMT"
DEVICE_FAMILY   = "C-Series"
DEVICE_VENDOR   = "onsemi"
VBR_TYP_MIN     = 24.2   # V_br típico mínimo según datasheet [V]
VBR_TYP_MAX     = 24.7   # V_br típico máximo según datasheet [V]
I_MAX_ABSOLUTE  = 20e-3  # Corriente máxima absoluta del dispositivo [A]
VOV_MAX         = 5.0    # Sobrevoltaje máximo recomendado [V]

# =============================================================================
#  CONFIGURACIÓN DEL BARRIDO
# =============================================================================
# Fase 1 - Fino en directa:  -0.8 V → 0 V, paso 0.01 V (curva directa)
# Fase 2 - Grueso en medio:   1 V → 21 V,   paso 1 V    (zona pre-breakdown)
# Fase 3 - Fino en inversa:  21 V → 30 V,   paso 0.05 V (breakdown + post)

# --- Fase 1: Fino en directa (tensiones negativas) ---
V_FINE_FWD_START = -0.3
V_FINE_FWD_STOP  = -0.3
V_FINE_FWD_STEP  = 0.01

# --- Fase 2: Grueso en el medio (zona pre-breakdown) ---
V_COARSE_START  = 1.0     # Inicio fase gruesa [V]
V_COARSE_STOP   = 23.0    # Fin fase gruesa [V]
V_COARSE_STEP   = 1.0     # Paso fase gruesa [V]

# --- Fase 3: Fino en inversa (breakdown + post-breakdown) ---
V_FINE_REV_START = 23.05   # Inicio fase fina inversa [V]
V_FINE_REV_STOP  = 30.0    # Fin fase fina [V] (V_br_max + V_ov_max)
V_FINE_REV_STEP  = 0.01    # Paso fase fina [V]

# --- Límite de corriente (COMPLIANCE) ---
I_COMPLIANCE    = 100e-6  # 100 µA (200× debajo del máximo absoluto de 20 mA)

# --- Temporización ---
NPLC            = 1.0     # 1 PLC = 20 ms a 50 Hz. Subir a 5-10 si hay ruido.
DELAY_PER_POINT = 0.05   # Settling time entre puntos [s]

# --- Operador por defecto ---
OPERATOR        = "PI_GammaTracker"

# --- Archivos de salida ---
OUTPUT_DIR      = "datos_iv"
SAVE_PLOT       = True

# --- Conexión del instrumento ---
VISA_RESOURCE   = None    # None = autodetectar

# =============================================================================
#  PARÁMETROS DE EXTRACCIÓN DE V_br
# =============================================================================
# Rango de voltaje para el ajuste lineal de √I vs V.
# Se ajusta automáticamente, pero estos son los defaults si la detección falla.
VBR_FIT_V_MIN   = 25.0   # Inicio del rango de ajuste [V]
VBR_FIT_V_MAX   = 28.0   # Fin del rango de ajuste [V]
SQRT_I_THRESHOLD = 1e-4  # Umbral mínimo de √I para incluir en el ajuste [√A]


# =============================================================================
#  FUNCIONES AUXILIARES
# =============================================================================

def find_keithley_2450(rm):
    """
    Busca automáticamente un Keithley 2450 entre los recursos VISA disponibles.
    Retorna el resource string o None si no lo encuentra.
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
    Fuente: voltaje | Medición: corriente | Sensing: 2-wire | Terminales: frontales
    
    Basado en la configuración validada el 2026-08-03 (ver LOG).
    Usa :READ? para la lectura (no :MEAS:CURR? ni :MEAS:VOLT? que reconfiguran
    la función de sensado internamente — bug documentado en el LOG).
    """
    # Reset completo
    inst.write("*RST")
    inst.write("*CLS")
    time.sleep(1)
    
    # Configurar como fuente de voltaje, medir corriente
    inst.write(":SOUR:FUNC VOLT")
    inst.write(":SENS:FUNC 'CURR'")
    
    # Rango de voltaje: 200 V range cubre hasta 30 V que necesitamos
    if v_max <= 20:
        inst.write(":SOUR:VOLT:RANG 20")
    else:
        inst.write(":SOUR:VOLT:RANG 200")
    
    # Compliance de corriente
    inst.write(":SENS:CURR:RANG:AUTO ON")
    inst.write(f":SOUR:VOLT:ILIM {i_compliance}")
    
    # NPLC (velocidad/precisión del ADC)
    inst.write(f":SENS:CURR:NPLC {nplc}")
    
    # Desactivar autorange de voltaje en source
    inst.write(":SOUR:VOLT:RANG:AUTO OFF")
    
    # Empezar en 0 V
    inst.write(":SOUR:VOLT 0")
    
    # Seleccionar terminales frontales (banana jacks)
    inst.write(":ROUT:TERM FRON")
    
    # Modo de sensing: 2-wire
    inst.write(":SENS:CURR:RSEN OFF")
    
    print("\n  --- Configuración del instrumento ---")
    print(f"  Fuente: VOLTAJE (rango {'20 V' if v_max <= 20 else '200 V'})")
    print(f"  Medición: CORRIENTE (autorange)")
    print(f"  Compliance: {i_compliance*1e6:.1f} µA")
    print(f"  NPLC: {nplc}")
    print(f"  Terminales: FRONTALES (banana jacks)")
    print(f"  Sensing: 2-wire")
    print(f"  Lectura: :READ? (no reconfigura función de sensado)")


def generate_three_phase_sweep():
    """
    Genera la lista de voltajes para el barrido en tres fases:
    - Fase 1: fino en directa (tensiones negativas)
    - Fase 2: grueso en la zona pre-breakdown
    - Fase 3: fino en la zona de breakdown y post-breakdown
    
    Retorna: array de voltajes, lista de tuplas (nombre, idx_start, idx_end)
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
    Extrae V_br mediante ajuste lineal de √I vs V en la región post-breakdown.
    
    Método: definido por onsemi en el datasheet C-Series (nota 3):
    "The breakdown voltage (V_br) is defined as the value of the voltage 
    intercept of a straight line fit to a plot of √I vs V"
    
    Retorna: dict con V_br, slope, intercept, r_squared, v_fit_range
             o None si no se puede ajustar.
    """
    v = np.array(voltages)
    i = np.array(currents)
    
    # Trabajar solo con corrientes positivas (polarización inversa del SiPM)
    mask_positive = i > 0
    if not np.any(mask_positive):
        return None
    
    sqrt_i = np.sqrt(np.abs(i))
    
    # Autodetección del rango de ajuste si no se especifica
    if v_fit_min is None or v_fit_max is None:
        # Buscar la zona donde √I crece linealmente
        # Criterio: √I > umbral (estamos en post-breakdown)
        mask_above = (sqrt_i > sqrt_i_threshold) & mask_positive
        if np.sum(mask_above) < 5:
            return None
        
        v_above = v[mask_above]
        if v_fit_min is None:
            v_fit_min = v_above[0]  # Primer punto por encima del umbral
        if v_fit_max is None:
            v_fit_max = v_above[-1]  # Último punto medido
    
    # Seleccionar puntos en el rango de ajuste
    mask_fit = (v >= v_fit_min) & (v <= v_fit_max) & mask_positive
    if np.sum(mask_fit) < 5:
        return None
    
    v_fit = v[mask_fit]
    sqrt_i_fit = sqrt_i[mask_fit]
    
    # Ajuste lineal: √I = slope * V + intercept
    slope, intercept, r_value, p_value, std_err = stats.linregress(v_fit, sqrt_i_fit)
    
    if slope <= 0:
        return None
    
    # V_br = -intercept / slope (donde √I = 0)
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
    Incluye columnas calculadas para facilitar el análisis posterior.
    """
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Metadata como comentarios
        for key, value in metadata.items():
            writer.writerow([f"# {key}: {value}"])
        writer.writerow([])
        
        # Encabezado de datos
        writer.writerow(["Voltage_V", "Current_A", "Current_uA", 
                          "AbsCurrent_A", "SqrtAbsCurrent_sqrtA"])
        
        # Datos
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
    Solicita información de la muestra al operador de forma interactiva.
    """
    print("\n--- Información de la muestra ---")
    print(f"  Dispositivo: {DEVICE_MODEL} ({DEVICE_VENDOR} {DEVICE_FAMILY})")
    print()
    
    # SAMPLE_ID
    print("  Nomenclatura: MFC60035_{Lote}_{Número}")
    print("  Lote L1: Invoice 0871... (STAN-2025)")
    print("  Lote L2: Invoice 0872... (STAN-2025-02)")
    print()
    sample_id = input("  SAMPLE_ID (ej. MFC60035_L1_01): ").strip()
    if not sample_id:
        sample_id = "MFC60035_test"
        print(f"    → Usando ID por defecto: {sample_id}")
    
    # Temperatura
    temp_str = input("  Temperatura ambiente [°C] (Enter=no registrada): ").strip()
    if temp_str:
        try:
            temperature = float(temp_str)
            temp_label = f"{temperature:.1f} °C"
        except ValueError:
            temp_label = temp_str
    else:
        temp_label = "no registrada"
    
    # Notas
    notes = input("  Notas (Enter=ninguna): ").strip()
    if not notes:
        notes = ""
    
    return sample_id, temp_label, notes


def setup_realtime_plot(sample_id):
    """
    Configura la figura con 1 panel para visualización en tiempo real:
    I vs V (escala lineal)
    """
    plt.ion()
    fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
    fig.suptitle(f"Curva I-V — {sample_id} — {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 fontsize=12, fontweight='bold')
    
    line1, = ax1.plot([], [], 'b.-', markersize=3, linewidth=0.8)
    ax1.set_xlabel("Voltaje [V]")
    ax1.set_ylabel("Corriente [A]")
    ax1.set_title("I-V (lineal)")
    ax1.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.pause(0.1)
    
    return fig, ax1, (line1,)


def update_plot(fig, axes, lines, measured_v, measured_i, vbr_result=None):
    """
    Actualiza el gráfico I-V lineal en tiempo real.
    """
    ax1 = axes
    line1 = lines[0]
    
    v_arr = np.array(measured_v)
    i_arr = np.array(measured_i)
    
    line1.set_data(v_arr, i_arr)
    ax1.relim()
    ax1.autoscale_view()
    
    if vbr_result is not None:
        ax1.set_title(f"I-V (lineal) — $V_{{br}}$ = {vbr_result['vbr']:.3f} V "
                       f"(R² = {vbr_result['r_squared']:.5f})")
    
    fig.canvas.draw_idle()
    fig.canvas.flush_events()


# =============================================================================
#  MEDICIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 72)
    print("  MEDICIÓN DE CURVA I-V — CAMPAÑA DE CARACTERIZACIÓN SiPM")
    print(f"  Dispositivo: {DEVICE_MODEL} ({DEVICE_VENDOR} {DEVICE_FAMILY})")
    print(f"  V_br esperado: {VBR_TYP_MIN}–{VBR_TYP_MAX} V | I_max: {I_MAX_ABSOLUTE*1e3:.0f} mA")
    print("=" * 72)
    
    # --- Solicitar información de la muestra ---
    sample_id, temperature, notes = prompt_sample_info()
    
    timestamp_start = datetime.now()
    print(f"\n  Fecha/hora: {timestamp_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Muestra:    {sample_id}")
    print(f"  Temperatura: {temperature}")
    
    # --- Crear directorio de salida ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"  Directorio creado: {OUTPUT_DIR}")
    
    # --- Generar lista de voltajes (tres fases) ---
    voltages_to_sweep, phases = generate_three_phase_sweep()
    n_points = len(voltages_to_sweep)
    
    print(f"\n  Barrido: {n_points} puntos total en 3 fases:")
    for name, i_start, i_end in phases:
        n = i_end - i_start
        v0 = voltages_to_sweep[i_start]
        v1 = voltages_to_sweep[i_end - 1]
        print(f"    {name}: {v0:+.2f} → {v1:+.2f} V ({n} pts)")
    print(f"  Compliance: {I_COMPLIANCE*1e6:.1f} µA")
    
    # --- Conectar al instrumento ---
    print("\n[1/5] Buscando Keithley 2450...")
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
    inst.timeout = 10000
    inst.write_termination = '\n'
    inst.read_termination = '\n'
    
    idn = inst.query("*IDN?").strip()
    print(f"  Instrumento: {idn}")
    
    # --- Configurar instrumento ---
    print("\n[2/5] Configurando instrumento...")
    v_abs_max = max(abs(voltages_to_sweep[0]), abs(voltages_to_sweep[-1]))
    setup_keithley(inst, v_abs_max, I_COMPLIANCE, NPLC)
    
    # --- Preparar gráfico en tiempo real ---
    print("\n[3/5] Preparando visualización...")
    fig, axes, lines = setup_realtime_plot(sample_id)
    
    # --- Realizar barrido ---
    print(f"\n[4/5] Iniciando medición ({n_points} puntos)...")
    measured_v = []
    measured_i = []
    compliance_hit = False
    compliance_voltage = None
    
    try:
        inst.write(":OUTP ON")
        print("  Salida ENCENDIDA")
        time.sleep(0.5)
        
        for idx, v_set in enumerate(voltages_to_sweep):
            # Setear voltaje
            inst.write(f":SOUR:VOLT {v_set:.6f}")
            
            # Settling time
            time.sleep(DELAY_PER_POINT)
            
            # Leer corriente con :READ? (no reconfigura sensado — ver LOG bug)
            reading = inst.query(":READ?").strip()
            current = float(reading)
            
            # Usar voltaje seteado (error source Keithley 2450 < 0.02%)
            voltage = v_set
            
            measured_v.append(voltage)
            measured_i.append(current)
            
            # Verificar compliance
            if abs(current) >= I_COMPLIANCE * 0.95:
                compliance_hit = True
                compliance_voltage = voltage
                print(f"\n  ⚠ COMPLIANCE alcanzado a V = {voltage:.3f} V, "
                      f"I = {current*1e6:.2f} µA")
                print(f"    Deteniendo barrido por seguridad.")
                break
            
            # Indicar transición de fase
            for name, i_start, i_end in phases:
                if idx == i_start and idx > 0:
                    print(f"\n  → {name} (V = {v_set:+.2f} V)")
            
            # Actualizar gráfico cada 5 puntos
            if idx % 5 == 0 or idx == n_points - 1:
                update_plot(fig, axes, lines, measured_v, measured_i)
            
            # Progreso
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
        # SIEMPRE apagar la salida
        print("  Apagando salida...")
        inst.write(":SOUR:VOLT 0")
        time.sleep(0.2)
        inst.write(":OUTP OFF")
        print("  Salida APAGADA ✓")
    
    # --- Extraer V_br y guardar datos ---
    if len(measured_v) < 2:
        print("\n  No hay suficientes datos para guardar.")
        inst.close()
        rm.close()
        return
    
    print(f"\n[5/5] Análisis y guardado ({len(measured_v)} puntos)...")
    
    # Extraer V_br
    vbr_result = extract_vbr(measured_v, measured_i)
    
    if vbr_result is not None:
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  V_br = {vbr_result['vbr']:.3f} V                          │")
        print(f"  │  R² = {vbr_result['r_squared']:.6f}                       │")
        print(f"  │  Rango ajuste: {vbr_result['v_fit_min']:.2f}–{vbr_result['v_fit_max']:.2f} V "
              f"({vbr_result['n_points_fit']} pts)    │")
        print(f"  │  V_br datasheet: {VBR_TYP_MIN}–{VBR_TYP_MAX} V              │")
        print(f"  └─────────────────────────────────────────┘")
        
        # Verificar consistencia con datasheet
        if vbr_result['vbr'] < VBR_TYP_MIN - 1.0 or vbr_result['vbr'] > VBR_TYP_MAX + 1.0:
            print(f"  ⚠ ATENCIÓN: V_br fuera del rango típico del datasheet.")
            print(f"    Verificar conexiones, temperatura, o si el dispositivo es correcto.")
    else:
        print("\n  ⚠ No se pudo extraer V_br (datos insuficientes en zona post-breakdown).")
        print("    Posibles causas: compliance muy bajo, rango de voltaje insuficiente,")
        print("    o el dispositivo no está conectado correctamente.")
    
    # Actualizar gráfico final con ajuste
    update_plot(fig, axes, lines, measured_v, measured_i, vbr_result)
    
    # --- Construir metadata ---
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
        "NPLC": NPLC,
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
        "Notas": notes,
    }
    
    # --- Guardar CSV ---
    ts_str = timestamp_start.strftime("%Y%m%d_%H%M%S")
    filename_base = f"IV_{sample_id}_{ts_str}"
    
    csv_path = os.path.join(OUTPUT_DIR, filename_base + ".csv")
    save_data_csv(csv_path, measured_v, measured_i, metadata)
    
    # --- Guardar gráfico ---
    if SAVE_PLOT:
        png_path = os.path.join(OUTPUT_DIR, filename_base + ".png")
        fig.savefig(png_path, dpi=150, bbox_inches='tight')
        print(f"  Gráfico guardado en: {png_path}")
    
    # --- Resumen final ---
    print("\n" + "=" * 72)
    print("  RESUMEN DE LA MEDICIÓN")
    print("=" * 72)
    print(f"  Muestra:          {sample_id}")
    print(f"  Modelo:           {DEVICE_MODEL}")
    print(f"  Temperatura:      {temperature}")
    print(f"  Puntos medidos:   {len(measured_v)}")
    print(f"  Rango V:          {min(measured_v):.3f} → {max(measured_v):.3f} V")
    print(f"  Rango I:          {min(measured_i)*1e6:.4f} → {max(measured_i)*1e6:.4f} µA")
    if vbr_result:
        print(f"  V_br extraído:    {vbr_result['vbr']:.3f} V (R² = {vbr_result['r_squared']:.5f})")
    if compliance_hit:
        print(f"  ⚠ Compliance:    alcanzado a {compliance_voltage:.3f} V")
    print(f"  CSV:              {csv_path}")
    if SAVE_PLOT:
        print(f"  PNG:              {png_path}")
    print(f"  Duración:         {duration_s:.0f} s")
    print("=" * 72)
    
    # --- Mantener gráfico abierto ---
    plt.ioff()
    print("\nCerrá la ventana del gráfico para terminar.")
    plt.show()
    
    # --- Cerrar conexión ---
    inst.close()
    rm.close()
    print("Conexión cerrada. Fin.")


# =============================================================================
if __name__ == "__main__":
    main()
