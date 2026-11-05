"""QOO-156 QASM-equivalence benchmark verdict guard: fail closed on NEQ."""
from __future__ import annotations
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ABBA = load_from_path("qoo156_cli_abba", ROOT / "scripts/qoo156_cli_abba.py")
CODSPEED = load_from_path(
    "qoo156_codspeed_cli_guard",
    ROOT / "benchmarks/codspeed/test_qoo156_cli_supervisor.py",
)


@pytest.mark.parametrize(
    "status,accept",
    [
        ("equivalent\n", True),
        ("equivalent*\n", True),
        ("not_equivalent\n", False),
        ("NOT EQUIVALENT\n", False),
        ("unknown\n", False),
        ("Timeout\n", False),
        ("MemoryOut\n", False),
        ("prefix equivalent\n", False),
        ("equivalent\nnot_equivalent\n", False),
        ("\n", False),
    ],
)
def test_both_science_guards_reject_false_positive(status, accept):
    assert ABBA.accepted_dual_verdict(status.encode()) is accept
    assert CODSPEED.accepted_dual_verdict(status) is accept


class FakeProc:
    def __init__(self, output):
        self.output = output
        self.returncode = 0

    def communicate(self, timeout=None):
        return self.output, b"" if isinstance(self.output, bytes) else ""


@pytest.mark.parametrize("bad", ["not_equivalent\n", "unknown\n", "equivalent\nnot_equivalent\n"])
def test_abba_real_run_path_rejects_bad_verdict(monkeypatch, bad):
    monkeypatch.setattr(ABBA.subprocess, "Popen", lambda *args, **kwargs: FakeProc(bad.encode()))
    with pytest.raises(AssertionError, match="incorrect verdict"):
        ABBA.run(Path("/not/a/real/cli"), [Path("/not/a/real.qasm")], "dual_ghz32")


@pytest.mark.parametrize("bad", ["not_equivalent\n", "unknown\n", "equivalent\nnot_equivalent\n"])
def test_codspeed_real_run_path_rejects_bad_verdict(monkeypatch, tmp_path, bad):
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("QOO156_BASE_CLI", "/not/a/real/cli")
    monkeypatch.setenv("QOO156_HEAD_CLI", "/not/a/real/cli")
    monkeypatch.setattr(CODSPEED.subprocess, "Popen", lambda *args, **kwargs: FakeProc(bad))
    with pytest.raises(AssertionError, match="expected exact EQ verdict"):
        CODSPEED.run_case("base", "dual_qpe8")


@pytest.mark.parametrize("valid", ["equivalent\n", "equivalent*\n"])
def test_codspeed_real_run_path_accepts_valid_equivalence(monkeypatch, tmp_path, valid):
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("QOO156_HEAD_CLI", "/not/a/real/cli")
    monkeypatch.setattr(CODSPEED.subprocess, "Popen", lambda *args, **kwargs: FakeProc(valid))
    assert CODSPEED.run_case("head", "dual_ghz32") == "ok"
