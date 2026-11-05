# QOO-157 P7 — Canonical residual weighted-CNF/weight/projection/protected provenance

2026-11-05. **Science-only structural study; no new timing or solver-policy decision.**

## Why this is the next nonduplicated direction

[P6 warm-start 16/16 native science and 10/10 official CodSpeed](D4_WARMSTART_P6.md) is complete. It found identical component-search counters and only mixed ±1–2% hosted non-Macro timing differences, so repeating P6 is low priority.

The prior [BiPe six-option science + official CodSpeed comparison](D4_BIPE_OPTION_ABLATION.md) found QAOA7 default ~92.8 ms and manual sharp ~64.5 ms, while QFT16 no BiPe was far slower than auto, yet the **same residual number of clauses** was printed for several option variants. That counter does not prove an identical clause multiset, and matching effective decimal output alone does not identify how preprocessing changes search structure. This P7 tests the **content** without any official timing; original BiPe CodSpeed remains the sole timing evidence.

## Fixed provenance and instrumentation

- QuPRS isolated branch `experiment/qoo157-d4-effective-digit-parity`, upstream d4 `be15f91f3e9769e1f5cb175fa27e3eca3a1ea690` in a temporary scratch clone only. Same source-pinned `matched_precision_variant.py` (38 effective decimal digits / actual GMP 128 bits) and previously validated output-only `d4_bipe_instrument.py`. **Never modify d4 upstream, QuPRS dev/main, production solver configuration or routine CI.**
- Source input: exact original QAOA7 genuine NEQ and QFT16 EQ weighted CNF from [source science Actions #41822549728](https://github.com/PhysicsQoo/QuPRS/actions/runs/41822549728); verify each original byte SHA256 from archived `matched-science-report.json`. Compare all six previously verified BiPe option configurations on each circuit (2×6=12).
- Environment-gated `QOO157_RESIDUAL_DUMP` **only during native science subprocess** captures post-BiPe, pre-DPLL internal `formula.clauses` with all signed literals (including duplicate clauses), `formula.weightMap` literal-to-text weight entries, the `projected` set and `varProtected` set from `runPreproc`. Environment unset outside this experiment; no CodSpeed.
- Canonicalization sorts literals *within each clause* and sorts clauses while retaining duplicates, producing an exact literal-id-based **multiset SHA256**. Other independent SHA256 digests represent source-preserved weight strings, effective projection, protected-variable set and a combined source-variable-identity fingerprint. Numeric 38-digit source WMC must match archived rational count under the fixed earlier `COUNT_CONCORDANT_UNCERTIFIED` screen; neither this digest nor the screen proves strict arithmetic error bounds or cross-solver equivalence.
- For each same-input option pair record **separately** same variable/clauses dimensions, same canonical clause content, weight strings, projection and protected set. Same counts but different contents is the key gap identified by earlier work. Literal identifiers are not canonicalized modulo variable-renaming: **different SHA does not automatically imply nonequivalent Boolean function**.
- Preserve all twelve raw dumps + scratch C++ patch, binary SHA, runner HEAD, source CNF hashes and science report as immutable Actions artifact. An error/time limit/failed source provenance is not a PASS, and no runtime speed claim may be inferred from a native hash.

## Run and admission

[P7 source-control refinement commit `6f1c7093`](https://github.com/PhysicsQoo/QuPRS/commit/6f1c7093c766424fb1b1fb6352f20bc89074d150), [dedicated science Actions #41942959399](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942959399). Existing workflow: [`qoo157-d4-canonical-residual.yml`](../../.github/workflows/qoo157-d4-canonical-residual.yml), [scratch patch source](d4_residual_dump_patch.py), [native science analysis](qoo157_d4_residual_identity.py).

The complete immutable result is documented below. A material different residual content/hash with distinct within-d4 native search work suggests a **future** controlled interpretation of BiPe’s benefit, *not* a justification for another full six-option CodSpeed run. For actual algorithmic attribution, the next gate is to capture source-identifiable BiPe transformations (SCC equivalence, vivification, BVA) and verify the transformed weighted formula still counts the same. GPMC remains QuPRS recommended solver; d4 stays research-only pending standalone scientific/conformance and official CodSpeed basis.

Track under existing [Linear QOO-157](https://linear.app/qoogohome/issue/QOO-157), not a new duplicate issue. Ganak arithmetic qualification is owned separately by QOO-98.



## 12/12 independent extended provenance audit — verified

**PASS:** [Actions #41942959399](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942959399), measured experiment SHA `6f1c7093c766424fb1b1fb6352f20bc89074d150`; [raw science artifact `13378235343`](https://github.com/PhysicsQoo/QuPRS/actions/runs/41942959399/artifacts/13378235343) includes **all 12 raw residual dumps**, source-only C++ patch, native trace JSON, binary SHA and original SHA references. d4 scratch executable SHA256 `2e9869853dcc2432be62fecb2421ee1a3c6b19e7d34b0d9ad67a17adb280ad7b`. All **12/12** exact source-byte original CNF controls and complex WMC `COUNT_CONCORDANT_UNCERTIFIED` gate PASS. Numeric output across variants is **concordant, not necessarily bitwise identical**: some QAOA imaginary components vary in late digits, and QFT real components differ by ~3.65e−25 at the source-count screen scale.

**Do not classify this as the first canonical residual audit.** The earlier [Actions #41841100007, artifact #13329836269](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841100007) already demonstrated native residual clause/byte identity. [BiPe native stage stats #41847739344, artifact #13331518772](https://github.com/PhysicsQoo/QuPRS/actions/runs/41847739344) already pinned BiPe v1.0.0 and measured equivalence-gate / degree-work evidence. **P7's distinct new contribution is independent revalidation plus synchronized protected-variable/projection/weight-string SHA256 and explicit option-pair comparisons**, not a novel discovery of SCC substitution.

### Actual raw and canonical results

| Option | QAOA7 post-BiPe clauses | QFT16 clauses | Canonical *and raw-order* residual vs default |
| --- | ---: | ---: | --- |
| `auto_default` | 677 | 1058 | baseline |
| `manual_sharp` | 677 | 1058 | **exactly identical** |
| `auto_no_vivif` | 677 | 1058 | **exactly identical** |
| `auto_no_probing` | 677 | 1058 | **exactly identical** |
| `auto_no_equiv_subst` | 677 | 1058 | **different despite identical dimensions** |
| `none` | 823 | 1144 | different |

For `auto_no_equiv_subst`, a multiset symmetric comparison to default shows **QAOA7 166 removed + 166 new clauses**, and **QFT16 350 removed + 350 new clauses**, preserving the respective 677 and 1058 cardinalities. All six variants **within each circuit** share the exact same SHA for *literal-weight string map*, *projected variable list* and *protected-variable list*. No variable relabeling normalization was attempted, so a changed literal-id-based SHA is not evidence of non-equivalence by itself; WMC outputs are numerically concordant under the screened tolerance.

Full baseline clause SHA256:
- QAOA7 default: `fe81c52fc2d54b89b74c67c14bf3cdba9bbe334a8c529e7a918395a10299402f`; no equivalence substitution: `2f7af04fb7afa86e6160a872c0ddf779dbd40dddae21a7eaf4581a1c095b3d57`.
- QFT16 default: `c4ef1793d99daf4a923d0fdfe66debb05a080495be95a6fbe621137537f94bc7`; no equivalence substitution: `64babdf1498cee90cd7e97c482a728f61173ed03bdd74866773edee7b5560312`.

**Prior native BiPe statistics (already archived, NOT a new P7 experiment):** pinned BiPe v1.0.0 showed **146 QAOA7 equivalence gates and 86 QFT16 gates remain when `equiv-subst=false`**, while other four enabled modes substitute before gate counters. Its **degeneracy-based treewidth proxy** was QAOA7 **2→2** (little structural benefit) and QFT16 **11→8** (plausible benefit); this is not exact treewidth and not a stage-time measurement.

**Meaning for previous official CodSpeed:** [six-option official hosted CodSpeed #41839512753](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839512753) had QAOA7 median `auto_default=92.775650 ms`, `manual_sharp=64.499798 ms` (−30.48%), `auto_no_vivif=82.069987 ms` (−11.54%), `auto_no_probing=90.345407 ms` (−2.62%), despite raw post-BiPe residuals being **byte-for-byte identical**. This **narrows the plausible causes** to option-dependent preprocessing work, cost not represented by the canonical dump, or hosted measurement noise — **not a changed residual clause multiset in these four variants**. This observation does **not** isolate a particular BiPe stage's CPU or prove stable ≥30% improvement, as hosted CodSpeed itself is not fixed Macro Runner ABBA and the native stage t_total was intentionally excluded.

## Decision / next useful study

No new official CodSpeed was run for P7: hashes and standalone native counters are science, not performance instruments. For a material shipping decision, measure **preprocessor-including vs preprocessor-only** within the **same source-pinned d4 scratch binary** under **official CodSpeed**, narrowly on QAOA7 default/manual_sharp/no_vivif, with exact post-preproc raw and weighted fingerprints. This must be an independently timed stage-specific *counterfactual*; it may distinguish preprocessing overhead from solver cost if post-BiPe formula and downstream configuration truly match. Do not repeat all six options or compare absolute WallTime across different hosted runs. Macro Runner paired ABBA remains the gate for a production-level percent-regression claim.

No d4 upstream, QuPRS dev/main, solver default or routine CI changed. Continue in existing QOO-157, not a new Linear issue.