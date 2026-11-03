"""Additive Qiskit 2.6.1 Level-0 Simulation identities. Do not edit legacy 32."""
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
SOLVERS = ("gpmc", "ganak")
BACKENDS = ("python", "rust")
QASM261_NODE_PREFIX = "benchmarks/codspeed/test_mqt_qasm261_simulation.py::test_versioned_mqt_simulation"
QASM261_URIS = tuple(
    f"{QASM261_NODE_PREFIX}[q261_{case_id}_{solver}_{backend}]"
    for case_id, _, _, _ in QASM261_CASES
    for solver in SOLVERS
    for backend in BACKENDS
)
QASM261_COUNT = 24
QASM261_SHA256 = "b19b1331f912f7abd976bfa6911d1969c718b4159211f428506f2b8a4ebb49aa"
