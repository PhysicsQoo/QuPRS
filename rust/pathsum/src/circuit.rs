//! Native Rust circuit construction backed by the existing QuantumOp IR.
//! No Qiskit runtime, Python dependency, or float coercion is introduced.
use crate::{ir::QuantumOp, qasm, rational::Angle};
use anyhow::{bail, Result};
use std::path::Path;

/// Validated native `QuantumOp` gate-list input, **not** a symbolic
/// [`crate::PathSum`]. Verification converts gate lists to symbolic
/// Path-sums internally and exposes the residual via the result.
///
/// Supported QASM 2/3 decimal angles are preserved as exact rational
/// radian terms and supported `pi` factors remain symbolic in [`Angle`].
/// Rotation helpers take `Angle` values, not silently rounded `f64`.
/// Unsupported QASM operations cause parsing errors.
///
/// # Example
///
/// ```rust
/// use quprs::{rational::Angle, QuantumCircuit};
/// let angle = Angle::from_qasm_str("1.2345678901234567")?;
/// let mut direct = QuantumCircuit::new(1);
/// direct.rz(0, angle)?;
/// let parsed = QuantumCircuit::from_qasm_str(
///     "OPENQASM 3.0;\nqubit[1] q;\nrz(1.2345678901234567) q[0];\n"
/// )?;
/// assert_eq!(direct, parsed);
/// # Ok::<(), anyhow::Error>(())
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QuantumCircuit {
    num_qubits: usize,
    ops: Vec<QuantumOp>,
}

impl QuantumCircuit {
    /// Construct an empty circuit with a fixed register width.
    pub fn new(num_qubits: usize) -> Self {
        Self { num_qubits, ops: Vec::new() }
    }

    /// Validate and adopt an owned operation list without reallocation.
    ///
    /// Each operation is checked before the circuit can escape. The original
    /// allocation and exact Angle values are retained; validation is linear
    /// in gate count, but does not rebuild the operations Vec.
    pub fn from_ops(num_qubits: usize, ops: Vec<QuantumOp>) -> Result<Self> {
        let circuit = Self { num_qubits, ops };
        for op in &circuit.ops {
            circuit.validate(op)?;
        }
        Ok(circuit)
    }

    /// Strictly parse the supported OpenQASM 2/3 unitary subset.
    pub fn from_qasm_str(source: &str) -> Result<Self> {
        let (ops, n) = qasm::parse_qasm_str(source).map_err(anyhow::Error::msg)?;
        Self::from_ops(n, ops)
    }

    /// Strictly parse an OpenQASM file; reject unsupported operations.
    pub fn from_qasm_file(path: impl AsRef<Path>) -> Result<Self> {
        let (ops, n) = qasm::parse_file(path.as_ref()).map_err(anyhow::Error::msg)?;
        Self::from_ops(n, ops)
    }

    pub fn num_qubits(&self) -> usize {
        self.num_qubits
    }

    /// Borrow operations without cloning the existing source IR.
    pub fn operations(&self) -> &[QuantumOp] {
        &self.ops
    }

    pub fn len(&self) -> usize {
        self.ops.len()
    }

    pub fn is_empty(&self) -> bool {
        self.ops.is_empty()
    }

    /// Append an operation after bounds and distinct-operand validation.
    pub fn push(&mut self, op: QuantumOp) -> Result<&mut Self> {
        self.validate(&op)?;
        self.ops.push(op);
        Ok(self)
    }

    pub fn h(&mut self, qubit: usize) -> Result<&mut Self> {
        self.push(QuantumOp::H(qubit))
    }
    pub fn x(&mut self, qubit: usize) -> Result<&mut Self> {
        self.push(QuantumOp::X(qubit))
    }
    pub fn y(&mut self, qubit: usize) -> Result<&mut Self> {
        self.push(QuantumOp::Y(qubit))
    }
    pub fn z(&mut self, qubit: usize) -> Result<&mut Self> {
        self.push(QuantumOp::Z(qubit))
    }
    pub fn cx(&mut self, control: usize, target: usize) -> Result<&mut Self> {
        self.push(QuantumOp::CX(control, target))
    }
    pub fn cz(&mut self, control: usize, target: usize) -> Result<&mut Self> {
        self.push(QuantumOp::CZ(control, target))
    }
    /// The source Angle is preserved without conversion to f64.
    pub fn rz(&mut self, qubit: usize, theta: Angle) -> Result<&mut Self> {
        self.push(QuantumOp::RZ(qubit, theta))
    }
    pub fn rx(&mut self, qubit: usize, theta: Angle) -> Result<&mut Self> {
        self.push(QuantumOp::RX(qubit, theta))
    }
    pub fn ry(&mut self, qubit: usize, theta: Angle) -> Result<&mut Self> {
        self.push(QuantumOp::RY(qubit, theta))
    }

    fn check_wire(&self, qubit: usize) -> Result<()> {
        if qubit >= self.num_qubits {
            bail!("qubit index {qubit} is outside circuit width {}", self.num_qubits);
        }
        Ok(())
    }

    fn validate(&self, op: &QuantumOp) -> Result<()> {
        use QuantumOp::*;
        match op {
            H(q) | X(q) | Y(q) | Z(q) | S(q) | SDG(q) | T(q) | TDG(q)
            | P(q, _) | RX(q, _) | RY(q, _) | RZ(q, _)
            | U1(q, _) | U2(q, _, _) | U3(q, _, _, _) | U(q, _, _, _) => {
                self.check_wire(*q)
            }
            CX(control, target) | CZ(control, target) | SWAP(control, target) => {
                self.check_wire(*control)?;
                self.check_wire(*target)?;
                if control == target {
                    bail!("a two-qubit gate requires distinct operands");
                }
                Ok(())
            }
            CCX(c1, c2, target) => {
                self.check_wire(*c1)?;
                self.check_wire(*c2)?;
                self.check_wire(*target)?;
                if c1 == c2 || c1 == target || c2 == target {
                    bail!("CCX requires three distinct operands");
                }
                Ok(())
            }
            GlobalPhase(_) => Ok(()),
        }
    }
}
