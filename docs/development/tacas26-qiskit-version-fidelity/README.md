# TACAS26 Qiskit 1.4.2 versus 2.6.1 transpiler numerical fidelity

Source QASM: original paper MQTBench inputs, fixed Git blobs and SHA256.
Each Qiskit version receives the same source, terminal measurements
removed, same target H/Ry/Rz/CX basis, same seed 42, optimization
levels 0 and 3, approximation degree 1.0. Each result is QASM2
serialized and reloaded before comparison with original.
The original paper's saved transpiled QASM is a third comparator
with UNKNOWN original optimization settings.

Qubits 1-8: full operator projective trace distance from stabilized
phase-aligned normalized Frobenius. Qubits 9-22: maximum of the
phase-aligned state distances for |0> and |+> inputs; these are NOT
the trace-based projective operator distance and do NOT bound it.
Float64 computation does NOT certify mathematically exact equality.

| Case | Qubit | Opt | Saved historic | Qiskit 1.4.2 | Qiskit 2.6.1 | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| grover4 | 4 | 0 | 2.06698e-15 | 3.522861e-15 | 4.181197e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| grover4 | 4 | 3 | 2.06698e-15 | 2.06698e-15 | 2.034913e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qnn8 | 8 | 0 | 7.013441e-15 | 6.87399e-15 | 8.590198e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qnn8 | 8 | 3 | 7.013441e-15 | 7.125857e-15 | 1.738272e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qpeinexact8 | 8 | 0 | 1.179186e-15 | 2.138493e-15 | 2.370325e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qpeinexact8 | 8 | 3 | 1.179186e-15 | 1.179186e-15 | 1.163438e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qaoa9 | 9 | 0 | 2.132173e-15 | 7.502213e-15 | 8.10807e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qaoa9 | 9 | 3 | 2.132173e-15 | 2.095486e-15 | 3.441619e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qft16 | 16 | 0 | 2.058663e-15 | 2.906671e-15 | 3.161796e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qft16 | 16 | 3 | 2.058663e-15 | 2.030903e-15 | 2.396845e-05 | LATEST_LARGER |
| vqe16 | 16 | 0 | 1.062487e-11 | 1.425727e-14 | 1.740745e-14 | BOTH_AT_FLOAT_NOISE_FLOOR |
| vqe16 | 16 | 3 | 1.062487e-11 | 1.06249e-11 | 2.212814e-15 | LATEST_SMALLER |
| qft20 | 20 | 0 | 5.401217e-06 | 3.092478e-15 | 3.507026e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qft20 | 20 | 3 | 5.401217e-06 | 5.401217e-06 | 8.833286e-05 | LATEST_LARGER |
| qft22 | 22 | 0 | 9.392588e-06 | 3.244961e-15 | 3.975202e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qft22 | 22 | 3 | 9.392588e-06 | 9.392588e-06 | 0.0001100719 | LATEST_LARGER |
| qpeexact20 | 20 | 0 | 2.996056e-06 | 7.698024e-15 | 6.840546e-15 | BOTH_AT_FLOAT_NOISE_FLOOR |
| qpeexact20 | 20 | 3 | 2.996056e-06 | 2.996056e-06 | 7.514071e-05 | LATEST_LARGER |

No performance timings are claimed. CodSpeed required for timing.
Graphstate64 intentionally excluded due to simulation resource
constraints. The historical source QASM is NOT rewritten.
Full diagnostics in qiskit142.json, qiskit261.json and comparison.json.
