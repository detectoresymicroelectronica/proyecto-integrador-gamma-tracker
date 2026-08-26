#!/usr/bin/env python3
"""
=============================================================================
  BIAS DC DE SiPM PARA MEDICIÓN DE PULSOS — Dispositivo MFC60035_05
=============================================================================
  Proyecto: Gamma Tracker — Medición de pulsos SiPM
  Fecha de creación: 2026-08-25

  Descripción:
    Aplica un voltaje de bias DC estable al SiPM #05 a través del Keithley
    2450 SMU, para observar los pulsos (dark counts / señales de fotones)
    en el osciloscopio mediante la fast output (J2) de la PCB breakout.

    El script:
      1. Verifica las conexiones (checklist interactivo)
      2. Permite elegir V_ov (voltaje sobre breakdown)
      3. Valida TODOS los parámetros antes de aplicar voltaje
      4. Verifica la configuración del instrumento por readback
      5. Rampa el voltaje gradualmente (protección contra transitorios)
      6. Monitorea la corriente en tiempo real
      7. Apaga de forma segura ante cualquier error o Ctrl+C

  Configuración de bias: Config A (AND9782/D, elegida en LOG 4)
    ┌─────────────────────────────────────────────────────────┐
    │  Keithley 2450          PCB Breakout                    │
    │  ┌──────────┐          ┌───────────────┐                │
    │  │ HI (+)  ─┼── → ────┼─ J1 (ÁNODO)   │                │
    │  │ LO (−)  ─┼── → ────┼─ J3 (CÁTODO)  │  ← GND        │
    │  └──────────┘          │               │                │
    │                        │ J2 (FAST OUT) ─┼── → Oscilosc. │
    │                        └───────────────┘                │
    └─────────────────────────────────────────────────────────┘

    En Config A el Keithley sourcea voltaje NEGATIVO.
    V_source = −(V_br + V_ov)
    La corriente medida es NEGATIVA (se muestra como |I|).

  Dispositivo: onsemi MICROFC-60035-SMT (C-Series, 6×6 mm, µcell 35 µm)
  V_br (dispositivo #05, medido 11/08/2026 a 16°C): 24.719 V
  I_dark esperada a V_ov = 2.5 V: ~611 nA (medida 24/08 a 16°C)

  Instrumento: Keithley 2450 SMU vía USB (USBTMC)

  Setup requerido:
    - Python 3.11+ (Anaconda base)
    - Librerías: pyvisa, pyvisa-py, pyusb
    - Driver: libusb-win32 (instalado con Zadig)
    - Keithley 2450 conectado por USB

  Uso:
    python bias_sipm_05.py

  ADVERTENCIA:
    Corriente máxima absoluta del MICROFC-60035-SMT: 20 mA.
    El compliance por defecto (100 µA) está 200× por debajo de ese límite.
    NO subir el compliance sin justificación.
=============================================================================
"""

import pyvisa
import time
import sys
import signal
from datetime import datetime

# =============================================================================
#  PARÁMETROS DEL DISPOSITIVO (NO MODIFICAR sin justificación)
# =============================================================================

DEVICE_ID = "MFC60035_05"
V_BR = 24.719              # V_br medido el 11/08/2026 a 16°C [V]
V_BR_TEMP_REF = 16.0       # Temperatura a la que se midió V_br [°C]
DV_BR_DT = 21.5e-3         # Coeficiente de temperatura [V/°C] (datasheet)
I_MAX_ABSOLUTE = 20e-3     # Corriente máxima absoluta del SiPM [A]
I_DARK_EXPECTED_nA = 611.0  # I_dark esperada a V_ov=2.5V, 16°C [nA]

# =============================================================================
#  PARÁMETROS DE PROTECCIÓN (modificar con precaución)
# =============================================================================

I_COMPLIANCE = 100e-6       # Compliance de corriente [A] (100 µA)
                             # → 200× por debajo de I_max (20 mA)
                             # → Suficiente: I_dark máxima medida ~611 nA

NPLC = 1.0                  # Ciclos de línea para medición de corriente
                             # NPLC=1 → integración ~20 ms (50 Hz)

V_OV_MIN_SOFT = 0.5         # V_ov mínimo recomendado [V] (warning)
V_OV_MAX_SOFT = 5.0         # V_ov máximo recomendado [V] (datasheet)
V_OV_MAX_HARD = 7.0         # V_ov máximo absoluto [V] (el script bloquea)
V_BIAS_MAX_HARD = 32.0      # V_bias máximo absoluto [V] (bloqueo)

