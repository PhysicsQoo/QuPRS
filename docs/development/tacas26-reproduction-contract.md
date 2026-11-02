# TACAS 2026 paper reproducibility gate (v0.14.0)

Status: **scientific acceptance requirement, NOT YET CERTIFIED**.

A reproducer must explicitly distinguish an archived-paper verdict from a new
scientific claim. Reproducing the published label is necessary but is not, by
itself, evidence that two independently truncated source QASM files are
operator-equal to the new 1e-8 projective-distance threshold.

## Exact published artifact contract

- Official source: PhysicsQoo/Artifact-of-tacas26 at
  `d8d3e7da555e9e20bdec6f3abe4a13ad899af62b`.
- The artifact Dockerfile actually clones QuPRS **v0.9.1**, Git
  `e928abc47dd15926364ec77905eb0d5dc92ce8cc`, not the later v0.13.0.
- Prefer the archived Zenodo image DOI `10.5281/zenodo.18158735`
  over mutable Docker Hub tags and floating Python dependencies. Audit its
  installed QuPRS and GPMC binary hashes before claiming exact reproduction.
- `experiments/table_MQT.py`: paper original QASM vs
  `h,ry,rz,cx`, Hybrid/Proportional, 200-second timeout. Its
  `tolerance=1e-10` line is unused; the effective value is
  QuPRS v0.9.1 `config.TOLERANCE=1e-10`.
- v0.9.1 GPMC invokes `-mode=1`, parses complex numbers to Python
  float and evaluates `round(log2(abs(count)), 3)` **before**
  applying the 1e-10 magnitude tolerance. No independent projective
  distance tolerance exists in v0.9.1.
- The archived paper expects QPE-inexact20 positive to be
  `equivalent*` (up to global phase), Hybrid ~0.623 seconds on the
  paper's Azure E8ads v5. Historical walltime is **not a CodSpeed number**.

## Two required, separate acceptance lanes

**A. Artifact fidelity (historical outcomes).** Run the unchanged archived
image and scripts, source-pinned 200-second budget, reproduce the reported
Table 2 / Table 3 verdicts and distinguish timeout/OOM. Record the real
solver phase, output and exact archived source/image identity. Compare the
verdict matrix across the actual paper corpus; no selective omission.
Historical runtimes are descriptive, not valid speedups against modern
hardware. All new formal runtime comparisons must use CodSpeed.

**B. Scientific continuity (modern).** Keep the 1e-8 default
`approximate_distance_tolerance`, 1e-10 RR and high-resolution WMC
classifier unchanged. For each historical positive/negative, compare the
pinned original QASM inputs, observed printed WMC count, distance estimate,
precision warnings, actual stage and source-pair oracle. A discrepant
positive is `SOURCE_PRECISION_REVIEW` until an *independent* source-difference
bound or corrected Qiskit transpilation is available. The default must
not be relaxed merely to reproduce a prior label.

**C. Explicitly configured reproduction (non-default).** The existing
modern QPE-inexact20 tolerance sweep at SHA
`d8db00a4c2ec42a6be41170e5ded0cd94ffc7683` observed:
1e-8 and QCEC reference 2e-8 -> not_equivalent;
3e-6 -> not_equivalent; 5e-6 and 1e-5 -> equivalent*;
and genuine Random_Rotation negative still not_equivalent at 1e-5.
A case-specific, documented distance tolerance may reproduce the published
label under a **different** approximate-equivalence contract, but it is
*not* an exact-equivalence proof or a retroactive correction to the paper.

The `scripts/replay_tacas26_artifact.py` pure-Python source audit
replays the exact v0.9.1 **magnitude** rounding on the recorded modern
Python GPMC log count and source hashes; it requires an explicit phase to
replay a full historical verdict. Without the archived solver's phase it
returns `PHASE_UNOBSERVED`, not a fabricated `equivalent*`. This
provenance-only tool does not alter the QuPRS API, invoke GPMC, measure
runtime, or certify source equivalence.

## Graduation / P2 exit requirements

1. Source-pinned manifest fully covers both paper Table 2/3 corpora and
   approved supplemental circuits, including expected verdict and timeout;
   report deviations, not only positives.
2. v0.9.1 archived environment passes observed historical verdict checks,
   including actual QPE-inexact20 `equivalent*` with phase evidence.
3. Modern backend Python/Rust and Hybrid/WMC-only each have clearly recorded
   current verdict and tolerance, no hidden fallback to old rounding.
4. Source-transpilation fidelity and solver arithmetic warnings reviewed:
   (D_\mathrm{proj}) bound independent of sampled states if asserting
   new 1e-8 operator equivalence.
5. Performance gates use CodSpeed on comparable runner cohorts with
   explicit source+HEAD identity; retain main's original 32 benchmark
   URIs until the agreed versioned sunset. No mixing old paper seconds with
   new CodSpeed measurements.

Keep PR #131 Draft until both science and performance concerns are qualified.


## Opt-in real archived QPE-inexact20 replay (added 2026-11-02)

