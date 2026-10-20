
## Sesión de diseño de PCB: EVB-TIA v0 en KiCad (esquemático, footprints, floorplan, ruteo y plano de masa)

**Tipo:** diseño de PCB (KiCad 10.0.5, Windows 10). Sin trabajo experimental.
**Duración:** 10/10 por la tarde → 11/10 de madrugada.
**Estado al cierre:** esquemático cerrado (ERC 0/0). Placa ubicada, ruteada y con plano de masa. **DRC: 0 errores, 0 ítems sin conectar, 52 advertencias de serigrafía.** Antes de seguir con la serigrafía, la placa se revisa con José (director) y Lara.

---

## Objetivo

Pasar a KiCad el circuito definido en el LOG 9 (TIA de una etapa con ADA4895, Configuración C de la AND9782/D, banco de R_F con jumpers) y llegar a una placa lista para fabricar y ensamblar en JLCPCB.

---

## Resumen

- **Criterio general:** usar la placa de Lara (`placa_detector_v3`, ya fabricada y probada) como guía, y cambiar algo solo cuando el diseño lo exige. Excepción aceptada: la placa la ensambla JLCPCB a máquina, así que los footprints no tienen que ser los de soldadura a mano que usó Lara. Se busca una placa lo más limpia posible, sin componentes opcionales sin uso.
- **Esquemático:** 7 bloques funcionales, 31 componentes, ERC 0 errores / 0 advertencias.
- **Layout:** el primer floorplan (56 × 45 mm, 4 agujeros M3) desperdiciaba espacio. Se rehízo siguiendo la forma en que Lara aprovecha el espacio: **33,5 × 34,5 mm, sin agujeros**, densidad de courtyard 0,32 (Lara: 0,34).
- **Métricas críticas, iguales en las dos versiones:** pad 3 del SiPM → −IN = 8,2 mm; lazo de C_F = 19 mm (~28 mm²).
- **Ruteo:** completo, con el cruce de +5V por la capa inferior (debajo de TIA_OUT, nunca debajo de TIA_IN).
- **Plano de masa:** zona GND en F.Cu y B.Cu, dos áreas sin cobre (alrededor de TIA_IN y de U2) y vías de GND en el SiPM, U2 y los desacoples.
- **Hallazgo importante:** el footprint del SiPM heredado de Lara tiene los pads configurados para **no conectarse a zonas**. El pad 1 (GND, ánodo) quedaba sin tocar el plano. Se corrigió en el pad 1 (*Solid*).

---

## 1. Criterios de diseño acordados

| Criterio | Decisión | Motivo |
|---|---|---|
| Referencia | Seguir la placa de Lara salvo cambios necesarios por diseño | Ya fue fabricada y funciona; reduce errores por inexperiencia en KiCad |
| Ensamblado | JLCPCB monta todo, con el SiPM soldado en la placa | Repetibilidad; evita soldar a mano el SiPM y el SOT-23-6 |
| Footprints | Estándar de máquina, no los *HandSolder* de Lara (excepto C_F) | Lara soldaba a mano; acá no hace falta |
| Componentes opcionales | Ninguno, salvo C_F | Criterio propio: placa lo más limpia posible |
| SMA | Se suelda en el laboratorio (mismo modelo que Lara) | Por eso J3 se excluye del BOM y del archivo de posiciones |

---

## 2. Bibliotecas

### 2.1 SiPM (MICROFC-60035-SMT-TR1)

- **Símbolo:** se exportó del esquemático de Lara (`EVB-TIA.kicad_sym`) y se usa **sin cambios**: pines 1, 2, 3 y EP 5, sin pin 4. Se había propuesto agregar el pin 4 y cambiar el tipo del pin 5; se descartó porque el símbolo es el de onsemi.
- **Footprint:** `XDCR_MICROFC-60035-SMT-TR1.kicad_mod`, exportado del PCB de Lara a `EVB-TIA.pretty`. Se borraron los 5 polígonos de F.Paste sobre el pad 5 (el pad 5 queda solo en F.Cu). Los pads 1 a 4 tienen F.Cu, F.Mask y F.Paste.
- Ambas bibliotecas se registraron en la tabla del proyecto con `${KIPRJMOD}`.

### 2.2 ADA4895-1 (SOT-23-6)

No hay símbolo descargable: SnapEDA no lo tiene. Se creó `ADA4895.kicad_sym` con el pinout del datasheet:

