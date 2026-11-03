# CodSpeed v2 — source-pinned cross-instrument benchmark contract

## Status and scope

This replaces the experimental three-shard design. **Five shards only**, with
the original frozen 32 pytest benchmark node IDs and original CodSpeed v5
Simulation semantics. An isolated native Rust CPU experiment runs for **the
same exact commit** in the **same GitHub Actions workflow run**. For pull
requests, the original seven paired Solver-inclusive WallTime workloads also
run for the same HEAD, with a pinned base compiled separately.

The routine workflow is [codspeed.yml](../../.github/workflows/codspeed.yml).
The sole authoritative evidence aggregator is
[report_codspeed_cross_instrument.py](../../scripts/report_codspeed_cross_instrument.py).
Optional CPU subprocess/memory/cross-method experiments use the *same
workflow_dispatch* (and require base_sha for paired modes); standalone
diagnostics are no longer permitted to masquerade as a full PR performance
decision. All expensive optional modes remain off in routine PR CI.

## Same-SHA evidence axes

| Family | Instrument | Routine | Count | Measurement contract |
| --- | --- | --- | ---: | --- |
| Feynman/MQT host | CodSpeed v5 Simulation, subprocess disabled | Yes, five shards | 32 | Original Python/Rust verifier host-only modeled CPU |
| Hybrid GPMC/Ganak paired | CodSpeed v5 WallTime | PR (or manual paired) | 7 pairs / 14 identities | Full new Python process, RR, CNF, external solver, I/O and process exit |
| Native Rust core | cargo-codspeed 6 / CodSpeed v5 Simulation | Yes | 11 | Native PhaseCoeff and RR, no Python and no solver |
| Native Rust memory | cargo-codspeed 6 / Memory | Manual only | 11 | Rust benchmark process allocations, not Solver RSS |
| Solver-inclusive CPU | CodSpeed Simulation with subprocess tracking enabled | Manual only | 7 | Whole verifier plus child solver modeled CPU, not elapsed WallTime |
| Expanded cross-method | CodSpeed Simulation **and** WallTime | Manual paired only | 8 CPU / 48 WallTime | Source-pinned optional matrix, never compare unlike modes as equivalent elapsed-time units |

The three-shard trial workflow and weighted-planner/checker are removed.
The original 32 identities must not be expanded, renamed, or divided into
different benchmark scopes without an explicit migration. A five-shard
collection fails if any node is missing, duplicated, or renamed.

## Source identity and provenance

Every measured source checkout must equal the immutable GitHub event HEAD,
**not** the pull-request synthetic merge commit. The paired WallTime job
additionally checks out the immutable base SHA and builds two independent
Python/Rust environments with identical HEAD QASM fixtures. It preserves
the GPMC submodule revision, dependency freezes, solver verdict, and
instrument statistics.

After each CodSpeed action, write a machine-readable SHA manifest with exact
Git commit/tree, fixture revision, GPMC submodule, instrument, runner and
SHA-256 of the **first-party CodSpeed measurement export**. The final
cross-validate job downloads only artifacts from the **same workflow run**
and rejects source mismatches, duplicate/missing shard IDs and missing
required experiment data. It does not import CodSpeed's carried-forward
values from other commits. The original 32 test names remain the canonical
identity hash, currently
`7eb82617bf092c81c6a6bde6e8cd05cec9bab71879f17b2bf315c9c420c7c8ed`.

Rust core data are uploaded by cargo-codspeed to CodSpeed's service. The
GitHub manifest proves the pinned benchmark source and successful instrument
step, **not** that local Rust numeric metrics are available in JSON; the
audit labels those values remote-only until queried at that exact SHA.
Never fabricate numerical Rust data or pretend the native 11 microbench
identities measure MPFR WMC encoding; they do not yet include that fixture.

The core report links each Rust VQE4/GPMC, QAOA7/GPMC and QFT16/GPMC
host-only CPU Simulation result (full raw instrument record) with that
same SHA's paired WallTime result. These are diagnostic axes, not summable
costs or interchangeable throughput metrics.

## Correctness is separate from performance

Each paired case verifies solver invocation on base and HEAD, source/revision,
stage, backend, solver, direction and verdict. A verdict change excludes a
performance comparison even if both elapsed values exist. Known Ganak
printed-resolution negatives retain PRECISION_LIMITED, **never scientific
equivalence PASS**. The independent complex128 source witness is not a
rigorous distance certificate. Each report has distinct scientific_status,
evidence_collection, and performance_certified fields; CI upload success
does not mean all three gates passed.

The existing Python/Rust scientific tests and v0.14 tolerance policy remain
unchanged. No source angle approximation, solver change, precision weakening
or additional WMC attempt may be introduced merely to improve benchmarks.

## How to interpret results

1. For a particular PR HEAD, inspect one combined cross-instrument artifact
   and all jobs in its workflow run. Require identical HEAD and mode labels.
2. Inspect each **individual circuit/backend/solver** across relevant
   instruments; VQE4 cannot alone determine the outcome of QFT16 or QAOA7.
3. Compare base/HEAD *within the same instrument*, fixture, precision and
   CPU/toolchain cohort. WallTime uses same-host exploratory paired data but
   currently only three measured rounds; it is **not** a qualified Macro
   Runner variance-calibrated release gate.
4. Use a differential flamegraph to explain source-of-cost changes. For
   Rust PhaseCoeff cache, group repeated vs distinct source angles and
   compare direct encoder/from_phase work; record solver workload and
   verdict before drawing causal conclusions.
5. The same-SHA joined report must expose conflicts such as "CPU improves,
   WallTime flat", not silently overwrite a metric, average unlike modes,
   or classify every CI green job as a numerical pass.

Do not compare the old pre-CodSpeed-v5 Simulation baseline against the v5
cycle model without a migration. Do not compare subprocess-tracked Simulation
against the 32 legacy subprocess-disabled identities as if they were the
same benchmark. Cross-hardware simulation cache-model differences and
shared-runner walltime variance require explicit warnings.

## Expensive experiments

Normal source-changing PRs collect exactly one five-shard Simulation suite,
one paired WallTime suite, and one Rust core CPU suite. To request the optional
modes, manually dispatch the unified CodSpeed workflow on the desired
source branch with the exact `base_sha` and any of
`include_solver_cpu`, `include_rust_memory`,
`include_cross_method`; all selected modes run against the same HEAD and
contribute to its evidence bundle. A push to dev/main without a base collects
five-shard CPU and native-core as a BASELINE_ONLY bundle; it **must not** be
claimed as a paired end-to-end regression verdict.

The automatic audit tests check absent or duplicate results, corrupt SHA
metadata, incomplete original 32 IDs, and PRECISION_LIMITED status.
Failure to produce any required same-SHA artifact blocks evidence
collection even if unrelated CI jobs passed.

## Remaining scientific/measurement limitations

- Native cargo-codspeed numeric observations still live in CodSpeed; only
  source and upload provenance can be machine-validated by the GitHub bundle.
- Fine-grained MPFR encoder and CNF stage-level Rust CodSpeed cases should
  be added under separate new IDs, not by changing 32 existing test names.
- Formal WallTime regression thresholds require a qualified stable Macro
  Runner or controlled repeatability and a documented per-case variance
  calibration. Only CodSpeed results may be used to make time-based decisions.
- Repetition-level Solver verdicts, full executable SHA and CNF/weight
  equality should be strengthened in a subsequent dedicated semantic gate.
