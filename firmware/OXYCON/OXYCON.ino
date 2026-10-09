/*
 * OXYCON — PSA Oxygen Concentrator Controller
 * IIT Bhilai | Ashish Devadas
 *
 * Hardware:
 *   - Arduino Uno
 *   - MQ-135 gas sensor (O2 purity approximation via analog read)
 *   - 3× solenoid valves (V1, V2, V3) — 12V, driven via MOSFET/relay
 *   - 2× zeolite columns (A, B) — alternating adsorption/desorption
 *   - 16×2 I2C LCD (PCF8574 backpack, addr 0x27)
 *   - Buzzer (optional alarm)
 *
 * PSA Cycle (3-valve, 2-column):
 *   V1 — inlet valve for column A   (D4)
 *   V2 — inlet valve for column B   (D5)
 *   V3 — equalisation / purge valve  (D6)
 *
 *   Phase 1 — Column A adsorbs, column B regenerates:
 *     V1 ON  (compressed air → column A)
 *     V2 OFF (column B vents to atmosphere)
 *     V3 OFF
 *
 *   Phase 2 — Equalisation (pressure balance between columns):
 *     V1 OFF, V2 OFF, V3 ON
 *
 *   Phase 3 — Column B adsorbs, column A regenerates:
 *     V1 OFF
 *     V2 ON  (compressed air → column B)
 *     V3 OFF
 *
 *   Phase 4 — Equalisation again:
 *     V1 OFF, V2 OFF, V3 ON
 *
 * Connections:
 *   MQ-135 AO  → A0
 *   V1 relay   → D4
 *   V2 relay   → D5
 *   V3 relay   → D6
 *   Buzzer     → D7  (optional)
 *   LCD SDA    → A4
 *   LCD SCL    → A5
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "config.h"

// ── LCD ───────────────────────────────────────────────────────────────────────
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);

// ── State machine ──────────────────────────────────────────────────────────────
enum Phase { PHASE_A_ADSORB, PHASE_EQ1, PHASE_B_ADSORB, PHASE_EQ2 };
Phase        currentPhase     = PHASE_A_ADSORB;
unsigned long phaseStartMs    = 0;
unsigned long lastLcdUpdateMs = 0;
uint32_t      cycleCount      = 0;

// ── Forward declarations ───────────────────────────────────────────────────────
void setValves(bool v1, bool v2, bool v3);
float readO2Pct();
void  updateLCD(float o2Pct);
void  alarmBuzzer(bool on);
void  nextPhase();
unsigned long phaseDuration(Phase p);


// ═══════════════════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(9600);

    pinMode(PIN_V1,     OUTPUT);
    pinMode(PIN_V2,     OUTPUT);
    pinMode(PIN_V3,     OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);

    // Safe state — all valves off
    setValves(false, false, false);

    // LCD init
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0); lcd.print("  OXYCON v1.0   ");
    lcd.setCursor(0, 1); lcd.print(" IIT Bhilai     ");
    delay(2000);
    lcd.clear();

    // MQ135 warm-up
    lcd.setCursor(0, 0); lcd.print("Sensor warm-up  ");
    lcd.setCursor(0, 1); lcd.print("Please wait...  ");
    Serial.println(F("OXYCON PSA Controller starting..."));
    Serial.println(F("Warming up MQ-135 (20 s)"));
    delay(20000UL);   // MQ-135 needs ~20 s preheat for stable readings
    lcd.clear();

    // Start first phase
    phaseStartMs = millis();
    applyPhase(currentPhase);

    Serial.println(F("PSA cycle started."));
    Serial.println(F("time_ms,phase,V1,V2,V3,o2_pct,cycle"));
}


// ═══════════════════════════════════════════════════════════════════════════════
void loop() {
    unsigned long now = millis();

    // ── Phase transition ───────────────────────────────────────────────────────
    if (now - phaseStartMs >= phaseDuration(currentPhase)) {
        nextPhase();
        phaseStartMs = now;
        applyPhase(currentPhase);
    }

    // ── Sensor read + display (throttled) ─────────────────────────────────────
    if (now - lastLcdUpdateMs >= LCD_UPDATE_MS) {
        lastLcdUpdateMs = now;
        float o2 = readO2Pct();
        updateLCD(o2);
        logSerial(now, o2);

        // Low O2 alarm (should never trigger if PSA working — it produces >90%)
        if (o2 < O2_MIN_ALARM) {
            alarmBuzzer(true);
        } else {
            alarmBuzzer(false);
        }
    }
}


// ── Phase helpers ──────────────────────────────────────────────────────────────
void applyPhase(Phase p) {
    switch (p) {
        case PHASE_A_ADSORB: setValves(true,  false, false); break;
        case PHASE_EQ1:      setValves(false, false, true);  break;
        case PHASE_B_ADSORB: setValves(false, true,  false); break;
        case PHASE_EQ2:      setValves(false, false, true);  break;
    }
}

void nextPhase() {
    switch (currentPhase) {
        case PHASE_A_ADSORB: currentPhase = PHASE_EQ1;      break;
        case PHASE_EQ1:      currentPhase = PHASE_B_ADSORB; break;
        case PHASE_B_ADSORB: currentPhase = PHASE_EQ2;      break;
        case PHASE_EQ2:
            currentPhase = PHASE_A_ADSORB;
            cycleCount++;
            break;
    }
}

unsigned long phaseDuration(Phase p) {
    return (p == PHASE_EQ1 || p == PHASE_EQ2) ? EQUALISE_MS : ADSORB_MS;
}


// ── Valve control ─────────────────────────────────────────────────────────────
// Valves are active-HIGH (relay module IN pin = HIGH → relay energised → valve open).
// Change to LOW if your relay board is active-low.
void setValves(bool v1, bool v2, bool v3) {
    digitalWrite(PIN_V1, v1 ? HIGH : LOW);
    digitalWrite(PIN_V2, v2 ? HIGH : LOW);
    digitalWrite(PIN_V3, v3 ? HIGH : LOW);
}


// ── MQ-135 O2 approximation ───────────────────────────────────────────────────
/*
 * NOTE ON MQ-135 FOR O2 MEASUREMENT:
 * The MQ-135 is not an O2 sensor — it detects CO2, NH3, benzene, etc.
 * In a PSA concentrator, the enriched O2 stream contains fewer interfering
 * gases (mainly N2 removed), so the MQ-135 resistance rises with O2 purity.
 * This gives a rough RELATIVE measurement, not an absolute % reading.
 * For clinical-grade accuracy, use a dedicated O2 sensor (e.g. KE-25, ME2-O2).
 *
 * Calibration:
 *   1. Expose sensor to ambient air (20.9% O2) — read raw ADC → compute R0
 *   2. Map R0 ratio to O2% using empirical curve (see calibrate_sensor.ino)
 */
