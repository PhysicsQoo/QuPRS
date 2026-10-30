import math
import signal
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
from qiskit import QuantumCircuit, qasm2, qasm3

from QuPRS import config
from QuPRS.utils.verification_tolerances import current_rr_tolerance, per_call_rr_tolerance
from QuPRS.interface.gate_library import gate_map, support_gate_set
from QuPRS.pathsum import PathSum, Register
from QuPRS.pathsum.statistics import StatisticsManager
from QuPRS.utils.verification_timeout import VerificationTimeout
from QuPRS.utils.solver_process import SolverTimeout
from QuPRS.utils.util import set_safe_memory_limit


def timeout_handler(signum, frame):
    raise VerificationTimeout("Operation timed out")



def build_circuit(circuit: QuantumCircuit, initial_state: bool | list | tuple = None):
    pathsum_circuit = initialize(circuit, initial_state)
    gate_list = get_gates(circuit)
    for gate in gate_list:
        assert gate[0] in support_gate_set, "Not support %s gate yet." % gate[0]
        # print(pathsum_circuit, gate)
        pathsum_circuit = gate_map(
            pathsum_circuit,
            gate[0],
            gate[1],
            gate[2],
        )

    return pathsum_circuit


def initialize(circuit: QuantumCircuit, initial_state: bool | list | tuple = None):
    """
    Construct initial PathSum and the name mapping.
    """
    qiskit_regs = circuit.qregs
    if not qiskit_regs:
        return PathSum.QuantumCircuit(
            Register(circuit.num_qubits, "q"), initial_state=initial_state
        )
    regs = [Register(reg.size, reg.name) for reg in qiskit_regs]
    return PathSum.QuantumCircuit(*regs, initial_state=initial_state)


def get_gate(circuit: QuantumCircuit, gate):
    """Get a gate properties."""
    gate_name = gate.operation.name
    gate_params = gate.operation.params
    qubits_old = gate.qubits
    qubits = []
    for qubit in qubits_old:
        qubits.append(circuit.find_bit(qubit).index)
    return gate_name, tuple(qubits), tuple(gate_params)


def get_gates(circuit: QuantumCircuit):
    gates = []
    for gate in circuit.data:
        gates.append(get_gate(circuit, gate))
    return gates


def add_gate(
    pathsum_circuit: PathSum, gate, is_bra=False, count=0, debug=False
) -> tuple[PathSum, int]:
    assert gate[0] in support_gate_set, "Not support %s gate yet." % gate[0]
    if debug:
        print(f"gate:{gate}, is_bra: {is_bra}")
    pathsum_circuit = gate_map(
        pathsum_circuit,
        gate[0],
        gate[1],
        gate[2],
        is_bra,
    )

    count += 1
    if debug:
        print(count, pathsum_circuit)
    return pathsum_circuit, count


def load_circuit(circuit: str) -> QuantumCircuit:
    """
    Load a Qiskit circuit from a file or qasm string.

    Args:
        circuit (str): The path to the QASM file or a QASM string.

    Returns:
        QuantumCircuit: The loaded Qiskit circuit.
    """
    if isinstance(circuit, str):
        if circuit.endswith(".qasm"):
            f = open(circuit, "r")
            data = f.read()
            if "OPENQASM 3.0" in data:
                return qasm3.load(circuit)
            else:
                return qasm2.load(circuit)
        elif "OPENQASM" in circuit:
            if "OPENQASM 3.0" in circuit:
                return qasm3.loads(circuit)
            else:
                return qasm2.loads(circuit)
        else:
            raise ValueError("Invalid circuit format")
    elif isinstance(circuit, QuantumCircuit):
        return circuit


