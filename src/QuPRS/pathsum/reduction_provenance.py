"""Request-local evidence for approximate symbolic path-sum reductions.

An RR rule hit is only a source-exact argument if no tolerance-based phase
change was used. Recording an event here is not a computed error bound. A
nonconstant residual without a propagated operator bound is inconclusive.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from QuPRS.utils.util import reduce_expression as _reduce_expression

_CURRENT = ContextVar("quprs_rr_provenance", default=None)
_MAX_EVENTS = 128


@dataclass
class RRProvenance:
    events: list[dict] = field(default_factory=list)
    unbounded: bool = False
    total_events: int = 0
    preserve_source: bool = False

    def record(self, kind, before, after, *, nonconstant, applied=True, detail=None):
        self.total_events += 1
        if nonconstant and applied:
            self.unbounded = True
        if len(self.events) < _MAX_EVENTS:
            self.events.append({
                "kind": kind,
                "before": str(before)[:320],
                "after": str(after)[:320],
                "nonconstant": bool(nonconstant),
                "applied": bool(applied),
                "error_bound_certified": False,
                "detail": detail,
            })


@contextmanager
def capture_rr_provenance(*, preserve_source=False):
    """Capture per-request RR evidence and optionally forbid lossy reductions.

    Source preservation retains global-phase labels and the last faithfully reduced PathSum. WMC can
    continue from that exact residual, not a regenerated original circuit.
    """
    evidence = RRProvenance(preserve_source=preserve_source)
    token = _CURRENT.set(evidence)
    try:
        yield evidence
    finally:
        _CURRENT.reset(token)


def tracked_reduce_expression(expr, mod_coeffs=1, linearize=True, drop_small=True):
    """Compare actual RR normalization against tolerance-free normalization.

    Cached normalization alone cannot own evidence: even cache hits must be
    inspected per verification. Only nonconstant differences block a
    projective-equivalence verdict; scalar global phase is diagnostic only.
    """
    value = _reduce_expression(expr, mod_coeffs, linearize, drop_small)
    evidence = _CURRENT.get()
    if evidence is not None and drop_small:
        exact = _reduce_expression(expr, mod_coeffs, linearize, False)
        if value != exact:
            try:
                residual = (exact - value).expand()
                nonconstant = bool(residual.free_symbols)
            except (AttributeError, TypeError):
                residual = f"unresolved({exact}) - ({value})"
                nonconstant = True
            skip_loss = evidence.preserve_source
            evidence.record(
                "phase_normalization", exact, value,
                nonconstant=nonconstant, applied=not skip_loss,
                detail=str(residual)[:320],
            )
            if skip_loss:
                return exact
    return value


def allow_omega_match(term, target):
    """Reject approximate omega matches when preserving original phase."""
    evidence = _CURRENT.get()
    if term == target:
        return True
    if evidence is None:
        return True
    skip_match = evidence.preserve_source
    evidence.record(
        "omega_coefficient_match", term, target,
        nonconstant=True, applied=not skip_match,
        detail=("Near-special omega match skipped to preserve source"
                if skip_match else "Near-special omega coefficient selected"),
    )
    return not skip_match


def record_approximate_omega(term, target):
    """Compatibility for standalone research callers capturing omega events."""
    evidence = _CURRENT.get()
    if evidence is not None and term != target:
        evidence.record(
            "omega_coefficient_match", term, target, nonconstant=True,
            applied=not evidence.preserve_source,
            detail="Near-special omega coefficient selected by RR tolerance",
        )
