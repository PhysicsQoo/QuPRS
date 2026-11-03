# TACAS 2026 Qiskit 1.4.2 original QASM numerical check

Paper Table 2 used Qiskit 1.4.2 for H/Ry/Rz/CX transpilation.
The Feynman appendix was separately transpiled with Qiskit 1.2.4.
This experiment imports exact archived Table 2 original and transpiled
QASM files with Qiskit 1.4.2. It DOES NOT re-transpile them.
Every pair is matched against the existing Ganak source-pinned SHA256.

| Circuit | Qubits | Numerical check | Qiskit floating distance or sample-state difference | GPMC30 printed-point D | Ganak6 printed-point D |
|---|---:|---|---:|---:|---:|
| graphstate64 | 64 | NOT_MEASURED_RESOURCE_BOUND | not measured | 4.0805497e-15 | 5.4520449e-05 |
| grover4 | 4 | FULL_FLOAT_OPERATOR | 7.7428705e-08 | 1.1068519e-15 | 2.2606715e-05 |
| grover6 | 6 | FULL_FLOAT_OPERATOR | 0 | 7.7510554e-15 | 4.2980792e-05 |
| qaoa11 | 11 | SAMPLED_FLOAT_STATEVECTORS | 4.2886891e-15 | 6.2233417e-16 | 4.2676283e-05 |
| qaoa9 | 9 | SAMPLED_FLOAT_STATEVECTORS | 2.4041273e-15 | nonphysical† | 2.1686139e-05 |
| qft16 | 16 | SAMPLED_FLOAT_STATEVECTORS | 2.0586634e-15 | 2.9802322e-15 | 5.7211512e-05 |
| qft20 | 20 | SAMPLED_FLOAT_STATEVECTORS | 5.4012172e-06 | 7.0263747e-06 | 3.5643387e-05 |
| qft22 | 22 | SAMPLED_FLOAT_STATEVECTORS | 9.3925885e-06 | 1.1494377e-05 | 3.4861714e-05 |
| qnn4 | 4 | FULL_FLOAT_OPERATOR | 0 | 4.9737567e-15 | 3.2368777e-05 |
| qnn8 | 8 | FULL_FLOAT_OPERATOR | 0 | 7.4207463e-15 | 3.736904e-05 |
| qpeexact20 | 20 | SAMPLED_FLOAT_STATEVECTORS | 2.9960562e-06 | 4.2370633e-06 | 2.2606715e-05 |
| qpeinexact16 | 16 | SAMPLED_FLOAT_STATEVECTORS | 3.4616653e-15 | nonphysical† | 7.732986e-05 |
| qpeinexact8 | 8 | FULL_FLOAT_OPERATOR | 4.2146849e-08 | nonphysical† | 8.2876443e-05 |
| qwalk3 | 3 | FULL_FLOAT_OPERATOR | 5.3726901e-08 | 1.4901161e-15 | 3.2445524e-05 |
| vqe16 | 16 | SAMPLED_FLOAT_STATEVECTORS | 1.0624871e-11 | 1.0770159e-11 | 4.8513207e-05 |
| vqe4 | 4 | FULL_FLOAT_OPERATOR | 2.9802322e-08 | nonphysical† | 2.2606715e-05 |
| wstate8 | 8 | FULL_FLOAT_OPERATOR | 4.4703484e-08 | 2.3008598e-15 | 2.6190632e-05 |

The float-only Qiskit matrix comparison does not certify exact
semantic equivalence, nor does it prove transpiler or solver fault.
The sample-state differences for n>8 cannot be substituted into
the QuPRS trace-based projective distance decision.
See qiskit142-20.json for pinned QASM SHA256 and sample overlap details.
Science-only: no CodSpeed performance data and no Solver runs.

## GPMC30 printed-point distance provenance

Original Python/GPMC MPFR30 run: https://github.com/PhysicsQoo/QuPRS/actions/runs/41481701901 (source SHA ff4d3032a83c0ae18ba3a7d195cb1b1a8804492f). Distances are inferred from the exact fractional interpretation of solver-printed complex components with normalization 2**k; the trace-based printed-point formula is sqrt(1-(Re(WMC)**2+Im(WMC)**2)/2**k). The accompanying 20-row CSV preserves each case's root argument and exponent k. Solver arithmetic error is NOT_CERTIFIED.

† The printed-root argument is slightly negative for five cases due to magnitude exceeding physical normalization by approximately 1e-30 to 1e-61; no real-valued D follows and no clipping to zero is performed. QFT20, QFT22, QPEexact20 have nonzero GPMC printed-point D around 7.03e-6, 1.15e-5 and 4.24e-6, all below the 2e-5 paper-reproduction threshold. Qiskit values for >8 qubits reflect sampled state differences instead of a global trace-based operator distance. Float64 operator-distance calculations near zero can also show an artificial 1e-8 floor from cancellation.
