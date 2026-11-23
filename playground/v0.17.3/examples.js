// One source of truth for the browser's independently checked circuit pairs.
// These are small unitary OpenQASM 2 examples, not formal proof certificates.
const qasm = (gates, qubits) =>
  'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[' + qubits + '];\n' +
  (gates ? gates + '\n' : '');
export const CATEGORIES = Object.freeze([
  {
    "id": "equivalent",
    "title": "Exact unitary identities"
  },
  {
    "id": "decomposition",
    "title": "Decompositions and multi-qubit gates"
  },
  {
    "id": "global_phase",
    "title": "Global-phase equivalence"
  },
  {
    "id": "different",
    "title": "Non-equivalent circuits"
  },
  {
    "id": "tolerance",
    "title": "Numerical tolerance examples"
  }
]);
const entries = [
  {
    "id": "identity",
    "title": "H·H = I",
    "category": "equivalent",
    "description": "Hadamard is its own inverse.",
    "qubits": 1,
    "gatesA": "h q[0];\nh q[0];",
    "gatesB": "",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "phase",
    "title": "Small phase difference",
    "category": "tolerance",
    "description": "A nonzero phase rotation is detectable beyond the selected tolerance.",
    "qubits": 1,
    "gatesA": "u1(0.000001) q[0];",
    "gatesB": "",
    "mode": "wmc",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "different"
  },
  {
    "id": "cz",
    "title": "CZ decomposition",
    "category": "decomposition",
    "description": "Hadamard conjugation transforms CX to CZ.",
    "qubits": 2,
    "gatesA": "cz q[0],q[1];",
    "gatesB": "h q[1];\ncx q[0],q[1];\nh q[1];",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "hzh",
    "title": "H·Z·H = X",
    "category": "decomposition",
    "description": "Hadamard conjugates Pauli Z into Pauli X.",
    "qubits": 1,
    "gatesA": "h q[0];\nz q[0];\nh q[0];",
    "gatesB": "x q[0];",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "ss",
    "title": "S·S = Z",
    "category": "equivalent",
    "description": "Two S gates equal Z.",
    "qubits": 1,
    "gatesA": "s q[0];\ns q[0];",
    "gatesB": "z q[0];",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "xx",
    "title": "X·X = I",
    "category": "equivalent",
    "description": "Two bit flips cancel.",
    "qubits": 1,
    "gatesA": "x q[0];\nx q[0];",
    "gatesB": "",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "ttdg",
    "title": "T·T† = I",
    "category": "equivalent",
    "description": "The inverse phase gate restores the original circuit.",
    "qubits": 1,
    "gatesA": "t q[0];\ntdg q[0];",
    "gatesB": "",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "reverse-cx",
    "title": "Reverse CX with H",
    "category": "decomposition",
    "description": "Hadamard gates on both wires reverse CX control and target.",
    "qubits": 2,
    "gatesA": "h q[0];\nh q[1];\ncx q[0],q[1];\nh q[0];\nh q[1];",
    "gatesB": "cx q[1],q[0];",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "cx-cancel",
    "title": "CX·CX = I",
    "category": "equivalent",
    "description": "Two controlled-X gates cancel.",
    "qubits": 2,
    "gatesA": "cx q[0],q[1];\ncx q[0],q[1];",
    "gatesB": "",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "commute",
    "title": "Independent gates commute",
    "category": "equivalent",
    "description": "Disjoint one-qubit gates can exchange order.",
    "qubits": 2,
    "gatesA": "h q[0];\nx q[1];",
    "gatesB": "x q[1];\nh q[0];",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  },
  {
    "id": "x-different",
    "title": "X ≠ I",
    "category": "different",
    "description": "A Pauli-X changes the unitary, not merely its global phase.",
    "qubits": 1,
    "gatesA": "x q[0];",
    "gatesB": "",
    "mode": "wmc",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "different"
  },
  {
    "id": "t-different",
    "title": "T ≠ I",
    "category": "different",
    "description": "A relative phase is not a global phase.",
    "qubits": 1,
    "gatesA": "t q[0];",
    "gatesB": "",
    "mode": "wmc",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "different"
  },
  {
    "id": "rz-p",
    "title": "RZ and U1 differ by global phase",
    "category": "global_phase",
    "description": "RZ(π/2) and U1(π/2) share a projective unitary.",
    "qubits": 1,
    "gatesA": "rz(pi/2) q[0];",
    "gatesB": "u1(pi/2) q[0];",
    "mode": "wmc",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "phase_equivalent"
  },
  {
    "id": "ghz-order",
    "title": "Independent GHZ entanglers",
    "category": "decomposition",
    "description": "Target-disjoint CX gates commute after preparing the control.",
    "qubits": 3,
    "gatesA": "h q[0];\ncx q[0],q[1];\ncx q[0],q[2];",
    "gatesB": "h q[0];\ncx q[0],q[2];\ncx q[0],q[1];",
    "mode": "hybrid",
    "strategy": "difference",
    "distance_tolerance": 1e-8,
    "rr_tolerance": 1e-10,
    "expected": "equivalent"
  }
];
export const EXAMPLES = Object.freeze(entries.map(({gatesA,gatesB,...meta}) =>
  Object.freeze({...meta,circuit1:qasm(gatesA,meta.qubits),circuit2:qasm(gatesB,meta.qubits)})));
