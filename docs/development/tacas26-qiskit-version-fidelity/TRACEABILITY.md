# TACAS26 transcompiler-to-verifier evidence traceability contract

Scope: **`experiment/tacas26-paper-reproduction` only**. This research
archive is distinct from formal PR #131, the published original-QASM
v0.9.1 reproduction, and CodSpeed performance studies.

## Reproduction unit and immutable identity

The scientific unit is **one exact QASM pair + one QuPRS executable
version/commit + one method/backend/Solver + one complete tolerance
configuration**. Identical circuit names alone are NOT sufficient.
Distinguish:

1. Original MQTBench input QASM (paper corpus commit and full SHA256).
2. Paper's historical frozen transpiled QASM (full SHA256; exact original
   optimization seed/level not inferred).
3. New Qiskit 1.4.2 or 2.6.1 transpiled **full QASM2 bytes** and SHA256,
   optimization level, target basis, approximation degree, transpiler seed.
4. Independent QuPRS v0.9.1 or v0.14.0-candidate verifier invocation
   against the **same generated QASM bytes**, using fixed executable
   version/SHA, backend, method and selected WMC Solver.

Every recorded result must be keyed at least by the input QASM SHA256,
verifier source SHA, backend, method, Solver, full tolerance tuple, run ID
and attempt index. Never identify a scientific result solely by a
human-readable circuit family, a date or the branch name.

## Outputs and required audit data

The Git-tracked evidence directory
`docs/development/tacas26-qiskit-version-fidelity/` contains:

- `qiskit142.json` / `qiskit261.json`: original per-version observations,
  including Qiskit, Python, NumPy, other installed dependency versions,
  runner/platform, archived QASM paths and output SHA256.
- `generated-qasm/qiskit-{version}/{circuit}-opt{level}.qasm`: **actual
  compiler output bytes**. The solver/QuPRS comparison must consume
  exactly these files, without retranspiling.
- `comparison.json` and `comparison.csv`: fidelity comparison;
  the historical frozen-QASM column is not silently interpreted as a
  controlled legacy-optimizer baseline.
- `transpiled-inputs.jsonl`: one **observed** row per generated QASM,
  including source/input/output hashes, exact compiler settings, exported
  QASM2 numerical metric and the metric's definition.
- `planned-verifier-runs.jsonl`: explicit **NOT_COLLECTED** placeholders
  for v0.9.1 / v0.14.0 candidate. These ARE NOT QuPRS outcomes.
- `evidence-manifest.json`: CI run/commit, source versions, counts, SHA256
  of saved QASM files and evidence datasets. The manifest itself lives in
  the Git commit and is not self-hashed.

Both CI artifacts (temporary) and repository commits (longer-lived,
protected by repository history) retain these files. Do not delete or
overwrite historical runs without preserving the original commit/run
and immutable input identity.

### Required fields for every actual QuPRS invocation

- **Source and execution identity:** full source/translated QASM file paths,
  SHA256, QuPRS version, full source commit, Python/Rust backend, environment
  and package versions, source workflow and GitHub Actions run/job/attempt
  identifiers, original output filename, Solver executable SHA/version/mode.
- **Configuration:** `method`, `rr_tolerance`,
  `wmc_phase_tolerance`, `approximate_distance_tolerance`, any relevant
  legacy magnitude tolerance, timeout, CNF weight format and MPFR digits/bits.
  Record whether each parameter is explicitly supplied or from a default.
- **Reduction:** whether RR was entered; what rule(s) fired, if observable;
  whether RR determined the result before WMC; final residual PathSum
  fingerprint; for Hybrid, verify that the residual—not the original
  PathSum—was converted into CNF. If tracing is unavailable, write
  `NOT_INSTRUMENTED` rather than guessing.
- **Solver:** whether WMC was invoked; actual CNF and weights SHA256;
  raw solver stdout/stderr (byte-preserving file or lossless UTF-8 plus
  hash), original printed real/imag component strings, parsed values,
  normalization exponent, solver-internal MPFR setting and separately
  **printed** precision. Do not substitute a derived decimal number for
  the solver's actual printed value.
- **Numerics:** the full distance formula/metric name, point estimate,
  any independently justified error bound, printing-limited resolution,
  signed physicality residual, tolerance used, precision warning,
  `decision_basis`, float-vs-high-precision conversion provenance.
- **Verdict:** the exact `equivalent` / `equivalent*` /
  `not_equivalent` / `unknown` label, independently derived binary
  EQ/NEQ decision, comparison against paper, and any mismatch reason.
  Do not count `equivalent` vs `equivalent*` as a binary mismatch.
- **Failure state:** distinguish an actual Solver Timeout, an external
  watchdog cancellation, an exception, missing result and successful RR
  completion. Do not infer a WMC number from a Timeout or RR-only result.
- **Performance:** only measured and interpreted through a separate
  CodSpeed source run; do not present Actions wall clock or a timeout
  budget as a performance benchmark.

For any step not executed or not instrumented, use explicit statuses,
`null` values and a reason. **Missing is not zero**. Retain the raw
source record and create new derived interpretations as separate records.

## Fidelity metric limits

For <=8 qubits, the current Qiskit comparison uses full-operator
projective distance with a float64-stabilized aligned-Frobenius formula.
For 9–22 qubits, it uses the **maximum of two phase-aligned statevector
differences** for input `|0...0>` and `|+...+>`. The second measure is
NOT the QuPRS trace-based projective operator distance, an error
certificate, or an upper bound for all input states.

Do not use the two-state number as a directly interchangeable tolerance
or to claim Qiskit 2.6.1 was more semantically exact without full
operator/independent mathematical support. Preserve the per-sample
complex overlap and input labels.

## Connections to pre-existing historical evidence

Historical v0.9.1 GPMC raw stdout and WMC replay are already stored in:

- `docs/development/tacas26-results/wmc-evidence.json`
- `docs/development/tacas26-results/results.json`
- `docs/development/tacas26-wmc-tolerance-evidence-contract.md`

The 101-case modern Ganak/GPMC numerical comparison has a separate
permanent archive in
`docs/development/tacas26-ganak101-permanent/`.

These historical numerical counts are tied to the **paper-frozen QASM**;
they MUST NOT be copied into a v0.9.1/v0.14.0 trial whose input is
freshly transpiled Qiskit 2.6.1 QASM. Even when circuit names match,
their actual CNF/weights and weighted counts can differ.

At archive creation, `planned-verifier-runs.jsonl` has no real QuPRS
verdicts, RR traces, Solver WMC outputs or CodSpeed data. The verifier
comparison is a separate experiment, to be executed and archived with
its own pinned source/evidence manifest. A `v0.14.0-candidate` branch
name is not sufficient; record a concrete commit SHA for each trial.

## Generation

After both independent pinned compiler jobs successfully save their full
QASM2 files, the aggregation job verifies the saved SHA256, copies both
sets into the Git archive, then runs:

```bash
python -m scripts.tacas26_comparison_evidence \
  --archive-dir docs/development/tacas26-qiskit-version-fidelity
```

Any missing/mismatched QASM, version, parameter tuple or expected
case/row causes a hard failure before publishing the manifest.
The script does not execute a quantum verifier or Solver and never
fabricates WMC or RR evidence.
