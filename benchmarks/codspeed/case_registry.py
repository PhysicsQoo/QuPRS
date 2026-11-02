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
