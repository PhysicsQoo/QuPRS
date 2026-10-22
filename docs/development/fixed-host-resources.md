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

**Timeout and descendant cleanup:** Each outer trial runs in a new POSIX
session/process group. On an outer timeout, the entire group is sent SIGKILL,
and the immediate worker is reaped. Group cleanup is also attempted when the
worker exits normally, to catch native solvers that survived their Python
parent. A trial requiring post-exit group cleanup is **INCONCLUSIVE** even if
its previously written JSON reports success. Mock subprocess regression tests
cover both paths without starting GPMC or Ganak. Process-group supervision is
not a guarantee for a child that deliberately escapes into a different session;
this harness is intended for a controlled Linux host, and the actual GPMC and
Ganak lifecycle must be verified separately on that host before accepting
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
