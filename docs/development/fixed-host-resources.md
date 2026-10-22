# Fixed-host solver resource trials (opt-in)

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
  --warmups 1 --repeats 3 --walltime 90 --solver-timeout 45 \
  --rss-limit-mib 3072 --sample-ms 50 \
  --output-dir /tmp/quprs-fixed-host-run-001
```

For Rust, repeat on the same host with `--backend rust` and a **different**
empty output directory. The output `manifest.json` preserves the host's
self-reported identifier, CPU description, source SHA/tree, Python, Rust,
tool executable hashes, warmups and every trial's raw observer result.
Only complete, positive checks that report a numeric WMC solver time enter
the median Walltime and observed RSS summaries. Every failed, missing,
resource-inconclusive or invalid case remains visible and blocks that group.

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
