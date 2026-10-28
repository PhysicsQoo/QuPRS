"""Numerical-distance and solver-precision cross-backend regression tests.

The reference precision bounds are mathematical fixtures, not certificates of
external weighted solver arithmetic. The public API tests must pass normally.
"""
from contextlib import contextmanager
import math
import os

from mpmath import mp
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from QuPRS import check_equivalence, config, _pathsum_rust
from QuPRS.utils import WMC


PREFIX = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
SOLVERS = ("gpmc", "ganak")
EPS = 2e-4


def qasm(operations=""):
    return PREFIX + operations


@contextmanager
def solver_binary(solver):
    """Use exactly the selected real solver for the native FFI prototype."""
    key = "QUPRS_" + solver.upper() + "_PATH"
    old = os.environ.get(key)
    with WMC(solver) as path:
        os.environ[key] = str(path)
        try:
            yield
        finally:
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def normalize_status(result):
    return {
        "Equivalent": "equivalent",
        "Equivalent (Up to Global Phase)": "equivalent*",
        "Not Equivalent": "not_equivalent",
        "Unknown": "unknown",
        "Timeout": "Timeout",
    }.get(result["status"], result["status"])


def trace_defect_from_distance(distance):
    sq = distance * distance
    return sq / (1 + math.sqrt(1 - sq))


def interval_distance_classification(m_hat, error_bound, epsilon):
    """Independent reference with an explicitly supplied *valid* m error bound.

    This is a mathematical oracle, not a claim that empirical solver deviations
    provide a certified universal bound.
    """
    if not (0 <= error_bound < 1):
        raise ValueError("invalid error bound")
    m_lo = max(0.0, m_hat - error_bound)
    m_hi = min(1.0, m_hat + error_bound)
    boundary = math.sqrt(1 - epsilon * epsilon)
    if m_lo >= boundary:
        return "inside"
    if m_hi < boundary:
        return "outside"
    return "unknown"


@pytest.mark.parametrize("ratio", ["0.5", "0.99999999", "1", "1.00000001", "1.5"])
def test_distance_to_magnitude_boundary_high_precision(ratio):
    """Do not subtract a floating-point cosine rounded to one."""
    with mp.workdps(90):
        eps = mp.mpf("0.0002")
        distance = eps * mp.mpf(ratio)
        theta = 2 * mp.asin(distance)
        m = abs(mp.cos(theta / 2))
        defect = 1 - m
        derived = mp.sqrt(1 - m * m)
        assert abs(derived - distance) < mp.mpf("1e-75")
        assert abs(defect - distance * distance / (1 + mp.sqrt(1 - distance * distance))) < mp.mpf("1e-75")
        assert (derived <= eps) == (mp.mpf(ratio) <= 1)


def test_f64_cannot_reliably_resolve_1e_8_distance_using_unit_magnitude():
    # An epsilon_D of 1e-8 needs a magnitude defect around 5e-17.
    tau = trace_defect_from_distance(1e-8)
    assert 0 < tau < math.ulp(1.0)
    assert 1.0 - tau == 1.0
    assert trace_defect_from_distance(1e-4) > tau