V_RAMP_STEP = 1.0           # Paso de la rampa de voltaje [V]
V_RAMP_DELAY = 0.3          # Delay entre pasos de la rampa [s]
SETTLING_TIME = 2.0          # Tiempo de estabilización post-rampa [s]
MONITOR_INTERVAL = 2.0      # Intervalo de monitoreo de corriente [s]

# =============================================================================
#  VARIABLE GLOBAL PARA SHUTDOWN SEGURO
# =============================================================================

_inst_global = None       # Referencia para el handler de Ctrl+C
_v_current_global = 0.0   # Voltaje actual del source (para rampa de apagado)


# =============================================================================
#  FUNCIONES AUXILIARES
# =============================================================================

def find_keithley(rm):
    """
    Busca el Keithley 2450 entre los recursos USB disponibles.
    Retorna el resource string o None si no lo encuentra.
    """
    resources = rm.list_resources()

    if not resources:
        return None

    print("  Recursos VISA encontrados:")
    for res in resources:
        if "USB" not in res.upper():
            continue
        try:
            inst = rm.open_resource(res)
            inst.timeout = 5000
            inst.write_termination = '\n'
            inst.read_termination = '\n'
            idn = inst.query("*IDN?").strip()
            print(f"    {res}")
            print(f"    → {idn}")
            inst.close()
            if "2450" in idn or "MODEL 2450" in idn.upper():
                return res
        except Exception as e:
            print(f"    {res} → Error: {e}")

    return None


def setup_instrument(inst, i_compliance, nplc):
    """
    Configura el Keithley 2450 para bias DC en Config A.

    Fuente:   Voltaje (valores negativos para inversa en Config A)
    Medición: Corriente
    Sensing:  2-wire (frontales, banana jacks)

    Retorna True si la configuración fue verificada correctamente.
    """
    # ── Reset completo ──
    inst.write("*RST")
    inst.write("*CLS")
    time.sleep(1)

    # ── Fuente de voltaje ──
    inst.write(":SOUR:FUNC VOLT")

    # ── Rango de voltaje: 200 V ──
    # Necesario porque V_bias > 20 V (el rango de 20 V no alcanza)
    inst.write(":SOUR:VOLT:RANG 200")
    inst.write(":SOUR:VOLT:RANG:AUTO OFF")

    # ── Voltaje inicial: 0 V ──
    inst.write(":SOUR:VOLT 0")

    # ── Medición de corriente ──
    inst.write(":SENS:FUNC 'CURR'")
    inst.write(":SENS:CURR:RANG:AUTO ON")

    # ── Compliance (límite de corriente) ──
    inst.write(f":SOUR:VOLT:ILIM {i_compliance}")

    # ── NPLC ──
    inst.write(f":SENS:CURR:NPLC {nplc}")

    # ── Terminales frontales ──
    inst.write(":ROUT:TERM FRON")

    # ── 2-wire sensing ──
    inst.write(":SENS:CURR:RSEN OFF")

    # ── Salida apagada (confirmación) ──
    inst.write(":OUTP OFF")

    return True


