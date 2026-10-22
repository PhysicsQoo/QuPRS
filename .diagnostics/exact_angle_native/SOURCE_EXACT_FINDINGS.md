# Source-exact versus Qiskit-rounded scientific verdicts

This is a research diagnostic for QASM *literal-source* semantics. It is not a
new production solver, not an automatically accepted benchmark baseline, and
not an approximate-equality tolerance.

## Exact source unitary witness

The original decimal rotation literal, e.g. `2.0330832984526417`, denotes
an exact rational number of radians. The QASM expression `pi/2` denotes an
exact rational multiple of the mathematical constant pi. Neither source
expression is converted to Python binary64 before evaluation.

For the two source unitaries U and V, define for a fixed input basis index x:

\[
D_{a,b;x}=U_{a,x}V_{b,x}-U_{b,x}V_{a,x}.
\]

If U and V differ only by a global phase, every such minor is identically
zero. Conversely, even one rigorously **nonzero** minor proves the matrices
are inequivalent *including modulo global phase*, without choosing a
numerical-equivalence tolerance.

Each complex-ball operation in the pinned FLINT Arb implementation encloses
the exact mathematical result. The scripts return a non-equivalence witness
only when a computed minor excludes zero; otherwise the result is explicitly
INCONCLUSIVE. No strict equivalence result is generated.

## Source-pinned witnesses

| Source pair | SHA256 (left/right) | Input x | Outputs (a,b) | Nonzero minor (real, imaginary) |
|---|---|---:|---:|---|
| QPEexact8 | 8d514d06f7c9e81abda1042796cc34227624c9ed66097bee1ce5e97a87884dda / 227ab45a4eb033889aa57bb53e54938e74d757fea30eaa3d276b495048dc6141 | 0 | 137, 153 | (1.86517348e-34 ± 5.06e-82, 1.25739783e-33 ± 5.69e-82) |
| Graphstate16 | cf068868f970e553ac9a8fb4998c7c2a6a2e3e6e7a437e3a636f477e34682e36 / d2c38d1663dc26757ecb09748918be41c0064cc67bc52d4d7c1c2dfc3fbdd1c9 | 0 | 0, 8 | (-9.47497919e-36 ± 8.48e-62, 2.11277227e-21 ± 7.13e-62) |

The enclosures exclude the origin (the imaginary parts alone suffice).
Both scripts use 256-bit complex-ball arithmetic and support exactly the
RX/RY/RZ/CX/X gates occurring in these pinned QASM fixtures. Unknown syntax
must cause an error, never be silently dropped. The full original source,
source hashes, scripts, Python and FLINT environment, result JSON and artifact
SHA256 manifests are archived by the separate jobs.

- QPEexact8: https://github.com/PhysicsQoo/QuPRS/actions/runs/39714182011
- Graphstate16: https://github.com/PhysicsQoo/QuPRS/actions/runs/39714444491

## Meaning for strict versus approximate acceptance

The prior Qiskit matrix oracle reported a residual of about 1.87e-15 for
QPEexact8. That numerical observation is compatible with a rigorously
nonzero exact-source difference and **cannot certify exact equality**.

Consequently:

1. The original 12 native positive regressions contain eight valid exact
   decimal-angle cancellation positives, but four QPEexact8 items should
   no longer be labeled "strict source-exact positives" without contrary
   rigorous evidence. A Rust Unknown result is incomplete, **not** a proven
   false negative for source-exact semantics.
2. Existing Graphstate16 benchmark expectations requiring Equivalent
   conflict with the pinned exact-source witness. Changing expectations
   globally without an explicit semantics contract is **not** justified.
3. A future user-selected approximate-equivalence mode must state a metric
   (e.g. norm bound or distance modulo global phase) with a validated
   numerical bound. It must not silently reuse the strict Equivalent status.
4. The Rust symbolic-angle backend still needs full exact a*pi+b rational
   arithmetic, including the pi-rational FreeRational component; the current
   decimal-only BigRational patch is insufficient.

Before modifying the original benchmark classifications, independently
review gate application order, QASM register endianness, sign conventions,
and interval arithmetic semantics, including comparison with a second
implementation on representative reduced circuits. Keep both PRs Draft
until independent acceptance is documented.
