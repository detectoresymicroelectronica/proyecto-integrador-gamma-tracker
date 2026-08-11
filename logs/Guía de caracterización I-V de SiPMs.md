Campaña de dispersión de V_br

**Proyecto:** Upgrade Gamma Tracker — Evaluación de SiPMs candidatos para matriz multipixel  
**Fecha de preparación:** 4 de agosto de 2026  
**Última actualización:** 6 de agosto de 2026 — modelo confirmado por etiquetas de Mouser  
**Estado:** Modelo MICROFC-60035-SMT confirmado. Pendiente verificar si existe un segundo modelo.

---

## 1. Contexto y objetivo

El prototipo Gamma Tracker (TRL 4-5) utilizó SiPMs de área reducida. El nuevo proyecto integrador propone evaluar SiPMs de mayor área activa y menor tensión de polarización, con el objetivo de construir una matriz multipixel (ej. 4×4 píxeles) para mapeo espacial de actividad gamma en cirugía radioguiada.

Se dispone de **10 dispositivos SiPM del modelo onsemi MICROFC-60035-SMT** (C-Series, 6×6 mm, microcelda 35 µm), provenientes de **dos lotes de compra distintos** (5 unidades cada uno, adquiridos vía Mouser Electronics con órdenes STAN-2025 y STAN-2025-02).

> **Nota (2026-08-06):** ambas etiquetas de Mouser muestran el mismo MFG P/N (MICROFC-60035-SMT-TR). Se mencionó previamente que podrían ser dos modelos distintos y que se compraron 10 de cada uno. Pendiente confirmar en laboratorio si existen sobres adicionales con un segundo modelo. Si se confirma un segundo modelo, agregar su datasheet al proyecto y extender este protocolo con sus parámetros específicos.

El objetivo inmediato es **caracterizar las curvas I-V de los 10 dispositivos confirmados** para:

- Determinar el voltaje de ruptura (V_br) individual de cada uno.
- Cuantificar la **dispersión de V_br** dentro de cada lote y entre lotes.
- Evaluar la uniformidad del modelo para su uso en polarización compartida en la matriz multipixel.
- Si se confirma un segundo modelo, extender la comparación entre modelos.

### ¿Por qué importa la dispersión de V_br?

En una matriz multipixel, los SiPMs típicamente comparten una línea de polarización común. Si los dispositivos del mismo modelo tienen V_br muy distintos, al aplicar un mismo V_bias cada SiPM opera a un sobrevoltaje (V_ov = V_bias − V_br) diferente. Dado que la ganancia, la PDE, el dark count rate y el crosstalk dependen fuertemente de V_ov, esto produce una **respuesta no uniforme entre píxeles**, complicando la calibración y degradando el desempeño del sistema.

Un modelo con baja dispersión de V_br permite polarizar todos los píxeles con una fuente única y obtener respuesta uniforme, simplificando la electrónica y la calibración.

---

## 2. Conceptos clave: qué es un SiPM

### Estructura

Un SiPM (Silicon Photomultiplier) es un detector de luz de estado sólido compuesto por un arreglo de **cientos o miles de microceldas** conectadas en paralelo. Cada microcelda contiene:

- Un **fotodiodo de avalancha (APD)** operado en **modo Geiger** (polarizado por encima de V_br).
- Una **resistencia de quenching** en serie, que extingue la avalancha y permite la recarga.
- Una **salida rápida (fast output)** acoplada capacitivamente.

Todos los ánodos y cátodos están sumados, resultando en un dispositivo de tres terminales: ánodo, cátodo y fast output.

### Principio de operación

1. **Espera:** cada microcelda está polarizada a V_bias = V_br + V_ov. Campo eléctrico intenso, sin corriente (salvo corriente oscura).
2. **Detección:** un fotón genera un par electrón-hueco → avalancha auto-sostenida → pulso de corriente macroscópico. Respuesta digital: dispara o no dispara.
3. **Quenching:** la resistencia en serie limita la corriente, el voltaje cae por debajo de V_br, la avalancha se extingue. La microcelda se recarga con constante de tiempo τ (depende del tamaño de microcelda).
4. **Suma analógica:** la señal total del SiPM es la suma de las microceldas que dispararon. El dispositivo es "pseudo-analógico": cada microcelda es binaria, pero el conjunto da una respuesta proporcional al número de fotones (mientras N_fotones ≪ N_microceldas).

### Parámetros relevantes para la caracterización