| Pin | Función | Tipo |
|---|---|---|
| 1 | OUT | output |
| 2 | V− | power_in |
| 3 | +IN | input |
| 4 | −IN | input |
| 5 | DIS | input |
| 6 | V+ | power_in |

Footprint `Package_TO_SOT_SMD:SOT-23-6`, campo LCSC = **C654293**. El pinout físico se verificó con el footprint: pads 1-2-3 de un lado y 6-5-4 del otro, en sentido antihorario.

![Símbolo ADA4895 en el Symbol Editor](../docs/images/logs/simbolo_ADA4895_10-10-26.png)

---

## 3. Esquemático

### 3.1 Bloques

Se organizó en bloques con la misma filosofía que el esquemático de Lara: un recuadro por función, con títulos en inglés.

| Bloque | Componentes | Función |
|---|---|---|
| BIAS FILTER | J1, R1 = R2 = 50 Ω, C1 = 10 nF, C2 = 100 nF | Filtro RC de dos etapas para la tensión de bias del SiPM (AND9782, Fig. 10) |
| 5V POWER INPUT | J2 + PWR_FLAG | Entrada de +5 V |
| SENSOR & COUPLING | U1 (SiPM), C3 = 10 nF, R3 = 10 Ω, C4 = 1 µF | Configuración C: bias → R3 → cátodo; ánodo a GND; lectura por cátodo a través de C4 (C_c) |
| ESD PROTECTION | D1 = BAT54S | Clamp de −IN a GND y +5 V |
| TRANSIMPEDANCE AMPLIFIER | U2, R4 = R5 = 1 kΩ, C5 = 10 µF, C6 = 100 nF, C9 = 10 µF, C10 = 100 nF | TIA, divisor Uref = 2,5 V con filtro, desacople de V+ |
| CONFIGURABLE TIA FEEDBACK | R6 = 2,2 kΩ, R7 = 3 kΩ, R8 = 750 Ω, R9 = 240 Ω, JP1–JP3, C7 y C8 (DNP) | Banco de R_F del LOG 9 y lugar para C_F |
| OUTPUT | R10 = 50 Ω, C11 = 1 µF, R11 = 10 kΩ, J3 (SMA) | Resistencia serie de salida, acople AC y referencia a masa |

Etiquetas de red: `+V_BIAS`, `TIA_IN`, `TIA_OUT`, `UREF`, `VOUT`. Los valores "50" se mantienen así en el esquemático; en el BOM se asigna una pieza de 49,9 Ω.

![Esquemático completo con los 7 bloques](../docs/images/logs/esquematico_EVB-TIA_v0_10-10-26.png)

### 3.2 Decisiones y cambios respecto del diseño de Lara

| Tema | Decisión | Justificación |
|---|---|---|
| Salida rápida del SiPM (R22, J11 en Lara) | **Eliminada**; el pin 2 del SiPM queda con marca de no-conexión | No se usa en esta placa; se descartó dejarla sin montar para que la placa quede limpia |
| C_c (C4 = 1 µF) | **Agregado** | En el LOG 9, el acople DC dejaba −IN a ~29 V. C4 tiene que ser de ≥ 50 V |
| Capacitor de acople de salida (C11) + R11 = 10 kΩ | **Incluidos** (por error se habían quitado y se restauraron) | Es el circuito simulado. Sin C11 el pulso es el mismo pero montado sobre 2,5 V; C11 lleva la base a 0 V |
| C_F | **2 footprints sin montar (C7, C8)** en paralelo con todo el banco de R_F | Pedido de José (09/10): constantes de tiempo ajustables a cada centellador, soldando C_F en el laboratorio |
| Capacitor bulk extra en la entrada de +5 V | **Descartado** | No está en el diseño de Lara y no lo exige el diseño |
| Protección ESD | **BAT54S** en −IN | Decisión propia; protege la entrada del opamp de transitorios del SiPM y del bias |
| R3 (serie del bias) | 10 Ω | LOG 9: recomendación de la AND9782 para el SiPM de 6 mm, y asegura ganancia de ruido > 10 |

### 3.3 Correspondencia de referencias (placa ↔ LOG 9 / simulación / Lara)

