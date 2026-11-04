# QOO-98 second scoped original-QuPRS source-CNF scientific admission

**No solver performance instrument**. Reuse immutable original prepared
weighted CNFs from QuPRS/QOO-157 scientific artifact `13317939531`;
compare *same Boolean clauses, positive/negative signed weights* for
`qaoa7_neq` and `qft16_eq` only. Source GPMC grammar
`c p weight L REAL IMAG 0` must be translated to pinned Ganak native
`c p weight L REAL+IMAGi 0` **without rounding or changing Decimal
components**. Original source SHA checked against the archived 38d report;
native Ganak output compared to archived GPMC 38d value only within
**one Ganak printed last-digit step per component**. This is a
`PRINT_CONCORDANT_UNCERTIFIED` scientific screen, NOT 38d or full
internal arithmetic error certification; on mismatch, stop and archive
evidence.

The native Ganak v2.8.0 binary must pass both official archive/executable
SHA and `--version` embedded commit checks. Only mode6, `--mpfrprec=127`,
two original source CNFs, 48s subprocess timeout/case, 10m entire CI.
No CodSpeed or comparison to d4 WallTime.

This tests a direct follow-up to the verified 10/10 tiny native mode6
formatted-count conformance ([Actions #41852483869](https://github.com/PhysicsQoo/QuPRS/actions/runs/41852483869)).
If it succeeds, a later **conditional** same-CNF solver-inclusive
CodSpeed can measure same requested 127 MPFR bits, but Ganak's **printed
9-digit resolution** remains disqualified as equal 38-digit *output*.
No upstream or QuPRS dev/main/regular CI edits.

## Completed original prepared QuPRS CNF semantic-count science gate — 2026-11-04

**[GitHub Actions #41854007964 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41854007964)**, measured SHA `f308852c79769211d76b5291134663837e7f9dd7`, immutable [artifact #13335303867](https://github.com/PhysicsQoo/QuPRS/actions/runs/41854007964/artifacts/13335303867). The official Ganak v2.8.0 archive/executable SHA and embedded `--version` commit passed again; `--mode=6 --mpfrprec=127`. Two QOO-157 **original prepared weighted** CNFs used with exactly unchanged source SHA and Boolean clause text; only GPMC `c p weight L REAL IMAG 0` was losslessly serialized as Ganak's `c p weight L REAL+IMAGi 0` preserving exact Decimal real/imag components and literal polarity. Inputs: QAOA7 NEQ **470 vars / 823 clauses / 638 signed literal weight records**; QFT16 EQ **486 vars / 1144 clauses / 800 signed weight records**. The native Ganak-converted CNFs and semantic source/converted SHA checks are in the artifact.

| Original source CNF | Native Ganak 127-bit Mode6 printed real and imag | Source archival GPMC38 exact printed reference | Per-component *output only* result |
| --- | --- | --- | --- |
| QAOA7 genuine NEQ | `-8.37717865e+22 + 1.13965484e+09i` | `-83771786496950192578442.633561488483115 + 1139654835.6944534730741909189788430012i` | **within 1 Ganak printed ULP** for real and imag |
| QFT16 EQ | `-3.43315056e+01 + -2.25179981e+15i` | `-34.331505647373494455571177193328751996 - 2251799813685247.9438082036909803239107i` | **within 1 Ganak printed ULP** for real and imag |

For QAOA7 the nominal Ganak last-place step is `1e14` for the very-large real component and `10` for the smaller imaginary component; for QFT16 steps are `1e-7` (real) and `1e7` (imag). Their respective numeric deltas from the archival GPMC38 reference are **within those printed steps**. This verifies *source-semantic syntax roundtrip + two original-CNF native Mode6 print screens*, not mathematically certified internal counting: the archival GPMC38 reference itself is an observation with no solver arithmetic error bound, Ganak output is rounded, and no exact large-CNF rational oracle was executed. Consequently all source-case statuses are **`PRINT_CONCORDANT_UNCERTIFIED`**, not scientifically equivalent at 38 output digits.

**Important implication:** Ganak Mode6 can indeed execute real QuPRS original weighted CNF semantics at **127 requested MPFR bits** and print components consistent within its documented **9-digit output resolution**; a blanket claim that Ganak lacks any correct complex WMC support is false. However this is not an equal-38-digit observable output comparison with GPMC/d4. QuPRS must maintain `NOT_COMPARABLE_FOR_38D_OUTPUT` until an approved, non-invasive high-resolution output pathway exists. **No three-solver CodSpeed was run**, and this science CI reports no time, even if GitHub actions wall time is visible.

See earlier tiny independent native [10/10 Mode6 output fixture gate](https://github.com/PhysicsQoo/QuPRS/actions/runs/41852483869). Next task QOO-98 may examine whether existing upstream diagnostic/API can provide ≥38 printed digits without modifying competition solver; otherwise stop three-way fair-output performance effort and keep current GPMC default. No QuPRS dev/main or solver source changes.
