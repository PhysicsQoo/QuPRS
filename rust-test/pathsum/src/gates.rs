// src/gates.rs
use crate::pathsum::PathSum;
use crate::rational::{Rational, PhaseCoeff};
use crate::pathsum::{self};
use rustc_hash::FxHashSet;

/// Defines the application direction of quantum gates
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Side {
    Ket, // Forward: modify output end (F_out)
    Bra, // Backward: replace input end (x_in)
}
pub trait QuantumGates {
    // Basic Pauli Gates
    fn apply_x(&mut self, qubit: usize, side: Side);
    fn apply_y(&mut self, qubit: usize, side: Side);
    fn apply_z(&mut self, qubit: usize, side: Side);
    
    // Clifford Gates
    fn apply_h(&mut self, qubit: usize, side: Side);
    fn apply_s(&mut self, qubit: usize, side: Side);
    fn apply_sdg(&mut self, qubit: usize, side: Side);
    fn apply_cx(&mut self, control: usize, target: usize, side: Side);
    fn apply_cz(&mut self, control: usize, target: usize, side: Side);
    fn apply_ccx(&mut self, control1: usize, control2: usize, target: usize, side: Side);

    // Non-Clifford Gates
    fn apply_t(&mut self, qubit: usize, side: Side);
    fn apply_tdg(&mut self, qubit: usize, side: Side);

    // Rotation Gates
    fn apply_p(&mut self, qubit: usize, phase: PhaseCoeff, side: Side);
    fn apply_rx(&mut self, qubit: usize, theta: PhaseCoeff, side: Side);
    fn apply_ry(&mut self, qubit: usize, theta: PhaseCoeff, side: Side);
    fn apply_rz(&mut self, qubit: usize, phase: PhaseCoeff, side: Side);

    fn apply_u1(&mut self, qubit: usize, phase: PhaseCoeff, side: Side);
    fn apply_u2(&mut self, qubit: usize, phi: PhaseCoeff, lam: PhaseCoeff, side: Side);
    fn apply_u3(&mut self, qubit: usize, theta: PhaseCoeff, phi: PhaseCoeff, lam: PhaseCoeff, side: Side);
    
    fn apply_u(&mut self, qubit: usize, theta: PhaseCoeff, phi: PhaseCoeff, lam: PhaseCoeff, side: Side);
}

impl QuantumGates for PathSum {
    // ==========================================
    // Pauli Gates
    // ==========================================
    fn apply_x(&mut self, qubit: usize, side: Side) {
        // X gate is equivalent to XOR 1 in F[q]. In our system, 1 is the empty monomial vec![]
        match side {
            Side::Ket => {
                // Ket: F[q] = F[q] ⊕ 1
                let one = vec![]; 
                if self.f.functions[qubit].contains(&one) {
                    self.f.functions[qubit].remove(&one);
                } else {
                    self.f.functions[qubit].insert(one);
                }
            }
            Side::Bra => {
                // Bra: Substitute x_i -> x_i ⊕ 1
                let x_i = qubit as u32;
                
                // Construct polynomial P = {x_i, 1}
                let mut sub_poly = FxHashSet::default();
                sub_poly.insert(vec![x_i]);
                sub_poly.insert(vec![]); // Constant 1
                
                self.substitute_var_with_poly(x_i, &sub_poly);
            }
        }
    }

