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
