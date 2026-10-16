"""Regression tests for deferred Ganak verification in the Rust backend.

A reduction-only check must not start the packaged solver. Actual WMC calls
must still fail fast on an invalid executable; the public Python resource
context retains its packaged-distribution verification.
"""
import pytest
from qiskit import QuantumCircuit

from QuPRS import check_equivalence
from QuPRS.utils import WMC


def test_rust_reduction_does_not_prevalidate_ganak(monkeypatch):
    import QuPRS.utils.ganak_distribution as distribution

    def forbidden(*args, **kwargs):
        raise AssertionError("Python Ganak validation is unnecessary before reduction")

    monkeypatch.delenv("QUPRS_GANAK_PATH", raising=False)
    monkeypatch.setattr(distribution, "binary_diagnostics", forbidden)
    identity = QuantumCircuit(1)
    result = check_equivalence(
        identity, identity, method="reduction_rules",
        strategy="Difference", backend="rust", tool_name="ganak",
    )
    assert result.equivalent in {"equivalent", "equivalent*"}
    assert result.wmc_time is None


def test_rust_hybrid_reduction_skips_invalid_ganak_override(monkeypatch, tmp_path):
    bogus = tmp_path / "invalid-ganak"
    bogus.write_bytes(b"not-a-ganak-executable")
    monkeypatch.setenv("QUPRS_GANAK_PATH", str(bogus))
    identity = QuantumCircuit(1)
    result = check_equivalence(
        identity, identity, method="hybrid",
        strategy="Difference", backend="rust", tool_name="ganak",
    )
    assert result.equivalent in {"equivalent", "equivalent*"}
    assert result.wmc_time is None


def test_rust_wmc_rejects_invalid_ganak_override(monkeypatch, tmp_path):
    bogus = tmp_path / "invalid-ganak"
    bogus.write_bytes(b"not-a-ganak-executable")
    monkeypatch.setenv("QUPRS_GANAK_PATH", str(bogus))
    identity = QuantumCircuit(1)
    hh = QuantumCircuit(1)
    hh.h(0)
    hh.h(0)
    with pytest.raises(Exception, match="Wrong Ganak architecture|Ganak .*failed|Ganak .*architecture"):
        check_equivalence(
            identity, hh, method="wmc_only",
            strategy="Difference", backend="rust", tool_name="ganak",
        )


def test_python_ganak_resource_keeps_default_verification(monkeypatch):
    import QuPRS.utils.ganak_distribution as distribution

    def forbidden(*args, **kwargs):
        raise RuntimeError("packaged Ganak verification is required")

    monkeypatch.delenv("QUPRS_GANAK_PATH", raising=False)
    monkeypatch.setattr(distribution, "binary_diagnostics", forbidden)
    with pytest.raises(RuntimeError, match="verification is required"):
        with WMC("ganak"):
            pytest.fail("Unverified binary must not be yielded")