| Placa | LOG 9 / simulación | Lara |
|---|---|---|
| R3 | "R4" del LOG 9 | — |
| C4 | C_c (C9 en la simulación) | — |
| U2 | U1 en la simulación | — |
| R6 | R_F base (R5 en la simulación) | — |
| R10 / C11 / R11 | R8 / C8 / R6 en la simulación | — |
| J1, R1, R2, C1, C2, C3 | — | J8, R12, R13, C23, C24, C25 |
| J2, U1, J3 | — | J2, U4, J6 |

### 3.4 Verificación

ERC: **0 errores, 0 advertencias**. El error "Input Power pin not driven" se resolvió con PWR_FLAG en +5V y GND.

---

## 4. Footprints

| Componentes | Footprint | Criterio |
|---|---|---|
| Resistencias | `R_0603_1608Metric` | Estándar para ensamblado a máquina |
| Capacitores (salvo C4, C7, C8) | `C_0805_2012Metric` | Decisión propia: unifica el tamaño de todos los capacitores |
| C4 (C_c, 1 µF, ≥ 50 V) | `C_1206_3216Metric` | Decisión propia. Está sobre el bias de ~30 V; 1206 deja margen para conseguir 1 µF / 50 V (inferencia, a verificar en LCSC) |
| C7, C8 (C_F, DNP) | `C_0603_1608Metric_Pad1.08x0.95mm_HandSolder` | Se sueldan a mano en el laboratorio |
| D1 | `SOT-23` | |
| U2 | `SOT-23-6` | |
| J1, J2, JP1–JP3 | `PinHeader_1x02_P2.54mm_Vertical` | |
| U1 | `EVB-TIA:XDCR_MICROFC-60035-SMT-TR1` | De Lara |
| J3 | `EVB-TIA:LPRS_SMA_CONNECTOR_ANCHITO` | De Lara; se suelda en el laboratorio (excluido de BOM y posiciones) |

**Inconsistencia a resolver:** en las consultas pendientes figuraba C_F en 0805, pero en la placa quedó en **0603 HandSolder**. Hay que confirmar con José cuál se usa (consulta 3).

---

## 5. Board Setup (reglas de diseño)

### 5.1 Constraints (valores finales)

| Parámetro | Valor | Nota |
|---|---|---|
| Minimum clearance | 0,2 mm | Margen sobre la capacidad de JLCPCB |
| Minimum track width | 0,2 mm | |
| Minimum annular width | 0,1 mm | Estaba en 0,15; se bajó porque marcaba error en las vías de 0,5/0,3 |
| Minimum via diameter | 0,5 mm | Estaba en 0,6; mismo motivo |
| Copper to hole clearance | 0,25 mm | |
| Copper to edge clearance | 0,3 mm | El relleno no llega al borde de fresado |
| Minimum drill size | 0,3 mm | |
| Hole to hole clearance | 0,25 mm | |
| Silk: minimum text height | 1,0 mm | Se propone bajar a 0,8 mm (ver §10) |
| Silk: minimum text thickness | 0,15 mm | |

**Capacidades de JLCPCB para 2 capas** (consultadas en su página de capacidades):
- vía mínima de 0,15 mm de agujero y 0,25 mm de diámetro;
- el diámetro tiene que superar al agujero en 0,1 mm (0,15 mm preferido);
- el anillo de 0,18–0,25 mm que también figura corresponde a **pads pasantes de componentes**, no a vías.

La vía de 0,5/0,3 (diferencia de 0,2 mm, anillo de 0,1 mm) es fabricable.

### 5.2 Pre-defined Sizes

| Pistas | Uso | Vías (diámetro / agujero) | Uso |
|---|---|---|---|
| 0,3 mm | Señales: SiPM, TIA_IN/OUT, salida, bias, UREF | 0,6 / 0,3 | Vía estándar |
| 0,5 mm | +5V (recorridos largos) | 0,5 / 0,3 | GND debajo de U2 (no entra una de 0,6) |

El desplegable de vía quedó en 0,5/0,3 al colocar varias vías de GND, así que la mayoría de las vías de la placa son de 0,5/0,3. Es fabricable y no hace falta cambiarlas.

---

## 6. Floorplan

### 6.1 Método

Antes de ubicar los componentes en KiCad se hizo un plano a escala con Python:
- se leyeron las geometrías reales de cada footprint del `.kicad_pcb`;
- se definieron las posiciones;
- se verificó por código que no hubiera superposiciones de courtyard, invasiones de la zona del cristal ni conflictos entre recorridos y pads o pistas de otras redes (pista 0,3 mm, separación 0,2 mm).

