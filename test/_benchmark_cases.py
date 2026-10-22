"""CI-sized benchmark selection shared by pytest-benchmark and CodSpeed.

Each tuple is (QASM filename, reduction strategy, reverse-input order).
Preserve order and values unless intentionally updating performance baselines:
pytest node IDs and CodSpeed shard membership depend on these tuples.
These are existing, proven CI cases, not the full paper reproduction matrix.
"""

MQT_CASES = (
    ("ghz_nativegates_ibm_qiskit_opt0_32.qasm", "straightforward", True),
    ("graphstate_nativegates_ibm_qiskit_opt0_16.qasm", "naive", False),
    ("grover-noancilla_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", True),
    ("qaoa_nativegates_ibm_qiskit_opt0_7.qasm", "proportional", False),
    ("qft_nativegates_ibm_qiskit_opt0_16.qasm", "proportional", True),
    ("vqe_nativegates_ibm_qiskit_opt0_4.qasm", "proportional", False),
)

FEYNMAN_CASES = (
    ("adder_8.qasm", "proportional", False),
    ("gf2^4_mult.qasm", "proportional", False),
    ("tof_3.qasm", "proportional", True),
    ("vbe_adder_3.qasm", "proportional", True),
)