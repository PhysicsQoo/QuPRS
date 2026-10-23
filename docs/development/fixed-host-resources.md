# Fixed-host solver resource trials (opt-in)

## Delivery and research validation

The GitHub-hosted same-job comparison is an exploratory integration and
resource-observation test. Acceptance of the opt-in tooling requires source
correctness, bounded native process lifecycle checks, complete provenance and
fail-closed trial summaries; it does **not** require a registered self-hosted
runner or a fixed physical-host result. A dedicated, controlled Linux host is
an optional separate research validation for paper-quality absolute or
cross-version Walltime and resource claims. Hosted observations must never
be labelled as fixed-physical-host evidence.

Measured-trial Hybrid execution-path classifications exclude warmup routes.
Warmup route counts remain available as separate metadata.

The existing [benchmark experiment policy](benchmark-testing.md) distinguishes
CodSpeed Simulation from wall-clock execution and sampled process-tree RSS.

The `scripts/fixed_host_resource_repeats.py` helper runs repeated, bounded,
**real equivalence checks** on one externally controlled Linux host. It reuses
the original representative MQT QASM inputs and original strategies/directions
and tests the selected GPMC or Ganak tool independently (Python/Rust backend).

Use a dedicated, otherwise idle CPU host and keep **the same machine**,
CPU frequency governor/affinity, Linux image/kernel, Python/Rust environment,
GPMC/Ganak binary SHA256 and input QASM files for every compared run.
A Docker image or `ubuntu-latest` label alone is **not** a fixed CPU host.

Example (run inside the validated Python 3.12 environment with QuPRS built):

```sh
python scripts/fixed_host_resource_repeats.py \
  --host-id research-cpu-a --case grover4 --case qaoa7 --case qft16 \
  --solver gpmc --solver ganak --backend python \
  --warmups 1 --repeats 4 --walltime 90 --solver-timeout 45 \
  --rss-limit-mib 3072 --sample-ms 50 \
  --output-dir /tmp/quprs-fixed-host-run-001
```

Use `--backend python --backend rust` in the same run to compare both
backends on the **same** controlled host, or select a single backend if
needed. Each group has one warmup and four measured repetitions.
The fixed-host driver executes the groups in four counterbalanced rounds:
**forward / reverse / reverse / forward** over circuit/solver/backend
combinations. This reduces order bias without proving that thermal drift
or contention is absent. Runs with unbalanced repeat counts fail preflight.

Each trial is written to a distinct JSON path, and the `manifest.json`
is atomically checkpointed **after every trial**, including incomplete
attempts. The manifest preserves host ID, CPU description, source SHA/tree,
toolchain, native solver hashes, planned and completed attempts, warmups,
per-group Hybrid path classification and each raw observer result. The
`summary.csv` separately reports Walltime medians/MAD, sampled RSS and
whether the group was RR-only, WMC-reported or mixed. Failed or interrupted
jobs must retain their last completed manifest and checksums.
Only complete, positive checks with valid resource observations enter
the **Hybrid end-to-end** median Walltime and sampled RSS summaries.
A successful RR-only Hybrid check may legitimately report `tool_time=None`;
it is not an invalid result or a missing solver failure. The manifest
distinguishes `RR_ONLY_REPORTED`, `WMC_TIME_REPORTED` and
`MIXED_HYBRID_PATHS` from the observed metadata, not from the circuit name.
Numeric tool time alone does **not** establish a true native WMC execution:
any **Solver-only** speed/memory claim requires separate model-counting
`execve`/input evidence, excluding Ganak `--version` probes. A mixed-path
group is valid for Hybrid end-to-end comparison but is **not** valid for
Solver-only attribution. Every failed, missing, resource-inconclusive or
invalid case remains visible and blocks that group.

**Timeout and descendant cleanup (Linux only):** Each outer trial runs
in a new process group. The Python and Rust native solver supervisors may
themselves create independent sessions/process groups: terminating only
the outer group would therefore be insufficient. The trial harness enables
Linux child-subreaper mode, kills its outer group on timeout, then discovers,
terminates and reaps adopted descendants across session/group boundaries.
On normal worker exit, unexpected live descendants also trigger cleanup.
Any timeout, needed post-exit cleanup, failed inspection or incomplete reap
makes the group **INCONCLUSIVE**, even when a stale JSON reports success.
Tests include a clean completion, a hanging three-level mock tree with
independent sessions, and an early-exiting parent leaving a detached child;
they do not invoke GPMC or Ganak.

This is a controlled **Linux** lifecycle contract, not a portable macOS/Windows
one. It does not promise to kill processes delegated to a different privileged
supervisor or an external cgroup, nor an uninterruptible kernel task. Run
real forced-timeout and orphan checks on the dedicated research host for
**both** native solvers and Python/Rust backends before accepting empirical
performance evidence.

**Memory terms and limitations**

- `elapsed_seconds`: end-to-end monotonic Walltime, including solver I/O
  and subprocess startup; repeat on a controlled host for A/B evidence.
- `sampled_peak_tree_rss_mib`: observed max of parent and *live descendants*
  sampled at the configured interval. It can miss short-lived solver peaks,
  so this is **not** a certified exact instantaneous Peak RSS.
- CodSpeed v5 `Memory`: a **separate** allocation/eBPF instrument. Heap
  peak/total allocations are not process-tree RSS; external solver child
  coverage must be explicitly established, not inferred from simulation
  subprocess tracking. `--experimental-memory-track-physical` is experimental
  and reports a different physical-memory metric, not a validated RSS peak.

