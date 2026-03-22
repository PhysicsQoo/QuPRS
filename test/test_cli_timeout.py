
import pytest
import subprocess
import os
import shutil

def find_cli_binary():
    # Try common target locations
    paths = [
        "rust/target/release/QuPRS_cli",
        "rust/target/debug/QuPRS_cli",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    # Try cargo run if not found
    return "cargo run --quiet --manifest-path rust/Cargo.toml --bin QuPRS_cli --"

def test_cli_timeout_single_circuit():
    """
    Test that the CLI tool correctly reports timeout in single circuit mode.
    """
    cli = find_cli_binary()
    qasm_file = "benchmarks/MQTBench/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_16.qasm"
    
    if not os.path.exists(qasm_file):
        pytest.skip(f"Benchmark file {qasm_file} not found")

    # Run CLI with 0s timeout
    cmd = cli.split() + [qasm_file, "--timeout", "0"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check stdout/stderr for timeout warning
    # display.rs: "⚠️  TIMEOUT"
    # runner.rs: "⚠️  WARNING: Reduction aborted due to timeout."
    combined_output = result.stdout + result.stderr
    assert "TIMEOUT" in combined_output or "timeout" in combined_output
    assert "WARNING" in combined_output
    print("CLI Single Circuit Timeout verified.")

def test_cli_timeout_dual_circuit():
    """
    Test that the CLI tool correctly reports timeout in dual circuit mode.
    """
    cli = find_cli_binary()
    qasm_file = "benchmarks/MQTBench/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_16.qasm"
    
    if not os.path.exists(qasm_file):
        pytest.skip(f"Benchmark file {qasm_file} not found")

    # Run CLI to compare file with itself with 0s timeout
    cmd = cli.split() + [qasm_file, qasm_file, "--timeout", "0"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    combined_output = result.stdout + result.stderr
    assert "TIMEOUT" in combined_output or "timeout" in combined_output
    print("CLI Dual Circuit Timeout verified.")