def verify_instrument_config(inst, i_compliance, nplc):
    """
    Verifica la configuración del instrumento leyendo los parámetros de vuelta.
    Compara cada valor seteado contra el valor leído del instrumento.

    Retorna (ok, mensajes) donde ok es True si todo coincide.
    """
    errors = []
    warnings = []

    # ── Verificar función de fuente ──
    sour_func = inst.query(":SOUR:FUNC?").strip()
    if "VOLT" in sour_func.upper():
        print(f"    ✓ Fuente: {sour_func}")
    else:
        errors.append(f"Fuente esperada VOLT, leída: {sour_func}")

    # ── Verificar función de medición ──
    sens_func = inst.query(":SENS:FUNC?").strip()
    if "CURR" in sens_func.upper():
        print(f"    ✓ Medición: {sens_func}")
    else:
        errors.append(f"Medición esperada CURR, leída: {sens_func}")

    # ── Verificar rango de voltaje ──
    v_range = float(inst.query(":SOUR:VOLT:RANG?").strip())
    if v_range >= 200:
        print(f"    ✓ Rango voltaje: {v_range:.0f} V")
    else:
        errors.append(f"Rango esperado 200 V, leído: {v_range} V")

    # ── Verificar compliance ──
    ilim = float(inst.query(":SOUR:VOLT:ILIM?").strip())
    # Tolerancia del 5% en la lectura
    if abs(ilim - i_compliance) / i_compliance < 0.05:
        print(f"    ✓ Compliance: {ilim*1e6:.1f} µA")
    else:
        errors.append(f"Compliance esperado {i_compliance*1e6:.1f} µA, "
                      f"leído: {ilim*1e6:.1f} µA")

    # ── Verificar NPLC ──
    nplc_read = float(inst.query(":SENS:CURR:NPLC?").strip())
    if abs(nplc_read - nplc) < 0.01:
        print(f"    ✓ NPLC: {nplc_read}")
    else:
        warnings.append(f"NPLC esperado {nplc}, leído: {nplc_read}")

    # ── Verificar terminales ──
    term = inst.query(":ROUT:TERM?").strip()
    if "FRON" in term.upper():
        print(f"    ✓ Terminales: {term}")
    else:
        errors.append(f"Terminales esperadas FRON, leídas: {term}")

    # ── Verificar sensing ──
    rsen = inst.query(":SENS:CURR:RSEN?").strip()
    if rsen == "0" or "OFF" in rsen.upper():
        print(f"    ✓ Sensing: 2-wire (RSEN OFF)")
    else:
        warnings.append(f"RSEN esperado OFF, leído: {rsen}")

    # ── Verificar salida apagada ──
    outp = inst.query(":OUTP?").strip()
    if outp == "0" or "OFF" in outp.upper():
        print(f"    ✓ Salida: OFF")
    else:
        errors.append(f"Salida debería estar OFF, leída: {outp}")

    # ── Verificar voltaje en 0 ──
    v_set = float(inst.query(":SOUR:VOLT?").strip())
    if abs(v_set) < 0.01:
        print(f"    ✓ Voltaje seteado: {v_set:.6f} V")
    else:
        errors.append(f"Voltaje debería ser 0 V, leído: {v_set} V")

    # ── Resumen ──
    for w in warnings:
        print(f"    ⚠ {w}")
    for e in errors:
        print(f"    ✖ {e}")

    return len(errors) == 0


def ramp_voltage(inst, v_start, v_target, step_size, delay):
    """
    Rampa gradual de voltaje para proteger el SiPM.

    En Config A, los voltajes son NEGATIVOS para inversa:
      - Encendido: 0 → −27 V (rampa hacia más negativo)
      - Apagado:  −27 → 0 V (rampa hacia menos negativo)

    Monitorea corriente en cada paso. Aborta si se alcanza compliance.

    Retorna: (éxito: bool, voltaje_final: float)
    """
    global _v_current_global

    # Calcular pasos
    delta = v_target - v_start
    if abs(delta) < 0.001:
        return True, v_start

    direction = 1 if delta > 0 else -1
    n_steps = max(1, int(abs(delta) / step_size))

    # Generar lista de voltajes con pasos limpios
    voltages = []
    for i in range(1, n_steps + 1):
        v = v_start + direction * step_size * i
        # Clampar al target
        if direction > 0:
            v = min(v, v_target)
        else:
            v = max(v, v_target)
        voltages.append(round(v, 6))

    # Asegurar que el target exacto esté al final
    if abs(voltages[-1] - v_target) > 0.001:
        voltages.append(v_target)
    # Eliminar duplicados consecutivos
    voltages_clean = [voltages[0]]
    for v in voltages[1:]:
        if abs(v - voltages_clean[-1]) > 0.001:
            voltages_clean.append(v)
    voltages = voltages_clean

    for idx, v in enumerate(voltages):
        inst.write(f":SOUR:VOLT {v:.6f}")
        _v_current_global = v
        time.sleep(delay)

        # Leer corriente (usa :READ? para no reconfigurar sensado)
        reading = inst.query(":READ?").strip()
        current = float(reading)
        abs_current = abs(current)

        pct = (idx + 1) / len(voltages) * 100
        print(f"\r  Rampa [{pct:5.1f}%]: V = {v:+8.3f} V | "
              f"|I| = {abs_current*1e9:8.1f} nA", end="", flush=True)

        # Verificar compliance
        if abs_current >= I_COMPLIANCE * 0.95:
            print(f"\n\n  ✖ COMPLIANCE ALCANZADO durante rampa")
            print(f"    V = {v:+.3f} V | I = {abs_current*1e6:.2f} µA")
            print(f"    Límite: {I_COMPLIANCE*1e6:.1f} µA")
            print(f"    ABORTANDO rampa por seguridad del dispositivo.")
            return False, v

    print()  # Newline después de la rampa
    return True, v_target