El plano está publicado como artifact: **"Floorplan EVB-TIA v0"** (claude.ai/artifact/AF9i3hLMxgUqC1dSTkxX5W). Incluye el plano interactivo, la tabla de posiciones, la tabla de ganancias y la justificación.

### 6.2 Primera versión (descartada)

56 × 45 mm, 4 agujeros M3. El filtro de bias iba en una sola fila de ~19 mm a la izquierda del SiPM y quedaba mucho espacio vacío. Densidad de courtyard: 0,15. Al comparar con la placa de Lara se decidió compactar.

### 6.3 Análisis de la placa de Lara (`placa_detector_v3.kicad_pcb`)

- Contorno de 25,2 × 51,3 mm, 31 footprints, densidad de courtyard 0,34, **sin agujeros de montaje**. Tiene 102 segmentos de pista, 3 vías y 4 zonas (3 en F.Cu, 1 en B.Cu).
- Organización en columna, en el orden en que circula la señal: header de bias arriba → filtro → SiPM cerca del borde → etapas de amplificación → SMA de salida abajo. El header de alimentación va al costado.

### 6.4 Versión compacta (adoptada)

| Placa | Contorno | Área | Densidad | Agujeros |
|---|---|---|---|---|
| Lara | 25,2 × 51,3 mm | 1293 mm² | 0,34 | No |
| EVB-TIA v0, primera versión | 56 × 45 mm | 2520 mm² | 0,15 | 4 × M3 |
| **EVB-TIA v0, compacta** | **33,5 × 34,5 mm** | **1156 mm²** | **0,32** | No |

Disposición:
- **Arriba a la izquierda:** J1 y el filtro de bias en un bloque de 2 filas. J1 → R1 → nodo C1 → R2 baja → C2 → +V_BIAS hacia C3 y R3, que están sobre el cátodo.
- **SiPM** (U1) debajo del filtro. Zona libre para el cristal: courtyard + 1 mm (9,6 × 9,6 mm).
- **Amplificador** a la derecha del SiPM. Se trasladó el bloque entero con la misma geometría interna de la primera versión, así que las métricas críticas no cambian.
- **Uref** (R4, R5, C5) arriba al centro. **Salida** (R10 y C11 en columna sobre OUT, R11) y **SMA** arriba a la derecha.
- **J2** (+5 V) abajo a la izquierda, a 4,7 mm del courtyard del SiPM (J8 de Lara está a ~6 mm).

**Contorno:** `Edge.Cuts` de (100, 50) a (133,5; 84,5) mm.

| Métrica | Valor |
|---|---|
| Pad 3 del SiPM → C4 → pin 4 (−IN) | 8,2 mm |
| Lazo de C_F (−IN → C7 → TIA_OUT → OUT) | 19 mm, ~28 mm² |
| Bus TIA_IN hasta la rama más lejana (R7) | 14,3 mm |
| Distancia mínima de piezas altas al SiPM | 4,7 mm (J2) |

**Topología de U2 (decisión importante):** con el pinout del SOT-23-6, −IN (pin 4) y OUT (pin 1) quedan en esquinas diagonales. Por eso el lazo de realimentación siempre encierra un lado del integrado: los pines {3, 2} o los {5, 6}. Se eligió encerrar **{5, 6} (V+)**. C10 queda dentro del lazo y el +5V entra por un cruce corto en la capa inferior, por debajo de TIA_OUT. U2 va rotado 270°.

### 6.5 Posiciones de colocación (absolutas, del floorplan)

