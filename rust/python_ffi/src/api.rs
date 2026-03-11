// rust/python_ffi/src/api.rs

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::PyDict;

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
    let _ = tool_name;
    let _ = safe_mode;

    let (ops1, num_qubits1) = extract_circuit(circuit1)?;
    let (ops2, num_qubits2) = extract_circuit(circuit2)?;
    let system_qubits = std::cmp::max(num_qubits1, num_qubits2);

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

    let result = pyo3::Python::with_gil(|py| {
        py.allow_threads(|| {
            core_check_equivalence(system_qubits, &ops1, &ops2, rs_method, rs_strategy, timeout)
        })
    }).map_err(|e| PyValueError::new_err(format!("Verification Engine Failed: {}", e)))?;

    Python::with_gil(|py| {
        let dict = PyDict::new_bound(py);
        
        let status_str = match result.status {
            EquivalenceStatus::Equivalent => "Equivalent",
            EquivalenceStatus::EquivalentUpToGlobalPhase => "Equivalent (Up to Global Phase)",
            EquivalenceStatus::NotEquivalent => "Not Equivalent",
            _ => "Unknown",
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

        Ok(dict.to_object(py))
    })
}