<p align="center">
  <img src="docs/images/banner_gamma_tracker.png" alt="Gamma Tracker" width="100%">
</p>

# Gamma Tracker
### Sonda gamma para cirugía radioguiada

<p>
Sistema de detección de radiación gamma para asistencia en cirugía laparoscópica oncológica, basado en <strong>centellador inorgánico + SiPM</strong>, con electrónica de lectura multicanal e interfaz en tiempo real.
</p>

<hr>

<p>
<strong>PROYECTO INTEGRADOR</strong><br>
Ingeniería en Telecomunicaciones · Instituto Balseiro · 2026–2027
</p>

<p>
<strong>Autor:</strong> Dana E. González<br>
<strong>Director:</strong> José Lipovetzky<br>
<strong>Codirector:</strong> Fabricio Alcalde
</p>

---

## Contexto

Este proyecto continúa y extiende el trabajo de la tesis *Gamma Tracker* (Torletti, 2025), que demostró la viabilidad de una sonda gamma portátil basada en centellador + SiPM para localización de tejido tumoral marcado con FDG (TRL 4–5). El dispositivo se encuentra en proceso de patentamiento ante el INPI.

El presente proyecto integrador busca avanzar hacia un sistema de mayor resolución espacial y espectral, abordando cuatro líneas principales:

* **Nuevo fotosensor:** evaluación de SiPMs de mayor área activa y menor tensión de polarización, con capacidad de espectroscopía de altura de pulso para discriminación energética a 511 keV.
* **Acople óptico:** comparación cuantitativa de técnicas (grasa óptica, adhesivos UV, fibra óptica) para optimizar eficiencia de transferencia de luz y estabilidad mecánica.
* **Sistema multipixel:** diseño de una matriz de centelladores acoplados a un arreglo de SiPMs con lectura multicanal para mapeo espacial de actividad gamma en tiempo real.
* **Electrónica e interfaz:** desarrollo de electrónica de adquisición, comunicación inalámbrica y alimentación por baterías, aptas para entorno quirúrgico (objetivo TRL 5–6).

---

## Estructura del repositorio

```text
logs/               Cuaderno de laboratorio digital (un archivo por sesión) + criterios/guias/instrucciones
scripts/
  ├── read/         Control de instrumentos y lectura
  └── analysis/     Post-procesamiento, comparación y visualización
data/               Datos experimentales organizados por campaña
  └── <campaña>/
      ├── raw/      CSV crudos (inmutables)
      └── graphs/   Curvas de los resultados
hardware/           Diseños de PCB (KiCad), uno por placa
  └── EVB-TIA-v0/
      └── fab/      Archivos de fabricación enviados (Gerber, BOM, CPL)
docs/               Documentación de soporte e imágenes de los logs
```

## 📓 Cuaderno de laboratorio

> El directorio `logs/` funciona como **cuaderno de laboratorio digital** del proyecto. Cada archivo registra una sesión de trabajo con objetivo, configuración experimental, observaciones, resultados, decisiones técnicas y pendientes. Tambien se incluyen documentos que sustenten las decisiones experimentales.
>
> Los logs priorizan **trazabilidad y reproducibilidad** por sobre presentación. Todo se registra en el cuaderno, preservando el historial completo del razonamiento experimental. 
>
> ```
> logs/
>  ├── 1 LOG — Lunes 3 de agosto de 2026.md
>  ├── 2 LOG — Lunes 10 de agosto de 2026.md
>  └── ...
> ```

---


## Progreso del proyecto

### Hitos

