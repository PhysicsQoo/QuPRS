# Small Weighted-CNF Interval Reference

This is an **independent, deliberately bounded research reference**, not a
replacement WMC solver, production verifier, or automatic certificate for
QuPRS's Path-sum-to-CNF encoder.

## What it proves

For at most 12 Boolean variables, it enumerates every assignment satisfying
an explicit CNF and encloses each signed complex literal weight using exact
rational endpoint arithmetic. Addition, subtraction, multiplication and
absolute-value-squared are implemented as outward rational intervals, avoiding
floating-point narrowing. A normalized complex magnitude is enclosed using
integer square roots with outward decimal-rational bounds.

For an **exact rational radian** angle θ in [-1,1], the weights
`exp(+iθ)` and `exp(-iθ)` use consecutive alternating Taylor partial
sums for sine and cosine. Decreasing term magnitudes and the alternating-series
remainder theorem prove that the exact values lie within those intervals.
The input is `Fraction`, **not** a Python float. Unsupported angles or floats
are rejected instead of silently approximated.

The one-variable, no-clause trace reference assigns
`w(+)=exp(+iδ/2)`, `w(-)=exp(-iδ/2)`. Its count is
`2 cos(δ/2)`, so its normalized magnitude matches the analytic
`I` versus `RZ(δ)` trace. In particular `δ=1/1000` radians yields a
rigorously bounded magnitude **strictly less than 1**. Exact identity, pure
phase, zero, signed/complex cancellation and a two-variable XOR CNF provide
independent controls.

## What it does not prove

A manually constructed CNF is **not** the same as the CNF emitted by the QuPRS
encoder. This implementation does **not** read a QuPRS-generated DIMACS file,
parse its full complex-weight dialect, or establish its encoding equivalence to
an input QASM. It does **not** bound actual GPMC/Ganak internal arithmetic,
solver output formatting or numeric normalization. The angle in an ordinary
binary floating-point QASM pipeline is not automatically an exact rational
radian. Thus a reference bound **must not** be retroactively attached to a
native Solver result as a certificate. It also does not solve near-one
certification for general circuits.

No QuPRS source, acceptance thresholds, reducer, solver selection or default
CI testing is changed. The existing near-identity scientific RED remains a
separate unresolved observation.

## Reproduce

With Python 3.11+ and no external dependencies:

```sh
python -m unittest discover -s .diagnostics/wmc_interval_reference -p 'test_*.py' -v
python .diagnostics/wmc_interval_reference/run_reference.py \
  --output interval-wmc-reference-results
(cd interval-wmc-reference-results && sha256sum -c reference-results.sha256)
```

The standalone opt-in workflow saves source provenance, test output, JSON,
SHA256 checksums and JUnit. The entire reference test should be **GREEN**;
it must never turn the separate actual native WMC strict-equivalence RED green
by `xfail`/`skip`, reducing the tolerance or relabeling a false positive.


## Importing actual emitted DIMACS (bounded Python bridge)

The optional bridge reads **actual** Python QuPRS `to_DIMACS` output from
Qiskit-derived one-qubit Path-sums. The narrow importer recognizes each
supported GPMC/Ganak complex-weight text dialect, the weighted marker,
header, per-literal weights, implicit unit weights, clauses and unsatisfiable
constraints. It fails closed on duplicate weights, unsupported tokens,
nonfinite numbers or more than 12 variables.

A decimal literal is interpreted as the **exact rational value of the
bytes printed into the CNF**. This makes the independent exhaustive count
of that printed CNF a rigorous rational reference. It does **not** prove
that the printed decimal encloses the intended transcendental coefficient
or that a native solver's float output has a certified error bound.

The normalization matches QuPRS's WMC code path for an \(n\)-qubit
Path-sum with \(p\) path variables: \(\vert Z\vert/2^{n+p/2}\).
Integer-square-root bounds handle odd `p` without an intermediate float.

The opt-in native bridge runs identity, HH, X, near-RZ and far-RZ Qiskit
cases for **each solver independently**. It saves the actual generated
CNF bytes and QASM source digests, exact printed-weight reference interval,
raw solver stdout/exit, actual binary SHA256 and source/tree SHAs.
Any claimed numerical agreement with the selected native solver or Qiskit
dense `Operator` is explicitly labelled an **observational float
comparison**, not a certificate. The near-RZ reference bound below 1
applies only to the printed-weight CNF, not automatically to the physical
source or the native solver.

Run after installing QuPRS with both GPMC/Ganak and Qiskit:
```sh
python -m pytest -q .diagnostics/wmc_interval_reference/test_import_dimacs.py
python -u .diagnostics/wmc_interval_reference/run_encoded_bridge.py \
  --output wmc-encoded-bridge-results
```

The extended opt-in Actions workflow runs this native comparison separately
from the original dependency-free reference. Neither modifies the existing
strict WMC scientific RED nor a maintained release/correctness baseline.


## Rust-generated CNF and represented-coefficient intervals

