# QOO-157 — isolated d4 complex-WMC proof of concept

This directory is an experimental **external counter** probe, not a QuPRS
SolverAdapter, dependency, CI release gate, or supported solver. It deliberately
does not change the Python/Rust public API or the GPMC/Ganak defaults.

## Pinned inputs

- Upstream C++ implementation: https://github.com/jm62300/d4
- Review snapshot: be15f91f3e9769e1f5cb175fa27e3eca3a1ea690 (2026-07-21)
- Local QuPRS parent commit: 79e975b0b21c0c650db7a76fe6e35b926c67c2c8
- Main experiment branch: experiment/qoo157-d4-complex-wmc-poc

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
      --binary /tmp/qoo157-d4-upstream/demo/counter/build/counter \
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

## Known blockers before any adapter or release decision

1. **C++ computation precision not yet certified:** in reviewed
   c++/counter/src/Counter.cpp, mpf_set_default_prec(426) occurs after
   counter->run(). Printing 50 significant digits is not proof that weights and
   arithmetic ran at 426 bits; the implementation may use an earlier default.
   Check a high-precision cancellation probe and native GMP precision before
   claiming a numerical advantage over GPMC or Ganak.
2. **Output dialect differs:** C++ currently prints
   "c s exact arb float <real><+|-><imag>i", which is NOT the same as Ganak's
   "arb cpx" or the existing QuPRS parser's other float prefixes. The PoC
   uses a strict d4-only parser; production integration requires a dedicated
   adapter with decimal-string preservation and typed failures.
3. **CNF grammar is only source-level plausible:** validate real
   QuPRS-generated paired weights, negative-literal normalization, SAT/UNSAT,
   all-free-variable and cancellation cases on a compiled native binary. The
   independent oracle intentionally rejects projected CNF in this phase.
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
