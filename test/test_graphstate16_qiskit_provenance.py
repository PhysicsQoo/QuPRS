"""Independent P0/P1 source-QASM and Qiskit statevector checks for Graphstate16.

No QuPRS PathSum, reduction rules, CNF, or solver is used for these tests.
These checks corroborate the intended Graphstate state preparation and gate
semantics numerically, but cannot certify an arbitrary 16-qubit full unitary
from a finite set of sampled input states.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from qiskit import qasm2
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[1]
NAME = "graphstate_nativegates_ibm_qiskit_opt0_16.qasm"
SOURCES = (
    ROOT / "benchmarks/MQTBench" / NAME,
    ROOT / "benchmarks/MQTBench/h,ry,rz,cx" / NAME,
)
GIT_BLOBS = (
    "ab34308febb31ea9a49e9761a988aad7017f3487",
    "c2c6f9d04f6a8c2778415572aa247ee93e138c09",
)
CX = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$", re.MULTILINE)
N = 16
SIZE = 1 << N


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode()
                        + b"\0" + data).hexdigest()


def _source_and_edges():
    assert tuple(map(_blob, SOURCES)) == GIT_BLOBS
    a, b = (p.read_text(encoding="utf-8") for p in SOURCES)
    edges_a = [(int(x), int(y)) for x, y in CX.findall(a)]
    edges_b = [(int(x), int(y)) for x, y in CX.findall(b)]
    assert edges_a == edges_b and len(edges_a) == 16
    assert len({frozenset(e) for e in edges_a}) == 16
    degree = Counter(q for edge in edges_a for q in edge)
    assert sorted(degree) == list(range(N))
    assert set(degree.values()) == {2}
    return a, b, edges_a


def _graphstate_reference(edges):
    """Graphstate |G> = prod_(u,v) CZ_uv * H^16 |0>, up to global phase."""
    indices = np.arange(SIZE, dtype=np.int32)
    parity = np.zeros(SIZE, dtype=np.int8)
    for u, v in edges:
        parity ^= (((indices >> u) & 1) & ((indices >> v) & 1)).astype(np.int8)
    return np.where(parity == 0, 1.0, -1.0).astype(np.complex128) / np.sqrt(SIZE)


def _phase_aligned_l2(a, b):
    overlap = np.vdot(a, b)
    assert abs(overlap) > 0.5
    return np.linalg.norm(a - b * (np.conj(overlap) / abs(overlap)))


@pytest.fixture(scope="module")
def source_circuits():
    a, b, edges = _source_and_edges()
    # Qiskit is an independent QASM importer/statevector engine here.
    circuit_a, circuit_b = qasm2.loads(a), qasm2.loads(b)
    assert circuit_a.num_qubits == circuit_b.num_qubits == N
    assert not circuit_a.clbits and not circuit_b.clbits
    assert circuit_a.count_ops().get("cx") == circuit_b.count_ops().get("cx") == 16
    return circuit_a, circuit_b, edges


def test_graphstate_source_pins_and_regular_graph(source_circuits):
    _, _, edges = source_circuits
    assert len(edges) == 16


def test_graphstate_both_qasm_prepare_same_full_graph_state(source_circuits):
    """Compare *all* 2^16 output amplitudes for the |0> state preparation."""
    circuit_a, circuit_b, edges = source_circuits
    expected = _graphstate_reference(edges)
    for circuit in (circuit_a, circuit_b):
        vector = Statevector.from_instruction(circuit).data
        assert abs(np.linalg.norm(vector) - 1) < 1e-10
        assert _phase_aligned_l2(expected, vector) < 1e-10


@pytest.mark.parametrize("basis", [0, 1, 1 << 3, 1 << 12, SIZE - 1])
def test_graphstate_source_qasm_unitary_basis_samples(source_circuits, basis):
    """Matrix-free check of representative columns; not full-unitary proof."""
    a, b, _ = source_circuits
    state = Statevector.from_int(basis, SIZE)
    output_a, output_b = state.evolve(a).data, state.evolve(b).data
    assert abs(np.linalg.norm(output_a) - 1) < 1e-10
    assert abs(np.linalg.norm(output_b) - 1) < 1e-10
    assert _phase_aligned_l2(output_a, output_b) < 1e-10


def test_graphstate_independent_qiskit_detects_rotation_error(source_circuits):
    """A deliberately changed angle must be detectable as genuinely wrong."""
    circuit_a, _, _ = source_circuits
    b = SOURCES[1].read_text(encoding="utf-8")
    needle = "ry(2.0330832984526417) q[1];"
    assert b.count(needle) == 1
    mutated = b.replace(needle, "ry(2.0340832984526417) q[1];")
    circuit_mutated = qasm2.loads(mutated)
    original_state = Statevector.from_instruction(circuit_a).data
    corrupted_state = Statevector.from_instruction(circuit_mutated).data
    assert _phase_aligned_l2(original_state, corrupted_state) > 1e-4


def test_graphstate_transpilation_provenance_is_not_fabricated(source_circuits):
    """QASM contents prove gate-level properties, not the old compiler build."""
    a, b, _ = source_circuits
    assert a.startswith("// Used Gate Set:")
    assert "OPENQASM 2.0;" in a and "OPENQASM 2.0;" in b
    # Do not infer the exact Qiskit version or random seed from a filename.
    assert "qiskit_version=" not in a + b
    assert "seed_transpiler=" not in a + b