| Ref | X (mm) | Y (mm) | Rot |
|---|---|---|---|
| U1 | 111,15 | 68,01 | 0° |
| C4 | 118,45 | 65,26 | 0° |
| U2 | 123,05 | 64,12 | 270° |
| C7 | 122,95 | 70,81 | 0° |
| C8 | 122,95 | 72,56 | 0° |
| R6 | 122,95 | 74,31 | 0° |
| R9 | 122,95 | 76,06 | 0° |
| R8 | 122,95 | 77,81 | 0° |
| R7 | 122,95 | 79,56 | 0° |
| JP3 | 126,75 | 75,61 | 90° |
| JP2 | 126,75 | 78,15 | 90° |
| JP1 | 126,75 | 80,69 | 90° |
| C10 | 124,55 | 67,91 | 270° |
| C9 | 128,65 | 67,01 | 0° |
| D1 | 119,75 | 68,21 | 0° |
| C6 | 122,10 | 60,17 | 90° |
| R5 | 118,15 | 57,21 | 180° |
| C5 | 118,05 | 59,61 | 180° |
| R4 | 118,15 | 55,01 | 0° |
| R3 | 113,90 | 61,73 | 270° |
| C3 | 113,90 | 58,35 | 90° |
| R10 | 124,45 | 60,41 | 90° |
| C11 | 124,45 | 56,60 | 90° |
| R11 | 122,50 | 55,00 | 270° |
| J3 | 129,20 | 54,30 | 0° |
| J1 | 102,60 | 52,50 | 0° |
| R1 | 106,30 | 52,50 | 0° |
| C1 | 110,60 | 52,50 | 0° |
| R2 | 108,40 | 55,00 | 270° |
| C2 | 110,60 | 57,50 | 0° |
| J2 | 103,00 | 77,50 | 0° |

**Nota:** la placa real puede diferir levemente de esta tabla. En una captura, C10 parecía estar ~0,5 mm más cerca de U2 de lo previsto, lo que apretaba la vía de +5V contra el bus TIA_IN. El DRC final no marca errores de separación. La referencia definitiva es el archivo de KiCad.

> [!NOTE]
> Estas posiciones corresponden al floorplan del 10/10. En el LOG 11 la placa se reordenó y el contorno pasó a (113,2; 53,75) → (146,7; 88,25). Para la versión fabricada, la referencia es el CPL del LOG 12.

![Floorplan compacto (artifact) y placa con los componentes ubicados](../docs/images/logs/floorplan_compacto_EVB-TIA_v0_10-10-26.png)

---

## 7. Ruteo

### 7.1 Configuración

Grilla de 0,25 mm, router en modo *Walk around*, pistas de 0,3 mm para señales y 0,5 mm para +5V.

### 7.2 Orden

Se ruteó de lo más crítico a lo menos crítico:
1. Pad 3 del SiPM → C4 → pin 4, y R3 → pad 3.
2. Bus TIA_IN (pin 4 → C7, C8, R6–R9) y pad 3 de D1.
3. Retorno TIA_OUT (pin 1 → costado de U2 → R6, C7, C8, pin 2 de los JP) y R7–R9 → JP.
4. Salida: pin 1 → R10 → C11 → J3, y R11.
5. UREF: R4, R5, C5 → C6 → pin 3.
6. Filtro de bias.
7. +5V.

C7 y C8 se rutean aunque no se monten, para que soldar C_F en el laboratorio no requiera cablear.

### 7.3 +5V

| Tramo | Recorrido |
|---|---|
| J2 → R4 | Por el borde izquierdo y el superior, por fuera de J1 para no cruzar J1 → R1 |
| J2 → D1 | Por debajo del SiPM |
| J2 → C9 | Por el borde inferior y el derecho |
| C9 → C10 / pines 5–6 | **Cruce por B.Cu:** vía junto a C9 (≈ 127,7; 68,6) → pista en B.Cu por debajo de TIA_OUT → vía junto a C10 (≈ 123,1; 67,3) |

Es tensión continua, así que la longitud no importa. La regla es que ningún tramo pase por debajo de TIA_IN.

**Problema encontrado:** la tecla V no colocaba la vía. El motivo era que la posición elegida, entre C10 y TIA_OUT, no tenía lugar para la vía (0,6 mm + 0,2 mm de separación por lado), y el router la rechazaba sin avisar. Se resolvió colocándola del otro lado de C10.

![Detalle del cruce de +5V por B.Cu (C9 → C10)](../docs/images/logs/cruce_5V_BCu_10-10-26.png)

---

## 8. Plano de masa

### 8.1 Zona GND

Una sola zona en **F.Cu y B.Cu** que cubre toda la placa:
- red GND, clearance 0,2 mm, ancho mínimo 0,25 mm;
- *Remove islands: Always*;
- *Pad connections: Thermal reliefs for PTH*: los SMD van sólidos (menos inductancia) y los pasantes con alivio térmico (el SMA se suelda a mano).

El ajuste de *Thermal reliefs for PTH* se hizo después del primer DRC: con alivio en todos los pads, el pad 2 de C6 tenía un solo rayo y daba error.

### 8.2 Áreas sin cobre (Rule Areas, solo *Keep out copper fills*)