The additional opt-in Rust job runs a standalone crate example
`rust/pathsum/examples/interval_cnf_reference.rs`. It creates an ordinary
Rust WMC-only miter using the public strategy and WmcManager API, calls the
actual `encode_trace` and `to_dimacs_string` for both GPMC and Ganak,
and saves emitted CNF bytes and source QASM alongside variable-specific
Rust PhasePolynomial coefficient provenance. This is neither a mock
encoder nor a production change.

A separate rational reference certifies
`exp(2*pi*i*a/b)` for the **represented** Rust phase fraction `a/b`:
Machin's pi identity uses rational alternating arctangent bounds,
Taylor polynomials have explicit Lagrange remainders, and derivatives
bound the uncertainty from pi. Each emitted `f64` decimal is considered
an exact printed rational point. A componentwise hull of this point
and the ideal represented-coefficient reference conservatively encloses
both, and the resulting finite CNF is counted by the independently
bounded enumerator. This provides a rigorous *represented-coefficient
versus emitted-weight* discrepancy envelope, conditioned on the phase
mapping, not a full verification proof.

Crucial exclusions:

- The Rust QASM angle parser uses approximation/continued fractions
  before reaching PhasePolynomial. The original source-radian value
  is not certified equal to the represented fraction.
- There is no certified interval encompassing the GPMC/Ganak internal
  floating-point weighted count. Their stdout is captured and compared
  observationally only.
- Rust and Python generate different CNF encodings. Equal DIMACS bytes
  or literal variable identities are **not** required for semantic parity.
- If the reference produces `upper < 1`, it certifies inequivalence
  only within its stated represented-coefficient model; it must not be
  advertised as certification of the original QASM circuit.
- The maintained near-identity native verdict remains a real scientific
  RED until a separately reviewed strict-positive policy exists.

The research branch workflow stores the exact Rust CNFs, source QASM,
phase coefficient metadata, independent interval results, raw native
solver outputs, SHA256 evidence and test output under
`rust-wmc-phase-results`. It is not a default required CI or release gate.

```sh
python -m pytest -q .diagnostics/wmc_interval_reference/test_phase_coeff_reference.py
python .diagnostics/wmc_interval_reference/run_rust_bridge.py \
  --output rust-wmc-phase-results
```


## Exact source-decimal RZ to represented Rust coefficient audit

A third independent check binds the *literal QASM decimal radians* to the
recorded Rust phase coefficients for exactly one positive `RZ(δ)` acting
as the Bra-side circuit against the one-qubit identity. It recognizes only
a small, strictly checked OpenQASM 2.0 source pattern; other expressions,
multiple gates, and unsupported mappings fail closed.

The QASM decimal literal (e.g. `rz(0.001)`) is read as an exact
`Fraction(1,1000)` radians. It is **not** obtained by converting Qiskit's
`float` or trusting Rust's floating-point parser. The one-gate RZ Bra
formula in `rust/pathsum/src/gates.rs` gives the exact source-phase
complex weights:

- Constant phase monomial: `exp(+i δ/2)`, coefficient `δ/(4π)`.
- Input-bit monomial `x[0]`: `exp(-i δ)`, coefficient
  `1−δ/(2π)` (modulo 1).

An independent rational-π interval bounds the exact source coefficients;
the strict rational-radian Taylor reference bounds the corresponding
complex phases. For each actual Rust-emitted phase literal, the audit
records both the internal `Angle`/`PhaseCoeff` rational and its
**rigorously upper-bounded distance** from the ideal source coefficient.
It then recomputes the actual small CNF using (a) source-complex weights
and (b) a conservative per-component hull containing the source,
represented Rust phase, and printed decimal weight.

For the nonzero 0.001-radian case, both the source-radian reference and
this three-way hull are required to have normalized upper magnitude < 1;
these are conditional small-model mathematical conclusions, not arbitrary
floating-point tolerance checks.

Important limitation: matching the two expected monomials and clauses
gives a constrained source-to-CNF validation for this one known gate
mapping. It is **not** a generic QASM parser correctness proof,
a numerical certificate for GPMC or Ganak internals, nor a replacement
for the separate native `wmc_only` strict-positive RED. Tiny angles
can be lost earlier in Rust's approximate `Angle::from_qasm_str`;
a separate fail-closed boundary study is needed for those.

The source-radian test is opt-in and runs within the dedicated Rust
diagnostic job:

```sh
python -m pytest -q \
  .diagnostics/wmc_interval_reference/test_qasm_rz_source_reference.py
```


## New near-identity counterexample under 1e-8 numerical acceptance

The research-only source-to-actual-Python-CNF runner now includes the
one-qubit `rz(0.0002)` case. Its exact source decimal is `1/5000`
radians. The independent source trace has magnitude
`cos(1/10000)`, with ideal unit defect about `5e-9`, which
lies within QuPRS's 1e-8 numerical WMC acceptance band.