def test_reference_uncertainty_guard_has_three_distinct_outcomes():
    eps = 5e-4
    boundary = math.sqrt(1 - eps * eps)
    assumed_bound = 3e-9  # illustration only; NOT a solver certification
    assert interval_distance_classification(boundary + 3e-8, assumed_bound, eps) == "inside"
    assert interval_distance_classification(boundary - 3e-8, assumed_bound, eps) == "outside"
    assert interval_distance_classification(boundary, assumed_bound, eps) == "unknown"


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("theta,expected", [
    ("0.00032", "equivalent"),
    ("0.00048", "not_equivalent"),
])
def test_native_distance_mode_has_no_early_strict_negative(solver, theta, expected):
    """Native opt-in path: strict RR negative must not preempt distance mode."""
    left, right = qasm(), qasm("rz(" + theta + ") q[0];\n")
    with solver_binary(solver):
        rr = _pathsum_rust.check_equivalence(
            left, right, method="reduction_rules", strategy="Naive",
            tool_name=solver, timeout=45, approximate_distance_tolerance=EPS,
        )
        hybrid = _pathsum_rust.check_equivalence(
            left, right, method="hybrid", strategy="Naive",
            tool_name=solver, timeout=45, approximate_distance_tolerance=EPS,
        )
        wmc = _pathsum_rust.check_equivalence(
            left, right, method="wmc_only", strategy="Naive",
            tool_name=solver, timeout=45, approximate_distance_tolerance=EPS,
        )
    assert normalize_status(rr) == "unknown", (solver, theta, rr)
    assert normalize_status(hybrid) == expected, (solver, theta, hybrid)
    assert normalize_status(wmc) == expected, (solver, theta, wmc)
    assert "wmc_solver_time_sec" in hybrid
    assert "wmc_solver_time_sec" not in rr


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("theta,expected", [
    ("0.00032", "equivalent"),
    ("0.00048", "not_equivalent"),
])
def test_public_distance_api_contract(backend, theta, expected):
    """The opt-in API must work in both execution backends."""
    left, right = qasm(), qasm("rz(" + theta + ") q[0];\n")
    result = check_equivalence(
        left, right, backend=backend, method="hybrid", strategy="Naive",
        tool_name="gpmc", timeout=45, approximate_distance_tolerance=EPS,
    )
    assert result.equivalent == expected


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_public_sub_f64_distance_guard(backend):
    """WMC float output cannot by itself resolve a projective D of 1e-8."""
    left, right = qasm(), qasm("rz(0.00000002) q[0];\n")
    result = check_equivalence(
        left, right, method="wmc_only", backend=backend, tool_name="gpmc",
        strategy="Naive", timeout=45, approximate_distance_tolerance=1e-8,
    )
    # A definite answer is permitted only with valid numerical/symbolic
    # certification, never because a rounded-to-one f64 count looks exact.
    if result.equivalent != "unknown":
        assert getattr(result, "distance_interval_certified", False), (
            backend, result.equivalent, "uncertified near-boundary verdict"
        )


def test_multi_step_cancellation_preserves_net_rotation_in_python_wmc():
    """Local tiny rotations and cancellations must not erase a larger residue."""
    identity = QuantumCircuit(1)
    multi = QuantumCircuit(1)
    for _ in range(40):
        multi.rz(1.5e-5, 0)
        multi.rz(-1.5e-5, 0)
    multi.rz(6e-4, 0)
    total = QuantumCircuit(1)
    total.rz(6e-4, 0)
    assert Operator(multi).equiv(Operator(total), atol=1e-10, rtol=0)
    assert not Operator(identity).equiv(Operator(total), atol=1e-8, rtol=0)
    before = config.get_tolerance()
    try:
        config.set_tolerance(1e-6)
        for target in (multi, total):
            result = check_equivalence(
                identity, target, backend="python", method="wmc_only",
                strategy="Naive", tool_name="gpmc", timeout=45,
                wmc_magnitude_tolerance=1e-8,
            )
            assert result.equivalent == "not_equivalent"
            assert result.tool_time is not None
    finally:
        config.set_tolerance(before)


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("depth", (60, 80))
def test_true_identity_solver_numerical_floor_is_reported_not_hidden(solver, depth):
    """Solver-specific observations must never become a universal error bound."""
    identity, many_h = QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(depth):
        many_h.h(0)
    assert Operator(identity).equiv(Operator(many_h), atol=1e-12, rtol=0)
    answer = check_equivalence(
        identity, many_h, method="wmc_only", backend="python",
        strategy="Naive", tool_name=solver, timeout=45,
        wmc_magnitude_tolerance=1e-8,
    )
    assert answer.equivalent == "equivalent", (solver, depth, answer.equivalent)
    assert answer.tool_time is not None
    assert answer.log_wmc is not None
    expected_log2 = 1 + depth / 2
    observed_rel_error = abs(math.expm1((float(answer.log_wmc) - expected_log2) * math.log(2)))
    assert math.isfinite(observed_rel_error)
    assert observed_rel_error < 1e-8, (solver, depth, observed_rel_error)
    if solver == "ganak":
        # Case-specific reference, not a guarantee for other circuits.
        assert observed_rel_error > 1e-10


@pytest.mark.parametrize("depth", (60, 80))
def test_ganak_too_strict_magnitude_gate_rejects_a_true_identity(depth):
    identity, many_h = QuantumCircuit(1), QuantumCircuit(1)
    for _ in range(depth):
        many_h.h(0)
    answer = check_equivalence(
        identity, many_h, method="wmc_only", backend="python",
        strategy="Naive", tool_name="ganak", timeout=45,
        wmc_magnitude_tolerance=1e-10,
    )
    assert answer.equivalent == "not_equivalent"
    assert answer.tool_time is not None


