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