For **each** selected GPMC/Ganak CNF, the runner requires the source
phase formula, the actual emitted weighted-CNF literal activation
and unique Boolean extension, and an outward-rational interval
enclosing the source and printed complex weights whose normalized
magnitude upper bound is **strictly less than one**. If the
enclosure touches one or the encoding is unsupported, it must
**not** claim non-equivalence. Actual solver stdout and binary
SHA256 are saved as distinct *observations*, not part of the proof.

This is a restricted source-model/CNF encoding audit only, not a
generic QASM compiler proof or a floating-point error bound on native
GPMC/Ganak. It does not automatically alter `check_equivalence`
results, the paper's reduction-first Hybrid or the configurable
numerical policy. The independent native WMC strict-positive
scientific RED is kept in Draft PR #90.

The standalone opt-in [small-RZ source-CNF workflow]
(../../.github/workflows/wmc-rz-small-source-certificate.yml)
runs the independent rational test and the actual Python source-CNF
generator against both native solvers; the existing broader certificate
workflow remains unchanged.

## Python source-decimal diagonal-family certificate (bounded)

The new separate research job compares **exact literal source QASM**
against the **real Python Path-sum's CNF** for a tightly constrained
one-qubit diagonal gate family. The source grammar accepts 1 to 4
sequential gates drawn from: decimal-radian `rz(δ)`, `u1(δ)` (QASM2 alias for Qiskit P), plus
`z`, `s`, `sdg`, `t`, `tdg`. It rejects arbitrary QASM, other
gates, source expressions, multi-registers and angles with absolute
magnitude above 0.5 radian. This is *not* a general OpenQASM verifier.

The source phase is independently derived from diagonal gate matrices:
an RZ(δ) contributes a constant phase exp(-iδ/2) and an input-bit phase
exp(+iδ); QASM2 U1(δ) (same unitary as P(δ)) contributes exp(+iδ)
to the bit phase; Z/S/T and their
inverses contribute exact rational multiples of pi to that bit phase.
Original literal decimal radians are kept as exact Fractions. Each
complex phase gets a conservatively enclosed rational Taylor + Machin
pi reference, rounded *outward* to 50 decimal places.

The actual Python gate mapping and `to_DIMACS` are called without
overriding them. The source phase monomials must be exactly constant
and/or input-bit terms; the corresponding positive weighted literals
are found using the existing `P_to_wlogi` ordering. The independently
parsed CNF then undergoes exhaustive **Boolean truth-table auditing**:
for each input bit value there must be exactly one satisfying extension,
and every weighted literal must be true precisely when the source
monomial activates. An unexpected gate, polynomial term, output map,
path variable, auxiliary multiplicity, weighted literal, or CNF larger
than twelve variables fails closed.

The reference enumerates this **actual finite weighted CNF** twice:
with mathematically derived source weights, and with a conservative
componentwise hull of those source weights and the exact emitted
decimal weights. Only when the latter's rigorously enclosed
normalized trace magnitude has upper bound **strictly below one** is
a *limited source/printed-CNF non-equivalence certificate* produced.
If one is exactly equivalent, a tiny angle is lost, or the result
cannot be enclosed, the tool reports **INCONCLUSIVE**. It never infers
equivalence just from a near-one numerical result.

This is a scoped source/weighted-CNF certificate conditioned on the
**fixed and audited Python diagonal-gate semantics and compiler path**.
It is not a formal proof for general gate mapping, general CNF encoders
or native floating solver arithmetic. Real GPMC/Ganak outputs, binary
digests and stdout are captured as *observations only*; they are not
silently promoted to mathematical bounds. The work does not change
the production API, ordinary Hybrid/Reduction execution, existing
Draft scientific REDs, or the default WMC acceptance tolerance.

Evidence and tests live in:

- `python_diagonal_source_certificate.py` — standalone formal restricted model;
- `test_python_diagonal_source_certificate.py` — negative/fail-closed controls;
- `run_python_source_certificate.py` — exact source, actual Python CNFs,
  true GPMC/Ganak crosschecks, case-by-case JSON;
- `python-source-certificate-results/` — QASM, raw CNFs, tests, solver
  outputs, source hashes and verified SHA256 manifest, uploaded by
  the opt-in workflow.

```sh
python -m pytest -q \
  .diagnostics/wmc_interval_reference/test_python_diagonal_source_certificate.py
python .diagnostics/wmc_interval_reference/run_python_source_certificate.py \
  --output python-source-certificate-results
```


## SolverAdapter integration evidence

The opt-in generated-DIMACS bridge now includes the Python solver-adapter
contract tests along with its independent emitted-weight parser controls.
The bridge and source-QASM jobs record the actual `solver_adapter.py` source
hash in their evidence. Both Ganak and GPMC remain explicitly selected and
are run separately with their own weight grammars and native arguments.
The capture hook observes the real `solver_process.run` called by `run_wmc`;
it does not fabricate a solver result or promote numerical agreement to a
proof. A failing source/solver run must fail the workflow (including all
piped Rust checks), rather than merely producing uploaded diagnostic output.
