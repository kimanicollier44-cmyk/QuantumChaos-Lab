#!/usr/bin/env python3
"""QuantumChaos-Lab - educational quantum chaos lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * This lab puts the two faces of chaos side by side. Classically,
    the kicked rotor (standard map) at strong kicking diffuses:
    <p^2> grows linearly in time, without bound. Quantum-mechanically
    the same rotor, evolved exactly on a finite momentum basis,
    refuses to diffuse - its <p^2> saturates. That saturation is
    dynamical localization, the wave-mechanical brake on classical
    chaos, and it is measured here, not asserted.
  * The second face is spectral. Integrable systems have level
    spacings that behave like random points (Poisson statistics,
    <r> ~ 0.386); chaotic systems repel their levels (Wigner/GOE
    statistics, <r> ~ 0.536). Both ensembles are generated and
    diagonalized inside this file and graded against those class
    values.
  * Everything is a finite, seeded toy. The random matrices are
    drawn from a seeded generator, not measured from any nucleus,
    quantum dot, or device. The rotor lives on 64 momentum states.
    No output predicts a real chaotic system, secures a random
    number, or encrypts anything - those uses are permanent HOLD
    gates, with Gemini Argon 4 Extended Thinking as DECIDER
    (names-only, tighten-only), Muse as advisor (never overrides
    HOLD), and Google Flow plan-only seats.
"""
import hashlib
import json
import math
import random
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# Classical standard map. K_CRITICAL ~ 0.9716 is the labelled textbook
# value for the last invariant torus of the standard map: below it,
# momentum stays bounded for most initial conditions; above it, large-
# scale diffusion sets in. The lab measures both regimes.
SEED_CLASSICAL = 20261117
ENSEMBLE = 2000
STEPS = 200
K_STRONG = 10.0
K_QUANTUM = 5.0
K_WEAK = 0.5
K_CRITICAL_LABELLED = 0.9716

# Quantum kicked rotor. Dimensionless units: kick period T = 1,
# effective hbar = 1. Momentum basis m = -N/2 .. N/2-1 on a torus.
Q_N = 64
Q_KICKS = 200
Q_INITS = (-3, -2, -1, 0, 1, 2, 3)
Q_AVG_FROM = 120
Q_FIT_WINDOW = (3, 14)

# Level statistics. Poisson toy: sorted seeded uniform points.
# GOE toy: seeded Gaussian symmetric matrices, own Jacobi solver.
SEED_POISSON = 777
POISSON_POINTS = 3000
GOE_SIZE = 36
GOE_COUNT = 10
GOE_SEED0 = 1000
R_POISSON_CLASS = 0.38629   # exact: 2*ln(2) - 1
R_GOE_CLASS = 0.53590       # Atas et al. large-N GOE value, labelled
HIST_BINS = ((0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0),
             (2.0, 2.5), (2.5, 3.0), (3.0, float("inf")))

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "chaos_based_encryption_claim": "HOLD - no chaos-based encryption design, evaluation, or security claim",
    "secure_random_generation_claim": "HOLD - seeded generator output is not secure randomness and must never be sold as entropy",
    "real_system_prediction_claim": "HOLD - no predicting real chaotic systems (weather, fluids, plasmas) from a toy map",
    "financial_market_prediction": "HOLD - no market, price, or trading prediction from chaos models",
    "weather_control_claim": "HOLD - no weather prediction-for-control or modification claims",
    "hardware_random_source_claim": "HOLD - no claim that this simulation models or certifies a physical random-number device",
    "quantum_hardware_claim": "HOLD - a 64-state finite-basis simulation is not a quantum hardware result",
    "cryptanalysis_use": "HOLD - no using the rotor or level statistics to attack real ciphers or protocols",
    "real_system_control_guidance": "HOLD - no control guidance for real lasers, accelerators, plasmas, or reactors",
    "weapons_guidance_claim": "HOLD - no weapons, guidance, or targeting use of chaotic-dynamics models",
    "benchmark_supremacy_claim": "HOLD - no benchmark, supremacy, or advantage claim from toy sizes",
    "medical_signal_claim": "HOLD - no EEG, cardiac, or other medical chaos-diagnosis claims",
    "gambling_prediction_claim": "HOLD - no roulette, lottery, or gambling prediction",
    "spectral_data_as_measurement_claim": "HOLD - seeded random matrices are not measured spectra; never present them as nuclear, atomic, or device data",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# Small memo so the demo, the checks, and the tests share one run of
