#!/usr/bin/env python3
"""
=============================================================================
  COMPARACIÓN DE CURVAS I-V — SiPMs MICROFC-60035-SMT
=============================================================================
  Lee los CSV generados por iv_curve_sipm.py y superpone las curvas
  para visualizar la dispersión de V_br entre dispositivos.
  
  Genera 3 comparaciones:
    - Batch 1: dispositivos 01–05
    - Batch 2: dispositivos 06–10
    - Global:  dispositivos 01–10
  
  Uso: python comparar_iv_sipm.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import csv
import os
import glob

# =============================================================================
#  CONFIGURACIÓN (editar acá)
# =============================================================================

DATA_DIR    = "datos_iv"

# Grupos de comparación: (nombre, lista de SAMPLE_IDs, sufijo para archivos)
COMPARISON_GROUPS = [
    ("Batch 1 (01–05)",
     ["MFC60035_01", "MFC60035_02", "MFC60035_03", "MFC60035_04", "MFC60035_05"],
     "batch1"),
    ("Batch 2 (06–10)",
     ["MFC60035_06", "MFC60035_07", "MFC60035_08", "MFC60035_09", "MFC60035_10"],
     "batch2"),
    ("Global (01–10)",
     ["MFC60035_01", "MFC60035_02", "MFC60035_03", "MFC60035_04", "MFC60035_05",
      "MFC60035_06", "MFC60035_07", "MFC60035_08", "MFC60035_09", "MFC60035_10"],
     "global"),
]

# Estilo de cada curva: (color, marcador) — 10 estilos para cubrir todos
STYLES = [
    ("#1f77b4", "o"),    # azul, círculo
    ("#ff7f0e", "s"),    # naranja, cuadrado
    ("#2ca02c", "^"),    # verde, triángulo arriba
    ("#d62728", "D"),    # rojo, diamante
    ("#9467bd", "v"),    # violeta, triángulo abajo
    ("#8c564b", "P"),    # marrón, plus grueso
    ("#e377c2", "X"),    # rosa, X gruesa
    ("#7f7f7f", "h"),    # gris, hexágono
    ("#bcbd22", "d"),    # amarillo-verde, diamante fino
    ("#17becf", "*"),    # cyan, estrella
]

# Parámetros de extracción de V_br
SQRT_I_THRESHOLD = 1e-4  # Umbral mínimo de √I para incluir en ajuste [√A]

# Guardar gráficos
SAVE_PLOTS = True
OUTPUT_DIR = "datos_iv"


# =============================================================================
#  FUNCIONES
# =============================================================================

def find_csv_for_sample(data_dir, sample_id):
    """
    Busca el CSV más reciente para un SAMPLE_ID dado.
    Los archivos se llaman IV_{sample_id}_{timestamp}.csv
    """
    pattern = os.path.join(data_dir, f"IV_{sample_id}_*.csv")
    files = sorted(glob.glob(pattern))
    if len(files) == 0:
        return None
    return files[-1]  # El más reciente (por timestamp en el nombre)


def read_iv_csv(filepath):
    """
    Lee un CSV con metadata en comentarios (#) y datos tabulares.
    Retorna: voltages, currents, metadata (dict)
    """
    metadata = {}
    voltages = []
    currents = []
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header_found = False
        
        for row in reader:
            if len(row) == 0:
                continue
            
            # Líneas de metadata (empiezan con #)
            if row[0].startswith("# "):
                parts = row[0][2:].split(": ", 1)
                if len(parts) == 2:
                    metadata[parts[0].strip()] = parts[1].strip()
                continue
            
            # Header
            if row[0] == "Voltage_V":
                header_found = True
                continue
            
            # Datos
            if header_found:
                try:
                    voltages.append(float(row[0]))
                    currents.append(float(row[1]))
                except (ValueError, IndexError):
                    continue
    
    return np.array(voltages), np.array(currents), metadata


def extract_vbr(voltages, currents, sqrt_i_threshold=SQRT_I_THRESHOLD):
    """
    Extrae V_br mediante ajuste lineal de √I vs V (método onsemi).
    """
    mask_positive = currents > 0
    if not np.any(mask_positive):
        return None
    
    sqrt_i = np.sqrt(np.abs(currents))
    mask_above = (sqrt_i > sqrt_i_threshold) & mask_positive
    if np.sum(mask_above) < 5:
        return None
    
    v_fit = voltages[mask_above]
    sqrt_i_fit = sqrt_i[mask_above]
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(v_fit, sqrt_i_fit)
    if slope <= 0:
        return None
    
    vbr = -intercept / slope
    return {
        'vbr': vbr,
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value**2,
    }


# =============================================================================
#  MAIN
# =============================================================================

def run_comparison(group_name, sample_ids, suffix):
    """
    Ejecuta la comparación para un grupo de dispositivos.
    Genera 3 gráficos: I-V lineal, √I vs V, dispersión de V_br.
    
    Es la misma lógica que el main() original, parametrizada por grupo.
    """
    print(f"\n  --- {group_name} ---")

    # --- Cargar datos ---
    data = {}
    vbr_results = {}

    for sample_id in sample_ids:
        filepath = find_csv_for_sample(DATA_DIR, sample_id)
        if filepath is None:
            print(f"  ⚠ No se encontró CSV para {sample_id}")
            continue

        v, i, meta = read_iv_csv(filepath)
        data[sample_id] = (v, i, meta)

        vbr = extract_vbr(v, i)
        vbr_results[sample_id] = vbr

        vbr_str = f"{vbr['vbr']:.3f} V (R²={vbr['r_squared']:.5f})" if vbr else "N/A"
        print(f"  {sample_id}: {len(v)} pts | V_br = {vbr_str} | {os.path.basename(filepath)}")

    if len(data) == 0:
        print(f"\n  *** No se encontraron datos para {group_name}. ***")
        return

    # --- Resumen de dispersión ---
    vbr_values = [vbr_results[s]['vbr'] for s in vbr_results if vbr_results[s] is not None]

    if len(vbr_values) > 1:
        vbr_mean = np.mean(vbr_values)
        vbr_std = np.std(vbr_values, ddof=1)
        vbr_range = max(vbr_values) - min(vbr_values)

        print(f"\n  ┌───────────────────────────────────────────┐")
        print(f"  │  DISPERSIÓN DE V_br (N={len(vbr_values)})                    │")
        print(f"  │  Media:    {vbr_mean:.3f} V                         │")
        print(f"  │  Std:      {vbr_std*1e3:.1f} mV                          │")
        print(f"  │  Rango:    {vbr_range*1e3:.1f} mV                          │")
        print(f"  │  Min:      {min(vbr_values):.3f} V                         │")
        print(f"  │  Max:      {max(vbr_values):.3f} V                         │")
        print(f"  └───────────────────────────────────────────┘")

    # --- Gráfico 1: I-V lineal superpuestas ---
    fig1, ax1 = plt.subplots(1, 1, figsize=(10, 7))

    for idx, sample_id in enumerate(sample_ids):
        if sample_id not in data:
            continue
        v, i, meta = data[sample_id]
        color, marker = STYLES[idx % len(STYLES)]

        label = sample_id
        if vbr_results.get(sample_id) is not None:
            label += f" (V_br={vbr_results[sample_id]['vbr']:.3f} V)"

        ax1.plot(v, i * 1e6, color=color, marker=marker, markersize=3,
                 linewidth=0.8, markevery=5, label=label)

    ax1.set_xlabel("Voltaje [V]", fontsize=12)
    ax1.set_ylabel("Corriente [µA]", fontsize=12)
    ax1.set_title(f"Curvas I-V superpuestas — {group_name}", fontsize=13)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()

    # --- Gráfico 2: √I vs V (para comparar V_br) ---
    fig2, ax2 = plt.subplots(1, 1, figsize=(10, 7))

    for idx, sample_id in enumerate(sample_ids):
        if sample_id not in data:
            continue
        v, i, meta = data[sample_id]
        color, marker = STYLES[idx % len(STYLES)]

        mask = i > 0
        if not np.any(mask):
            continue

        sqrt_i = np.sqrt(np.abs(i[mask]))

        label = sample_id
        if vbr_results.get(sample_id) is not None:
            label += f" (V_br={vbr_results[sample_id]['vbr']:.3f} V)"

        ax2.plot(v[mask], sqrt_i, color=color, marker=marker, markersize=3,
                 linewidth=0.8, markevery=5, label=label)

        # Superponer recta de ajuste
        vbr = vbr_results.get(sample_id)
        if vbr is not None:
            v_line = np.linspace(vbr['vbr'] - 0.3, v[mask][-1], 50)
            sqrt_i_line = vbr['slope'] * v_line + vbr['intercept']
            sqrt_i_line = np.maximum(sqrt_i_line, 0)
            ax2.plot(v_line, sqrt_i_line, color=color, linestyle='--',
                     linewidth=1.2, alpha=0.7)
            # Marcar V_br
            ax2.axvline(x=vbr['vbr'], color=color, linestyle=':',
                        linewidth=0.8, alpha=0.5)

    ax2.set_xlabel("Voltaje [V]", fontsize=12)
    ax2.set_ylabel("$\\sqrt{|I|}$ [$\\sqrt{A}$]", fontsize=12)
    ax2.set_title(f"√I vs V — Extracción de V_br — {group_name}", fontsize=13)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()

    # --- Gráfico 3: V_br de cada dispositivo (strip chart) ---
    fig3 = None
    if len(vbr_values) > 1:
        fig3, ax3 = plt.subplots(1, 1, figsize=(8, 5))

        for idx, sample_id in enumerate(sample_ids):
            vbr = vbr_results.get(sample_id)
            if vbr is None:
                continue
            color, marker = STYLES[idx % len(STYLES)]
            ax3.plot(idx + 1, vbr['vbr'], color=color, marker=marker,
                     markersize=12, markeredgecolor='black', markeredgewidth=0.5)

        ax3.axhline(y=vbr_mean, color='black', linestyle='-', linewidth=1,
                     label=f"Media = {vbr_mean:.3f} V")
        ax3.axhspan(vbr_mean - vbr_std, vbr_mean + vbr_std,
                     alpha=0.15, color='gray', label=f"±1σ = ±{vbr_std*1e3:.1f} mV")

        ax3.set_xlabel("Dispositivo", fontsize=12)
        ax3.set_ylabel("V_br [V]", fontsize=12)
        ax3.set_title(f"Dispersión de V_br — {group_name}", fontsize=13)
        ax3.set_xticks(range(1, len(sample_ids) + 1))
        ax3.set_xticklabels([s.replace("MFC60035_", "#") for s in sample_ids])
        ax3.legend(fontsize=10)
        ax3.grid(True, axis='y', alpha=0.3)
        plt.tight_layout()

    # --- Guardar ---
    if SAVE_PLOTS:
        path1 = os.path.join(OUTPUT_DIR, f"comparacion_IV_lineal_{suffix}.png")
        fig1.savefig(path1, dpi=150, bbox_inches='tight')
        print(f"\n  Guardado: {path1}")

        path2 = os.path.join(OUTPUT_DIR, f"comparacion_sqrtI_Vbr_{suffix}.png")
        fig2.savefig(path2, dpi=150, bbox_inches='tight')
        print(f"  Guardado: {path2}")

        if fig3 is not None:
            path3 = os.path.join(OUTPUT_DIR, f"dispersion_Vbr_{suffix}.png")
            fig3.savefig(path3, dpi=150, bbox_inches='tight')
            print(f"  Guardado: {path3}")


def main():
    print("=" * 68)
    print("  COMPARACIÓN DE CURVAS I-V — SiPMs MICROFC-60035-SMT")
    print("=" * 68)

    for group_name, sample_ids, suffix in COMPARISON_GROUPS:
        run_comparison(group_name, sample_ids, suffix)

    print("\nCerrá las ventanas de los gráficos para terminar.")
    plt.show()
    print("Fin.")


if __name__ == "__main__":
    main()
