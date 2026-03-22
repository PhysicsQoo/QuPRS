
import pytest
import time
from qiskit import QuantumCircuit
from QuPRS.interface.load_qiskit import check_equivalence

def test_timeout_mechanism_rust():
    """
    Test that the Rust backend correctly identifies and reports a timeout.
    """
    # Create a circuit large enough that reduction takes more than 0.001s
    qc = QuantumCircuit(50)
    for _ in range(20):
        for i in range(50):
            qc.h(i)
            qc.t(i)
            qc.cx(i, (i + 1) % 50)
    
    # Use a very short timeout (0s) to trigger check immediately after global start
    result = check_equivalence(qc, qc, method="hybrid", timeout=0, backend="rust")
    
    assert result.equivalent == "timeout", f"Expected 'timeout' but got '{result.equivalent}'"
    print(f"Timeout correctly triggered in {result.verification_time:.4f}s")

def test_timeout_mechanism_python():
    """
    Test that the Python backend correctly identifies and reports a timeout.
    """
    # Create a circuit large enough to take more than 1 second in Python
    qc = QuantumCircuit(50)
    for _ in range(100):
        for i in range(50):
            qc.h(i)
            qc.t(i)
            qc.cx(i, (i + 1) % 50)
    
    # Python uses signal.alarm which is per-second
    result = check_equivalence(qc, qc, method="hybrid", timeout=1, backend="python")
    
    assert result.equivalent == "timeout", f"Expected 'timeout' but got '{result.equivalent}'"
    print(f"Python Timeout correctly triggered in {result.verification_time}")