# each expensive experiment. Keys are the experiment parameters.
_CACHE = {}


def _linfit_slope(xs, ys):
    """Least-squares slope of y vs x (both plain sequences)."""
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    return (n * sxy - sx * sy) / denom if denom else 0.0


def _loglog_slope(ts, ys):
    pts = [(math.log(t), math.log(y)) for t, y in zip(ts, ys) if t > 0 and y > 0]
    return _linfit_slope([a for a, _ in pts], [b for _, b in pts])


# ================================================================ 1. Classical standard map
# The kicked rotor, classical side: a particle on a circle kicked
# periodically. One step is
#     p' = p + K sin(theta),   theta' = theta + p'  (mod 2 pi).
# Momentum is kept unwrapped so diffusion is visible; the angle is
# wrapped onto the circle. An ensemble of seeded trajectories gives
# <p^2>(t) - the diffusion curve the quantum side will refuse to follow.

def standard_map_step(theta, p, K):
    p_new = p + K * math.sin(theta)
    return (theta + p_new) % (2.0 * math.pi), p_new


def classical_series(K, steps=STEPS, ens=ENSEMBLE, seed=SEED_CLASSICAL):
    """<p^2> at every step for a seeded ensemble started at p = 0."""
    key = ("classical", K, steps, ens, seed)
    if key in _CACHE:
        return _CACHE[key]
    rng = random.Random(seed)
    thetas = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(ens)]
    ps = [0.0] * ens
    series = []
    for _ in range(steps + 1):
        series.append(sum(x * x for x in ps) / ens)
        for i in range(ens):
            ps[i] += K * math.sin(thetas[i])
            thetas[i] = (thetas[i] + ps[i]) % (2.0 * math.pi)
    _CACHE[key] = series
    return series


def classical_report():
    strong = classical_series(K_STRONG)
    weak = classical_series(K_WEAK)
    sample_t = list(range(0, STEPS + 1, 5))
    exponent = _loglog_slope(sample_t[4:], [strong[t] for t in sample_t[4:]])
    weak_exponent = _loglog_slope(sample_t[4:], [weak[t] for t in sample_t[4:]])
    return {
        "K_strong": K_STRONG,
        "K_weak": K_WEAK,
        "K_critical_labelled": K_CRITICAL_LABELLED,
        "ensemble": ENSEMBLE,
        "steps": STEPS,
        "strong_p2_at_50": round(strong[50], 4),
        "strong_p2_at_100": round(strong[100], 4),
        "strong_p2_final": round(strong[STEPS], 4),
        "strong_diffusion_exponent": round(exponent, 4),
        "strong_D_measured": round(strong[STEPS] / STEPS, 4),
        "strong_D_naive_K2_over_2": round(K_STRONG ** 2 / 2.0, 4),
        "weak_p2_max": round(max(weak), 4),
        "weak_p2_final": round(weak[STEPS], 4),
        "weak_diffusion_exponent": round(weak_exponent, 4),
    }


# ================================================================ 2. Quantum kicked rotor
# The same rotor, quantum side. The Floquet step is
#     U = exp(-i p^2 / 2hbar) . exp(-i K cos(theta) / hbar),
# applied on a finite momentum basis. The kick is diagonal in the
# angle representation and the free rotation is diagonal in the
# momentum representation, so one step is: DFT to the angle grid,
# multiply by the kick phase, DFT back, multiply by the free phase.
# The transform pair is written out as explicit matrices - unitary
# by construction, and the checks prove the roundtrip is the identity.
# Dynamical localization: <p^2> grows for a while, then saturates
# near ell^2, where ell is the localization length - while the
# classical ensemble at the same K keeps diffusing.

