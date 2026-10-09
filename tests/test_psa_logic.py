"""
test_psa_logic.py — Python simulation of OXYCON PSA cycle logic
IIT Bhilai | Ashish Devadas

Tests validate the state machine transitions, timing, valve patterns,
and O2 sensor maths that are implemented in the Arduino firmware.

Run with:
    pytest tests/ -v
"""

import math
import pytest


# ── Constants mirrored from config.h ─────────────────────────────────────────
ADSORB_MS    = 6000
EQUALISE_MS  = 500
MQ135_R0     = 76.63
MQ135_RL     = 10.0
ADC_VREF     = 5.0
ADC_STEPS    = 1023.0
O2_AMBIENT   = 20.9
O2_SCALE     = 95.0
O2_MIN_ALARM = 30.0
O2_MAX_DISPLAY = 99.0


# ── PSA state machine (Python mirror of firmware) ─────────────────────────────

class Phase:
    A_ADSORB = 0
    EQ1      = 1
    B_ADSORB = 2
    EQ2      = 3

PHASE_NAMES = {
    Phase.A_ADSORB: "A_ADSORB",
    Phase.EQ1:      "EQ1",
    Phase.B_ADSORB: "B_ADSORB",
    Phase.EQ2:      "EQ2",
}


def phase_duration(phase: int) -> int:
    """Mirror of phaseDuration() in OXYCON.ino."""
    if phase in (Phase.EQ1, Phase.EQ2):
        return EQUALISE_MS
    return ADSORB_MS


def apply_phase(phase: int) -> tuple[bool, bool, bool]:
    """Returns (V1, V2, V3) for a given phase. Mirror of applyPhase()."""
    if phase == Phase.A_ADSORB:
        return (True, False, False)
    elif phase in (Phase.EQ1, Phase.EQ2):
        return (False, False, True)
    elif phase == Phase.B_ADSORB:
        return (False, True, False)
    raise ValueError(f"Unknown phase: {phase}")


def next_phase(phase: int) -> tuple[int, int]:
    """
    Returns (new_phase, delta_cycle) where delta_cycle = 1 when a full cycle
    completes (i.e. on the EQ2 → A_ADSORB transition).
    """
    transitions = {
        Phase.A_ADSORB: Phase.EQ1,
        Phase.EQ1:      Phase.B_ADSORB,
        Phase.B_ADSORB: Phase.EQ2,
        Phase.EQ2:      Phase.A_ADSORB,
    }
    new_phase = transitions[phase]
    delta_cycle = 1 if (phase == Phase.EQ2) else 0
    return new_phase, delta_cycle


def read_o2_pct(adc_val: float) -> float:
    """
    Mirror of readO2Pct() in OXYCON.ino.
    adc_val: raw 10-bit ADC value (0–1023)
    """
    v_sensor = adc_val * (ADC_VREF / ADC_STEPS)
    if v_sensor < 0.01:
        v_sensor = 0.01
    r_sensor = MQ135_RL * (ADC_VREF - v_sensor) / v_sensor
    ratio = r_sensor / MQ135_R0
    o2 = O2_AMBIENT + (1.0 - ratio) * O2_SCALE
    return max(0.0, min(O2_MAX_DISPLAY, o2))


# ─────────────────────────────────────────────────────────────────────────────
class TestPhaseDuration:
    def test_adsorb_phases_use_adsorb_ms(self):
        assert phase_duration(Phase.A_ADSORB) == ADSORB_MS
        assert phase_duration(Phase.B_ADSORB) == ADSORB_MS

    def test_equalise_phases_use_equalise_ms(self):
        assert phase_duration(Phase.EQ1) == EQUALISE_MS
        assert phase_duration(Phase.EQ2) == EQUALISE_MS

    def test_adsorb_longer_than_equalise(self):
        assert ADSORB_MS > EQUALISE_MS

    def test_cycle_total_time(self):
        """One full PSA cycle = 2 × ADSORB + 2 × EQUALISE."""
        total = (2 * ADSORB_MS) + (2 * EQUALISE_MS)
        assert total == 2 * ADSORB_MS + 2 * EQUALISE_MS
        assert total == 13000   # 6000+500+6000+500