float readO2Pct() {
    // Average MQ135_SAMPLES readings to reduce noise
    long sum = 0;
    for (int i = 0; i < MQ135_SAMPLES; i++) {
        sum += analogRead(PIN_MQ135);
        delay(2);
    }
    float adcVal = sum / (float)MQ135_SAMPLES;

    // Convert ADC to sensor resistance
    float vSensor = adcVal * (ADC_VREF / ADC_STEPS);
    if (vSensor < 0.01f) vSensor = 0.01f;   // avoid divide-by-zero
    float rSensor = MQ135_RL * (ADC_VREF - vSensor) / vSensor;

    // Rs/R0 ratio — in clean air this is ~1.0, in enriched O2 it drops
    float ratio = rSensor / MQ135_R0;

    // Empirical mapping: ratio 1.0 → O2_AMBIENT (20.9%), ratio ~0.3 → ~95%
    // Linear model — run calibrate_sensor.ino for a curve fit to your sensor
    float o2 = O2_AMBIENT + (1.0f - ratio) * O2_SCALE;
    o2 = constrain(o2, 0.0f, O2_MAX_DISPLAY);
    return o2;
}


// ── LCD display ───────────────────────────────────────────────────────────────
void updateLCD(float o2Pct) {
    // Line 0: O2 purity
    lcd.setCursor(0, 0);
    lcd.print("O2: ");
    if (o2Pct < 10.0f) lcd.print(" ");
    lcd.print(o2Pct, 1);
    lcd.print("%   ");

    // Line 1: phase name + cycle count
    lcd.setCursor(0, 1);
    switch (currentPhase) {
        case PHASE_A_ADSORB: lcd.print("ColA  "); break;
        case PHASE_EQ1:      lcd.print("Eq1   "); break;
        case PHASE_B_ADSORB: lcd.print("ColB  "); break;
        case PHASE_EQ2:      lcd.print("Eq2   "); break;
    }
    lcd.print("Cyc:");
    lcd.print(cycleCount);
    lcd.print("   ");
}


// ── Serial logging (CSV) ──────────────────────────────────────────────────────
void logSerial(unsigned long nowMs, float o2) {
    const char* phaseNames[] = {"A_ADSORB","EQ1","B_ADSORB","EQ2"};
    Serial.print(nowMs);         Serial.print(',');
    Serial.print(phaseNames[currentPhase]); Serial.print(',');
    Serial.print(digitalRead(PIN_V1)); Serial.print(',');
    Serial.print(digitalRead(PIN_V2)); Serial.print(',');
    Serial.print(digitalRead(PIN_V3)); Serial.print(',');
    Serial.print(o2, 2);         Serial.print(',');
    Serial.println(cycleCount);
}


// ── Buzzer ────────────────────────────────────────────────────────────────────
void alarmBuzzer(bool on) {
    digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
}