| Área | Capas | Rectángulo (absoluto, aprox.) | Cubre |
|---|---|---|---|
| K1 | F.Cu y B.Cu | (119,15; 64,2) → (122,75; 80,4) | Pad 2 de C4, pin 4, bus TIA_IN, pad 3 de D1 y pads izquierdos de C7–R7 |
| K2 | Solo F.Cu | (121,35; 62,0) → (124,85; 66,2) | U2 entero (incluido OUT) |

- **K2 va solo en F.Cu** porque en B.Cu, debajo de U2, tiene que haber plano para la vía de GND del pin 2. En el floorplan esta área estaba planteada en las dos capas, lo que dejaba esa vía sin conexión; se corrigió acá.
- Se sugirió correr el borde derecho de K1 ~0,5 mm para cubrir por completo los pads izquierdos del banco. **No está confirmado que se haya hecho.**

**Por qué se saca el cobre** (análisis de esta sesión):
- **Hecho:** el datasheet del ADA4895 recomienda no poner plano debajo de −IN ni de OUT. La capacidad parásita en −IN aumenta la ganancia de ruido (1 + C_in/C_F) y reduce el margen de fase.
- **Estimación (no medida):** el cobre alrededor del bus TIA_IN agrega ~1 pF (~0,1–0,3 pF por el plano inferior y ~0,5–1 pF por el relleno lateral). Frente a ~3400 pF del SiPM, el cambio en C_in es ~0,03 %, **no medible** con el SiPM de 6 mm.
- **Decisión:** se aplica igual. No cuesta nada, sigue la recomendación del fabricante y deja la placa preparada para SiPM más chicos, donde el parásito sí pesaría. Este argumento sirve para la tesis.

### 8.3 Conexión del SiPM al plano (hallazgo)

Alrededor de todos los pads del SiPM quedaba un halo sin cobre, incluido el pad 1 (GND). En las propiedades del pad, *Pad connection* decía **"From parent footprint"**: el footprint heredado de Lara está configurado para no conectar sus pads a zonas.

- **Corrección:** pad 1 → *Pad connection* = **Solid**. Los pads 2, 3, 4 y 5 quedan como estaban, porque no son GND.
- Además, el pad 1 tiene una vía de GND a ~0,4 mm del pad, conectada por el relleno.
- **Consulta a Lara:** ¿la configuración del footprint fue intencional?

### 8.4 Vías de GND

| Ubicación | Cantidad | Motivo |
|---|---|---|
| Pin 2 de U2 (debajo del cuerpo), pista corta desde el pin | 1, de 0,5/0,3 | **Obligatoria**: el pin 2 queda dentro de K2 y no toca el relleno de arriba |
| Pad 1 del SiPM (ánodo) | 1 como mínimo; una 2ª opcional | Retorno de la corriente del pulso |
| Pads GND de C10, C9, C6, C5, R5, C1, C2, C3 | 1 cada uno | Un desacople solo funciona con masa cercana. En C10 hizo falta pista pad → vía porque está dentro del lazo, sin relleno arriba |
| Zona de abajo a la derecha | No se agregaron | Ver abajo |

**Zona de abajo a la derecha:** ahí no hay relleno en F.Cu. Es una isla encerrada por la pista de +5V que KiCad eliminó por no tener conexión a GND. Se decidió **no agregar vías para recuperarla**: el plano inferior está entero debajo, y el beneficio (algo de blindaje lateral) no es medible.

**Tira fina en los bordes** izquierdo y superior, entre la pista de +5V y el borde: está unida al relleno por los dos extremos. Opcionalmente se le pueden agregar 2–3 vías de costura.

### 8.5 Análisis: ¿cuántas vías en el pad 1 del SiPM?

**Hecho** (All About Circuits): dos vías en paralelo dan L_eq = (L + M)/2, donde M es la inductancia mutua entre ellas. M se vuelve chica cuando la distancia entre centros supera el largo de la vía (1,6 mm en esta placa). En un primer momento había tomado 1 mm; **se corrigió a ≥ 1,6 mm**.

**Estimación** (supuestos: vía de ~0,5–1 nH; pulso de ~7 mA de pico con ~3 ns de subida para 140 keV en LYSO; señal útil en decenas de MHz):

| Conexión del pad 1 | L | V = L·di/dt durante la subida |
|---|---|---|
| Sin vía (rodeo de ~2 cm) | ~10 nH | ~20 mV |
| 1 vía | ~1 nH | ~2 mV |
| 2 vías separadas | ~0,5 nH | ~1 mV |

