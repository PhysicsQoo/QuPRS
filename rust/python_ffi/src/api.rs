// rust/python_ffi/src/api.rs

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::{PyDict, PyList};

use std::path::Path;
use std::time::Instant;

use pathsum::{
    check_equivalence_with_options as core_check_equivalence_with_options,
    VerificationOptions, VerificationMethod, VerificationStrategy, EquivalenceStatus,
    ir::QuantumOp, qasm,
};
use crate::circuit::QuantumCircuit;

#[pyclass]
pub struct PathSum;

#[pymethods]
impl PathSum {
    #[allow(non_snake_case)]
    #[staticmethod]
    pub fn QuantumCircuit(qubit_num: usize) -> QuantumCircuit {
        QuantumCircuit::new(qubit_num)
    }
}

fn extract_circuit(obj: &Bound<'_, PyAny>) -> PyResult<(Vec<QuantumOp>, usize)> {
    if let Ok(s) = obj.extract::<String>() {
        let path = Path::new(&s);
        if path.exists() {
            qasm::parse_file(path).map_err(|e| PyValueError::new_err(e))
        } else {
            qasm::parse_qasm_str(&s).map_err(|e| PyValueError::new_err(e))
        }
    } else if let Ok(qc) = obj.extract::<PyRef<'_, QuantumCircuit>>() {
        Ok((qc.ops.clone(), qc.num_qubits))
    } else {
        Err(PyTypeError::new_err("Input must be a QASM path, string, or QuantumCircuit."))
    }
}

