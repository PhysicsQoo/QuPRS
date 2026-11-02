# TACAS 2026 — QuPRS-only experimental results

Permanent Git archive; source QuPRS v0.9.1 (e928abc47dd15926364ec77905eb0d5dc92ce8cc).
Science verdict reproduction. Paper reference seconds are historical, not current measured times or CodSpeed-certified performance.

## Summary

- Canonical QuPRS calls: **184**; derived positive Hybrid RR cells: **37**.
- Cases with archived observations: **184 / 184**.
- Historical paper Hybrid reference times available: **46 / 74** (when transcribed).
- Actual QuPRS-native verification times captured in stored 2026-11-02 evidence: **0 / 184**; null means not captured, not zero.
- Historical QuPRS v0.9.1 API exposes verification_time, pathsum_time, to_DIMACS_time, gpmc_time and wmc_time; the former runner omitted them.
- QuPRS's own >200 time strings are censored limits, not an observed 200.0-second measurement.
- Original-source elapsed time and historical paper reference time are science metadata; use CodSpeed for formal performance comparison.
- Classification counts: CENSORED_WATCHDOG_COMPATIBLE = 3, CENSORED_WATCHDOG_UNRESOLVED = 1, MATCH = 142, MISSING_RESULT = 1, NO_PUBLISHED_VERDICT = 35, PAPER_UNQUALIFIED_COMPATIBLE = 2.
- Input run records: 41452992918 = 10, 41453497227 = 68, 41461438155 = 144.
- Matching published Timeout is MATCH. External watchdog means censored; missing JSON means MISSING_RESULT.
- Paper Figure 3 per-case verdicts are incompletely transcribed; no silent claims of equality.
- Original per-case JSON, recorded GPMC stdout, child stdout/stderr and source hashes are in results.json.
- Git tracked data is authoritative for preservation, not the expiring Actions artifacts.

## Table 2 positive MQT

