// src/gates.rs 
use crate::pathsum::PathSum;
use crate::rational::{Rational, PhaseCoeff};
use crate::pathsum;

pub trait QuantumGates {
    fn apply_h(&mut self, qubit: usize);
    fn apply_cx(&mut self, control: usize, target: usize);
    // ... 
}

impl QuantumGates for PathSum {
    fn apply_cx(&mut self, control: usize, target: usize) {
        self.f.apply_xor(control, target);
    }

    fn apply_h(&mut self, qubit: usize) {
        let new_var = self.v.get_fresh_var();
        let new_var_mono = vec![new_var];

        let current_f_q = self.f.functions[qubit].clone();
        
        let half = PhaseCoeff::new_constant(Rational::new(1, 2));
        
        for term in current_f_q {
            let new_term = pathsum::mul_monomials(&term, &new_var_mono);
            self.p.add_term(new_term, half.clone());
        }

        let mut new_poly = rustc_hash::FxHashSet::default();
        new_poly.insert(new_var_mono);
        self.f.functions[qubit] = new_poly;
    }
    
    // ...
}