def _validate_rust_qasm_global_phase_contract(circuit1, circuit2) -> None:
    """Reject relative scalar phases that the QASM2 Rust bridge cannot carry.

    Equal explicitly specified input phases cancel in the comparison and
    therefore may be omitted by the transport without changing either exact
    equality or equality up to global phase. Unequal scalar phases cannot
    safely be discarded when the public API distinguishes the two.
    """

    def phase_of(circuit) -> float:
        if not isinstance(circuit, QuantumCircuit):
            return 0.0
        try:
            phase = float(circuit.global_phase)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Rust backend requires a bound numeric QuantumCircuit.global_phase"
            ) from exc
        if not np.isfinite(phase):
            raise ValueError(
                "Rust backend requires a finite QuantumCircuit.global_phase"
            )
        return phase

    if phase_of(circuit1) != phase_of(circuit2):
        raise ValueError(
            "Rust QASM2 transport cannot preserve unequal "
            "QuantumCircuit.global_phase values. The exact-vs-global-phase "
            "equivalence classification would be unreliable."
        )


# =============================================================================
# check_equivalence: Unified Quantum Circuit Equivalence Checking Interface
# =============================================================================
# This function provides a unified interface for verifying the equivalence of two
# quantum circuits using various verification methods, including reduction rules,
# weighted model counting (WMC), or a hybrid approach. It is designed to be
# extensible and follows the documentation and code style conventions of this
# project. All lines are wrapped to comply with E501, and spacing follows E226.
# =============================================================================


