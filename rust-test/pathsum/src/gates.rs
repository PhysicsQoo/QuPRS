// src/gates.rs
use crate::pathsum::PathSum;
use crate::rational::{Rational, FreeRational, PhaseCoeff};
use crate::pathsum::{self, Monomial};
use rustc_hash::FxHashSet;

pub trait QuantumGates {
    // Basic Pauli Gates
    fn apply_x(&mut self, qubit: usize);
    fn apply_y(&mut self, qubit: usize);
    fn apply_z(&mut self, qubit: usize);
    
    // Clifford Gates
    fn apply_h(&mut self, qubit: usize);
    fn apply_s(&mut self, qubit: usize);
    fn apply_sdg(&mut self, qubit: usize);
    fn apply_cx(&mut self, control: usize, target: usize);
    fn apply_cz(&mut self, control: usize, target: usize);
    fn apply_ccx(&mut self, control1: usize, control2: usize, target: usize);

    // Non-Clifford Gates
    fn apply_t(&mut self, qubit: usize);
    fn apply_tdg(&mut self, qubit: usize);
}

impl PathSum {
    pub(crate) fn add_global_phase(&mut self, phase: PhaseCoeff) {
        if !phase.is_zero() {
            self.p.add_term(vec![], phase);
        }
    }
    pub(crate) fn apply_phase_to_poly(&mut self, poly: &FxHashSet<Monomial>, phase: PhaseCoeff) {
        if poly.is_empty() { return; }

        let denom_u64 = phase.constant.denom as u64;
        let max_order = if !phase.symbols.is_empty() {
            usize::MAX
        } else {
            if denom_u64.is_power_of_two() {
                denom_u64.trailing_zeros() as usize
            } else {
                usize::MAX
            }
        };

        let arith_poly = crate::pathsum::phase_poly::expand_xor_to_arithmetic(poly, max_order);

        for (term, coeff) in arith_poly {
            let final_coeff = phase.clone() * coeff;
            self.p.add_term(term, final_coeff); 
        }
    }

    pub(crate) fn apply_phase_gate(&mut self, qubit: usize, phase: PhaseCoeff) {
        let poly = self.f.functions[qubit].clone();
        self.apply_phase_to_poly(&poly, phase);
    }
}

impl QuantumGates for PathSum {
    // ==========================================
    // Pauli Gates
    // ==========================================
    fn apply_x(&mut self, qubit: usize) {
        // X gate is equivalent to XOR 1 in F[q]. In our system, 1 is the empty monomial vec![]
        let one = vec![];
        if self.f.functions[qubit].contains(&one) {
            self.f.functions[qubit].remove(&one);
        } else {
            self.f.functions[qubit].insert(one);
        }
    }

    fn apply_z(&mut self, qubit: usize) {
        self.apply_phase_gate(qubit, PhaseCoeff::new_constant(Rational::new(1, 2)));
    }

    fn apply_y(&mut self, qubit: usize) {
        // Y = i * X * Z
        // 1. Add global phase i (i.e., 1/4)
        self.add_global_phase(PhaseCoeff::new_constant(Rational::new(1, 4)));
        // 2. Apply Z and X in sequence
        self.apply_z(qubit);
        self.apply_x(qubit);
    }

    // ==========================================
    // Clifford Gates
    // ==========================================
    

    fn apply_h(&mut self, qubit: usize) {
        let new_var = self.v.get_fresh_var();
        let new_var_mono = vec![new_var];

        let mut y_poly = FxHashSet::default();
        y_poly.insert(new_var_mono.clone());
        // adds phase 1/2 * F_q * Y
        let product_poly = pathsum::mul_boolean_polys(&self.f.functions[qubit], &y_poly);
        self.apply_phase_to_poly(&product_poly, PhaseCoeff::new_constant(Rational::new(1, 2)));

        self.f.functions[qubit] = y_poly;

        if self.auto_reduce {
            self.full_reduce();
        }
    }

    fn apply_s(&mut self, qubit: usize) {
        self.apply_phase_gate(qubit, PhaseCoeff::new_constant(Rational::new(1, 4)));
    }

    fn apply_sdg(&mut self, qubit: usize) {
        self.apply_phase_gate(qubit, PhaseCoeff::new_constant(Rational::new(3, 4)));
    }

    fn apply_cx(&mut self, control: usize, target: usize) {
        self.f.apply_xor(control, target);
        if self.auto_reduce {
            self.full_reduce();
        }
    }

    fn apply_cz(&mut self, control: usize, target: usize) {
        // CZ adds phase 1/2 * (F[ctrl] * F[tgt])
        let poly_c = &self.f.functions[control];
        let poly_t = &self.f.functions[target];

        let product_poly = pathsum::mul_boolean_polys(poly_c, poly_t);
        self.apply_phase_to_poly(&product_poly, PhaseCoeff::new_constant(Rational::new(1, 2)));
    }

