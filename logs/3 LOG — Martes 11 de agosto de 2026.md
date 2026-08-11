
## Objetivo del día

Evaluar el efecto de NPLC en la calidad de las mediciones I-V, caracterizar el segundo batch de 5 SiPMs (MFC60035_06 a _10), re-medir el primer batch para verificar si la diferencia de medias entre batches observada es térmica o de lote, y analizar la dispersión global de V_br sobre los 10 dispositivos.

---

## Contexto

- Setup validado el 2026-08-03 y protocolo de medición estabilizado el 2026-08-10 (ver LOGs anteriores).
- El 2026-08-10 se caracterizó el batch 1 (MFC60035_01 a _05), obteniendo V_br medio = 24.669 V con σ = 46.9 mV.
- Quedó pendiente evaluar NPLC > 1 para reducir ruido post-breakdown, medir el batch 2, y analizar dispersión global.
- Temperatura ambiente de hoy: **16.0 °C** (registrada en los CSV). 

---

## Trabajo realizado

### 1. Comparación de NPLC (1, 5, 10) en dispositivo #05

**Objetivo:** determinar si aumentar NPLC reduce el ruido punto a punto en la zona post-breakdown, y cuantificar el costo en tiempo.

**Dispositivo:** MFC60035_05 (elegido por tener el V_br más alto y corriente post-breakdown ligeramente mayor, lo que facilita la detección de variaciones).

**Configuración:** idéntica a la campaña (3 fases, compliance 100 µA, delay 50 ms), variando únicamente NPLC. Las 3 corridas se ejecutaron consecutivamente sin mover cables ni abrir la caja, usando el script `iv_nplc_comparison.py`.

**Resultados:**

| NPLC | Duración [s] | V_br [V] | Observación |
|---|---|---|---|
| 1 | 305 | 24.696 | Referencia |
| 5 | 802 | 24.717 | Sin mejora visible en ruido |
| 10 | 1379 | 24.751 | Sin mejora visible en ruido |

**Conclusiones del experimento NPLC:**

- **El ruido post-breakdown NO se reduce al aumentar NPLC.** Las tres curvas muestran fluctuaciones de amplitud comparable en la zona de 27–30 V. Esto sugiere que el ruido observado no es instrumental (interferencia de línea, ruido del ADC) sino físico: fluctuaciones estocásticas del dark count rate del SiPM, intrínsecas al dispositivo.
- **Decisión:** evaluar estadisticamente los resultados y la opcion de seguir aumentando el NPLC.
- **Se observó una deriva de V_br de +55 mV durante las 3 corridas consecutivas** (40 min total). 

### 2. Caracterización de SiPMs — Batch 2 (MFC60035_06 a _10)

**Configuración del barrido:** idéntica a la campaña del 10/08.

| Parámetro | Valor |
|---|---|
| Fase 1 (fino directa) | −0.3 → −0.3 V, paso 10 mV |
| Fase 2 (grueso) | 1 → 23 V, paso 1 V |
| Fase 3 (fino inversa) | 23.05 → 30 V, paso 10 mV |
| Compliance | 100 µA |
| NPLC | 1.0 |
| Delay por punto | 50 ms |
| Condición de luz | Oscuridad (cubierta opaca) |
| Temperatura | 16.0 °C |

**Resultados:**

> [!IMPORTANT] > Los archivos de estas mediciones se encuentran en: data/SiPM/raw/MFC60035/11-08-2026

| Dispositivo | V_br [V] |
|---|---|
| MFC60035_06 | 24.566 |
| MFC60035_07 | 24.581 |
| MFC60035_08 | 24.545 |
| MFC60035_09 | 24.529 |
| MFC60035_10 | 24.531 |

**Dispersión batch 2:**

| Métrica | Valor |
|---|---|
| Media | 24.550 V |
| σ | 22.5 mV |
| Rango | 52 mV |

### 3. Re-medición del batch 1 (MFC60035_01 a _05) a la misma temperatura

**Motivación:** la primera comparación global mostró una separación de ~120 mV entre las medias de los dos batches. Como fueron medidos en sesiones distintas (posiblemente a temperaturas diferentes), era necesario re-medir el batch 1 bajo las mismas condiciones ambientales del batch 2 para discriminar efecto térmico vs efecto de lote.

**Resultados batch 1 re-medido (hoy, 16 °C):**

> [!IMPORTANT] > Los archivos de estas mediciones se encuentran en: data/SiPM/raw/MFC60035/11-08-2026