El lazo completo del pulso (pad 3 → C4, con ~1 nH propio → −IN → masa → pad 1) suma ~5–10 nH. Pasar de 1 a 2 vías cambia el total ~5–10 %.

**Conclusión:** lo que importa es tener al menos una vía pegada al pad. La segunda casi seguro no se podría medir.

![Placa completa con zonas rellenas](../docs/images/logs/placa_zonas_GND_10-10-26.png)
![Detalle del SiPM: pad 1 conectado al relleno y su vía](../docs/images/logs/detalle_SiPM_pad1_10-10-26.png)

---

## 9. Verificación (DRC)

| Corrida | Resultado | Acción |
|---|---|---|
| 1 | 21 errores: 10 de *annular width* (0,10 < 0,15), 10 de *via diameter* (0,5 < 0,6), 1 de *thermal relief incomplete* (pad 2 de C6) | Se bajaron los mínimos de anillo (0,1) y diámetro de vía (0,5) según JLCPCB; zona en *Thermal reliefs for PTH* |
| 2 | 10 errores de *via diameter* | Faltaba guardar *Minimum via diameter* = 0,5 |
| 3 | **0 errores, 0 sin conectar**, 52 advertencias | Pendiente: serigrafía |

Las 52 advertencias son:
- *Silkscreen clearance*: textos encimados entre sí o sobre otros componentes (C1/R1, R2/C2, C4/C5, R5/C5, C4/D1, C7/C8, etc.);
- *Text height out of range*: la referencia de U1 mide 0,64 mm, que viene del footprint de Lara.

Hay 5 *Ignored Tests* que no se revisaron. La superposición de courtyard entre JP1–JP3, que se esperaba, no apareció como error.

![DRC final](../docs/images/logs/DRC_final_10-10-26.png)

---

## 10. Próximo paso propuesto (en espera de la revisión): serigrafía

1. Referencias a 0,8 mm de alto y 0,15 mm de grosor (*Edit → Edit Text & Graphics Properties*), y bajar el mínimo de la regla a 0,8 mm. Alternativa: 1 mm, más legible pero más difícil de ubicar.
2. Mover cada referencia a un lugar libre (M sobre el texto, R para rotar). Ocultar solo las de pasivos donde no entren.
3. Etiquetas a agregar:
   - `BIAS` con `+`/`GND` en J1;
   - `+5V`/`GND` en J2;
   - `OUT` en J3;
   - mini tabla de R_F junto a los JP;
   - `EVB-TIA v0 · 2026`.

   El título y el autor pueden ir en B.Silkscreen.
4. DRC y exclusión de las advertencias que no importen.

Después: archivos de fabricación (Gerber, taladro), BOM y archivo de posiciones (CPL) con partes LCSC, y pedido.

---

## 11. Temas para revisar con José y Lara

**Layout general**
1. ¿Les parece bien la disposición compacta de 33,5 × 34,5 mm (§6.4)? ¿Algún cambio de orientación de los conectores?
2. **Mecánica (consulta 8):**
   - se eliminaron los agujeros de montaje, como en la placa de Lara. ¿Hace falta fijar la placa? Hay lugar para un agujero abajo a la izquierda, cerca de (110; 79,5);
   - tamaño de los cristales y cómo se sujetan; J2 queda a 4,7 mm del courtyard del SiPM.
3. Posición del SMA (arriba a la derecha) y de los headers (J1 arriba a la izquierda, J2 abajo a la izquierda).

**Circuito / layout crítico**

4. Topología de realimentación: lazo que encierra V+ (pines 5–6) con el cruce de +5V por B.Cu debajo de TIA_OUT (§6.4, §7.3).
5. Áreas sin cobre K1/K2. Según la estimación del §8.2, con el SiPM de 6 mm el efecto no es medible. ¿Mantener o simplificar?
6. Tamaño del footprint de C_F: 0603 HandSolder en la placa vs 0805 en la consulta 3.
7. Vías de 0,5/0,3 en casi todas las GND (fabricables según JLCPCB).

**Para Lara**

8. El footprint del SiPM tiene los pads en "no conectar a zonas". ¿Fue intencional? ¿Cómo conectó ella el ánodo a masa?
9. ¿Qué estrategia de plano de masa usó? Su placa tiene 3 zonas en F.Cu, 1 en B.Cu y solo 3 vías.

