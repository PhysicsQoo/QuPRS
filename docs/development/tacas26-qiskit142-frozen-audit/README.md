# TACAS 2026 Qiskit 1.4.2 original QASM numerical check

Paper Table 2 used Qiskit 1.4.2 for H/Ry/Rz/CX transpilation.
The Feynman appendix was separately transpiled with Qiskit 1.2.4.
This experiment imports exact archived Table 2 original and transpiled
QASM files with Qiskit 1.4.2. It DOES NOT re-transpile them.
Every pair is matched against the existing Ganak source-pinned SHA256.

| Circuit | Qubits | Numerical check | Floating distance or maximum sample state difference | Ganak printed-point D |
|---|---:|---|---:|---:|
| graphstate64 | 64 | NOT_MEASURED_RESOURCE_BOUND | not measured | 5.4520449e-05 |
| grover4 | 4 | FULL_FLOAT_OPERATOR | 7.7428705e-08 | 2.2606715e-05 |
| grover6 | 6 | FULL_FLOAT_OPERATOR | 0 | 4.2980792e-05 |
| qaoa11 | 11 | SAMPLED_FLOAT_STATEVECTORS | 4.2886891e-15 | 4.2676283e-05 |
| qaoa9 | 9 | SAMPLED_FLOAT_STATEVECTORS | 2.4041273e-15 | 2.1686139e-05 |
| qft16 | 16 | SAMPLED_FLOAT_STATEVECTORS | 2.0586634e-15 | 5.7211512e-05 |
| qft20 | 20 | NOT_MEASURED_RESOURCE_BOUND | not measured | 3.5643387e-05 |
| qft22 | 22 | NOT_MEASURED_RESOURCE_BOUND | not measured | 3.4861714e-05 |
| qnn4 | 4 | FULL_FLOAT_OPERATOR | 0 | 3.2368777e-05 |
| qnn8 | 8 | FULL_FLOAT_OPERATOR | 0 | 3.736904e-05 |
| qpeexact20 | 20 | NOT_MEASURED_RESOURCE_BOUND | not measured | 2.2606715e-05 |
| qpeinexact16 | 16 | SAMPLED_FLOAT_STATEVECTORS | 3.4616653e-15 | 7.732986e-05 |
| qpeinexact8 | 8 | FULL_FLOAT_OPERATOR | 4.2146849e-08 | 8.2876443e-05 |
| qwalk3 | 3 | FULL_FLOAT_OPERATOR | 5.3726901e-08 | 3.2445524e-05 |
| vqe16 | 16 | SAMPLED_FLOAT_STATEVECTORS | 1.0624871e-11 | 4.8513207e-05 |
| vqe4 | 4 | FULL_FLOAT_OPERATOR | 2.9802322e-08 | 2.2606715e-05 |
| wstate8 | 8 | FULL_FLOAT_OPERATOR | 4.4703484e-08 | 2.6190632e-05 |

The float-only Qiskit matrix comparison does not certify exact
semantic equivalence, nor does it prove transpiler or solver fault.
The sample-state differences for n>8 cannot be substituted into
the QuPRS trace-based projective distance decision.
See qiskit142-20.json for pinned QASM SHA256 and sample overlap details.
Science-only: no CodSpeed performance data and no Solver runs.
