# Wiring Guide — OXYCON PSA Oxygen Concentrator
**IIT Bhilai | Ashish Devadas**

---

## Components

| Component | Quantity | Purpose |
|-----------|----------|---------|
| Arduino Uno (Rev3) | 1 | Main controller |
| MQ-135 gas sensor | 1 | O2 purity approximation |
| 5V relay module (or MOSFET driver) | 3 | Drive 12 V solenoid valves |
| 12 V solenoid valve (N.C.) | 3 | V1 (col A inlet), V2 (col B inlet), V3 (equalise) |
| 16×2 LCD with PCF8574 I2C backpack | 1 | Display |
| Buzzer (5 V passive) | 1 | Low-O2 alarm (optional) |
| 12 V DC power supply | 1 | Solenoids |
| 5 V USB or barrel jack | 1 | Arduino |

---

## Arduino Pin Assignments

| Signal | Arduino Pin | Notes |
|--------|-------------|-------|
| MQ-135 AO | A0 | Analog input |
| V1 relay IN | D4 | Column A inlet — active HIGH |
| V2 relay IN | D5 | Column B inlet — active HIGH |
| V3 relay IN | D6 | Equalisation / purge — active HIGH |
| Buzzer | D7 | Active HIGH; omit if not used |
| LCD SDA | A4 | I2C data |
| LCD SCL | A5 | I2C clock |

---

## MQ-135 Wiring

```
MQ-135 VCC  ──── 5 V (Arduino)
MQ-135 GND  ──── GND
MQ-135 AO   ──── A0 (Arduino)
MQ-135 DO   ──── not connected (digital threshold output, unused)
```

The MQ-135 breakout board includes a 10 kΩ load resistor between AO and GND.
If your breakout does not, add one externally. Update `config.h → MQ135_RL`
to match your actual load resistor value.

**Warm-up:** The firmware waits 20 seconds after power-on for the sensor to
stabilise. Do not take readings before then.

---

## Solenoid Valve Wiring (via relay module)

Each valve is a 12 V N.C. (normally-closed) solenoid. The relay sits
between the Arduino's 5 V logic and the 12 V coil.

```
Arduino D4/D5/D6 ──── Relay IN pin
Arduino 5V       ──── Relay VCC
Arduino GND      ──── Relay GND

12 V supply (+) ──── Relay COM
Relay NO        ──── Solenoid coil (+)
Solenoid coil (–) ── 12 V supply (–) / GND
```

> **Active-LOW relay modules:** Some relay boards energise on LOW.
> If your valves open when the Arduino pin is LOW, add `!` to the
> `setValves()` calls in `OXYCON.ino`, or swap to:
> ```cpp
> digitalWrite(PIN_V1, v1 ? LOW : HIGH);
> ```

**Flyback protection:** Most relay module boards include a flyback diode.
If using bare MOSFETs, add a 1N4007 across the solenoid coil (cathode to +12 V).

---

## LCD (16×2, PCF8574 I2C backpack)

```
LCD SDA ──── A4 (Arduino SDA)
LCD SCL ──── A5 (Arduino SCL)
LCD VCC ──── 5 V
LCD GND ──── GND
```

Default I2C address is `0x27`. If the display is blank, try `0x3F`.
Update `config.h → LCD_I2C_ADDR` to match.

To scan for the actual address, upload any I2C scanner sketch before flashing OXYCON.

---

## PSA Plumbing (pneumatic schematic)

```
   Compressor output
         │
    ┌────┴────┐
    │         │
   [V1]      [V2]        ← inlet valves (Arduino D4, D5)
    │         │
 Column A   Column B      ← zeolite molecular sieve beds
 (adsorbs)  (regenerates)
    │         │
    └────┬────┘
         │
        [V3]              ← equalisation / purge valve (Arduino D6)
         │
      (vent / product O2 output)
```

**Valve logic per phase:**

| Phase | V1 (ColA inlet) | V2 (ColB inlet) | V3 (Equalise) | What happens |
|-------|:-:|:-:|:-:|---|
| A_ADSORB | ON  | OFF | OFF | Air → Col A; Col A adsorbs N₂; O₂ exits product port |
| EQ1      | OFF | OFF | ON  | Columns equilibrate pressure |
| B_ADSORB | OFF | ON  | OFF | Air → Col B; Col B adsorbs N₂; O₂ exits product port |
| EQ2      | OFF | OFF | ON  | Columns equilibrate pressure again |

---

## Notes

1. **Power supply isolation:** Keep the 12 V solenoid circuit and the Arduino 5 V circuit on separate grounds, joined only at a single common point, to avoid noise on the analog MQ-135 reading.
2. **MQ-135 placement:** Mount the sensor on the O2 product outlet line, not inside the zeolite chamber.
3. **I2C pull-ups:** The PCF8574 backpack board includes 4.7 kΩ pull-ups on SDA/SCL. No additional resistors needed.
4. **Buzzer:** A 5 V passive buzzer (piezo) works directly on D7. For a louder alarm, drive it through a transistor.