**Serigrafía**

10. ¿Referencias a 0,8 mm u ocultar las de los pasivos? ¿Qué etiquetas consideran imprescindibles?

---

## 12. Correcciones durante la sesión (trazabilidad)

| Propuesta inicial | Corrección | Motivo |
|---|---|---|
| Agregar el pin 4 al símbolo del SiPM | Se usa el símbolo sin cambios | Es el símbolo de onsemi |
| Crear a mano el símbolo del ADA4895 | Se generó el archivo `.kicad_sym` | No había símbolo descargable |
| C5 como bulk de entrada | Descartado | No es necesario por diseño y no está en Lara |
| R22 y J11 sin montar | Eliminados | Placa limpia |
| Sin capacitor de acople de salida | Restaurado C11 + R11 | Es el circuito simulado |
| Rótulo provisorio ("Sonda gamma con SiPM") | Título real del PI: "Desarrollo de un sistema de detección gamma para cirugía radioguiada" | Tomado de la propuesta |
| Footprints 0603 estándar → 0805 HandSolder de Lara | Estándar de máquina; capacitores 0805, C4 1206 | Ensambla JLCPCB |
| Floorplan de 56 × 45 mm "sin problema por el espacio vacío" | Floorplan compacto de 33,5 × 34,5 mm | La comparación con Lara mostró el desperdicio |
| K2 en F.Cu y B.Cu | Solo F.Cu | La vía de GND del pin 2 necesita plano abajo |
| Vías múltiples separadas ≥ 1 mm | ≥ 1,6 mm (largo de la vía) | Verificado en bibliografía |
| Importancia de las vías múltiples | Reducida: lo crítico es la 1ª vía | Estimación cuantitativa §8.5 |

---

## Pendientes

- [x] Revisión del layout con José y Lara (§11). → Reunión con José el 13/10 (LOG 11). La parte de Lara (consultas 12 y 13) sigue abierta.
- [ ] Ampliar K1 ~0,5 mm a la derecha, si no se hizo.
- [x] Serigrafía (§10) y DRC final. → LOG 11 (DRC 0/0/0).
- [ ] Revisar los 5 *Ignored Tests* del DRC.
- [x] Archivos de fabricación: Gerber, taladro, BOM y CPL con partes LCSC. → LOG 12.
- [ ] Resolver las consultas de `Consultas_pendientes_EVB-TIA.md`.
- [ ] Simular la estabilidad con C_F agregando ~15 nH en serie (inductancia del lazo físico) antes de soldar C_F grandes.
- [ ] Exportar el esquemático a PDF y hacer backup del proyecto KiCad (ZIP). → El ZIP de fabricación se hizo el 19/10 (LOG 12); falta el PDF del esquemático.

---

## Archivos

> [!IMPORTANT]
> El proyecto KiCad de la EVB-TIA v0 se encuentra en: `hardware/EVB-TIA-v0/`

- **Proyecto KiCad:**
  - `EVB-TIA-v0.kicad_pro`, `.kicad_sch`, `.kicad_pcb`;
  - bibliotecas `EVB-TIA.kicad_sym`, `ADA4895.kicad_sym` y `EVB-TIA.pretty/` (SiPM y SMA).
- **Artifact:** "Floorplan EVB-TIA v0" (versión 2, compacta).
- **Documentación:** `Consultas_pendientes_EVB-TIA.md` (actualizado en esta sesión).

## Referencias

- Analog Devices, ADA4895-1/-2 Data Sheet, Rev. B (pinout, recomendaciones de layout).
- onsemi, AND9782/D, Rev. 3 (Configuración C, Fig. 10 filtro de bias).
- onsemi, MICROC-SERIES/D.
- Torletti Daniluk (2025), `placa_detector_v3` (esquemático y PCB).
- JLCPCB, *PCB Manufacturing Capabilities* — https://jlcpcb.com/capabilities/pcb-capabilities
- All About Circuits, *Different via configurations for connecting decoupling capacitors* — https://www.allaboutcircuits.com/technical-articles/different-via-configurations-for-connecting-decoupling-capacitors/
- In Compliance Magazine, *Decoupling Capacitor Design on PCBs to Minimize Inductance and Maximize EMI Performance* — https://incompliancemag.com/decoupling-capacitor-design-on-pcbs-to-minimize-inductance-and-maximize-emi-performance/
