// rust/python_ffi/src/circuit.rs

use pyo3::prelude::*;
use pathsum::{ir::QuantumOp, PathSum, rational::{Angle, FreeRational}};

const PI: f64 = std::f64::consts::PI;
/// A Python-facing class to build quantum circuits programmatically.
#[pyclass]
#[derive(Clone)]
pub struct QuantumCircuit {
    #[pyo3(get)]
    pub num_qubits: usize,
    pub ops: Vec<QuantumOp>,
}

#[pymethods]
impl QuantumCircuit {
    #[new]
    pub fn new(num_qubits: usize) -> Self {
        Self {
            num_qubits,
            ops: Vec::new(),
        }
    }
    pub fn __repr__(&self) -> String {
        format!("<QuPRS.QuantumCircuit: {} qubits, {} gates>", self.num_qubits, self.ops.len())
    }

    pub fn __str__(&self) -> String {
        if self.ops.is_empty() {
            return "QuantumCircuit: (empty)".to_string();
        }

        let mut ps = PathSum::new(self.num_qubits);
        ps.set_auto_reduce(true);
        
        for op in &self.ops {
            op.apply(&mut ps, false);
        }
        ps.full_reduce(None);

        format!(
            "QuantumCircuit(qubits={})\n------------------\n{}",
            self.num_qubits,
            ps.print_status() 
        )
    }
    // ==========================================
    // Standard Clifford & Pauli Gates
    // ==========================================
    pub fn h(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::H(q)); slf }
    pub fn x(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::X(q)); slf }
    pub fn y(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::Y(q)); slf }
    pub fn z(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::Z(q)); slf }
    
    // Phase Gates
    pub fn s(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::S(q)); slf }
    pub fn sdg(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::SDG(q)); slf }
    pub fn t(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::T(q)); slf }
    pub fn tdg(mut slf: PyRefMut<'_, Self>, q: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::TDG(q)); slf } // 🌟 這裡修復了您的 Bug！

    // ==========================================
    // Parameterized Rotations
    // ==========================================
    pub fn rx(mut slf: PyRefMut<'_, Self>, q: usize, theta: f64) -> PyRefMut<'_, Self> {
        let phase = Angle::new_constant(FreeRational::from_f64(theta/PI));
        slf.ops.push(QuantumOp::RX(q, phase));
        slf
    }
    pub fn ry(mut slf: PyRefMut<'_, Self>, q: usize, theta: f64) -> PyRefMut<'_, Self> {
        let phase = Angle::new_constant(FreeRational::from_f64(theta/PI));
        slf.ops.push(QuantumOp::RY(q, phase));
        slf
    }
    pub fn rz(mut slf: PyRefMut<'_, Self>, q: usize, theta: f64) -> PyRefMut<'_, Self> {
        let phase = Angle::new_constant(FreeRational::from_f64(theta/PI));
        slf.ops.push(QuantumOp::RZ(q, phase));
        slf
    }
    pub fn u3(mut slf: PyRefMut<'_, Self>, q: usize, theta: f64, phi: f64, lam: f64) -> PyRefMut<'_, Self> {
        let p_theta = Angle::new_constant(FreeRational::from_f64(theta/PI));
        let p_phi = Angle::new_constant(FreeRational::from_f64(phi/PI));
        let p_lam = Angle::new_constant(FreeRational::from_f64(lam/PI));
        slf.ops.push(QuantumOp::U3(q, p_theta, p_phi, p_lam));
        slf
    }

    // ==========================================
    // Multi-Qubit Gates
    // ==========================================
    pub fn cx(mut slf: PyRefMut<'_, Self>, control: usize, target: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::CX(control, target)); slf }
    pub fn cz(mut slf: PyRefMut<'_, Self>, control: usize, target: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::CZ(control, target)); slf }
    pub fn ccx(mut slf: PyRefMut<'_, Self>, c1: usize, c2: usize, target: usize) -> PyRefMut<'_, Self> { slf.ops.push(QuantumOp::CCX(c1, c2, target)); slf }

}