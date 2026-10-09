"""
generate_plots.py — Generate media plots for OXYCON README
Run from repo root: python3 tools/generate_plots.py
"""

import os
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

os.makedirs("media", exist_ok=True)

# ── Colour palette ──────────────────────────────────────────────────────────
DARK_BG   = "#0f1117"
CARD_BG   = "#1a1d2e"
ACCENT1   = "#4fc3f7"   # cyan  — O2 purity
ACCENT2   = "#ef5350"   # red   — alarm line
ACCENT3   = "#66bb6a"   # green — cycle boundaries
V1_COL    = "#42a5f5"
V2_COL    = "#ab47bc"
V3_COL    = "#ff7043"
TEXT_COL  = "#e0e0e0"

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor":   CARD_BG,
    "axes.edgecolor":   "#333",
    "axes.labelcolor":  TEXT_COL,
    "xtick.color":      TEXT_COL,
    "ytick.color":      TEXT_COL,
    "text.color":       TEXT_COL,
    "grid.color":       "#2a2d3e",
    "grid.linestyle":   "--",
    "grid.alpha":       0.7,
    "font.family":      "DejaVu Sans",
})


# ════════════════════════════════════════════════════════════════════════════════
# Figure 1 — PSA Cycle Timing Diagram
# ════════════════════════════════════════════════════════════════════════════════

ADSORB_MS   = 6000
EQUALISE_MS = 500
CYCLE_MS    = 2 * ADSORB_MS + 2 * EQUALISE_MS   # 13 000

# Build phase timeline for 3 full cycles
phases  = ["A_ADSORB", "EQ1", "B_ADSORB", "EQ2"]
durs    = [ADSORB_MS, EQUALISE_MS, ADSORB_MS, EQUALISE_MS]
valves  = [
    (True,  False, False),   # A_ADSORB
    (False, False, True),    # EQ1
    (False, True,  False),   # B_ADSORB
    (False, False, True),    # EQ2
]

t = 0
timeline = []
for _ in range(3):
    for i, phase in enumerate(phases):
        timeline.append((t, t + durs[i], phase, valves[i]))
        t += durs[i]
T_total = t / 1000  # seconds

fig, axes = plt.subplots(3, 1, figsize=(12, 6), sharex=True)
fig.suptitle("OXYCON — PSA Cycle Valve States", fontsize=13, color=TEXT_COL, y=0.97)

labels = ["V1 (Col A inlet)", "V2 (Col B inlet)", "V3 (Equalise)"]
colors = [V1_COL, V2_COL, V3_COL]

# Phase background colours
phase_colors = {
    "A_ADSORB": "#1e2a3a",
    "EQ1":      "#2a1e3a",
    "B_ADSORB": "#1e3a2a",
    "EQ2":      "#2a1e3a",
}

for ax_idx, ax in enumerate(axes):
    ax.set_ylim(-0.1, 1.2)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["OFF", "ON"], fontsize=9)
    ax.set_ylabel(labels[ax_idx], color=colors[ax_idx], fontsize=9)
    ax.grid(True, axis='x')

    for t0, t1, phase, v in timeline:
        t0s, t1s = t0 / 1000, t1 / 1000
        # background shading
        ax.axvspan(t0s, t1s, color=phase_colors[phase], alpha=0.5)
        # valve signal
        val = v[ax_idx]
        ax.plot([t0s, t1s], [int(val), int(val)], color=colors[ax_idx], lw=2.5)
        # step down/up at transitions
        if t0 > 0:
            prev_val = timeline[timeline.index((t0, t1, phase, v)) - 1][3][ax_idx]
            ax.plot([t0s, t0s], [int(prev_val), int(val)], color=colors[ax_idx], lw=2.5)

# Phase labels on top axis
for t0, t1, phase, _ in timeline[:4]:
    mid = (t0 + t1) / 2000
    axes[0].text(mid, 1.05, phase.replace("_", "\n"), ha='center', va='bottom',
                 fontsize=7.5, color=TEXT_COL, alpha=0.8)

axes[-1].set_xlabel("Time (s)", color=TEXT_COL)