@per_call_rr_tolerance
def check_equivalence(
    circuit1: str | QuantumCircuit,
    circuit2: str | QuantumCircuit,
    method: str = "hybrid",
    strategy: str = "Difference",
    tool_name: str = "gpmc",
    timeout: int = 600,
    safe_mode: bool = False,
    backend: str = "python",
    wmc_magnitude_tolerance: float | None = None,
    wmc_phase_tolerance: float | None = None,
    approximate_distance_tolerance: float | None = None,
    rr_tolerance: float | None = None,
    phase_tolerance: float | None = None,
):
    """
    Check whether two quantum circuits are equivalent using different verification
    methods.

    Args:
        circuit1 (str | QuantumCircuit): The first quantum circuit to compare. It can
            be a file path or a Qiskit circuit object.
        circuit2 (str | QuantumCircuit): The second quantum circuit to compare. It can
            be a file path or a Qiskit circuit object.
        method (str, optional): Verification method. Default is "hybrid".
            - 'hybrid': Uses both Reduction Rules (RR) and Weighted Model Counting
              (WMC). This is the recommended mode.
            - 'reduction_rules': Uses only Reduction Rules. If reduction is
              incomplete, returns 'unknown'.
            - 'wmc_only': Uses Weighted Model Counting (WMC), without
              reduction-rule matching. Python still normalizes phase
              coefficients while building the PathSum, but preserves
              small nonzero input phases rather than removing them
              using the local reduction tolerance.
        strategy (str, optional): Internal strategy for handling quantum gates.
            Default is "Difference".
            - 'Difference': Uses a difference-based strategy.
            - 'Proportional': Uses a proportional strategy.
            - 'Naive': Uses a naive strategy.
            - 'Straightforward': Uses a straightforward strategy.
        timeout (int, optional): Requested deadline in seconds (default 600).
            The external WMC subprocess consumes only the remaining monotonic
            budget. This is NOT a strict end-to-end wall-clock timeout for Rust
            in-process reduction/encoding or Python symbolic work on a
            non-main POSIX thread. Timeout returns a distinct "Timeout" status;
            solver process/parse failures raise exceptions and do not imply
            circuit inequivalence. See README "Solver subprocess reliability
            and timeout limits" for supported-platform and cleanup guarantees.
        safe_mode (bool, optional): If True, enables safe mode with memory limits by
            using multiple processes. Default is False.
        rr_tolerance (float | None): Per-call RR numerical coefficient matching.
            Defaults to 1e-10. Preserves small source phase terms.
        phase_tolerance (float | None): Phase zero classification in radians
            for RR and WMC; conflicts with a different wmc_phase_tolerance.
        wmc_magnitude_tolerance (float | None): Normalized WMC trace magnitude
            acceptance threshold. None uses config.WMC_MAGNITUDE_TOLERANCE.
            Independent of reduction tolerance and not a formal proof bound.
            Use rr_tolerance=... on each verification. Reduction caches
            include the per-call value in their cache key; there is no
            mutable process-global RR tolerance. This setting affects RR
            matching, not gate-source phase preservation.
        wmc_phase_tolerance (float | None): WMC phase threshold separating
            "equivalent" and "equivalent*" for near-unit magnitudes.
            None uses config.WMC_PHASE_TOLERANCE.
        approximate_distance_tolerance (float | None): Optional projective
            Hilbert-Schmidt distance threshold in (0, 1). None preserves
            existing numerical magnitude semantics. Near-boundary counts
            may return unknown; this is not a formal solver error certificate.
            A nondefault explicit WMC magnitude tolerance conflicts; an
            explicit 1e-8 is accepted but unused by the distance classifier.
            Python RR retains its existing tolerance semantics. Hybrid
            passes the final RR-reduced PathSum to WMC only if RR is inconclusive.

    Returns:
        EquivalenceCheckResult: An object containing the result dictionary and the
            final PathSum circuit object.
    """
    rr_tolerance = current_rr_tolerance()
    if phase_tolerance is not None:
        if wmc_phase_tolerance is not None and wmc_phase_tolerance != phase_tolerance:
            raise ValueError("phase_tolerance conflicts with wmc_phase_tolerance")
        wmc_phase_tolerance = phase_tolerance
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout must be a positive integer number of seconds")
    if approximate_distance_tolerance is not None:
        eps = approximate_distance_tolerance
        if (isinstance(eps, bool) or not isinstance(eps, (int, float))
            or not math.isfinite(eps) or not 0 < eps < 1):
            raise ValueError("approximate_distance_tolerance must be finite and in (0, 1)")
        if wmc_magnitude_tolerance is not None and wmc_magnitude_tolerance != 1e-8:
            raise ValueError("approximate_distance_tolerance conflicts with nondefault wmc_magnitude_tolerance")
        # The magnitude threshold is unused in distance mode. Do not inherit
        # mutable legacy defaults: the PyO3 and native Rust APIs use 1e-8.
        wmc_magnitude_tolerance = 1e-8
    elif wmc_magnitude_tolerance is None:
        wmc_magnitude_tolerance = config.WMC_MAGNITUDE_TOLERANCE
    if wmc_phase_tolerance is None:
        wmc_phase_tolerance = config.WMC_PHASE_TOLERANCE
    for name, threshold in (
        ("wmc_magnitude_tolerance", wmc_magnitude_tolerance),
        ("wmc_phase_tolerance", wmc_phase_tolerance),
    ):
        if (isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold) or not 0 < threshold < 1):
            raise ValueError(f"{name} must be finite and in (0, 1)")
    # Validate method argument
    if method not in ["hybrid", "reduction_rules", "wmc_only"]:
        raise ValueError(
            "Invalid method parameter. Choose from 'hybrid', "
            "'reduction_rules', or 'wmc_only'."
        )

    if backend == "rust":
        _validate_rust_qasm_global_phase_contract(circuit1, circuit2)
        request_started = time.monotonic()
        request_deadline = request_started + timeout
        from QuPRS import _pathsum_rust
        
        # Load circuits as QASM strings to pass to Rust if they are QuantumCircuits
        if isinstance(circuit1, QuantumCircuit):
            c1_input = qasm3.dumps(circuit1) if "OPENQASM 3.0" in getattr(circuit1, 'qasm', lambda: '')() else qasm2.dumps(circuit1)
        else:
            c1_input = circuit1
            
        if isinstance(circuit2, QuantumCircuit):
            c2_input = qasm3.dumps(circuit2) if "OPENQASM 3.0" in getattr(circuit2, 'qasm', lambda: '')() else qasm2.dumps(circuit2)
        else:
            c2_input = circuit2
        import os
        from QuPRS.utils import WMC, get_ganak_path
        from QuPRS.utils.solver_process import SOLVER_ENV_LOCK
        environment_key = f"QUPRS_{tool_name.upper()}_PATH"
        # Account for time spent serializing QASM AND waiting on the global
        # executable-override lock. A queued request must never get a fresh
        # full timeout budget after another verification finishes.
        acquired = SOLVER_ENV_LOCK.acquire(
            timeout=max(0.0, request_deadline - time.monotonic())
        )
        if not acquired:
            rust_res = {
                "status": "Timeout",
                "verification_time_sec": time.monotonic() - request_started,
            }
        else:
            try:
                # Rust core accepts whole seconds. Floor rather than round up
                # so that acquiring the lock does not extend the deadline.
                remaining = int(request_deadline - time.monotonic())
                if remaining < 1:
                    rust_res = {
                        "status": "Timeout",
                        "verification_time_sec": time.monotonic() - request_started,
                    }
                else:
                    previous_path = os.environ.get(environment_key)
                    # Keep resource extraction alive and never leak a temporary
                    # executable path into a later independent verification.
                    resource = get_ganak_path(verify=False) if tool_name == "ganak" else WMC(tool_name)
                    with resource as exe_path:
                        os.environ[environment_key] = str(exe_path)
                        try:
                            remaining = int(request_deadline - time.monotonic())
                            if remaining < 1:
                                rust_res = {
                                    "status": "Timeout",
                                    "verification_time_sec": time.monotonic() - request_started,
                                }
                            else:
                                rust_res = _pathsum_rust.check_equivalence(
                                    c1_input,
                                    c2_input,
                                    method=method,
                                    strategy=strategy,
                                    tool_name=tool_name,
                                    timeout=remaining,
                                    safe_mode=safe_mode,
                                    wmc_magnitude_tolerance=wmc_magnitude_tolerance,
                                    wmc_phase_tolerance=wmc_phase_tolerance,
                                    approximate_distance_tolerance=approximate_distance_tolerance,
                                    rr_tolerance=rr_tolerance,
                                    phase_tolerance=wmc_phase_tolerance,
                                )
                        finally:
                            if previous_path is None:
                                os.environ.pop(environment_key, None)
                            else:
                                os.environ[environment_key] = previous_path
            finally:
                SOLVER_ENV_LOCK.release()
        # Parse rust result dict into EquivalenceCheckResult
        # Handle string mappings
        equiv_map = {
            "Equivalent": "equivalent",
            "Equivalent (Up to Global Phase)": "equivalent*",
            "Not Equivalent": "not_equivalent",
            "Timeout": "Timeout",
            "MemoryOut": "MemoryOut",
        }
        mapped_equiv = equiv_map.get(rust_res.get("status"), "unknown")
        if rust_res.get("status") == "Unknown" and method == "reduction_rules":
            mapped_equiv = "unknown"
        elif rust_res.get("status") == "Unknown":
            mapped_equiv = "unknown"
            
        # WMC classification is numerical evidence, not an exact proof.
        rust_wmc_numerical_verdict = (
            rust_res.get("wmc_numerical_verdict")
            if rust_res.get("wmc_solver_time_sec") is not None
            and mapped_equiv in ("equivalent", "equivalent*", "not_equivalent", "unknown")
            else None
        )

        return EquivalenceCheckResult(
            qubit_num=rust_res.get("qubits", 0),
            gate_num=rust_res.get("gates1", 0),
            gate_num2=rust_res.get("gates2", 0),
            method=method,
            strategy=strategy,
            equivalent=mapped_equiv,
            verification_time=rust_res.get("verification_time_sec", 0.0),
            pathsum_time=rust_res.get("pathsum_time_sec", 0.0),
            final_pathsum=rust_res.get("final_ps", "N/A"),
            progress="N/A",  # Not tracked same way in rust
            Statistics=rust_res.get("stats", {}), # In python it's a StatisticsManager, but keeping dict for print compatibility
            to_DIMACS_time=rust_res.get("wmc_dimacs_time_sec"),
            tool_name=tool_name,
            tool_time=rust_res.get("wmc_solver_time_sec"),
            wmc_time=rust_res.get("wmc_time_sec"),
            CNF=None,
            expect=None,
            log_wmc=None,
            wmc_numerical_verdict=rust_wmc_numerical_verdict,
            wmc_magnitude_tolerance=wmc_magnitude_tolerance,
            wmc_phase_tolerance=wmc_phase_tolerance,
            approximate_distance_tolerance=approximate_distance_tolerance,
            decision_basis=rust_res.get("decision_basis"),
            wmc_printed_verdict=rust_res.get("wmc_printed_verdict"),
            wmc_precision_reason=rust_res.get("wmc_precision_reason"),
            wmc_solver_invoked=rust_res.get("wmc_solver_invoked"),
        )
    try:
        from QuPRS.utils.strategy import Strategy

        strategy_obj = Strategy.get(strategy)
    except ValueError as e:
        raise e


    start_time = time.time()
    deadline = time.monotonic() + timeout

    # Load circuits from file, QASM string, or QuantumCircuit
    qiskit_circuit1 = load_circuit(circuit1)
    qiskit_circuit2 = load_circuit(circuit2)

    if qiskit_circuit1.num_qubits != qiskit_circuit2.num_qubits:
        return EquivalenceCheckResult(
            qubit_num=max(qiskit_circuit1.num_qubits, qiskit_circuit2.num_qubits),
            gate_num=len(qiskit_circuit1.data),
            gate_num2=len(qiskit_circuit2.data),
            method=method,
            strategy=strategy,
            equivalent="not_equivalent",
            wmc_magnitude_tolerance=wmc_magnitude_tolerance,
            wmc_phase_tolerance=wmc_phase_tolerance,
            approximate_distance_tolerance=approximate_distance_tolerance,
            decision_basis="structural",
            wmc_solver_invoked=False,
            verification_time=0.0,
            pathsum_time=0.0,
            final_pathsum="N/A",
            progress="0/0",
            Statistics=StatisticsManager(),
            to_DIMACS_time=None,
            tool_name=tool_name,
            tool_time=None,
            wmc_time=None,
            CNF=(None,),
            expect=None,
            log_wmc=None,
        )

    # Initialize PathSum circuit and reduction switch
    initial_state = initialize(qiskit_circuit1)
    pathsum_circuit = initial_state
    reduction_enabled = method != "wmc_only"
    pathsum_circuit.set_reduction_switch(reduction_enabled)
    qubit_num = initial_state.num_qubits

    l1 = len(qiskit_circuit1.data)
    l2 = len(qiskit_circuit2.data)

    gates1 = get_gates(qiskit_circuit1)
    gates2 = get_gates(qiskit_circuit2)

    set_safe_memory_limit()
    # SIGALRM and ITIMER_REAL belong to the entire process, not QuPRS.
    # If an embedding application (or an outer nested check) has an active
    # timer, leave BOTH its handler and its countdown entirely untouched.
    # The solver subprocess still has its independent monotonic deadline.
    use_alarm = (
        hasattr(signal, "SIGALRM")
        and hasattr(signal, "getitimer")
        and threading.current_thread() is threading.main_thread()
        and signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    )
    previous_alarm_handler = None
    if use_alarm:
        previous_alarm_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

    try:
        to_DIMACS_time = None
        tool_time = None
        wmc_time = None
        CNF = (None,)
        log_wmc = None
        expect = None
        wmc_numerical_verdict = None
        wmc_solver_invoked = False
        rr_phase_label_accepted_by_tolerance = False
        wmc_precision_reason = None
        wmc_printed_verdict = None
        wmc_numeric_model_bound = None

        # Run the selected strategy to build the PathSum circuit
        pathsum_time = f">{timeout}"
        if safe_mode:
            elapsed_so_far = time.time() - start_time
            remaining_time = max(1, int(timeout - elapsed_so_far))
            pathsum_circuit = strategy_obj.safe_run(
                pathsum_circuit, gates1, gates2, timeout=remaining_time
            )
        else:
            pathsum_circuit = strategy_obj.run(pathsum_circuit, gates1, gates2)
        pathsum_time = round(time.time() - start_time, 3)
        progress = f"{strategy_obj.count}/{l1 + l2}"

        # Reduction rules check (if enabled)
        if method != "wmc_only":
            if pathsum_circuit.f == initial_state.f:
                if pathsum_circuit.P == initial_state.P:
                    equivalent = "equivalent"
                P_free_symbols = pathsum_circuit.P.free_symbols
                # check_P_symbol = tuple(
                #     filter(lambda x: x.name in pathsum_circuit.f.bits, P_free_symbols)
                # )
                if len(P_free_symbols) == 0:
                    # Phase coefficients are in cycles; compare wrapped radians.
                    cycles = float(pathsum_circuit.P.evalf()) % 1.0
                    phase = (cycles * math.tau) % math.tau
                    phase_is_within_tolerance = (
                        min(phase, math.tau - phase) < wmc_phase_tolerance
                    )
                    equivalent = (
                        "equivalent" if phase_is_within_tolerance
                        else "equivalent*"
                    )
                    rr_phase_label_accepted_by_tolerance = (
                        phase_is_within_tolerance
                        and pathsum_circuit.P != initial_state.P
                    )
                else:
                    equivalent = "unknown"
            elif len(pathsum_circuit.pathvar) == 0:
                # Strict non-equality alone does not establish D > epsilon.
                equivalent = ("unknown" if approximate_distance_tolerance is not None
                              else "not_equivalent")
            else:
                equivalent = "unknown"

        # Preserve the published hybrid algorithm: WMC consumes the final
        # RR residual only when reduction itself remains inconclusive.
        # Diagnostic tolerance events do not override RR's verdict.
        if method == "wmc_only" or (
            method == "hybrid" and equivalent == "unknown"
        ):
            from QuPRS.interface.ps2wmc import run_wmc, to_DIMACS
            from QuPRS.utils.wmc_solvers import classify_weighted_count

            current_elapsed = time.time() - start_time
            if current_elapsed >= timeout:
                raise VerificationTimeout("Timeout before WMC")
            if use_alarm:
                signal.alarm(int(timeout - current_elapsed + 1))
            temp_name = None
            try:
                to_DIMACS_time = f">{timeout - pathsum_time}"
                log_wmc = None
                theta = None
                expect = pathsum_circuit.num_qubits + pathsum_circuit.num_pathvar / 2
                import os
                import tempfile

                # Convert PathSum to CNF (DIMACS format)
                to_DIMACS_start_time = time.time()
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".cnf"
                ) as temp_file:
                    temp_name = temp_file.name
                    CNF = to_DIMACS(pathsum_circuit, temp_name, tool_name=tool_name)
                to_DIMACS_time = round(time.time() - to_DIMACS_start_time, 3)

                # Run weighted model counting (WMC)
                tool_time = f">{timeout - pathsum_time - to_DIMACS_time}"
                tool_start_time = time.time()
                wmc_solver_invoked = True
                if approximate_distance_tolerance is None:
                    complex_number = run_wmc(
                        temp_name, tool_name,
                        timeout=max(0.0, deadline - time.monotonic()),
                    )
                    equivalent, log_wmc = classify_weighted_count(
                        complex_number[0], complex_number[1], expect,
                        magnitude_tolerance=wmc_magnitude_tolerance,
                        phase_tolerance=wmc_phase_tolerance,
                    )
                else:
                    from QuPRS.utils.precision_count import (
                        classify_observed_distance, approximate_printed_log2,
                    )
                    # Exactly one selected external solver invocation per WMC.
                    # The -prec value is in decimal digits, not binary bits.
                    counted = run_wmc(
                        temp_name, tool_name,
                        timeout=max(0.0, deadline - time.monotonic()),
                        preserve_count=True,
                        precision_digits=90 if tool_name == "gpmc" else None,
                    )
                    twice = int(round(2 * expect))
                    if tool_name == "gpmc":
                        from QuPRS.utils.gpmc_cnf_metadata import (
                            gpmc_cnf_budget_metadata,
                        )
                        from QuPRS.utils.gpmc_distance_budget import (
                            classify_gpmc_single_count,
                        )
                        nvars, nweights, max_weight_sq = (
                            gpmc_cnf_budget_metadata(CNF)
                        )
                        budget = classify_gpmc_single_count(
                            counted,
                            expected_twice_log2=twice,
                            distance_tolerance=approximate_distance_tolerance,
                            phase_tolerance=wmc_phase_tolerance,
                            cnf_vars=nvars, number_of_weights=nweights,
                            maximum_weight_magnitude_squared=max_weight_sq,
                            precision_digits=90,
                        )
                        equivalent = budget.status
                        wmc_printed_verdict = budget.printed_status
                        wmc_precision_reason = budget.reason
                        wmc_numeric_model_bound = budget.component_error
                    else:
                        # Ganak mode-6 may expose only nine significant
                        # printed digits; unresolved precision stays unknown.
                        equivalent, evidence = classify_observed_distance(
                            counted, twice, approximate_distance_tolerance,
                            wmc_phase_tolerance,
                        )
                        wmc_printed_verdict = evidence.status
                        wmc_precision_reason = (
                            "ganak_printed_uncertified_" + evidence.reason
                        )
                    log_wmc = approximate_printed_log2(counted)
                tool_time = round(time.time() - tool_start_time, 3)
                # Preserve the numeric verdict as an observation. It is not
                # an independent proof of source-exact equivalence.
                wmc_numerical_verdict = equivalent
                wmc_time = tool_time + to_DIMACS_time
            finally:
                # Always clean up the CNF even on solver timeout/error or
                # malformed output. Full CNF retention is not the default.
                if temp_name and os.path.exists(temp_name):
                    os.remove(temp_name)
                if use_alarm:
                    signal.alarm(0)
        Time = round(time.time() - start_time, 3)

    except (VerificationTimeout, SolverTimeout):
        Time = f">{timeout}"
        equivalent = "Timeout"
        progress = f"{strategy_obj.count}/{l1 + l2}"
        if use_alarm:
            signal.alarm(0)
    except MemoryError:
        Time = round(time.time() - start_time, 3)
        if pathsum_time == f">{timeout}":
            pathsum_time = Time
        equivalent = "MemoryOut"
        progress = f"{strategy_obj.count}/{l1 + l2}"
        if use_alarm:
            signal.alarm(0)
    except Exception as e:
        if use_alarm:
            signal.alarm(0)
        raise e
    finally:
        if use_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_alarm_handler)

    # Return result as a dataclass object
    Result = EquivalenceCheckResult(
        # Circuit information
        qubit_num=qubit_num,
        gate_num=l1,
        gate_num2=l2,
        # Method and strategy
        method=method,
        strategy=strategy,
        # Result
        equivalent=equivalent,
        verification_time=Time,
        pathsum_time=pathsum_time,
        final_pathsum=pathsum_circuit,
        progress=progress,
        Statistics=pathsum_circuit._stats,
        # If method runs WMC, then to_DIMACS_time and tool_time are not None
        to_DIMACS_time=to_DIMACS_time,
        tool_name=tool_name,
        tool_time=tool_time,
        wmc_time=wmc_time,
        CNF=CNF,
        expect=expect,
        log_wmc=log_wmc,
        wmc_numerical_verdict=wmc_numerical_verdict,
        wmc_solver_invoked=wmc_solver_invoked,
        wmc_precision_reason=wmc_precision_reason,
        wmc_printed_verdict=wmc_printed_verdict,
        wmc_numeric_model_bound=wmc_numeric_model_bound,
        approximate_distance_tolerance=approximate_distance_tolerance,
        decision_basis=("numerical_approximate" if approximate_distance_tolerance is not None and tool_time is not None
                        and equivalent in ("equivalent", "equivalent*", "not_equivalent")
                        else "numerical_legacy" if tool_time is not None and approximate_distance_tolerance is None
                        and equivalent in ("equivalent", "equivalent*", "not_equivalent")
                        else "inconclusive" if equivalent == "unknown"
                        else "symbolic_phase_tolerance" if tool_time is None
                        and rr_phase_label_accepted_by_tolerance
                        and equivalent == "equivalent"
                        else "symbolic" if tool_time is None and equivalent in ("equivalent", "equivalent*", "not_equivalent")
                        else None),
        wmc_magnitude_tolerance=wmc_magnitude_tolerance,
        wmc_phase_tolerance=wmc_phase_tolerance,
    )
    return Result


