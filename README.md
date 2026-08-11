# Gamma Tracker — Sonda gamma para cirugía radioguiada

Sistema de detección de radiación gamma para asistencia en cirugía laparoscópica oncológica, basado en centellador inorgánico acoplado a fotomultiplicador de silicio (SiPM), con electrónica de lectura multicanal e interfaz en tiempo real.

Proyecto Integrador — Ingeniería en Telecomunicaciones — Instituto Balseiro, 2026  
Autor: Dana E. González
Director: José Lipovetzky
Codirector: Fabricio Alcalde

---

## Contexto

Este proyecto continúa y extiende el trabajo de la tesis *Gamma Tracker* (Torletti, 2025), que demostró la viabilidad de una sonda gamma portátil basada en centellador + SiPM para localización de tejido tumoral marcado con FDG (TRL 4–5). El dispositivo se encuentra en proceso de patentamiento ante el INPI.

El presente proyecto integrador busca avanzar hacia un sistema de mayor resolución espacial y espectral, abordando cuatro líneas principales:

- **Nuevo fotosensor:** evaluación de SiPMs de mayor área activa y menor tensión de polarización, con capacidad de espectroscopía de altura de pulso para discriminación energética a 511 keV.
- **Acople óptico:** comparación cuantitativa de técnicas (grasa óptica, adhesivos UV, fibra óptica) para optimizar eficiencia de transferencia de luz y estabilidad mecánica.
- **Sistema multipixel:** diseño de una matriz de centelladores acoplados a un arreglo de SiPMs con lectura multicanal para mapeo espacial de actividad gamma en tiempo real.
- **Electrónica e interfaz:** desarrollo de electrónica de adquisición, comunicación inalámbrica y alimentación por baterías, aptas para entorno quirúrgico (objetivo TRL 5–6).

## Estructura del repositorio

```
logs/               Cuaderno de laboratorio digital (un archivo por sesión)
scripts/
  ├── adquisicion/  Control de instrumentos (Keithley 2450, PyVISA/SCPI)
  └── analisis/     Post-procesamiento, comparación y visualización
data/               Datos experimentales organizados por campaña
  └── <campaña>/
      ├── raw/      CSV crudos (inmutables)
      └── processed/Datos derivados y resúmenes
figures/            Figuras finales para tesis e informes
```

## Convenciones

**Datos:** `IV_{modelo}_{numero}_{YYYYMMDD}.csv`  
**Logs:** `#LOG_YYYY-MM-DD.md`  
**Dispositivos:** `MFC60035_XX` (numeración secuencial por orden de medición)

## Instrumentación

| Equipo | Modelo | Interfaz |
|---|---|---|
| Source Measure Unit | Keithley 2450 | USB / SCPI vía PyVISA |
| SiPMs bajo prueba | onsemi MicroFC-60035-SMT (C-Series, 6×6 mm) | — |

## Dependencias

- Python 3.11+
- PyVISA + backend pyvisa-py
- NumPy, Matplotlib, SciPy

## Documentación relacionada

- Torletti (2025). *Gamma Tracker: instrumentación para la detección de radiación gamma en cirugía laparoscópica.* Instituto Balseiro.
- Knoll (2010). *Radiation Detection and Measurement.* 4th ed., Wiley.
- onsemi. *C-Series SiPM Datasheet* — MicroFC-60035-SMT.
- Keithley. *Model 2450 SourceMeter SMU — Reference Manual.*