    fn apply_z(&mut self, qubit: usize, side: Side) {
        let phase = PhaseCoeff::new_constant(Rational::new(1, 2));
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => self.p += (vec![qubit as u32], phase),
            }
    }

    fn apply_y(&mut self, qubit: usize, side: Side) {
        match side {
            Side::Ket => {
                // Y = i * X * Z
                self.p += PhaseCoeff::new_constant(Rational::new(1, 4));
                self.apply_z(qubit, Side::Ket);
                self.apply_x(qubit, Side::Ket);
            }
            Side::Bra => {
                // Y† = -i * Z * X
                // 1. Global Phase: -i 
                let phase_conj = PhaseCoeff::new_constant(Rational::new(3, 4));
                self.p += phase_conj;
                // 2. Operators: Z * X
                self.apply_x(qubit, Side::Bra);
                self.apply_z(qubit, Side::Bra);
            }
        }
    }

    // ==========================================
    // Clifford Gates
    // ==========================================
    

    fn apply_h(&mut self, qubit: usize, side: Side) {
        let new_var = self.v.get_fresh_var();
        match side {
            Side::Ket => {
                let mut y_poly = FxHashSet::default();
                y_poly.insert(vec![new_var]);
                // H on output end: F[q] = y, P += 1/2 * x * y
                let product_poly = pathsum::mul_boolean_polys(&self.f.functions[qubit], &y_poly);
                self.p += (&product_poly, PhaseCoeff::new_constant(Rational::new(1, 2)));
                self.f.functions[qubit] = y_poly;
            }
            Side::Bra => {
                let x_i = qubit as u32; 
                self.substitute_var(x_i, new_var);
                
                let mut cross_term = vec![x_i, new_var];
                cross_term.sort_unstable();
                self.p += (cross_term, PhaseCoeff::new_constant(Rational::new(1, 2)));
            }
        }
        
        if self.auto_reduce {
            self.full_reduce();
        }
    }

    fn apply_s(&mut self, qubit: usize, side: Side) {
        let phase = PhaseCoeff::new_constant(Rational::new(1, 4));
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::new_constant(Rational::zero()) - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }


    fn apply_sdg(&mut self, qubit: usize, side: Side) {
        let phase = PhaseCoeff::new_constant(Rational::new(3, 4));
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::new_constant(Rational::zero()) - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }

    fn apply_cx(&mut self, control: usize, target: usize, side: Side) {
        match side {
            Side::Ket => {
                // Ket: F[t] = F[t] ⊕ F[c]
                let poly_c = self.f.functions[control].clone();
                self.f.apply_xor_with_poly(target, &poly_c);
            }
            Side::Bra => {
                // Bra: Substitute x_t -> x_t ⊕ x_c
                let x_t = target as u32;
                let x_c = control as u32;
                
                // Construct polynomial P = {x_t, x_c}
                let mut sub_poly = FxHashSet::default();
                sub_poly.insert(vec![x_t]);
                sub_poly.insert(vec![x_c]);
                
                self.substitute_var_with_poly(x_t, &sub_poly);
            }
        }
    }

    fn apply_cz(&mut self, control: usize, target: usize, side: Side) {
        // CZ adds phase 1/2 * (F[ctrl] * F[tgt])
        match side {
            Side::Ket => {
                let poly_c = &self.f.functions[control];
                let poly_t = &self.f.functions[target];

                let product_poly = pathsum::mul_boolean_polys(poly_c, poly_t);
                self.p += (&product_poly, PhaseCoeff::new_constant(Rational::new(1, 2)));
            }
            Side::Bra => {
                // Bra: Substitute x_t -> x_t ⊕ (x_c * x_t)
                let x_t = target as u32;
                let x_c = control as u32;
                
                // Construct polynomial P = {x_t, x_c * x_t}
                let mut sub_poly = FxHashSet::default();
                sub_poly.insert(vec![x_t]);
                
                let mut cross_term = vec![x_c, x_t];
                cross_term.sort_unstable();
                sub_poly.insert(cross_term);
                
                self.substitute_var_with_poly(x_t, &sub_poly);
            }
        }
    }

    fn apply_ccx(&mut self, control1: usize, control2: usize, target: usize, side: Side) {
        match side {
            Side::Ket => {
                // CCX (Toffoli) on ket end: F[t] = F[t] ⊕ (F[c1] * F[c2])
                let poly_c1 = &self.f.functions[control1];
                let poly_c2 = &self.f.functions[control2];

                // Apply the Toffoli transformation: F[target] = F[target] XOR (F[ctrl1] AND F[ctrl2])
                let product_poly = pathsum::mul_boolean_polys(poly_c1, poly_c2);

                self.f.apply_xor_with_poly(target, &product_poly);
            }
            Side::Bra => {
                // CCX on bra end: Substitute x_t -> x_t ⊕ (x_c1 * x_c2)
                let x_t = target as u32;
                let x_c1 = control1 as u32;
                let x_c2 = control2 as u32;
                
                // Construct polynomial P = {x_t, x_c1 * x_c2}
                let mut sub_poly = FxHashSet::default();
                sub_poly.insert(vec![x_t]);
                
                let mut cross_term = vec![x_c1, x_c2];
                cross_term.sort_unstable();
                sub_poly.insert(cross_term);
                
                self.substitute_var_with_poly(x_t, &sub_poly);
             }
        }
    }

    // ==========================================
    // T Gates
    // ==========================================
    fn apply_t(&mut self, qubit: usize, side: Side) {
        let phase = PhaseCoeff::new_constant(Rational::new(1, 8));
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::new_constant(Rational::zero()) - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }

    fn apply_tdg(&mut self, qubit: usize, side: Side) {
        let phase = PhaseCoeff::new_constant(Rational::new(7, 8));
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::new_constant(Rational::zero()) - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }
    // ==========================================
    // Rotation Gates
    // ==========================================
    /// RX(theta) = U3(theta, -pi/2, pi/2)
    fn apply_rx(&mut self, qubit: usize, theta: PhaseCoeff, side: Side) {
        // phi = -pi/2 (-1/4 cycle)
        let neg_pi_over_2 = PhaseCoeff::new_constant(Rational::new(-1, 4));
        // lam = pi/2 (1/4 cycle)
        let pi_over_2 = PhaseCoeff::new_constant(Rational::new(1, 4));
        
        self.apply_u(qubit, theta, neg_pi_over_2, pi_over_2, side);
    }

    /// RY(theta) = U3(theta, 0, 0)
    fn apply_ry(&mut self, qubit: usize, theta: PhaseCoeff, side: Side) {
        let zero = PhaseCoeff::new_constant(Rational::zero());
        // phi = 0, lam = 0
        self.apply_u(qubit, theta, zero.clone(), zero, side);
    }
    fn apply_rz(&mut self, qubit: usize, phase: PhaseCoeff, side: Side) {
        // RZ(φ) = exp(-iφ/2) * P(φ)
        match side {
            Side::Ket => {
                let zero = PhaseCoeff::new_constant(Rational::zero());
                let global_correction = zero - (phase.clone() / 2);
                self.p += global_correction;
                self.p += (&self.f.functions[qubit], phase);
            }
            Side::Bra => {
                let x_i = vec![qubit as u32];
                
                let zero = PhaseCoeff::new_constant(Rational::zero());
                let conj_phase = zero.clone() - phase;
                
                let global_correction = zero - (conj_phase.clone() / 2);
                
                self.p += global_correction;
                self.p += (x_i, conj_phase);
            }
        }
    }
    fn apply_p(&mut self, qubit: usize, phase: PhaseCoeff,side: Side) {
         match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::new_constant(Rational::zero()) - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }

    fn apply_u1(&mut self, qubit: usize, phase: PhaseCoeff, side: Side) {
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::new_constant(Rational::zero()) - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }
    /// U2 Gate: X-Y plane rotation defined as U2(phi, lam) = U3(pi/2, phi, lam)
    fn apply_u2(&mut self, qubit: usize, phi: PhaseCoeff, lam: PhaseCoeff, side: Side) {
        // theta = pi/2 (即 1/4 cycle)
        let pi_over_2 = PhaseCoeff::new_constant(Rational::new(1, 4));
        self.apply_u(qubit, pi_over_2, phi, lam, side);
    }
    /// U3(theta, phi, lam)
    fn apply_u3(&mut self, qubit: usize, theta: PhaseCoeff, phi: PhaseCoeff, lam: PhaseCoeff, side: Side) {
        self.apply_u(qubit, theta, phi, lam, side);
    }
    fn apply_u(&mut self, qubit: usize, theta: PhaseCoeff, phi: PhaseCoeff, lam: PhaseCoeff, side: Side) {
        // Generate two fresh path variables
        let v0 = self.v.get_fresh_var();
        let v1 = self.v.get_fresh_var();

        // Pre-compute coefficient constants
        let half = PhaseCoeff::new_constant(Rational::new(1, 2));
        let quarter = PhaseCoeff::new_constant(Rational::new(1, 4));
        let three_quarter = PhaseCoeff::new_constant(Rational::new(3, 4));
        
        let theta_term_v0 = theta.clone() / 2;
        let theta_global = theta.clone() / -4;

        match side {
            Side::Ket => {
                let x_i = &self.f.functions[qubit];
                
                let mut v0_poly = FxHashSet::default();
                v0_poly.insert(vec![v0]);
                let mut v1_poly = FxHashSet::default();
                v1_poly.insert(vec![v1]);

                // Add phase terms
                self.p += (x_i, lam.clone() / 2);
                self.p += (&v1_poly, phi.clone() / 2);
                self.p += (&v0_poly, theta_term_v0);
                self.p += theta_global;
                self.p += (x_i, three_quarter);
                self.p += (&v1_poly, quarter);

                // Add cross terms
                let cross_x_v0 = pathsum::mul_boolean_polys(x_i, &v0_poly);
                self.p += (&cross_x_v0, half.clone());
                
                let mut cross_v0_v1 = vec![v0, v1];
                cross_v0_v1.sort_unstable();
                self.p += (cross_v0_v1, half);

                // Update boolean state: x_i -> v1
                self.f.functions[qubit] = v1_poly;
            }
            Side::Bra => {
                let x_i_idx = qubit as u32;

                // Substitute x_i -> v1
                self.substitute_var(x_i_idx, v1);

                // Add phase terms
                self.p += (vec![x_i_idx], phi.clone() / -2);
                self.p += (vec![v1], lam.clone() / -2);
                self.p += (vec![v0], theta_term_v0);
                self.p += theta_global;
                self.p += (vec![x_i_idx], quarter);
                self.p += (vec![v1], three_quarter);

                // Add cross terms
                let mut cross_x_v0 = vec![x_i_idx, v0];
                cross_x_v0.sort_unstable();
                self.p += (cross_x_v0, half.clone());

                let mut cross_v0_v1 = vec![v0, v1];
                cross_v0_v1.sort_unstable();
                self.p += (cross_v0_v1, half);
            }
        }

        if self.auto_reduce {
            self.full_reduce();
        }
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
        ps.apply_x(0, Side::Ket);
        let one = vec![];
        assert!(ps.f.functions[0].contains(&one), "X gate should add empty vec (1) to F");
        assert!(ps.f.functions[0].contains(&vec![0]), "Original x0 should still be in F");

        // Test Z gate (Phase 1/2)
        ps.apply_z(0, Side::Ket);
        assert!(ps.p.terms[&vec![0]].is_pure_half(), "Z gate should add 1/2 phase to x0");
        // Note: Since F[0] now becomes x0 ⊕ 1, Z gate also adds 1/2 phase to constant term (vec![])
        assert!(ps.p.terms[&one].is_pure_half(), "Z gate should add 1/2 phase to the constant term");
    }

    #[test]
    fn test_apply_y() {
        let mut ps = setup_test_env(1);
        ps.apply_y(0, Side::Ket);
        
        // Y = iXZ. Expected: global phase 1/4, Z phase 1/2 * x0, F[0] becomes x0 ⊕ 1
        let one = vec![];
        assert!(ps.p.terms[&one].is_pure_quarter(), "Y gate should add global phase 1/4");
        assert!(ps.p.terms[&vec![0]].is_pure_half(), "Y gate should add 1/2 phase to x0");
        assert!(ps.f.functions[0].contains(&one), "Y gate should flip F");
    }

    #[test]
    fn test_apply_s_and_sdg() {
        let mut ps = setup_test_env(1);
        ps.apply_s(0, Side::Ket);
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "S gate should add 1/4 phase");

        // Sdg should cancel out S
        ps.apply_sdg(0, Side::Ket); 
        assert!(ps.p.terms.is_empty(), "S and Sdg should cancel each other out (Modulo 1)");
    }

    #[test]
    fn test_apply_t_and_tdg() {
        let mut ps = setup_test_env(1);
        ps.apply_t(0, Side::Ket);
        assert!(ps.p.terms[&vec![0]].is_pure_fraction(1, 8), "T gate should add 1/8 phase");

        // Tdg should cancel out T
        ps.apply_tdg(0, Side::Ket); 
        assert!(ps.p.terms.is_empty(), "T and Tdg should cancel each other out (Modulo 1)");
    }

    #[test]
    fn test_apply_cz() {
        let mut ps = setup_test_env(2);
        ps.apply_cz(0, 1, Side::Ket);
        
        let mut mono = vec![0, 1];
        mono.sort_unstable(); 
        assert!(ps.p.terms[&mono].is_pure_half(), "CZ should add 1/2 * x0 * x1 phase");
    }

    #[test]
    fn test_boolean_phase_cross_terms() {
        let mut ps = setup_test_env(2);
        
        // 1. Prepare state: F[0] = x_0 ⊕ x_1
        ps.apply_cx(1, 0, Side::Ket); 
        
        // 2. Apply S gate: equivalent to adding phase 1/4 * (x_0 ⊕ x_1)
        // Theoretical expansion: 1/4(x_0) + 1/4(x_1) - 2 * 1/4(x_0 * x_1)
        // In Modulo 1 space, cross term coefficient -1/2 ≡ 1/2
        ps.apply_s(0, Side::Ket);
         // Verify cross term
         let mut cross = vec![0, 1];
         cross.sort_unstable();
         assert!(ps.p.terms[&cross].is_pure_half(), "Cross term x_0*x_1 should have 1/2 phase (-1/2 mod 1)");
        
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "Linear term x_0 should have 1/4 phase");
        assert!(ps.p.terms[&vec![1]].is_pure_quarter(), "Linear term x_1 should have 1/4 phase");
        
        let mut cross = vec![0, 1];
        cross.sort_unstable();
        assert!(ps.p.terms[&cross].is_pure_half(), "Cross term x_0*x_1 should have 1/2 phase (-1/2 mod 1)");
    }
    #[test]
    fn test_apply_h() {
        let mut ps = setup_test_env(1);
        ps.apply_h(0, Side::Ket);
        
        let new_var = 1;
        let new_var_mono = vec![new_var];
        
        assert!(ps.f.functions[0].contains(&new_var_mono), "F[0] should contain the new path variable");
        assert_eq!(ps.f.functions[0].len(), 1, "F[0] should ONLY contain the new path variable");

        let mut cross_term = vec![0, new_var];
        cross_term.sort_unstable();
        assert!(ps.p.terms[&cross_term].is_pure_half(), "P should contain the 1/2 phase for (x0 * y)");
    }

    #[test]
    fn test_apply_cx() {
        let mut ps = setup_test_env(2);
        ps.apply_cx(0, 1, Side::Ket);
        
        assert!(ps.f.functions[1].contains(&vec![1]), "Target should still contain its original variable");
        assert!(ps.f.functions[1].contains(&vec![0]), "Target should now contain the control variable");
        assert_eq!(ps.f.functions[1].len(), 2, "Target F should be exactly x0 ⊕ x1");
        
        assert!(ps.p.terms.is_empty(), "CX gate should not add any phase to P");
    }

    #[test]
    fn test_apply_ccx() {
        let mut ps = setup_test_env(3);
        ps.apply_ccx(0, 1, 2, Side::Ket);
        
        assert!(ps.f.functions[2].contains(&vec![2]), "Target should contain its original variable x2");
        
        let mut cross = vec![0, 1];
        cross.sort_unstable();
        assert!(ps.f.functions[2].contains(&cross), "Target should contain the AND product of controls (x0 * x1)");
        assert_eq!(ps.f.functions[2].len(), 2, "Target F should be exactly x2 ⊕ (x0 * x1)");
        
        assert!(ps.p.terms.is_empty(), "CCX gate should not add any phase to P");
    }

    #[test]
    fn test_apply_p() {
        let mut ps = setup_test_env(1);
        
        let phase = PhaseCoeff::new_constant(Rational::new(1, 4));
        ps.apply_p(0, phase, Side::Ket);
        
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "P gate should add relative phase");
        
        assert!(!ps.p.terms.contains_key(&vec![]), "P gate MUST NOT add global phase");
    }

    #[test]
    fn test_apply_rz() {
        let mut ps = setup_test_env(1);
        
        let phase = PhaseCoeff::new_constant(Rational::new(1, 4));
        ps.apply_rz(0, phase, Side::Ket);
        
        
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "RZ gate should add relative phase");
        
        assert!(ps.p.terms[&vec![]].is_pure_fraction(7, 8), "RZ gate MUST add -phase/2 global phase");
    }
}