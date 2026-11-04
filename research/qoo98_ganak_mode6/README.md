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
