// src/gates.rs
use rustc_hash::{FxHashSet};
use crate::pathsum::PathSum;
use crate::rational::Rational;


/// Define a Trait containing all quantum gate operations
pub trait QuantumGates {
    fn apply_h(&mut self, qubit: usize);
    fn apply_cx(&mut self, control: usize, target: usize);
}

/// Implement this Trait for PathSum
impl QuantumGates for PathSum {
    fn apply_h(&mut self, qubit: usize) {
        // 1. Allocate new variable (now considered as y_i)
        let new_var = self.get_fresh_var();
        let new_var_mono = vec![new_var];

        // 2. Update phase P += (1/2) * F[q] * y
        let current_f_q = self.boolean_functions[qubit].clone();
        let half = Rational::new(1, 2);

        for term in current_f_q {
            let new_term = Self::mul_monomials(&term, &new_var_mono);
            self.add_phase(new_term, half);
        }

        // 3. F[q] = y
        let mut new_poly = FxHashSet::default();
        new_poly.insert(new_var_mono);
        self.boolean_functions[qubit] = new_poly;
    }
    fn apply_cx(&mut self, control: usize, target: usize) {
        let ctrl_poly = self.boolean_functions[control].clone();
        let target_poly = &mut self.boolean_functions[target];

        for term in ctrl_poly {
            if target_poly.contains(&term) {
                target_poly.remove(&term);
            } else {
                target_poly.insert(term);
            }
        }
    }

}