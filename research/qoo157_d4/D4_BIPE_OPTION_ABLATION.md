# QOO-157 — pinned d4 BiPe option-level ablation (next bounded pilot)

The **previous** [GPMC-vs-d4 preprocessing result](ACTUAL_PREPROCESSING_COMPARISON.md)
found QAOA7 BiPe on slower than off, QFT16 BiPe on much faster than off.
This pilot probes candidate causes without editing native solver algorithms.

Pinned d4 upstream `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`;
same research-only GMP 38-decimal patch, **actual 128 GMP bits**, and identical
`QOO157_BIPE` diagnostic stdout for all variants. Exact source-CNF SHA and
archived original d4-38 complex count are checked before any CodSpeed.

Two original circuits × six d4 option groups:
- `auto_default`: original auto-config enabled, sharp-equiv, density-driven presets.
- `none`: auto-config disabled and preproc-method=none.
- `manual_sharp`: auto-config disabled but sharp-equiv retained. **Bundle
  comparison** against default, not a single-rule isolation.
- `auto_no_equiv_subst`: disable SCC/binary-equivalence substitution.
- `auto_no_vivif`: disable SAT oracle vivification within elimination loop.
- `auto_no_probing`: disable failed-literal probing.

The last three are single-switch comparisons against the default; auto-config
might still override some nested options, so record actual native outcomes
and treat an identical before/after structure as an unproven activation rather
than proof the option was irrelevant. All variants share the exact same binary.
Record actual native **before/after active vars, clauses, protected vars,
projected set**, and full complex printed count for each case.

Scientific screen: same original archive d4-38 count and 1e-12 count-scale
criterion, **COUNT_CONCORDANT_UNCERTIFIED** only; timeout/error/count mismatch
is censored, never a speedup. Mandatory baseline and no-BiPe controls.
Performance: official CodSpeed v5 full subprocess inclusive, 3 rounds,
**within-d4 only**. The output-only debug counters are held constant across
all variants, but do not certify absolute cross-solver timing neutrality.
GitHub hosted runner WallTime is observational until Macro Runner ABBA.

**Ganak** is not included in this equal-38-effective-digit experiment because
pinned Ganak 2.8.0 mode6's printed WMC is not demonstrated to have 38 digits;
QOO-98 remains the precision qualification owner. No dev/main/default change.


## Confirmed experiment: same-source 12-variant CodSpeed and native residual dimensions

**Status SUCCESS** — [GitHub Actions #41839512753](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839512753), [raw science and official CodSpeed artifact #13326829794](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839512753/artifacts/13326829794), measured HEAD `261e365bf3dee1bea5530b102018e2cad8f3263e`. **12/12 scientific print-count screens passed** against archived d4-38 exact-rational printed count; **12/12 official CodSpeed v5 WallTime measurements completed**, no censored variants. Exact original source CNF SHA verified. d4 research executable SHA256 `c4ffd2befbab061a4c30eb4b269abdbbe82405f8e34b0011e32488b3a38dda65`, upstream `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690`, actual GMP 128 bits (38 effective decimal digits). Every test uses the same scratch diagnostic binary and exact source CNF.

**Official CodSpeed raw three-round medians (milliseconds), *within the one d4 run***:

| Config | QAOA7 genuine NEQ | QAOA7 vs default | QFT16 EQ | QFT16 vs default |
| --- | ---: | ---: | ---: | ---: |
| `auto_default` | **92.775650** | — | **1134.517316** | — |
| `none` | **56.476381** | −39.13% | 6121.688328 | +439.59% |
| `manual_sharp` | 64.499798 | **−30.48%** | 1058.052259 | **−6.74%** |
| `auto_no_equiv_subst` | 121.481484 | **+30.94%** | 1120.806382 | −1.21% |
| `auto_no_vivif` | 82.069987 | **−11.54%** | 1115.406182 | −1.68% |
| `auto_no_probing` | 90.345407 | −2.62% | 1125.281566 | −0.81% |

All WMC values concordant under the *screen* only; arithmetic error bounds **NOT_CERTIFIED**. Every source trace has the **same final dimensions within each circuit**, independent of option flags: QAOA7 **470 vars, 470 active vars, 677 clauses**, except `none` **823** clauses; QFT16 **486 vars, 486 active vars, 1058 clauses**, except `none` **1144** clauses. Protected source variables are **319** and **400** throughout. **Identical counts of variables/clauses do not prove identical residual Boolean clauses, literal mapping, source weights, or equivalent search states**: canonical residual CNF hashing remains required.

**Source-provenance constraint**: pinned d4 `--preproc.auto-config=true` uses a **density-dependent preset**; the native help specifies threshold `auto-config-ratio=7`. Original QAOA7 **823/470 ≈1.751** and QFT16 **1144/486 ≈2.354** both select the **sparse Arjun-like** side of the threshold, so their opposite performance direction is **NOT caused by selecting sparse on one and dense on the other**. The `manual_sharp` toggle disables auto-config and thereby may alter **multiple** eliminator options at once (BVA, fill limits, sparsification, resolvent caps / growth); its −30.48% QAOA observation is **not** a single-rule causal effect. `auto_no_equiv_subst`, `auto_no_vivif`, `auto_no_probing` are one-option source toggles, but their **runtime activation / stage-level hit counts are not yet certified**.

**Measurement integrity**: CodSpeed recorded `rounds=3` for every row, but the QFT16 `none` per-measurement duration **6.122 s exceeds `--codspeed-max-time=5`**; its exported min, median and max are identical. This may indicate effective sampling saturation. **Do not overstate sample independence or use the 5.40× QFT no/auto comparison as a formal statistical gate** without rerunning a scoped CodSpeed sample with a sufficiently large `--codspeed-max-time`, fixed Macro Runner and paired order. Other short per-row single-run percentage differences (especially QFT16 −1% to −7%) also need paired repeated verification. The large QAOA manual/default gap is a candidate for more robust testing, not a proven upstream optimization.

**Scientific interpretation**: QAOA7's auto-default BiPe **reduces 146 clauses** yet still runs slower than no-preprocessing; switching to manual sharp-equiv or removing oracle vivification reduces net walltime while maintaining the same final *dimension counts*. QFT16's BiPe **reduces 86 clauses** yet clearly avoids the long search of `none`; this supports preprocessing as workload-dependent, not inherently beneficial or harmful. Direct BiPe stage CPU attribution is still unavailable; **CodSpeed is the only performance ranking source**.

**Next conformance question**: capture the **canonicalized residual clause multiset SHA** (and, independently, literal-weight/projection provenance) from each option without inserting diagnostic operations into CodSpeed-timed execution. Distinguish two cases: different residual CNF content with same dimensions, versus actual identical residual CNF but different preprocessing effort. After the residual content is known, a targeted, same-binary CodSpeed ABBA pilot may test `auto_default`, `manual_sharp`, `auto_no_vivif`, and `none` only, with QFT16 maximum-time and RSS controls. No default change pending this evidence.
