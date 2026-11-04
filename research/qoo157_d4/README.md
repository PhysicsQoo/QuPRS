# QOO-157 — isolated d4 complex-WMC proof of concept

This directory is an experimental **external counter** probe, not a QuPRS
SolverAdapter, dependency, CI release gate, or supported solver. It deliberately
does not change the Python/Rust public API or the GPMC/Ganak defaults.

## Pinned inputs

- Upstream C++ implementation: https://github.com/jm62300/d4
- Review snapshot: be15f91f3e9769e1f5cb175fa27e3eca3a1ea690 (2026-07-21)
- Local QuPRS parent commit: 79e975b0b21c0c650db7a76fe6e35b926c67c2c8
- Main experiment branch: experiment/qoo157-d4-complex-wmc-poc

The upstream README describes an obsolete demo/counter path; the pinned tree
actually builds the executable in c++/counter/build/counter using c++/counter/build.sh.
Its build script also compiles the parent library and resolves upstream dependencies.

The source review found that the C++ counter has an MpzComplexSemiring and
recognizes paired complex CNF weights. The upstream *Rust* shim currently
rejects D4_WEIGHT_COMPLEX; use the C++ demo executable through a controlled
subprocess, **not** the Rust FFI.

## Bounded commands

First test the independent oracle without building anything:

    python3 -m unittest discover -v -s research/qoo157_d4 -p 'test_*.py'
    python3 research/qoo157_d4/poc_d4.py --workdir /tmp/qoo157-oracle-only

Build upstream in a separate research checkout (DO NOT add it to QuPRS
Cargo.toml, wheels or Docker images):

    git clone https://github.com/jm62300/d4.git /tmp/qoo157-d4-upstream
    git -C /tmp/qoo157-d4-upstream checkout --detach be15f91f3e9769e1f5cb175fa27e3eca3a1ea690
    cd /tmp/qoo157-d4-upstream/c++/counter
    ./build.sh -j

Do not consider native runnable until checking the actual build output path
and compiler dependency versions. If the binary is available:

    python3 research/qoo157_d4/poc_d4.py \
      --workdir /tmp/qoo157-d4-evidence \
      --binary /tmp/qoo157-d4-upstream/c++/counter/build/counter \
      --cnf /path/to/a/real/quprs-emitted-small.cnf \
      --timeout 30

The script writes the exact fixture input CNFs, their SHA256, a bounded
independent rational WMC oracle and (only when a binary is supplied) native
stdout/stderr SHA, executable SHA, arguments, raw-decimal parsed result and
pilot discrepancy to report.json. No native execution is inferred from
oracle-only mode. Keep the original stdout/stderr from the host run separately
if investigating a mismatch; hashes alone do not reproduce the error.

The exhaustive oracle is limited to 16 CNF variables; large paper-family
circuits are separate independent end-to-end and CodSpeed work.

## Measured native findings — 2026-11-04

Source and reports: GitHub Actions run 41805111794 (QuPRS experiment commit
30c375014204b2f9a5352384d494c645d89dd778), native artifact
13308294729, pinned d4 C++ executable SHA256
b60215c8e3a4b87d7d2c8336c28a4f8e799adf91419151c55c1aeaca3acc88dc.

- Nine hand-computable source CNFs parsed and reproduced the exact rational
  oracle under the original strict 1e-25 screen.
- QuPRS' actual Rust WmcManager emitted three weighted CNFs
  (identity1, H/T/H miter, Bell/T miter); d4 parsed and counted all three.
  The independent exact-rational oracle of the **serialized f64 weights**
  differs by at most 5.0e-20, 8.8e-20 and 2.8e-19 in a real or imaginary
  component, respectively. These are real nonzero numeric discrepancies,
  **not** grammar failures, and cannot be silently called precise matches.
- The first run failed its 1e-25 pilot threshold on 3/3 QuPRS cases. The
  parser/oracle now reports three distinct outcomes:
  `PILOT_TIGHT` (strict original 1e-25 screen),
  `PILOT_NEAR_UNCERTIFIED` (only a weak 1e-15 finite-precision
  *compatibility* screen), and `PILOT_MISMATCH` (or `NATIVE_ERROR`).
  Passing compatibility **never** means certified high-precision arithmetic
  or QuPRS EQ/NEQ consistency. The global precision gate is always
  `NOT_CERTIFIED` until separate evidence establishes an arithmetic bound.
