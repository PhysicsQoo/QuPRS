# TACAS 2026 paper reproducibility gate (v0.14.0)

Status: **SUBSTANTIALLY_REPRODUCED (QuPRS-only, qualified acceptance)**.
This is a reproducibility milestone, **not** an assertion that every published
case, the archived Docker environment, or formal performance metrics have been
strictly certified. The older strict-acceptance ambition described later in
this document is superseded by the bounded acceptance decision below.

## QuPRS-only qualified closeout decision (2026-11-02)

**User-approved rule:** most major QuPRS TACAS results are reproduced;
exhaustive case-by-case reproduction is **not required**. Stop expensive
retries unless later evidence reveals a clear scientific verdict contradiction
or a correctness defect affecting modern QuPRS. This acceptance applies only
to historical QuPRS source/algorithm behavior, and does **not** certify strict
operator equivalence under the new v0.14.0 tolerance criteria.

**Observed bounded evidence**, from the complete 24-shard original QuPRS
v0.9.1/GPMC experiment
[Actions 41461438155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41461438155)
at SHA `06c6346d0811383e443448d177b1054233cdf06f`:

- All **184 historical QuPRS direct-call identities** were scheduled:
  77 previously observed direct calls plus 107 previously missing calls.
  A new 144-case cohort also repeated 37 positive Hybrid calls to capture
  the RR-column provenance; this is not 144 additional distinct identities.
- **23 / 24 CI shards succeeded**, 1 shard failed because the positive
  `wstate32:wmc_only` child did not write a result file
  (`MISSING_RESULT`); 24 shard artifacts were archived.
- Among the 144 new invocation records: **104** direct comparisons match
  the transcribed paper labels (including matching historical `Timeout`);
  **2** WState16 records returned `Timeout` against the paper's
  unqualified `FAILED_TO_VERIFY`; **3** external-watchdog terminations
  are censored (not verified Solver outcomes); **1** positive WState32
  WMC-only result file is missing; **34** have no independently usable
  paper-label oracle for direct comparison. These categories partition
  all 144 records. No established `equivalent` versus
  `not_equivalent` contradictory verdict was observed.
- A returned **QuPRS `Timeout` matching a paper `Timeout` is a
  legitimate `MATCH`**. Do not count it as a CI failure or pressure
  the solver to finish. `EXTERNAL_TIMEOUT` remains censored;
  `MISSING_RESULT` remains missing, not an assumed timeout.
- The positive **QPE-inexact20 Hybrid `equivalent*`** verdict was
  reproduced directly from the original QuPRS v0.9.1/GPMC source.
  This historical verdict does not change the scientific acceptance
  criteria of the modern v0.14.0 numerical classifier.

**Closeout outcome:** `QU_PRS_PAPER_MAJORITY_REPRODUCED`.
Preserve existing immutable Actions logs, GPMC stdout, per-case JSON,
QASM/source hashes and artifacts; do not delete or relabel ambiguous
evidence. The old 187-item exploratory schema is not the official
184-call execution protocol. The archived paper experiment is a
**qualified historical result**, not a full archival-image/environment
certification or a CodSpeed performance comparison.

**No further large-scale Solver reruns** for WState32, censored watchdogs,
or hard historical cases merely to reach 100% coverage. Keep the 24-shard
reproducer opt-in only; ordinary docs, code or CI updates must not launch
it. Continue separate v0.14.0 science/correctness and CodSpeed work under
their own independent gates; do not attach this historical reproduction
criterion to PR #131 or change production tolerances to force old labels.

## Scope locked: QuPRS only (user decision, 2026-11-02)

**Reproduce QuPRS and only QuPRS.** Use the immutable official TACAS
artifact's scripts, QASM pairs, QuPRS v0.9.1 source and bundled GPMC,
`Hybrid` / `wmc_only` / `reduction_rules` semantics,
`Proportional` strategy, 200-second verification timeout, and the
artifact's derivation of the published RR column from the same Hybrid run.

**Out of scope; do not execute, install solely for benchmarking, or require
any results from** QCEC, Quokka-sharp, PyZX, or Feynver, even though the
submitted artifact launches them in its broader comparison scripts.
No cross-tool speedup claim or competitor-result reproduction is a gate.

The target is **184 direct QuPRS invocations and 37 derived positive RR cells**
(221 QuPRS result cells), with the documented Table 2/3/Figure 3 paper-view
subset clearly distinguished from additional artifact-script cases. The
original-GPMC solver used by QuPRS is an *internal dependency*, not an
independent competitor experiment. Keep already captured exploratory
independent RR-only results as `ADDITIONAL_METHOD_CONTROL`, never replace
the paper's derived RR result with them. Remaining formal performance
comparisons must use CodSpeed; this historical source-verdict run is
scientific reproducibility only.



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


## Dedicated experiment branch, separate from release PR #131

Research lives on `experiment/tacas26-paper-reproduction`, **not** the
`feat/per-call-tolerance-api` branch. The latter was restored to
`af002f35815c8ee90bda0d7c2c5821ba8a43dcf9` with a
checked force-with-lease update *only after* retaining all eight TACAS
research commits on the dedicated experiment ref.

The standalone `.github/workflows/tacas26-research.yml` performs
quick Python syntax and 187-row source/schema audits **only** on commits
to the research branch. Full 200-second historical Solver invocations
are **not** automatically launched by every research push. Any future
expensive cohorts require explicit bounded opt-in activation and
per-shard evidence. Existing archived Actions runs and artifact IDs remain
as immutable historical evidence even after PR HEAD cleanup.

