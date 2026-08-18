# LOG — Lunes 18 de agosto de 2026

## Objetivo del día

Familiarizarse con KiCad y diseñar una placa breakout para el SiPM MICROFC-60035-SMT que permita conectar el SMU (bias) y un amplificador RF (fast output) para la etapa de readout de pulsos.

---

## Contexto

- Caracterización I-V de los SiPMs en curso (10 dispositivos medidos, ver LOGs anteriores).
- El director propuso como siguiente paso diseñar una PCB para soldar el SiPM y facilitar las conexiones al instrumental.
- La placa debe sacar tres señales: cátodo, ánodo y fast output.
- El amplificador RF para la fast output todavía no está definido (modelo pendiente).
- Se decidió usar esta placa como ejercicio para aprender KiCad desde cero.

---

## Trabajo realizado

### 1. Instalación y familiarización con KiCad 10.0

Se instaló KiCad 10.0 en Windows. Se identificaron las herramientas principales del flujo de diseño de PCB:

| Herramienta | Función |
|---|---|
| **Schematic Editor** | Dibujar el circuito eléctrico (símbolos, conexiones lógicas) |
| **Symbol Editor** | Crear o modificar símbolos esquemáticos de componentes |
| **PCB Editor** | Diseñar el layout físico de la placa (footprints, pistas, zonas de cobre) |
| **Footprint Editor** | Crear o modificar footprints (huellas físicas de los pads de soldadura) |
| **Gerber Viewer** | Previsualizar archivos de fabricación |

**Concepto clave aprendido:** un componente en KiCad tiene dos representaciones — el **símbolo** (representación lógica/eléctrica para el esquemático) y el **footprint** (representación física de los pads en el PCB). KiCad los vincula por número de pin.

### 2. Obtención del símbolo y footprint del MICROFC-60035-SMT

