"""Source-QASM/CodSpeed argument contract without building Rust or calling WMC.

Check the real verifier harness with an injected QuPRS function.  These tests
are quick and prevent argument-count/fixture-corpus regressions before CI runs.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "benchmarks/codspeed/solver_case.py"
MARKER = "QUPRS_WALLTIME_RESULT "


@pytest.fixture
def harness(monkeypatch):
    fake_quprs = types.ModuleType("QuPRS")
    calls = []

    def fake_check(first, second, **options):
        calls.append((Path(first), Path(second), options))
        return types.SimpleNamespace(
            equivalent="not_equivalent", wmc_solver_invoked=True,
            rr_approximate=False,
        )

    fake_quprs.check_equivalence = fake_check
    monkeypatch.setitem(sys.modules, "QuPRS", fake_quprs)
    spec = importlib.util.spec_from_file_location("isolated_codspeed_solver_case", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, calls


@pytest.mark.parametrize("suffix,folder,method", [
    ([], "h,ry,rz,cx", "hybrid"),
    (["transpiled"], "h,ry,rz,cx", "hybrid"),
    (["random_rotation", "hybrid"], "Random_Rotation", "hybrid"),
    (["random_rotation", "hybrid", "qiskit-2.6.1-opt0"],
     "qiskit-2.6.1-opt0/Random_Rotation", "hybrid"),
    (["transpiled", "wmc_only", "qiskit-2.6.1-opt0"],
     "qiskit-2.6.1-opt0/h,ry,rz,cx", "wmc_only"),
])
def test_exact_legacy_and_modern_positional_contract(
    harness, monkeypatch, capsys, tmp_path, suffix, folder, method
):
    module, calls = harness
    fixture_root = tmp_path / "benchmarks/MQTBench"
    filename = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
    (fixture_root / filename).parent.mkdir(parents=True, exist_ok=True)
    (fixture_root / filename).write_text("source", encoding="utf-8")
    target = fixture_root / folder / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("target", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        str(HARNESS), str(tmp_path), filename, "proportional",
        "gpmc", "rust", "0", *suffix,
    ])
    module.main()
    assert len(calls) == 1
    left, right, options = calls[0]
    assert (left, right) == (fixture_root / filename, target)
    assert options["method"] == method
    assert options["backend"] == "rust"
    assert options["tool_name"] == "gpmc"
    line = capsys.readouterr().out.strip()
    assert line.startswith(MARKER)
    payload = json.loads(line[len(MARKER):])
    assert payload["solver_invoked"] is True
    assert payload["qasm_corpus"] == (
        "qiskit-2.6.1-opt0" if len(suffix) == 3 else "historical"
    )


def test_formal_qasm261_reverse_case_pins_same_corpus(harness, monkeypatch, tmp_path):
    module, calls = harness
    root = tmp_path / "benchmarks/MQTBench"
    filename = "qft_nativegates_ibm_qiskit_opt0_16.qasm"
    base = root / filename
    target = root / "qiskit-2.6.1-opt0/Random_Rotation" / filename
    for path in (base, target):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixed qasm", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        str(HARNESS), str(tmp_path), filename, "proportional",
        "gpmc", "rust", "1", "random_rotation", "hybrid", "qiskit-2.6.1-opt0",
    ])
    module.main()
    assert calls[0][:2] == (target, base)


@pytest.mark.parametrize("suffix", [
    ["random_rotation", "hybrid", "invalid"],
    ["random_rotation", "hybrid", "qiskit-2.6.1-opt0", "extra"],
])
def test_invalid_qasm_corpus_or_extra_argument_rejected(harness, monkeypatch, tmp_path, suffix):
    module, calls = harness
    monkeypatch.setattr(sys, "argv", [
        str(HARNESS), str(tmp_path), "fixture.qasm", "proportional",
        "gpmc", "rust", "0", *suffix,
    ])
    with pytest.raises((ValueError, SystemExit)):
        module.main()
    assert calls == []


def test_qasm_basename_rejects_traversal(harness, monkeypatch, tmp_path):
    module, calls = harness
    monkeypatch.setattr(sys, "argv", [
        str(HARNESS), str(tmp_path), "../unsafe.qasm", "proportional",
        "gpmc", "rust", "0", "random_rotation", "hybrid", "qiskit-2.6.1-opt0",
    ])
    with pytest.raises(ValueError, match="basename"):
        module.main()
    assert calls == []


def test_legacy_dev_api_uses_verified_90_digits_not_unsupported_args(harness, monkeypatch, tmp_path):
    module, calls = harness
    # The checked-out dev API has no RR or precision-digits keyword.
    def legacy_checker(first, second, *, method, strategy, tool_name,
                       backend, timeout, wmc_phase_tolerance,
                       approximate_distance_tolerance):
        return None
    monkeypatch.setattr(module, "check_equivalence", legacy_checker)
    monkeypatch.setattr(
        sys.modules["QuPRS"], "config",
        types.SimpleNamespace(TOLERANCE=1e-10), raising=False,
    )
    rust_src = tmp_path / "rust/pathsum/src/solver_adapter.rs"
    rust_src.parent.mkdir(parents=True)
    rust_src.write_text(
        """impl SolverAdapter for GpmcDistanceAdapter {
    fn arguments(&self) -> &'static [&'static str] { &["-mode=1", "-prec=90"] }
}
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    options, provenance = module._compatible_solver_kwargs({
        "rr_tolerance": 1e-10, "approximate_distance_tolerance": 1e-8,
        "wmc_phase_tolerance": 1e-8, "gpmc_precision_digits": 90,
    })
    assert options == {
        "approximate_distance_tolerance": 1e-8,
        "wmc_phase_tolerance": 1e-8,
    }
    assert provenance == "legacy_90_digit_distance_source_checked"
    assert calls == []


