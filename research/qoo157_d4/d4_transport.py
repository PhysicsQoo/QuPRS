"""Strict, decimal-preserving transport for pinned d4 native counter stdout.

Research-only. The count is a finite printed observation, NOT an arithmetic
error certificate or a statement of global-phase equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

_LINE = re.compile(r"^c s exact arb (float|int)[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_REAL = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_COMPLEX = re.compile(rf"^({_REAL})((?:\+|-)(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)i$")
_MAX_TOKEN = 512
_MAX_EXPONENT = 2048


@dataclass(frozen=True)
class D4PrintedCount:
    real: Fraction
    imag: Fraction
    real_half_unit: Fraction
    imag_half_unit: Fraction
    format_name: str
    arithmetic_certified: bool = False


def _component(token: str, *, integer: bool = False) -> tuple[Fraction, Fraction]:
    if len(token) > _MAX_TOKEN:
        raise ValueError("d4 printed count token too long")
    if integer:
        if re.fullmatch(r"[+-]?\d+", token) is None:
            raise ValueError("invalid d4 integer printed count")
        return Fraction(int(token)), Fraction(0)
    if re.fullmatch(_REAL, token) is None:
        raise ValueError("non-finite or invalid d4 printed count")
    try:
        val = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError("malformed d4 decimal count") from exc
    if not val.is_finite() or abs(val.adjusted()) > _MAX_EXPONENT:
        raise ValueError("d4 printed count exponent outside bounded range")
    if val.is_zero():
        # Visible exact-zero token, not a proof of zero inside finite GMP.
        return Fraction(0), Fraction(0)
    # Conservative printed last-place half-unit only. Trimming digits at
    # the printer does not establish an internal arithmetic rounding bound.
    return Fraction(val), Fraction(5) * (Fraction(10) ** (val.as_tuple().exponent - 1))


def parse_d4_printed(stdout: str) -> D4PrintedCount:
    if len(stdout) > 1_048_576:
        raise ValueError("d4 stdout exceeds transport limit")
    matches = _LINE.findall(stdout)
    if not matches:
        raise ValueError("d4 output lacks a recognized arb float/int count")
    found = None
    for kind, printed in matches:
        raw = re.sub(r"\s+", "", printed)
        if kind == "int":
            real, ru = _component(raw, integer=True)
            imag, iu = Fraction(0), Fraction(0)
        elif raw.endswith("i"):
            pair = _COMPLEX.fullmatch(raw)
            if pair is None:
                raise ValueError("malformed d4 complex float count")
            real, ru = _component(pair.group(1))
            imag, iu = _component(pair.group(2))
        else:
            real, ru = _component(raw)
            imag, iu = Fraction(0), Fraction(0)
        new = D4PrintedCount(real, imag, ru, iu, f"c s exact arb {kind}")
        if found is not None and (found.real, found.imag) != (new.real, new.imag):
            raise ValueError("d4 output contains conflicting weighted counts")
        if found is None:
            found = new
        else:
            # Never select a less conservative printed-unit estimate.
            found = D4PrintedCount(
                real, imag, max(found.real_half_unit, ru),
                max(found.imag_half_unit, iu), found.format_name,
            )
    assert found is not None
    return found