CodSpeed Memory should initially run only as an isolated, opt-in diagnostic
on a kernel that supports eBPF/BTF and the target native allocator. Keep its
raw run, instrument version, tracked processes/allocators and result scope
separate from this observer. Neither metric creates a GitHub-hosted
performance regression gate or modifies the maintained v5 Simulation
baseline.


## GitHub-hosted within-job exploratory comparison (opt-in)

Use the separate `Opt-in Hosted Solver Resource Comparison` Actions workflow on
the diagnostic research branch to obtain **actual native-solver end-to-end
Walltime and sampled process-tree RSS on one GitHub-hosted VM**. This is
*not* the dedicated fixed physical host, and its output **must not** be
combined with fixed-host or CodSpeed Simulation/Memory baselines.

The workflow uses one `ubuntu-24.04` job and one exact-source build for all
trials. The `scripts/hosted_solver_comparison.py` driver preserves the
original Grover4, QAOA7 and QFT16 QASM pairs, strategies and directions.
For each case it runs four cells (GPMC/Python, Ganak/Python, Ganak/Rust,
GPMC/Rust) with one warmup and **four** measured repetitions per cell.
The measured rounds reverse the cell and circuit ordering as
forward / reverse / reverse / forward (an ABBA-like scheduling control).
It does not establish randomization or eliminate shared-host interference.

Each of the 60 scheduled trials receives a unique filename, including failed
runs. After every trial the manifest is atomically checkpointed; a missing
or invalid sample remains **INCONCLUSIVE**, not an excluded outlier.
Artifacts contain the exact source/tree SHA, native binary hashes, original
input QASM SHA256, CPU/kernel and run metadata, all trial JSON, manifest,
CSV of median/MAD Walltime and observed RSS summaries, and SHA256SUMS.
A nonzero workflow result does not erase evidence: artifact upload is
configured to run even when an experiment reports INCONCLUSIVE.

Comparisons **within the same job/VM** may support exploratory hypotheses
about relative solver behavior. A separate Actions run can use different
underlying CPU hardware, frequency policy, temperature, contention or VM
placement, even with the same `runs-on` label. Replicate on independent runs
before claiming stability, and use a controlled research host for
paper-quality long-term/cross-version performance claims. Avoid a
percentage-based GitHub-hosted gate.

To invoke the driver in a prepared Ubuntu Linux development environment:

```sh
python scripts/hosted_solver_comparison.py \
  --case grover4 --case qaoa7 --case qft16 \
  --warmups 1 --repeats 4 \
  --walltime 90 --solver-timeout 45 \
  --rss-limit-mib 3072 --sample-ms 50 \
  --output-dir hosted-solver-evidence/trials
```

The original `scripts/fixed_host_resource_repeats.py` and optional
`quprs-research` self-hosted job remain available for a distinct
controlled-environment study.


## Additional paper cases: native solver eligibility (opt-in)

The original three-case exploratory cohort remains the default. A separate,
non-baseline `Opt-in Additional Solver Case Coverage` workflow first tests
two additional **existing** MQT pairs, VQE4 and Graphstate16. The profiling
resolver obtains the original method, strategy, source/transpiled order and
QASM paths from `test/_benchmark_cases.py`; no algorithm or gate is changed.

The native preflight runs outside every timed region and uses `strace` to
verify a successful `execve` of the selected packaged GPMC or Ganak
executable. For each candidate, both Python and Rust must independently
show real solver launch and a positive equivalence result. A case with
partial native coverage, a failed equivalence verdict or a missing native
`execve` is explicitly **ineligible** for solver-comparison timing, even
if reduction-only results otherwise appear equivalent. This prevents
equating Path-sum Reduction performance with GPMC/Ganak execution.

Only eligible cases are passed to the interleaved hosted resource observer
with the unchanged warmup, four measured repeats, identical time/RSS
limits, original QASM hashes and all raw evidence. The preflight may
legitimately select zero cases; the workflow then reports an inconclusive
experiment and uploads the negative eligibility evidence without quietly
substituting another circuit. Such an outcome is informative and must not
be relabelled as a solver performance result.

The new cases are optional and are not appended to every existing
CodSpeed/Pytest regression suite, so they do not expand the maintained
baseline or introduce runtime-derived CI percentage gates.


### First optional-case eligibility result

In [GitHub-hosted Actions run #39778599649](https://github.com/PhysicsQoo/QuPRS/actions/runs/39778599649),
the four VQE4 solver/backend combinations all passed actual native
`execve` preflight and yielded positive `equivalent*` classifications.
VQE4 therefore qualified for 20 observations (4 combinations × 1 warmup
+ 4 measured repetitions), all accepted on that VM. Run artifact
`additional-native-solver-case-evidence` retains preflight `strace`
evidence, raw observation JSON and SHA256SUMS.

By contrast, Graphstate16, with the original `naive` strategy, returned
`equivalent` in all four combinations **without native CNF model-counting work**
(`solver_time=null` in each). It is a legitimate reduction-only success,
not a failed quantum equivalence result and not a GPMC/Ganak benchmark.
The preflight must keep semantic correctness, numerical solver timing and
verified native launch as **separate fields**.

Do not compare one VM's VQE4 timing against a different VM's other case
timing as though it were a controlled same-host result. Native tool-time
and end-to-end Walltime are distinct, and observed sampled-tree RSS cannot
be described as exact peak RSS.