def safe_shutdown(inst, current_voltage):
    """
    Apagado seguro: rampa gradual a 0 V + apagar salida.
    Se llama en cualquier condición de salida (normal, error, Ctrl+C).
    """
    global _v_current_global

    print("\n  ┌─────────────────────────────────────┐")
    print("  │  APAGADO SEGURO                     │")
    print("  └─────────────────────────────────────┘")

    try:
        # Rampa gradual si el voltaje no está cerca de 0
        if abs(current_voltage) > 0.5:
            print(f"  Rampa: {current_voltage:+.3f} V → 0 V...")
            ramp_voltage(inst, current_voltage, 0.0, V_RAMP_STEP, 0.1)

        # Forzar 0 V
        inst.write(":SOUR:VOLT 0")
        time.sleep(0.2)
        _v_current_global = 0.0

        # Apagar salida
        inst.write(":OUTP OFF")

        # Verificar que se apagó
        time.sleep(0.2)
        outp = inst.query(":OUTP?").strip()
        if outp == "0" or "OFF" in outp.upper():
            print("  ✓ Salida APAGADA")
        else:
            print(f"  ⚠ Estado de salida: {outp} — verificar manualmente")

        v_check = float(inst.query(":SOUR:VOLT?").strip())
        print(f"  ✓ Voltaje: {v_check:.6f} V")

    except Exception as e:
        print(f"  ⚠ Error durante apagado seguro: {e}")
        # Intento de emergencia
        try:
            inst.write(":OUTP OFF")
            print("  ⚠ Salida forzada OFF (sin rampa)")
        except Exception:
            print("  ✖ NO SE PUDO APAGAR LA SALIDA")
            print("  ✖ APAGAR MANUALMENTE EL KEITHLEY 2450")


def signal_handler(signum, frame):
    """Handler de Ctrl+C: ejecuta apagado seguro y sale."""
    global _inst_global, _v_current_global
    print("\n\n  *** Ctrl+C detectado ***")
    if _inst_global is not None:
        safe_shutdown(_inst_global, _v_current_global)
    sys.exit(0)


