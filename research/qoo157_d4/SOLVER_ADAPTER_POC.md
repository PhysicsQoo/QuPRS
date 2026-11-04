# QOO-157 — opt-in d4 Python SolverAdapter integration pilot

Branch: experiment/qoo157-d4-adapter-poc, derived from the pinned QOO-157
research branch. These files are **not** part of the installed QuPRS package,
wheel, Rust public API, or default solver registry. This branch does not
distribute d4.

## Scope

- `d4_transport.py` parses only upstream-supported
  `c s exact arb float` (real/complex) and `c s exact arb int`.
  It retains the exact printed decimal as a Fraction and a conservative
  **printed-digit** half-unit. These intervals do not cover GMP internal
  error or source phase-weight error.
- `d4_solver_adapter_poc.py` extends QuPRS' existing Python
  SolverAdapter through a **scoped, explicit opt-in** registration.
  No GPMC/Ganak code is changed or substituted.
- It requires an operator-supplied external executable path and research
  build provenance; the run-time verifies its binary SHA-256. The provenance
  file is **not a cryptographically trusted precision attestation**:
  until upstream has an official build/release contract, only CI-generated
  pinned source/binary evidence is acceptable for a scientific experiment.
- The existing QuPRS `execute_solver` function supplies the timeout,
  process supervision, temporary input lifetime and typed output errors.
  The exact native arguments are `counter -i input.cnf`; there is no
  shell, subprocess duplication, FFI, automatic fallback or default switch.

## Research provenance manifest (operator supplied)

```json
{
  "binary_sha256": "<actual external compiled counter SHA-256>",
  "d4_upstream_commit": "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
  "gmp_preparse_bits": 426,
  "source_patch_approved_for_research": true
}
```

This metadata is a minimum entry gate and is not in itself proof that the
binary did initialize GMP before parsing. Always cross-check source diff,
native build logs and measured complex cancellation fixtures from
CI #41808891018 / CI #41808946607.

## Focused CI

`.github/workflows/qoo157-d4-adapter-poc.yml` first runs a stdlib-only
transport unit suite and then builds the existing QuPRS development package,
running only the new opt-in integration test and the existing incumbent
SolverAdapter contract tests. It asserts no production `src/`, Rust source,
packaging metadata or solver submodule changed relative to
`dev@79e975b0b21c0c650db7a76fe6e35b926c67c2c8`.

## Not yet demonstrated

- Rust d4 adapter integration and Python/Rust equality/near-tolerance
  verdict parity against genuinely executed upstream binary.
- Native executable provenance verification in a production trust model,
  macOS/Windows binaries, license compatibility/redistribution compliance.
- Robust exact arithmetic / rigorous interval bounds; the CLI's
  `exact arb` label is not a finite GMP arithmetic proof.
- Same-SHA, same-host CodSpeed solver-inclusive latency/RSS. No performance
  conclusion can be taken from the scoped correctness CI.

No dev PR, no release support decision.

## P0 admission floor

Pinned d4 A/B recovered all 16/16 nonzero-residual fixtures at 256-bit, but 128-bit still lost the 1e-60 residual. Python/Rust opt-in research admission therefore both require preparse GMP >=256 bits; this is not an arbitrary-circuit error certificate.