@pytest.mark.parametrize("backend", ("python", "rust"))
@pytest.mark.parametrize("bad", (0, 1, -1e-8, float("nan"), float("inf"), False, True, "1e-8"))
def test_public_distance_rejects_invalid_parameters_before_verification(backend, bad):
    with pytest.raises(ValueError, match="approximate_distance_tolerance"):
        check_equivalence(
            qasm(), qasm(), backend=backend, method="reduction_rules",
            approximate_distance_tolerance=bad,
        )


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_distance_and_magnitude_parameters_are_mutually_exclusive(backend):
    with pytest.raises(ValueError, match="conflicts"):
        check_equivalence(
            qasm(), qasm(), backend=backend, method="reduction_rules",
            approximate_distance_tolerance=EPS, wmc_magnitude_tolerance=1e-6,
        )


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_opt_in_exact_rr_fast_path_retains_proof_provenance(backend):
    result = check_equivalence(
        qasm(), qasm(), backend=backend, method="hybrid",
        approximate_distance_tolerance=EPS,
    )
    assert result.equivalent == "equivalent"
    assert result.tool_time is None
    assert result.decision_basis == "symbolic"
    assert result.approximate_distance_tolerance == EPS


def test_distance_classification_guard_at_the_reference_boundary():
    from QuPRS.utils.wmc_solvers import classify_approximate_weighted_count
    eps = 2e-4
    tau = trace_defect_from_distance(eps)
    for defect, expected in (
        (tau - 6e-9, "equivalent"),
        (tau, "unknown"),
        (tau + 6e-9, "not_equivalent"),
    ):
        result, _ = classify_approximate_weighted_count(
            4.0 * (1.0 - defect), 0.0, 2.0,
            distance_tolerance=eps, phase_tolerance=1e-8,
        )
        assert result == expected, (defect, result)


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_distance_mode_ignores_mutable_legacy_magnitude_default(backend):
    """The opt-in distance API does not inherit an unrelated WMC default."""
    original = config.WMC_MAGNITUDE_TOLERANCE
    try:
        config.WMC_MAGNITUDE_TOLERANCE = 1e-6
        result = check_equivalence(
            qasm(), qasm(), backend=backend, method="reduction_rules",
            approximate_distance_tolerance=EPS,
        )
        assert result.equivalent == "equivalent"
        assert result.decision_basis == "symbolic"
    finally:
        config.WMC_MAGNITUDE_TOLERANCE = original


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_structural_mismatch_has_consistent_provenance(backend):
    different_size = qasm().replace("qreg q[1]", "qreg q[2]")
    result = check_equivalence(
        qasm(), different_size, backend=backend, method="hybrid",
        approximate_distance_tolerance=EPS,
    )
    assert result.equivalent == "not_equivalent"
    assert result.tool_time is None
    assert result.decision_basis == "structural"


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_explicit_default_wmc_magnitude_is_not_a_distance_conflict(backend):
    """The canonical unused WMC default is accepted by all public backends."""
    result = check_equivalence(
        qasm(), qasm(), backend=backend, method="reduction_rules",
        approximate_distance_tolerance=EPS,
        wmc_magnitude_tolerance=1e-8,
    )
    assert result.equivalent == "equivalent"
    assert result.approximate_distance_tolerance == EPS


def test_direct_pyo3_structural_mismatch_has_explicit_provenance():
    two = qasm().replace("qreg q[1]", "qreg q[2]")
    raw = _pathsum_rust.check_equivalence(
        qasm(), two, method="hybrid", approximate_distance_tolerance=EPS,
    )
    assert raw["status"] == "Not Equivalent"
    assert raw["decision_basis"] == "structural"
    assert raw["wmc_solver_invoked"] is False


@pytest.mark.parametrize("backend", ("python", "rust"))
def test_public_wmc_observation_identifies_real_solver_invocation(backend):
    result = check_equivalence(
        qasm(), qasm("rz(0.001) q[0];\n"),
        backend=backend, method="wmc_only", strategy="Naive",
        tool_name="gpmc", timeout=45,
    )
    assert result.wmc_solver_invoked is True
    assert result.decision_basis == "numerical_legacy"
    assert result.wmc_numerical_verdict == result.equivalent


