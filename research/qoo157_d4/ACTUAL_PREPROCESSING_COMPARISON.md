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
