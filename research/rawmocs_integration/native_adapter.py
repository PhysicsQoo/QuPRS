"""Experimental scoped in-process WMC transport; not a built-in backend."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from fractions import Fraction
import math

from QuPRS.utils.solver_adapter import (
    SolverCapabilities, SolverExecutionError, SolverResultError, registered_solver_adapter,
)
from QuPRS.utils.solver_process import SolverTimeout
from rawmocs_quprs import RawAdapter, SUPPORTED_DIGITS


class NativeFailure(SolverExecutionError):
    def __init__(self, error):
        self.kind = error.kind
        self.diagnostics = error.diagnostics
        super().__init__(str(error))


@dataclass(frozen=True)
class NativeAdapter(RawAdapter):
    token: object = field(default=None, repr=False, compare=False)

    def execute_native(self, cnf_path, timeout, *, capture_decimal):
        # Lazy optional import; existing GPMC/CLI paths have no native dependency.
        import rawmocs
        digits = int(self.arguments[1])
        budget_ms = min(86400000, math.floor(timeout * 1000))
        if budget_ms <= 0:
            raise SolverTimeout("Native budget exhausted before solve")
        try:
            result = rawmocs.solve_file(cnf_path, digits=digits, timeout_ms=budget_ms, token=self.token)
        except rawmocs.SolveError as exc:
            if exc.kind == "TIMEOUT":
                raise SolverTimeout(str(exc)) from exc
            raise NativeFailure(exc) from exc
        if result.digits != digits or result.precision_bits != {30:100,60:200,100:333,130:432}[digits]:
            raise SolverResultError("Native precision mismatch")
        status = "SATISFIABLE" if result.sat else "UNSATISFIABLE"
        text = f"s {status}\nc r mpfr {result.real} {result.imag}\n"
        sat, count = self.parse_protocol(text)
        for value, unit, binary in ((count.real, count.real_print_half_unit, result.real_binary),
                                    (count.imag, count.imag_print_half_unit, result.imag_binary)):
            if binary.precision_bits != result.precision_bits or abs(binary.exponent2) > 16384:
                raise SolverResultError("Native binary transport outside supported range")
            exact = Fraction(int(binary.significand)) * Fraction(2)**binary.exponent2
            if abs(exact - value) > unit:
                raise SolverResultError("Native binary/decimal mismatch")
        # Preserve existing printed-count semantics for matched CLI verdicts.
        # The binary value is checked, not advertised as an exact WMC certificate.
        return (count if capture_decimal else self.parse_output(text)), sat


@contextmanager
def registered_native(digits=30, *, token=None):
    if type(digits) is not int or digits not in SUPPORTED_DIGITS:
        raise ValueError("unsupported Native precision")
    adapter = NativeAdapter("rawmocs_native", ("--digits", str(digits)), SolverCapabilities("pair"), token=token)
    with registered_solver_adapter(adapter):
        yield adapter