Workflow: `.github/workflows/tacas26-archived-qpe20.yml` has a standalone
opt-in PR edited job, not part of any routine CodSpeed shard or mandatory
PR suite. It downloads the **prebuilt** Zenodo 18158735 `tacas26.tar.gz`,
records its actual SHA256 and Docker image inspect JSON, then loads it without
rebuilding. The container runs `scripts/tacas26_archive_qpe20_probe.py`
with network disabled, original `/app` QuPRS executable untouched and
script mounted read-only. It verifies QuPRS v0.9.1 commit, QASM SHA256,
legacy classifier source and tolerance, records the package/OS/Qiskit
versions and actual historical `gpmc.so` SHA256.

The observer intercepts the original `ps2wmc.subprocess.run` and
`ps2wmc.run_wmc` **without replacing their results**. It preserves
unmodified solver stdout, stderr, command/returncode, complex count,
historical phase computed through the original `get_theta` and final
QuPRS Hybrid/Proportional verdict. It **fails closed** unless it obtains
real `equivalent*` from the archival image and the replayed phase
agrees with the returned historical verdict. The JSON is saved on both
success and failure. QPE20 is one required step, not a claim that all
36 paper rows or WMC-only timeout have been reproduced.

The first CI result must be inspected for archive availability and
disk constraints before scheduling the complete paper corpus. If the Zenodo
prebuilt download fails, report **NOT_EXECUTED / ARCHIVE_UNAVAILABLE**,
not a pass based on a mutable Docker Hub tag. Time metrics in the original
QuPRS object are not evidence of modern performance; use CodSpeed for
all quantitative performance comparisons.


## Pinned source checkout option (no Docker download, same original algorithms)

An alternative to the archived Zenodo Docker is the existing CodSpeed
workflow's *separate opt-in* job `tacas26-source-qpe20`: checkout
QuPRS v0.9.1 at exact immutable commit
`e928abc47dd15926364ec77905eb0d5dc92ce8cc` into
`$GITHUB_WORKSPACE/historical` and import only historical
`src/QuPRS`. Python 3.12 + Qiskit 1.4.2, numpy<2, SymEngine, and the
original **packaged** `gpmc.so` are used; no Rust build, no modifications
to v0.9.1, no repository fork and no worktree on the user's computer.
The independently mounted probe uses `QUPRS_ARCHIVE_ROOT` to determine
the exact historical checkout, without changing mathematical operations.

This is *SOURCE_REPRODUCED*, not
`ARCHIVED_IMAGE_ENVIRONMENT_REPRODUCED`. Its GPMC binary hash, Python
pip freeze and raw phase/output are retained. The job fails closed if the
actual v0.9.1 verdict differs from paper `equivalent*`, if GPMC was
not invoked, if the phase replay is inconsistent, or if any original
source SHA does not match. This option allows reproducing the original
algorithm without first retrieving the large Zenodo Docker tarball.


## Full source-pinned TACAS case registry (2026-11-02)

The executable source-pinned matrix is built *from the existing* manifest
\`docs/development/paper-corpus-manifest.json\` and \`benchmarks/codspeed/paper_difficulty.json\`.
It explicitly covers 187 QuPRS invocations:
- 36 Table2 positive pairs x 3 modes (Hybrid/RR/WMC) = 108.
- Table3(a) supplemental WState32 positive Hybrid = 1.
- 37 Table3(b) original-versus-Random_Rotation pairs x Hybrid/WMC = 74.
- 4 Feynman source pairs as a separately labeled RR-only Figure3 sample.

Table3(a) other positive Hybrid cases reuse the identical Table2 source/solver
observations; separate QCEC/Quokka/PyZX experiments are *not* falsely
presented as QuPRS reproductions. The paper says 35 in prose but Table2
has 36 listed rows. Exact source Git blob SHA1 is verified for each official
positive pair; negative QASM bytes are tied to the fixed v0.9.1 historical
checkout, SHA256 recorded per invocation, never regenerated.

Historical verdict fields not yet individually transcribed from the published
tables are explicitly NOT_YET_TRANSCRIBED. Only the independently reproduced
QPE-inexact20 positive equivalent* is hard-asserted. A returned verdict
without reference expected outcome is an OBSERVATION, not an acceptance pass.
The initial bounded 10-case CI smoke is run with two isolated shards,
200-second QuPRS time limit, separate 215-second watchdog (timeout recorded
as censored, not as not-equivalent), original GPMC native binary and Qiskit
1.4.2. Per-case raw GPMC stdout, phase, complex counts and QASM hashes are
retained. The script stores **no** non-CodSpeed performance measurements.

Full matrix execution requires further explicit opt-in with bounded small
batches; the manifest's 187 identities are a plan, not completed science.


## Full WMC-only / RR-only / Feynman follow-up

The remaining 109 invocations, after 10 actual smoke cases and 68
independent Hybrid work items, are all non-Hybrid:
70 Table2 RR-only/WMC-only, 36 Table3(b) WMC-only, and 3 Figure3
Feynman RR-only. They have a separate opt-in 16-way source checkout
workflow \`tacas26-paper-nonhybrid-full\`, never mixed into the 5 legacy
CodSpeed Simulation shards. Some historical WMC-only examples deliberately
require the full 200-second timeout, and source-run observation is not a
performance benchmark. Launch the expensive continuation only after
confirming full Hybrid evidence is intact and source/paper version checks pass.
