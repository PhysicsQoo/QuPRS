# TACAS Artifact Python-only continuity experiment

**Source of truth**: the TACAS artifact Dockerfile pins the immutable, pre-Rust
Python implementation QuPRS v0.9.1 at
e928abc47dd15926364ec77905eb0d5dc92ce8cc.
The currently studied Python implementation is pinned to
dev@059aa076670401b733f6a573201f83611107b924.
The paper's *initial* manuscript checkout has not been independently
established. Do not confuse it with the final submitted artifact source.

## Controlled design

Both source trees run on the **same GitHub-hosted Linux instance**, under
Python 3.12 and Qiskit 1.4.2, one observation per subprocess. Current Python
source is imported with backend=python. The historical code is imported
directly from the checked-out original tree, without backporting newer
source code. The original GPMC executable is obtained via the historical
package and the current executable via the current package. Their SHA256
identities are saved separately: native binary differences are an
**uncontrolled confound**, even with identical machine and QASM.

An independent source-policy check reads the real historical and current
Python AST and verifies the distinct numerical decision formulae. The
historical WMC branch rounds log2(|Z|) to three decimals before comparing
to config.TOLERANCE=1e-10; the current branch uses the unrounded
magnitude/phase classifier with magnitude tolerance 1e-6. A strict
Fraction/Taylor source oracle for a nonzero 0.001-radian RZ demonstrates
the mathematical inequivalence, without claiming a native run.

Real observations use these small bounded pairs (Naive):
identity/identity, H/H, HH/I, I/X, I/RZ(0.001), I/RZ(0.1);
for each, Reduction-only, Hybrid, and WMC-only are recorded.
A representative pinned original artifact benchmark pair
grover-noancilla_4 and its (h,ry,rz,cx) translation is also included for
Reduction-only and Hybrid using the paper's Proportional strategy.
Every original file is read from immutable artifact source by both
versions; their QASM SHA256 digests must match. No QASM corpus is
regenerated or silently mutated.

Each invocation is an independent subprocess with an outer timeout,
a bounded native solver timeout, and a source-local Python import path.
The diagnostic wraps the existing original to_DIMACS and run_wmc calls
only to observe invocation, genuine solver returns and raw CNF bytes.
It does **not** override mathematical answers or replace the solver.
Final status, whether Hybrid called WMC, reduction counts, solver complex
count, normalized log2, source and binary hashes, original CNF and input
provenance are retained separately.

A returned modern or historical "equivalent" for a proven unequal
near-identity RZ is **not** called a scientific PASS. Verdict differences
are classified as actual observations rather than automatically treated
as CI failure. Environment errors, missing observations or timeouts
remain explicitly UNRESOLVED and fail the full comparison; they must
not be recoded as negative equivalence.

## Important exclusions

- Not a complete rerun of the paper tables, and not a comparison of
  paper-era walltimes with CodSpeed or GitHub-hosted walltimes.
- This tests the **final artifact-pinned version**, not a guessed exact
  checkout used at October 2025 manuscript submission.
- A shared CPU/Qiskit version does not by itself guarantee reproducible
  GPMC native results if the two executable hashes differ.
- WMC acceptance tolerance and original Hybrid Reduction -> residual
  WMC selection are unchanged. Existing Rust parser research remains
  independent, as it postdates the paper implementation.
- No scientific red is hidden with xfail/skip or a looser tolerance.
- This is a stand-alone opt-in research workflow; it must not alter
  default CI, performance baseline, packaging or any protected branch.

The evidence is saved as source-policy.json, individual
artifact/dev JSON and actual generated CNF files, comparison.json/csv,
package environment, source HEADs, GPMC hashes, stdout/stderr,
and a checksum manifest. It is intentionally kept in Draft until all
historical runtime observations can be reviewed for validity.