# =============================================================================
#  FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    global _inst_global, _v_current_global

    # ── Registrar handler de Ctrl+C desde el inicio ──
    signal.signal(signal.SIGINT, signal_handler)

    # ════════════════════════════════════════════════════════════════════
    #  ENCABEZADO
    # ════════════════════════════════════════════════════════════════════

    print()
    print("=" * 70)
    print("  BIAS DC DE SiPM PARA MEDICIÓN DE PULSOS")
    print(f"  Dispositivo: {DEVICE_ID}")
    print(f"  V_br = {V_BR:.3f} V (medido a {V_BR_TEMP_REF:.0f} °C)")
    print(f"  Config A: cátodo = GND, ánodo = −Vbias")
    print("=" * 70)

    # ════════════════════════════════════════════════════════════════════
    #  PASO 1: VERIFICACIÓN DE CONEXIONES
    # ════════════════════════════════════════════════════════════════════

    print("\n" + "─" * 70)
    print("  PASO 1: VERIFICACIÓN DE CONEXIONES FÍSICAS")
    print("─" * 70)
    print("""
  Diagrama de conexión (Config A — AND9782/D):

  Keithley 2450                PCB Breakout SiPM
  ┌──────────────┐            ┌─────────────────────────┐
  │              │            │                         │
  │  HI (+) ────┼── rojo ───┼── J1 (ANODE_BIAS)       │
  │  [banana]    │            │       ↓                 │
  │              │            │   Pin 1 (Ánodo) ──┐     │
  │              │            │                   │SiPM │
  │              │            │   Pin 3 (Cátodo) ─┘     │
  │              │            │       ↓                 │
  │  LO (−) ────┼── negro ──┼── J3 (CATHODE_GND)      │
  │  [banana]    │            │                         │
  └──────────────┘            │   Pin 2 (Fast Out)      │
                              │       ↓                 │
  Osciloscopio                │                         │
  ┌──────────────┐            │                         │
  │  CH ────────┼── señal ──┼── J2 (FAST_OUT)          │
  │  GND ───────┼── malla ──┼── J3 (CATHODE_GND)      │
  └──────────────┘            └─────────────────────────┘

  CHECKLIST — verificar cada punto antes de continuar:

    [ ] 1. Keithley HI (+, banana roja)  → J1 (ANODE_BIAS)
    [ ] 2. Keithley LO (−, banana negra) → J3 (CATHODE_GND)
    [ ] 3. Fast Output J2 → canal del osciloscopio
    [ ] 4. GND del osciloscopio → J3 (compartida con Keithley LO)
    [ ] 5. SiPM en OSCURIDAD (cubierta opaca) para dark counts
    [ ] 6. Keithley 2450 ENCENDIDO y conectado por USB
    [ ] 7. NO hay otros instrumentos conectados a los mismos puntos
    [ ] 8. Cables en buen estado, conexiones firmes
""")

    try:
        input("  Presionar ENTER cuando TODAS las conexiones estén verificadas...")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelado.")
        return

    # ════════════════════════════════════════════════════════════════════
    #  PASO 2: SELECCIÓN DE V_ov
    # ════════════════════════════════════════════════════════════════════

    print("\n" + "─" * 70)
    print("  PASO 2: SELECCIÓN DE SOBRETENSIÓN (V_ov)")
    print("─" * 70)

    print(f"\n  Parámetros del dispositivo {DEVICE_ID}:")
    print(f"    V_br = {V_BR:.3f} V (medido a {V_BR_TEMP_REF:.0f} °C)")
    print(f"    dV_br/dT = {DV_BR_DT*1e3:.1f} mV/°C (datasheet)")
    print(f"    V_ov recomendado: {V_OV_MIN_SOFT:.1f} – {V_OV_MAX_SOFT:.1f} V (datasheet)")
    print(f"    V_ov típico para pulsos: 2.5 – 3.5 V")
    print(f"    I_dark esperada (V_ov=2.5V, 16°C): ~{I_DARK_EXPECTED_nA:.0f} nA")

    print(f"\n  NOTA: V_br fue medido a {V_BR_TEMP_REF:.0f} °C. Si la temperatura")
    print(f"  actual es diferente, el V_ov efectivo variará:")
    print(f"    ΔV_br ≈ {DV_BR_DT*1e3:.1f} mV por cada °C de diferencia")
    print(f"    Ej: a 21 °C → V_br ≈ {V_BR + DV_BR_DT*(21-V_BR_TEMP_REF):.3f} V "
          f"(+{DV_BR_DT*(21-V_BR_TEMP_REF)*1e3:.0f} mV)")

    while True:
        try:
            v_ov_str = input(f"\n  Ingresar V_ov [V] (rango {V_OV_MIN_SOFT}–{V_OV_MAX_SOFT}): ").strip()
            v_ov = float(v_ov_str)
        except ValueError:
            print("  ⚠ Valor inválido. Ingresar un número (ej: 2.5)")
            continue
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelado.")
            return

        # ── Validación 1: no negativo ──
        if v_ov < 0:
            print("  ✖ V_ov debe ser positivo (es la sobretensión sobre V_br).")
            continue

        # ── Validación 2: bloqueo absoluto ──
        if v_ov > V_OV_MAX_HARD:
            print(f"  ✖ V_ov = {v_ov:.2f} V excede el límite absoluto "
                  f"({V_OV_MAX_HARD:.1f} V).")
            print(f"     El script no permite valores tan altos por seguridad.")
            continue

        # ── Validación 3: V_bias absoluto ──
        v_bias_check = V_BR + v_ov
        if v_bias_check > V_BIAS_MAX_HARD:
            print(f"  ✖ V_bias resultante ({v_bias_check:.3f} V) excede el "
                  f"límite de {V_BIAS_MAX_HARD:.1f} V.")
            continue

        # ── Validación 4: warning por debajo del mínimo ──
        if v_ov < V_OV_MIN_SOFT:
            print(f"  ⚠ V_ov = {v_ov:.2f} V está por debajo del mínimo "
                  f"recomendado ({V_OV_MIN_SOFT:.1f} V).")
            print(f"     Los pulsos podrían ser muy pequeños o inexistentes.")
            resp = input("  ¿Continuar de todas formas? (s/N): ").strip().lower()
            if resp != 's':
                continue

        # ── Validación 5: warning por encima del máximo ──
        if v_ov > V_OV_MAX_SOFT:
            print(f"\n  ⚠ ATENCIÓN: V_ov = {v_ov:.2f} V excede el máximo "
                  f"recomendado ({V_OV_MAX_SOFT:.1f} V).")
            print(f"     Aumentan significativamente: DCR, crosstalk, afterpulsing.")
            print(f"     Riesgo de daño si la temperatura es alta.")
            resp = input("  ¿Continuar bajo su responsabilidad? (s/N): ").strip().lower()
            if resp != 's':
                continue

        break

    # ── Calcular voltajes ──
    v_bias = V_BR + v_ov                # Magnitud del bias [V]
    v_source = -(V_BR + v_ov)           # Voltaje del source (Config A → NEGATIVO)

    # ════════════════════════════════════════════════════════════════════
    #  PASO 3: VERIFICACIONES DE SEGURIDAD
    # ════════════════════════════════════════════════════════════════════

    print("\n" + "─" * 70)
    print("  PASO 3: VERIFICACIONES DE SEGURIDAD")
    print("─" * 70)

    print(f"\n  Parámetros calculados:")
    print(f"    V_br      = {V_BR:>10.3f} V")
    print(f"    V_ov      = {v_ov:>10.3f} V")
    print(f"    V_bias    = {v_bias:>10.3f} V  (= V_br + V_ov)")
    print(f"    V_source  = {v_source:>+10.3f} V  (Config A → negativo)")
    print(f"    Compliance= {I_COMPLIANCE*1e6:>10.1f} µA")

    print(f"\n  Verificaciones:")

    all_ok = True

    # ── Check 1: Voltaje dentro del rango del Keithley 2450 ──
    if abs(v_source) > 200:
        print(f"    ✖ |V_source| = {abs(v_source):.3f} V > 200 V "
              f"(rango máximo del 2450)")
        all_ok = False
    else:
        print(f"    ✓ |V_source| = {abs(v_source):.3f} V < 200 V "
              f"(dentro del rango del instrumento)")

    # ── Check 2: Compliance vs I_max ──
    margin_compliance = I_MAX_ABSOLUTE / I_COMPLIANCE
    if margin_compliance < 10:
        print(f"    ✖ Margen compliance/I_max = {margin_compliance:.0f}× "
              f"(debe ser >= 10×)")
        all_ok = False
    else:
        print(f"    ✓ Margen compliance/I_max = {margin_compliance:.0f}× "
              f"({I_COMPLIANCE*1e6:.0f} µA vs {I_MAX_ABSOLUTE*1e3:.0f} mA)")

    # ── Check 3: Potencia máxima si compliance ──
    p_max_compliance = v_bias * I_COMPLIANCE
    print(f"    ✓ P_max (si compliance) = {p_max_compliance*1e3:.2f} mW "
          f"(despreciable)")

    # ── Check 4: V_bias vs V_br ──
    if v_bias < V_BR:
        print(f"    ⚠ V_bias ({v_bias:.3f} V) < V_br ({V_BR:.3f} V)")
        print(f"       El SiPM no estará en modo Geiger — no habrá pulsos.")
    else:
        print(f"    ✓ V_bias ({v_bias:.3f} V) > V_br ({V_BR:.3f} V) "
              f"→ modo Geiger activo")

    # ── Check 5: V_ov dentro del rango recomendado ──
    if V_OV_MIN_SOFT <= v_ov <= V_OV_MAX_SOFT:
        print(f"    ✓ V_ov = {v_ov:.2f} V dentro del rango recomendado "
              f"({V_OV_MIN_SOFT}–{V_OV_MAX_SOFT} V)")
    else:
        print(f"    ⚠ V_ov = {v_ov:.2f} V fuera del rango recomendado "
              f"({V_OV_MIN_SOFT}–{V_OV_MAX_SOFT} V)")

    # ── Check 6: Consistencia aritmética ──
    if abs(v_source + v_bias) > 0.001:
        print(f"    ✖ Error de consistencia: V_source + V_bias = "
              f"{v_source + v_bias:.6f} (debería ser 0)")
        all_ok = False
    else:
        print(f"    ✓ Consistencia: V_source = −V_bias ✓")

    # ── Check 7: V_source es negativo (Config A) ──
    if v_source >= 0:
        print(f"    ✖ V_source = {v_source:+.3f} V es positivo. "
              f"En Config A debe ser NEGATIVO.")
        all_ok = False
    else:
        print(f"    ✓ V_source negativo (correcto para Config A)")

    if not all_ok:
        print(f"\n  ✖ VERIFICACIONES FALLIDAS — abortando por seguridad.")
        return

    # ════════════════════════════════════════════════════════════════════
    #  PASO 4: CONFIRMACIÓN FINAL
    # ════════════════════════════════════════════════════════════════════

    print(f"\n" + "─" * 70)
    print(f"  CONFIRMACIÓN FINAL")
    print(f"─" * 70)

    print(f"""
  ╔═════════════════════════════════════════════════╗
  ║  Se va a aplicar al SiPM {DEVICE_ID}:       ║
  ║                                                 ║
  ║    V_source = {v_source:>+10.3f} V                      ║
  ║    V_ov     = {v_ov:>10.3f} V                       ║
  ║    I_limit  = {I_COMPLIANCE*1e6:>10.1f} µA                    ║
  ║                                                 ║
  ║  El voltaje se aplicará gradualmente            ║
  ║  ({V_RAMP_STEP:.0f} V/paso, {V_RAMP_DELAY:.1f} s/paso).                       ║
  ║                                                 ║
  ║  Ctrl+C en cualquier momento = apagado seguro   ║
  ╚═════════════════════════════════════════════════╝
""")

    try:
        resp = input("  Escribir 'SI' (mayúsculas) para aplicar el bias: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelado.")
        return

    if resp != "SI":
        print("  Cancelado por el usuario.")
        return

    # ════════════════════════════════════════════════════════════════════
    #  PASO 5: CONEXIÓN Y CONFIGURACIÓN DEL INSTRUMENTO
    # ════════════════════════════════════════════════════════════════════

    print(f"\n" + "─" * 70)
    print(f"  PASO 5: CONEXIÓN AL INSTRUMENTO")
    print(f"─" * 70)

    print("\n  [5.1] Buscando Keithley 2450...")
    rm = pyvisa.ResourceManager('@py')
    resource = find_keithley(rm)

    if resource is None:
        print("\n  ✖ No se encontró el Keithley 2450.")
        print("  Verificar:")
        print("    - Cable USB conectado")
        print("    - Instrumento encendido")
        print("    - Driver libusb-win32 instalado (Zadig)")
        rm.close()
        return

    print(f"\n  [5.2] Conectando a: {resource}")
    inst = rm.open_resource(resource)
    inst.timeout = 10000
    inst.write_termination = '\n'
    inst.read_termination = '\n'
    _inst_global = inst

    idn = inst.query("*IDN?").strip()
    print(f"  Instrumento: {idn}")

    # Verificar que es un 2450
    if "2450" not in idn:
        print(f"  ✖ El instrumento no parece ser un Keithley 2450.")
        print(f"     IDN: {idn}")
        inst.close()
        rm.close()
        return

    # ── Configurar ──
    print(f"\n  [5.3] Configurando instrumento...")
    setup_instrument(inst, I_COMPLIANCE, NPLC)

    # ── Verificar configuración por readback ──
    print(f"\n  [5.4] Verificando configuración (readback del instrumento):")
    config_ok = verify_instrument_config(inst, I_COMPLIANCE, NPLC)

    if not config_ok:
        print(f"\n  ✖ La configuración del instrumento no coincide.")
        print(f"     Abortando por seguridad.")
        inst.close()
        rm.close()
        _inst_global = None
        return

    print(f"\n  ✓ Instrumento configurado y verificado correctamente.")

    # ════════════════════════════════════════════════════════════════════
    #  PASO 6: APLICAR BIAS (RAMPA)
    # ════════════════════════════════════════════════════════════════════

    print(f"\n" + "─" * 70)
    print(f"  PASO 6: APLICANDO BIAS")
    print(f"─" * 70)

    # Encender salida (a 0 V)
    print(f"\n  Encendiendo salida a 0 V...")
    inst.write(":OUTP ON")
    time.sleep(0.5)

    # Verificar que la salida se encendió
    outp = inst.query(":OUTP?").strip()
    if outp == "1" or "ON" in outp.upper():
        print(f"  ✓ Salida ENCENDIDA (a 0 V)")
    else:
        print(f"  ✖ No se pudo encender la salida. Estado: {outp}")
        inst.close()
        rm.close()
        _inst_global = None
        return

    # Medir corriente a 0 V como referencia
    time.sleep(0.5)
    reading_0v = float(inst.query(":READ?").strip())
    print(f"  Corriente a 0 V: {abs(reading_0v)*1e9:.1f} nA "
          f"(debería ser ~0 nA)")

    if abs(reading_0v) > 1e-6:  # > 1 µA a 0 V es sospechoso
        print(f"  ⚠ Corriente anormalmente alta a 0 V ({abs(reading_0v)*1e6:.2f} µA)")
        print(f"     Posible cortocircuito o conexión incorrecta.")
        try:
            resp = input("  ¿Continuar de todas formas? (s/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = 'n'
        if resp != 's':
            safe_shutdown(inst, 0.0)
            inst.close()
            rm.close()
            _inst_global = None
            return

    # Rampa de voltaje
    print(f"\n  Rampa: 0 V → {v_source:+.3f} V "
          f"(pasos de {V_RAMP_STEP} V, delay {V_RAMP_DELAY} s)...")

    success, v_final = ramp_voltage(inst, 0.0, v_source, V_RAMP_STEP, V_RAMP_DELAY)

    if not success:
        print(f"\n  ✖ Rampa abortada por compliance.")
        print(f"     Posibles causas:")
        print(f"       - Conexión incorrecta (cortocircuito)")
        print(f"       - SiPM dañado")
        print(f"       - Polaridad invertida")
        safe_shutdown(inst, v_final)
        inst.close()
        rm.close()
        _inst_global = None
        return

    # ── Estabilización ──
    print(f"\n  Estabilizando ({SETTLING_TIME:.0f} s)...", end="", flush=True)
    time.sleep(SETTLING_TIME)
    print(" OK")

    # ── Lectura estabilizada ──
    reading_stable = float(inst.query(":READ?").strip())
    i_stable_nA = abs(reading_stable) * 1e9

    # Verificar voltaje seteado
    v_set_check = float(inst.query(":SOUR:VOLT?").strip())

    timestamp = datetime.now().strftime('%H:%M:%S')

    print(f"\n  ╔═══════════════════════════════════════════════╗")
    print(f"  ║         BIAS APLICADO EXITOSAMENTE            ║")
    print(f"  ╠═══════════════════════════════════════════════╣")
    print(f"  ║  Dispositivo:  {DEVICE_ID:>28s}  ║")
    print(f"  ║  V_source:     {v_source:>+25.3f} V  ║")
    print(f"  ║  V_setpoint:   {v_set_check:>+25.3f} V  ║")
    print(f"  ║  V_ov:         {v_ov:>25.3f} V  ║")
    print(f"  ║  |I_dark|:     {i_stable_nA:>23.1f} nA  ║")
    print(f"  ║  Compliance:   {I_COMPLIANCE*1e6:>22.1f} µA  ║")
    print(f"  ║  Hora:         {timestamp:>25s}  ║")
    print(f"  ╚═══════════════════════════════════════════════╝")

    # Verificar consistencia del voltaje seteado
    if abs(v_set_check - v_source) > 0.01:
        print(f"\n  ⚠ El voltaje seteado ({v_set_check:+.6f} V) no coincide "
              f"con el esperado ({v_source:+.6f} V)")

    # Comparar corriente con valor esperado (si V_ov ~ 2.5 V)
    if 2.0 <= v_ov <= 3.0:
        ratio = i_stable_nA / I_DARK_EXPECTED_nA
        if 0.3 < ratio < 3.0:
            print(f"\n  ✓ I_dark consistente con medición previa "
                  f"(esperado ~{I_DARK_EXPECTED_nA:.0f} nA, medido {i_stable_nA:.0f} nA)")
        else:
            print(f"\n  ⚠ I_dark ({i_stable_nA:.0f} nA) difiere significativamente "
                  f"del valor esperado (~{I_DARK_EXPECTED_nA:.0f} nA)")
            print(f"     Posibles causas: diferencia de temperatura, luz ambiente, "
                  f"dispositivo diferente.")

    # ════════════════════════════════════════════════════════════════════
    #  PASO 7: MONITOREO CONTINUO
    # ════════════════════════════════════════════════════════════════════

    print(f"\n" + "─" * 70)
    print(f"  PASO 7: MONITOREO DE CORRIENTE")
    print(f"  (Ctrl+C para apagar de forma segura y salir)")
    print(f"─" * 70)

    print(f"\n  {'Tiempo':>10s}  {'V_source [V]':>14s}  "
          f"{'|I_dark| [nA]':>14s}  {'Estado':>10s}")
    print(f"  {'─'*10}  {'─'*14}  {'─'*14}  {'─'*10}")

    try:
        t_start = time.time()
        n_compliance = 0

        while True:
            reading = inst.query(":READ?").strip()
            current = float(reading)
            abs_current = abs(current)
            elapsed = time.time() - t_start

            # Determinar estado
            if abs_current >= I_COMPLIANCE * 0.95:
                estado = "COMPLIANCE"
                n_compliance += 1
            elif abs_current > 5e-6:  # > 5 µA
                estado = "ALTO"
            elif abs_current > 1e-6:  # > 1 µA
                estado = "normal"
            else:
                estado = "OK"

            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            print(f"  {mins:4d}:{secs:02d}     "
                  f"{v_source:>+10.3f} V  "
                  f"{abs_current*1e9:>12.1f} nA  "
                  f"{estado:>10s}")

            # Advertencia si compliance sostenido
            if n_compliance >= 3:
                print(f"\n  ⚠ COMPLIANCE sostenido ({n_compliance} lecturas consecutivas).")
                print(f"     Verificar el dispositivo. Presionar Ctrl+C para apagar.")
                n_compliance = 0  # Reset para no spamear
            elif abs_current < I_COMPLIANCE * 0.95:
                n_compliance = 0  # Reset si corriente baja

            time.sleep(MONITOR_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n  *** Ctrl+C — Iniciando apagado seguro ***")

    # ════════════════════════════════════════════════════════════════════
    #  APAGADO
    # ════════════════════════════════════════════════════════════════════

    safe_shutdown(inst, v_source)

    inst.close()
    rm.close()
    _inst_global = None

    print(f"\n  Sesión finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


# =============================================================================
#  EJECUCIÓN
# =============================================================================

if __name__ == "__main__":
    main()
