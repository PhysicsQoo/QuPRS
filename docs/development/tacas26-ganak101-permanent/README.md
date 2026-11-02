# TACAS 2026: Ganak 101 science and the 20 EQ-to-NEQ cases

Research-only source-pinned archive, **not** a production release or
certified numerical error bound. Original QuPRS v0.9.1 SHA: e928abc47dd15926364ec77905eb0d5dc92ce8cc.
Ganak run: https://github.com/PhysicsQoo/QuPRS/actions/runs/41540814150
GPMC comparison run: https://github.com/PhysicsQoo/QuPRS/actions/runs/41485674318

All 24 original Ganak mode-6 CI shards were independently checked against
GPMC case, verdict and QASM source SHA256 identities. Exactly 101 cases,
45 historic EQ and 56 historic NEQ, with zero timeout/missing cases.

**Ganak at distance=2e-5, RR=1e-10, phase=1e-8: 81/101 match; 20
false NEQ; 0 false EQ.** All 56 historic NEQ remain NEQ; 25/45 historic
EQ remain EQ. All 20 mismatches actually called Ganak (14 WMC-only,
6 Hybrid). GPMC Python30, Rust30 and Python90 reproduce all 101 historic
binary decisions independently in the comparison run.

## Twenty discordant cases

Each point distance below is INFERRED from float-parsed printed log2 WMC
magnitude via sqrt(1 - exp(2*ln(2)*(log2_WMC - expected_log2))).
It is NOT a certified quantum projective distance. The resolution column
is a QuPRS output-format diagnostic, NOT a proven Solver rounding bound.

| Case | Method | Inferred point D | Printed resolution D | Resolution / threshold |
|---|---|---:|---:|---:|
| table2:graphstate64:positive:wmc_only | wmc_only | 5.452045e-05 | 8.493094e-05 | 4.25 |
| table2:grover4:positive:hybrid | hybrid | 2.260672e-05 | 7.344928e-05 | 3.67 |
| table2:grover4:positive:wmc_only | wmc_only | 3.244552e-05 | 5.890201e-05 | 2.95 |
| table2:grover6:positive:wmc_only | wmc_only | 4.298079e-05 | 6.372368e-05 | 3.19 |
| table2:qaoa11:positive:wmc_only | wmc_only | 4.267628e-05 | 7.398528e-05 | 3.70 |
| table2:qaoa9:positive:hybrid | hybrid | 2.168614e-05 | 8.652621e-05 | 4.33 |
| table2:qaoa9:positive:wmc_only | wmc_only | 2.666104e-05 | 4.8487e-05 | 2.42 |
| table2:qft16:positive:wmc_only | wmc_only | 5.721151e-05 | 9.424322e-05 | 4.71 |
| table2:qft20:positive:hybrid | hybrid | 3.564339e-05 | 5.670581e-05 | 2.84 |
| table2:qft22:positive:wmc_only | wmc_only | 3.486171e-05 | 0.0001301563 | 6.51 |
| table2:qnn4:positive:hybrid | hybrid | 3.236878e-05 | 5.394797e-05 | 2.70 |
| table2:qnn8:positive:wmc_only | wmc_only | 3.736904e-05 | 9.117017e-05 | 4.56 |
| table2:qpeexact20:positive:hybrid | hybrid | 2.260672e-05 | 0.0001161335 | 5.81 |
| table2:qpeinexact16:positive:wmc_only | wmc_only | 7.732986e-05 | 0.000115043 | 5.75 |
| table2:qpeinexact8:positive:wmc_only | wmc_only | 8.287644e-05 | 0.0001206313 | 6.03 |
| table2:qwalk3:positive:wmc_only | wmc_only | 3.244552e-05 | 4.712161e-05 | 2.36 |
| table2:vqe16:positive:wmc_only | wmc_only | 4.851321e-05 | 0.0001009742 | 5.05 |
| table2:vqe4:positive:hybrid | hybrid | 2.260672e-05 | 0.0001161335 | 5.81 |
| table2:vqe4:positive:wmc_only | wmc_only | 7.105994e-05 | 0.000106624 | 5.33 |
| table2:wstate8:positive:wmc_only | wmc_only | 2.619063e-05 | 5.144879e-05 | 2.57 |

Point distances for the 20 false NEQ: min 2.168614e-05,
median 3.525255e-05, max 8.287644e-05.
Their print-resolution diagnostics: min 4.712161e-05,
median 8.572857e-05,
max 0.0001301563; every diagnostic exceeds the 2e-5 threshold.

This pattern is consistent with a Ganak MODE-6 OUTPUT limitation, not
proof that its internal complex WMC arithmetic is incorrect. The upstream
pinned src/main.cpp:656 formats the complex MPFR solution with %.8Re:
https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L650-L656
Increasing internal --mpfrprec does not recover discarded output digits.
The 56 historical NEQ controls are far from the threshold and do not
prove that a larger tolerance is safe on arbitrary inputs.

Files:
- ganak101-raw.jsonl: all 101 original complete scientific verifier records.
- ganak101-science.csv: 101-row binary/printed-number/GPMC crosscheck.
- ganak20-eq-to-neq.csv: focused 20-row P1 numerical comparison.
- manifest.json: original run IDs and SHA256 checks of shard and archive data.

No solver internals or production defaults changed. Solver arithmetic,
CNF normalization and weight/angle error remain NOT_CERTIFIED.
Performance is not evaluated here and requires CodSpeed.
