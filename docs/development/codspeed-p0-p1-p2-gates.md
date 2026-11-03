# P0/P1 concurrent experimental gate and P2 promotion decision

Status: experiment design, not release certification. Applied to QuPRS PR #131
against its exact current HEAD. Both workstreams are triggered on a single
PR `edited` event, with isolated jobs and NO new PR/worktree or automatic
migration of the legacy 32 Simulation IDs.

## P0 — QPE-inexact20 scientific source/verdict hold

Use two independent deterministic 20-qubit **statevector input probes**
(|0…0> and a nontrivial product state) with Qiskit qasm2 and source-pinned
original/transpiled/Random_Rotation circuits; report overlap and
global-phase-corrected residual without constructing a 2^20-by-2^20
unitary matrix. This screens source differences, **not a complete unitary
equivalence proof** and not a rigorous QuPRS projective-distance certificate.

Execute bounded QuPRS GPMC calls for Python/Rust x Hybrid/WMC-only x
transpiled/Random_Rotation. Record the printed/numerical verdict,
Solver invoked, RR approximation and precision warning per call. Keep P0
SCIENCE_HOLD if source/input-state probes disagree with positive expectation,
Python/Rust or method results disagree, or WMC computation is insufficiently
qualified. A printed magnitude warning alone does not override a meaningful
distance classifier; an unexpected verdict is not automatically waved away
as tolerance. Do not promote QPE-inexact20 positive in P1.

## P1 — five-round same SHA source-backed CodSpeed WallTime

Distinct experimental IDs for graphstate64 positive (RR ended), qaoa11
positive (GPMC called), qwalk4 positive (RR ended), qwalk4 negative (GPMC
called), and qpeinexact20 negative (GPMC called). The latter remains
science-conditional pending independent source oracle.

Each gets >=5 actual CodSpeed measured rounds and a complete per-invocation
scientific record, with 15s solver cap/24s watchdog and separate source
identity SHA per pair. Do not use Python wall-clock timing or independently
compare with the old paper's historical runtimes. Hosted non-Macro variance
means no formal performance certification after a single run. Timeout is
a censored failed observation, not a duration to include in a speedup.

## P2 — precise promotion and retirement gates

A candidate can enter **per PR** only after source hashes and source-oracle
status pass, backend/method/solver/direction and verified stage match intended
instrument, correct independent verdict including approximate/equivalent*
handling, 5+ rounds in >=2 independently scheduled CodSpeed runs under a
stable runner cohort, measured variance and CI cost/timeout envelope, and
comparable base/HEAD measurement semantics. Red E2E regressions cannot be
removed simply by dropping an old benchmark.

**Opt-in/nightly**: real science-qualified high-cost or high-variance cases
(QNN8 9.4s first pilot; negative QPE-inexact20 ~8s), numeric edge cases
and distinct Hybrid/WMC-only method comparisons. **Science HOLD**: QPE20
transpiled positive until source and solver classification reconciled.
**Manual stress**: historical >200s/timeout circuits including QFT24, QNN12,
Wstate16/32. **RR-only Simulation** must measure genuine algorithm CPU,
not solver-excluded host wrappers; only solver-inclusive CodSpeed WallTime
is primary end-to-end performance evidence.

The old 32 Simulation identities/five shards continue unchanged to at least
v0.17.0 and 90 days dual operation; earliest retirement v0.18.0 and only
after full benchmark replacement coverage and stable release baselines.
When semantic identity changes introduce a NEW URI and NEW baseline.
Archive the old suite's original sources/hash and v2 manifest reader.


## P0 tolerance sensitivity: required independent axes (2026-11-02)

A source-pinned Qiskit 20q statevector sample at parent SHA fcf5bfd
found nonzero relative-phase-corrected residuals:
- zero input: 4.237063348873223e-6;
- deterministic nontrivial product: 3.7867814364903053e-6.
This is neither an exact source-operator verdict nor the QuPRS projective
Hilbert-Schmidt distance. Both Python/Rust Hybrid reported not_equivalent
at default approximate_distance_tolerance=1e-8; WMC-only timed out with a
15-second subprocess limit. Do not automatically conclude a tool bug.

New opt-in diagnostic uses independent public API settings: sweep distance
tolerances 1e-9 .. 1e-5 (explicit QCEC comparator 2e-8);
hold RR default 1e-10 and GPMC MPFR 30 digits fixed for that lane;
separately compare rr_tolerance=0 and 1e-7, wmc_phase_tolerance=1e-6 and
MPFR 90 digits. GPMC 90 is a *diagnostic precision control*, not a proposal
to make all production solvers always use maximum precision. Only actual
solver returned verdicts and warning reasons can be used to infer a
printed-numerical threshold bracket; this is NOT a certified exact source
distance, and timeout entries remain censored. Never change the defaults
just to force a desired equivalent verdict. The phase tolerance determines
equivalent vs equivalent*, not the projective non-equivalence boundary.

The prior P1 five-round CodSpeed experiment DID capture 5 measured rounds
per case and stable stage/verdict for all 7 observed invocations; only the
standalone report script failed with ModuleNotFoundError due to Python
script sys.path. The report import is repaired without changing any original
CodSpeed measurements or re-running that five-round workload. Archive and
analyze its raw CodSpeed export separately until the fixed reporter is
tested via CI.