| Parámetro | Qué es | Por qué importa |
|---|---|---|
| **V_br** (breakdown voltage) | Voltaje a partir del cual la avalancha se auto-sostiene | Define el punto de operación. Su dispersión entre dispositivos determina la viabilidad de polarización compartida. |
| **V_ov** (overvoltage) | V_bias − V_br | Controla ganancia, PDE, DCR, crosstalk. Todas las especificaciones dependen de V_ov. |
| **Ganancia** | Carga por avalancha / carga del electrón | Determina la amplitud de los pulsos. Aumenta con V_ov y con el tamaño de microcelda. |
| **PDE** | Probabilidad de detectar un fotón incidente | Combina eficiencia cuántica, probabilidad de avalancha y fill factor. Aumenta con V_ov. |
| **DCR** (dark count rate) | Tasa de avalanchas por generación térmica (sin luz) | Ruido fundamental. Aumenta con V_ov y con temperatura. |
| **Crosstalk** | Disparo de microceldas vecinas por fotones IR de la avalancha | Simula detección de fotones adicionales. Aumenta con tamaño de microcelda y V_ov. |
| **Afterpulsing** | Re-disparo por portadores atrapados | Contribuye a ruido correlacionado. Típicamente bajo en C-Series (~0.2%). |
| **dV_br/dT** | Dependencia de V_br con temperatura | ~21.5 mV/°C para C-Series. Crítico para reproducibilidad entre mediciones. |

### Especificaciones del MICROFC-60035-SMT (datasheet MICROC-SERIES/D, Rev. 9)

| Parámetro | Valor | Condición |
|---|---|---|
| Área activa | 6 × 6 mm² | — |
| Tamaño de microcelda | 35 µm | — |
| Número de microceldas | 18,980 | — |
| Fill factor | 64% | — |
| Paquete | 7 × 7 mm², SMT, 4-side tileable | — |
| V_br | 24.2 – 24.7 V (típico) | 21 °C |
| V_ov recomendado | 1.0 – 5.0 V | — |
| Ganancia | 3 × 10⁶ | V_ov = 2.5 V |
| PDE pico | 35% @ 420 nm | V_ov = 2.5 V |
| DCR | Escala con área (ver datasheet 1 mm: 30–96 kHz) | V_ov = 2.5 V, 21 °C |
| Crosstalk | 7% | V_ov = 2.5 V |
| Afterpulsing | 0.2% | V_ov = 2.5 V |
| Risetime (fast output) | 300 ps | — |
| τ (microcell recovery) | 82 ns | — |
| Capacitancia (fast terminal) | 48 pF | V_ov = 2.5 V |
| **Corriente máxima absoluta** | **20 mA** | **No exceder** |
| dV_br/dT | 21.5 mV/°C | — |
| dGain/dT | −0.8 %/°C | — |

**Pinout (paquete SMT):**

| Pin | Función |
|---|---|
| 1 | Ánodo |
| 2 | Fast Output |
| 3 | Cátodo |
| 4 | No Connect (soldar a PCB, puede ir a GND o floating) |
| 5 (paddle) | No Connect (NO soldar, dejar floating) |

> **Nota sobre la definición de V_br (datasheet, nota 3):** "The breakdown voltage (V_br) is defined as the value of the voltage intercept of a straight line fit to a plot of √I vs V, where I is the current and V is the bias voltage." Esto confirma el método de extracción que usaremos.

---

## 3. Método de extracción de V_br

El método estándar definido por onsemi para los C-Series (y aplicable a SiPMs en general) es:

1. Medir la curva I-V en inversa (corriente vs. voltaje de polarización).
2. Calcular **√I** para cada punto.
3. Graficar **√I vs. V**.
4. En la región post-breakdown, la relación es aproximadamente lineal.
5. Realizar un **ajuste lineal** en esa región.
6. **V_br = intersección de la recta con el eje V** (donde √I = 0).

Este método es más robusto y reproducible que identificar el "codo" visualmente, ya que produce un valor numérico definido y comparable entre dispositivos.

### Consideraciones prácticas

- La región para el ajuste lineal debe elegirse con cuidado: suficientemente por encima de V_br para que la relación sea lineal, pero sin ir tan alto que la corriente empiece a desviarse por efectos de alta inyección.
- Con el barrido fino (paso ≤ 0.1 V) se obtienen suficientes puntos en la zona de transición.
- Es recomendable implementar la extracción de V_br en el script de análisis (Python), para que sea automática y reproducible.

---

## 4. Protocolo de medición

### 4.1. Setup (ya validado — ver LOG 2026-08-03)

| Componente | Detalle |
|---|---|
| Instrumento | Keithley 2450 SMU, FW 1.6.1a |
| Conexión | USB (libusb-win32 via Zadig) |
| Python | 3.11.5 (Anaconda base) |
| Script | `iv_curve_sipm.py` |
| Sensing | 2-wire (justificado: impedancias altas, corrientes bajas) |
| Terminales | Frontales (banana) |
| Backend VISA | pyvisa-py |

