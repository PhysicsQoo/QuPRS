# QOO-98 — native release binary: Ganak 2.8.0 Mode6 output precision qualification

Separate independent branch `experiment/qoo98-ganak-mode6-print-science`
based on QuPRS `dev`, **no upstream solver edits**, no CodSpeed.
Pinned release artifact is official
[meelgroup/ganak v2.8.0](https://github.com/meelgroup/ganak/releases/tag/release%2Fv2.8.0);
verify **both** archived tarball SHA256 and actual Linux/x86_64 executable
SHA256 from `src/QuPRS/utils/ganak-release.txt`, and require
`--version` embedded SHA `b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281`.

Five small weighted CNF fixtures (including upstream's own mode6 example,
signed complex weight, negative imaginary component, near-cancellation,
and exact zero cancellation) are run in the **actual unmodified pinned native
binary** with `--mode=6 --mpfrprec=127` and `256`. Exact reference
values are independent decimal/rational values; verify each printed real/imag
is exactly eight fractional digits in scientific notation and the original
reference falls within **one printed decimal step**. This is **only an output
resolution screen**, not an MPFR internal arithmetic error bound.
Check `--mpfrprec=512` is rejected by the pinned CLI as expected.

Subtle semantics: with satisfying assignments but **zero total complex
weighted count due cancellation**, upstream main.cpp emits the textual
`s UNSATISFIABLE` when its count is zero. A QuPRS WMC integration must
parse the numeric count and independently distinguish a zero weighted sum
from Boolean UNSAT; do not treat the SAT text as a sound equivalence verdict.

Ganak native weight syntax is `c p weight L REAL+IMAGi 0`; GPMC/d4 use
another representation. A future *fair same CNF* study must preserve the
**same Boolean clause multiset and exact signed literal weights**, while
using verified solver-specific weight serialization. A byte-identical
weighted DIMACS file cannot be assumed to be accepted by all three solvers.
QuPRS `WmcProblem.serialize` presently supports canonical PathSum weights
with negative literal weight 1; it is not by itself a generic serializer for
all arbitrarily signed-weight reduced SCC CNFs.

**No formal 38-digit three-way verdict/performance claim** is possible
from Ganak mode6's hard-coded nine-digit complex stdout. A conditional
fixed requested-bits and same semantic weighted-CNF official CodSpeed may
be considered after scientific admission, but cannot be represented as
equal 38-digit *output* precision. Keep QOO-98 In Progress, nonblocking
v0.14; original GPMC remains default. Use native source and artifact for
provenance; no release CI change.

## Completed pinned-native Ganak 2.8.0 science outcome — 2026-11-04

**[GitHub Actions #41852483869 SUCCESS](https://github.com/PhysicsQoo/QuPRS/actions/runs/41852483869)**, HEAD `fc9210a9011782ae8e20a8c5efb7814a4cd4fe7a`; [immutable artifact #13334339155](https://github.com/PhysicsQoo/QuPRS/actions/runs/41852483869/artifacts/13334339155) includes `native-mode6-print-science.json`, all 5 exact small weighted CNFs, executable digest, commit and limitations. Official upstream `release/v2.8.0` archive SHA `bea7150787a1e8f2b1bd658cb5a3c227d631d25054f5ff77ce23422e1c8b040c` and extracted executable SHA `934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd` were both verified. `--version` embedded `b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281` was accepted.

**10/10** native Mode6 `--mpfrprec=127` and `256` numeric printed-complex checks passed against independently specified exact-decimal/rational small-fixture references **within one printed last-place step per component**. The actual native output is `quadruple float` for 127 and `octuple float` for 256; each real and imaginary component is formatted with precisely **8 digits after the scientific-notation decimal point (~9 significant digits)**. **512-bit request is rejected** with native exit code 1 and `mpfr precision must not be more than 256 bits`. No native internal MPFR arithmetic uncertainty certificate or 38-digit output precision established.

| Independent small fixture | Expected exact complex WMC | 127-bit native printed complex WMC | 256-bit native printed complex WMC |
| --- | --- | --- | --- |
| upstream 2-variable | `1.5+1i` | `1.50000000e+00 + 1.00000000e+00i` | same 9-digit values |
| signed real and imag | `-1.23456789012345 + 0.123456789012345i` | `-1.23456789e+00 + 1.23456789e-01i` | same |
| negative imaginary | `0.87654321098765 - 0.12345678901234i` | `8.76543211e-01 + -1.23456789e-01i` | same |
| near-cancellation | `1e-22 + 2e-22i` | `1.00000000e-22 + 2.00000000e-22i` | same |
| exact cancellation | `0+0i` | `0.00000000e+00 + 0.00000000e+00i` | same |

**Critical exact-zero discovery, verified in the native binary, not merely source:** The final exact-cancellation fixture is a **Boolean SAT** source CNF (one variable, zero clauses), with opposing literal weights `1+0i` and `-1+0i`; its WMC is precisely `0+0i`. Ganak 2.8.0 **prints `s UNSATISFIABLE`** for both 127-bit and 256-bit runs, solely because its [main.cpp L601–602](https://github.com/meelgroup/ganak/blob/b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281/src/main.cpp#L601-L602) uses the *count-zero predicate* to select the textual SAT label. Thus **the label cannot be used as Boolean satisfiability evidence or as a QuPRS EQ/NEQ verdict** on signed/complex WMC, even though the numeric `0+0i` is a valid cancellation result. Need audit QuPRS adapters to ensure numeric-first handling and appropriate precision warnings.

**Precise conclusion:** Real Mode6 native executions support the source-observed 9-digit printed resolution bottleneck and accept a 127-bit requested internal precision, yet leave all-operation effective internal precision **UNCERTIFIED**. The 9-digit printed format is a *relative-digit restriction*, not a universal 1e-8 absolute floor: the nonzero 1e-22 result prints with nominal ~1e-30 last-place step, but without a certified error bound. Do not apply the 1e-12 screened d4/GPMC count equivalence threshold to Ganak's rounded point estimate. Any conditional CodSpeed is only a **same Boolean clauses + exact mathematical weights, solver-native serialization** workload comparison with output-resolution caveat; no formal 38-output-digit three-way ranking or default solver change.
