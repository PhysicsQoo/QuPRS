// src/ir.rs
use crate::pathsum::PathSum;
use crate::gates::{QuantumGates, Side};
use crate::rational::PhaseCoeff;

/// Intermediate Representation (IR) for quantum operations.
/// Pure data structure containing operation definitions.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum QuantumOp {
    // Single Qubit Gates
    H(usize),
    X(usize),
    Y(usize),
    Z(usize),
    S(usize),
    SDG(usize),
    T(usize),
    TDG(usize),

    // Two Qubit Gates
    CX(usize, usize),      // CNOT: Control, Target
    CZ(usize, usize),      // CZ: Control, Target
    SWAP(usize, usize),    // SWAP

    // Three Qubit Gates
    CCX(usize, usize, usize), // Toffoli: Ctrl1, Ctrl2, Target

    // Parameterized Gates
    P(usize, PhaseCoeff), // General phase gate
    RX(usize, PhaseCoeff),
    RY(usize, PhaseCoeff),
    RZ(usize, PhaseCoeff),
    
    // Universal single qubit gate
    U1(usize, PhaseCoeff), 
    U2(usize, PhaseCoeff, PhaseCoeff), 
    U3(usize, PhaseCoeff, PhaseCoeff, PhaseCoeff), // theta, phi, lam
    U(usize, PhaseCoeff, PhaseCoeff, PhaseCoeff), // theta, phi, lam
}

impl QuantumOp {
    /// Apply this operation to a PathSum circuit.
    /// 
    /// # Arguments
    /// * `ps` - Target PathSum circuit
    /// * `is_bra` - If true, apply as adjoint (Bra-side) operation
    pub fn apply(&self, ps: &mut PathSum, is_bra: bool) {
        let side = if is_bra { Side::Bra } else { Side::Ket };

        match self {
            Self::H(q) => ps.apply_h(*q, side),
            Self::X(q) => ps.apply_x(*q, side),
            Self::Y(q) => ps.apply_y(*q, side),
            Self::Z(q) => ps.apply_z(*q, side),
            Self::S(q) => ps.apply_s(*q, side),
            Self::SDG(q) => ps.apply_sdg(*q, side),
            Self::T(q) => ps.apply_t(*q, side),
            Self::TDG(q) => ps.apply_tdg(*q, side),
            
            Self::CX(c, t) => ps.apply_cx(*c, *t, side),
            Self::CZ(c, t) => ps.apply_cz(*c, *t, side),
            Self::SWAP(q1, q2) => {
                ps.apply_cx(*q1, *q2, side);
                ps.apply_cx(*q2, *q1, side);
                ps.apply_cx(*q1, *q2, side);
            },

            Self::CCX(c1, c2, t) => ps.apply_ccx(*c1, *c2, *t, side),
            
            Self::P(q, theta) => ps.apply_p(*q, theta.clone(), side),
            Self::RX(q, theta) => ps.apply_rx(*q, theta.clone(), side),
            Self::RY(q, theta) => ps.apply_ry(*q, theta.clone(), side),
            Self::RZ(q, theta) => ps.apply_rz(*q, theta.clone(), side),
            
            Self::U1(q, phi) => ps.apply_u1(*q, phi.clone(), side),
            Self::U2(q, phi, lam) => ps.apply_u2(*q, phi.clone(), lam.clone(), side),
            Self::U3(q, theta, phi, lam) => ps.apply_u3(*q, theta.clone(), phi.clone(), lam.clone(), side),
            Self::U(q, theta, phi, lam) => ps.apply_u(*q, theta.clone(), phi.clone(), lam.clone(), side)
        }
    }
}

