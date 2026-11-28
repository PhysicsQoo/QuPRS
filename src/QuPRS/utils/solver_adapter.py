"""Independent WMC solver transports. Solver counts are numerical observations."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, ContextManager

from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS, parse_count_line
from QuPRS.utils.precision_count import PrintedCount, parse_printed_solver_output


class SolverExecutionError(RuntimeError):
    """The selected solver returned nonzero."""


class SolverResultError(ValueError):
    """The selected solver did not return a finite count."""


@dataclass(frozen=True)
class SolverCapabilities:
    weight_format: str
    complex_weights: bool = True
    exact_count_certificate: bool = False


@dataclass(frozen=True)
class SolverResult:
    solver_id: str
    count: complex | PrintedCount
    arguments: tuple[str, ...]
    returncode: int
    elapsed_seconds: float
    sat: bool | None = None


@dataclass(frozen=True)
class SolverAdapter:
    solver_id: str
    arguments: tuple[str, ...]
    capabilities: SolverCapabilities
    resource_factory: Callable[[], ContextManager] | None = field(default=None, repr=False)

    def resource(self, resolver):
        return self.resource_factory() if self.resource_factory else resolver(self.solver_id)

    def format_weights(self, real, imag):
        raise NotImplementedError("Solver must implement its weight grammar")

    def verify_binary(self, executable, timeout):
        pass

    def parse_output_precise(self, stdout):
        """Retain exact decimal text through the selected solver boundary.

        This is a printed-value observation, NOT a Solver error certificate.
        """
        try:
            return parse_printed_solver_output(stdout)
        except ValueError as exc:
            raise SolverResultError(str(exc)) from exc

    def parse_output(self, stdout):
        count = None
        for line in stdout.splitlines():
            parsed = parse_count_line(line)
            if parsed is not None:
                if count is not None and count != parsed:
                    raise SolverResultError(
                        f"{self.solver_id} WMC output contains conflicting counts"
                    )
                count = parsed
        if count is not None:
            return count
        raise SolverResultError(f"{self.solver_id} WMC output format error, result: {stdout}")


class GpmcAdapter(SolverAdapter):
    def format_weights(self, real, imag):
        return f"{real} {imag} 0", "1.0 0.0 0"


class GanakAdapter(SolverAdapter):
    def format_weights(self, real, imag):
        sign = "+" if imag >= 0 else "-"
        return f"{real} {sign} {abs(imag)}i 0", "1.0 + 0.0i 0"

    def verify_binary(self, executable, timeout):
        import os
        from QuPRS.utils.ganak_distribution import binary_diagnostics
        binary_diagnostics(
            executable, bool(os.environ.get("QUPRS_GANAK_PATH")),
            max(0.0, min(10.0, timeout)),
        )


class RawmocsPythonNativeAdapter(GpmcAdapter):
    """Experimental opt-in binding; no executable or subprocess required."""

    def _solve(self, source, timeout, *, capture_decimal, memory):
        import math
        from fractions import Fraction
        from QuPRS.utils.precision_count import _number_and_unit
        from QuPRS.utils.solver_process import SolverTimeout
        try:
            import rawmocs
        except ImportError as exc:
            raise SolverExecutionError(
                "RaWMoCS Python native backend requires the released rawmocs 0.3.0 package"
            ) from exc
        if rawmocs.__version__ != "0.3.0":
            raise SolverExecutionError("RaWMoCS Python native backend requires rawmocs 0.3.0")
        budget = min(86_400_000, math.floor(timeout * 1000))
        if budget <= 0:
            raise SolverTimeout("Native budget exhausted before solve")
        digits = 30
        try:
            solve = rawmocs.solve if memory else rawmocs.solve_file
            result = solve(source, digits=digits, timeout_ms=budget)
        except rawmocs.SolveError as exc:
            if exc.kind == "TIMEOUT":
                raise SolverTimeout(str(exc)) from exc
            error = SolverExecutionError(str(exc))
            error.kind = exc.kind
            error.diagnostics = exc.diagnostics
            raise error from exc
        if result.digits != digits or result.precision_bits != 100 or type(result.sat) is not bool:
            raise SolverResultError("Native precision or SAT status mismatch")
        if any("/" in x for x in (result.real, result.imag)):
            raise SolverResultError("Native decimal count required")
        try:
            real, ru = _number_and_unit(result.real)
            imag, iu = _number_and_unit(result.imag)
            for value, unit, binary in ((real, ru, result.real_binary),
                                        (imag, iu, result.imag_binary)):
                if binary.precision_bits != 100 or abs(binary.exponent2) > 16384:
                    raise ValueError("Native binary transport outside supported range")
                exact = Fraction(int(binary.significand)) * Fraction(2)**binary.exponent2
                if abs(exact - value) > unit:
                    raise ValueError("Native binary/decimal mismatch")
            if not result.sat and (real or imag):
                raise ValueError("Native UNSAT with nonzero count")
            if capture_decimal:
                return PrintedCount(real, imag, ru, iu, "rawmocs-mpfr"), result.sat
            re, im = float(real), float(imag)
            if not math.isfinite(re) or not math.isfinite(im):
                raise ValueError("Native count outside finite binary64 range")
            return complex(re, im), result.sat
        except (ValueError, OverflowError) as exc:
            raise SolverResultError(str(exc)) from exc

    def execute_native(self, cnf_path, timeout, *, capture_decimal):
        return self._solve(cnf_path, timeout, capture_decimal=capture_decimal, memory=False)

    def execute_native_text(self, cnf_text, timeout, *, capture_decimal):
        return self._solve(cnf_text, timeout, capture_decimal=capture_decimal, memory=True)


_BUILTINS = {
    "rawmocs_python_native": RawmocsPythonNativeAdapter("rawmocs_python_native", (), SolverCapabilities("pair")),
    "gpmc": GpmcAdapter("gpmc", SOLVER_ARGUMENTS["gpmc"], SolverCapabilities("pair")),
    "ganak": GanakAdapter("ganak", SOLVER_ARGUMENTS["ganak"], SolverCapabilities("complex-i")),
}
_EXTENSIONS = {}
_LOCK = RLock()


def get_solver_adapter(solver_id):
    with _LOCK:
        adapter = (_BUILTINS.get(solver_id) or _EXTENSIONS.get(solver_id)) if isinstance(solver_id, str) else None
    if adapter is None:
        raise ValueError(f"Unsupported solver: {solver_id}")
    return adapter


@contextmanager
def registered_solver_adapter(adapter):
    """Scoped third-solver registration; cannot override native solvers."""
    if not isinstance(adapter, SolverAdapter) or not isinstance(adapter.solver_id, str) or not adapter.solver_id:
        raise ValueError("Invalid solver adapter identity")
    with _LOCK:
        if adapter.solver_id in _BUILTINS or adapter.solver_id in _EXTENSIONS:
            raise ValueError(f"Solver already registered: {adapter.solver_id}")
        _EXTENSIONS[adapter.solver_id] = adapter
    try:
        yield adapter
    finally:
        with _LOCK:
            if _EXTENSIONS.get(adapter.solver_id) is adapter:
                del _EXTENSIONS[adapter.solver_id]


def execute_solver(adapter, cnf_path, timeout, *, resource_resolver, process_runner, capture_decimal=False, cnf_text=None):
    """Invoke the explicitly selected solver, preserving process supervision."""
    import time
    from QuPRS.utils.solver_process import SOLVER_ENV_LOCK, SolverTimeout
    started = time.monotonic()
    budget = float(timeout)

    def remaining():
        return max(0.0, budget - (time.monotonic() - started))

    if not SOLVER_ENV_LOCK.acquire(timeout=remaining()):
        raise SolverTimeout("SolverTimeout: expired while waiting for solver lock")
    try:
        if remaining() <= 0:
            raise SolverTimeout("SolverTimeout: budget exhausted before solver launch")
        if cnf_text is not None:
            native_text = getattr(adapter, "execute_native_text", None)
            if native_text is None:
                raise SolverExecutionError("Selected solver does not support memory CNF")
            count, sat = native_text(cnf_text, remaining(), capture_decimal=capture_decimal)
            return SolverResult(adapter.solver_id, count, adapter.arguments, 0,
                                time.monotonic() - started, sat)
        native = getattr(adapter, "execute_native", None)
        if native is not None:
            count, sat = native(cnf_path, remaining(), capture_decimal=capture_decimal)
            return SolverResult(adapter.solver_id, count, adapter.arguments, 0,
                                time.monotonic() - started, sat)
        with adapter.resource(resource_resolver) as executable:
            adapter.verify_binary(executable, remaining())
            if remaining() <= 0:
                raise SolverTimeout("SolverTimeout: budget exhausted before solver launch")
            command = [str(executable), *adapter.arguments, str(cnf_path)]
            output = process_runner(command, timeout=remaining())
    finally:
        SOLVER_ENV_LOCK.release()

    if output.returncode != 0:
        raise SolverExecutionError(
            f"{adapter.solver_id} failed: status={output.returncode}, "
            f"command={command!r}\nstdout={output.stdout}\nstderr={output.stderr}"
        )
    return SolverResult(
        adapter.solver_id, (adapter.parse_output_precise(output.stdout) if capture_decimal
                            else adapter.parse_output(output.stdout)),
        adapter.arguments, output.returncode, time.monotonic() - started,
    )
