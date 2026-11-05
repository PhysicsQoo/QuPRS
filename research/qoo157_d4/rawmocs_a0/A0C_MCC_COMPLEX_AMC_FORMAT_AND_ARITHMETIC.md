# RaWMoCS A0c — MCC 2026 input/output and dual arithmetic research preflight

Date: 2026-11-05. Owner: QOO-173. Research-only, no new repo, no Rust implementation, no MCC submission or CodSpeed run.

## 1. Official evidence and scope

- [MCC 2026 tracks](https://mccompetition.org/2026/mc_description): Track 1 #SAT, Track 2B signed real WMC, Track 3 projected counting, Track 4 mixed projected weighted counting, experimental Track 5B field/complex Algebraic Model Counting. Ranking A exact (wrong answers excluded), C approximate guarantee and D heuristic have distinct reporting. Resources in the 2026 rules: 3600s/32 GB. Future MCC editions may alter these.
- [MCC data format v1.2, 2025-06-10](https://mccompetition.org/assets/files/mccomp_format_25.pdf), linked from 2026 rules: type line, weighted/projection details, AMC complex numeric grammar, SAT status and result outputs. The PDF was inspected visually on pages 6, 7 and 12.
- [MCC 2026 submission rules](https://mccompetition.org/2026/submission): top-level build.sh (no parameters) and run.sh (one CNF filename), target container, standardized stdout; 2026 submissions use **private GitHub repository** with organizer access. This is **only a future submission requirement**, not a reason to create a RaWMoCS repository during A0 research.

## 2. Complex AMC count is EXACT over finite rational component input (mathematical feasibility)

The competition AMC complex format accepts complex weights a+bi where a,b are finite decimals or fractions (normally with at most nine significant fractional digits as described in the 2025-format specification). Each component is exactly representable as a rational: arithmetic can be carried out in Q[i] with arbitrary-precision integer numerator/denominator. This offers a mathematical route to **exact** Track 5B results, although runtime/memory viability and all official edge cases remain untested.

QuPRS also needs complex exponentials of arbitrary source angles. Many are not in Q[i]: e.g. exp(i*pi/4) has sqrt(2) in its components; decimal-radian angles in general have no finite rational-complex representation. **Do not use one numeric kernel or one accuracy claim for both target workloads.**

Prospective arithmetic modes:
1. ExactGaussianRational: competition weight grammar (integer/fraction/finite decimal) -> exact rational complex, with exact +,*, no rounding. Optional dedicated optimized kernels for #SAT integer and real rational WMC. No premature f64.
2. MultiprecisionComplex: QuPRS source-phase prepared weights, adaptive GMP/MPFR/MPC or another numerical implementation, numeric provenance but no automatic source-exact error proof.
3. ValidatedIntervalComplex: deferred until output bounds and rounding are independently proven. Not equivalent to increasing decimal precision or printing more digits.

Optional special cyclotomic roots of unity may later permit exact calculations for restricted symbolic phase families, but **A1 does not require symbolic algebra** or correctness for arbitrary source angles.

## 3. 2025 format and 2026-track parser contract

From official data-format v1.2:
- Input DIMACS-like header: p cnf N M; N and declared free/unused variables are part of full-count semantics. Actual count must honor both weights or default unit weights for unweighted variables. Invalid header/literal/count must fail closed.
- Problem type comment: c t mc, wmc, pmc, pwmc or amc-complex; program must inspect and support or return explicit unsupported-format status, not silently interpret an AMC input as a real WMC problem.
- Complex literal format: c p weight L a+bi 0, or a-bi; both polarity weights are expected for weighted variables. Unspecified weights default 1+0i. Fractional components such as 1/3+2/5i should be kept as rational text, not rounded early.
- Projected input uses c p show V1 V2 ... 0. Track 4 input requires special attention to distinct projected semantics, especially weights on non-projection variables. The official 2025 format explicitly adds a warning for weights on non-projection vars, whereas our EPWMC oracle rejects such weights: adapt via a documented policy after actual current format conformance tests. Do not treat Ganak2 CAV25 projected class-weight sum as identical without mode-level evidence.
- The format permits negative/zero weights in 2025 updates; the complex subsection contains an imprecise or inherited real-domain condition like 0 <= w(l) despite complex numbers having no order. **Do not implement ordering of complex numbers or auto-reject negative imaginary/real components**; rely on actual typed complex examples and competition organizers' effective format clarification before final admission.
- New 2026 Track 2B negative weights and experimental Track 5B imply independent acceptance/error policy, not a single blanket "probability weight" mode.
- Comments can appear around clauses; typed count and contradictory/duplicate projection/weight declarations require deterministic parse policy; no undocumented fallthrough.

### Minimal A0c research parser examples (expected math; no parser implementation yet)

1. p cnf 1 0, type amc-complex, weights +1=1+0i, -1=-1+0i -> SAT, complex count exactly 0 (cancellation).
2. p cnf 1 0, type amc-complex, +1=0+0i, -1=1+0i -> SAT, count exactly 1, not UNSAT.
3. p cnf 1 1 with clause (x), +1=1/3+2/5i, -1=1+0i -> SAT, count exactly 1/3+2/5i.
4. p cnf 1 2 with both (x), (not x) -> UNSAT, count zero (different status from 1).
5. p cnf 2 1 with clause (x or y), positive weights x=2, y=3, negative=1 each -> SAT, count 11, not the SAT-only or pure-literal-rewrite count 8.
6. p cnf 2 1, type amc-complex, x free and (+x)=(1/2+1/4i), (-x)=(1/2-1/4i), y forced true with unit weight -> SAT, count exactly 1 (imaginary cancellation).

These are designed test vectors; they are NOT yet valid complete byte-for-byte MCC files or executed competition-format tests.

## 4. Output contract: SAT and complex WMC count are distinct evidence

The official format requires logical status line s SATISFIABLE|UNSATISFIABLE|UNKNOWN, typed count line c s type amc-complex, real and imaginary signed log10 estimates, and full numeric result c s SOLVERTYPE PRECISION NOTATION VALUE with complex textual format a+bi or a-bi (no interior spaces). The source's example uses c s exact double float 0.55-1.1i, but using such an example is **not itself a certification** that a floating implementation is mathematically exact. Actual ranking A requires correctness under the competition rules.

For exact complex zero due to cancellation, a solver must report SATISFIABLE when independently proven SAT; zero count is not an UNSAT certificate. For UNSAT, count zero with logical UNSAT. If logical status has not been established, do not infer from complex count; an independently checked SAT oracle may be needed even when counted value is zero. Handle separately zero real-part, zero imaginary-part and signed magnitude log10 lines; the 2025 format is less explicit about each zero-component edge case and should be confirmed with the organizers or an accepted reference parser prior to entering a competition.

The output must identify numeric type honestly (exact rational vs finite-precision point). No fabricated approximate PAC certificate or "exact" label based solely on GMP/MPFR working digits.

## 5. Later A1 implementation / science and runtime controls

- Keep parser separate from QuPRS proprietary/simple GPMC pair grammar and Ganak complex-i grammar. A new competition input adapter must parse the official complex text rather than assume the QuPRS c p weight x real imag 0 output.
- Separate boolean SAT proof/search from weighted count. Cache includes arithmetic and literal weights version; avoid zero-weight division in backtracking.
- First solver science oracle: [48 QuPRS/general rational complex cases](https://github.com/PhysicsQoo/QuPRS/tree/experiment/qoo157-d4-effective-digit-parity/research/qoo157_d4/rawmocs_a0), verified at exact rational reference level, plus future official MCC small text fixtures.
- Performance can only be claimed from **official CodSpeed** same-SHA pinned inputs/environment for QuPRS. MCC published walltime, benchmark solved counts and ranks are competition scores, not interchangeable with QuPRS CodSpeed measurements. Track A/C/D are distinct scientific acceptance paths.
- Scope remains documentation only. No new repo, no Rust code, no QuPRS main/dev/CI default changes.

## 6. Remaining items

Official current-year (future year if entered) format/rules must be revalidated; actual submission-specific parser and stdout conformance requires a runnable executable, hence **belongs to A1/R4 after a repo exists**. Current A0c closes the research-format design preflight and separates viable exact-rational AMC from QuPRS source-phase numerical WMC.
