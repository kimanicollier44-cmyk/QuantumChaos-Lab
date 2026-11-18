"""Tests for QuantumChaos-Lab: map, rotor, spacings, classifier, gates."""
import math

import pytest

import main as m


# ---- classical standard map
def test_map_step_kick_formula():
    _, p = m.standard_map_step(math.pi / 2.0, 0.0, 10.0)
    assert abs(p - 10.0) < 1e-12


def test_map_step_angle_wraps():
    th, _ = m.standard_map_step(math.pi / 2.0, 0.0, 10.0)
    assert abs(th - (math.pi / 2.0 + 10.0) % (2.0 * math.pi)) < 1e-12


def test_map_step_zero_angle_no_kick():
    _, p = m.standard_map_step(0.0, 3.25, 7.0)
    assert p == 3.25


def test_classical_deterministic_same_seed():
    a = m.classical_series(10.0, steps=40, ens=300, seed=42)
    b = m.classical_series(10.0, steps=40, ens=300, seed=42)
    assert a == b and a[0] == 0.0


def test_strong_diffusion_exponent_near_1():
    rep = m.classical_report()
    assert 0.85 < rep["strong_diffusion_exponent"] < 1.15


def test_strong_p2_grows_monotone_large():
    rep = m.classical_report()
    assert rep["strong_p2_at_50"] < rep["strong_p2_at_100"] < rep["strong_p2_final"]
    assert rep["strong_p2_final"] > 3000.0


def test_measured_D_below_naive():
    rep = m.classical_report()
    assert 0.0 < rep["strong_D_measured"] < rep["strong_D_naive_K2_over_2"]


def test_weak_kick_bounded():
    rep = m.classical_report()
    assert rep["weak_p2_max"] < 2.0
    assert rep["weak_p2_final"] < rep["strong_p2_final"] / 1000.0


