"""Focused Python native SolverAdapter contract for an external d4 binary.

No d4 native executable is bundled or spawned in these contract tests; the
production process supervisor is injected with a deterministic fake runner.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from QuPRS.interface.ps2wmc import run_wmc, wlogi_to_clauses
from QuPRS.utils.solver_adapter import (
    SolverExecutionError, SolverResultError, get_solver_adapter,
    registered_solver_adapter,
)
from d4_solver_adapter_poc import UPSTREAM, external_research_adapter


def make_poc(tmp_path, *, bits=426, source_approved=True):
    fake = tmp_path / "d4-counter"
    fake.write_bytes(b"research-only d4 executable content")
    manifest = tmp_path / "build-provenance.json"
    manifest.write_text(json.dumps({
        "binary_sha256": sha256(fake.read_bytes()).hexdigest(),
        "d4_upstream_commit": UPSTREAM,
        "gmp_preparse_bits": bits,
        "source_patch_approved_for_research": source_approved,
    }))
    return external_research_adapter(fake, manifest), fake, manifest


def test_d4_opt_in_registered_only_during_context(tmp_path, monkeypatch):
    adapter, fake, _ = make_poc(tmp_path)
    from QuPRS.utils import solver_process

    calls = []
    def runner(cmd, *, timeout):
        assert timeout > 0
        calls.append(cmd)
        return SimpleNamespace(
            returncode=0,
            stdout="s SATISFIABLE\nc s exact arb float 1.0000000000000000000000000000000000000001e-40+0i\n",
            stderr="",
        )
    monkeypatch.setattr(solver_process, "run", runner)
    with pytest.raises(ValueError, match="Unsupported"):
        get_solver_adapter("d4-poc")
    before = get_solver_adapter("gpmc").arguments
    with registered_solver_adapter(adapter):
        assert get_solver_adapter("d4-poc") is adapter
        assert wlogi_to_clauses([], {}, tool_name="d4-poc")[0] == []
        precise = run_wmc("source.cnf", "d4-poc", timeout=5, preserve_count=True)
        assert precise.real > 0
        assert precise.real < 1
        assert precise.format_name == "c s exact arb float"
        assert not adapter.capabilities.exact_count_certificate
        legacy = run_wmc("source.cnf", "d4-poc", timeout=5)
        assert legacy[0] > 0
        assert calls == [[str(fake), "-i", "source.cnf"]] * 2
    with pytest.raises(ValueError, match="Unsupported"):
        get_solver_adapter("d4-poc")
    assert get_solver_adapter("gpmc").arguments == before
    assert get_solver_adapter("ganak").arguments == ("--mode=6",)


def test_pinned_binary_mismatch_and_insufficient_precision_fail(tmp_path):
    adapter, fake, manifest = make_poc(tmp_path)
    adapter.verify_binary(fake, 5)
    fake.write_bytes(b"binary tampered")
    with pytest.raises(SolverExecutionError, match="SHA mismatch"):
        adapter.verify_binary(fake, 5)
    with pytest.raises(SolverExecutionError, match="preparse"):
        make_poc(tmp_path, bits=64)
    with pytest.raises(SolverExecutionError, match="source patch"):
        make_poc(tmp_path, source_approved=False)


def test_strict_malformed_and_nonzero_do_not_fallback(tmp_path, monkeypatch):
    adapter, fake, _ = make_poc(tmp_path)
    from QuPRS.utils import solver_process
    calls = []
    def runner(cmd, *, timeout):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="c s exact arb float nan+0i\n", stderr="")
    monkeypatch.setattr(solver_process, "run", runner)
    with registered_solver_adapter(adapter):
        with pytest.raises(SolverResultError, match="d4"):
            run_wmc("source.cnf", "d4-poc", timeout=5, preserve_count=True)
    assert calls == [[str(fake), "-i", "source.cnf"]]
