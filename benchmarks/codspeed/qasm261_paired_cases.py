"""Frozen Qiskit 2.6.1 Level-0 GPMC candidates, independent CodSpeed URIs.

Five fixtures observed to invoke GPMC in the first Rust/GPMC pilot.
Promotion is based on *new* same-fixture base/HEAD evidence, not historical
QASM runtimes. Science oracle: experiment TACAS run 41573879894.
"""
# (case_id, filename, strategy, reverse, variant, expected_binary)
GPMC_PAIRS = (
    ("q261_qaoa7_negative", "qaoa_nativegates_ibm_qiskit_opt0_7.qasm",
     "proportional", False, "random_rotation", "not_equivalent"),
    ("q261_qft16_negative", "qft_nativegates_ibm_qiskit_opt0_16.qasm",
     "proportional", True, "random_rotation", "not_equivalent"),
    ("q261_qnn4_negative", "qnn_nativegates_ibm_qiskit_opt0_4.qasm",
     "proportional", False, "random_rotation", "not_equivalent"),
    ("q261_vqe4_negative", "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
     "proportional", False, "random_rotation", "not_equivalent"),
    ("q261_vqe8_positive", "vqe_nativegates_ibm_qiskit_opt0_8.qasm",
     "proportional", False, "transpiled", "equivalent"),
)
POSITIONS = (("A1", "base"), ("B1", "head"), ("B2", "head"), ("A2", "base"))