def _rotor_operators(K, N):
    ms = list(range(-N // 2, N // 2))
    theta = [2.0 * math.pi * j / N for j in range(N)]
    kick = [complex(math.cos(-K * math.cos(t)), math.sin(-K * math.cos(t)))
            for t in theta]
    free = [complex(math.cos(-m * m / 2.0), math.sin(-m * m / 2.0))
            for m in ms]
    sq = math.sqrt(N)
    W = [[complex(math.cos(m * theta[j]), math.sin(m * theta[j])) / sq
          for m in ms] for j in range(N)]
    return ms, kick, free, W


def _rotor_step(c, kick, free, W, N):
    a = [sum(W[j][i] * c[i] for i in range(N)) for j in range(N)]
    a = [a[j] * kick[j] for j in range(N)]
    c = [sum(a[j] * W[j][i].conjugate() for j in range(N)) for i in range(N)]
    return [c[i] * free[i] for i in range(N)]


def quantum_rotor_run(K=K_QUANTUM, kicks=Q_KICKS, N=Q_N,
                      inits=Q_INITS, avg_from=Q_AVG_FROM):
    """Ensemble of plane-wave inits; returns (<p^2> series, time-averaged
    momentum distribution, momentum grid). Averages are over the initial
    momenta and, for the distribution, over kicks >= avg_from - both
    stated openly, because a single snapshot is interference-ragged."""
    key = ("quantum", K, kicks, N, tuple(inits), avg_from)
    if key in _CACHE:
        return _CACHE[key]
    ms, kick, free, W = _rotor_operators(K, N)
    series = [0.0] * (kicks + 1)
    dist = [0.0] * N
    for m0 in inits:
        c = [0j] * N
        c[ms.index(m0)] = 1.0 + 0j
        acc = [0.0] * N
        count = 0
        for t in range(kicks + 1):
            series[t] += sum((abs(c[i]) ** 2) * ms[i] * ms[i]
                             for i in range(N))
            if t >= avg_from:
                for i in range(N):
                    acc[i] += abs(c[i]) ** 2
                count += 1
            if t < kicks:
                c = _rotor_step(c, kick, free, W, N)
        for i in range(N):
            dist[i] += acc[i] / count
    w = float(len(inits))
    result = ([x / w for x in series], [x / w for x in dist], ms)
    _CACHE[key] = result
    return result


def _fit_localization_length(dist, ms, window=Q_FIT_WINDOW):
    """Fit ln P(|m|) vs |m| on the stated window; P ~ exp(-2|m|/ell)."""
    pooled = {}
    for p, m in zip(dist, ms):
        pooled[abs(m)] = pooled.get(abs(m), 0.0) + p
    lo, hi = window
    pts = [(m, math.log(p)) for m, p in sorted(pooled.items())
           if lo <= m <= hi and p > 0.0]
    slope = _linfit_slope([a for a, _ in pts], [b for _, b in pts])
    return -2.0 / slope if slope < 0 else float("inf")


def quantum_report():
    series, dist, ms = quantum_rotor_run()
    classical = classical_series(K_QUANTUM)
    sat = sum(series[150:]) / len(series[150:])
    early = sum(series[60:100]) / len(series[60:100])
    ell_fit = _fit_localization_length(dist, ms)
    ell_moment = math.sqrt(2.0 * sat)
    core_mass = sum(p for p, m in zip(dist, ms) if abs(m) <= 16)
    return {
        "K": K_QUANTUM,
        "basis_N": Q_N,
        "kicks": Q_KICKS,
        "inits": list(Q_INITS),
        "p2_at_50": round(series[50], 4),
        "p2_saturated_mean_last50": round(sat, 4),
        "plateau_ratio_late_over_early": round(sat / early, 4),
        "classical_p2_final_same_K": round(classical[STEPS], 4),
        "saturation_ratio_quantum_over_classical": round(
            sat / classical[STEPS], 4),
        "localization_length_fit": round(ell_fit, 4),
        "localization_length_moment": round(ell_moment, 4),
        "mass_within_|m|<=16": round(core_mass, 4),
        "fit_window_|m|": list(Q_FIT_WINDOW),
        "note": "ell_fit is a labelled estimate from the exponential "
                "tail of the saturated distribution; ell_moment = "
                "sqrt(2 <p^2>_sat) is the cross-check.",
    }


# ================================================================ 3. Level-spacing statistics
# Two ensembles, two universality classes.
# (a) Integrable toy: a diagonal "Hamiltonian" whose eigenvalues are
#     seeded uniform points. Sorted spacings behave like gaps between
#     random points: Poisson statistics, P(s) = exp(-s), <r> = 0.386.
# (b) Chaotic toy: seeded Gaussian orthogonal ensemble (GOE) matrices,
#     diagonalized by a from-scratch cyclic Jacobi solver. Levels
#     repel: P(s) follows the Wigner surmise (pi/2) s exp(-pi s^2/4),
#     <r> = 0.536. The spacing ratio r needs no unfolding, which is
#     exactly why this lab leads with it; the histogram uses bulk
#     spacings only, where the density is roughly constant.

def jacobi_eigenvalues(matrix, tol=1e-12, max_sweeps=100):
    """Eigenvalues of a real symmetric matrix, cyclic Jacobi rotations."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    for _ in range(max_sweeps):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n)
                            for j in range(n) if i != j))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) < 1e-15:
                    continue
                phi = 0.5 * math.atan2(2.0 * apq, a[q][q] - a[p][p])
                co, si = math.cos(phi), math.sin(phi)
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = co * akp - si * akq
                    a[k][q] = si * akp + co * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = co * apk - si * aqk
                    a[q][k] = si * apk + co * aqk
    return sorted(a[i][i] for i in range(n))


def _spacings(eigs):
    return [eigs[i + 1] - eigs[i] for i in range(len(eigs) - 1)]


def _r_values(eigs):
    sp = _spacings(eigs)
    out = []
    for i in range(len(sp) - 1):
        hi = max(sp[i], sp[i + 1])
        if hi > 0:
            out.append(min(sp[i], sp[i + 1]) / hi)
    return out


def mean_spacing_ratio(eigs):
    rs = _r_values(eigs)
    return sum(rs) / len(rs) if rs else 0.0


def poisson_eigenvalues(points=POISSON_POINTS, seed=SEED_POISSON):
    rng = random.Random(seed)
    return sorted(rng.uniform(0.0, 1.0) for _ in range(points))


def goe_eigenvalues(size=GOE_SIZE, seed=GOE_SEED0):
    rng = random.Random(seed)
    a = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i, size):
            v = rng.gauss(0.0, 1.0)
            a[i][j] = v
            a[j][i] = v
    return jacobi_eigenvalues(a)


def _poisson_cdf(s):
    return 1.0 - math.exp(-s)


def _wigner_cdf(s):
    return 1.0 - math.exp(-math.pi * s * s / 4.0)


def _histogram(spacings, bins=HIST_BINS):
    mean = sum(spacings) / len(spacings)
    counts = [0] * len(bins)
    for x in spacings:
        s = x / mean
        for i, (lo, hi) in enumerate(bins):
            if lo <= s < hi:
                counts[i] += 1
                break
    return [c / len(spacings) for c in counts]


def _curve_masses(cdf, bins=HIST_BINS):
    out = []
    for lo, hi in bins:
        top = 1.0 if math.isinf(hi) else cdf(hi)
        out.append(top - cdf(lo))
    return out


def _l1(xs, ys):
    return sum(abs(a - b) for a, b in zip(xs, ys))


def spacing_report():
    key = "spacing_report"
    if key in _CACHE:
        return _CACHE[key]
    pois_eigs = poisson_eigenvalues()
    pois_r = mean_spacing_ratio(pois_eigs)
    pois_hist = _histogram(_spacings(pois_eigs))
    goe_rs = []
    goe_bulk_spacings = []
    for s in range(GOE_COUNT):
        eigs = goe_eigenvalues(seed=GOE_SEED0 + s)
        goe_rs.extend(_r_values(eigs))
        n = len(eigs)
        bulk = eigs[n // 4: 3 * n // 4]
        goe_bulk_spacings.extend(_spacings(bulk))
    goe_r = sum(goe_rs) / len(goe_rs)
    goe_hist = _histogram(goe_bulk_spacings)
    pois_curve = _curve_masses(_poisson_cdf)
    wig_curve = _curve_masses(_wigner_cdf)
    report = {
        "poisson_points": POISSON_POINTS,
        "poisson_mean_r": round(pois_r, 4),
        "poisson_class_r": R_POISSON_CLASS,
        "goe_size": GOE_SIZE,
        "goe_matrices": GOE_COUNT,
        "goe_mean_r_pooled": round(goe_r, 4),
        "goe_class_r": R_GOE_CLASS,
        "poisson_hist_L1_to_poisson_curve": round(_l1(pois_hist, pois_curve), 4),
        "poisson_hist_L1_to_wigner_curve": round(_l1(pois_hist, wig_curve), 4),
        "goe_hist_L1_to_wigner_curve": round(_l1(goe_hist, wig_curve), 4),
        "goe_hist_L1_to_poisson_curve": round(_l1(goe_hist, pois_curve), 4),
        "histogram_note": "GOE histogram uses bulk spacings (middle half "
                          "of each spectrum); <r> uses all spacings and "
                          "needs no unfolding.",
    }
    _CACHE[key] = report
    return report


# ================================================================ 4. kNN dynamics classifier
# Features: diffusion exponent alpha (<p^2> ~ t^alpha), mean spacing
# ratio <r>, and the saturation ratio rho = <p^2>_quantum /
# <p^2>_classical at the same K and time. The training grid is
# labelled by the lab's own dynamics model (model_label below) - the
# classifier interpolates the model, it does not replace the
# measurements.

def model_label(alpha, mean_r, rho):
    """The dynamics model distilled to a three-way teaching label."""
    if rho < 0.25:
        return "localized"
    if alpha >= 0.65 and mean_r >= 0.46:
        return "chaotic-diffusive"
    if alpha >= 0.85:
        return "chaotic-diffusive"
    return "regular"


def _training_grid():
    rows = []
    for alpha in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2):
        for mean_r in (0.35, 0.386, 0.43, 0.47, 0.50, 0.536, 0.58):
            for rho in (0.0, 0.05, 0.15, 0.30, 0.60, 1.00):
                rows.append(((alpha, mean_r, rho),
                             model_label(alpha, mean_r, rho)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    alpha, mean_r, rho = features
    return (alpha / 1.2, (mean_r - 0.30) / 0.35, rho)


def classify_dynamics(alpha, mean_r, rho, k=5):
    """kNN over the model-labelled grid, deterministic tie-breaking."""
    target = _scaled((alpha, mean_r, rho))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for _, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0) + 1
    priority = {"chaotic-diffusive": 0, "localized": 1, "regular": 2}
    return sorted(votes.items(), key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def scenario_features():
    """The three teaching scenarios, with features measured by the lab."""
    crep = classical_report()
    qrep = quantum_report()
    srep = spacing_report()
    sample_t = list(range(0, STEPS + 1, 5))
    qseries, _, _ = quantum_rotor_run()
    late_t = [t for t in sample_t if t >= 100]
    alpha_q = _loglog_slope(late_t, [qseries[t] for t in late_t])
    return {
        "classical_strong_K10": (
            crep["strong_diffusion_exponent"], srep["goe_mean_r_pooled"], 1.0),
        "classical_weak_K0.5": (
            crep["weak_diffusion_exponent"], srep["poisson_mean_r"], 1.0),
        "quantum_rotor_K5": (
            round(alpha_q, 4), srep["poisson_mean_r"],
            qrep["saturation_ratio_quantum_over_classical"]),
    }


def classifier_report():
    return {name: classify_dynamics(*features)
            for name, features in scenario_features().items()}


# ================================================================ 5. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumchaos-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all prediction / crypto / hardware gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantumchaos-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Lead with the contrast, not the hype: the classical rotor diffuses forever, the quantum rotor stops - and the level statistics say why. Keep the seeded-toy label on every spectrum; a random matrix is a model of chaos, not a measurement of it.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["a classical rotor phase portrait smearing into a diffusive cloud",
                  "the quantum momentum distribution freezing into an exponential profile",
                  "two spacing histograms: one piled at zero, one repelled from it",
                  "level curves bending away from each other instead of crossing",
                  "the saturation plateau drawn flat against the classical ramp"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. classical standard map - mechanics
    th, p = standard_map_step(math.pi / 2.0, 0.0, 10.0)
    chk("map_step_kick_formula", abs(p - 10.0) < 1e-12)
    chk("map_step_angle_wraps",
        abs(th - (math.pi / 2.0 + 10.0) % (2.0 * math.pi)) < 1e-12)
    th2, p2 = standard_map_step(0.0, 3.25, 7.0)
    chk("map_step_zero_angle_no_kick", p2 == 3.25
        and abs(th2 - 3.25 % (2.0 * math.pi)) < 1e-12)
    s_a = classical_series(K_STRONG, steps=40, ens=300, seed=42)
    s_b = classical_series(K_STRONG, steps=40, ens=300, seed=42)
    chk("classical_deterministic_same_seed", s_a == s_b)
    chk("classical_starts_at_zero", s_a[0] == 0.0)

    # 2. classical diffusion vs boundedness
    crep = classical_report()
    chk("strong_diffusion_exponent_near_1",
        0.85 < crep["strong_diffusion_exponent"] < 1.15)
    chk("strong_p2_grows_large", crep["strong_p2_final"] > 3000.0)
    chk("strong_p2_monotone_growth",
        crep["strong_p2_at_50"] < crep["strong_p2_at_100"]
        < crep["strong_p2_final"])
    chk("strong_D_below_naive_rate",
        0.0 < crep["strong_D_measured"] < crep["strong_D_naive_K2_over_2"])
    chk("weak_kick_bounded", crep["weak_p2_max"] < 2.0)
    chk("weak_far_below_strong",
        crep["weak_p2_final"] < crep["strong_p2_final"] / 1000.0)
    chk("weak_exponent_below_strong",
        crep["weak_diffusion_exponent"] < crep["strong_diffusion_exponent"])

    # 3. quantum rotor - transform machinery
    ms, kick, free, W = _rotor_operators(K_QUANTUM, Q_N)
    rng = random.Random(5)
    vec = [complex(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(Q_N)]
    norm0 = math.sqrt(sum(abs(x) ** 2 for x in vec))
    vec = [x / norm0 for x in vec]
    a = [sum(W[j][i] * vec[i] for i in range(Q_N)) for j in range(Q_N)]
    back = [sum(a[j] * W[j][i].conjugate() for j in range(Q_N))
            for i in range(Q_N)]
    chk("dft_roundtrip_identity",
        max(abs(back[i] - vec[i]) for i in range(Q_N)) < 1e-9)
    stepped = _rotor_step(vec, kick, free, W, Q_N)
    chk("floquet_step_norm_preserving",
        abs(sum(abs(x) ** 2 for x in stepped) - 1.0) < 1e-9)
    chk("kick_phases_unit_modulus", all(abs(abs(x) - 1.0) < 1e-12 for x in kick))
    chk("free_phases_unit_modulus", all(abs(abs(x) - 1.0) < 1e-12 for x in free))

    # 4. quantum rotor - dynamical localization
    qrep = quantum_report()
    chk("quantum_saturates_far_below_classical",
        qrep["saturation_ratio_quantum_over_classical"] < 0.15)
    chk("quantum_plateau_flat",
        0.5 < qrep["plateau_ratio_late_over_early"] < 1.5)
    chk("quantum_grew_before_saturating",
        qrep["p2_saturated_mean_last50"] > 50.0
        and qrep["p2_at_50"] > 20.0)
    chk("localization_length_in_range",
        3.0 < qrep["localization_length_fit"] < 25.0)
    chk("localization_fit_matches_moment",
        abs(math.log(qrep["localization_length_fit"]
                     / qrep["localization_length_moment"]))
        < math.log(2.5))
    chk("distribution_concentrated", qrep["mass_within_|m|<=16"] > 0.80)

    # 5. Jacobi eigensolver
    chk("jacobi_known_2x2",
        jacobi_eigenvalues([[2.0, 1.0], [1.0, 2.0]]) == [1.0, 3.0])
    chk("jacobi_diagonal_passthrough",
        jacobi_eigenvalues([[3.0, 0.0], [0.0, -1.0]]) == [-1.0, 3.0])
    rng = random.Random(9)
    n = 12
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            v = rng.uniform(-1, 1)
            mat[i][j] = v
            mat[j][i] = v
    eigs = jacobi_eigenvalues(mat)
    trace = sum(mat[i][i] for i in range(n))
    frob = sum(mat[i][j] ** 2 for i in range(n) for j in range(n))
    chk("jacobi_trace_invariant", abs(sum(eigs) - trace) < 1e-8)
    chk("jacobi_frobenius_invariant",
        abs(sum(e * e for e in eigs) - frob) < 1e-7)
    chk("jacobi_output_sorted",
        all(eigs[i] <= eigs[i + 1] for i in range(n - 1)))

    # 6. level statistics - Poisson vs GOE
    srep = spacing_report()
    chk("poisson_mean_r_at_class",
        abs(srep["poisson_mean_r"] - R_POISSON_CLASS) < 0.03)
    chk("goe_mean_r_at_class",
        abs(srep["goe_mean_r_pooled"] - R_GOE_CLASS) < 0.045)
    chk("goe_r_exceeds_poisson_r",
        srep["goe_mean_r_pooled"] > srep["poisson_mean_r"] + 0.10)
    chk("poisson_hist_prefers_poisson_curve",
        srep["poisson_hist_L1_to_poisson_curve"]
        < srep["poisson_hist_L1_to_wigner_curve"])
    chk("goe_hist_prefers_wigner_curve",
        srep["goe_hist_L1_to_wigner_curve"]
        < srep["goe_hist_L1_to_poisson_curve"])
    chk("poisson_hist_close_to_curve",
        srep["poisson_hist_L1_to_poisson_curve"] < 0.35)
    chk("goe_hist_close_to_curve",
        srep["goe_hist_L1_to_wigner_curve"] < 0.35)
    chk("curve_masses_normalised",
        abs(sum(_curve_masses(_poisson_cdf)) - 1.0) < 1e-9
        and abs(sum(_curve_masses(_wigner_cdf)) - 1.0) < 1e-9)
    chk("r_ratio_bounds",
        0.0 <= mean_spacing_ratio(poisson_eigenvalues(points=200, seed=3))
        <= 1.0)

    # 7. classifier - labels come from the dynamics model itself
    rep = classifier_report()
    chk("classifier_strong_chaotic",
        rep["classical_strong_K10"] == "chaotic-diffusive")
    chk("classifier_weak_regular", rep["classical_weak_K0.5"] == "regular")
    chk("classifier_quantum_localized",
        rep["quantum_rotor_K5"] == "localized")
    feats = scenario_features()
    chk("classifier_matches_model",
        all(classify_dynamics(*f) == model_label(*f) for f in feats.values()))
    chk("model_label_localized_by_rho",
        model_label(1.0, 0.536, 0.05) == "localized")
    chk("model_label_regular_quiet",
        model_label(0.1, 0.386, 1.0) == "regular")

    # 8. gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_crypto_hold", gate("chaos_based_encryption_claim") == "HOLD")
    chk("gate_random_hold", gate("secure_random_generation_claim") == "HOLD")
    chk("gate_prediction_hold", gate("real_system_prediction_claim") == "HOLD")
    chk("gate_spectral_hold",
        gate("spectral_data_as_measurement_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumChaos-Lab - kicked rotor + level statistics lab")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - chaos has two faces, and both are toys here")
    print("    Classically the kicked rotor diffuses forever. Quantum-")
    print("    mechanically it localizes and stops. Spectrally, integrable")
    print("    systems cluster their levels (Poisson) while chaotic systems")
    print("    repel them (Wigner/GOE). Every number below is computed in")
    print("    this file from seeded, finite toys - no measured spectrum,")
    print("    no real system, no prediction of anything.")
    crep = classical_report()
    print("\n[2] Classical standard map - diffusion vs bounded motion")
    print(f"    ensemble {crep['ensemble']} trajectories, {crep['steps']} kicks, "
          f"angles seeded")
    print(f"    K = {crep['K_strong']:.1f} (strong): <p^2> 50 kicks "
          f"{crep['strong_p2_at_50']:.1f} | 100 kicks "
          f"{crep['strong_p2_at_100']:.1f} | final {crep['strong_p2_final']:.1f}")
    print(f"      fitted diffusion exponent {crep['strong_diffusion_exponent']:.4f}"
          "  (1 = pure diffusion)")
    print(f"      measured D = <p^2>/t = {crep['strong_D_measured']:.2f} "
          f"(naive K^2/2 = {crep['strong_D_naive_K2_over_2']:.1f} - "
          "correlations cut it)")
    print(f"    K = {crep['K_weak']:.1f} (weak, below the labelled K_c ~ "
          f"{crep['K_critical_labelled']}): <p^2> max {crep['weak_p2_max']:.4f}, "
          f"final {crep['weak_p2_final']:.4f} - bounded, no diffusion")
    qrep = quantum_report()
    print("\n[3] Quantum kicked rotor - dynamical localization")
    print(f"    Floquet evolution on {qrep['basis_N']} momentum states, "
          f"{qrep['kicks']} kicks, K = {qrep['K']:.1f}, hbar = 1")
    print(f"    <p^2> at 50 kicks {qrep['p2_at_50']:.1f} -> saturated mean "
          f"(last 50) {qrep['p2_saturated_mean_last50']:.1f}")
    print(f"    plateau ratio late/early {qrep['plateau_ratio_late_over_early']:.4f}"
          "  (1 = perfectly flat)")
    print(f"    classical rotor at the same K reaches "
          f"{qrep['classical_p2_final_same_K']:.1f} - saturation ratio "
          f"{qrep['saturation_ratio_quantum_over_classical']:.4f}")
    print(f"    localization length: tail fit ell = "
          f"{qrep['localization_length_fit']:.2f} (labelled estimate), "
          f"moment ell = {qrep['localization_length_moment']:.2f}")
    print(f"    momentum mass within |m| <= 16: "
          f"{qrep['mass_within_|m|<=16']:.4f} of 1")
    srep = spacing_report()
    print("\n[4] Level-spacing statistics - Poisson vs Wigner/GOE")
    print(f"    integrable toy (diagonal, {srep['poisson_points']} seeded "
          f"points): <r> = {srep['poisson_mean_r']:.4f} "
          f"(Poisson class {srep['poisson_class_r']})")
    print(f"    chaotic toy (GOE {srep['goe_size']}x{srep['goe_size']}, "
          f"{srep['goe_matrices']} matrices, own Jacobi solver): "
          f"<r> = {srep['goe_mean_r_pooled']:.4f} "
          f"(GOE class {srep['goe_class_r']})")
    print(f"    histogram L1: Poisson data -> Poisson curve "
          f"{srep['poisson_hist_L1_to_poisson_curve']:.4f} vs Wigner curve "
          f"{srep['poisson_hist_L1_to_wigner_curve']:.4f}")
    print(f"                  GOE data     -> Wigner curve "
          f"{srep['goe_hist_L1_to_wigner_curve']:.4f} vs Poisson curve "
          f"{srep['goe_hist_L1_to_poisson_curve']:.4f}")
    print("    -> levels repel in the chaotic ensemble and cluster in the")
    print("       integrable one. The r-ratio needs no unfolding; the GOE")
    print("       histogram uses bulk spacings only, and says so.")
    print("\n[5] Dynamics classifier (TinyML kNN, labels from the lab's model)")
    feats = scenario_features()
    for name, label in classifier_report().items():
        a, r, rho = feats[name]
        print(f"    {name:24s} alpha {a:.3f} | <r> {r:.3f} | rho {rho:.3f} "
              f"-> {label}")
    print("\n[6] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[7] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "classical":
        print(json.dumps(classical_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "quantum":
        print(json.dumps(quantum_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "spacings":
        print(json.dumps(spacing_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "chaos_based_encryption_claim"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