# Cycle boundary markers
for c in range(1, 4):
    x = c * CYCLE_MS / 1000
    for ax in axes:
        ax.axvline(x, color=ACCENT3, lw=1, ls=':', alpha=0.7)

axes[0].text(0.5, 1.13, "▼ cycle 1", transform=axes[0].get_xaxis_transform(),
             ha='left', fontsize=8, color=ACCENT3, alpha=0.8)

fig.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("media/psa_cycle.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved media/psa_cycle.png")


# ════════════════════════════════════════════════════════════════════════════════
# Figure 2 — Simulated O2 Purity vs Cycle
# ════════════════════════════════════════════════════════════════════════════════

# Simulate O2 build-up over ~120 cycles (26 minutes)
# Model: O2 starts at ambient, rises with a saturation curve, then noise
import random
random.seed(42)

N_CYCLES = 120
cycles = list(range(N_CYCLES))
o2_vals = []
for c in cycles:
    # Saturation model: starts at 20.9%, approaches ~93% asymptotically
    o2_true = 20.9 + (93 - 20.9) * (1 - math.exp(-c / 15))
    noise   = random.gauss(0, 0.8)
    o2_vals.append(min(99, max(0, o2_true + noise)))

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(cycles, o2_vals, color=ACCENT1, lw=1.5, label="O₂ purity (measured)")

# Reference lines
ax.axhline(20.9, color="#888", lw=1, ls='--', alpha=0.7, label="Ambient air (20.9%)")
ax.axhline(90,   color=ACCENT3, lw=1, ls='--', alpha=0.7, label="Target: 90%")
ax.axhline(30,   color=ACCENT2, lw=1, ls='--', alpha=0.8, label="Alarm threshold (30%)")

ax.fill_between(cycles, o2_vals, 20.9, where=[v > 20.9 for v in o2_vals],
                color=ACCENT1, alpha=0.08)

ax.set_xlabel("PSA Cycle Number", fontsize=11)
ax.set_ylabel("O₂ Purity (%)", fontsize=11)
ax.set_title("OXYCON — O₂ Purity Build-up (Simulated)", fontsize=12)
ax.set_ylim(0, 100)
ax.set_xlim(0, N_CYCLES - 1)
ax.legend(fontsize=9, loc='lower right',
          facecolor=CARD_BG, edgecolor="#444", labelcolor=TEXT_COL)
ax.grid(True)

# Annotate peak purity
peak_cycle = max(range(N_CYCLES), key=lambda i: o2_vals[i])
ax.annotate(f"Peak: {o2_vals[peak_cycle]:.1f}%",
            xy=(peak_cycle, o2_vals[peak_cycle]),
            xytext=(peak_cycle - 20, o2_vals[peak_cycle] - 10),
            arrowprops=dict(arrowstyle='->', color=TEXT_COL, lw=1.2),
            fontsize=9, color=TEXT_COL)

fig.tight_layout()
plt.savefig("media/o2_purity.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved media/o2_purity.png")


# ════════════════════════════════════════════════════════════════════════════════
# Figure 3 — Dashboard preview
# ════════════════════════════════════════════════════════════════════════════════

fig = plt.figure(figsize=(12, 7), facecolor=DARK_BG)
gs  = GridSpec(3, 4, figure=fig, hspace=0.55, wspace=0.4)

def stat_card(ax, label, value, unit, color=ACCENT1):
    ax.set_facecolor(CARD_BG)
    for sp in ax.spines.values():
        sp.set_edgecolor("#2a2d3e")
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.5, 0.65, f"{value}", ha='center', va='center',
            fontsize=22, fontweight='bold', color=color, transform=ax.transAxes)
    ax.text(0.5, 0.28, unit, ha='center', va='center',
            fontsize=10, color=color, alpha=0.8, transform=ax.transAxes)
    ax.text(0.5, 0.08, label, ha='center', va='center',
            fontsize=8.5, color=TEXT_COL, alpha=0.65, transform=ax.transAxes)

