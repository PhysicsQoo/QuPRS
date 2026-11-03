"""One source for CodSpeed case identity. Benchmarks keep their existing IDs.

The legacy 32 are owned by test/_benchmark_cases.py and must not be renamed;
this registry owns the separate solver and exploratory case tables.
History from TACAS26 only ranks candidates, never supplies current timings.
"""
from __future__ import annotations
from dataclasses import dataclass

NATIVE_IDS = (
    "native_rr_tolerance[0.0000000001]", "native_rr_tolerance[0.00000001]",
    "native_rr_tolerance[0]", "phase_clifford_add", "phase_clifford_sub",
    "phase_decimal_add", "phase_decimal_scale", "phase_decimal_sub",
    "phase_symbolic_add", "rr_hh_pipeline", "rr_nonclifford_pipeline",
    "phase_decimal_hash_repeated", "phase_decimal_hash_unique",
    "phase_decimal_hash_mixed",
    "wmc_trace_cnf_unweighted",
    "wmc_trace_f64_repeated",
    "wmc_trace_f64_unique",
    "wmc_trace_mpfr96_repeated",
    "wmc_trace_mpfr96_unique",
    "wmc_trace_mpfr192_repeated",
    "wmc_trace_mpfr192_unique",
    "wmc_dimacs_mpfr96_unique",
    "rr_elim_direct", "rr_hh_direct", "rr_omega_direct",
)

LEGACY_CASE_COUNT = 32
LEGACY_SHARD_COUNT = 5
LEGACY_IDENTITY_SHA256 = "7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed"