El SiPM no está en las librerías estándar de KiCad. Se descargó el símbolo esquemático (`.kicad_sym`) y el footprint (`.kicad_mod`) desde **SnapEDA** (https://www.snapeda.com/parts/MICROFC-60035-SMT-TR1/Onsemi/view-part/).

**Importación de librerías:**

- Símbolo: Schematic Editor → Preferences → Manage Symbol Libraries → Project Libraries → agregar el `.kicad_sym`.
- Footprint: ventana principal de KiCad → Preferences → Manage Footprint Libraries → Project Libraries → crear una carpeta `.pretty` conteniendo el `.kicad_mod` y agregarla.

**Nota:** las librerías de símbolos se gestionan desde el Schematic Editor; las de footprints desde la ventana principal de KiCad o el PCB Editor. No están disponibles desde el otro editor.

**Observación sobre el símbolo de SnapEDA:** el símbolo no incluye el pin 4 (No Connect). El footprint sí tiene el pad 4 físico. Esto genera un warning al importar al PCB ("No net found for component U1 pad 4") que es esperable y no es un error.

### 3. Diseño del esquemático

Se creó el proyecto `SiPM_breakout` con template default. El esquemático incluye:

| Componente | Referencia | Función |
|---|---|---|
| MICROFC-60035-SMT-TR1 | U1 | SiPM |
| Conn_01x01 | J1 | Conector ANODE_BIAS (−Vbias del SMU) |
| Conn_01x01 | J2 | Conector FAST_OUT (salida al amplificador RF) |
| Conn_01x01 | J3 | Conector CATHODE_GND (0V, referencia) |

**Conexiones eléctricas:**

- Pin 3 (Cathode) → J3 (CATHODE_GND)
- Pin 1 (Anode) → J1 (ANODE_BIAS)
- Pin 2 (Fast Output) → J2 (FAST_OUT)
- Pin 5 (EP/Paddle) → No Connect flag (X)

**ERC (Electrical Rules Check):** 0 errores, 0 warnings (después de importar la librería de footprints).

### 4. Asignación de footprints y diseño del PCB

**Footprints asignados:**

| Componente | Footprint |
|---|---|
| U1 (SiPM) | XDCR_MICROFC-60035-SMT-TR1 (de SnapEDA) |
| J1, J2, J3 | PinHeader_1x01_P2.54mm_Vertical (librería estándar KiCad) |

**Layout del PCB:**

- Dimensiones de la placa: **20 mm × 15 mm** (definido en Edge.Cuts).
- Capa única: **F.Cu** (cara superior).
- SiPM centrado a la izquierda, tres pin headers alineados a la derecha.
- Ancho de pistas: **1.0 mm** (por recomendación del director, para fabricación robusta en CNC/artesanal).
- Pistas explícitas para ánodo y fast output; conexión del cátodo a través del plano de masa.

### 5. Plano de masa — Análisis y decisión de configuración

Se discutió extensamente la implementación del plano de masa y su conexión eléctrica. El análisis incluyó la revisión del datasheet del MICROFC-60035-SMT y del application note **AND9782/D** (Biasing and Readout of onsemi SiPM Sensors).

**Configuraciones de bias para C-Series (P-on-N) según AND9782/D:**

| Config | Cátodo | Ánodo | Fast Output | Requiere cap | Timing óptimo |
|---|---|---|---|---|---|
| **A** | **0V (GND)** | **−Vbias** | Referenciado a 0V | No | Sí |
| B | +Vbias | 0V (GND) | Referenciado a 0V | Sí (10 nF) | Sí (con cap) |
| C | 0V | +Vbias | Referenciado a 0V | No | Menos óptimo |
| D | −Vbias | 0V | Referenciado a 0V | Sí (10 nF) | Menos óptimo |

**Decisión: se eligió la Configuración A.**

Justificación:
- Óptimo timing de fast output sin necesidad de capacitor de desacople adicional.
- El cátodo (substrato del chip en estructura P-on-N) está a 0V, proporcionando el camino de retorno de alta frecuencia natural para la fast output.
- El Keithley 2450 puede operar en los 4 cuadrantes, por lo que puede sourcing de tensión negativa sin problemas.

**Consecuencia:** el plano de masa del PCB se conectó a la net del **cátodo** (Net-(J3-Pin_1)).

**Pad 4:** conectado al plano de masa (net del cátodo), según la recomendación del datasheet. Esto proporciona también un camino térmico desde el encapsulado al plano de cobre.

### 6. Verificación del footprint — Plano mecánico del datasheet

Se revisó el plano "Recommended PCB Solder Footprint" del datasheet (CWDFN4 7×7, 4.5P, CASE 512AG). Las notas confirman:

- Pin 4: soldarse al PCB, opcionalmente conectar a ground.
- Pin 5 (paddle): **no soldar** para optimizar la soldadura de pines 1–4. Si se suelda (por disipación térmica), conectar a ground.
- No debe haber contactos eléctricos (vías) debajo del paddle.

**Pendiente:** verificar que el footprint de SnapEDA coincida con las dimensiones del plano oficial.

### 7. Exportación de archivos de fabricación (Gerbers)

Se exportaron los archivos Gerber desde **File → Plot** en el PCB Editor.

**Configuración de exportación:**

- Plot format: **Gerber**
- Capas seleccionadas en "Include Layers" (panel izquierdo): **F.Cu** y **Edge.Cuts**
- **"Plot on All Layers"** (panel central): ninguna capa seleccionada — si se seleccionan capas aquí, se agregan a todas las capas ploteadas, lo cual puede contaminar los archivos (por ejemplo, incluyendo el plano de masa en Edge.Cuts).
- Coordinate format: 4,6 mm
- Extended X2 format habilitado

**Error detectado y resuelto:** inicialmente se habían seleccionado capas en "Plot on All Layers", lo que causaba que el plano de masa apareciera en el archivo de Edge.Cuts. Al deseleccionar todo en ese panel, los archivos se generaron correctamente.

Los archivos Gerber fueron enviados al taller para fabricación por fresado CNC.

**DRC final:** 0 errores, 0 unconnected items.

---

## Decisiones técnicas y justificación

- **Configuración A (cátodo = GND):** basada en el application note AND9782/D de onsemi. Para SiPMs C-Series (P-on-N), esta configuración da el mejor timing de fast output sin componentes adicionales, porque el substrato del chip ya está a 0V.
- **Plano de masa en F.Cu:** reduce el tiempo de fresado CNC (la fresa solo corta los surcos de aislación), provee un retorno de baja impedancia para las señales rápidas de la fast output, y es la práctica recomendada por onsemi en las layout guidelines del AND9782/D.
- **Pistas de 1.0 mm:** ancho robusto para fabricación artesanal/CNC. Las corrientes son de µA, por lo que no hay limitación eléctrica.
- **Pin headers genéricos:** elección temporal para prototipado. En revisiones futuras se pueden cambiar a SMA (especialmente para fast output, por impedancia controlada de 50 Ω).

---

## Impacto en el setup de medición (cambios por Configuración A)

La elección de Configuración A **cambia la convención de polaridad** respecto a las mediciones I-V realizadas el 03/08 y 10/08.

### Diagrama de conexión (Configuración A)

```
  Keithley 2450                Plaqueta breakout
  ┌──────────┐                ┌─────────────────────┐
  │          │                │                     │
  │  HI (+) ─┼── cable ──────┼─ J1 (ANODE_BIAS)    │
  │          │                │       ↓             │
  │          │                │   Pin 1 (Anode)     │
  │          │                │       ↕  SiPM U1    │
  │          │                │   Pin 3 (Cathode)   │
  │          │                │       ↓             │
  │  LO (−) ─┼── cable ──────┼─ J3 (CATHODE_GND)   │
  │          │                │                     │
  └──────────┘                │   Pin 2 (Fast Out)  │
                              │       ↓             │
  Amplificador RF             │                     │
  ┌──────────┐                │                     │
  │  IN     ─┼── cable ──────┼─ J2 (FAST_OUT)      │
  │  GND    ─┼── cable ──────┼─ J3 (CATHODE_GND)   │
  └──────────┘                │                     │
                              │   Plano de masa:    │
                              │   conectado a J3    │
                              │   (net del cátodo)  │
                              │                     │
                              │   Pin 4 (NC) → GND  │
                              │   Pin 5 (EP) → N/C  │
                              └─────────────────────┘
```

### Tabla de cambios

| Aspecto | Antes (Config B implícita) | Ahora (Config A) |
|---|---|---|
| SMU HI (+) | Cátodo | **Ánodo → J1 (ANODE_BIAS)** |
| SMU LO (−) | Ánodo | **Cátodo → J3 (CATHODE_GND)** |
| Voltaje de bias | Positivo (+24–28 V) | **Negativo (−24 a −28 V)** |
| Plano de masa PCB | Net del ánodo | **Net del cátodo (J3)** |
| Convención I-V | V > 0 → inversa (operación) | **V < 0 → inversa (operación)** |
| V_br reportado | Positivo directo | **|V| (siempre positivo)** |
| Fast output | — | **J2 (FAST_OUT) → amplificador RF** |
| GND amplificador | — | **Compartida con J3 (CATHODE_GND)** |

### Mapeo rápido de pines de la plaqueta

| Pin plaqueta | Nombre | Pin SiPM | Conexión externa |
|---|---|---|---|
| **J1** | ANODE_BIAS | Pin 1 (Anode) | SMU HI (+), sourcing −Vbias |
| **J2** | FAST_OUT | Pin 2 (Fast Output) | Entrada amplificador RF |
| **J3** | CATHODE_GND | Pin 3 (Cathode) | SMU LO (−), GND amplificador RF |

### Acciones realizadas
- [x] Modificar `iv_curve_sipm_complete.py` → versión 3.0 (`iv_curve_sipm_complete_v3.py`)
  - Voltajes de barrido negativos para inversa
  - `extract_vbr` trabaja con |V| y |I|
  - Gráficos muestran |V| vs |I| para lectura directa
  - Metadata incluye configuración de bias y conexión a plaqueta
  - CSV incluye columnas con signo y absolutas
- [ ] Verificar que los gráficos y el ajuste de V_br funcionen con la nueva convención de signo (requiere medición real)
- [ ] Documentar la nueva convención en la guía de caracterización

---

## Pendientes del LOG anterior — estado

- [ ] Evaluar efecto de NPLC en la calidad de las mediciones → pendiente
- [ ] Caracterizar el segundo batch de 5 SiPMs (MFC60035_06 a _10) → pendiente
- [ ] Correr script de comparación con los 10 dispositivos → pendiente
- [ ] Evaluar dispersión global (N=10) vs intra-batch → pendiente
- [ ] Revisar si el rango del ajuste de √I vs V necesita acotarse → pendiente
- [ ] Documentar temperatura ambiente de cada sesión → pendiente

---

## Pendientes para próximas sesiones

- [ ] Recibir la placa fabricada y soldar el SiPM
- [ ] Verificar dimensiones del footprint de SnapEDA contra el plano mecánico oficial (CWDFN4 7×7, CASE 512AG)
- [ ] Crear el footprint a mano (opción B del plan original) como ejercicio de aprendizaje y verificación
- [ ] Definir el modelo del amplificador RF para la fast output (el app note AND9782/D sugiere Mini-Circuits ZX60-43S+ o ZFL-1000LN+, 50 Ω, 1 GHz, 20 dB)
- [ ] Adaptar los scripts de medición I-V a la nueva convención de polaridad (Config A)
- [ ] Evaluar si la placa necesita una revisión futura con conector SMA para la fast output (impedancia controlada 50 Ω)
- [ ] Planificar la medición de deriva térmica a tensión constante (bonus del director)

---

## Referencias consultadas

- **AND9782/D** — Biasing and Readout of ON Semiconductor SiPM Sensors (Rev. 3, April 2019). Fuente principal para la elección de configuración de bias.
- **DataSheet MICROC-SERIES/D** — C-Series SiPM Sensors datasheet. Pinout, recommended PCB solder footprint, evaluation boards.
- **Gamma Tracker (tesis Torletti Daniluk)** — Referencia de diseño PCB previo con KiCad para SiPM + amplificador BGA614.

---

*Log generado al finalizar la sesión del 18 de agosto de 2026.*
