# QOO-98 / QOO-157 — Conditional Ganak 2.8.0 vs GPMC: requested MPFR127

**Official CodSpeed v5 SUCCESS**: [Actions #41855074902](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855074902), [raw immutable artifact #13337246601](https://github.com/PhysicsQoo/QuPRS/actions/runs/41855074902/artifacts/13337246601), QuPRS code SHA `1f520105e6ba903672ce4e34543e11427acf071e`. 8/8 official subprocess-inclusive WallTime benchmarks PASS (4 circuits × two solvers); a *fresh* same-run 8/8 native complex printed-count preflight PASS before any timing. Same GitHub-hosted `ubuntu-24.04` runner and same prepared source CNF per circuit, pinned GPMC gitlink `a1bda3489e959d3695b6798d327c5a1fc1bed305`, pinned native official Ganak `release/v2.8.0` embedded SHA `b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281`.

**The scientifically defensible benchmark scope is conditional only.** Both solvers request **127 MPFR bits** (GPMC `-mode=1 -prec=38` ≈127 bits, Ganak `--mode=6 --mpfrprec=127`). GPMC prints 38 effective decimal digits; unchanged Ganak Mode6 emits **only 9 printed significant digits**. This is **not a same-38-digit OUTPUT precision ranking**, not a certification of either solver's internal arithmetic error bound, and does not validate near-cancellation verdict boundaries. Ganak inputs are the **same mathematical Boolean clauses and literal-weight values** in its required `REAL + ABS(IMAG)i` dialect; byte-identical weighted-DIMACS syntax would be invalid and scientifically inappropriate.

### Actual official CodSpeed — three rounds per identity, medians (milliseconds)

| Original weighted source CNF | GPMC127 median ms | Ganak127 median ms | Ganak/GPMC median ratio | Observed faster |
| --- | ---: | ---: | ---: | --- |
| Grover4 EQ | **55.483** | 285.044 | 5.138× | **GPMC** |
| QAOA7 genuine NEQ | **24.379** | 214.622 | 8.804× | **GPMC** |
| QPE exact8 EQ | **43.024** | 186.151 | 4.327× | **GPMC** |
| QFT16 EQ | 974.784 | **669.436** | 0.687× | **Ganak; about 31.3% lower elapsed** |

*Reproduced from artifact `ganak-gpmc-conditional-codspeed.json` `stats.median_ns`; each of the eight identities has three reported rounds.* Observed per-round min–max in milliseconds: Grover4 GPMC 44.182–58.223 / Ganak 283.072–287.624; QAOA7 GPMC 23.996–24.387 / Ganak 213.343–215.935; QPE exact8 GPMC 43.005–43.033 / Ganak 185.621–186.438; QFT16 GPMC 974.703–1009.816 / Ganak 666.802–673.422.

### Mechanism interpretation and limits

- **The claim 'GPMC is universally faster than Ganak' is disproved under this explicit conditional experimental setting** by the QFT16 counterexample. Three of four examples favor GPMC by factors 4.33–8.80, while QFT16 favors Ganak by a smaller factor ≈1.456 (GPMC/Ganak).
- The original GPMC, d4 and Ganak inputs for each circuit share the Boolean source and mathematically equal complex literal weights; **only the solver-specific serialization dialect differs**. Before CodSpeed, the original-source CNF SHA, immutable archived scientific report and pinned Ganak executable are rechecked on the actual runner.
- No solver source changed; the timing covers prepared-CNF child subprocess startup + parsing + native preprocessing + counting + stdout parsing, **not** QuPRS RR, QASM transpilation or the external SCC quotient calculation.
- GPMC printed **38d** and Ganak printed **9d**. Requested 127-bit working precision is only an internal bit request; comparable requested MPFR bits do not imply comparable published numerical accuracy or a valid equal-output-precision WMC race. Ganak's 9d output screen is `PRINT_CONCORDANT_UNCERTIFIED`, using native print half-ULP and historical 1e-12 scale on large inputs; the source reference is itself a solver observation, not an exact oracle.
- This was **one hosted run with three rounds**, not Macro Runner ABBA/BAAB or repeated cross-run significance testing. The Grover4 GPMC range 44.182–58.223 ms especially warrants paired replication before setting any time guard.
- No default solver migration, Ganak upstream change, broad survey or regular dev/main CI changes are justified.

### Mechanism-focused next science gates (no new performance claims)

1. **QFT16 inversion**: inspect pinned Ganak's `Arjun` preprocessing, `Puura`, tree decomposition, branch decisions, and component cache behavior versus GPMC. Record source-pinned *native operation counters* first. Do not claim that Ganak's 9d formatting makes search cheaper; output printing itself is not isolated.
2. **QAOA7/Grover4/QPE smaller-circuit overhead**: quantify parser/solver startup and native preprocessing versus actual search-work counters for both solvers; differentiate relative overhead from structural reduction. Existing GPMC VS×TD, BiPe stats and SCC results can be reused, not rerun in full.
3. **Precision boundary (QOO-98)**: without changing competition solver upstream, seek a credible native high-resolution complex output/error-bound interface; until then keep `NOT_COMPARABLE_FOR_38D_OUTPUT`. A potential conditional Macro Runner experiment is secondary and must retain the precision qualification.

The results must be summarized with the qualifiers **same requested MPFR bits** and **different final output resolution** together. Never silently present these ratios as the prior 38-decimal GPMC–d4 fairness comparison.