2026-11-02 investigation: all sixteen previously triggered non-Hybrid
shards failed before Solver execution, during `pytest` collection,
because `scripts/tacas26_compare_paper.py` contained an invalid
multi-line `elif ... and obs.get("verdict") in` expression. This is
research report-parser syntax, not 109 measured quantum-verdict failures.
Fix only on this experiment branch, then revalidate the paper oracle
before any repeat of 109 expensive original-GPMC cases.


## Official Artifact code audit (2026-11-02; supersedes provisional 187-call claim)

Reference the *actual* submitted experiment scripts, pinned to
[Artifact-of-tacas26@d8d3e7da](https://github.com/PhysicsQoo/Artifact-of-tacas26/tree/d8d3e7da555e9e20bdec6f3abe4a13ad899af62b),
rather than treating the exploratory 187-ID registry as the exact paper execution protocol.

- \`experiments/table_MQT.py\`: enumerates **37** original MQTBench QASM files
  (36 Table 2 positive rows plus WState32, which also appears in Table 3).
  Per file, it invokes **one Hybrid** and **one WMC-only** QuPRS run.
  Its \`RR_result\` is **derived from that same Hybrid result**:
  \`RR_time = result.pathsum_time\`;
  \`RR_result = result.equivalent if result.to_DIMACS_time is None else "unknown"\`.
  It does **not** invoke a separate \`reduction_rules\` run for Table 2 RR.
  Do not substitute independent RR-only verdicts or times for published RR columns.
- \`experiments/table_MQT_Random_Rotation.py\`: enumerates **37** original QASM
  filenames and pairs with \`Random_Rotation/\`; RR is explicitly disabled.
  Per pair it runs Hybrid and WMC-only, both with \`strategy="Proportional"\`,
  \`timeout=200\`.
- \`experiments/table_Feynman.py\`: enumerates **36** original Feynman QASM
  files paired with \`h,y,z,t,tdg,cx/\` and invokes QuPRS
  \`method="reduction_rules"\` independently, plus the bundled
  \`experiments/feynver\` external comparison. The pre-existing 4-item
  \`feynman_ci_sample\` is **only a smoke sample**, not full Figure 3(a)
  original-script coverage.
- The MQT scripts additionally enable qcec, quokka_sharp, and, for positive
  MQT, pyzx. Reproducing *every comparison tool* in the paper is a separate
  lane in the official artifact, **explicitly excluded by project scope**.

Hence the original three scripts imply **184 direct QuPRS executions**
(\`37 * (Hybrid + WMC)\` positive, \`37 * (Hybrid + WMC)\` negative, and
\`36 * RR\` Feynman), with **37 derived positive RR result cells**:
**221 QuPRS result cells**, not 221 direct calls. Paper Table 2 displays only
36 positive rows; WState32 remains a separately labelled original-script
extra positive, not an invented Table 2 publication row.
The original positive script also invokes WState32 WMC-only, which the
provisional registry omitted.

The previous **187-row matrix** is retained *temporarily* as an immutable
exploratory-evidence index: 108 Table 2 IDs include 36 **independent**
RR-only runs (non-paper protocol), 74 Table 3 negative IDs, 1 extra
WState32 Hybrid ID, and only 4 Feynman RR sample IDs. This is neither
the paper's 184 direct calls nor the 221 output cells. Its provisional
\`remaining 109\` cohort must **not** be launched as the claimed complete
artifact reproduction. Do not discard its already archived results; label
independent RR-only output as **ADDITIONAL_METHOD_CONTROL**.

From existing GitHub Action logs, **78** distinct exploratory source-run
records exist: **74** Hybrid, **2** WMC-only and **2** RR-only.
One of the RR-only records is Table 2 GHZ32 (additional control, not
the published RR execution); the other is Feynman \`tof_3\`.
Thus **77 of the 184** canonical direct-call identities have execution
records (including scientifically censored outcomes); **107** still lack
original-script-matched execution records: **36** positive WMC,
**36** negative WMC, **35** Feynman RR. The positive 37 Hybrid records
cannot alone certify the 37 published RR result cells because the current
observer does **not** preserve \`pathsum_time\` or \`to_DIMACS_time\`.
Add those fields and replay the 37 positive Hybrid cases (with bounded
shards) before certifying the derived RR column. A censored timeout is
not an observed verdict.

Migration actions:
1. Separate **DIRECT_CALL**, **DERIVED_FROM_HYBRID** and **EXTRA_CONTROL**
   provenance in the registry and reports, without changing historical
   stored artifact IDs.
2. Build the full 36-Feynman list from the immutable v0.9.1 checkout;
   pin input bytes, and add WState32 positive WMC. Do not execute
   or gate on Feynver or other non-QuPRS results.
3. Make independent RR-only an opt-in *modern-method comparison*, never
   the historical RR-column oracle. Preserve stage outputs from the real
   original Hybrid invocation and re-derive RR exactly as the official script.
4. Only run the corrected remaining **107** direct-call identities and
   the bounded positive-Hybrid stage recapture after the lightweight source
   contract passes. Do not trigger expensive Solver workflows on every push.
5. Report outcomes, censored timeouts, source hashes and paper verdicts
   separately. Any formal *new* performance comparison remains CodSpeed-only.

This supersedes the older statements above claiming that 187 experimental
identities equal the complete original execution corpus. The previous
187-ID CI green gate remains a **schema/smoke** pass, not paper certification.
