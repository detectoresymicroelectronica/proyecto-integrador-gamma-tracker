 
## Objetivo del día

Puesta en marcha del setup de medición de curvas I-V para caracterización de nuevos SiPMs candidatos a upgrade del Gamma Tracker, usando Keithley 2450 SMU controlado por Python.

---

## Contexto del proyecto

- El proyecto Gamma Tracker (tesis de Lara Torletti, TRL 5) demostró la viabilidad de un detector gamma basado en centellador + SiPM para cirugía laparoscópica.

- El nuevo PI propone evaluar SiPMs de mayor área activa y menor tensión de polarización para mejorar resolución espectral y discriminación energética.

- **Tarea inmediata:** levantar curvas I-V para caracterizar nuevos SiPMs candidatos y comparar con los utilizados anteriormente.
  

---

## Trabajo realizado

### 1. Setup de software

- Entorno: **Anaconda (base)**, Python 3.11.5, Windows.

- Librerías instaladas: `pyvisa`, `pyvisa-py`, `pyusb`, `matplotlib`, `numpy`.

- Backend VISA: `pyvisa-py` (puro Python, no requiere NI-VISA).

- **Driver USB:** fue necesario instalar el driver **libusb-win32** mediante la herramienta **Zadig** (https://zadig.akeo.ie/) para que Windows exponga el Keithley como dispositivo USBTMC accesible desde Python.

### 2. Conexión con el instrumento

- **Instrumento:** Keithley 2450 SourceMeter SMU.

- **Serial:** 04302182 | **Firmware:** 1.6.1a

- **Conexión:** USB Type-B (puerto trasero "USB Device") → USB Type-A (notebook).

- **Resource string VISA:** `USB0::1510::9296::04302182::0::INSTR`

- La configuración USB del instrumento no tiene parámetros ajustables (el mensaje "no settings available for USB" en pantalla es normal).

- Verificación exitosa con script.

  
### 3. Script de medición I-V (`iv_curve_sipm.py`)

- Desarrollado en Python, control SCPI vía PyVISA.

- Funcionalidades: barrido de voltaje punto a punto, medición de corriente, gráfico en tiempo real (matplotlib), guardado automático de CSV + PNG con metadata.

- **Configuración del instrumento por SCPI:**

  - Fuente: voltaje | Medición: corriente

  - Terminales: frontales (banana jacks)

  - Sensing: 2-wire

  - NPLC configurable (default: 1.0)

- Protección: compliance de corriente configurable; la salida se apaga automáticamente al finalizar, ante error, o con Ctrl+C.

- Archivos de salida en carpeta `datos_iv/`, nombrados como `IV_{SAMPLE_ID}_{timestamp}.csv/.png`.

  

### 4. Bug corregido durante la puesta en marcha

- **Problema:** la corriente medida se clavaba siempre en ~0.015 V (valor sin sentido).

- **Causa:** el comando `:MEAS:VOLT?` reconfigura internamente la función de sensado del instrumento de corriente a voltaje, rompiendo la medición.

- **Solución:** reemplazar `:MEAS:CURR?` + `:MEAS:VOLT?` por `:READ?` (toma lectura sin reconfigurar) y usar el voltaje seteado como valor de voltaje (error de source del 2450 es <0.02%).

### 5. Validación con resistencia

- Se midió una resistencia como validación del setup antes de conectar un SiPM.

- **Parámetros de la medición:**

  - Barrido: 0 V → 60 V, paso 1 V

  - Compliance: ~340 µA (estimado del gráfico)

  - SAMPLE_ID: `SiPM_nuevo_01` (nombre provisional, era la resistencia de validación)

- **Resultado:** curva I-V lineal hasta ~35 V donde se alcanza el compliance y se aplana. Comportamiento óhmico verificado correctamente.

- Gráfico y CSV guardados exitosamente.

  

---
> [!NOTE] > Acá se puso en marcha el entorno de medición que se usa en todos los scripts que utilizan el Keithley 2450.
## Entorno de ejecución validado

| Componente | Detalle |
|---|---|
| Python | 3.11.5 (Anaconda base) |
| Ejecución | Anaconda Prompt → `python iv_curve_sipm.py` |
| Editor | VS Code (solo edición, no ejecución) |
| OS | Windows |
| Instrumento | Keithley 2450, FW 1.6.1a, USB |
| Driver USB | libusb-win32 (instalado con Zadig) |

---

## Decisiones técnicas

- **Backend pyvisa-py:** evita dependencia de NI-VISA (que requiere cuenta institucional para descargar).

- **Compliance conservador para SiPMs:** se definió una estrategia escalonada: 10 µA (exploratoria) → 100 µA (fina) → 1 mA (solo con datasheet).


---

## Pendientes

- [x] Confirmar con el director el modelo de SiPM a medir y obtener datasheet

- [x] Definir rangos seguros de voltaje y compliance para el SiPM específico

- [x] Realizar medición exploratoria del SiPM (compliance 10 µA)

- [x] Medición fina en la zona de breakdown

- [x] Medir en oscuridad (cubrir el SiPM para evitar fotocorriente)

- [x] Renombrar SAMPLE_ID correctamente para cada detector

- [x] Evaluar si es necesario medir a distintas **temperaturas**


---