| Case | Method | Paper verdict | Observed | Paper Hybrid (s) | New run (s) | Status | Classification | Run |
|---|---|---|---|---:|---:|---|---|---|
| ghz32 | hybrid | equivalent* | equivalent* | 0.027 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ghz32 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41452992918](https://github.com/PhysicsQoo/QuPRS/actions/runs/41452992918) |
| ghz64 | hybrid | equivalent* | equivalent* | 0.084 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ghz64 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ghz128 | hybrid | equivalent* | equivalent* | 0.306 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ghz128 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate16 | hybrid | equivalent | equivalent | 0.162 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate16 | wmc_only | equivalent | equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate32 | hybrid | equivalent | equivalent | 0.33 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate32 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate64 | hybrid | equivalent* | equivalent* | 1.068 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate64 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover4 | hybrid | equivalent* | equivalent* | 0.213 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover4 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover5 | hybrid | equivalent* | equivalent* | 0.194 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover5 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover6 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover6 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa7 | hybrid | equivalent* | equivalent* | 1.023 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa7 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa9 | hybrid | equivalent* | equivalent* | 0.974 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa9 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa11 | hybrid | equivalent* | equivalent* | 1.636 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa11 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft16 | hybrid | equivalent* | equivalent* | 1.818 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft16 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft20 | hybrid | equivalent* | equivalent* | 20.122 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft20 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft22 | hybrid | equivalent* | equivalent* | 82.866 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft22 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft24 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft24 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn4 | hybrid | equivalent* | equivalent* | 0.738 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn4 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn8 | hybrid | equivalent* | equivalent* | 15.694 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn8 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn12 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn12 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact8 | hybrid | equivalent* | equivalent* | 0.326 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact8 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact16 | hybrid | equivalent* | equivalent* | 0.33 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact16 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact20 | hybrid | equivalent* | equivalent* | 0.581 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact20 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact24 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact24 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact8 | hybrid | equivalent* | equivalent* | 0.333 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact8 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact16 | hybrid | equivalent* | equivalent* | 0.295 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact16 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact20 | hybrid | equivalent* | equivalent* | 0.623 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact20 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact24 | hybrid | equivalent* | equivalent* | 1.075 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact24 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk3 | hybrid | equivalent | equivalent | 0.107 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk3 | wmc_only | equivalent | equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk4 | hybrid | equivalent* | equivalent* | 0.154 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk4 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk5 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk5 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe4 | hybrid | equivalent* | equivalent* | 0.388 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe4 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe8 | hybrid | equivalent* | equivalent* | 0.818 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe8 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe16 | hybrid | equivalent | equivalent | 2.878 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe16 | wmc_only | equivalent | equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate4 | hybrid | equivalent* | equivalent* | 0.147 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate4 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate8 | hybrid | equivalent* | equivalent* | 0.182 | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate8 | wmc_only | equivalent* | equivalent* | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate16 | hybrid | FAILED_TO_VERIFY | Timeout | — | — | RETURNED | PAPER_UNQUALIFIED_COMPATIBLE | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate16 | wmc_only | FAILED_TO_VERIFY | Timeout | — | — | RETURNED | PAPER_UNQUALIFIED_COMPATIBLE | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |

## WState32 positive extra

| Case | Method | Paper verdict | Observed | Paper Hybrid (s) | New run (s) | Status | Classification | Run |
|---|---|---|---|---:|---:|---|---|---|
| wstate32 | hybrid | Timeout | — | — | — | EXTERNAL_TIMEOUT | CENSORED_WATCHDOG_COMPATIBLE | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate32 | wmc_only | NOT_REPORTED_IN_TABLE | — | — | — | MISSING_RESULT | MISSING_RESULT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |

## Table 3 negative MQT

| Case | Method | Paper verdict | Observed | Paper Hybrid (s) | New run (s) | Status | Classification | Run |
|---|---|---|---|---:|---:|---|---|---|
| ghz32 | hybrid | not_equivalent | not_equivalent | 0.04 | — | RETURNED | MATCH | [Actions 41452992918](https://github.com/PhysicsQoo/QuPRS/actions/runs/41452992918) |
| ghz32 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41452992918](https://github.com/PhysicsQoo/QuPRS/actions/runs/41452992918) |
| ghz64 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| ghz64 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ghz128 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| ghz128 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate16 | hybrid | not_equivalent | not_equivalent | 0.16 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| graphstate16 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate32 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| graphstate32 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| graphstate64 | hybrid | not_equivalent | not_equivalent | 1.223 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| graphstate64 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover4 | hybrid | not_equivalent | not_equivalent | 0.478 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| grover4 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover5 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| grover5 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover6 | hybrid | MemoryOut | MemoryOut | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| grover6 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa7 | hybrid | not_equivalent | not_equivalent | 1.61 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qaoa7 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa9 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qaoa9 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qaoa11 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qaoa11 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft16 | hybrid | not_equivalent | not_equivalent | 5.674 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qft16 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft20 | hybrid | not_equivalent | not_equivalent | 30.508 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qft20 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft22 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qft22 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft24 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qft24 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn4 | hybrid | not_equivalent | not_equivalent | 0.838 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qnn4 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn8 | hybrid | not_equivalent | not_equivalent | 13.421 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qnn8 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qnn12 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qnn12 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact8 | hybrid | not_equivalent | not_equivalent | 45.512 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeexact8 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact16 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeexact16 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact20 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeexact20 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeexact24 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeexact24 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact8 | hybrid | not_equivalent | not_equivalent | 0.66 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeinexact8 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact16 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeinexact16 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact20 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeinexact20 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qpeinexact24 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qpeinexact24 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk3 | hybrid | not_equivalent | not_equivalent | 0.707 | — | RETURNED | MATCH | [Actions 41452992918](https://github.com/PhysicsQoo/QuPRS/actions/runs/41452992918) |
| qwalk3 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk4 | hybrid | not_equivalent | not_equivalent | 5.314 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qwalk4 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qwalk5 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| qwalk5 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe4 | hybrid | not_equivalent | not_equivalent | 1.215 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| vqe4 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe8 | hybrid | not_equivalent | not_equivalent | 0.509 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| vqe8 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| vqe16 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| vqe16 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate4 | hybrid | not_equivalent | not_equivalent | 0.127 | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| wstate4 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate8 | hybrid | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| wstate8 | wmc_only | not_equivalent | not_equivalent | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate16 | hybrid | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| wstate16 | wmc_only | Timeout | Timeout | — | — | RETURNED | MATCH | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| wstate32 | hybrid | Timeout | — | — | — | EXTERNAL_TIMEOUT | CENSORED_WATCHDOG_COMPATIBLE | [Actions 41453497227](https://github.com/PhysicsQoo/QuPRS/actions/runs/41453497227) |
| wstate32 | wmc_only | Timeout | — | — | — | EXTERNAL_TIMEOUT | CENSORED_WATCHDOG_COMPATIBLE | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |

## Figure 3 Feynman

| Case | Method | Paper verdict | Observed | Paper Hybrid (s) | New run (s) | Status | Classification | Run |
|---|---|---|---|---:|---:|---|---|---|
| adder_8 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^4_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| tof_3 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41452992918](https://github.com/PhysicsQoo/QuPRS/actions/runs/41452992918) |
| vbe_adder_3 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| barenco_tof_10 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| barenco_tof_3 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| barenco_tof_4 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| barenco_tof_5 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| csla_mux_3 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| csum_mux_9 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^10_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^16_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^32_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^5_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^64_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | — | — | — | EXTERNAL_TIMEOUT | CENSORED_WATCHDOG_UNRESOLVED | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^6_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^7_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^8_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| gf2^9_mult | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| grover_5 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | Timeout | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ham15-high | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | Timeout | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ham15-low | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| ham15-med | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| hwb6 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent* | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| mod5_4 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent* | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| mod_adder_1024 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | MemoryOut | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| mod_mult_55 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| mod_red_21 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent* | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qcla_adder_10 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qcla_com_7 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent* | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qcla_mod_7 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | Timeout | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| qft_4 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| rc_adder_6 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| tof_10 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| tof_4 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |
| tof_5 | reduction_rules | UNTRANSCRIBED_FROM_FIGURE | equivalent | — | — | RETURNED | NO_PUBLISHED_VERDICT | [Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155) |

## Derived RR from the same Hybrid invocation

| Case | Paper RR | Derived RR | PathSum (s) | Run |
|---|---|---|---|---|
| ghz32 | equivalent* | equivalent* | — | 41461438155 |
| ghz64 | equivalent* | equivalent* | — | 41461438155 |
| ghz128 | equivalent* | equivalent* | — | 41461438155 |
| graphstate16 | equivalent | equivalent | — | 41461438155 |
| graphstate32 | equivalent | equivalent | — | 41461438155 |
| graphstate64 | equivalent* | equivalent* | — | 41461438155 |
| grover4 | unknown | unknown | — | 41461438155 |
| grover5 | equivalent* | equivalent* | — | 41461438155 |
| grover6 | Timeout | Timeout | — | 41461438155 |
| qaoa7 | unknown | unknown | — | 41461438155 |
| qaoa9 | unknown | unknown | — | 41461438155 |
| qaoa11 | unknown | unknown | — | 41461438155 |
| qft16 | unknown | unknown | — | 41461438155 |
| qft20 | unknown | unknown | — | 41461438155 |
| qft22 | unknown | unknown | — | 41461438155 |
| qft24 | unknown | unknown | — | 41461438155 |
| qnn4 | unknown | unknown | — | 41461438155 |
| qnn8 | unknown | unknown | — | 41461438155 |
| qnn12 | unknown | unknown | — | 41461438155 |
| qpeexact8 | equivalent* | equivalent* | — | 41461438155 |
| qpeexact16 | equivalent* | equivalent* | — | 41461438155 |
| qpeexact20 | unknown | unknown | — | 41461438155 |
| qpeexact24 | unknown | unknown | — | 41461438155 |
| qpeinexact8 | equivalent* | equivalent* | — | 41461438155 |
| qpeinexact16 | equivalent* | equivalent* | — | 41461438155 |
| qpeinexact20 | unknown | unknown | — | 41461438155 |
| qpeinexact24 | unknown | unknown | — | 41461438155 |
| qwalk3 | equivalent | equivalent | — | 41461438155 |
| qwalk4 | equivalent* | equivalent* | — | 41461438155 |
| qwalk5 | Timeout | Timeout | — | 41461438155 |
| vqe4 | unknown | unknown | — | 41461438155 |
| vqe8 | unknown | unknown | — | 41461438155 |
| vqe16 | unknown | unknown | — | 41461438155 |
| wstate4 | equivalent* | equivalent* | — | 41461438155 |
| wstate8 | unknown | unknown | — | 41461438155 |
| wstate16 | FAILED_TO_VERIFY | unknown | — | 41461438155 |
| wstate32 | NOT_REPORTED_IN_TABLE | UNOBSERVED | — | 41461438155 |

## Data files

- results.csv: full 184-row case table, original-paper reference times and explicitly nullable reproduction timings.
- derived_rr.csv: 37 same-Hybrid RR result cells with optional native PathSum stage times, not 37 separate method calls.
- results.json: full raw evidence (with repeated observations and provenance).
- wmc-evidence.csv: one row per original QuPRS call, with raw GPMC printed real/imag, expected_log2 and original v0.9.1 classifier metadata.
- wmc-evidence.json: original GPMC stdout and float64 outputs for future tolerance replay; no inferred digits or error bounds.
- The aim of this archive is reproducibility in CI and preservation of scientific WMC values, not performance benchmarking.
