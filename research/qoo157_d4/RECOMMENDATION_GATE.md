# QOO-157 — should d4 replace GPMC as QuPRS' recommended solver?

Status (2026-11-04): **NO GLOBAL DEFAULT SWITCH / CONDITIONAL RESEARCH CANDIDATE**.
This is a go/no-go plan, NOT a measured performance conclusion.

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

## Pilot now in progress (not a release benchmark)

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

**Keep GPMC as the general recommended and default Solver.**
Promote d4 first to a documented optional external Solver on supported
Linux/macOS systems ONLY if the above science/latency/licensing checks pass.
Then consider data-driven *per-family recommendations*. A general switch
requires substantially more evidence than the available six small-CNF
parity fixtures.
