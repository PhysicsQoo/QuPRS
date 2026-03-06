// rust-test/python_ffi/src/lib.rs
use pyo3::prelude::*;

#[pyfunction]
fn hello_from_quprs() -> PyResult<String> {
    Ok("Hello from QuPRS Core Engine!".to_string())
}

#[pymodule]
fn pathsum(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_from_quprs, m)?)?;
    Ok(())
}