### 4.2. Condiciones de medición

**Oscuridad:** cubrir el SiPM durante toda la medición para eliminar fotocorriente. Un capuchón opaco o caja cerrada es suficiente. No mover la cubierta entre mediciones del mismo dispositivo.

**Temperatura:** registrar temperatura ambiente al inicio y al final de cada medición. Anotar en el CSV o en un log separado. Si la temperatura varía más de ~2 °C durante la campaña, corregir V_br a temperatura de referencia (ej. 21 °C) usando el coeficiente dV_br/dT del datasheet.

**Estabilización:** antes de cada barrido, dejar el dispositivo conectado y con la salida apagada durante ~30 s para que se termalice en la condición de montaje.

### 4.3. Nomenclatura de muestras

Formato definido:

```
MFC60035_{Lote}_{Número}
```

Donde Lote identifica el sobre de Mouser de origen:

```
Lote L1: Invoice 0871... (Cust PO: STAN-2025, Line Item 002)
  → MFC60035_L1_01, MFC60035_L1_02, ..., MFC60035_L1_05

Lote L2: Invoice 0872... (Cust PO: STAN-2025-02, Line Item 001)
  → MFC60035_L2_01, MFC60035_L2_02, ..., MFC60035_L2_05
```

**Importante:**
- Marcar físicamente cada dispositivo antes de sacarlo del sobre (etiqueta, posición en bandeja numerada).
- Fotografiar cada sobre abierto con los dispositivos numerados para trazabilidad.
- Si se confirma un segundo modelo, agregar una serie adicional con prefijo apropiado (ej. `MFC30035_...` o el que corresponda).

### 4.4. Secuencia sugerida de medición

Valores concretos para el MICROFC-60035-SMT (V_br típico: 24.2–24.7 V, I_max: 20 mA):

```
Fase 1 — Exploratoria (MFC60035_L1_01)
  ├── Objetivo: verificar que el setup mide correctamente el SiPM, ubicar V_br real
  ├── Barrido: 0 V → 32 V, paso 0.5 V
  ├── Compliance: 10 µA (conservador)
  ├── NPLC: 1.0
  └── Resultado esperado: corriente plana ~nA hasta ~24 V, luego crecimiento abrupto
      hasta alcanzar compliance. Permite ubicar V_br aproximado.

Fase 2 — Fina (todos los dispositivos, los 10)
  ├── Barrido grueso: 0 V → 21 V, paso 1 V
  │   (documenta corriente oscura pre-breakdown, debe ser ~nA)
  ├── Barrido fino: 21 V → 30 V, paso 0.05 V
  │   (zona de interés: 180 puntos, cubre desde ~3 V antes de V_br hasta ~5 V después)
  ├── Compliance: 100 µA
  │   (muy por debajo del máximo de 20 mA; suficiente para resolver la zona post-breakdown)
  ├── NPLC: 1.0 (si hay mucho ruido en la zona pre-breakdown, subir a 5)
  └── Tiempo estimado: ~3-4 min por dispositivo (dependiendo de delays del script)

Fase 3 — Verificación de reproducibilidad
  ├── Repetir medición de MFC60035_L1_01 y MFC60035_L2_05
  └── Comparar V_br extraído: diferencia < 20 mV indica buena reproducibilidad del setup
```

> **Justificación del rango 21–30 V:** con V_br típico entre 24.2 y 24.7 V, arrancar en 21 V da ~3 V de margen pre-breakdown para documentar la corriente oscura de base. Terminar en 30 V da ~5 V de V_ov, que es el máximo recomendado por el datasheet. No hay necesidad de ir más arriba.

> **Justificación del compliance de 100 µA:** a V_ov = 5 V la corriente oscura de un SiPM de 6 mm con DCR del orden de cientos de kHz produce corrientes en el rango de µA a decenas de µA. Un compliance de 100 µA es suficiente para capturar la zona de interés sin riesgo. Si durante la exploratoria se observa que la corriente crece más rápido de lo esperado, ajustar. En ningún caso superar 1 mA sin justificación, y nunca acercarse a los 20 mA del máximo absoluto.

### 4.5. Orden de medición

1. **MFC60035_L1_01** — exploratoria + fina (primer dispositivo, calibra expectativas)
2. MFC60035_L1_02 a MFC60035_L1_05 — fina
3. MFC60035_L2_01 a MFC60035_L2_05 — fina
4. **Repetir MFC60035_L1_01 y MFC60035_L2_05** — verificación de reproducibilidad

