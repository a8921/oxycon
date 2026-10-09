/*
 * calibrate_sensor.ino — MQ-135 R0 calibration for OXYCON
 * IIT Bhilai | Ashish Devadas
 *
 * PURPOSE:
 *   Determine the baseline resistance R0 of your specific MQ-135 sensor
 *   in clean ambient air (20.9 % O2).  Copy the resulting R0 value into
 *   config.h → MQ135_R0.
 *
 * HOW TO USE:
 *   1. Place the sensor in a well-ventilated area away from the concentrator.
 *   2. Power the Arduino and wait for the 60-second warm-up message.
 *   3. Open the Serial Monitor at 9600 baud.
 *   4. After warm-up, the sketch prints 30 Rs/R0 measurements and a final
 *      averaged R0 value.
 *   5. Copy that R0 value into config.h.
 *
 * WIRING:
 *   MQ-135 AO → A0
 *   MQ-135 VCC → 5 V
 *   MQ-135 GND → GND
 *   Load resistor RL = 10 kΩ between A0 and GND (matches config.h MQ135_RL)
 */

#define PIN_MQ135    A0
#define MQ135_RL    10.0f   // load resistor (kΩ) — must match config.h
#define ADC_VREF     5.0f
#define ADC_STEPS 1023.0f
#define SAMPLES       20    // samples averaged per reading
#define READINGS      30    // number of readings to average for R0

// ─────────────────────────────────────────────────────────────────────────────
float readRs() {
    long sum = 0;
    for (int i = 0; i < SAMPLES; i++) {
        sum += analogRead(PIN_MQ135);
        delay(5);
    }
    float adcVal  = sum / (float)SAMPLES;
    float vSensor = adcVal * (ADC_VREF / ADC_STEPS);
    if (vSensor < 0.01f) vSensor = 0.01f;
    return MQ135_RL * (ADC_VREF - vSensor) / vSensor;
}

// ─────────────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);
    Serial.println(F("========================================"));
    Serial.println(F("  OXYCON MQ-135 Calibration Sketch"));
    Serial.println(F("  Place sensor in CLEAN AMBIENT AIR"));
    Serial.println(F("========================================"));
    Serial.println(F("Warming up sensor — 60 seconds..."));

    for (int i = 60; i > 0; i--) {
        Serial.print(F("  "));
        Serial.print(i);
        Serial.println(F(" s remaining"));
        delay(1000);
    }

    Serial.println(F("\nWarm-up complete.  Taking readings...\n"));
    Serial.println(F("Reading#  Rs(kΩ)"));
    Serial.println(F("────────  ───────"));

    double sumR0 = 0.0;
    for (int n = 1; n <= READINGS; n++) {
        float rs = readRs();
        sumR0 += rs;

        Serial.print(F("  "));
        if (n < 10) Serial.print(' ');
        Serial.print(n);
        Serial.print(F("       "));
        Serial.println(rs, 3);

        delay(2000);   // 2 s between readings
    }

    float r0 = (float)(sumR0 / READINGS);

    Serial.println();
    Serial.println(F("========================================"));
    Serial.print(F("  Averaged R0 = "));
    Serial.print(r0, 4);
    Serial.println(F(" kΩ"));
    Serial.println();
    Serial.println(F("  Copy this value into config.h:"));
    Serial.print(F("    #define MQ135_R0   "));
    Serial.print(r0, 2);
    Serial.println(F("f"));
    Serial.println(F("========================================"));
}

void loop() {
    // Nothing — calibration complete; re-run by pressing reset.
}
