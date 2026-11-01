"""RR → Hybrid → WMC: original-source distance parity at a numeric boundary.

Compare a high-precision analytic source-unitary oracle with strict RR,
WMC-only, and Hybrid configured with positive RR tolerance on the same QASM.
An inconclusive approximate RR proof must never alter the source-faithful
strict-RR residual passed to WMC. The two opposing distance-boundary
cases must match the original source oracle on both Python and Rust.
"""
import json

from mpmath import mp
import pytest

from QuPRS import check_equivalence


_ID = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
_EPS = 1e-8
_RR = 1e-10


def _source(a: str, b: str):
    # H H = I.  Put the tiny angle before the HH pair because both
    # Python and Rust reduce at an H gate, before the larger rotation.
    return (
        _ID + f"rz({a}) q[0];\n"
        + "h q[0];\nh q[0];\n"
        + f"rz({b}) q[0];\n"
    )


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize(
    "a,b,expected_exact",
    [
        ("0.0000000004", "0.0000000198", "not_equivalent"),
        ("-0.0000000004", "0.0000000202", "equivalent"),
    ],
    ids=["source-above-residual-below", "source-below-residual-above"],
)
def test_partial_rr_near_wmc_distance_threshold(
    backend, a, b, expected_exact, record_property
):
    with mp.workdps(85):
        theta = mp.mpf(a) + mp.mpf(b)
        source_distance = abs(mp.sin(theta / 2))
        residual_distance = abs(mp.sin(mp.mpf(b) / 2))
        epsilon = mp.mpf("1e-8")
        assert (
            ("equivalent" if source_distance < epsilon else "not_equivalent")
            == expected_exact
        ), "Independent source-unitary oracle is incorrectly set up"
        assert (source_distance < epsilon) != (residual_distance < epsilon), (
            "Reference fixture must straddle the actual distance threshold"
        )
        source_distance_string = mp.nstr(source_distance, 24)
        residual_distance_string = mp.nstr(residual_distance, 24)

    base_kwargs = {
        "backend": backend, "strategy": "Naive",
        "tool_name": "gpmc", "timeout": 45,
        "approximate_distance_tolerance": _EPS,
        "gpmc_precision_digits": 30,
    }
    source = _source(a, b)
    strict = check_equivalence(
        _ID, source, method="hybrid", rr_tolerance=0, **base_kwargs
    )
    reference = check_equivalence(
        _ID, source, method="wmc_only", rr_tolerance=_RR, **base_kwargs
    )
    rr_only = check_equivalence(
        _ID, source, method="reduction_rules", rr_tolerance=_RR, **base_kwargs
    )
    # The rejected approximate RR probe must not contaminate WMC input.
    # No source-to-residual distance warning is needed for an exact WMC
    # residual, since source-level distance is preserved by strict RR.
    import warnings
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always", RuntimeWarning)
        tolerant = check_equivalence(
            _ID, source, method="hybrid", rr_tolerance=_RR, **base_kwargs
        )
    assert not any(
        "RR-approximated residual PathSum" in str(w.message)
        for w in observed
    )
    evidence = {
        "backend": backend, "tiny_angle": a, "large_angle": b,
        "exact_source_distance": source_distance_string,
        "nominal_residual_distance": residual_distance_string,
        "source_oracle": expected_exact,
        "strict_hybrid": strict.equivalent,
        "wmc_only": reference.equivalent,
        "rr_only": rr_only.equivalent,
        "tolerant_hybrid": tolerant.equivalent,
        "tolerant_solver_called": bool(tolerant.wmc_solver_invoked),
        "tolerant_result_matches_source_oracle":
            tolerant.equivalent == expected_exact,
    }
    print("RR_WMC_SOURCE_BOUNDARY " + json.dumps(evidence, sort_keys=True))
    for name, value in evidence.items():
        record_property("rrwmc_" + name, str(value))

    # First establish that the real solver can classify the original
    # source operator with the requested distance tolerance.
    assert strict.equivalent == expected_exact, evidence
    assert reference.equivalent == expected_exact, evidence
    assert strict.wmc_solver_invoked is True, evidence
    assert reference.wmc_solver_invoked is True, evidence

    # RR deliberately leaves the larger rotation unresolved. Hybrid's
    # WMC path must use the source-faithful strictly reduced residual
    # if tolerant reduction discarded a small but nonzero source angle.
    assert rr_only.equivalent == "not_equivalent", evidence
    assert not rr_only.wmc_solver_invoked, evidence
    assert tolerant.wmc_solver_invoked is True, evidence
    assert tolerant.final_pathsum == strict.final_pathsum, evidence
    assert tolerant.final_pathsum != rr_only.final_pathsum, evidence
    assert tolerant.equivalent == expected_exact, evidence
    assert tolerant.rr_approximate is False, evidence

    # At WMC fallback, both backends must classify the strict RR residual.


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("0.0000000004", "0.0000000198", "not_equivalent"),
        ("-0.0000000004", "0.0000000202", "equivalent"),
    ],
)
def test_default_hybrid_rr_tolerance_matches_explicit_value(
    backend, a, b, expected
):
    """The public default must preserve the source-faithful WMC input."""
    source = _source(a, b)
    options = dict(
        backend=backend, method="hybrid", strategy="Naive",
        tool_name="gpmc", timeout=60,
        approximate_distance_tolerance=_EPS,
    )
    implicit = check_equivalence(_ID, source, **options)
    explicit = check_equivalence(
        _ID, source, rr_tolerance=_RR, **options,
    )
    assert implicit.equivalent == explicit.equivalent == expected
    assert implicit.wmc_solver_invoked is explicit.wmc_solver_invoked is True
    assert implicit.final_pathsum == explicit.final_pathsum
    assert implicit.rr_approximate is explicit.rr_approximate is False


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize(
    "a,b", [
        ("0.0000000004", "0.0000000198"),
        ("-0.0000000004", "0.0000000202"),
    ],
)
@pytest.mark.parametrize(
    "distance_epsilon,expected",
    [(1e-7, "equivalent"), (1e-9, "not_equivalent")],
)
def test_hybrid_source_distance_threshold_is_not_hardcoded(
    backend, a, b, distance_epsilon, expected
):
    """Changing distance tolerance must control the same source metric."""
    result = check_equivalence(
        _ID, _source(a, b), backend=backend, method="hybrid",
        strategy="Naive", rr_tolerance=_RR,
        approximate_distance_tolerance=distance_epsilon,
        tool_name="gpmc", timeout=60,
    )
    assert result.equivalent == expected
    assert result.wmc_solver_invoked is True
    assert result.rr_approximate is False


@pytest.mark.parametrize(
    "a,b,expected", [
        ("0.0000000004", "0.0000000198", "not_equivalent"),
        ("-0.0000000004", "0.0000000202", "equivalent"),
    ],
)
def test_python_safe_mode_preserves_source_distance_through_hybrid(
    a, b, expected
):
    """Spawned tolerant RR must retain provenance for faithful WMC fallback."""
    result = check_equivalence(
        _ID, _source(a, b), backend="python", method="hybrid",
        strategy="Naive", rr_tolerance=_RR, safe_mode=True,
        approximate_distance_tolerance=_EPS,
        tool_name="gpmc", timeout=90,
    )
    assert result.equivalent == expected
    assert result.wmc_solver_invoked is True
    assert result.rr_approximate is False