    fn apply_ccx(&mut self, control1: usize, control2: usize, target: usize) {
        let poly_c1 = &self.f.functions[control1];
        let poly_c2 = &self.f.functions[control2];

        // Apply the Toffoli transformation: F[target] = F[target] XOR (F[ctrl1] AND F[ctrl2])
        let product_poly = pathsum::mul_boolean_polys(poly_c1, poly_c2);

        self.f.apply_xor_with_poly(target, &product_poly);

        if self.auto_reduce {
            self.full_reduce();
        }
    }

    // ==========================================
    // T Gates
    // ==========================================
    fn apply_t(&mut self, qubit: usize) {
        self.apply_phase_gate(qubit, PhaseCoeff::new_constant(Rational::new(1, 8)));
    }

    fn apply_tdg(&mut self, qubit: usize) {
        self.apply_phase_gate(qubit, PhaseCoeff::new_constant(Rational::new(7, 8)));
    }
    // ==========================================
    // Rotation Gates
    // ==========================================
}


#[cfg(test)]
mod tests {
    use super::*;

    /// Helper function: creates a test PathSum with auto_reduce disabled to verify exact algebraic state
    fn setup_test_env(num_qubits: usize) -> PathSum {
        let mut ps = PathSum::new(num_qubits);
        ps.auto_reduce = false; // Disable auto-reduce to inspect raw expansion state
        ps
    }

    #[test]
    fn test_apply_x_and_z() {
        let mut ps = setup_test_env(1);
        
        // Test X gate (XOR 1)
        ps.apply_x(0);
        let one = vec![];
        assert!(ps.f.functions[0].contains(&one), "X gate should add empty vec (1) to F");
        assert!(ps.f.functions[0].contains(&vec![0]), "Original x0 should still be in F");

        // Test Z gate (Phase 1/2)
        ps.apply_z(0);
        assert!(ps.p.terms[&vec![0]].is_pure_half(), "Z gate should add 1/2 phase to x0");
        // Note: Since F[0] now becomes x0 ⊕ 1, Z gate also adds 1/2 phase to constant term (vec![])
        assert!(ps.p.terms[&one].is_pure_half(), "Z gate should add 1/2 phase to the constant term");
    }

    #[test]
    fn test_apply_y() {
        let mut ps = setup_test_env(1);
        ps.apply_y(0);
        
        // Y = iXZ. Expected: global phase 1/4, Z phase 1/2 * x0, F[0] becomes x0 ⊕ 1
        let one = vec![];
        assert!(ps.p.terms[&one].is_pure_quarter(), "Y gate should add global phase 1/4");
        assert!(ps.p.terms[&vec![0]].is_pure_half(), "Y gate should add 1/2 phase to x0");
        assert!(ps.f.functions[0].contains(&one), "Y gate should flip F");
    }

    #[test]
    fn test_apply_s_and_sdg() {
        let mut ps = setup_test_env(1);
        ps.apply_s(0);
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "S gate should add 1/4 phase");

        // Sdg should cancel out S
        ps.apply_sdg(0); 
        assert!(ps.p.terms.is_empty(), "S and Sdg should cancel each other out (Modulo 1)");
    }

    #[test]
    fn test_apply_t_and_tdg() {
        let mut ps = setup_test_env(1);
        ps.apply_t(0);
        assert!(ps.p.terms[&vec![0]].is_pure_fraction(1, 8), "T gate should add 1/8 phase");

        // Tdg should cancel out T
        ps.apply_tdg(0); 
        assert!(ps.p.terms.is_empty(), "T and Tdg should cancel each other out (Modulo 1)");
    }

    #[test]
    fn test_apply_cz() {
        let mut ps = setup_test_env(2);
        ps.apply_cz(0, 1);
        
        let mut mono = vec![0, 1];
        mono.sort_unstable(); 
        assert!(ps.p.terms[&mono].is_pure_half(), "CZ should add 1/2 * x0 * x1 phase");
    }

    #[test]
    fn test_boolean_phase_cross_terms() {
        let mut ps = setup_test_env(2);
        
        // 1. Prepare state: F[0] = x_0 ⊕ x_1
        ps.apply_cx(1, 0); 
        
        // 2. Apply S gate: equivalent to adding phase 1/4 * (x_0 ⊕ x_1)
        // Theoretical expansion: 1/4(x_0) + 1/4(x_1) - 2 * 1/4(x_0 * x_1)
        // In Modulo 1 space, cross term coefficient -1/2 ≡ 1/2
        ps.apply_s(0);
        
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "Linear term x_0 should have 1/4 phase");
        assert!(ps.p.terms[&vec![1]].is_pure_quarter(), "Linear term x_1 should have 1/4 phase");
        
        let mut cross = vec![0, 1];
        cross.sort_unstable();
        assert!(ps.p.terms[&cross].is_pure_half(), "Cross term x_0*x_1 should have 1/2 phase (-1/2 mod 1)");
    }
}