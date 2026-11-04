"""Research-only dual d4-38/d4-96 SolverAdapter with one untimed SHA check.

The d4 binary and source SHA are fixed and verified before CodSpeed; this
bypasses *only* per-invocation hashing of an immutable CI scratch binary.
No production default, fallback, or wheel bundle.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from QuPRS.utils.solver_adapter import SolverCapabilities, SolverExecutionError
from d4_solver_adapter_poc import D4ResearchAdapter, UPSTREAM

ALLOWED = (38, 96)


@dataclass(frozen=True)
class MatchedD4ResearchAdapter(D4ResearchAdapter):
    prechecked_binary_path: str = ""
    target_decimal_digits: int = 0

    def verify_binary(self, executable, timeout):
        if not timeout > 0:
            raise SolverExecutionError("no time remains before d4 execution")
        if self.target_decimal_digits not in ALLOWED:
            raise SolverExecutionError("unsupported matched precision")
        if self.upstream_commit != UPSTREAM:
            raise SolverExecutionError("untrusted d4 upstream source revision")
        if Path(executable).resolve(strict=True).as_posix() != self.prechecked_binary_path:
            raise SolverExecutionError("d4 binary path changed since source preflight")
        # SHA-256 is verified once outside the official CodSpeed measured
        # calls; this strictly assumes an immutable test-owned CI file.


def read_pinned_manifest(binary: Path, manifest: Path, digits: int) -> dict:
    if digits not in ALLOWED:
        raise ValueError("supported effective-decimal budgets are 38 and 96")
    path = binary.resolve(strict=True)
    meta = json.loads(manifest.read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != meta.get("binary_sha256"):
        raise ValueError("d4 binary hash does not match recorded provenance")
    if (meta.get("upstream_commit") != UPSTREAM
            or meta.get("target_decimal_digits") != digits
            or meta.get("source_patch_isolated") is not True
            or meta.get("precision_certified") is not False):
        raise ValueError("d4 precision variant provenance invalid")
    bits = meta.get("gmp_requested_bits")
    actual = meta.get("gmp_actual_bits")
    if type(bits) is not int or type(actual) is not int:
        raise ValueError("d4 variant missing requested or actual GMP bit count")
    if actual < bits or actual > bits + 128:
        raise ValueError("d4 observed GMP precision incompatible with requested bits")
    return meta


def matched_adapter(binary: Path, manifest: Path, digits: int):
    meta = read_pinned_manifest(binary, manifest, digits)
    path = binary.resolve(strict=True)

    @contextmanager
    def resource():
        yield path

    return MatchedD4ResearchAdapter(
        solver_id=f"d4-{digits}",
        arguments=("-i",),
        capabilities=SolverCapabilities("pair", exact_count_certificate=False),
        resource_factory=resource,
        expected_binary_sha256=meta["binary_sha256"],
        upstream_commit=UPSTREAM,
        preparse_gmp_bits=meta["gmp_requested_bits"],
        prechecked_binary_path=path.as_posix(),
        target_decimal_digits=digits,
    )