# ---- quantum kicked rotor
def test_dft_roundtrip_identity():
    ms, kick, free, W = m._rotor_operators(m.K_QUANTUM, m.Q_N)
    import random
    rng = random.Random(5)
    vec = [complex(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(m.Q_N)]
    norm = math.sqrt(sum(abs(x) ** 2 for x in vec))
    vec = [x / norm for x in vec]
    a = [sum(W[j][i] * vec[i] for i in range(m.Q_N)) for j in range(m.Q_N)]
    back = [sum(a[j] * W[j][i].conjugate() for j in range(m.Q_N))
            for i in range(m.Q_N)]
    assert max(abs(back[i] - vec[i]) for i in range(m.Q_N)) < 1e-9


def test_floquet_step_norm_preserving():
    ms, kick, free, W = m._rotor_operators(m.K_QUANTUM, m.Q_N)
    vec = [0j] * m.Q_N
    vec[ms.index(0)] = 1.0 + 0j
    out = m._rotor_step(vec, kick, free, W, m.Q_N)
    assert abs(sum(abs(x) ** 2 for x in out) - 1.0) < 1e-9


def test_phases_unit_modulus():
    _, kick, free, _ = m._rotor_operators(m.K_QUANTUM, m.Q_N)
    assert all(abs(abs(x) - 1.0) < 1e-12 for x in kick)
    assert all(abs(abs(x) - 1.0) < 1e-12 for x in free)


def test_quantum_saturates_far_below_classical():
    rep = m.quantum_report()
    assert rep["saturation_ratio_quantum_over_classical"] < 0.15


def test_quantum_plateau_flat():
    rep = m.quantum_report()
    assert 0.5 < rep["plateau_ratio_late_over_early"] < 1.5
    assert rep["p2_saturated_mean_last50"] > 50.0


def test_localization_length_estimates_agree():
    rep = m.quantum_report()
    assert 3.0 < rep["localization_length_fit"] < 25.0
    ratio = rep["localization_length_fit"] / rep["localization_length_moment"]
    assert abs(math.log(ratio)) < math.log(2.5)


def test_distribution_concentrated():
    rep = m.quantum_report()
    assert rep["mass_within_|m|<=16"] > 0.80


# ---- Jacobi eigensolver
def test_jacobi_known_2x2():
    assert m.jacobi_eigenvalues([[2.0, 1.0], [1.0, 2.0]]) == [1.0, 3.0]


def test_jacobi_diagonal_passthrough():
    assert m.jacobi_eigenvalues([[3.0, 0.0], [0.0, -1.0]]) == [-1.0, 3.0]


def test_jacobi_invariants():
    import random
    rng = random.Random(9)
    n = 12
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            v = rng.uniform(-1, 1)
            mat[i][j] = v
            mat[j][i] = v
    eigs = m.jacobi_eigenvalues(mat)
    trace = sum(mat[i][i] for i in range(n))
    frob = sum(mat[i][j] ** 2 for i in range(n) for j in range(n))
    assert abs(sum(eigs) - trace) < 1e-8
    assert abs(sum(e * e for e in eigs) - frob) < 1e-7
    assert all(eigs[i] <= eigs[i + 1] for i in range(n - 1))


# ---- level statistics
def test_poisson_mean_r_at_class():
    rep = m.spacing_report()
    assert abs(rep["poisson_mean_r"] - m.R_POISSON_CLASS) < 0.03


def test_goe_mean_r_at_class():
    rep = m.spacing_report()
    assert abs(rep["goe_mean_r_pooled"] - m.R_GOE_CLASS) < 0.045
    assert rep["goe_mean_r_pooled"] > rep["poisson_mean_r"] + 0.10


def test_histograms_prefer_own_curve():
    rep = m.spacing_report()
    assert (rep["poisson_hist_L1_to_poisson_curve"]
            < rep["poisson_hist_L1_to_wigner_curve"])
    assert (rep["goe_hist_L1_to_wigner_curve"]
            < rep["goe_hist_L1_to_poisson_curve"])
    assert rep["poisson_hist_L1_to_poisson_curve"] < 0.35
    assert rep["goe_hist_L1_to_wigner_curve"] < 0.35


def test_curve_masses_normalised():
    assert abs(sum(m._curve_masses(m._poisson_cdf)) - 1.0) < 1e-9
    assert abs(sum(m._curve_masses(m._wigner_cdf)) - 1.0) < 1e-9


# ---- classifier
def test_classifier_scenarios():
    rep = m.classifier_report()
    assert rep["classical_strong_K10"] == "chaotic-diffusive"
    assert rep["classical_weak_K0.5"] == "regular"
    assert rep["quantum_rotor_K5"] == "localized"


def test_classifier_matches_model_on_scenarios():
    for features in m.scenario_features().values():
        assert m.classify_dynamics(*features) == m.model_label(*features)


def test_model_label_rules():
    assert m.model_label(1.0, 0.536, 0.05) == "localized"
    assert m.model_label(0.1, 0.386, 1.0) == "regular"
    assert m.model_label(1.0, 0.536, 1.0) == "chaotic-diffusive"


# ---- gates + seats
def test_hold_gates_count_and_style():
    assert len(m.HOLD_GATES) == 14
    assert all(v.startswith("HOLD") for v in m.HOLD_GATES.values())


@pytest.mark.parametrize("action", [
    "chaos_based_encryption_claim", "secure_random_generation_claim",
    "real_system_prediction_claim", "financial_market_prediction",
    "spectral_data_as_measurement_claim",
])
def test_gated_actions_hold(action):
    assert m.gate(action) == "HOLD"


def test_sandbox_proceeds():
    assert m.gate("run_simulation") == "PROCEED"


def test_argon4_seat():
    decider = m.brains_report()["decider"]
    assert decider["seat"] == "Gemini Argon 4 Extended Thinking"
    assert decider["can_override_hold"] is False
    assert decider["live_calls"] == 0


def test_claude_and_flow_seats():
    brains = m.brains_report()
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0


def test_hold_demo_exit_code(capsys):
    assert m.main(["hold-demo"]) == 2
    assert "chaos_based_encryption_claim" in capsys.readouterr().out


def test_checks_all_pass():
    checks = m.run_checks()
    assert all(ok for _, ok in checks)
