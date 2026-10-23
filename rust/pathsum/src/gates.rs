// src/gates.rs
use crate::pathsum::PathSum;
use crate::rational::{Rational, FreeRational, PhaseCoeff, Angle};
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
    fn apply_p(&mut self, qubit: usize, phase: Angle, side: Side);
    fn apply_rx(&mut self, qubit: usize, theta: Angle, side: Side);
    fn apply_ry(&mut self, qubit: usize, theta: Angle, side: Side);
    fn apply_rz(&mut self, qubit: usize, phase: Angle, side: Side);

    fn apply_u1(&mut self, qubit: usize, phase: Angle, side: Side);
    fn apply_u2(&mut self, qubit: usize, phi: Angle, lam: Angle, side: Side);
    fn apply_u3(&mut self, qubit: usize, theta: Angle, phi: Angle, lam: Angle, side: Side);
    
    fn apply_u(&mut self, qubit: usize, theta: Angle, phi: Angle, lam: Angle, side: Side);
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
        
        if self.is_auto_reduce() {
            self.full_reduce();
        }
    }

    fn apply_s(&mut self, qubit: usize, side: Side) {
        let phase = PhaseCoeff::new_constant(Rational::new(1, 4));
        match side {
            Side::Ket => self.p += (&self.f.functions[qubit], phase),
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_phase = PhaseCoeff::ZERO - phase;
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
                let conj_phase = PhaseCoeff::ZERO - phase;
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
                self.p += (&product_poly, PhaseCoeff::HALF);
            }
            Side::Bra => {
                let mut term = vec![control as u32, target as u32];
                term.sort_unstable();
                self.p += (term, PhaseCoeff::HALF);
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
                let conj_phase = PhaseCoeff::ZERO - phase;
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
                let conj_phase = PhaseCoeff::ZERO - phase;
                self.p += (x_i, conj_phase);
            }
        }
    }
    // ==========================================
    // Rotation Gates
    // ==========================================
    /// RX(theta) = U3(theta, -pi/2, pi/2)
    fn apply_rx(&mut self, qubit: usize, theta: Angle, side: Side) {
        // phi = -pi/2 (-1/4 cycle)
        let neg_pi_over_2 = Angle::new_constant(FreeRational::new(-1, 2));
        // lam = pi/2 (1/4 cycle)
        let pi_over_2 = Angle::new_constant(FreeRational::new(1, 2));
        self.apply_u(qubit, theta, neg_pi_over_2, pi_over_2, side);

    }

    /// RY(theta) = U3(theta, 0, 0)
    fn apply_ry(&mut self, qubit: usize, theta: Angle, side: Side) {
        let zero = Angle::ZERO;
        // phi = 0, lam = 0
        self.apply_u(qubit, theta, zero.clone(), zero.clone(), side);
    }
    fn apply_rz(&mut self, qubit: usize, theta: Angle, side: Side) {
        // RZ(φ) = exp(-iφ/2) * P(φ)
        match side {
            Side::Ket => {
                let x_i = &self.f.functions[qubit];
                self.p += (theta.clone()/-4).to_phase_coeff();
                self.p += (x_i, (theta.clone() /2).to_phase_coeff());
            }
            Side::Bra => {
                let x_i_idx = qubit as u32;
                let mut x_i_poly = FxHashSet::default();
                x_i_poly.insert(vec![x_i_idx]);
                
                self.p += (theta.clone() / 4).to_phase_coeff();
                self.p += (&x_i_poly, (theta.clone() / -2).to_phase_coeff());
                
            }
        }
    }
    fn apply_p(&mut self, qubit: usize, theta: Angle,side: Side) {
        // Angle stores theta/pi, while the PathSum exponent is normalized
        // to 2*pi: P(theta)|1> = exp(i*theta)|1>. The half factor is
        // essential for both P and U1, including bra-side conjugation.
        match side {
            Side::Ket => {
                let phase = (theta / 2).to_phase_coeff();
                self.p += (&self.f.functions[qubit], phase);
            }
            Side::Bra => {
                let x_i = vec![qubit as u32];
                let conj_theta = Angle::ZERO - theta / 2;
                let conj_phase = conj_theta.to_phase_coeff();
                self.p += (x_i, conj_phase);
            }
        }
    }

    fn apply_u1(&mut self, qubit: usize, theta: Angle, side: Side) {
        self.apply_p(qubit, theta, side);
    }
    /// U2 Gate: X-Y plane rotation defined as U2(phi, lam) = U3(pi/2, phi, lam)
    fn apply_u2(&mut self, qubit: usize, phi: Angle, lam: Angle, side: Side) {
        // Angle stores theta/pi: the U2 theta=pi/2 constant is HALF.
        let pi_over_2 = Angle::HALF;
        self.apply_u(qubit, pi_over_2, phi, lam, side);
    }
    /// U3(theta, phi, lam)
    fn apply_u3(&mut self, qubit: usize, theta: Angle, phi: Angle, lam: Angle, side: Side) {
        self.apply_u(qubit, theta, phi, lam, side);
    }
    fn apply_u(&mut self, qubit: usize, theta: Angle, phi: Angle, lam: Angle, side: Side) {
        // Generate two fresh path variables
        let v0 = self.v.get_fresh_var();
        let v1 = self.v.get_fresh_var();

        let mut v0_poly = FxHashSet::default();
        v0_poly.insert(vec![v0]);
        let mut v1_poly = FxHashSet::default();
        v1_poly.insert(vec![v1]);

        // Pre-compute coefficient constants
        let half = PhaseCoeff::HALF;
        let quarter = PhaseCoeff::QUARTER;
        let three_quarters = PhaseCoeff::THREE_QUARTERS;
        match side {
            Side::Ket => {
                let x_i = &self.f.functions[qubit];

                let lam_coeff = (lam.clone() / 2).to_phase_coeff();
                let phi_coeff = (phi.clone() / 2).to_phase_coeff();
                let theta_coeff = (theta.clone() / 2).to_phase_coeff();
                let global_coeff = (theta.clone() / -4).to_phase_coeff();

                // Add phase terms
                self.p += (x_i, lam_coeff);
                self.p += (&v1_poly, phi_coeff);
                self.p += (&v0_poly, theta_coeff);
                self.p += global_coeff;
                self.p += (x_i, three_quarters.clone());
                self.p += (&v1_poly, quarter.clone());

                // Add cross terms
                let cross_x_v0 = pathsum::mul_boolean_polys(x_i, &v0_poly);
                self.p += (&cross_x_v0, half.clone());
                
                let cross_v0_v1 = pathsum::mul_boolean_polys(&v0_poly, &v1_poly);
                self.p += (&cross_v0_v1, half.clone());

                // Update boolean state: x_i -> v1
                self.f.functions[qubit] = v1_poly;
            }
            Side::Bra => {
                let x_i_idx = qubit as u32;
                let mut x_i_poly = FxHashSet::default();
                x_i_poly.insert(vec![x_i_idx]);
                
                let lam_coeff = (lam.clone() / -2).to_phase_coeff();
                let phi_coeff = (phi.clone() / -2).to_phase_coeff();
                let theta_coeff = (theta.clone() / 2).to_phase_coeff();
                let global_coeff = (theta.clone() / -4).to_phase_coeff();

                // Substitute x_i -> v1
                self.substitute_var(x_i_idx, v1);

                // Add phase terms
                self.p += (&x_i_poly, phi_coeff);
                self.p += (&v1_poly, lam_coeff);
                self.p += (&v0_poly, theta_coeff);
                self.p += global_coeff;
                self.p += (&x_i_poly, quarter.clone());
                self.p += (&v1_poly, three_quarters.clone());

                // Add cross terms
                let cross_x_v0 = pathsum::mul_boolean_polys(&x_i_poly, &v0_poly);
                self.p += (&cross_x_v0, half.clone());

                let cross_v0_v1 = pathsum::mul_boolean_polys(&v0_poly, &v1_poly);
                self.p += (&cross_v0_v1, half.clone());
            }
        }

        if self.is_auto_reduce() {
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
        ps.set_auto_reduce(false); // Disable auto-reduce to inspect raw expansion state
        ps
    }

    // An independent amplitude oracle: enumerate ALL fresh path variables
    // in the unreduced one-qubit PathSum. In contrast to API verdict tests,
    // this does not call Reduction, WMC, or compare two copies of apply_u.
    // The complex exponential is used only as a numerical crosscheck for
    // small rational-pi gate matrices, never as a strict source certificate.
    fn unreduced_one_qubit_operator(
        ps: &PathSum,
    ) -> [[num_complex::Complex64; 2]; 2] {
        use num_complex::Complex64;
        use std::f64::consts::PI;
        assert_eq!(ps.v.num_qubits, 1);
        assert_eq!(ps.f.functions.len(), 1);
        let mut fresh: Vec<u32> = ps.v.path_vars.iter()
            .copied().filter(|&v| v >= 1).collect();
        fresh.sort_unstable();
        assert!(fresh.len() <= 5, "Bound exhaustive oracle size");
        let mut matrix = [[Complex64::new(0.0, 0.0); 2]; 2];
        let normalization = ((1u32 << fresh.len()) as f64).sqrt();
        for input in 0..2u32 {
            for mask in 0..(1u32 << fresh.len()) {
                let mut assignment = input;
                for (j, &id) in fresh.iter().enumerate() {
                    assert!(id < 32);
                    if (mask & (1u32 << j)) != 0 {
                        assignment |= 1u32 << id;
                    }
                }
                let is_true = |mono: &Vec<u32>| -> bool {
                    mono.iter().all(|&id| (assignment & (1u32 << id)) != 0)
                };
                let output = ps.f.functions[0].iter()
                    .fold(false, |acc, mono| acc ^ is_true(mono));
                let mut cycle = 0.0;
                for (mono, coeff) in &ps.p.terms {
                    assert!(coeff.symbols.is_empty(),
                            "Only exact rational-pi gates supported");
                    if is_true(mono) {
                        cycle += coeff.constant.numer as f64
                            / coeff.constant.denom as f64;
                    }
                }
                let value = Complex64::from_polar(1.0, 2.0 * PI * cycle)
                    / normalization;
                matrix[output as usize][input as usize] += value;
            }
        }
        matrix
    }

    fn assert_matrix_matches(
        actual: [[num_complex::Complex64; 2]; 2],
        expected: [[num_complex::Complex64; 2]; 2],
        context: &str,
    ) {
        for row in 0..2 {
            for col in 0..2 {
                assert!(
                    (actual[row][col] - expected[row][col]).norm() < 1e-11,
                    "{context}: matrix[{row}][{col}] was {:?}, expected {:?}",
                    actual[row][col], expected[row][col]
                );
            }
        }
    }

    #[test]
    fn test_one_qubit_raw_pathsum_against_independent_unitary_matrices() {
        use num_complex::Complex64 as C;
        use std::f64::consts::PI;
        let i = C::new(0.0, 1.0);
        let e = |angle: f64| C::from_polar(1.0, angle);

        for (theta, phi, lambda, t, p, l) in [
            (Angle::ZERO, Angle::ZERO, Angle::ZERO, 0.0, 0.0, 0.0),
            (Angle::HALF, Angle::QUARTER, Angle::THREE_QUARTERS,
             PI / 2.0, PI / 4.0, 3.0 * PI / 4.0),
            (Angle::QUARTER, Angle::HALF, Angle::QUARTER,
             PI / 4.0, PI / 2.0, PI / 4.0),
            (Angle::HALF, Angle::ZERO, Angle::ZERO,
             PI / 2.0, 0.0, 0.0),
        ] {
            let c = (t / 2.0).cos();
            let s = (t / 2.0).sin();
            // Independently specified Qiskit U(theta,phi,lambda) matrix;
            // NOT derived from Rust apply_u() or from a solver verdict.
            let target = [
                [C::new(c, 0.0), -e(l) * s],
                [e(p) * s, e(p + l) * c],
            ];
            for side in [Side::Ket, Side::Bra] {
                let mut ps = setup_test_env(1);
                ps.apply_u3(0, theta.clone(), phi.clone(), lambda.clone(), side);
                let got = unreduced_one_qubit_operator(&ps);
                let reference = if matches!(side, Side::Bra) {
                    [
                        [target[0][0].conj(), target[1][0].conj()],
                        [target[0][1].conj(), target[1][1].conj()],
                    ]
                } else {
                    target
                };
                assert_matrix_matches(got, reference, "U3 analytic unitary");

                let mut same = setup_test_env(1);
                same.apply_u(0, theta.clone(), phi.clone(), lambda.clone(), side);
                assert_eq!(same.p.terms, ps.p.terms, "U and U3 phase mismatch");
                assert_eq!(same.f.functions, ps.f.functions, "U and U3 output mismatch");
                assert_eq!(same.v.path_vars, ps.v.path_vars, "U and U3 path variables differ");
            }
        }

        for (theta, radians) in [
            (Angle::ZERO, 0.0),
            (Angle::HALF, PI / 2.0),
            (Angle::QUARTER, PI / 4.0),
            (Angle::new_constant(crate::rational::FreeRational::new(-1, 4)),
             -PI / 4.0),
        ] {
            let c = (radians / 2.0).cos();
            let s = (radians / 2.0).sin();
            let rx = [[C::new(c,0.0), -i*s], [-i*s, C::new(c,0.0)]];
            let ry = [[C::new(c,0.0), C::new(-s,0.0)],
                      [C::new(s,0.0), C::new(c,0.0)]];
            let rz = [[e(-radians/2.0), C::new(0.0,0.0)],
                      [C::new(0.0,0.0), e(radians/2.0)]];
            for (name, expected) in [("rx", rx), ("ry", ry), ("rz", rz)] {
                for side in [Side::Ket, Side::Bra] {
                    let mut ps = setup_test_env(1);
                    match name {
                        "rx" => ps.apply_rx(0,theta.clone(),side),
                        "ry" => ps.apply_ry(0,theta.clone(),side),
                        "rz" => ps.apply_rz(0,theta.clone(),side),
                        _ => unreachable!(),
                    }
                    let target = if matches!(side,Side::Bra) {
                        [
                            [expected[0][0].conj(),expected[1][0].conj()],
                            [expected[0][1].conj(),expected[1][1].conj()],
                        ]
                    } else {
                        expected
                    };
                    assert_matrix_matches(
                        unreduced_one_qubit_operator(&ps), target, name
                    );
                }
            }
        }
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
    fn test_u2_matches_u3_pi_over_two_as_raw_pathsum() {
        // Qiskit U2(phi, lambda) = U3(pi/2, phi, lambda).
        // Angles store theta/pi, therefore pi/2 is Angle::HALF.
        // Compare unsimplified polynomial/Boolean tensors so a
        // near-identity numerical tolerance cannot hide a theta bug.
        for (phi, lam) in [
            (Angle::ZERO, Angle::ZERO),
            (Angle::QUARTER, Angle::THREE_QUARTERS),
            (Angle::HALF, Angle::QUARTER),
        ] {
            for side in [Side::Ket, Side::Bra] {
                let mut u2 = setup_test_env(1);
                let mut u3 = setup_test_env(1);
                u2.apply_u2(0, phi.clone(), lam.clone(), side);
                u3.apply_u3(0, Angle::HALF, phi.clone(), lam.clone(), side);
                assert_eq!(u2.p.terms, u3.p.terms,
                    "U2 phase polynomial must equal U3(pi/2,phi,lambda) on both sides");
                assert_eq!(u2.f.functions, u3.f.functions,
                    "U2 Boolean output must match U3(pi/2,phi,lambda)");
                assert_eq!(u2.v.path_vars, u3.v.path_vars,
                    "U2 path variable structure differs");
            }
        }
    }

    #[test]
    fn test_apply_p() {
        let mut ps = setup_test_env(1);
        // P(pi/4) contributes (pi/4)/(2*pi) = 1/8 to phase polynomial.
        ps.apply_p(0, Angle::QUARTER, Side::Ket);
        assert!(
            ps.p.terms[&vec![0]].is_pure_fraction(1, 8),
            "P(pi/4) must contribute 1/8 cycle, not 1/4"
        );
        assert!(!ps.p.terms.contains_key(&vec![]), "P must not add global phase");
    }

    #[test]
    fn test_p_u1_relative_phase_unit_contract() {
        let mut p_half = setup_test_env(1);
        p_half.apply_p(0, Angle::HALF, Side::Ket);
        assert!(p_half.p.terms[&vec![0]].is_pure_quarter(),
                "P(pi/2) must be S, not Z");

        let mut u1_half = setup_test_env(1);
        u1_half.apply_u1(0, Angle::HALF, Side::Ket);
        assert_eq!(u1_half.p.terms, p_half.p.terms,
                   "U1(pi/2) must match P(pi/2)");

        let mut p_bra = setup_test_env(1);
        p_bra.apply_p(0, Angle::HALF, Side::Bra);
        assert!(p_bra.p.terms[&vec![0]].is_pure_three_quarters(),
                "Bra(P(pi/2)) must contribute -1/4 cycle");

        let mut p_pi = setup_test_env(1);
        p_pi.apply_p(0, Angle::new_constant(crate::rational::FreeRational::new(1, 1)), Side::Ket);
        assert!(p_pi.p.terms[&vec![0]].is_pure_half(),
                "P(pi) must be Z, not Identity");
    }

    #[test]
    fn test_apply_rz() {
        let mut ps = setup_test_env(1);
        
        let phase = Angle::HALF; 
        ps.apply_rz(0, phase, Side::Ket);
        
        println!("P terms after RZ: {:?}", ps.print_status());
        assert!(ps.p.terms[&vec![0]].is_pure_quarter(), "RZ gate should add relative phase");
        
        assert!(ps.p.terms[&vec![]].is_pure_fraction(7, 8), "RZ gate MUST add -phase/2 global phase");
    }
}