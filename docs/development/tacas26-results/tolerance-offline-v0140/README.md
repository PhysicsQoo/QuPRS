# TACAS v0.9.1 to v0.14.0 binary equivalence tolerance replay

**PRIMARY GOAL: equivalent/equivalent* versus not_equivalent; the phase subtype is secondary.**
OFFLINE ORIGINAL PRINTED COUNTS ONLY; not a new v0.14 solver run.

101 cases with GPMC counts, including 45 historical positive
and 56 historical negative results.

Maximum positive distance estimate: {'id': 'table2:qpeinexact24:positive:hybrid', 'value': '1.377299540961785e-05'}
Minimum negative distance estimate: {'id': 'table3_negative:qaoa11:negative:hybrid', 'value': '0.2465671607550327'}
Candidate for reproduced binary historical WMC labels: 2e-5 distance (101/101).
This must not replace the modern public default 1e-8.

The old phase [0, 2pi) label convention is inconsistent with
modern signed atan2 wrapping for five near-zero negative phases.
One phase tolerance cannot reproduce all historical three-way labels; this is a SECONDARY label discrepancy.

## Primary binary result (phase tolerance = 1e-8 rad only for secondary label)

| Distance epsilon | binary equivalence reproduced | secondary exact label |
|---:|---:|---:|
| 1e-8 | 79/101 | 78/101 |
| 1e-7 | 90/101 | 88/101 |
| 1e-6 | 94/101 | 89/101 |
| 1e-5 | 98/101 | 93/101 |
| 1.4e-5 | 101/101 | 96/101 |
| 2e-5 | 101/101 | 96/101 |
| 1e-4 | 101/101 | 96/101 |
| 1e-3 | 101/101 | 96/101 |

## Evidence limits
Phase tolerance does not enter the WMC equivalent/not_equivalent test.
The binary historical-fit interval is [max original accepted distance, min original rejected distance).
It only applies to fixed historical printed GPMC values: RR reduction, CNF normalization,
solver precision and generated WMC values may change in a real v0.14.0 rerun.
Cases lacking printed WMC output (RR-only, timeout, watchdog) are NOT scored.
Do not change v0.14 default 1e-8 from these historical data alone.

Data: cases.csv, sweep.csv, report.json

Old classifier rounded log2(magnitude) to three decimals before
1e-10 comparison. The theoretical coarse rounded-log acceptance
boundary can reach about 0.0263 projective distance;
the observed printed original counts need only ~1.38e-5.
Separate tolerance scopes: RR chemistry cannot be reconstructed
from these printed GPMC values; original phase labels are
not an independent source-equivalence oracle.
