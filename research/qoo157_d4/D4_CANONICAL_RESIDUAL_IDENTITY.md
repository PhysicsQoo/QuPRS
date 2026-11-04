# QOO-157 — native d4 residual CNF canonical identity study

A **science-only**, no-CodSpeed analysis to distinguish whether the six BiPe
option variants reported with identical residual variables/clauses actually
produce equal residual **clause multisets**, equal literal-weight text, and
equal projected-variable identities.

Compiles pinned d4 38-effective-digit scratch source, with the already approved
preparse GMP precision and pre/post metadata patches, and an extra **environment
gated** dump of formula after `runPreproc`. Dumps are made only for untimed
science check, never a CodSpeed-timed execution. No default solver changes.
Each of QAOA7 genuine NEQ and QFT16 EQ has six options already tested by
[CodSpeed #41839512753](https://github.com/PhysicsQoo/QuPRS/actions/runs/41839512753).
The study reuses exact original weighted CNF SHA and archived d4-38 complex count
scientific screen; no new QASM or RR.

Native dump records all Boolean clauses (including duplicates), all literal
weight strings, and projected variable list. Python sorts clauses and literals
to create canonical **clause-multiset SHA256**, separately hashes literal-weight
text and projection, and retains bytewise raw dumps as artifact evidence.
Clause hash equality is stronger than coincident dimensions but **does not**
by itself certify reweighted WMC semantics or numerical accuracy.

Results of this workflow must not be used as timing evidence; the existing
official CodSpeed option pilot is the only performance dataset.
