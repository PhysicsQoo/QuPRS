## PRECISION-FAIR SCIENTIFIC AND PERFORMANCE VERDICT — 2026-11-04

The earlier fixed d4 **426-bit / 50-printed-digit** vs GPMC30/90
comparison was **not equal effective arithmetic precision** and
must not be used as a matched-precision conclusion.
The [completed 30/90 requested-digit experiment](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb18beefdbc51abcbc403f)
has the same nominal requested and output digits, but GMP actually
allocated **128/320 bits** versus MPFR **100/299 bits**.

The principal completed [equal-effective-digit CodSpeed run](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb1b9fefdbc51abcbc4108)
and [source-pinned CI #41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728)
enforced **GPMC 127 bits vs d4 128 bits = 38 effective decimal digits**
and **GPMC 319 bits vs d4 320 bits = 96 effective decimal digits**.
Each solver prints the same number of significant digits and uses the
same QuPRS source-weighted CNF. Eight of eight prepared CNF count
pairs passed the empirical scientific-concordance gate. In official
CodSpeed WallTime 3-round medians the d4/GPMC ratio was:
Grover4 3.63× / 3.63× (38/96 digits);
QAOA7 true NEQ 3.93× / 3.46×;
QPEexact8 2.98× / 2.98×;
QFT16 1.55× / 1.48×.
All eight observed same-run directions favored GPMC.

**Decision** remains GPMC recommended/default, d4 opt-in research only.
These are CodSpeed hosted-runner **OBSERVATIONS** and carry the
WallTime-not-on-Macro-Runner warning. No statistical speedup/regression
certificate or whole-Hybrid benchmark is claimed. Internal arithmetic
error bounds are not certified by same printed digit counts.

Full raw artifacts and source, actual bit, and provenance audit are
recorded in [EFFECTIVE_PRECISION_FAIRNESS.md](EFFECTIVE_PRECISION_FAIRNESS.md).
**Do not reuse the 426-bit data as equal-precision evidence.**

---

# QOO-157 — should d4 replace GPMC as QuPRS' recommended solver?

Status (2026-11-04): **NO-GO for replacing GPMC as recommended first choice or default**.
Completed official CodSpeed solver-inclusive WMC-only pilot on four representative
real QuPRS-emitted weighted CNFs. d4-426 was slower in all four observed
head-to-head same-run cases. Preserve GPMC as the recommended/default solver.

## Completed first-party CodSpeed WallTime pilot

Source code measured: `8b48aa6bbe83eb25a6bba0760ce7d2ab93034b1b`.
[GitHub Actions #41816616183](https://github.com/PhysicsQoo/QuPRS/actions/runs/41816616183)
SUCCESS. [CodSpeed run 6aeb0f25e2759d7342f6ae61](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb0f25e2759d7342f6ae61)
COMPLETED. Artifact ID `13315227468` contains original source QASM SHA,
identical generated CNF bytes and SHA, native patched d4 binary/source SHA,
science preflight, official first-party CodSpeed WallTime export, toolchain
and runner metadata.

| Genuine source-CNF case | GPMC30 median | GPMC90 median | d4-426 median | d4 / GPMC30 |
| --- | ---: | ---: | ---: | ---: |
| Grover4 EQ | 61.413 ms | 61.422 ms | 229.226 ms | 3.73x |
| QAOA7 genuine Random_Rotation NEQ | 41.299 ms | 41.419 ms | 148.717 ms | 3.60x |
| QPEexact8 EQ | 61.503 ms | 61.518 ms | 190.486 ms | 3.10x |
| QFT16 EQ | 1129.565 ms | 1270.067 ms | 1922.255 ms | 1.70x |

- Same source CNF across all three solver modes; Rust WMC-only emitted the
  paired complex weights. Four of four preflight science records were
  `NUMERICALLY_CONCORDANT_UNCERTIFIED` against GPMC90 at 1e-12 scale-relative
  screening; this is not an independent proof of original circuit equivalence.
- Each CodSpeed v5 WallTime benchmark has three rounds. The measured operation
  is Python QuPRS `run_wmc` on prepared CNF, including supervisor/binary
  preflight/subprocess and count parsing. It **excludes** QASM parsing,
  PathSum construction, CNF generation, RR/Hybrid, and complete verification.
- Official CodSpeed explicitly warns `Walltime results may be unreliable`
  because the samples ran outside a dedicated Macro Runner. This is
  **OBSERVATION_ONLY / NOT PERFORMANCE_CERTIFIED**: no fixed absolute or
  relative speedup/regression threshold can be justified from this hosted run.
  It nevertheless gives no evidence for d4 superiority in the four tested
  families; all observed directions favor GPMC.
- A 426-bit GMP working default versus GPMC 30/90 decimal working digits
  does not equalize arithmetic contracts, nor establish d4 accuracy bounds.
  Do not conflate WMC count screening with source/projective distance proof.

**Decision:** keep GPMC first/default, preserve d4 opt-in research.
Further work should target a reasoned d-DNNF compile-and-reweight workload,
or independently justified new CNF classes, with CodSpeed on a controlled
same-host/ABBA cohort. Re-running essentially the same hosted benchmark
will not resolve statistical reliability or the observed lack of advantage.


## What has been independently demonstrated

- The upstream d4 C++ counter at `jm62300/d4@be15f91...` accepts the
  QuPRS weighted-CNF pair grammar and returns complex numbers through
  a supervised subprocess; the upstream Rust FFI path is *not* complex-ready.
- Original d4's late `mpf_set_default_prec(426)` caused small nonzero
  residuals (1e-32/1e-40/1e-60) to vanish. A temporary **preparse** fix
  has native A/B success on 16 controls and six real QuPRS source CNFs.
- Python `run_wmc()` with a scoped external d4 adapter: 6/6 genuine
  QuPRS source CNFs at research 1e-25 screening tolerance.
- Rust `WmcOnly` actual native d4: three solver-invoked EQ/NEQ verdicts,
  plus exact same six CNF decimal-rational printed counts as Python.
- GPMC and d4 agreed on **two** source-exact 1-qubit P-gate distances
  straddling 1e-8, but d4's printed verdict remained `unknown` for one
  EQ case despite numerical point-estimate EQ.
- These results do NOT certify d4 internal GMP arithmetic error bounds or
  establish comparative speed, memory safety, startup cost, concurrency,
  packaging legality, or consistent scientific verdicts over TACAS cases.

## Four distinct decisions

1. **External research solver (already viable)**: opt-in with explicit
   binary SHA, source pin and research-only GMP-before-parser patch.
2. **Recommended on selected circuit families**: only after controlled,
   solver-inclusive CodSpeed comparisons against GPMC 30 and 90 digits
   at identical source weights, CNF SHA, methods and output verification.
3. **Recommended as general first choice**: requires representative
   workload-coverage gains including Grover, QAOA, QFT, QPE and VQE and
   no correctness/resource regressions, not just one easy CNF.
4. **Change the default from GPMC to d4**: requires maintained upstream
   precision fix, a trustworthy precision metadata contract, Python/Rust
   public API parity, release-scope macOS/Windows and packaging/licensing
   viability. This is a distinct, strictly higher bar.

## Source-pinned pilot design (now completed; historical design notes)

Isolated workflow `.github/workflows/qoo157-d4-codspeed-choice.yml`:
- QASM pairs in grover4 EQ, qaoa7 true NEQ, qpeexact8 EQ, qft16 EQ.
- Rust WMC-only path without RR generates the SAME complex paired-weight
  CNF for GPMC30, GPMC90 and d4-426. Source SHA and CNF SHA archived.
- Correctness/timeout admission happens BEFORE CodSpeed. A case becomes
  eligible only if all three runs finish and their decimal-rational counts
  agree to 1e-12 on max(1,component) absolute scale. This is merely an
  empirical count concordance screen, not a source or solver certificate.
- Each eligible case is officially measured with CodSpeed v5 WallTime
  using the existing QuPRS Python `run_wmc` supervisor; includes subprocess,
  I/O, binary SHA preflight and parsing. It excludes QASM parsing and CNF
  generation. Preflight execution times MUST NOT enter performance ranking.
- Timed-out, memory-failed, unsupported-QASM or divergent cases are
  explicitly *censored* and reported. They are never given invented zero or
  timeout-as-duration values.
- Hosted-runner non-ABBA first pass is **OBSERVATION_ONLY**. For any candidate
  advantage, follow with the existing source-pinned ABBA/BAAB CodSpeed
  comparison pattern on a qualified Macro Runner or controlled same host,
  including full Rust WMC-only and Hybrid end-to-end workloads.
- No new simulation identity replaces the original 32; this is an isolated
  pilot and adds no recurring regular 5-shard costs.

## Known release blockers and must-not-infer constraints

- Upstream root LICENSE text is LGPL-2.1, but actual counter C++ source
  headers declare GPL-3.0-or-later; do not bundle or link privately built
  d4 into QuPRS wheels without rights and obligation analysis.
- The d4 `complexToString` formatter uses 50 significant decimal digits
  on non-Windows, but on `_WIN32` uses `get_d()` (double), losing much
  of the GMP precision. Default cross-platform parity is **NOT_MET**.
- Fifty printed digits do not establish 50-digit *internal accuracy*.
  Reported precision and a conservative metadata contract need an
  upstream-maintained source path; near-threshold printed unknown cannot be
  silently upgraded to certified EQ.
- d4 compiler/DNNF reuse advantages, if any, must be measured separately:
  first cold solve includes decomposition/compilation; cached reweighting
  is NOT a valid substitute for first-solve time.
- QuPRS hybrid RR-first can avoid WMC completely: speed of the external
  Solver need not improve end-to-end use cases that finish in RR.
- GPMC and Ganak remain independent supported solvers; no implicit fallback,
  no default switch, no tolerance changes.

## Provisional recommendation

**Keep GPMC as the general recommended and default Solver.** No-GO for a global d4 recommendation based on the completed four-case CodSpeed pilot.
Promote d4 first to a documented optional external Solver on supported
Linux/macOS systems ONLY if the above science/latency/licensing checks pass.
Then consider data-driven *per-family recommendations*. A general switch
requires substantially more evidence than the available six small-CNF
parity fixtures.
