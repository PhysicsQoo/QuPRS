// src/pathsum/boolean_state.rs
use rustc_hash::FxHashSet;
use super::phase_poly::Monomial; 

#[derive(Clone, Debug)]
pub struct BooleanState {
    pub functions: Vec<FxHashSet<Monomial>>,
}

impl BooleanState {
    pub fn new(num_qubits: usize) -> Self {
        let mut functions = Vec::with_capacity(num_qubits);
        for i in 0..num_qubits {
            let mut poly = FxHashSet::default();
            poly.insert(vec![i as u32]);
            functions.push(poly);
        }
        Self { functions }
    }

    pub fn apply_xor(&mut self, control: usize, target: usize) {
        let ctrl_poly = self.functions[control].clone();
        let target_poly = &mut self.functions[target];
        for term in ctrl_poly {
            if target_poly.contains(&term) {
                target_poly.remove(&term);
            } else {
                target_poly.insert(term);
            }
        }
    }

    pub fn get_single_var(&self, qubit: usize) -> Option<u32> {
        let poly = &self.functions[qubit];
        if poly.len() == 1 {
            let term = poly.iter().next().unwrap();
            if term.len() == 1 { return Some(term[0]); }
        }
        None
    }
}