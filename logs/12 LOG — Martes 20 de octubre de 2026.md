
## Fabricación de la EVB-TIA v0: archivos de fabricación, pedido a JLCPCB (placa + ensamblado) y verificaciones

**Tipo:** generación de archivos de fabricación (KiCad 10.0.5) y armado del pedido en JLCPCB. Sin trabajo experimental.
**Fechas:** 19/10 (Gerber, taladros, BOM, CPL) y 20/10 (pedido, verificación de partes y de colocación).
**Continúa:** LOG 11 (retoques finales y serigrafía, DRC 0/0/0).

**Estado al cierre:**
- Pedido armado y verificado en el carrito de JLCPCB.
- **El checkout y la declaración de aduana los hace Tesorería.**
- Quedan pendientes las dos aprobaciones de JLCPCB (archivo de producción y colocación de componentes), que llegan a mi cuenta.

---

> [!IMPORTANT]
> ### 🏁 HITO 3 — EVB-TIA v0 enviada a fabricar
>
> **Fecha:** 20 de octubre de 2026
>
> **Resultado:** la primera placa propia del proyecto (TIA de una etapa con ADA4895, Configuración C, banco de R_F configurable con jumpers) pasó del diseño a la fabricación profesional: 5 placas ensambladas por JLCPCB, con el SiPM MICROFC-60035-SMT soldado por reflujo.
>
> **Recorrido:** simulación y definición del banco de R_F (LOG 9, 23/09) → esquemático, floorplan, ruteo y plano de masa (LOG 10, 10/10) → retoques con el director y serigrafía (LOG 11, 13–14/10) → archivos de fabricación y pedido (LOG 12, 19–20/10).
>
> **Significado:** cierra la etapa de diseño de la electrónica de lectura iniciada al confirmar que el 60035 no se puede leer sin amplificación (LOG del 31/08) y al validar la placa BGA614 ×100 de Lara (LOG 7, 09/09). Por primera vez se lee la **salida estándar** (carga completa, información de energía) con un TIA diseñado y simulado dentro del proyecto.
>
> **Habilita:** medición de la carga del SPE en hardware (resuelve la incertidumbre del modelo, LOG 9 §6.3), primeros espectros con LYSO/GSO y comparación con la placa de Lara. Es la base del paper sobre la electrónica de lectura previsto para EAMTA 2027.

---

## Resumen

- **Pedido:**
  - 5 placas (Y2-13868174A);
  - 5 placas ensambladas en Economic PCBA (SMT026102064336-13868174A);
  - envío DHL Express;
  - **total ≈ USD 526**, más impuestos de importación.
- **Costo:** el **95 % del costo son los 5 SiPM** (~USD 79 cada uno). La cantidad de 5 placas ensambladas la acordé con José.
- **Acabado:** **LeadFree HASL** (ENIG costaba ~USD 16 más).
- **Verificaciones:**
  - todos los capacitores tienen margen de tensión ≥ ×1,6 (los del bias son de 50 V);
  - el pinout de D1 se verificó contra su hoja de datos;
  - la orientación de U1, U2 y D1 se verificó en la vista previa de JLCPCB: **hubo que corregir U2 (90°) y D1 (180°)**.
- **Hallazgos de la nota AND9788 de onsemi** (manipulación y soldadura del SiPM):
  - pico de reflujo máximo de 260 °C durante ≤ 10 s, con ≤ 2 pasadas;
  - **el alcohol isopropílico concentrado daña el encapsulado** (solo se puede usar una solución al 20 %);
  - no se recomienda retrabajar el sensor a mano.

---

## 1. Preparación

- **Paso 0:** se congeló la versión con *File → Archive Project…* (ventana principal de KiCad) → `EVB-TIA-v0_fab_2026-10-19.zip`. ✓ Hecho.
- Se agregó en el esquemático el campo **LCSC = C905854** a U1. U2 ya tenía **LCSC = C654293**, porque el símbolo creado lo incluía.
- *Fabrication Outputs* está en el menú *File* del **editor de PCB**, no en la ventana principal de KiCad.