# ─────────────────────────────────────────────────────────────────────────────
class TestValvePatterns:
    def test_a_adsorb_v1_only(self):
        v1, v2, v3 = apply_phase(Phase.A_ADSORB)
        assert v1 is True
        assert v2 is False
        assert v3 is False

    def test_b_adsorb_v2_only(self):
        v1, v2, v3 = apply_phase(Phase.B_ADSORB)
        assert v1 is False
        assert v2 is True
        assert v3 is False

    def test_eq1_v3_only(self):
        v1, v2, v3 = apply_phase(Phase.EQ1)
        assert v1 is False
        assert v2 is False
        assert v3 is True

    def test_eq2_v3_only(self):
        v1, v2, v3 = apply_phase(Phase.EQ2)
        assert v1 is False
        assert v2 is False
        assert v3 is True

    def test_never_v1_and_v2_simultaneously(self):
        """V1 and V2 open at the same time would short-circuit columns."""
        for phase in (Phase.A_ADSORB, Phase.EQ1, Phase.B_ADSORB, Phase.EQ2):
            v1, v2, _ = apply_phase(phase)
            assert not (v1 and v2), f"V1 and V2 both open in phase {PHASE_NAMES[phase]}"

    def test_at_most_one_valve_open_per_phase(self):
        """Small PSA unit — only one valve should be open at a time."""
        for phase in (Phase.A_ADSORB, Phase.EQ1, Phase.B_ADSORB, Phase.EQ2):
            valves = apply_phase(phase)
            open_count = sum(1 for v in valves if v)
            assert open_count == 1, (
                f"Expected exactly 1 open valve in {PHASE_NAMES[phase]}, "
                f"got {open_count}"
            )


# ─────────────────────────────────────────────────────────────────────────────
class TestPhaseTransitions:
    def test_full_cycle_sequence(self):
        """A_ADSORB → EQ1 → B_ADSORB → EQ2 → A_ADSORB."""
        phase = Phase.A_ADSORB
        expected = [Phase.EQ1, Phase.B_ADSORB, Phase.EQ2, Phase.A_ADSORB]
        for expected_next in expected:
            phase, _ = next_phase(phase)
            assert phase == expected_next

    def test_cycle_count_increments_on_eq2(self):
        """cycle_count should go up exactly once per full cycle, on EQ2 → A_ADSORB."""
        phase = Phase.A_ADSORB
        cycle_count = 0
        for _ in range(4):
            phase, delta = next_phase(phase)
            cycle_count += delta
        assert cycle_count == 1

    def test_cycle_count_after_n_cycles(self):
        phase = Phase.A_ADSORB
        cycle_count = 0
        N = 10
        for _ in range(N * 4):
            phase, delta = next_phase(phase)
            cycle_count += delta
        assert cycle_count == N

    def test_returns_to_start_after_four_transitions(self):
        phase = Phase.A_ADSORB
        for _ in range(4):
            phase, _ = next_phase(phase)
        assert phase == Phase.A_ADSORB


