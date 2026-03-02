// src/pathsum/boolean_state.rs
use rustc_hash::FxHashSet;
use super::phase_poly::Monomial; 

/// Represents a quantum register for mapping flattened indices to named qubits.
#[derive(Clone, Debug)]
pub struct Register {
    pub name: String,
    pub size: usize,
}

impl Register {
    pub fn new(name: &str, size: usize) -> Self {
        Self {
            name: name.to_string(),
            size,
        }
    }
}

#[derive(Clone, Debug)]
pub struct BooleanState {
    pub functions: Vec<FxHashSet<Monomial>>,
    pub registers: Vec<Register>,
}

impl BooleanState {
    /// Construct a BooleanState using explicit register definitions.
    /// This initializes each qubit's boolean function to its corresponding input variable x_i,
    /// preserving the generic unitary matrix representation.
    pub fn new_with_regs(regs: &[Register]) -> Self {
        let total_qubits: usize = regs.iter().map(|r| r.size).sum();
        let mut functions = Vec::with_capacity(total_qubits);
        
        for i in 0..total_qubits {
            let mut poly = FxHashSet::default();
            poly.insert(vec![i as u32]);
            functions.push(poly);
        }
        
        Self { 
            functions,
            registers: regs.to_vec(),
        }
    }

    /// Backward-compatible constructor that defaults to a single register named "q".
    pub fn new(num_qubits: usize) -> Self {
        Self::new_with_regs(&[Register::new("q", num_qubits)])
    }

    pub fn apply_xor_with_poly(&mut self, target: usize, poly: &FxHashSet<Monomial>) {
        let target_poly = &mut self.functions[target];
        
        for term in poly {
            if target_poly.contains(term) {
                target_poly.remove(term);
            } else {
                target_poly.insert(term.clone());
            }
        }
    }
    /// Apply XOR logic for CNOT gates and pure boolean operations.
    pub fn apply_xor(&mut self, control: usize, target: usize) {
        let ctrl_poly = self.functions[control].clone();
        self.apply_xor_with_poly(target, &ctrl_poly);
    }

    /// Extract the variable ID if the boolean function is a single linear variable.
    pub fn get_single_var(&self, qubit: usize) -> Option<u32> {
        let poly = &self.functions[qubit];
        if poly.len() == 1 {
            let term = poly.iter().next().unwrap();
            if term.len() == 1 { 
                return Some(term[0]); 
            }
        }
        None
    }
    pub fn get_used_vars(&self) -> FxHashSet<u32> {
        let mut used_vars = FxHashSet::default();
        for poly in &self.functions {
            for term in poly {
                used_vars.extend(term.iter().copied());
            }
        }
        used_vars
    }

    /// Format a flat qubit index into its physical register name (e.g., "|ancilla_0>").
    pub fn format_qubit_name(&self, mut flat_index: usize) -> String {
        for reg in &self.registers {
            if flat_index < reg.size {
                return format!("|{}_{}>", reg.name, flat_index);
            }
            flat_index -= reg.size;
        }
        format!("|q_{}>", flat_index) // Fallback for out-of-bounds mapping
    }
}