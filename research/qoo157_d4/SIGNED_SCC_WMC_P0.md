# QOO-157 P0 — independent signed complex-weight binary-SCC quotient

**Science first; no benchmark unless the gate succeeds.** Source QuPRS
weighted DIMACS with `c p weight L REAL IMAG 0`, exact source SHA from
archived artifact `13317939531`, independent original binary-implication
SCC quotient. For signed equality (including negation), replace each source
variable with a signed representative. Multiply original *positive and negative*
complex literal weights into the corresponding representative truth weight.
All arithmetic performed in exact Fraction pairs; decimal export must be
finite and exact. Tautological source equivalence clauses disappear; every
source assignment satisfying binary equivalences has a unique reduced
assignment and vice versa. All singleton/free variables remain.

**Fail-closed** for unknown input metadata, contradictory binary SCCs,
unknown original CNF SHA, incomplete solver count output and failed exact
small truth-table checks. Synthetic exact oracle covers equal/negated, phases,
cancellation, weighted/unweighted, free variables, units and contradiction.
Large inputs are checked by original-vs-reduced count printed at nominal 38
effective decimal digits, GPMC MPFR 127 bits/d4 GMP actual 128 bits, using the
prior original archived GPMC38 reference and the 1e-12 count-scale screen.
That is an *observational consistency screen, not an internal arithmetic
error certificate*. No claim that signed representation is safe for a
different/projected WMC grammar outside the pinned QuPRS CNFs.

[Science workflow](../../.github/workflows/qoo157-signed-scc-reduction-science.yml)
builds original pinned GPMC and research-patched pinned d4. Four archived
source CNFs + four independently reduced CNFs are admitted only if 16
solver counts agree with the original GPMC38 within the prior scaling
screen. No timing; **official CodSpeed is the only source for performance**.
Reduced CNFs, exact signed mapping and scientific evidence are archived
for a subsequent same-CNF CodSpeed intervention. No dev/main/upstream edits.