# Stat cards — top row
ax0 = fig.add_subplot(gs[0, 0]); stat_card(ax0, "O₂ Purity",    "92.4",  "%", ACCENT1)
ax1 = fig.add_subplot(gs[0, 1]); stat_card(ax1, "Phase",        "ColA",  "",  V1_COL)
ax2 = fig.add_subplot(gs[0, 2]); stat_card(ax2, "Cycle Count",  "218",   "",  "#ffa726")
ax3 = fig.add_subplot(gs[0, 3]); stat_card(ax3, "Uptime",       "47m",   "",  "#ab47bc")

# O2 purity trend chart
ax_o2 = fig.add_subplot(gs[1, :2])
recent = o2_vals[-60:]
ax_o2.plot(recent, color=ACCENT1, lw=1.8)
ax_o2.axhline(90, color=ACCENT3, lw=0.8, ls='--', alpha=0.7)
ax_o2.set_title("O₂ Purity (last 60 cycles)", fontsize=9, color=TEXT_COL, pad=4)
ax_o2.set_ylabel("%", fontsize=8)
ax_o2.set_ylim(60, 100)
ax_o2.grid(True)

# Valve state chart
ax_valve = fig.add_subplot(gs[1, 2:])
valve_states = []
phase_seq = ["A_ADSORB", "EQ1", "B_ADSORB", "EQ2"]
vmap = {
    "A_ADSORB": (1, 0, 0),
    "EQ1":      (0, 0, 1),
    "B_ADSORB": (0, 1, 0),
    "EQ2":      (0, 0, 1),
}
for i in range(20):
    p = phase_seq[i % 4]
    valve_states.append(vmap[p])
v1s = [v[0] for v in valve_states]
v2s = [v[1] for v in valve_states]
v3s = [v[2] for v in valve_states]
x   = list(range(20))
ax_valve.step(x, [v + 2.2 for v in v1s], color=V1_COL, lw=1.5, where='post', label='V1')
ax_valve.step(x, [v + 1.1 for v in v2s], color=V2_COL, lw=1.5, where='post', label='V2')
ax_valve.step(x, v3s,                     color=V3_COL, lw=1.5, where='post', label='V3')
ax_valve.set_yticks([0.5, 1.6, 2.7])
ax_valve.set_yticklabels(["V3", "V2", "V1"], fontsize=8)
ax_valve.set_title("Valve States (last 20 transitions)", fontsize=9, color=TEXT_COL, pad=4)
ax_valve.set_xlabel("Transition #", fontsize=8)
ax_valve.grid(True, axis='x')

# Serial log preview (bottom)
ax_log = fig.add_subplot(gs[2, :])
ax_log.set_facecolor("#0d0f18")
for sp in ax_log.spines.values():
    sp.set_edgecolor("#222")
ax_log.set_xticks([]); ax_log.set_yticks([])

log_lines = [
    "time_ms ,phase    ,V1,V2,V3,o2_pct,cycle",
    "3847013  ,A_ADSORB ,1 ,0 ,0 ,92.41 ,218  ",
    "3848013  ,A_ADSORB ,1 ,0 ,0 ,92.38 ,218  ",
    "3849013  ,A_ADSORB ,1 ,0 ,0 ,92.55 ,218  ",
    "3853013  ,EQ1      ,0 ,0 ,1 ,91.87 ,218  ",
    "3854013  ,B_ADSORB ,0 ,1 ,0 ,92.12 ,218  ",
]
for i, line in enumerate(log_lines):
    col = "#4fc3f7" if i == 0 else "#a8d8a8" if i % 2 == 0 else "#c8c8c8"
    ax_log.text(0.01, 0.85 - i * 0.14, line,
                transform=ax_log.transAxes, fontsize=8,
                fontfamily='monospace', color=col)
ax_log.set_title("Serial Log (CSV)", fontsize=9, color=TEXT_COL, pad=4)

fig.suptitle("OXYCON v1.0 — Live Dashboard", fontsize=14,
             color=TEXT_COL, fontweight='bold', y=0.99)

plt.savefig("media/dashboard_preview.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved media/dashboard_preview.png")

print("\nAll plots generated successfully.")
