
## Sesión de laboratorio: Validación del sistema Arduino + DS18B20 y prueba de Peltier

### Objetivo

Validar la cadena de medición de temperatura (Arduino UNO + DS18B20) y comenzar la integración con la Peltier TEC1-12706.

---

### Resultados

#### 1. Instalación de librerías Arduino

- Se instalaron las librerías **OneWire** (Paul Stoffregen) y **DallasTemperature** (Miles Burton) en el Arduino IDE.

#### 2. Armado del circuito en breadboard

- Se montó el circuito del DS18B20 de forma ordenada en una breadboard:
    - DS18B20 (TO-92) ya estaba pegado con pasta térmica a la superficie de la Peltier.
    - Tres cables del sensor: rojo (VCC) → riel +, negro (GND) → riel −, verde (DATA) → fila 10.
    - Resistor pullup de 4.7 kΩ entre la línea de datos (fila 10) y el riel + (5V).
    - Jumper desde pin 2 del Arduino a la fila de datos.
    - Alimentación de la breadboard desde Arduino: 5V → riel +, GND → riel −.

#### 3. Detección del sensor (PeltierV01.ino)

- **Resultado:** `DeviceCount: 1`
- **Dirección:** `0x28 0xFF 0xB1 0x49 0x01 0x17 0x05 0xAF`
- **Resolución:** 12 bits (0.0625 °C)
- Nota: el primer intento dio `DeviceCount: 0` porque faltaba el resistor pullup de 4.7 kΩ.

#### 4. Lectura de temperatura ambiente (TempPIDPWM_V01.ino)

- Temperatura ambiente medida: **~19.125 °C** — consistente y estable.
- Se verificó respuesta térmica tocando el sensor con el dedo → la temperatura subió varios grados.
- Salida PID: valores negativos crecientes (integral windup) y PWM clavado en 255 — comportamiento esperado sin Peltier alimentada (setpoint = 10 °C < T_ambiente).
- Columnas de salida serial: `tiempo(s) tempC pidOutput PWM`

#### 5. Prueba de la Peltier TEC1-12706

- Se consiguió una **fuente programable** (reemplaza la ATX para alimentación de la Peltier).
- Se dispone de un **cooler Foxconn 364409-001 rev.d** como disipador alternativo (más simple que el watercooling AIO) para pruebas iniciales.
- **Peltier original:** medición de continuidad dio **1.2 MΩ** → circuito abierto, **celda quemada**. Se reemplazó.
- **Peltier nueva:** funciona correctamente conectada directamente a la fuente programable.
- **Circuito conmutador MOSFET (IRFZ44N):** la Peltier **no funciona** a través del circuito conmutador. Se aisló el problema al circuito. Pendiente: revisar soldaduras y componentes, posiblemente rearmar.

---

### Problemas identificados

|Problema|Estado|Acción|
|---|---|---|
|Falta de pullup 4.7 kΩ en bus 1-Wire|**Resuelto**|Se conectó el resistor en breadboard|
|Peltier original quemada (circuito abierto)|**Resuelto**|Reemplazada por unidad nueva|
|Circuito conmutador MOSFET no funciona|**Pendiente**|Revisar con multímetro (modo diodo en IRFZ44N), verificar soldaduras, posiblemente rearmar|
|Integral windup en PID|**Conocido**|Corregir en versión futura del sketch|

### Hardware verificado

- ✅ Arduino UNO — funcional
- ✅ DS18B20 (TO-92) — detectado, lectura correcta, 12 bits
- ✅ Breadboard con pullup 4.7 kΩ — funcionando
- ✅ Peltier TEC1-12706 (nueva) — funcional (test directo con fuente)
- ✅ Fuente programable — operativa
- ❌ Circuito conmutador MOSFET (IRFZ44N en perfboard) — no funciona, pendiente diagnóstico

### Componentes del circuito conmutador (por foto)

- IRFZ44N (TO-220) con disipador de aluminio
- LED transparente (indicador)
- 2 resistencias (valores por identificar)
- 1 diodo (por identificar — posible flyback)
- Bornera azul de 4 terminales (conexión de potencia)
- Conector dupont de 2 pines (señal desde Arduino)
- Perfboard con soldaduras punto a punto

### Pinout IRFZ44N (referencia para diagnóstico)

Con la etiqueta de frente y patas hacia abajo: G (izq) — D (centro) — S (der). Tab metálica = Drain. Test modo diodo: punta roja en Source, negra en Drain → debe dar 0.3–0.7 V. Invertido → OL.

---

### Próximos pasos

1. Diagnosticar y reparar (o rearmar) el circuito conmutador MOSFET
2. Probar el sistema completo: Arduino → MOSFET → Peltier con cooler Foxconn
3. Verificar control PID con enfriamiento real
4. Eventualmente migrar al sistema de watercooling AIO para mejor capacidad de disipación