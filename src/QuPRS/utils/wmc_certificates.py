"""Independently checkable *structural* certificates for exact discrete gates.

No floating solver output enters these proofs. Parameterized gates are
excluded because a certified exact source-angle domain is not yet wired
through both public backends. A circuit that needs path summation or
nontrivial phase equality beyond these sufficient conditions returns None.

This deliberately does not claim a certified WMC enclosure exists.
"""

_DISCRETE_GATES = frozenset({
    "h", "x", "y", "z", "s", "sdg", "t", "tdg",
    "cx", "cz", "swap", "ccx",
})


def certify_discrete_pathsum(circuit1, circuit2, pathsum, identity):
    """Return an exact structural verdict when sufficient evidence exists.

    A no-path Boolean ANF is a deterministic basis map; distinct output ANFs
    prove a different unitary (not even up to global phase). If the output
    map is the identity, an identical zero phase proves strict equality,
    while an input-independent constant phase proves global-phase equality.
    """
    if any(
        instruction.operation.name not in _DISCRETE_GATES
        for circuit in (circuit1, circuit2)
        for instruction in circuit.data
    ):
        return None
    if pathsum.pathvar:
        return None
    if pathsum.f != identity.f:
        return "not_equivalent"
    if pathsum.P == identity.P:
        return "equivalent"
    if not pathsum.P.free_symbols:
        return "equivalent*"
    # A nonconstant multilinear phase over exact Clifford/T source angles
    # witnesses a relative phase on the same deterministic basis map.
    # Each nonzero monomial is observable on some Boolean assignment.
    return "not_equivalent"
