# QOO-98 / QOO-157 — pinned Ganak 2.8.0 Mode 6 *internal bits* vs *printed output digits*

**Source-only audit, not a solver execution or CodSpeed experiment.** QuPRS
`dev/src/QuPRS/utils/ganak-release.txt` locks upstream Ganak commit
`b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281`, release v2.8.0,
and per-platform executable/archive SHA256. Its Python/Rust binary diagnostics
require matching executable hashes and embedded Ganak SHA in `--version`.
The pinned Linux/x86_64 distribution executable digest is
`934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd`.
Do not use unpinned system `ganak` for conformance or count/speed rankings.

## Pinned source findings

- [Ganak `src/main.cpp` lines 147–150](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L147-L150) sets `mpfr_precision=128` by default (requested **bits**, not decimal digits). [`--mode=6` and `--mpfrprec` CLI](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L182-L190) selects the complex MPFR field; [line 361](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L360-L361) registers the bits argument.
- [Lines 425–432](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L425-L432) **reject requested bits >256** and <2. Thus 512-bit mode6 attempts are *unsupported by pinned CLI*, not an admissible equal-bit test.
- [Lines 715–730](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L715-L730) instantiate `FGenMPFComplex(mpfr_precision)`; thus **127-bit request** is source-supported and nominally aligns with GPMC's 127-bit MPFR in QOO-157 P0. This alone is **not a native certificate of every semiring operation's working bits**, which requires actual binary execution and instrumentation-free numerical probes.
- **Critical output limitation**: [Mode6 lines 650–656](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L650-L656) emits `mpfr_printf("c s exact %s %.8Re + %.8Rei\\n", ...)`. Each component is printed in scientific notation with **8 digits after the decimal point, approximately 9 significant decimal digits**, **independent of `--mpfrprec`**. `ss << std::scientific << setprecision(40)` on [line 605](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L603-L606) does **not** control this separate `mpfr_printf` call. The literal output label `exact` is not a high-precision numerical error certificate.
- [Mode2 complex rationals lines 633–649](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L633-L649) additionally print `c s exact arb frac`; this can serve as a distinct exact-rational *oracle where supported*, **not** as a same-semiring performance substitute for Mode6.

## Consequences for QuPRS three-solver comparisons

**Source-falsified proposition:** Increasing pinned Ganak 2.8.0
`--mpfrprec` to 127, 128, or 256 bits does **not** produce 38-digit
Mode6 complex printed counts. Therefore, cannot put Ganak next to GPMC
MPFR127/d4 GMP128 as a solver with **equal 38-digit output resolution**
without rewriting upstream output (explicitly not approved).

**Narrowly viable conditional comparison:** request `--mpfrprec=127`,
confirm actual *pinned binary SHA* and exact same source weighted CNF/solver
path, and run numerical science fixtures with independent source
complex-rational or analytic oracle. Each printed Ganak real/imag part
must be handled as **9-digit-resolution evidence with an explicit decimal
rounding window**, not as a high-precision point estimate suitable for
`1e-12` or near-cancellation verdicts. For a `%.8Re` formatted value
`d.dddddddd × 10^e`, the nominal printed decimal *step* is
`10^(e-8)` for that component. The printed step is not a bound on
**internal arithmetic** error. If the independent oracle falls outside
a justified total numerical uncertainty bound, mark
`COUNT_OR_ARITHMETIC_DISAGREEMENT`. If the independent value is within
the *output-only* rounding interval but no internal arithmetic bound
exists, mark `PRINT_CONCORDANT_UNCERTIFIED`, not `FULL_38D_PASS`.
Do not infer acceptance of a projective-distance / cancellation boundary
from a coarse printed point estimate.

**Benchmark admission is separate:** Official CodSpeed solver-inclusive
WallTime can provide a **conditional same-workload performance observation**
if the same source CNF and verified solver execution, bits request, and
printed-limit caveat are recorded; it cannot be advertised as a same
**38-effective-output-digit** solver ranking. No blanket conclusion that
GPMC universally outperforms pinned Ganak is warranted by current runs.
QOO-98 owns any future native output/actual-precision conformance; QOO-157
owns GPMC/d4 mechanisms. Ganak is not a v0.14.0 release blocker.

## Bounded follow-up (not yet executed)

1. Run **one pinned native Linux x86_64 binary**, verify
   `ganak-release.txt` executable hash, `--version` embedded SHA and actual
   `--mode=6 --mpfrprec=127` acceptance.
2. Use fixed source-CNF SHA on 2–4 cheap fixtures including complex nonzero
   real/imag parts, negative sign, near-cancellation and a non-EQ case;
   compare against independent exact Fraction complex WMC or operator
   witness **with separate printed-resolution and arithmetic uncertainty
   evidence**.
3. Record whether a high-precision 38d **scientific count interface**
   exists without editing upstream. If not, mark native Ganak mode6
   `NOT_COMPARABLE_FOR_38D_OUTPUT`. Do **not** spend official three-way
   CodSpeed time pretending equality of output precision.