- The first run archived SHA256 but not the original QuPRS Rust CNF bytes.
  Subsequent branch-only CI explicitly archives the actual emitted CNF files
  in `evidence/quprs-source-cnf/` to make WMC numeric discrepancies
  independently reproducible.

For distance-based equivalence checking, a small **count** error can still be
material near the decision boundary. Do not reuse the exploratory 1e-15
count band as a QuPRS tolerance or numerical proof. The next research
milestone is to establish an actual d4 precision profile under fixed
weights, then compare native counter behavior with GPMC and Ganak.

## Known blockers before any adapter or release decision

1. **C++ computation precision not yet certified:** in reviewed
   c++/counter/src/Counter.cpp, mpf_set_default_prec(426) occurs after
   counter->run(). Printing 50 significant digits is not proof that weights and
   arithmetic ran at 426 bits; the implementation may use an earlier default.
   Check a high-precision cancellation probe and native GMP precision before
   claiming a numerical advantage over GPMC or Ganak.
2. **Output dialect differs:** d4 prints complex results as
   "c s exact arb float <real><+|-><imag>i", but may emit
   "c s exact arb int <count>" for unweighted/UNSAT CNFs, and a real float
   without imaginary suffix for real-only weights. The first native pilot
   matched 7/9 exact oracles and failed only to recognize the two real-integer
   output lines; the strict d4-only parser now accepts all three source-
   grounded dialects and rejects contradictory duplicate count lines.
   Production integration still needs a dedicated decimal-preserving adapter
   and typed errors; a parsed count is not a numerical certificate.
3. **CNF grammar is runtime plausible, numerical proof remains open:**
   Native d4 accepted the three source-generated QuPRS paired-weight CNFs,
   and all nine small direct controls. The three QuPRS inputs show nonzero
   ~1e-19 discrepancies versus the exact oracle of their serialized decimal
   weights. These cannot be silently rounded away. The independent oracle
   intentionally rejects projected CNF in this phase.
4. **License/packaging remains unresolved:** upstream LICENSE carries
   LGPL-2.1 text, while some C++ headers and rust/Cargo.toml declare
   GPL-3.0-or-later. Determine exact distribution/linking obligations prior to
   any bundled or statically linked binary; the PoC stays external.
5. **No timing conclusion yet:** only same-SHA, same-hardware CodSpeed
   solver-inclusive comparisons qualify. Report a lack of benefit as NO-GO.
6. **No false certificate:** a matching finite printed count is a numerical
   observation, not a bound on internal solver rounding. QuPRS retains its
   RR/phase/projective-distance tolerances and Unknown/error distinctions.

## P0 gates

A: native build + direct QuPRS CNF + brute-force correctness.
B: Python/Rust source-pinned realistic cases and precision limitation.
C: CodSpeed paired evidence and explicit benefit (speed, correctness coverage,
   or arithmetic precision), plus licensing audit.
D: **only after GO** implement a separately selectable opt-in adapter;
   GPMC remains default, no silent fallback. All changes must stay on the
   experiment branch until independently reviewed.

## Research addendum: source-precision vs d4 arithmetic (2026-11-04)

Pinned native CI #41805111794 passed 9/9 hand-computable controls, and
compiled the actual QuPRS Rust WmcManager emitted identity1, H-T-H, Bell-T
weighted CNFs. Those three real-CNF experiments disagreed with their exact
*serialized decimal* Fraction oracles by approximately 5.0e-20, 8.7e-20,
and 2.7e-19, respectively. This is a measured numeric discrepancy, not a
CNF/grammar incompatibility. It does **not** prove the source quantum circuits
are equivalent or give any safe EQ/NEQ tolerance by itself.

The experimental Rust emitter now additionally writes the exact same circuits
with QuPRS's existing MPFR 256-bit source-phase weight conversion, without
changing the default solver or WMC code path. The native CI archives all six
CNF bytes, SHA and per-case oracle comparisons. The precision probe runs
complex weights (two decimal components) with analytically known residuals
1e-12..1e-60 and a 10^30+1 vs -10^30 cancellation. It records **exact**
reported-decimal differences and whether a nonzero residual disappeared;
**the probe never passes/fails numerical certification based on 1e-15**. All
native measurements remain tagged NOT_CERTIFIED. A native crash still fails
its CI step. Do not modify upstream d4 source or the QuPRS tolerance contract.
