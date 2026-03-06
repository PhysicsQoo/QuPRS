// rust/python_ffi/src/lib.rs

mod circuit;
mod api;

use pyo3::prelude::*;
use api::check_equivalence;

/// The Python module initialization point.
/// The function name must match the module name specified in Cargo.toml/pyproject.toml.
#[pymodule]
fn pathsum_rust(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register the components from our submodules
    m.add_class::<circuit::QuantumCircuit>()?;
    m.add_class::<api::PathSum>()?;
    m.add_function(wrap_pyfunction!(check_equivalence, m)?)?;
    
    Ok(())
}