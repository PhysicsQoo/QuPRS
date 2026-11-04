# QOO-156 — internal Linux cgroup-v2 controller and P1 CLI timing (2026-11-04)

> **Research-only source branch**: `experiment/qoo156-internal-cgroup-p0`. No `dev`/main merge. This document distinguishes hard kernel-resource evidence, authentic WMC science, and performance admission.

## 1. Why the original controller layout was invalid

The initial CLI `MemoryCgroup::new` created `quprs-cli-<parent PID>` under its own current cgroup. On an ordinary cgroup-v2 *domain* hierarchy, enabling `+memory` on a parent still containing the supervisor violates the **no-internal-process rule**. The exact unmodified [preflight #41856706958](https://github.com/PhysicsQoo/QuPRS/actions/runs/41856706958) yielded `EBUSY` at `cgroup.subtree_control=+memory`, before building Rust.

Linux cgroup-v2 memory delegation must instead have an **empty**, memory-enabled delegated root, with the nonroot CLI supervisor in one child leaf and its isolated worker plus descendants in a *sibling* `quprs-cli-<PID>` cgroup. Source-scoped CLI implementation: [commit 5a09d30](https://github.com/PhysicsQoo/QuPRS/commit/5a09d30beb125e73c5541d7400cfac08b4704d53) changes only `rust/cli/src/supervisor.rs` to search actual owned/writable empty ancestors with `+memory`, configure `memory.max` and `memory.oom.group=1`, and read back the exact cap. If no enforceable delegated cgroup is found, CLI **fails closed** and does **not** relabel `RLIMIT_AS` as physical RSS protection. The Rust `rust/pathsum` subtree is unchanged.

The test-only Docker wrapper starts with privileges **solely to create a writable cgroup namespace** and delegate a group. It then runs the real `QuPRS_cli` as UID/GID 65534 with no privileged CLI rights. This does **not** imply an ordinary nonroot Linux host has been delegated a group or that Mac native `--max-memory-mib` is supported.

## 2. Internal controller positive and normal control

Exact source-pinned [GitHub Actions #41857419941](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857419941) **SUCCESS** (commit `954b065`). Test-only debug allocation is restricted to `debug_assertions`, and the underlying memory controller is the same Rust CLI implementation:

| Case | Actual worker memory.max | memory.peak | Internal kernel oom_kill | CLI code and output | Verdict |
|---|---:|---:|---:|---|---|
| Synthetic 192 MiB touched pages, limit64MiB | 67,108,864 B | 67,108,864 B | 2 | 125, `MemoryLimitExceeded`, stdout empty | **PASS** |
| Valid one-qubit circuit, limit256MiB, bounded 32 MiB test allocation | 268,435,456 B | 34,598,912 B | 0 | 0, complete Reduced PathSum State | **PASS** |

No Python-side simulated OOM or native solver modifications.

## 3. Authentic release GPMC/Ganak under internal CLI cap

[Actions #41858651234](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858651234), fixed source `0c349a6`, overall **NOT_ADMITTED** due one missing real Ganak low-cap process identity, even though three fully assessed cases passed:

| Solver and case | CLI requested cap | Kernel cgroup oom_kill | CLI science/output | Actual solver PID observed? | Classification |
|---|---:|---:|---|---|---|
| GPMC `-mode=1`, QFT16 | 256MiB | 0 | exit0, complete `not_equivalent` | yes | **COMPLETE PASS** |
| GPMC `-mode=1`, QFT16 | 32MiB | 3 | exit125 `MemoryLimitExceeded`, empty stdout | yes; PID gone | **INTERNAL OOM PASS** |
| Ganak 2.8.0 `--mode=6`, VQE4 | 256MiB | 0 | exit0, complete `not_equivalent` | yes | **COMPLETE PASS** |
| Ganak 2.8.0 `--mode=6`, VQE4 | 64MiB | 2 | exit125 `MemoryLimitExceeded`, empty stdout | **not observed** | **GROUP SAFETY PASS; SOLVER VICTIM NOT_ADMITTED** |

For Ganak 64MiB, group memory.peak exactly 64MiB and CLI returned the correct typed resource failure; this **does not prove** that the specific Ganak PID was selected by kernel OOM. One controlled 70MiB boundary refinement [#41859255540](https://github.com/PhysicsQoo/QuPRS/actions/runs/41859255540) also had exact memory.max, `oom_kill=2`, CLI125/no false verdict, but no Ganak PID record. **Do not repeat blind cap tuning.**

The follow-up **separate** source-locked authentic-Ganak experiment witnesses PID+ELF+argv under `--max-memory-mib 256` before inducing test-only additional page pressure **in the exact CLI-created worker cgroup** (the requested cap remains unchanged). This measures **adversarial group containment**, not Ganak's natural working-set minimum. Require real PID gone, kernel oom_kill, CLI typed125/empty science output, no harness-induced kill of the authentic solver. The external Docker-only [host attribution run #41855049422](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855049422) PASS is separate and must not be substituted for this internal CLI test.

## 4. P1 CodSpeed evidence and blocker

Connected official CodSpeed [run 6aeb4b9d](https://app.codspeed.io/PhysicsQoo/QuPRS/runs/6aeb4b9d09f1ddb2bf501af8) source-paired `dev@79e975b0` vs bounded CLI HEAD `e7cef40` on the same Ubuntu hosted job, `rust/pathsum` tree equal, ABBA order, 3 measurement rounds per variant:

| Tiny CLI workload | BASE mean of two minima | HEAD mean of two minima | Absolute delta | Relative delta |
|---|---:|---:|---:|---:|
| Single H | 1.041 ms | 2.235 ms | +1.195 ms | +114.8% |
| GHZ32 native RR | 1.180 ms | 2.381 ms | +1.200 ms | +101.7% |
| QPE exact8 native RR | 2.031 ms | 3.217 ms | +1.186 ms | +58.4% |

**Instrument warning:** all 12 are NON-MACRO WallTime with potential VM noise. This is OBSERVATIONAL only; the similar ~1.2ms fixed delta is consistent with subprocess, pipes and capture thread overhead, not native RR algorithm regression. Do not claim `no performance regression`. Existing true `runs-on: codspeed-macro` [GitHub job #126558702309](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124/job/126558702309) is **QUEUED and unassigned**, and the queued source is older than the final I/O / internal cgroup revisions. No valid final-SHA Macro performance admission yet. Do not dispatch duplicate Macro jobs while the runner is unavailable.

## 5. Cross-platform and merge gates

- Source-scoped Ubuntu24.04 and prior macOS14 CLI correctness [#41857895087](https://github.com/PhysicsQoo/QuPRS/actions/runs/41857895087) SUCCESS. New `macos-15` native Apple Silicon M1 is requested separately [#41858819331](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858819331); never infer PASS before assigned/complete.
- A native hosted macOS ARM64 correctness run is **not** equivalent to Mac mini/OrbStack Linux ARM64. Physical Linux cgroup delegation and process-tree containment must be separately verified in that runtime; production hosts without delegation fail closed.
- Do not integrate the whole experiment branch. Isolate CLI source change + focused tests to a clean `dev`-based PR **only after** remaining safety and actual Macro performance gates are decided. No solver code, numerical tolerances, native RR/CNF loops, or full five-shard CodSpeed retests for documentation changes.

## 6. Follow-up source-pinned real Ganak internal worker-cgroup OOM: PASS

**This new result supersedes only the previously pending *adversarial* Ganak containment verification, not the 64/70MiB natural low-cap PID attribution limits.**

[GitHub Actions #41860226028](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860226028) completed **SUCCESS**, exact tested source `464328ec3f21891841c6dc5d90f67e2c5a58dc31`, [evidence artifact #13340195444](https://github.com/PhysicsQoo/QuPRS/actions/runs/41860226028/artifacts/13340195444). The same native release CLI binary SHA256 `2242188d29056c5cc6db1d91bc6132bee1c91a212cf35fd54dacee6d2f5c3d50` and **unmodified** Ganak 2.8.0 ELF SHA256 `934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd` were used for the high-cap VQE4 science control and controlled OOM.

- **Positive high-cap control**: `--max-memory-mib=256`, exact readback 268435456 bytes, true `/opt/ganak --mode=6` PID witnessed, kernel `oom_kill=0`, CLI exit0 with complete `not_equivalent`, no test pressure.
- **Adversarial containment**: same requested CLI cap (256MiB) and same QASM, true Ganak PID20 + start time + full solver argv + pinned ELF observed **before** pressure, `SIGSTOP` confirmed. Test-only Python pressure then joined the **same CLI-created `quprs-cli-<PID>` worker cgroup**; the real Ganak was held alive until the kernel group OOM. `memory.oom.group=1`, readback cap268435456 B, actual peak268435456 B, `oom_kill delta=4`, authentic Ganak PID gone, CLI exit125 `MemoryLimitExceeded`, stdout empty. No harness-initiated kill of authentic Ganak. Output `QOO156_INTERNAL_REAL_GANAK_PRESSURE=PASS`.
- This proves a **real Ganak solver descendant is contained in the nonroot Rust CLI-created cgroup, and a kernel-enforced group OOM returns a typed non-scientific failure with no partial verdict**. The first-party root harness uses controlled pressure and supervisor-only test privileges. **Do not** infer Ganak natural minimum RSS, universal memory limit, lack of CLI fixed subprocess overhead, or ordinary-host delegation from this result.
- The earlier natural low-cap VQE4 Ganak 64/70MiB tests correctly returned typed125 and kernel events but did not witness PID before OOM; **their solver-specific attribution remains NOT_ADMITTED**. The strong group-containment certificate above is a *different* experiment that does not rewrite historical results.
- GPMC QFT16 native internal cap complete/positive real solver OOM were separately certified in exact [#41858651234](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858651234). It is now fair to state **both GPMC and Ganak have positive first-party internal CLI child-cgroup real-solver containment/OOM evidence**, each under its precise tested workload/protocol.

### Remaining gates still open

1. `macos-15` Apple Silicon native focused CLI test [#41858819331](https://github.com/PhysicsQoo/QuPRS/actions/runs/41858819331) is queued/unassigned as of this note; Ubuntu24.04 leg PASS. Mac mini/OrbStack **Linux ARM64** parity is a distinct environment and remains NOT_TESTED.
2. True assigned CodSpeed Macro job [#41825389124](https://github.com/PhysicsQoo/QuPRS/actions/runs/41825389124) remains queued/unassigned and tests an older source. The hosted ABBA showed a ~1.2ms fixed supervisor cost but has official non-Macro reliability warning. **P1 performance NOT_ADMITTED**, no claim of zero overhead.
3. A *regular unprivileged production Linux host* with a pre-delegated writable cgroup must still have its environment contract and permission model documented/verified. The protected CLI fails closed outside such an environment.
4. No `dev`/main merge of the entire experimental tree; no solver modifications, no full five-shard rerun due solely to this Markdown evidence.

