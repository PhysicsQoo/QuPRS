# TACAS26 — RR tolerance versus Ganak 2e-5: source-pinned scientific findings

Research-only. Authoritative full source: `experiment/tacas26-paper-reproduction`.
No changes to PR #131, `dev`, release defaults, or solver source.

## Actual controlled CI

- [GitHub Actions #41539989361](https://github.com/PhysicsQoo/QuPRS/actions/runs/41539989361) @ `c9c53bd4aba002c93e1dcc32f0471582008b6849`: 11/11 research Solver shards and 1/1 preflight SUCCESS. **47/47 processes returned a verdict, no timeout.** This is science only; no CodSpeed data or performance conclusion.
- Strict RR/GPMC distance experiment: 21 probes; 13 expected matches and 8 expected mismatches, including default/low-RR controls and two WMC-only pairs that provably ignore RR.
- Ganak 2.8.0 default mode 6 at `approximate_distance_tolerance=2e-5`: 26 Python/Rust probes; **20 matches, 6 false NEQ**. Actual `solver_invoked=true` for 24/26; the other two are RR-only terminations, not evidence of a Ganak calculation. 0 censored.
- The separate [full Python/Ganak 101-case source-pinned run #41540814150](https://github.com/PhysicsQoo/QuPRS/actions/runs/41540814150) was separately triggered at `1a38d7de190cacba4e2713f2bd7e586724a5fb6d`. It targets precisely 45 historic EQ / 56 historic NEQ, 44 hybrid / 57 WMC-only, with per-case scientific solver 200s and external watchdog 215s, and has its own artifacts. Its status must be re-checked: this initial report does not claim an end-to-end 101/101 result.

## 1. RR cannot substitute for projective distance when reproducing all paper methods

- Modern QuPRS **Hybrid** may conclude at tolerance-reduced RR residual, avoiding WMC. On QPE-inexact20 and QPE-inexact24 (paper EQ), `distance=1e-8` and `rr=1e-10` or `1e-6` return **NEQ**, with GPMC called.
- `rr=1e-5`, `2e-5`, or `1e-4` instead return **EQ*** in both tested QPE cases (Rust), with `rr_approximate=true` and **no GPMC call**. QPE-inexact20 Python at RR=2e-5 agrees.
- Two real paper negatives QAOA11 and QWalk4 Hybrid remain NEQ at `rr=1e-10`, `2e-5`, and `1e-4`; this is a bounded control, not a universal proof against false positives.
- **WMC-only does not run RR at all**. QFT20 and QFT22 paper-positive WMC-only remain NEQ at `distance=1e-8` for both `rr=1e-10` and `rr=1e-4`, with GPMC actually invoked. Historical 101 printed GPMC counts at distance 1e-8 had 22 binary mismatches: **11 WMC-only and 11 Hybrid**. Since WMC-only RR tolerance is irrelevant, no RR-only change can yield full 101/101 with distance 1e-8.
- Never describe `distance=1e-8, rr=1e-5` as an overall 1e-8 precision policy: RR may approximate-away differences much larger than projective threshold.

## 2. Ganak mode 6 at distance=2e-5 currently fails actual paper EQ/NEQ

- Both Python and Rust, both with actual Ganak invocation, returned NEQ for these original paper **EQ** WMC-only positives:
  - `table2:qft16:positive:wmc_only`;
  - `table2:qft22:positive:wmc_only`;
  - `table2:qaoa11:positive:wmc_only`.
- Other positives (QPE-inexact20/24 Hybrid, QFT20 WMC-only and QAOA7 Hybrid) matched, but frequently had `ganak_point_estimate_resolution_limited`; real negative controls all matched in this pilot.
- Ganak mode 6 printed-distance resolution estimates are of order `4.66e-5` to `1.30e-4`, larger than `2e-5`. For QFT22, point-estimated `log2|WMC|` is `69.99999999912332` (expect 70), corresponding to inferred `D_proj≈3.49e-5` versus old GPMC printed count `69.9999999999047` (inferred `D_proj≈1.15e-5`). These are **point estimates**, not independently certified operator distances.
- **Source-level formatting root cause:** at exact pinned Ganak upstream SHA `b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281`, `src/main.cpp` line 656 prints mode-6 complex MPFR output using `mpfr_printf("c s exact %s %.8Re + %.8Rei\\n", ...)`, about 9 significant digits even if internal arithmetic is more precise. The `--mpfrprec` CLI flag changes internal MPFR precision (128-bit default, 256-bit maximum), **not this fixed printed result format**.
  - [Exact pinned Ganak source](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L650-L656)
- Existing Ganak `--mode=2` computes with complex rational arithmetic and prints a fraction count. It is an **untested alternative** that could avoid mode-6 output granularity without modifying solver source, but input complex weights must be faithfully interpreted as rationals, and computational feasibility plus original transcendental source-angle error need separate qualification. No production integration or result is claimed.

## Decision

- For TACAS paper reproducibility, prefer independently tested **GPMC / projective distance=2e-5, rr=1e-10, phase=1e-8, MPFR30** (source-pinned modern Python and Rust 101/101; also Python MPFR90 101/101).
- Do **not** make `rr_tolerance=1e-5` a surrogate for distance=2e-5, or claim default Ganak mode6 satisfies 2e-5.
- Retain QuPRS production default distance=1e-8 and formal PR #131 Draft/unmerged. Precision arithmetic **NOT_CERTIFIED** for both independent Solver implementations without rigorous total-error and source/CNF bounds.
- Do not alter Ganak/GPMC upstream source just to reproduce rounded paper outcomes; keep exact source+solver provenance, raw numerical warnings, timeout states, and future CodSpeed comparisons separate.
