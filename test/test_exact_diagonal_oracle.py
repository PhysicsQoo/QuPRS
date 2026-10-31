"""Bounded strict source proof, independent of QuPRS and numerical WMC."""
import pytest
from _exact_diagonal_oracle import certify


def qasm(ops="", n=1):
    return 'OPENQASM 2.0;\ninclude "qelib1.inc";\n' + f'qreg q[{n}];\n{ops}'


@pytest.mark.parametrize("a,b,expected,witness", [
    ("", "rz(0.0002) q[0];", "not_equivalent", 0),
    ("", "rz(0.001) q[0];", "not_equivalent", 0),
    ("", "rz(1e-9) q[0];", "not_equivalent", 0),
    ("", "rz(1e-100) q[0];", "not_equivalent", 0),
    ("", "rz(0e-1000) q[0];", "equivalent", None),
    ("rz(0.0002) q[0];\nrz(-0.0002) q[0];", "", "equivalent", None),
    ("rz(pi/8) q[0];\nrz(pi/8) q[0];", "rz(pi/4) q[0];", "equivalent", None),
    ("rz(pi/8) q[0];", "rz(0.39269908169872414) q[0];", "not_equivalent", 0),
    ("rz(1e-9) q[0];", "p(1e-9) q[0];", "equivalent*", None),
    ("rz(pi) q[0];\nrz(pi) q[0];", "", "equivalent*", None),
    ("p(pi/2) q[0];\np(pi/2) q[0];\np(pi/2) q[0];\np(pi/2) q[0];",
     "", "equivalent", None),
])
def test_diagonal_exact_contract(a, b, expected, witness):
    result = certify(qasm(a), qasm(b))
    assert (result.verdict, result.witness_qubit) == (expected, witness)
    assert result.scope == "exact-qasm2-diagonal-rz-p-v1"
    assert len(result.left_sha256) == len(result.right_sha256) == 64


def test_two_qubit_source_witness():
    lhs = qasm("p(pi/8) q[0];\nrz(0.001) q[1];", n=2)
    rhs = qasm("rz(0.001) q[1];\np(pi/8) q[0];", n=2)
    assert certify(lhs, rhs).verdict == "equivalent"
    altered = qasm("rz(0.000999999) q[1];\np(pi/8) q[0];", n=2)
    assert (certify(lhs, altered).verdict,
            certify(lhs, altered).witness_qubit) == ("not_equivalent", 1)


@pytest.mark.parametrize("bad", [
    "h q[0];", "cx q[0],q[0];", "rz(pi*pi) q[0];",
    "rz(1/0) q[0];", "rz(nan) q[0];", "rz(0.1) q[1];",
    "rz(1e1000000) q[0];", "rz(1e-1000000) q[0];",
])
def test_unsupported_input_rejected(bad):
    with pytest.raises(ValueError):
        certify(qasm(bad), qasm())


@pytest.mark.parametrize("left,right,expected", [
    ("", "rz(0.0002) q[0];", "not_equivalent"),
    ("", "rz(0.001) q[0];", "not_equivalent"),
    ("rz(0.0002) q[0];\nrz(-0.0002) q[0];", "", "equivalent"),
    ("rz(pi/8) q[0];", "rz(0.39269908169872414) q[0];", "not_equivalent"),
    ("rz(1e-9) q[0];", "p(1e-9) q[0];", "equivalent*"),
])
def test_rust_rr_agrees_with_independent_diagonal_oracle(left, right, expected):
    from QuPRS import check_equivalence
    source_a, source_b = qasm(left), qasm(right)
    assert certify(source_a, source_b).verdict == expected
    result = check_equivalence(
        source_a, source_b, method="reduction_rules", backend="rust",
        strategy="Naive", tool_name="gpmc", timeout=30,
        # Independent source oracle treats any nonzero global phase as nonzero.
        # Use a tighter phase label threshold for these fixed test cases.
        phase_tolerance=1e-12,
    )
    # Exact symbolic source identity and tolerance-aware RR are distinct contracts.
    # pi/8 and its finite decimal approximation differ exactly, but fall
    # within the verifier's default approximate RR tolerance.
    approximate_expected = (
        "equivalent"
        if left == "rz(pi/8) q[0];" and right == "rz(0.39269908169872414) q[0];"
        else expected
    )
    assert result.equivalent == approximate_expected
    assert result.tool_time is None