## 2. Gerber

Se generaron con *File → Plot* (formato Gerber).

| Opción | Valor |
|---|---|
| Include Layers | F.Cu, B.Cu, F.Paste, B.Paste, F.Silkscreen, B.Silkscreen, F.Mask, B.Mask, Edge.Cuts |
| **Plot on All Layers** | **Vacío.** Habían quedado B.Cu y F.Silkscreen tildados de la exportación SVG: con eso, el cobre de abajo se habría copiado dentro de cada Gerber (cortocircuitos) |
| Subtract soldermask from silkscreen | ☑ |
| Check zone fills before plotting | ☑ |
| Plot drawing sheet | ☐ |
| Use drill/place file origin | ☐ (coordenadas absolutas) |
| Use Protel filename extensions | ☑ |
| Use extended X2 format | ☐ |
| Include netlist attributes | ☐ |
| Coordinate format | 4.6, mm |

Resultado: 9 archivos sin errores ni advertencias (`.gtl .gbl .gtp .gbp .gto .gbo .gts .gbs .gm1`) y el `.gbrjob`. Quedaron en `docs\`; se movieron a `fab\` para armar el .zip.

> [!WARNING]
> Es el mismo error que en el LOG 4 (18/08): capas tildadas en *Plot on All Layers* contaminan todos los Gerber. Revisar ese panel **siempre** antes de plotear, sobre todo después de exportar SVG o PDF.

## 3. Taladros

| Opción | Valor |
|---|---|
| Formato | Excellon |
| Mirror Y / Minimal header | ☐ |
| PTH and NPTH in single file | ☐ (separados: los agujeros de tornillo son NPTH) |
| Origin | **Absolute** (igual que los Gerber; si no, los agujeros quedan corridos respecto del cobre) |
| Units / Zeros | mm / Decimal |
| Map | No |

Resultado: `EVB-TIA-v0-PTH.drl` y `EVB-TIA-v0-NPTH.drl`.

**Paquete:** `EVB-TIA-v0_gerbers.zip` con los 11 archivos sueltos, sin subcarpeta. JLCPCB lo interpretó bien: 33,5 × 34,5 mm, 2 capas. La vista previa de las dos caras coincidió con el diseño.

## 4. BOM

Desde el esquemático: *Tools → Generate Bill of Materials* (*Symbol Fields Table*).

| Field | BOM Name | Incl. | Group by |
|---|---|---|---|
| Reference | Designator | ☑ | ☐ |
| Value | Comment | ☑ | ☑ |
| Footprint | Footprint | ☑ | ☑ |
| LCSC | LCSC Part # | ☑ | ☑ |
| Todos los demás | — | ☐ | — |

- **Engranaje ⚙:** se destildaron *Include 'DNP' Symbols* (saca C7/C8) e *Include 'Exclude from BOM' Symbols* (saca J1, J2, J3 y JP1–JP3).
- **Resultado:** `EVB-TIA-v0_BOM.csv` con **16 líneas y 23 componentes**.

## 5. CPL (archivo de posiciones)

Desde el PCB: *File → Fabrication Outputs → Component Placement*.

| Opción | Valor |
|---|---|
| Format / Units | CSV / mm |
| Include only SMD footprints | ☑ |
| Exclude Do Not Populate | ☑ |
| Exclude 'Exclude from BOM' | ☑ |
| **Use drill/place file origin** | **☐** (estaba tildado; se destildó para que coincida con los Gerber) |
| Single file both sides | ☑ |

- **Encabezados:** se renombraron al formato de JLCPCB:
  - de `Ref,Val,Package,PosX,PosY,Rot,Side`
  - a `Designator,Val,Package,Mid X,Mid Y,Rotation,Layer`.
- **Archivo:** `EVB-TIA-v0_CPL.csv`, con **23 componentes**, todos en la cara top. Las Y negativas son la convención de KiCad y JLCPCB las interpreta bien.
- **Observación:** R6, R9, R8 y R7 quedaron a **1,5 mm** de paso (no 1,75 como en el plan). Las courtyards no se superponen y quedan ~0,55 mm entre pads, suficiente para el ensamblado.

---

## 6. Partes elegidas (BOM final)

Las eligió automáticamente JLCPCB a partir de valor + footprint, y se confirmaron fila por fila. El aviso ⚠ de cada fila era un pedido de confirmación, no un error.

| Ref. | LCSC | Especificación | Tipo | Cant. comprada | Costo USD |
|---|---|---|---|---|---|
| C1, C3 | C1710 | 10 nF 50 V X7R 0805 (CL21B103KBANNNC) | Basic | 10 | 0,115 |
| C2, C6, C10 | C49678 | 100 nF 50 V X7R 0805 (CC0805KRX7R9BB104) | Basic | 15 | 0,308 |
| C4 | C1848 | 1 µF 50 V X7R 1206 (CL31B105KBHNNNE) | Basic | 5 | 0,273 |
| C5, C9 | C15850 | 10 µF 25 V X5R 0805 (CL21A106KAYNNNE) | Basic | 10 | 0,875 |
| C11 | C28323 | 1 µF 50 V X7R 0805 (CL21B105KBFNNNE) | Basic | 5 | 0,172 |
| D1 | C7420333 | BAT54S SOT-23 (hongjiacheng) | Extended | 10 | 0,129 |
| R1, R2, R10 | C849792 | 50 Ω 0,1 % thin film 0603 (RT0603BRE0750RL) | Extended | 23 | 0,621 |
| R3 | C22859 | 10 Ω 1 % 0603 | Basic | 5 | 0,016 |
| R4, R5 | C21190 | 1 kΩ 1 % 0603 | Basic | 10 | 0,030 |
| R6 | C4190 | 2,2 kΩ 1 % 0603 | Basic | 5 | 0,009 |
| R7 | C4211 | 3 kΩ 1 % 0603 | Basic | 5 | 0,012 |
| R8 | C23241 | 750 Ω 1 % 0603 | Extended | 20 | 0,070 |
| R9 | C23350 | 240 Ω 1 % 0603 | Extended | 20 | 0,034 |
| R11 | C25804 | 10 kΩ 1 % 0603 | Basic | 5 | 0,027 |
| **U1** | **C905854** | **MICROFC-60035-SMT-TR1** | Extended | 5 | **395,38** |
| **U2** | **C654293** | **ADA4895-1ARJZ-R2** | Extended | 5 | **58,04** |

- **Cantidades mayores que las necesarias** (10, 20, 23): son mínimos de compra o reservas por pérdidas en el montaje. Lo que sobra queda en la biblioteca de partes de la cuenta de JLCPCB para pedidos futuros; no se envía.
- **R1, R2, R10:** se mantuvo la de 50 Ω exactos (Extended) en lugar de buscar una de 49,9 Ω Basic. La diferencia eléctrica es nula.
- **R8 y R9** son Extended porque son los valores definidos en el estudio del LOG 9.

### 6.1 Verificación de tensión de los capacitores

| Capacitor | Función | Tensión de trabajo | Nominal | Margen |
|---|---|---|---|---|
| C1, C2, C3 | Filtro y desacople del bias | ~27–31 V | 50 V | ×1,6–1,9 |
| C4 | Acople cátodo → TIA_IN | ~25–28 V | 50 V | ×1,8–2 |
| C5 | Filtro de Uref | 2,5 V | 25 V | ×10 |
| C6 | Uref en el pin 3 | 2,5 V | 50 V | ×20 |
| C9 | Reserva de +5V | 5 V | 25 V | ×5 |
| C10 | Desacople de V+ | 5 V | 50 V | ×10 |
| C11 | Acople de salida | 2,5 V | 50 V | ×20 |

- **Criterio:** tensión nominal ≥ ~1,5–2 × la de trabajo. Se cumple en todos.
- El rango de 27–31 V corresponde a una sobretensión de 2,5–6 V sobre una tensión de ruptura de ~24,5 V.
- **Pérdida de capacidad por tensión continua (DC bias)** (valores típicos, no medidos):
  - C4 (1 µF, 1206) a ~28 V → ~0,4–0,6 µF efectivos. Sigue siendo > 100 × C_SiPM, así que no afecta;
  - C9 (10 µF, 0805, X5R) a 5 V → ~5–7 µF. Suficiente para la función de reserva.

### 6.2 D1: verificación del pinout

La parte elegida es de un fabricante poco conocido, así que se revisó su hoja de datos (*Function Diagram*, página 1). BAT54S:
- diodo 1: ánodo en el pin 1, cátodo en el pin 3;
- diodo 2: ánodo en el pin 3, cátodo en el pin 2.

O sea: **1 = ánodo, 2 = cátodo, 3 = común**, el pinout estándar. Coincide con la placa:
- pin 1 a GND (sujeta TIA_IN por debajo de ~−0,3 V);
- pin 2 a +5V (por encima de ~5,3 V);
- pin 3 a TIA_IN.

---

## 7. Opciones del pedido en JLCPCB

### 7.1 Placa

| Opción | Valor | Motivo |
|---|---|---|
| Material / capas / espesor | FR-4, 2, 1,6 mm | Diseño |
| Dimensiones | 33,5 × 34,5 mm (del Gerber) | |
| Cantidad | 5 | Mínimo; casi el mismo precio que 2 |
| Product Type | Industrial/Consumer | Las otras opciones suman controles y costo |
| Delivery | Single PCB | |
| Color / serigrafía | Verde / blanca | Más barato y rápido; permite ver las pistas al depurar |
| Material | FR4 TG135 | |
| **Acabado** | **LeadFree HASL** (+USD 1,10) | Ver §7.4 |
| Cobre | 1 oz | |
| Vías | **Tented** | Igual que en KiCad |
| Vía mínima | 0,3 mm / (0,4/0,45 mm) | Nuestras vías (0,3 mm de agujero, 0,5–0,6 mm de diámetro) entran sin recargo |
| Board outline tolerance | ±0,2 mm | |
| **Confirm Production File** | **Yes** (+USD 1,05) | Revisar el archivo procesado, con los agujeros de sujeción, antes de fabricar |
| Mark on PCB | Remove Mark | No imprimir el número de pedido |
| Electrical Test | Flying Probe | Incluido |
| Silkscreen | Ink-jet | |
| Shortage Preference | Require Full Quantity | |

**PCB Remark:**
> *Tooling holes: please place them in the copper (GND) area next to the two M3.5 mounting holes (top-right and bottom-left corners). Do not cut the +5V trace that runs along the board edges.*

### 7.2 Agujeros de sujeción (*tooling holes*)

- **Hecho** (guía de JLCPCB): en la Economic PCBA son obligatorios. Son 2 agujeros NPTH de 1,152 mm (con expansión de máscara de 0,148 mm), en esquinas opuestas y **dentro de la placa**. Si no los agrega el cliente, los pone JLCPCB.
- **Riesgo:** las esquinas libres de la placa tienen cerca la pista de +5V que recorre el borde.
- **Decisión:** que los agregue JLCPCB, con el comentario de arriba y la confirmación del archivo de producción activada para revisarlos antes de fabricar.
- **Alternativa para la v1:** diseñarlos en KiCad (opción *Added by Customer*).

### 7.3 Ensamblado

| Opción | Valor | Motivo |
|---|---|---|
| Tipo | Economic | El SiPM C905854 la admite |
| Lado | Top | Todos los SMD están arriba |
| Cantidad | **5** | Acordado con José (ver §10) |
| Tooling holes | Added by JLCPCB | §7.2 |
| **Confirm Parts Placement** | **Yes** (+USD 0,45) | Revisión de orientación por un ingeniero |
| Bake components | No | JLCPCB maneja los MSL con su proceso |
| **Board cleaning** | **No** | Los removedores de flux y el IPA concentrado dañan el SiPM (§9) |
| **Conformal coating** | **No** | Cubriría la ventana óptica del SiPM |
| Solder paste | **High temp.** (SAC305) | §7.5 |
| Nitrogen reflow | Yes | Incluido en Economic |
| Depanel / Flying probe / Function test / Photo confirmation | No | |
| Parts selection | By Customer | |

**Assembly remark:**
> *U1 is an optical sensor (SiPM, onsemi MICROFC-60035-SMT). Please keep its top window clean: no glue, no coating, no labels on it. U1 pad 5 (center) has no solder paste on purpose (manufacturer recommendation). Max reflow peak 260 °C for ≤10 s, max 2 reflow cycles (onsemi AND9788).*

**Stencil:** no se pidió; JLCPCB usa el suyo.
**Build time:** 24 h (PCBA Only), sin costo.

### 7.4 Acabado: ENIG vs LeadFree HASL

- **ENIG:** pads planos, mejor para el SiPM (pads grandes, sin patas; también importa que el cristal apoye plano) y el SOT-23-6. Mejor conservación en el tiempo. Costaba ~+USD 16.
- **LeadFree HASL:** superficie algo irregular (decenas de µm), pero es el estándar con el que se fabrica la mayoría de las placas con estos componentes. El riesgo es bajo.
- **Decisión: LeadFree HASL.** Se descartó HASL con plomo: tiene la misma irregularidad y además contiene plomo.

### 7.5 Pasta de soldar

- **Opciones de JLCPCB:**
  - **High temp** (Sn96,5 Ag3 Cu0,5): equipo hasta 260 °C, sin costo;
  - **Medium** (SnBiAg, 210 °C): +USD 31,40;
  - **Low** (SnBi, ~180 °C).
- **Límite de onsemi** (AND9788): pico de 260 °C durante ≤ 10 s, con ≤ 2 pasadas (J-STD-020).
- **Análisis:** el pico típico de un perfil SAC305 sobre la placa es de ~240–250 °C, dentro del límite aunque cerca. Los 105 °C del datasheet son la temperatura máxima de **almacenamiento**, no la de soldadura. El SiPM pasa una sola vez por el horno.
- **Decisión:** **High temp.**, con el límite escrito en el *Assembly remark*.

---

## 8. Verificación de la colocación (vista previa de JLCPCB)

**Qué indica el punto magenta** (JLCPCB, *PCB Assembly FAQs part 2*): es una **marca de orientación**, no necesariamente el pin 1. Tiene que coincidir con la marca de pin 1 de la serigrafía. Si la serigrafía y el CPL no coinciden, JLCPCB se guía por la serigrafía.

**Corrección del análisis:** al principio se interpretó el punto magenta como "pin 1" sin verificarlo. El diagnóstico de U2 y D1 se apoyó en la geometría (patas del modelo sobre pads), que no depende de ese significado.

| Componente | Estado inicial | Corrección | Resultado |
|---|---|---|---|
| U1 (SiPM) | Punto junto al punto blanco de pin 1, sobre el pad 1 (ánodo) | — | ✓ |
| U2 (ADA4895) | Modelo girado 90°: patas a los costados, pads en filas arriba/abajo | **+90° (horario)** | ✓ Pin 1 arriba a la derecha, junto al ▲ |
| D1 (BAT54S) | Modelo girado 180°: una pata a la izquierda, dos pads a la izquierda | **180°** | ✓ Pin 1 arriba a la izquierda (pad 1 = GND) |
| Pasivos | Alineados | — | ✓ |

**Por qué es crítico U1:** si quedara girado 180°, el ánodo y el cátodo se invertirían. Con el bias aplicado, el SiPM quedaría en directa y se dañaría.

**Para la v1:** las rotaciones de U2 y D1 difieren entre el 0° de la biblioteca de KiCad y el de la cinta de JLCPCB. Se pueden corregir directamente en el CPL.

![Vista previa de colocación en JLCPCB: U2 y D1 corregidos](../docs/images/logs/jlcpcb_colocacion_U2_D1_20-10-26.png)

---

## 9. Hallazgos de la nota AND9788/D de onsemi

*Handling and Soldering of Molded Leadframe Packaged SiPM Sensors*, Rev. 4, 2018. Aplica al sufijo -SMT.

- **Reflujo:** pico máximo de 260 °C durante ≤ 10 s, con **≤ 2 pasadas**, según J-STD-020. Pasta *no-clean*.
- **Limpieza:** **el IPA concentrado y los removedores de flux comerciales causan daño "severo e irreversible"** al encapsulado de resina epoxi. Si hace falta limpiar, usar una **solución de IPA al 20 %**, con la placa a temperatura ambiente.
  - **Esto corrige una indicación anterior** (limpiar la ventana con alcohol isopropílico).
- **Retrabajo manual: no recomendado.** Calentar por encima de 250 °C durante más de 60 s puede dañar el encapsulado. Si un SiPM sale mal soldado, no conviene intentar arreglarlo con aire caliente.
- **Humedad:** MSL 3 en carrete (168 h fuera del empaque) y **MSL 4 en cinta suelta (72 h)**. Horneado según J-STD-033, hasta 33 h a 90 °C, sin superar los 105 °C.
- **Stencil sugerido:** 0,1 mm de espesor, apertura = pad − 10 % en X e Y. Lo maneja JLCPCB.

### 9.1 Por qué el IPA concentrado daña el encapsulado

**Lo que dice onsemi (hecho):**
- el compuesto de moldeo transparente es una resina epoxi orgánica que los solventes pueden dañar;
- tiene una expansión térmica relativamente alta;
- no explica el mecanismo del daño.

**Mecanismo probable (inferencia, no confirmada por el fabricante):**
1. Para ser transparente, la resina no lleva relleno de sílice (los encapsulados negros llevan ~70–90 %). Por eso absorbe más solvente y se expande más con la temperatura.
2. Queda con tensiones residuales: contracción al curar, diferencia de expansión con el cobre y el silicio, y el reflujo.
3. El solvente penetra la superficie, la ablanda y la hincha. Bajo esas tensiones se forman microfisuras superficiales (*environmental stress cracking*, *crazing*).
4. Al 20 %, la actividad del solvente cae por debajo del umbral de daño, y el agua absorbida se elimina con el horneado.

**Consecuencias probables (inferencia):**
- dispersión de la luz → menos fotones detectados → peor resolución en energía;
- separación entre la resina y el leadframe → entrada de humedad → más corriente de fuga y riesgo de *popcorning* en un reflujo posterior.

**Reglas de manipulación en el laboratorio** (valen para todos los SiPM del proyecto, no solo la EVB):
- No usar IPA al 99 % ni toallitas con alcohol sobre el SiPM o cerca. Incluye limpiar flux después de soldar headers, SMA o C_F.
- Usar flux *no-clean* al soldar a mano.
- Si hay que limpiar: IPA al 20 % (20 ml de IPA + 80 ml de agua destilada), con la placa a temperatura ambiente.
- Grasa óptica: agua tibia con jabón y cepillo de nylon; después IPA al 20 % para las manchas, y horneado a 90 °C.

> [!WARNING]
> Estas reglas se suman al protocolo de soldadura del LOG 6 (≤ 260 °C, ≤ 10 s). Juntas forman el **protocolo de manipulación de SiPM** del proyecto.

---

## 10. Costos y logística

| Concepto | USD |
|---|---|
| Placa desnuda (5 u.): incluye acabado 1,10 y confirmación 1,05 | 6,15 |
| Armado: costo fijo 8,24 + stencil 1,55 | 9,79 |
| Componentes (16 ítems) | 456,11 |
| — de los cuales: SiPM ×5 | 395,38 |
| — de los cuales: ADA4895 ×5 | 58,04 |
| Recargo por partes Extended | 9,27 |
| Montaje 0,61 + confirmación de colocación 0,45 + nitrógeno 0,91 | 1,97 |
| **Subtotal** | **483,29** |
| Envío DHL Express (4–7 días hábiles) | 42,72 |
| **Total** | **≈ 526,01** |
| *Comentario de ensamblado* | *A cotizar por JLCPCB* |
| *Impuestos de importación* | *Se cobran al recibir* |

- **Cantidad (5 vs 2 placas ensambladas):** con 2, el total estimado era ~USD 211, unos USD 270 menos (3 SiPM). Se evaluó pedir 2 por ser una v0 sin probar. **José decidió 5.**
- **Envío:** DHL Express, elegido por José.
- **Pago y aduana:** los hace **Tesorería**.
  - En el detalle del ensamblado, *Product Description* aparecía como `jlcpcb_missing_text`. Le avisé a Tesorería que la descripción para aduana corresponde a *Research / Electronic evaluation board (prototype)*.
  - En los envíos por courier a Argentina suele pedirse el CUIT/CUIL del destinatario.
- **Pedidos:** placa **Y2-13868174A**; ensamblado **SMT026102064336-13868174A**.
- **Peso:** ~0,13 kg (placas) + 0,02 kg (ensamblado); 236,57 g declarados en el presupuesto.

---

## Pendientes

- [ ] Tesorería: checkout y pago.
- [ ] **Aprobar el archivo de producción** en JLCPCB: revisar dónde quedaron los agujeros de sujeción, que no corten la pista de +5V del borde.
- [ ] **Aprobar la colocación de componentes**: verificar otra vez U1, U2 y D1 en la propuesta del ingeniero.
- [ ] Responder la cotización del *Assembly remark* si la piden.
- [ ] Guardar en el repositorio del proyecto la carpeta `fab\` (Gerber .zip, BOM, CPL).
- [ ] Al recibir: inspección visual (orientación de U1, U2 y D1; soldaduras), medición de continuidad y cortos (+5V–GND, V_BIAS–GND), y después el procedimiento de encendido (primero +5 V, después el bias con límite de corriente).

## Mejoras anotadas para la v1

- Agujeros de sujeción diseñados en KiCad (1,152 mm NPTH), en lugar de dejarlos a criterio de JLCPCB.
- Corrección de rotación de U2 y D1 en el CPL (o con un campo de offset de rotación).
- Campo LCSC en todos los símbolos, para no depender de la elección automática.
- Evaluar ENIG.
- Evitar que la pista de +5V recorra los bordes cerca de las esquinas.

## Archivos

> [!IMPORTANT]
> Los archivos de fabricación se encuentran en: `hardware/EVB-TIA-v0/fab/`

- `EVB-TIA-v0_gerbers.zip` (9 Gerber + 2 .drl), `EVB-TIA-v0_BOM.csv`, `EVB-TIA-v0_CPL.csv` (encabezados de JLCPCB).
- Proyecto archivado: `EVB-TIA-v0_fab_2026-10-19.zip` (versión congelada que se fabricó).
- Hoja de datos de D1: `D1_Shotckey_C7420333.pdf`.

## Referencias

- onsemi, AND9788/D Rev. 4 — *Handling and Soldering of Molded Leadframe Packaged SiPM Sensors*.
- onsemi, MICROC-SERIES/D (temperaturas, MSL, pines 4 y 5).
- JLCPCB, *How to add tooling holes for PCB assembly order*; *PCB Assembly FAQs (part 2)*; *PCB Manufacturing Capabilities*.
- Hongjiacheng, BAT54 thru BAT54S datasheet (C7420333).
- LOG 9 (banco de R_F, tensiones de bias), LOG 10–11 (diseño de la placa).
