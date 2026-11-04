"""Opt-in, external-only d4 SolverAdapter research bridge (QOO-157).

Never registered by import. No bundled d4, no automatic fallback, and no
claim of an arithmetic precision certificate. Provenance is a research gate,
not a cryptographic attestation of internal GMP error bounds.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re

from QuPRS.utils.precision_count import PrintedCount
from QuPRS.utils.solver_adapter import (
    SolverAdapter, SolverCapabilities, SolverExecutionError, SolverResultError,
)
from d4_transport import parse_d4_printed

UPSTREAM = "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class D4ResearchAdapter(SolverAdapter):
    expected_binary_sha256: str = ""
    upstream_commit: str = ""
    preparse_gmp_bits: int = 0

    def format_weights(self, real, imag):
        return f"{real} {imag} 0", "1.0 0.0 0"

    def resource(self, resolver):
        # Research-only, explicit outside binary; no packaged fallback.
        if self.resource_factory is None:
            raise SolverExecutionError("d4 research adapter requires an explicit external binary")
        return self.resource_factory()

    def verify_binary(self, executable, timeout):
        if timeout <= 0:
            raise SolverExecutionError("d4 verification deadline exhausted")
        path = Path(executable)
        if not path.is_file():
            raise SolverExecutionError("d4 research binary not found")
        if not SHA256.fullmatch(self.expected_binary_sha256):
            raise SolverExecutionError("d4 research binary SHA is missing or malformed")
        if self.upstream_commit != UPSTREAM or self.preparse_gmp_bits < 128:
            raise SolverExecutionError("d4 research GMP initialization provenance insufficient")
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != self.expected_binary_sha256:
            raise SolverExecutionError("d4 research binary SHA mismatch")

    def parse_output_precise(self, stdout):
        try:
            count = parse_d4_printed(stdout)
        except ValueError as exc:
            raise SolverResultError(str(exc)) from exc
        return PrintedCount(
            count.real, count.imag, count.real_half_unit,
            count.imag_half_unit, count.format_name,
        )

    def parse_output(self, stdout):
        count = self.parse_output_precise(stdout)
        try:
            re_value = float(count.real)
            im_value = float(count.imag)
        except OverflowError as exc:
            raise SolverResultError("d4 count outside f64 range") from exc
        if not (math.isfinite(re_value) and math.isfinite(im_value)):
            raise SolverResultError("non-finite d4 result")
        return complex(re_value, im_value)


def external_research_adapter(binary: Path, provenance_file: Path) -> D4ResearchAdapter:
    """Build an adapter from explicit operator-supplied provenance and binary.

    The caller is responsible for verifying the CI provenance origin. This
    local file is insufficient to establish trusted internal arithmetic.
    """
    binary = Path(binary).resolve(strict=True)
    meta = json.loads(Path(provenance_file).read_text())
    sha = meta.get("binary_sha256")
    revision = meta.get("d4_upstream_commit")
    bits = meta.get("gmp_preparse_bits")
    if not isinstance(sha, str) or not SHA256.fullmatch(sha):
        raise SolverExecutionError("d4 manifest lacks a valid binary SHA256")
    if revision != UPSTREAM or type(bits) is not int or bits < 128 or bits > 2048:
        raise SolverExecutionError("d4 manifest lacks a supported preparse-GMP mode")
    if meta.get("source_patch_approved_for_research") is not True:
        raise SolverExecutionError("d4 manifest missing explicit research-only source patch")
    @contextmanager
    def resource():
        yield binary
    return D4ResearchAdapter(
        "d4-poc", ("-i",), SolverCapabilities("pair", exact_count_certificate=False),
        resource, sha, revision, bits,
    )