# (case_id, QASM, strategy, solver, reverse, backend).
# Identifiers frozen: never retroactively change CodSpeed baselines.
WALLTIME_CASES = (
    ("vqe4_gpmc", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "gpmc", False, "rust"),
    ("qft16_gpmc", "qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", "gpmc", True, "rust"),
    ("qaoa7_gpmc", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", "gpmc", False, "rust"),
    ("vqe4_ganak", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "ganak", False, "rust"),
    ("grover4_ganak", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "ganak", True, "rust"),
    ("vqe4_gpmc_python", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "gpmc", False, "python"),
    ("vqe4_ganak_python", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", "ganak", False, "python"),
)
WALLTIME_CASE_IDS = frozenset(row[0] for row in WALLTIME_CASES)
GANAK_PRECISION_LIMIT_CASES = {
    "grover4_ganak": "grover4",
    "vqe4_ganak": "vqe4",
    "vqe4_ganak_python": "vqe4",
}

# (case_id, QASM, strategy, reverse, solver, backend).
# Distinct from legacy subprocess-excluded CPU Simulation.
SOLVER_CPU_CASES = (
    ("vqe4-gpmc-rust", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False, "gpmc", "rust"),
    ("vqe4-gpmc-python", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False, "gpmc", "python"),
    ("grover4-gpmc-rust", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True, "gpmc", "rust"),
    ("qft16-gpmc-rust", "qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True, "gpmc", "rust"),
    ("qft16-ganak-rust", "qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True, "ganak", "rust"),
    ("qaoa7-gpmc-rust", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False, "gpmc", "rust"),
    ("qaoa7-ganak-python", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False, "ganak", "python"),
)
PYTHON_CORE_CASE_IDS = (
    "anf_target_absent", "anf_target_present",
    "hh_pair_match", "elim_candidate", "elim_no_candidate",
)
CROSS_CIRCUITS = (
    ("vqe4", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False),
    ("grover4", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True),
    ("qaoa7", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False),
    ("qft16", "qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True),
    ("graphstate16", "graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False),
    ("ghz32", "ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", True),
)
CROSS_METHOD_CASES = tuple(
    (f"{name}_{solver}_{backend}", filename, strategy, reverse, solver, backend)
    for name, filename, strategy, reverse in CROSS_CIRCUITS
    for solver in ("gpmc", "ganak") for backend in ("rust", "python")
)
CROSS_METHOD_CPU_IDS = frozenset({
    "vqe4_gpmc_rust", "vqe4_ganak_rust",
    "qaoa7_gpmc_rust", "qaoa7_ganak_rust",
})
CROSS_INSTRUMENT_MATCH = {
    "vqe4_gpmc": "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
    "qaoa7_gpmc": "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
    "qft16_gpmc": "qft_nativegates_ibm_qiskit_opt0_16.qasm",
}

@dataclass(frozen=True)
class PilotCase:
    id: str
    qasm: str
    strategy: str = "proportional"
    reverse: bool = False
    backend: str = "rust"
    solver: str = "gpmc"
    method: str = "hybrid"
    # These are hard pilot caps, not accepted production timeouts.
    solver_timeout_s: int = 15
    watchdog_s: int = 24
    expected_verdict: str = "equivalent_or_phase"
    expected_solver_invoked: bool | None = None
    # Explicit positive (transpiled) or negative (Random_Rotation) QASM pair.
    pair_variant: str = "transpiled"
    # New corpus needs a separate CodSpeed benchmark URI and fixture root.
    qasm_corpus: str = "historical"

# Pilot tests DIFFERENT circuit classes; stage is observed, not forced.
# Candidate is not promoted to nightly or every-PR on historical timing alone.
PILOT_CASES = (
    PilotCase("ghz64", "ghz_nativegates_ibm_qiskit_opt0_64.qasm", "straightforward"),
    PilotCase("graphstate32", "graphstate_nativegates_ibm_qiskit_opt0_32.qasm", "naive"),
    PilotCase("qpeexact8", "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm"),
    PilotCase("qpeinexact8", "qpeinexact_nativegates_ibm_qiskit_opt0_8.qasm"),
    PilotCase("qnn4", "qnn_nativegates_ibm_qiskit_opt0_4.qasm"),
    PilotCase("qwalk3", "qwalk-noancilla_nativegates_ibm_qiskit_opt0_3.qasm"),
    PilotCase("wstate4", "wstate_nativegates_ibm_qiskit_opt0_4.qasm"),
    PilotCase("vqe8", "vqe_nativegates_ibm_qiskit_opt0_8.qasm"),
)

# A separate paper-grounded gap screen; the existing eight IDs never change.
# Historical paper seconds are difficulty priors, not current CodSpeed timings.
# Each candidate is bounded and opt-in; no run equals a verdict certificate.
PAPER_GAP_PILOT_CASES = (
    PilotCase("graphstate64_positive",
              "graphstate_nativegates_ibm_qiskit_opt0_64.qasm", "naive"),
    PilotCase("qaoa11_positive",
              "qaoa_nativegates_ibm_qiskit_opt0_11.qasm"),
    PilotCase("qwalk4_positive",
              "qwalk-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"),
    PilotCase("qwalk4_negative",
              "qwalk-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
              expected_verdict="not_equivalent", pair_variant="random_rotation"),
    PilotCase("qpeinexact20_positive",
              "qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm"),
    PilotCase("qpeinexact20_negative",
              "qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm",
              expected_verdict="not_equivalent", pair_variant="random_rotation"),
    PilotCase("qnn8_positive",
              "qnn_nativegates_ibm_qiskit_opt0_8.qasm"),
)

# A representative two-Solver-invoked versus two-RR-terminated repeatability
# matrix, selected from the bounded eight-case evidence. This is an opt-in
# study, NEVER a replacement for the canonical 32 and five shards.
REPEATABILITY_EXPECTATIONS = {
    "qnn4": ("equivalent*", True),
    "vqe8": ("equivalent", True),
    "qpeexact8": ("equivalent*", False),
    "wstate4": ("equivalent*", False),
}
REPEATABILITY_CASES = tuple(
    case for case in PILOT_CASES if case.id in REPEATABILITY_EXPECTATIONS
)

# Qiskit 2.6.1 Level-0 is a NEW measured input identity, never a replacement
# for main's original 32 Simulation IDs or the seven baseline WallTime IDs.
# Every row has source-pinned strict 1e-8 GPMC Python/Rust EQ/NEQ evidence
# in docs/development/mqtbench-qiskit261-level0-acceptance on the TACAS
# research branch; this bounded CodSpeed pilot is a separate timing study.
QASM261_PILOT_CASES = (
    PilotCase("q261_ghz32_positive",
              "ghz_nativegates_ibm_qiskit_opt0_32.qasm",
              "straightforward", reverse=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_graphstate16_positive",
              "graphstate_nativegates_ibm_qiskit_opt0_16.qasm",
              "naive", qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_grover4_positive",
              "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm",
              reverse=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qaoa7_positive",
              "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qaoa7_negative",
              "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qft16_positive",
              "qft_nativegates_ibm_qiskit_opt0_16.qasm",
              reverse=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qft16_negative",
              "qft_nativegates_ibm_qiskit_opt0_16.qasm",
              reverse=True, pair_variant="random_rotation",
              expected_verdict="not_equivalent", qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qnn4_positive",
              "qnn_nativegates_ibm_qiskit_opt0_4.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qnn4_negative",
              "qnn_nativegates_ibm_qiskit_opt0_4.qasm",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_vqe4_positive",
              "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_vqe4_negative",
              "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qpeexact8_positive",
              "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_wstate4_positive",
              "wstate_nativegates_ibm_qiskit_opt0_4.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_vqe8_positive",
              "vqe_nativegates_ibm_qiskit_opt0_8.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_qpeinexact20_positive",
              "qpeinexact_nativegates_ibm_qiskit_opt0_20.qasm",
              qasm_corpus="qiskit-2.6.1-opt0"),
)


# Six *research-only* case IDs selected to fill missing evidence axes:
# WMC-only vs Hybrid, Python vs Rust, WMC positive vs negative, and
# a genuine NEQ Ganak sample.  Zero candidates are routine every-PR cases.
# CodSpeed WallTime is the only timing instrument; this first pass is
# ONE measured round per case, with 15s solver / 24s process watchdog.
# Any timeout is censored (not a zero/24s timing result).
QASM261_COVERAGE_GAP_CASES = (
    PilotCase("q261_gap_qaoa7_neq_wmconly_rust_gpmc",
              "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
              backend="rust", solver="gpmc", method="wmc_only",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              expected_solver_invoked=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_gap_qaoa7_neq_wmconly_python_gpmc",
              "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
              backend="python", solver="gpmc", method="wmc_only",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              expected_solver_invoked=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_gap_qaoa7_neq_hybrid_python_gpmc",
              "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
              backend="python", solver="gpmc", method="hybrid",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              expected_solver_invoked=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_gap_qft16_neq_hybrid_python_gpmc",
              "qft_nativegates_ibm_qiskit_opt0_16.qasm",
              backend="python", solver="gpmc", method="hybrid", reverse=True,
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              expected_solver_invoked=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_gap_vqe8_eq_wmconly_rust_gpmc",
              "vqe_nativegates_ibm_qiskit_opt0_8.qasm",
              backend="rust", solver="gpmc", method="wmc_only",
              expected_verdict="equivalent_or_phase",
              expected_solver_invoked=True, qasm_corpus="qiskit-2.6.1-opt0"),
    PilotCase("q261_gap_qaoa7_neq_hybrid_rust_ganak",
              "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
              backend="rust", solver="ganak", method="hybrid",
              pair_variant="random_rotation", expected_verdict="not_equivalent",
              expected_solver_invoked=True, qasm_corpus="qiskit-2.6.1-opt0"),
)