- **Hito 1 — Validación de SiPMs MICROFC-60035-SMT** (11/08/2026) — dispersión de V_br intra-lote σ ≈ 20 mV, ~100× menor que el modelo del prototipo anterior. Los 10 dispositivos son aptos para la matriz multipixel. Habilita la primera propuesta del PI.
- **Hito 2 — Primeros pulsos de fotón individual** (09/09/2026) — dark counts observados con la placa amplificadora BGA614 ×100 (SiPM #09). Primera vez que la cadena SiPM → amplificador → osciloscopio funciona en el proyecto.
- **Hito 3 — EVB-TIA v0 enviada a fabricar** (20/10/2026) — primera placa propia: TIA de una etapa con ADA4895 sobre la salida estándar del SiPM, con banco de R_F configurable por jumpers (159 Ω – 2,2 kΩ). 5 placas ensambladas en JLCPCB, con el SiPM soldado por reflujo.

### Registro semanal

**Semana del 03/08/2026**
- Setup de medición I-V validado (Keithley 2450 + pyvisa + script Python)
- Protocolo de conexión y seguridad definido 

**Semana del 10/08/2026**
- Caracterización I-V de los 10 SiPMs completada 
- Se confirmó offset de V_br entre lotes (~141 mV) 
- **→ Hito 1 alcanzado**

**Semana del 17/08/2026**
- Primer diseño en KiCad: placa breakout para el SiPM (fresada en CNC)

**Semana del 24/08/2026**
- Corriente oscura de los 10 SiPMs a V_ov = 2,5 V
- Plan del banco térmico (Peltier + watercooling + DS18B20)
- SiPM #05 destruido al soldarlo → protocolo de soldadura (≤ 260 °C, ≤ 10 s)

**Semana del 31/08/2026**
- Demostrado que el 60035 no se puede leer sin amplificación (3400 pF → ~0,14 mV/PE)

**Semana del 07/09/2026**
- Pulsos de fotón individual con la placa BGA614 ×100
- **→ Hito 2 alcanzado**

**Semana del 14/09/2026**
- Arduino + DS18B20 validado; Peltier nueva probada
- Comparación de topologías de amplificación (BGA614, TIA, amplificador inversor)

**Semana del 21/09/2026**
- Simulación del TIA de una etapa (ADA4895, Configuración C) y definición del banco de R_F

**Semanas del 05/10 y 12/10/2026**
- Diseño de la EVB-TIA v0 en KiCad: esquemático, layout, plano de masa, serigrafía (DRC 0/0/0)

**Semana del 19/10/2026**
- Archivos de fabricación y pedido a JLCPCB
- **→ Hito 3 alcanzado**

**Semana del 26/10/2026** *(próxima)*
- Banco térmico: reparar el conmutador de la Peltier y medir dV_br/dT
- Preparar la cadena de medición para la EVB-TIA (adquisición con osciloscopio, análisis de SPE)

---

## Convenciones

**Datos:** `{modelo}_{numero}_{YYYYMMDD}.csv`<br>
**Logs:** `N LOG — Día D de mes de AAAA.md`<br>
**Dispositivos:** `MFC60035_XX` (numeración secuencial por orden de medición)

---

## Instrumentación

| Equipo              | Modelo                                      | Interfaz              |
| ------------------- | ------------------------------------------- | --------------------- |
| Source Measure Unit | Keithley 2450                               | USB / SCPI vía PyVISA |
| Osciloscopio        | Keysight InfiniiVision DSOX3104T (1 GHz)    | —                     |
| Osciloscopio        | Rigol DS1204B (200 MHz)                     | —                     |
| Sensor de temperatura | DS18B20 + Arduino UNO                     | 1-Wire / serial       |
| Celda Peltier       | TEC1-12706                                  | —                     |
| SiPMs bajo prueba   | onsemi MicroFC-60035-SMT (C-Series, 6×6 mm) | —                     |

---

## Dependencias

* Python 3.11+
* PyVISA + backend pyvisa-py
* NumPy, Matplotlib, SciPy
* Arduino IDE: librerías OneWire y DallasTemperature
* KiCad 10 (diseño de PCB) y LTspice (simulación)

---

###  Casualties:

**Componentes destruidos:** `1`  
**Días sin quemar algo:** `56`

> 🫡 


---

## Documentación relacionada

* Torletti (2025). *Gamma Tracker: instrumentación para la detección de radiación gamma en cirugía laparoscópica.* Instituto Balseiro.
* Knoll (2010). *Radiation Detection and Measurement.* 4th ed., Wiley.
* onsemi. *C-Series SiPM Datasheet* — MicroFC-60035-SMT.
* onsemi. *AND9782/D — Biasing and Readout of onsemi SiPM Sensors.*
* onsemi. *AND9788/D — Handling and Soldering of Molded Leadframe Packaged SiPM Sensors.*
* Analog Devices. *ADA4895-1/-2 Data Sheet.*
* Keithley. *Model 2450 SourceMeter SMU — Reference Manual.*
