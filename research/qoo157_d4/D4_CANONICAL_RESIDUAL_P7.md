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

Results and any diagnostics/censorship are to be documented once the CI job finishes. A material different residual content/hash with distinct within-d4 native search work suggests a **future** controlled interpretation of BiPe’s benefit, *not* a justification for another full six-option CodSpeed run. For actual algorithmic attribution, the next gate is to capture source-identifiable BiPe transformations (SCC equivalence, vivification, BVA) and verify the transformed weighted formula still counts the same. GPMC remains QuPRS recommended solver; d4 stays research-only pending standalone scientific/conformance and official CodSpeed basis.

Track under existing [Linear QOO-157](https://linear.app/qoogohome/issue/QOO-157), not a new duplicate issue. Ganak arithmetic qualification is owned separately by QOO-98.
