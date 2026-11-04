# QOO-157 — Actual native preprocessing: GPMC weighted EE / d4 BiPe

**Independent source-pinned investigation.** This does *not* modify GPMC,
d4 upstream, QuPRS default solver or dev/main.

- Input: original archived QAOA7 NEQ and QFT16 EQ exact same source CNF SHA.
- GPMC: original pinned gitlink, `-mode=1 -prec=38 -vs=1 -td`;
  only `-pp_ee` vs `-no-pp_ee` changes. Native `[Init]`/`[Simp]`
  reports record actual pre/post variable, projected-variable and clause counts.
- d4: original pinned `be15f91`, research-only scratch patch to initialize
  GMP at 38d before input parsing, and an output-only `QOO157_BIPE`
  marker around original `runPreproc`. Compare default BiPe
  against `--preproc.auto-config=false --preproc.preproc-method=none`.
  Native markers record actual formula var count, **active** var count,
  clause count, protected-variable count and weight entries.
- Both solvers: complex WMC counts screened against archived GPMC38 exact
  rational *printed-value* reference; 38 **effective** decimal digits,
  GPMC 127 bits / d4 128 actual bits. This is not certified arithmetic
  error or quantum EQ/NEQ.
- Time: **official CodSpeed v5 WallTime only**, when each *within-solver*
  configuration pair meets numerical admission; censored pairs must not
  be ranked. These d4 binaries contain diagnostic stdout and must **not**
  be used for formal cross-solver speed ranking or shipped.
- Native preprocessor counters are not automatically comparable across
  GPMC and d4 because each performs distinct transformations, may use
  distinct variable renumbering and uses different projected semantics.
  Preserve both raw pre/post results, not a single aggregate 'percentage'.

Reproduction: [branch-scoped Actions workflow](../../.github/workflows/qoo157-preprocessing-compare.yml),
[science preflight](qoo157_preprocess_compare.py),
[research-only d4 instrument](d4_bipe_instrument.py),
[CodSpeed tests](test_codspeed_preprocessing_compare.py).

**Pending:** the workflow's actual CI/science results, peak RSS, GPMC
specific equivalent-literal merge counters, d4 BiPe exact elimination trace,
and Macro Runner ABBA. Ganak 2.8.0 mode6 cannot be added as a precision-fair
38-digit rank until QOO-98 confirms native working precision and print
resolution; this stage does not claim it is equivalent.


## Verified native results: CI #41837297080 (2026-11-04)