@dataclass(repr=False)
class EquivalenceCheckResult:
    """
    Dataclass for storing the result of quantum circuit equivalence checking.

    Attributes:
        qubit_num (int): Number of qubits in the circuit.
        gate_num (int): Number of gates in the first circuit.
        gate_num2 (int): Number of gates in the second circuit.
        method (str): Verification method used.
        strategy (str): Strategy used for gate handling.
        equivalent (str): Result of the equivalence check.
        verification_time (float): Total verification time in seconds.
        pathsum_time (float): Time spent on PathSum computation.
        final_pathsum (PathSum): Final PathSum circuit object.
        Statistics (StatisticsManager): Statistics for the computation.
        progress (str): Progress string (e.g., "N/M").
        to_DIMACS_time (Optional[float]): Time for CNF conversion.
        tool_name (Optional[str]): Name of the WMC tool used (if applicable).
        tool_time (Optional[float]): Time for weighted model counting.
        wmc_time (Optional[float]): Total WMC time.
        CNF (Optional[str]): CNF representation (if generated).
    """

    # Circuit information
    qubit_num: int
    gate_num: int
    gate_num2: int
    # Method and strategy
    method: str
    strategy: str
    # Result
    equivalent: str
    verification_time: float | str
    pathsum_time: float | str
    final_pathsum: PathSum
    Statistics: StatisticsManager
    progress: str = "0/0"
    # If method runs WMC, then to_DIMACS_time and tool_time are not None
    to_DIMACS_time: Optional[float] = None
    tool_name: Optional[str] = None
    tool_time: Optional[float | str] = None
    wmc_time: Optional[float | str] = None
    CNF: Optional[str] = None
    expect: Optional[float] = None
    log_wmc: Optional[float] = None
    # Numerical solver verdict is diagnostic, not an exact-equivalence proof.
    wmc_numerical_verdict: Optional[str] = None
    # Numerical GPMC error-model diagnostics; NOT a formal proof certificate.
    wmc_precision_reason: Optional[str] = None
    wmc_printed_verdict: Optional[str] = None
    wmc_numeric_model_bound: Optional[str] = None
    approximate_distance_tolerance: Optional[float] = None
    decision_basis: Optional[str] = None
    # For Rust WMC: distinguish an actual solver process from an analytic shortcut.
    wmc_solver_invoked: Optional[bool] = None
    # Effective thresholds recorded for reproducible numerical verdicts.
    wmc_magnitude_tolerance: float | None = None
    wmc_phase_tolerance: float | None = None

    @staticmethod
    def _fmt(val: float | str | None) -> str:
        """
        Unified formatting logic:
        1. If the value is a number (float/int) -> format to .3f (without unit)
        2. If the value is None -> return 'N/A'
        3. If the value is something else (e.g., error string)
            -> return the original string
        """
        if val is None:
            return "N/A"
        if isinstance(val, (int, float)):
            return f"{val:.3f}"
        return str(val)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__

        return (
            f"{class_name}(result={self.equivalent}, "
            f"method={self.method}, "
            f"time={self._fmt(self.verification_time)}s)"
        )

    def __str__(self) -> str:
        f = self._fmt
        lines = [
            "Equivalence Check Result",
            "-----------circuit information---------",
            f"  Qubits: {self.qubit_num}",
            f"  Gates:  {self.gate_num}",
            f"  Gates2: {self.gate_num2}",
            "-----------method and strategy---------",
            f"  Method: {self.method}",
            f"  Strategy: {self.strategy}",
            "-----------result----------------------",
            f"  Equivalent: {self.equivalent}",
            "-----------verification time-----------",
            f"  PathSum Time:   {f(self.pathsum_time)} s",
            f"  to_DIMACS Time: {f(self.to_DIMACS_time)} s",
            f"  tool Time:      {f(self.tool_time)} s",
            f"  wmc Time:       {f(self.wmc_time)} s",
            f"  Total Time:     {f(self.verification_time)} s",
            "-----------final pathsum circuit-------",
            f"  {self.final_pathsum}",
            "-----------statistics------------------",
            f"  {self.Statistics}",
            "-----------progress--------------------",
            f"  {self.progress}",
            "-----------CNF------------------------",
            f"  {self.CNF if self.CNF is not None else 'N/A'}",
            "-----------expect---------------------",
            f"  {self.expect if self.expect is not None else 'N/A'}",
            "-----------log_wmc--------------------",
            f"  {self.log_wmc if self.log_wmc is not None else 'N/A'}",
            "-----------tool name------------------",
            f"  {self.tool_name if self.tool_name is not None else 'N/A'}",
        ]
        return "\n".join(lines)
