"""Independent WMC solver transports. Solver counts are numerical observations."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, ContextManager

from QuPRS.utils.wmc_solvers import SOLVER_ARGUMENTS, parse_count_line


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
    count: complex
    arguments: tuple[str, ...]
    returncode: int
    elapsed_seconds: float


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


_BUILTINS = {
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


def execute_solver(adapter, cnf_path, timeout, *, resource_resolver, process_runner):
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
        adapter.solver_id, adapter.parse_output(output.stdout),
        adapter.arguments, output.returncode, time.monotonic() - started,
    )