**PASS** [GitHub Actions #41837297080](https://github.com/PhysicsQoo/QuPRS/actions/runs/41837297080) at measured code SHA `18a673241685d796976d49175f64597f02acce4b` (the subsequently updated branch's documentation HEAD is not the measurement SHA). [Immutable archived artifact #13325439074](https://github.com/PhysicsQoo/QuPRS/actions/runs/41837297080/artifacts/13325439074). Python scientific preflight finished with status `SCIENTIFIC_PREFLIGHT_COMPLETED_WITH_CENSORING_POSSIBLE`, **but no case was censored**: QAOA7 and QFT16 both admit *GPMC and d4* 38-effective-decimal-digit, **8/8 source WMC count concordant**. The differences against the original exact-rational reported count are nonzero, remain under the 1e-12 scaled count screen, and are **not a proof of exact numeric arithmetic or equivalent verdict**. Source CNF SHA were checked against artifact `13317939531`.

Native executable SHA256: GPMC `b4169bce97c995accfca5ef2246d7283af0ded3370391dec7cd852eb3fcb67ce` (MPFR 127 bits), d4 scratch instrumented `69db327a1835dad0666cf2a7bbdc2ae7eeea6f9d34376bbd0dcbdd88d2d9b4d8` (GMP 128 bits). C++ instrumentation is output-only and retained as patch in the artifact; **not a source-level performance-neutrality certificate**.

### Actual before/after, native solver reports

| Case | Solver/config | Before: vars/active/clauses | After: vars/active/clauses | Protected variables |
| --- | --- | --- | --- | ---: |
| QAOA7 NEQ | GPMC weighted EE on | 470 / — / 822 | **316 / — / 516** | n/a |
| QAOA7 NEQ | GPMC weighted EE off | 470 / — / 822 | 469 / — / 822 | n/a |
| QAOA7 NEQ | d4 BiPe default | 470 / 470 / 823 | 470 / **470** / **677** | **319** |
| QAOA7 NEQ | d4 BiPe none | 470 / 470 / 823 | 470 / 470 / 823 | 319 |
| QFT16 EQ | GPMC weighted EE on | 486 / — / 1143 | **383 / — / 939** | n/a |
| QFT16 EQ | GPMC weighted EE off | 486 / — / 1143 | 485 / — / 1143 | n/a |
| QFT16 EQ | d4 BiPe default | 486 / 486 / 1144 | 486 / **486** / **1058** | **400** |
| QFT16 EQ | d4 BiPe none | 486 / 486 / 1144 | 486 / 486 / 1144 | 400 |

Here GPMC reports `pvars` as 470→316 and 486→383 when EE is enabled, and 470→469 and 486→485 with EE disabled. d4 reported unmodified `weight_entries`=638 (QAOA7) and 800 (QFT16) and no change to the projected-set count; these fields do not certify that all weight mappings or semantics are unchanged internally. GPMC `Init` native clauses 822/1143 differ from raw CNF headers 823/1144 due to upstream native import/cleanup; **do not compare raw-header-to-native-Simp as if it measures only EE**. GPMC emits FlowCutter markers for both EE variants of both cases.

Source-fixed GPMC difference on this run: `-pp_ee` causes an additional **153 net variables** to disappear in QAOA7 versus EE-off (316 versus 469), and **102** in QFT16 (383 versus 485). d4 BiPe default removes **146 clauses** in QAOA7 and **86 clauses** in QFT16 but leaves total/active vars unchanged; **being protected is not itself being uneliminated by this mechanism**.

### Official CodSpeed v5 WallTime (3-round medians)

| Case | Within-solver contrast | Default/on | Disabled/off | Net effect of enabling preprocessing |
| --- | --- | ---: | ---: | --- |
| QAOA7 | GPMC weighted EE | **22.900135 ms** | 22.627347 ms | **~1.2% slower** (within likely hosted-run variation) |
| QFT16 | GPMC weighted EE | **938.572147 ms** | 1317.302558 ms | **28.75% lower** |
| QAOA7 | d4 BiPe | **111.388821 ms** | 63.196449 ms | **76.26% slower**, despite fewer clauses |
| QFT16 | d4 BiPe | **1396.368619 ms** | 7661.493388 ms | **81.77% lower**, about **5.49×** |

**Critical interpretation:** measurements are complete prepared-CNF child-solver calls (process startup, native parse, preprocess, search, capture and parse); the net effect is NOT isolated time spent *inside* preprocessing. Since d4 has scratch-added `QOO157_BIPE` trace output, the figure **may only be compared across d4 configurations in this same run**, not used to certify its speed relative to unmodified GPMC. Similarly GPMC EE on/off is a controlled *within-GPMC* comparison. Hosted WallTime outside Macro Runner has known variability and this single three-round run remains `OBSERVATION_ONLY`. No unbounded CI workload, no default solver change, no dev/main modification.

### Implication and next experiment

The GPMC advantage mechanism is not simply “it preprocesses but d4 does not”: both actually preprocess. **GPMC EE reduces many weighted Boolean variables**, whereas **pinned d4 BiPe preserves all active vars but simplifies clauses** on these inputs. In QAOA7 the d4 preprocessing work may cost more than the search reduction; in QFT16 removing even 86 clauses is associated with a large reduction in complete solver WallTime. To attribute cause to specific BiPe operations, next record BiPe stage-level native counters/time and test disable/enable individual strategies with exact WMC admission; a manual stopwatch is not formal CodSpeed evidence.

**Ganak 2.8.0 mode6** is a conditional third axis only: current QOO-98 evidence states printed complex WMC is around nine effective decimal digits, so a 38d precision-fair three-solver comparison **is not yet scientifically admitted**. Don't silently score it against GPMC38/d4-38. No Ganak build or CodSpeed run was initiated in this experiment.