# ─────────────────────────────────────────────────────────────────────────────
class TestO2Calculation:
    def _adc_for_rs(self, rs_kohm: float) -> float:
        """Inverse of the Rs calculation — gives the ADC value for a known Rs."""
        # rs = RL * (Vref - Vs) / Vs  →  Vs = RL * Vref / (rs + RL)
        v_sensor = MQ135_RL * ADC_VREF / (rs_kohm + MQ135_RL)
        adc = v_sensor / ADC_VREF * ADC_STEPS
        return adc

    def test_ambient_air_gives_approx_21pct(self):
        """At Rs = R0 (ratio = 1), O2 should equal O2_AMBIENT."""
        adc = self._adc_for_rs(MQ135_R0)
        o2 = read_o2_pct(adc)
        assert abs(o2 - O2_AMBIENT) < 0.5, f"Expected ~{O2_AMBIENT}%, got {o2:.2f}%"

    def test_higher_rs_gives_lower_o2(self):
        """More resistance (less O2 effect) → lower O2 reading."""
        adc_low  = self._adc_for_rs(MQ135_R0 * 1.5)   # higher Rs
        adc_high = self._adc_for_rs(MQ135_R0 * 0.5)   # lower Rs
        o2_low  = read_o2_pct(adc_low)
        o2_high = read_o2_pct(adc_high)
        assert o2_low < o2_high

    def test_enriched_o2_above_ambient(self):
        """PSA output (ratio < 1) should read above ambient O2."""
        adc = self._adc_for_rs(MQ135_R0 * 0.4)   # ratio = 0.4
        o2 = read_o2_pct(adc)
        assert o2 > O2_AMBIENT

    def test_o2_clamped_to_max_display(self):
        """Extreme ADC values should not exceed O2_MAX_DISPLAY."""
        o2 = read_o2_pct(1)   # very low ADC → very high computed O2
        assert o2 <= O2_MAX_DISPLAY

    def test_o2_not_negative(self):
        """O2 reading should never go below 0."""
        o2 = read_o2_pct(1023)   # maximum ADC
        assert o2 >= 0.0

    def test_alarm_threshold_below_psa_output(self):
        """
        A working PSA outputs > 85%.  The alarm at O2_MIN_ALARM=30% should
        only trigger on sensor failure or system fault, not during operation.
        """
        assert O2_MIN_ALARM < 85.0

    def test_ratio_formula_consistency(self):
        """Verify the formula: o2 = O2_AMBIENT + (1 - ratio) * O2_SCALE."""
        ratio = 0.5
        rs = MQ135_R0 * ratio
        adc = self._adc_for_rs(rs)
        o2 = read_o2_pct(adc)
        expected = O2_AMBIENT + (1.0 - ratio) * O2_SCALE
        expected = max(0.0, min(O2_MAX_DISPLAY, expected))
        assert abs(o2 - expected) < 1.0   # allow 1% tolerance for floating-point


# ─────────────────────────────────────────────────────────────────────────────
class TestPSASimulation:
    """Simulate a full PSA run and verify timing and state properties."""

    def _run_cycles(self, n_cycles: int):
        """
        Simulates n_cycles of PSA operation.
        Returns list of (phase, duration_ms, valves) tuples.
        """
        phase = Phase.A_ADSORB
        cycle_count = 0
        log = []

        while cycle_count < n_cycles:
            valves = apply_phase(phase)
            duration = phase_duration(phase)
            log.append((phase, duration, valves))
            phase, delta = next_phase(phase)
            cycle_count += delta

        return log

    def test_simulation_produces_correct_phase_count(self):
        """n cycles = 4 × n phases."""
        log = self._run_cycles(5)
        assert len(log) == 20

    def test_simulation_total_time(self):
        """Total wall time for n cycles should be n × (2 × ADSORB + 2 × EQUALISE)."""
        n = 3
        log = self._run_cycles(n)
        total_ms = sum(d for _, d, _ in log)
        expected_ms = n * (2 * ADSORB_MS + 2 * EQUALISE_MS)
        assert total_ms == expected_ms

    def test_valve_conflict_never_occurs_in_simulation(self):
        """V1 and V2 must never be simultaneously open across a full run."""
        log = self._run_cycles(10)
        for phase, _, (v1, v2, v3) in log:
            assert not (v1 and v2), (
                f"V1+V2 conflict in phase {PHASE_NAMES[phase]}"
            )

    def test_equalise_phases_total_fraction(self):
        """Equalisation time should be a small fraction of the total cycle time."""
        cycle_ms = 2 * ADSORB_MS + 2 * EQUALISE_MS
        eq_fraction = (2 * EQUALISE_MS) / cycle_ms
        assert eq_fraction < 0.15, (
            f"Equalisation taking {eq_fraction*100:.1f}% of cycle — too long"
        )
