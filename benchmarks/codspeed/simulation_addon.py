"""12 distinct source-pinned QASM261 Hybrid CPU cases; preserve original legacy 32.

Before v0.14 release, retire only the 12 additive Ganak aliases: external
Solver is excluded from CPU Simulation. Ganak itself is timed by WallTime.
The 12 surviving GPMC URI identities remain byte-for-byte stable.
"""
from __future__ import annotations

CORPUS_VERSION = "qiskit-2.6.1-opt0"
CORPUS_BASE = "benchmarks/MQTBench"
QASM261_CASES = (
    ("ghz32", "ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", True),
    ("graphstate16", "graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False),
    ("grover4", "grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True),
    ("qaoa7", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False),
    ("qft16", "qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True),
    ("vqe4", "vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False),
)
SOLVERS = ("gpmc",)  # CPU modeled instruction work, not a child Solver comparison
BACKENDS = ("python", "rust")
QASM261_SUITE_ID = "qiskit-2.6.1-opt0-v2-cpu"
QASM261_NODE_PREFIX = "benchmarks/codspeed/test_mqt_qasm261_simulation.py::test_versioned_mqt_simulation"
QASM261_URIS = tuple(
    f"{QASM261_NODE_PREFIX}[q261_{case_id}_{solver}_{backend}]"
    for case_id, _, _, _ in QASM261_CASES
    for solver in SOLVERS
    for backend in BACKENDS
)
QASM261_COUNT = 12
QASM261_SHA256 = "59d46eb951ca5280fddd19000ca14bfc45a71ea22717b178e76b76fd715e9a18"
