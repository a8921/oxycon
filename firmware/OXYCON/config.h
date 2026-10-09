/*
 * config.h — OXYCON tunable parameters
 *
 * Edit this file to adapt the firmware to different compressor / zeolite
 * column combinations without touching the main logic in OXYCON.ino.
 *
 * After changing any value, re-upload the sketch and let the machine run
 * for 5–10 minutes before evaluating O2 purity.
 */

#pragma once

// ── PSA timing ────────────────────────────────────────────────────────────────
// ADSORB_MS: how long each column adsorbs nitrogen per half-cycle.
//   Too short → nitrogen breakthrough, low purity.
//   Too long  → zeolite saturates, productivity drops.
//   Starting point: 5–8 s for a 5 LPM compressor + ~500 g zeolite/column.
#define ADSORB_MS         6000UL   // ms

// EQUALISE_MS: pressure equalisation between columns.
//   Shorter = less energy recovery; longer = dead time.
//   300–700 ms is typical for small PSA units.
#define EQUALISE_MS        500UL   // ms

// ── Compressor / flow parameters (informational — not used in timing logic) ──
#define COMPRESSOR_LPM       5.0f  // compressor rated flow, litres per minute
#define ZEOLITE_MASS_G     500.0f  // zeolite mass per column, grams

// ── MQ-135 sensor calibration ─────────────────────────────────────────────────
// Run firmware/tools/calibrate_sensor.ino to determine MQ135_R0 for YOUR sensor
// in clean ambient air. The default is approximate.
#define MQ135_R0            76.63f  // sensor resistance in clean air (kΩ)
#define MQ135_RL            10.0f   // load resistor on your breakout board (kΩ)

// ADC reference — 5.0 V for Uno; change to 3.3 if running on a 3.3 V board
#define ADC_VREF             5.0f
#define ADC_STEPS         1023.0f

// Number of ADC samples averaged each reading (higher = less noise, more latency)
#define MQ135_SAMPLES          10

// ── O2 mapping coefficients ───────────────────────────────────────────────────
// Linear model:  o2_pct = O2_AMBIENT + (1 - Rs/R0) * O2_SCALE
// Calibrate by measuring at a known O2% (e.g. ambient 20.9%) and at the
// concentrator output (typically 90–95% for a well-tuned PSA).
#define O2_AMBIENT          20.9f   // % O2 in ambient air
#define O2_SCALE            95.0f   // full-range scaling factor

// ── Alarm thresholds ──────────────────────────────────────────────────────────
// O2_MIN_ALARM: buzzer triggers below this value.
//   Ambient air is 20.9 %.  A working PSA should produce > 85–93 %.
//   Set low (30 %) to alarm only on sensor failure / system fault.
#define O2_MIN_ALARM        30.0f   // %

// O2_MAX_DISPLAY: cap displayed value to avoid >100% artifacts from noise
#define O2_MAX_DISPLAY      99.0f   // %

// ── Hardware pin assignments ──────────────────────────────────────────────────
// Change only if you rewire the board.
#define PIN_MQ135           A0
#define PIN_V1               4   // Column A inlet solenoid
#define PIN_V2               5   // Column B inlet solenoid
#define PIN_V3               6   // Equalisation / purge solenoid
#define PIN_BUZZER           7

// ── LCD ───────────────────────────────────────────────────────────────────────
// I2C address: 0x27 for PCF8574-based backpacks; 0x3F for some alternatives.
// Run an I2C scanner sketch if unsure.
#define LCD_I2C_ADDR        0x27
#define LCD_COLS              16
#define LCD_ROWS               2

// LCD refresh period (ms) — set to 0 to update every loop iteration (noisy)
#define LCD_UPDATE_MS       1000UL

// ── Serial logging ────────────────────────────────────────────────────────────
#define SERIAL_BAUD         9600
