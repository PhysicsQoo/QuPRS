# Nonzero decimal QASM angle safety

The native strict OpenQASM2 reader uses a bounded rational approximation to
represent angles internally. Some nonzero decimal-radian inputs, including
`1e-12`, can be rounded to zero by that representation **before** any
PathSum reduction or weighted model counting. Treating the zero approximation
as an identity rotation could give an unsound equivalence decision.

The source parser now rejects an explicitly nonzero angle if conversion into
the existing rational representation would yield zero. An underflowing
nonzero decimal token is rejected before it is treated as numeric zero.
Non-finite angle expressions are rejected as well. Zero inputs and currently
representable angles continue through the original code path.

This is *fail-closed hardening*, not arbitrary-precision decimal support:
a nonzero angle that is represented as a nonzero rational is still an
approximation, not an exact decimal-radian certificate. No numeric WMC
tolerance, selected solver, reduction order, or public result status is
changed. Exact decimal source semantics and original Qiskit-transpiled circuit
intent remain separate research questions. Do not classify a parse error as
proof of circuit inequivalence, and do not change original Python benchmarks
to require literal decimal equality.