| Dispositivo | V_br ayer [V] | V_br hoy [V] | Δ [mV] |
|---|---|---|---|
| MFC60035_01 | 24.646 | 24.687 | +41 |
| MFC60035_02 | 24.606 | 24.665 | +59 |
| MFC60035_03 | 24.665 | 24.686 | +21 |
| MFC60035_04 | 24.710 | 24.700 | −10 |
| MFC60035_05 | 24.719 | 24.719 | 0 |

**Dispersión batch 1 re-medido:**

| Métrica | Ayer | Hoy |
|---|---|---|
| Media | 24.669 V | 24.691 V |
| σ | 46.9 mV | 20.1 mV |
| Rango | 113 mV | 54 mV |

**Observaciones:**
- La media del batch 1 se corrió ligeramente (+22 mV) respecto a ayer. Los dispositivos #01, #02 y #03 se movieron más que #04 y #05, consistente con un efecto de orden de medición ayer (los primeros dispositivos se midieron con el setup menos estabilizado).
- La σ intra-batch bajó de 46.9 mV a 20.1 mV, comparable a la del batch 2 (22.5 mV). Esto indica que la dispersión real dispositivo a dispositivo es ~20 mV y que la medición de ayer tenía una componente de variabilidad extra (probablemente deriva térmica durante la sesión).

### 4. Comparación global — Resultados consolidados (mediciones de hoy)


> [!IMPORTANT] > Las figuras de la ultima comparación (11-08) se encuentran en: data/SiPM/graphs/MFC60035
> <small> No se incluyo la comparación con el batch1 del 10-08 porque es igual</small>

| Dispositivo | V_br [V] | Batch |
| ----------- | -------- | ----- |
| #01         | 24.687   | 1     |
| #02         | 24.665   | 1     |
| #03         | 24.686   | 1     |
| #04         | 24.700   | 1     |
| #05         | 24.719   | 1     |
| #06         | 24.566   | 2     |
| #07         | 24.581   | 2     |
| #08         | 24.545   | 2     |
| #09         | 24.529   | 2     |
| #10         | 24.531   | 2     |

| Estadístico | Batch 1 | Batch 2 | Global |
|---|---|---|---|
| Media [V] | 24.691 | 24.550 | 24.621 |
| σ [mV] | 20.1 | 22.5 | 77.0 |
| Rango [mV] | 54 | 52 | 190 |

**Conclusión principal:** la separación de ~141 mV entre las medias de los batches es **real y no térmica**. Ambos batches fueron medidos hoy a la misma temperatura (16 °C) y la separación persiste. Los dos invoices de Mouser provienen de lotes de fabricación (wafers) distintos, donde variaciones de proceso (dopaje, espesor de la zona de multiplicación) producen un corrimiento sistemático de V_br.

**Implicaciones para la matriz del Gamma Tracker:**

- **Intra-batch (mismo lote):** σ ~20 mV → variación de V_ov de ~0.8% a V_ov = 2.5 V. Excelente para polarización compartida sin compensación.
- **Inter-batch (lotes distintos):** Δ ~141 mV → variación de V_ov de ~5.6% a V_ov = 2.5 V. Requiere seleccionar dispositivos del mismo lote o implementar compensación individual de bias.
- **Rango total (N=10):** 190 mV → 7.6% de V_ov. Manejable para primera iteración, pero limita uniformidad de ganancia y PDE entre píxeles si se mezclan lotes.

---

## Scripts utilizados

| Script | Función | Estado |
|---|---|---|
| `iv_curve_sipm_complete.py` | Medición I-V de SiPM (3 fases, extracción de V_br) | Sin cambios |
| `iv_nplc_comparison.py` | Comparación NPLC: 3 corridas con NPLC 1, 5, 10 sobre mismo dispositivo | **Nuevo** |
| `comparar_iv_sipm.py` | Comparación de curvas I-V con 3 grupos (batch 1, batch 2, global) | **Modificado** |

**Cambios en `comparar_iv_sipm.py`:** se extendió para generar comparaciones por batch (01–05, 06–10) y global (01–10). La lógica de gráficos se extrajo a `run_comparison()` parametrizada por grupo. Se agregaron 5 estilos de marcador/color para cubrir los 10 dispositivos.

**Nuevo script `iv_nplc_comparison.py`:** wrapper sobre `iv_curve_sipm_complete.py` que ejecuta el barrido completo 3 veces con NPLC = [1, 5, 10], pide SAMPLE_ID una sola vez, mantiene la conexión abierta, y genera gráfico comparativo lineal al final. Cambios mínimos respecto al script de campaña (la función de barrido es idéntica, solo extraída a función para poder iterarla).

---

## Archivos generados

Todos en la carpeta `datos_iv/`:

**Comparación NPLC:**
- `IV_MFC60035_05_nplc_comp_NPLC1_*.csv/.png` — corrida NPLC = 1
- `IV_MFC60035_05_nplc_comp_NPLC5_*.csv/.png` — corrida NPLC = 5
- `IV_MFC60035_05_nplc_comp_NPLC10_*.csv/.png` — corrida NPLC = 10
- `comparacion_NPLC_MFC60035_05_nplc_comp_*.png` — gráfico comparativo

**SiPMs batch 2:**
- `IV_MFC60035_06_*.csv/.png` — #06
- `IV_MFC60035_07_*.csv/.png` — #07
- `IV_MFC60035_08_*.csv/.png` — #08
- `IV_MFC60035_09_*.csv/.png` — #09
- `IV_MFC60035_10_*.csv/.png` — #10

**SiPMs batch 1 re-medidos:**
- `IV_MFC60035_01_*.csv/.png` — #01 (segunda medición)
- `IV_MFC60035_02_*.csv/.png` — #02 (segunda medición)
- `IV_MFC60035_03_*.csv/.png` — #03 (segunda medición)
- `IV_MFC60035_04_*.csv/.png` — #04 (segunda medición)
- `IV_MFC60035_05_*.csv/.png` — #05 (segunda medición, además de la de NPLC)

**Comparaciones:**
- `comparacion_IV_lineal_batch1.png` — 5 curvas batch 1 superpuestas
- `comparacion_sqrtI_Vbr_batch1.png` — √I vs V batch 1
- `dispersion_Vbr_batch1.png` — strip chart V_br batch 1
- `comparacion_IV_lineal_batch2.png` — 5 curvas batch 2 superpuestas
- `comparacion_sqrtI_Vbr_batch2.png` — √I vs V batch 2
- `dispersion_Vbr_batch2.png` — strip chart V_br batch 2
- `comparacion_IV_lineal_global.png` — 10 curvas superpuestas
- `comparacion_sqrtI_Vbr_global.png` — √I vs V global
- `dispersion_Vbr_global.png` — strip chart V_br global

---

## Decisiones técnicas de la sesión

- **NPLC = 1 confirmado como óptimo para la campaña.** El ruido post-breakdown es intrínseco al SiPM (fluctuaciones de DCR), no instrumental. NPLC = 5 y 10 no lo reducen y multiplican el tiempo por 2.6× y 4.5× respectivamente.
- **Re-medición del batch 1 a misma temperatura que batch 2:** permitió confirmar que la diferencia de medias entre batches (~141 mV) es real (efecto de lote de fabricación) y no un artefacto térmico.
- **La dispersión intra-batch real es ~20 mV** (ambos batches consistentes a σ ≈ 20–22 mV cuando se miden en condiciones controladas). La σ de 46.9 mV del batch 1 medida ayer estaba inflada por variabilidad térmica? 

---

## Pendientes del LOG anterior — estado

- [x] Evaluar efecto de NPLC en la calidad de las mediciones → NPLC no reduce ruido post-breakdown; mantener NPLC = 1
- [x] Caracterizar el segundo batch de 5 SiPMs (MFC60035_06 a _10) → completado
- [x] Correr script de comparación con los 10 dispositivos → completado (batch 1, batch 2, global)
- [x] Evaluar dispersión global (N=10) vs intra-batch → σ_global = 77 mV, σ_intra ≈ 20 mV, dominada por offset inter-batch
- [ ] Revisar si el rango del ajuste de √I vs V necesita acotarse (excluir cola alta para mejorar R²) → pendiente
- [x] Documentar temperatura ambiente de cada sesión → 16.0 °C registrada en CSV
- [ ] Evaluar si es necesario medir a distintas temperaturas → pendiente; se tiene el dato natural de ayer (~14 °C) vs hoy (16 °C) que muestra sensibilidad, pero no se hizo un barrido controlado de temperatura

---

## Pendientes

- [ ] Revisar si el rango del ajuste de √I vs V necesita acotarse (excluir cola alta para mejorar R²)
- [ ] Evaluar medición a distintas temperaturas controladas (cuantificar dV_br/dT experimental y comparar con datasheet: 21.5 mV/°C)
- [ ] Verificar si la deriva de V_br observada en el experimento NPLC (+55 mV en 40 min) se estabiliza después de un warm-up más largo
- [ ] Definir criterio de selección de dispositivos para la matriz (¿mismo lote o compensación individual?)
- [ ] Evaluar corriente oscura a V_ov fijo (ej. V_br + 2.5 V) como indicador de DCR relativo entre dispositivos

---

*Log generado al finalizar la sesión del 11 de agosto de 2026.*