Total: 12 mediciones. Medir todos en la misma sesión o en sesiones lo más cercanas posible para minimizar variaciones ambientales. Registrar temperatura al inicio, a la mitad (entre lotes) y al final.

---

## 5. Análisis post-medición

### 5.1. Para cada dispositivo

1. Graficar I vs. V (escala lineal y logarítmica).
2. Graficar √I vs. V.
3. Ajustar recta en la región post-breakdown.
4. Extraer V_br (intersección con eje V).
5. Registrar corriente oscura a un V_ov fijo (ej. V_br + 2.5 V).

### 5.2. Análisis de dispersión

**Intra-lote (N=5 cada uno):**

| Métrica | Cálculo | Calcular para |
|---|---|---|
| V_br promedio | mean(V_br) | Lote L1, Lote L2 |
| Desviación estándar | std(V_br) — usar N-1 (muestra) | Lote L1, Lote L2 |
| Rango | max(V_br) − min(V_br) | Lote L1, Lote L2 |

**Inter-lote:**

| Métrica | Cálculo |
|---|---|
| Diferencia de medias | mean(V_br_L1) − mean(V_br_L2) |
| Dispersión global (N=10) | std de los 10 V_br combinados |
| Rango global | max − min de los 10 dispositivos |

### 5.3. Visualización sugerida

- Strip chart o box plot de V_br de los 10 dispositivos, codificado por color según lote (L1 vs. L2).
- Superponer todas las curvas √I vs. V en un mismo gráfico para ver visualmente la dispersión.
- Si se confirma un segundo modelo, agregar una serie adicional al gráfico.
- Comparar con datos previos del Gamma Tracker (SiPM Hamamatsu S13360-1350CS) si están disponibles.

### 5.4. Nota estadística

Con N=5 por lote (o N=10 global), la estimación de la desviación estándar tiene incertidumbre considerable. Diferencias claras (ej. σ ~ 50 mV vs. σ ~ 200 mV) son interpretables con confianza. Diferencias pequeñas entre lotes no son estadísticamente distinguibles con este tamaño de muestra. Para la decisión de ingeniería (¿sirve para polarización compartida?), lo que importa es el rango global de los 10 dispositivos: si el max − min es menor que ~100 mV, la variación de V_ov entre píxeles es aceptable para la mayoría de las aplicaciones.


---

## 7. Checklist pre-medición

**Ya resuelto (modelo MICROFC-60035-SMT):**
- [x] Modelo confirmado por etiquetas de Mouser: MICROFC-60035-SMT-TR
- [x] Datasheet disponible en proyecto: DataSheet_MICROCSERIESD.PDF
- [x] V_br esperado: 24.2–24.7 V → rango de barrido fino: 21–30 V
- [x] Compliance definido: 100 µA (máximo absoluto del dispositivo: 20 mA)
- [x] Nomenclatura definida: MFC60035_L1_01..05, MFC60035_L2_01..05

**Pendiente en laboratorio:**
- [x] **Verificar si existe un segundo modelo** (revisar si hay otros sobres, consultar con el director)
- [x] Marcar/numerar físicamente cada dispositivo (01 a 05 por lote, separar por sobre de origen)
- [x] Fotografiar sobres abiertos con dispositivos numerados
- [x] Actualizar SAMPLE_ID en el script `iv_curve_sipm.py` con nomenclatura MFC60035_Lx_0x
- [x] Verificar que el setup sigue funcionando (repetir medición de resistencia si hubo cambios)
- [x] Preparar cubierta opaca para medición en oscuridad
- [x] Tener termómetro accesible para registrar temperatura
- [x] Verificar espacio en disco para ~12 archivos CSV + PNG (10 mediciones + 2 repeticiones)

---

## 8. Archivos relacionados

| Archivo | Contenido |
|---|---|
| `LOG_2026-08-03_IV_curves_setup.md` | Setup del sistema, bug corregido, validación con resistencia |
| `DataSheet_MICROCSERIESD.PDF` | Datasheet C-Series onsemi (referencia comparativa) |
| `2450_Datasheet_1KW609043_20260618.pdf` | Datasheet Keithley 2450 SMU |
| `Propuesta_PI__Lipovetzky.pdf` | Propuesta de proyecto integrador (objetivos, cronograma) |
| `Gamma_Tracker_...compressed.pdf` | Tesis previa (Torletti) — antecedente directo |
| `iv_curve_sipm.py` | Script de medición (en laboratorio) |

---

*Documento generado como preparación para la campaña de caracterización.*  
*Actualización 2026-08-06: modelo MICROFC-60035-SMT confirmado. Parámetros de barrido definidos. Pendiente confirmar existencia de segundo modelo.*
