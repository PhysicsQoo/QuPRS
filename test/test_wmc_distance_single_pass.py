"""Real-solver public-path parity and one-invocation distance regressions."""
import pytest

from QuPRS import check_equivalence

PREFIX = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'


def rotated(theta):
    return PREFIX + f"rz({theta}) q[0];\n"


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
@pytest.mark.parametrize("method", ("hybrid", "wmc_only"))
@pytest.mark.parametrize("theta,expected", (
    ("0.00032", "equivalent"),
    ("0.00048", "not_equivalent"),
))
def test_real_solver_python_pyo3_rust_distance_parity(
    backend, solver, method, theta, expected,
):
    result = check_equivalence(
        PREFIX, rotated(theta), backend=backend, method=method,
        tool_name=solver, strategy="Naive", timeout=45,
        approximate_distance_tolerance=2e-4,
    )
    assert result.equivalent == expected, (
        backend, solver, method, theta, result.equivalent,
        result.wmc_precision_reason,
    )
    assert result.wmc_solver_invoked is True
    assert result.wmc_printed_verdict in (
        "equivalent", "not_equivalent", "unknown",
    )
    assert result.wmc_precision_reason is not None
    assert result.tool_time is not None
    assert result.wmc_time is not None


@pytest.mark.parametrize("solver", ("gpmc", "ganak"))
@pytest.mark.parametrize("method", ("hybrid", "wmc_only"))
def test_python_real_solver_runs_once(monkeypatch, solver, method):
    import QuPRS.interface.ps2wmc as ps2wmc

    calls = []
    real_run = ps2wmc.run_wmc

    def counted_run(*args, **kwargs):
        calls.append((args, kwargs))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(ps2wmc, "run_wmc", counted_run)
    result = check_equivalence(
        PREFIX, rotated("0.00048"), backend="python",
        method=method, tool_name=solver, strategy="Naive",
        timeout=45, approximate_distance_tolerance=2e-4,
    )
    assert result.equivalent == "not_equivalent"
    assert len(calls) == 1, (solver, method, calls)
    assert calls[0][1]["preserve_count"] is True
    # Default GPMC complex precision is an effective 30 digits without
    # explicitly setting the solver CLI -prec flag. Ganak is unchanged.
    assert calls[0][1]["precision_digits"] is None


def test_explicit_gpmc_90_digit_mode_runs_once(monkeypatch):
    from QuPRS.interface import ps2wmc
    calls = []
    real_run = ps2wmc.run_wmc

    def capture_run(*args, **kwargs):
        calls.append(kwargs.get("precision_digits"))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(ps2wmc, "run_wmc", capture_run)
    result = check_equivalence(
        PREFIX, rotated("0.00048"), backend="python",
        method="wmc_only", tool_name="gpmc", strategy="Naive",
        timeout=45, approximate_distance_tolerance=2e-4,
        gpmc_precision_digits=90,
    )
    assert result.equivalent == "not_equivalent", result.wmc_precision_reason
    assert calls == [90]


def test_rr_decided_hybrid_does_not_run_wmc(monkeypatch):
    import QuPRS.interface.ps2wmc as ps2wmc

    def forbidden(*args, **kwargs):
        raise AssertionError("RR-decided hybrid must not invoke WMC")

    monkeypatch.setattr(ps2wmc, "run_wmc", forbidden)
    result = check_equivalence(
        PREFIX, PREFIX, backend="python", method="hybrid",
        strategy="Naive", tool_name="gpmc", timeout=45,
        approximate_distance_tolerance=2e-4,
    )
    assert result.equivalent in ("equivalent", "equivalent*")
    assert result.wmc_solver_invoked is False


def test_native_ganak_insufficient_printed_resolution():
    observed = check_equivalence(
        PREFIX, rotated("0.00000002"), backend="python",
        method="wmc_only", strategy="Naive", tool_name="ganak",
        timeout=45, approximate_distance_tolerance=1e-8,
    )
    # Ganak's midpoint yields a usable solver-dependent numerical answer,
    # while the raw interval and dynamic warning preserve the limitation.
    assert observed.equivalent in ("equivalent", "equivalent*")
    assert observed.wmc_printed_verdict == "unknown"
    assert observed.wmc_print_resolution_distance is not None
    assert observed.wmc_precision_reason == "ganak_point_estimate_resolution_limited"


def test_true_h80_identity_not_blocked_by_speculative_gpmc_budget():
    # Eighty Hadamards are an exact identity. The earlier conjectural
    # CNF-size/MPFR operation allowance turned a printed equivalent
    # GPMC observation into unknown; production should use printed count.
    circuit = PREFIX + "h q[0];\n" * 80
    result = check_equivalence(
        PREFIX, circuit, backend="python", method="wmc_only",
        strategy="Naive", tool_name="gpmc", timeout=45,
        approximate_distance_tolerance=1.414213562373095e-4,
    )
    assert result.wmc_solver_invoked is True
    assert result.wmc_printed_verdict == "equivalent"
    assert result.equivalent == "equivalent"
    assert result.wmc_precision_reason.startswith("gpmc_printed_uncertified_")


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_real_ganak_warns_from_observed_output_granularity(backend):
    identity = PREFIX
    candidate = rotated("0.00000002")
    with pytest.warns(RuntimeWarning, match="Ganak printed-count rounding resolution"):
        result = check_equivalence(
            identity, candidate, backend=backend,
            method="wmc_only", strategy="Naive", tool_name="ganak",
            approximate_distance_tolerance=1e-8,
        )
    assert result.wmc_solver_invoked is True
    assert result.wmc_print_resolution_distance is not None
    assert result.wmc_print_resolution_distance > 1e-8
    assert result.wmc_precision_reason is not None


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_ganak_no_resolution_warning_for_loose_requested_precision(backend):
    import warnings

    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always", RuntimeWarning)
        result = check_equivalence(
            PREFIX, rotated("0.00000002"), backend=backend,
            method="wmc_only", strategy="Naive", tool_name="ganak",
            approximate_distance_tolerance=2e-4,
        )
    assert result.wmc_solver_invoked is True
    assert result.wmc_print_resolution_distance is None
    assert not [w for w in observed if "Ganak printed-count" in str(w.message)]


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_analytic_identity_emits_no_ganak_precision_warning(backend):
    import warnings

    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always", RuntimeWarning)
        result = check_equivalence(
            PREFIX, PREFIX, backend=backend,
            method="wmc_only", tool_name="ganak",
            approximate_distance_tolerance=1e-8,
        )
    assert result.equivalent == "equivalent"
    assert result.wmc_solver_invoked is False
    assert result.wmc_print_resolution_distance is None
    assert not [w for w in observed if "Ganak printed-count" in str(w.message)]
