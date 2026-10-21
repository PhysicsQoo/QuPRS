// rust/python_ffi/src/api.rs

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::{PyDict, PyList};

use std::path::Path;

use pathsum::{
    check_equivalence as core_check_equivalence,
    VerificationMethod, VerificationStrategy, EquivalenceStatus,
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
#[pyo3(signature = (circuit1, circuit2, method="hybrid", strategy="Difference", tool_name="gpmc", timeout=600, safe_mode=false))]
pub fn check_equivalence(
    circuit1: &Bound<'_, PyAny>,
    circuit2: &Bound<'_, PyAny>,
    method: &str,
    strategy: &str,
    tool_name: &str,
    timeout: u64,
    safe_mode: bool,
) -> PyResult<PyObject> {
    let _ = safe_mode;

    let (ops1, num_qubits1) = extract_circuit(circuit1)?;
    let (ops2, num_qubits2) = extract_circuit(circuit2)?;
    let system_qubits = std::cmp::max(num_qubits1, num_qubits2);

    if num_qubits1 != num_qubits2 {
        return Python::with_gil(|py| {
            let dict = PyDict::new_bound(py);
            dict.set_item("status", "Not Equivalent")?;
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

    let result = pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            core_check_equivalence(system_qubits, &ops1, &ops2, rs_method, rs_strategy, &tool_name_owned, timeout)
        })
    }).map_err(|e| PyValueError::new_err(format!("Verification Engine Failed: {}", e)))?;

    Python::with_gil(|py| {
        let dict = PyDict::new_bound(py);
        
        let status_str = match result.status {
            EquivalenceStatus::Equivalent => "Equivalent",
            EquivalenceStatus::EquivalentUpToGlobalPhase => "Equivalent (Up to Global Phase)",
            EquivalenceStatus::NotEquivalent => "Not Equivalent",
            EquivalenceStatus::Unknown => "Unknown",
            EquivalenceStatus::Timeout => "Timeout",
            EquivalenceStatus::MemoryOut => "MemoryOut",
        };

        dict.set_item("status", status_str)?;
        
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
        if let Some(ledger) = &result.stage_ledger {
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
            dict.set_item("stage_ledger", diagnostic)?;
        }

        Ok(dict.to_object(py))
    })
}