def test_focused_native_precision_transport_evidence():
    """Bounded native A/B evidence on the existing WMC CI runner.

    Experimental source is unchanged. Raw decimal Solver output is preserved
    before Python or Rust converts it to binary64. This test does not claim a
    numerical error certificate.
    """
    import hashlib
    import json
    import re
    import subprocess
    import time
    from contextlib import ExitStack
    from decimal import Decimal, localcontext
    from pathlib import Path

    from QuPRS.utils.solver_process import run as run_solver

    base = "b122962eccb9b686cb614b6e84f539e8b5cd9a14"
    gpmc_rev = "a1bda3489e959d3695b6798d327c5a1fc1bed305"
    source_diff = subprocess.check_output([
        "git", "diff", "--name-only", base, "HEAD", "--",
        "src/QuPRS", "rust/pathsum", "rust/python_ffi", "GPMC",
    ], text=True).strip()
    assert not source_diff, "Production source changed relative to precision baseline: " + source_diff
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD:GPMC"], text=True
    ).strip() == gpmc_rev

    cases = (
        ("sub_f64_magnitude", "0.99999999999999994746875", "0", "1", "0", True),
        ("magnitude_overshoot", "1.00000000000000005253125", "0", "1", "0", True),
        ("tiny_complex_phase", "1", "0.0000000000000000000001", "1", "0", True),
        ("catastrophic_cancellation", "10000000000000001", "0", "-10000000000000000", "0", False),
        ("signed_complex_cancellation", "10000000000000001", "0.00000000000000000001", "-10000000000000000", "0", False),
        ("negative_tiny_imaginary", "1", "-0.00000000000000000000000001", "1", "0", True),
    )
    modes = {
        "gpmc": (
            ("default", ("-mode=1",)),
            ("digits128", ("-mode=1", "-prec=128")),
            ("digits256", ("-mode=1", "-prec=256")),
        ),
        "ganak": (
            ("default_prob", ("--mode=6",)),
            ("default_prob0", ("--mode=6", "--prob", "0")),
            ("bits128_prob", ("--mode=6", "--mpfrprec", "128")),
            ("bits128_prob0", ("--mode=6", "--mpfrprec", "128", "--prob", "0")),
            ("bits256_prob", ("--mode=6", "--mpfrprec", "256")),
            ("bits256_prob0", ("--mode=6", "--mpfrprec", "256", "--prob", "0")),
        ),
    }
    prefixes = (
        "c s exact double prec-sci", "c s exact arb cpx",
        "c s exact quadruple float", "c s exact arb frac",
    )

    def sign_im(part):
        return "- " + part[1:] + "i" if part.startswith("-") else "+ " + part + "i"

    def make_cnf(solver, case):
        _, pos_re, pos_im, neg_re, neg_im, forced = case
        if solver == "gpmc":
            weights = (
                "c p weight 1 " + pos_re + " " + pos_im + " 0",
                "c p weight -1 " + neg_re + " " + neg_im + " 0",
            )
        else:
            weights = (
                "c p weight 1 " + pos_re + " " + sign_im(pos_im) + " 0",
                "c p weight -1 " + neg_re + " " + sign_im(neg_im) + " 0",
            )
        return "\n".join((
            "p cnf 1 " + str(int(forced)), "c t wmc",
            *weights, *(("1 0",) if forced else ()), "",
        ))

    def exact(case):
        _, pr, pi, nr, ni, forced = case
        with localcontext() as ctx:
            ctx.prec = 110
            return (
                Decimal(pr) if forced else Decimal(pr) + Decimal(nr),
                Decimal(pi) if forced else Decimal(pi) + Decimal(ni),
            )

    def as_decimal(part):
        if "/" in part:
            n, d = part.split("/")
            with localcontext() as ctx:
                ctx.prec = 110
                return Decimal(n) / Decimal(d)
        return Decimal(part)

    def read_raw(stdout):
        values = []
        for line in stdout.splitlines():
            for prefix in prefixes:
                if line.startswith(prefix) and (
                    len(line) == len(prefix) or line[len(prefix)].isspace()
                ):
                    raw = re.sub(r"\s+", "", line[len(prefix):]).replace("+-", "-")
                    try:
                        if not raw.endswith("i"):
                            parts = (raw, "0")
                        else:
                            raw_no_i = raw[:-1]
                            split = [
                                idx for idx in range(1, len(raw_no_i))
                                if raw_no_i[idx] in "+-" and raw_no_i[idx - 1] not in "eE"
                            ]
                            parts = (
                                (raw_no_i[:split[-1]], raw_no_i[split[-1]:])
                                if split else ("0", raw_no_i)
                            )
                        decimal_pair = tuple(as_decimal(p) for p in parts)
                        values.append((line[len(prefix):].strip(), decimal_pair))
                    except Exception as exc:
                        return {"error": "invalid_solver_count", "detail": repr(exc)}
        if not values:
            return {"error": "missing_solver_count"}
        if any(v[1] != values[0][1] for v in values[1:]):
            return {"error": "conflicting_solver_counts"}
        return {
            "raw": values[0][0],
            "real_decimal": str(values[0][1][0]),
            "imag_decimal": str(values[0][1][1]),
            "count_lines": len(values),
        }

    evidence = {
        "experiment": "source-pinned-native-precision-transport",
        "source_base": base,
        "gpmc_submodule": gpmc_rev,
        "source_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "native": [],
        "public_api": [],
    }
    folder = Path("wmc-evidence-results")
    folder.mkdir(exist_ok=True)
    import tempfile

    with ExitStack() as stack:
        binary = {
            solver: Path(stack.enter_context(WMC(solver)))
            for solver in ("gpmc", "ganak")
        }
        fingerprints = {
            solver: hashlib.sha256(path.read_bytes()).hexdigest()
            for solver, path in binary.items()
        }
        with tempfile.TemporaryDirectory(prefix="quprs-precision-") as tmp:
            for solver in ("gpmc", "ganak"):
                for case in cases:
                    payload = make_cnf(solver, case)
                    cnf_path = Path(tmp) / (solver + "-" + case[0] + ".cnf")
                    cnf_path.write_text(payload)
                    ref = exact(case)
                    for variant, flags in modes[solver]:
                        started = time.monotonic()
                        row = {
                            "solver": solver, "case": case[0],
                            "variant": variant, "flags": list(flags),
                            "binary_sha256": fingerprints[solver],
                            "cnf_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                            "oracle": [str(ref[0]), str(ref[1])],
                        }
                        try:
                            result = run_solver(
                                [str(binary[solver]), *flags, str(cnf_path)],
                                timeout=10,
                            )
                            row.update({
                                "returncode": result.returncode,
                                "stdout": result.stdout[:16000],
                                "stderr": result.stderr[:4000],
                            })
                            parsed = read_raw(result.stdout)
                            row["parsed_raw"] = parsed
                            if "real_decimal" in parsed:
                                with localcontext() as ctx:
                                    ctx.prec = 110
                                    row["absolute_error"] = [
                                        str(abs(as_decimal(parsed["real_decimal"]) - ref[0])),
                                        str(abs(as_decimal(parsed["imag_decimal"]) - ref[1])),
                                    ]
                        except Exception as exc:
                            row["error"] = repr(exc)
                        row["elapsed_sec"] = round(time.monotonic() - started, 6)
                        evidence["native"].append(row)

        api_cases = (
            ("well_inside", "0.00032", 2e-4, "equivalent"),
            ("well_outside", "0.00048", 2e-4, "not_equivalent"),
            ("boundary_guard", "0.0004", 2e-4, "unknown"),
            ("sub_f64_guard", "0.0000000205", 1e-8, "unknown"),
        )
        for name, theta, epsilon, expected_status in api_cases:
            left, right = qasm(), qasm("rz(" + theta + ") q[0];\n")
            for backend in ("python", "rust"):
                for solver in ("gpmc", "ganak"):
                    started = time.monotonic()
                    row = {
                        "case": name, "angle": theta, "distance_epsilon": epsilon,
                        "analytic_distance": abs(math.sin(float(theta) / 2)),
                        "backend": backend, "solver": solver,
                        "expected": expected_status,
                    }
                    try:
                        with solver_binary(solver):
                            answer = check_equivalence(
                                left, right, method="wmc_only", strategy="Naive",
                                backend=backend, tool_name=solver, timeout=20,
                                approximate_distance_tolerance=epsilon,
                            )
                        row.update({
                            "actual": answer.equivalent,
                            "decision_basis": answer.decision_basis,
                            "wmc_solver_invoked": answer.wmc_solver_invoked,
                            "log_wmc": str(answer.log_wmc),
                        })
                    except Exception as exc:
                        row["error"] = repr(exc)
                    row["elapsed_sec"] = round(time.monotonic() - started, 6)
                    evidence["public_api"].append(row)

    evidence_file = folder / "native-precision-focused.json"
    evidence_file.write_text(json.dumps(evidence, indent=2, default=str))
    print(
        "Focused precision native measurements:", len(evidence["native"]),
        "public API:", len(evidence["public_api"]),
        "artifact:", evidence_file,
    )
    assert len(evidence["native"]) == 54
    assert len(evidence["public_api"]) == 16
    baseline_failures = [
        x for x in evidence["native"]
        if x["variant"] in ("default", "default_prob")
        and (x.get("returncode") != 0 or "real_decimal" not in x.get("parsed_raw", {}))
    ]
    api_disagreements = [
        x for x in evidence["public_api"]
        if x.get("actual") != x["expected"]
    ]
    assert not baseline_failures, "Default native precision cases failed; inspect artifact"
    assert not api_disagreements, "Public source-to-WMC precision classifications differ; inspect artifact"
