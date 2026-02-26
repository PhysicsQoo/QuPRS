// src/gates.rs
use crate::pathsum::PathSum;
use crate::rational::{Rational, PhaseCoeff};
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
    
    // Non-Clifford Gates
    fn apply_t(&mut self, qubit: usize);
    fn apply_tdg(&mut self, qubit: usize);
}

impl PathSum {
    /// Core algebraic engine: transforms c * (m_1 ⊕ m_2 ⊕ ... ⊕ m_k) exactly and adds to P.
    /// Uses truncation modulo 1 to terminate polynomial expansion early, avoiding exponential blowup.
    pub(crate) fn apply_boolean_phase(&mut self, poly: &FxHashSet<Monomial>, base_coeff: PhaseCoeff) {
        let terms: Vec<Monomial> = poly.iter().cloned().collect();
        let n = terms.len();
        if n == 0 { return; }

        for degree in 1..=n {
            // Calculate coefficient for this degree: base_coeff * (-1)^(degree-1) * 2^(degree-1)
            let multiplier = if (degree - 1) % 2 == 0 {
                1_i64 << (degree - 1)
            } else {
                -(1_i64 << (degree - 1))
            };
            
            let current_coeff = base_coeff.clone() * multiplier;
            
            // [Core Optimization] If coefficient is zeroed by Modulo 1, higher-degree terms are also 0, terminate expansion!
            if current_coeff.is_zero() {
                break;
            }

            // Generate all combinations of size degree (Combinations)
            let mut combinations = Vec::new();
            let mut current = Vec::new();
            Self::generate_combinations(&terms, degree, 0, &mut current, &mut combinations);

            // Multiply monomials in each combination and add to P
            for combo in combinations {
                let mut merged_mono = vec![];
                for m in combo {
                    merged_mono = pathsum::mul_monomials(&merged_mono, &m);
                }
                self.p.add_term(merged_mono, current_coeff.clone());
            }
        }
    }

    /// Helper function: recursively generate C(n, k) combinations of array
    fn generate_combinations(
        terms: &[Monomial],
        degree: usize,
        start: usize,
        current: &mut Vec<Monomial>,
        result: &mut Vec<Vec<Monomial>>
    ) {
        if current.len() == degree {
            result.push(current.clone());
            return;
        }
        for i in start..terms.len() {
            current.push(terms[i].clone());
            Self::generate_combinations(terms, degree, i + 1, current, result);
            current.pop();
        }
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
        // Z gate: add phase 1/2
        let poly = self.f.functions[qubit].clone();
        self.apply_boolean_phase(&poly, PhaseCoeff::new_constant(Rational::new(1, 2)));
    }

    fn apply_y(&mut self, qubit: usize) {
        // Y = i * X * Z
        // 1. Add global phase i (i.e., 1/4)
        self.p.add_term(vec![], PhaseCoeff::new_constant(Rational::new(1, 4)));
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

        let current_f_q = self.f.functions[qubit].clone();
        let half = PhaseCoeff::new_constant(Rational::new(1, 2));
        
        for term in current_f_q {
            let new_term = pathsum::mul_monomials(&term, &new_var_mono);
            self.p.add_term(new_term, half.clone());
        }

        let mut new_poly = FxHashSet::default();
        new_poly.insert(new_var_mono);
        self.f.functions[qubit] = new_poly;

        if self.auto_reduce {
            self.full_reduce();
        }
    }

    fn apply_cx(&mut self, control: usize, target: usize) {
        self.f.apply_xor(control, target);
        if self.auto_reduce {
            self.full_reduce();
        }
    }

    fn apply_cz(&mut self, control: usize, target: usize) {
        // CZ adds phase 1/2 * (F[ctrl] * F[tgt])
        let mut product_poly = FxHashSet::default();
        for m1 in &self.f.functions[control] {
            for m2 in &self.f.functions[target] {
                let m = pathsum::mul_monomials(m1, m2);
                if product_poly.contains(&m) {
                    product_poly.remove(&m);
                } else {
                    product_poly.insert(m);
                }
            }
        }
        self.apply_boolean_phase(&product_poly, PhaseCoeff::new_constant(Rational::new(1, 2)));
    }
    fn apply_s(&mut self, qubit: usize) {
        let poly = self.f.functions[qubit].clone();
        self.apply_boolean_phase(&poly, PhaseCoeff::new_constant(Rational::new(1, 4)));
    }

    fn apply_sdg(&mut self, qubit: usize) {
        let poly = self.f.functions[qubit].clone();
        self.apply_boolean_phase(&poly, PhaseCoeff::new_constant(Rational::new(3, 4)));
    }
    // ==========================================
    // T Gates
    // ==========================================
    fn apply_t(&mut self, qubit: usize) {
        let poly = self.f.functions[qubit].clone();
        self.apply_boolean_phase(&poly, PhaseCoeff::new_constant(Rational::new(1, 8)));
    }

    fn apply_tdg(&mut self, qubit: usize) {
        let poly = self.f.functions[qubit].clone();
        self.apply_boolean_phase(&poly, PhaseCoeff::new_constant(Rational::new(7, 8)));
    }
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