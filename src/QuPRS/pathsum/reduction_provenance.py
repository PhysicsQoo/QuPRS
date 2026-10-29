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

    def record(self, kind, before, after, *, nonconstant, detail=None):
        self.total_events += 1
        if nonconstant:
            self.unbounded = True
        if len(self.events) < _MAX_EVENTS:
            self.events.append({
                "kind": kind,
                "before": str(before)[:320],
                "after": str(after)[:320],
                "nonconstant": bool(nonconstant),
                "error_bound_certified": False,
                "detail": detail,
            })


@contextmanager
def capture_rr_provenance():
    """Capture evidence per verification, without process-global solver state."""
    evidence = RRProvenance()
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
            evidence.record(
                "phase_normalization", exact, value,
                nonconstant=nonconstant, detail=str(residual)[:320],
            )
    return value


def record_approximate_omega(term, target):
    evidence = _CURRENT.get()
    if evidence is not None and term != target:
        evidence.record(
            "omega_coefficient_match", term, target, nonconstant=True,
            detail="Near-special omega coefficient selected by RR tolerance",
        )
