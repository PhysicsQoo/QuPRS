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


## Completed science result: original d4 residual clause identity

**SUCCESS**: [GitHub Actions #41841100007](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841100007), [artifact #13329836269](https://github.com/PhysicsQoo/QuPRS/actions/runs/41841100007/artifacts/13329836269), measured source SHA `05773452004962834f45c8084f5bfd915f82b1a3`. Pinned d4 scratch binary SHA256 `37e1a4678e73c6d8bd0673fa4acce0518a028870eaa6681251ddeeb767ae48ef`, GMP actual 128 bits (38 effective decimal digits). All source CNFs rechecked against original source hash and printed-complex WMC count screen; **12/12 source-WMC count screens passed**, no performance measurement in this workflow. Entire native residual files, corresponding raw byte hashes and separately canonicalized SHA256 reports remain in artifact.

| Original case | Residual identity group | Variants | Canonical clause multiset SHA prefix |
| --- | --- | --- | --- |
| QAOA7 NEQ | A | `auto_default`, `manual_sharp`, `auto_no_vivif`, `auto_no_probing` | `fe81c52fc2d54b` |
| QAOA7 NEQ | B | `auto_no_equiv_subst` | `2f7af04fb7afa8` |
| QAOA7 NEQ | C | `none` | `6c2a76a8d89929` |
| QFT16 EQ | A | `auto_default`, `manual_sharp`, `auto_no_vivif`, `auto_no_probing` | `c4ef1793d99daf` |
| QFT16 EQ | B | `auto_no_equiv_subst` | `64babdf1498cee` |
| QFT16 EQ | C | `none` | `57fb551e8ab044` |

Within **each case**, all six have identical literal-weight *text* SHA and identical projected-variable-set SHA. More strongly, all four group-A variants have **exactly the same raw residual dump SHA** (same clause ordering, weight lines and projection), not just the same canonical clause multiset. Group-B has the **same final dimension counts as A** but different actual Boolean clauses and a different raw dump. Group-C (no BiPe) is structurally larger.

**Mechanism inference with boundaries:** auto/default vs manual_sharp vs no-oracle-vivif vs no-probing produce exactly equal downstream native formula snapshots. Their different [within-d4 CodSpeed costs](D4_BIPE_OPTION_ABLATION.md) therefore cannot be attributed to the final exported clause multiset, literal-weight text, projection or clause order. This **supports** redundant native preprocessing work as a plausible explanation (not yet a stage CPU-cost certificate). Heap state, solver global state and hosted runner variance remain uncontrolled. `auto_no_equiv_subst` actually changes final clause content, so its QAOA7 slowdown may involve a different search problem and must **not** be attributed to preproc overhead alone.

**Decision:** Do not adjust production defaults. The next meaningful experiment isolates the auto-config changes (separate switches for BVA, oracle sparsif, fill limit, growth/resolvent caps), measures each **only with official CodSpeed** and a qualified same-device paired/ABBA design, uses sufficient max-time on QFT16 `none`, and checks exact residual fingerprints after each switch. An isolated internal timing trace must not replace CodSpeed ranking.