#[pyfunction]
#[pyo3(signature = (circuit1, circuit2, method="hybrid", strategy="Difference", tool_name="gpmc", timeout=600, safe_mode=false, wmc_magnitude_tolerance=1e-8, wmc_phase_tolerance=1e-8, approximate_distance_tolerance=None))]
pub fn check_equivalence(
    circuit1: &Bound<'_, PyAny>,
    circuit2: &Bound<'_, PyAny>,
    method: &str,
    strategy: &str,
    tool_name: &str,
    timeout: u64,
    safe_mode: bool,
    wmc_magnitude_tolerance: f64,
    wmc_phase_tolerance: f64,
    approximate_distance_tolerance: Option<f64>,
) -> PyResult<PyObject> {
    // The Python safe_mode worker isolation has no Rust FFI equivalent.
    // Never silently claim that the requested isolation is active.
    if safe_mode {
        return Err(PyValueError::new_err(
            "safe_mode is not supported by the Rust backend"
        ));
    }
    if !wmc_magnitude_tolerance.is_finite() || wmc_magnitude_tolerance <= 0.0
        || wmc_magnitude_tolerance >= 1.0
        || !wmc_phase_tolerance.is_finite() || wmc_phase_tolerance <= 0.0
        || wmc_phase_tolerance >= 1.0
    {
        return Err(PyValueError::new_err(
            "WMC magnitude and phase tolerances must be finite in (0, 1)"
        ));
    }

    if let Some(eps) = approximate_distance_tolerance {
        if !eps.is_finite() || eps <= 0.0 || eps >= 1.0 {
            return Err(PyValueError::new_err(
                "approximate_distance_tolerance must be finite and in (0, 1)"
            ));
        }
        if wmc_magnitude_tolerance != 1e-8 {
            return Err(PyValueError::new_err(
                "approximate_distance_tolerance conflicts with nondefault wmc_magnitude_tolerance"
            ));
        }
    }
    // Diagnostics-only FFI phase clock: default results are unchanged.
    // This is an extra opt-in and deliberately does not affect solver timing.
    let ffi_clock_enabled = std::env::var("QUPRS_FFI_PHASE_TIMING")
        .ok().as_deref() == Some("1");
    let total_ffi_start = ffi_clock_enabled.then(Instant::now);
    let parse_start = ffi_clock_enabled.then(Instant::now);
    let (ops1, num_qubits1) = extract_circuit(circuit1)?;
    let (ops2, num_qubits2) = extract_circuit(circuit2)?;
    let qasm_extract_ns = parse_start.map(|start| start.elapsed().as_nanos() as u64);
    let system_qubits = std::cmp::max(num_qubits1, num_qubits2);

    if num_qubits1 != num_qubits2 {
        return Python::with_gil(|py| {
            let dict = PyDict::new_bound(py);
            dict.set_item("status", "Not Equivalent")?;
            dict.set_item("decision_basis", "structural")?;
            dict.set_item("approximate_distance_tolerance", approximate_distance_tolerance)?;
            dict.set_item("wmc_solver_invoked", false)?;
            dict.set_item("qubits", system_qubits)?;
            dict.set_item("gates1", ops1.len())?;
            dict.set_item("gates2", ops2.len())?;
            dict.set_item("verification_time_sec", 0.0)?;
            dict.set_item("pathsum_time_sec", 0.0)?;
            dict.set_item("final_ps", "N/A")?;
            dict.set_item("stats", PyDict::new_bound(py))?;
            Ok(dict.to_object(py))
        });
    }

    let rs_method = match method.to_lowercase().as_str() {
        "hybrid" => VerificationMethod::Hybrid,
        "reduction_rules" => VerificationMethod::ReductionRules,
        "wmc_only" => VerificationMethod::WmcOnly,
        _ => return Err(PyValueError::new_err(format!("Unknown method: {}", method))),
    };

    let rs_strategy = match strategy.to_lowercase().as_str() {
        "naive" => VerificationStrategy::Naive,
        "straightforward" => VerificationStrategy::Straightforward,
        "proportional" => VerificationStrategy::Proportional,
        "difference" => VerificationStrategy::Difference,
        _ => return Err(PyValueError::new_err(format!("Unknown strategy: {}", strategy))),
    };

    let tool_name_owned = tool_name.to_lowercase();

    let native_bridge_start = ffi_clock_enabled.then(Instant::now);
    let options = VerificationOptions {
        method: rs_method,
        strategy: rs_strategy,
        tool_name: tool_name_owned,
        timeout_secs: timeout,
        wmc_magnitude_tolerance,
        wmc_phase_tolerance,
        approximate_distance_tolerance,
    };
    let result = pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            core_check_equivalence_with_options(system_qubits, &ops1, &ops2, &options)
        })
    }).map_err(|e| PyValueError::new_err(format!("Verification Engine Failed: {}", e)))?;
    let native_bridge_ns = native_bridge_start.map(|start| start.elapsed().as_nanos() as u64);

    Python::with_gil(|py| {
        let dict_build_start = ffi_clock_enabled.then(Instant::now);
        let dict = PyDict::new_bound(py);
        
        let status_str = match &result.status {
            EquivalenceStatus::Equivalent => "Equivalent",
            EquivalenceStatus::EquivalentUpToGlobalPhase => "Equivalent (Up to Global Phase)",
            EquivalenceStatus::NotEquivalent => "Not Equivalent",
            EquivalenceStatus::Unknown => "Unknown",
            EquivalenceStatus::Timeout => "Timeout",
            EquivalenceStatus::MemoryOut => "MemoryOut",
        };

        dict.set_item("status", status_str)?;
        dict.set_item("decision_basis", result.decision_basis)?;
        dict.set_item("wmc_solver_invoked", result.solver_invoked)?;
        dict.set_item("wmc_printed_verdict", result.wmc_printed_verdict)?;
        dict.set_item("wmc_precision_reason", result.wmc_precision_reason)?;
        dict.set_item("approximate_distance_tolerance", result.approximate_distance_tolerance)?;
        if result.wmc_time.is_some() && result.solver_invoked {
            dict.set_item("wmc_numerical_verdict", result.status.to_string())?;
        }
        
        dict.set_item("qubits", result.qubit_num)?;
        dict.set_item("gates1", result.gate_num1)?;
        dict.set_item("gates2", result.gate_num2)?;
        dict.set_item("verification_time_sec", result.verification_time)?;
        dict.set_item("pathsum_time_sec", result.pathsum_time)?;
        
        dict.set_item("final_ps", result.final_ps.print_status())?;
        let stats_dict = PyDict::new_bound(py);
        // -- Record reduction rule statistics
        stats_dict.set_item("hh_hits", result.final_ps.stats.hh.successes)?;
        stats_dict.set_item("hh_attempts", result.final_ps.stats.hh.attempts)?;
        
        stats_dict.set_item("omega_hits", result.final_ps.stats.omega.successes)?;
        stats_dict.set_item("omega_attempts", result.final_ps.stats.omega.attempts)?;
        
        stats_dict.set_item("elim_hits", result.final_ps.stats.elim.successes)?;
        stats_dict.set_item("elim_attempts", result.final_ps.stats.elim.attempts)?;
        dict.set_item("stats", stats_dict)?;
        if let Some(wmc_time) = result.wmc_time {
            dict.set_item("wmc_time_sec", wmc_time)?;
            dict.set_item("wmc_dimacs_time_sec", result.to_dimacs_time.unwrap_or(0.0))?;
            dict.set_item("wmc_solver_time_sec", result.tool_time.unwrap_or(0.0))?;
        }
        let mut stage_materialize_ns = None;
        if let Some(ledger) = &result.stage_ledger {
            let stage_build_start = ffi_clock_enabled.then(Instant::now);
            let diagnostic = PyDict::new_bound(py);
            diagnostic.set_item("schema", ledger.schema)?;
            diagnostic.set_item("total_native_wall_seconds", ledger.total_native_wall_seconds)?;
            diagnostic.set_item("solver_child_spawns", ledger.solver_child_spawns)?;
            diagnostic.set_item("reduction_max_depth", ledger.reduction_max_depth)?;
            diagnostic.set_item("closure_error_seconds", ledger.closure_error_seconds)?;
            diagnostic.set_item("has_stage_overlap", ledger.has_stage_overlap)?;
            let seconds = PyDict::new_bound(py);
            for (name, value) in &ledger.seconds {
                seconds.set_item(*name, *value)?;
            }
            diagnostic.set_item("exclusive_seconds", seconds)?;
            let calls = PyDict::new_bound(py);
            for (name, count) in &ledger.calls {
                calls.set_item(*name, *count)?;
            }
            diagnostic.set_item("stage_calls", calls)?;
            let probes = PyList::empty_bound(py);
            for sample in &ledger.structural_elim_attempts {
                let item = PyDict::new_bound(py);
                item.set_item("k_r", sample.k_r)?;
                item.set_item("l_r", sample.l_r)?;
                item.set_item("v_r", sample.v_r)?;
                item.set_item("d_r", sample.d_r)?;
                item.set_item("w_redundant_estimated", sample.w_redundant_estimated)?;
                probes.append(item)?;
            }
            diagnostic.set_item("structural_elim_attempts", probes)?;
            // Preserve the v0 Stage Ledger JSON shape when the second opt-in
            // QUPRS_ELIM_TIMING flag is not explicitly set.
            if ledger.elim_timing_enabled {
                let timings = PyList::empty_bound(py);
                for sample in &ledger.elim_attempt_timings {
                    let item = PyDict::new_bound(py);
                    item.set_item("structural_index", sample.structural_index)?;
                    item.set_item("elapsed_ns", sample.elapsed_ns)?;
                    item.set_item("success", sample.success)?;
                    timings.append(item)?;
                }
                diagnostic.set_item("elim_attempt_timings", timings)?;
            }
            if ledger.other_rule_timing_enabled {
                let records = PyList::empty_bound(py);
                for sample in &ledger.other_rule_timings {
                    let item = PyDict::new_bound(py);
                    item.set_item("rule", sample.rule)?;
                    item.set_item("elapsed_ns", sample.elapsed_ns)?;
                    item.set_item("success", sample.success)?;
                    item.set_item("candidate_count", sample.candidate_count)?;
                    item.set_item("within_reduction", sample.within_reduction)?;
                    records.append(item)?;
                }
                diagnostic.set_item("other_rule_timings", records)?;
            }
            dict.set_item("stage_ledger", diagnostic)?;
            stage_materialize_ns = stage_build_start
                .map(|start| start.elapsed().as_nanos() as u64);
        }

        // This stamp is taken before materializing the phase metadata so that
        // the diagnostic dictionary does not inflate the conversion estimate.
        if let Some(total_start) = total_ffi_start {
            let dict_build_ns = dict_build_start
                .expect("FFI phase clock implies dictionary clock")
                .elapsed().as_nanos() as u64;
            // Sample the outer clock BEFORE emitting its own metadata.
            // Otherwise this value incorrectly includes phase dict insertion.
            let ffi_pre_metadata_ns = total_start.elapsed().as_nanos() as u64;
            let phase = PyDict::new_bound(py);
            phase.set_item("schema", "quprs-rust-ffi-phase-v1")?;
            phase.set_item("qasm_extract_ns", qasm_extract_ns.unwrap_or(0))?;
            phase.set_item("native_bridge_ns", native_bridge_ns.unwrap_or(0))?;
            phase.set_item("python_dict_build_ns", dict_build_ns)?;
            phase.set_item("stage_ledger_materialize_ns", stage_materialize_ns.unwrap_or(0))?;
            phase.set_item("ffi_elapsed_excluding_phase_metadata_ns",
                           ffi_pre_metadata_ns)?;
            dict.set_item("ffi_phase_timings", phase)?;
        }

        Ok(dict.to_object(py))
    })
}