def test_legacy_dev_api_rejects_mixed_precision_or_unproven_defaults(harness, monkeypatch, tmp_path):
    module, _ = harness
    def legacy_checker(first, second, *, method, strategy, tool_name,
                       backend, timeout, wmc_phase_tolerance,
                       approximate_distance_tolerance):
        return None
    monkeypatch.setattr(module, "check_equivalence", legacy_checker)
    monkeypatch.setattr(
        sys.modules["QuPRS"], "config",
        types.SimpleNamespace(TOLERANCE=1e-10), raising=False,
    )
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="non-90"):
        module._compatible_solver_kwargs({
            "rr_tolerance": 1e-10,
            "approximate_distance_tolerance": 1e-8,
            "gpmc_precision_digits": 30,
        })
    with pytest.raises(FileNotFoundError):
        module._compatible_solver_kwargs({
            "rr_tolerance": 1e-10,
            "approximate_distance_tolerance": 1e-8,
            "gpmc_precision_digits": 90,
        })
    sys.modules["QuPRS"].config.TOLERANCE = 1e-9
    with pytest.raises(RuntimeError, match="RR default"):
        module._compatible_solver_kwargs({
            "rr_tolerance": 1e-10,
            "approximate_distance_tolerance": 1e-8,
            "gpmc_precision_digits": 90,
        })


def test_qasm261_source_capability_probe_reports_supported_modern_api(harness, monkeypatch, capsys):
    module, calls = harness
    def modern_checker(first, second, *, rr_tolerance, gpmc_precision_digits,
                       approximate_distance_tolerance, wmc_phase_tolerance, **kw):
        return None
    monkeypatch.setattr(module, "check_equivalence", modern_checker)
    monkeypatch.setattr(sys, "argv", [str(HARNESS), "--probe-qasm261-contract"])
    module.main()
    line = capsys.readouterr().out.strip()
    assert line.startswith(module.CAPABILITY_PREFIX)
    record = json.loads(line[len(module.CAPABILITY_PREFIX):])
    assert record["status"] == "SUPPORTED"
    assert record["precision_contract"] == "public_per_call_pinned"
    assert calls == []


def test_qasm261_probe_only_recognizes_known_legacy_precision_gap(harness, monkeypatch, capsys):
    module, calls = harness
    def legacy_checker(first, second, *, method, strategy, tool_name,
                       backend, timeout, wmc_phase_tolerance,
                       approximate_distance_tolerance):
        return None
    monkeypatch.setattr(module, "check_equivalence", legacy_checker)
    monkeypatch.setattr(sys.modules["QuPRS"], "config",
                        types.SimpleNamespace(TOLERANCE=1e-10), raising=False)
    monkeypatch.setattr(sys, "argv", [str(HARNESS), "--probe-qasm261-contract"])
    monkeypatch.setattr(module, "_compatible_solver_kwargs",
                        lambda _: (_ for _ in ()).throw(RuntimeError(
                            module.LEGACY_GPMC_90_UNPROVEN)))
    module.main()
    record = json.loads(capsys.readouterr().out.strip()[len(module.CAPABILITY_PREFIX):])
    assert record == {
        "status": "NOT_COMPARABLE_LEGACY_BASE",
        "reason": module.LEGACY_GPMC_90_UNPROVEN,
    }
    monkeypatch.setattr(module, "_compatible_solver_kwargs",
                        lambda _: (_ for _ in ()).throw(RuntimeError("Actual Solver failure")))
    with pytest.raises(RuntimeError, match="Actual Solver failure"):
        module.main()
    assert calls == []
