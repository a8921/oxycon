# PSA Theory — Pressure Swing Adsorption for O2 Concentration
**IIT Bhilai | Ashish Devadas**

---

## What PSA Does

Pressure Swing Adsorption separates nitrogen from air using a zeolite
molecular sieve (type 13X or LiX). Zeolite preferentially adsorbs nitrogen
under pressure. When the pressure is released, the nitrogen desorbs and
vents to atmosphere, regenerating the bed. By alternating two columns —
one adsorbing while the other regenerates — the system produces a
near-continuous stream of oxygen-enriched air.

**Typical output:** 90–95% O₂ at 1–5 LPM for a small two-column unit.

---

## The 4-Phase Cycle

OXYCON uses a simplified 3-valve, 2-column PSA cycle with an equalisation
step for energy recovery.

### Phase 1 — Column A Adsorbs (ADSORB_MS = 6 s)

```
Compressed air → V1 open → Column A
                            (zeolite traps N₂ under pressure)
                            → O₂ exits product port

Column B vents to atmosphere (N₂ desorbs from zeolite → regenerated)
V2 closed, V3 closed
```

### Phase 2 — Pressure Equalisation (EQUALISE_MS = 500 ms)

```
V1, V2 closed
V3 open → connects Col A (high pressure) to Col B (low pressure)

Purpose:
  • Recovers compressed-air energy — raises Col B pressure without
    running the compressor.
  • Reduces the pressure shock on the zeolite beds, extending their life.
  • Partially re-pressurises Col B before adsorption begins.
```

### Phase 3 — Column B Adsorbs (ADSORB_MS = 6 s)

Mirror of Phase 1 with columns swapped.

```
Compressed air → V2 open → Column B
V1 closed — Column A vents and regenerates
V3 closed
```

### Phase 4 — Pressure Equalisation (EQUALISE_MS = 500 ms)

Same as Phase 2 — connects the now high-pressure Col B to the
regenerated Col A before the next A-adsorption phase.

---

## Cycle Timing

| Phase | Duration | % of cycle |
|-------|----------|-----------|
| A_ADSORB | 6000 ms | 46.2 % |
| EQ1      |  500 ms |  3.8 % |
| B_ADSORB | 6000 ms | 46.2 % |
| EQ2      |  500 ms |  3.8 % |
| **Total** | **13 000 ms** | **100 %** |

Cycle time = **13 seconds** at default settings.

---

## Tuning Guidelines

### Adjusting ADSORB_MS

The adsorption phase length is the primary tuning parameter.

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| O₂ purity < 85% | Phase too short (nitrogen breakthrough) | Increase ADSORB_MS |
| Low flow rate / product volume | Phase too long (zeolite saturated early) | Decrease ADSORB_MS |
| Purity good but drops after long run | Zeolite regeneration incomplete | Decrease ADSORB_MS to shorten half-cycle |

**Starting point:** 5–8 s for a 5 LPM compressor with ~500 g zeolite per column.

### Adjusting EQUALISE_MS

- Shorter → less pressure recovery, more compressor work
- Longer → dead time, lower product flow
- 300–700 ms is typical; 500 ms is a reasonable default

### Zeolite Selection

- **13X (NaX):** Common, good for N₂ / O₂ separation, lower cost
- **LiX (Li-13X):** Higher selectivity, produces higher O₂ purity
- **5A:** Also used but less selective for O₂ concentration

---

## MQ-135 as an O₂ Proxy

The MQ-135 is not an O₂ sensor. It is a metal oxide semiconductor (MOS)
sensor that responds to CO₂, NH₃, benzene, alcohol, and smoke.

**Why it works here (approximately):**

In a PSA concentrator, the enriched O₂ stream has:
- Lower N₂ (removed by zeolite)
- Much lower CO₂ and trace VOCs (adsorbed by zeolite along with N₂)

The MQ-135 resistance rises in gas streams with fewer reducible interfering
gases. Inside a PSA output line, higher O₂ purity correlates with higher
sensor resistance (lower Rs/R0 ratio).

**The firmware maps:**
```
o2_pct = 20.9 + (1 - Rs/R0) × 95
```

This is a linear approximation only. For clinical-grade measurement, use
a dedicated electrochemical O₂ sensor such as the **KE-25** (Figaro) or
**ME2-O2** (Winsen).

---

## References

1. Ruthven, D. M. (1984). *Principles of Adsorption and Adsorption Processes*. Wiley.
2. Yang, R. T. (1997). *Gas Separation by Adsorption Processes*. Imperial College Press.
3. Vemula, R. R., et al. (2018). "Simulation of a 2-bed PSA process for oxygen production from air." *Separation and Purification Technology*, 197, 339–353.
