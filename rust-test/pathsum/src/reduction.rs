// src/reduction.rs
use rustc_hash::FxHashSet;
use crate::pathsum::{PathSum, Monomial};

use crate::rational::{PhaseCoeff, Rational};
use num_traits::Zero;

impl PathSum {
    pub fn get_reducible_vars(&self) -> Vec<u32> {
        let f_used_vars = self.f.get_used_vars();
        let mut reducible_vars: Vec<u32> = self.v.path_vars.iter()
            .copied()
            .filter(|&v| (v as usize) >= self.v.num_qubits && !f_used_vars.contains(&v))
            .collect();
        
        reducible_vars.sort_unstable_by(|a, b| b.cmp(a));
        
        reducible_vars
    }
    pub fn full_reduce(&mut self) {
        let mut reduced = true;
        let mut iterations = 0;

        while reduced {
            reduced = false;
            
            let reducible_vars = self.get_reducible_vars();

            if reducible_vars.is_empty() {
                break;
            }

            if self.try_reduce_elim(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if self.try_reduce_hh(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if self.try_reduce_omega(&reducible_vars) { reduced = true; iterations += 1; continue; }

            if iterations > 0 {
            println!(">> [Full Reduce] System converged after {} reduction steps.", iterations);
            }
        }
    }

    pub fn try_reduce_elim(&mut self, reducible_vars: &[u32]) -> bool {
        
        // 1. Find completely isolated internal variables (y_i)
        let mut vars_to_remove = Vec::new();
        for &var in reducible_vars {
            if !self.p.get_used_vars().contains(&var) {
                vars_to_remove.push(var);
            }
        }

        // 2. Perform elimination
        if vars_to_remove.is_empty() {
            return false;
        }

        for var in &vars_to_remove {
            self.v.path_vars.remove(var);
            println!(">> [Elimination] Removed decoupled path variable: {}", self.v.fmt_var(*var));
            
        }

        true
    }
    /// Attempt to execute HH Rule (Feynman path cancellation)
    /// Scan globally for isolated path variables and perform substitution.
    /// Return true if simplification was successful.
    pub fn try_reduce_hh(&mut self, reducible_vars: &[u32]) -> bool {
        for &var in reducible_vars {
            // ==========================================
            // Step 1: Extract Phi polynomial and verify coefficients
            // ==========================================
            let mut phi: FxHashSet<Monomial> = FxHashSet::default();
            let mut is_valid_hh = true;
            let mut y_terms_to_remove = Vec::new();

            for (mono, coeff) in &self.p.terms {
                if mono.contains(&var) {
                    if !coeff.is_pure_half() {
                        is_valid_hh = false;
                        break;
                    }
                    y_terms_to_remove.push(mono.clone());
                    
                    let mut phi_term = mono.clone();
                    phi_term.retain(|&v| v != var);
                    
                    // Add to Phi using XOR logic
                    if phi.contains(&phi_term) {
                        phi.remove(&phi_term);
                    } else {
                        phi.insert(phi_term);
                    }
                }
            }

            if !is_valid_hh || phi.is_empty() {
                continue;
            }

            // ==========================================
            // Step 2: Select substitution variable v from Phi
            // Condition: Must be a linear term (len == 1), prioritize largest ID
            // ==========================================
            let mut target_v = None;
            for term in &phi {
                if term.len() == 1 {
                    let var = term[0];
                    if target_v.map_or(true, |max_v| var > max_v) {
                        target_v = Some(var);
                    }
                }
            }

            let v = match target_v {
                Some(var) => var,
                None => continue, // No linear variable in Phi, cannot perform substitution
            };

            // Substitution expression R = Phi \ {v}
            let mut replacement = phi.clone();
            replacement.remove(&vec![v]);

            println!(">> [HH Rule] Integrator y: {}, Target v: {} -> {}", 
                    self.v.fmt_var(var), 
                    self.v.fmt_var(v), 
                    self.v.fmt_polynomial(&replacement)); // Brief output

            // ==========================================
            // Step 3: Perform variable substitution (Substitution) v -> R
            // ==========================================

            // 3a. Remove all terms containing y from P (path integral cancelled y)
            for mono in &y_terms_to_remove {
                self.p.terms.remove(mono);
            }

            // 3b. Substitute v in Boolean State (F) and Phase Polynomial (P)
            self.substitute_var_with_poly(v, &replacement);
            
            // ==========================================
            // Step 4: Garbage Collection
            // ==========================================
            self.v.path_vars.remove(&var);
            
            if (v as usize) >= self.v.num_qubits {
                self.v.path_vars.remove(&v);
            }
            return true;
        }
        false
    }
    fn check_omega_conditions(&self, y: u32) -> bool {
        let mut has_c0 = false;
        for (mono, coeff) in &self.p.terms {
            if mono.contains(&y) {
                if mono.len() == 1 {
                    // Linear term must be exactly 1/4 or 3/4
                    if coeff.is_pure_quarter() || coeff.is_pure_three_quarters() {
                        has_c0 = true;
                    } else {
                        return false; 
                    }
                } else {
                    // All non-linear cross terms must have coefficient exactly 1/2
                    if !coeff.is_pure_half() {
                        return false; 
                    }
                }
            }
        }
        has_c0
    }

    /// Attempt to execute ω-rule (Phase Gadget simplification)
    pub fn try_reduce_omega(&mut self, reducible_vars: &[u32]) -> bool {
        let mut target_y = None;
        let mut sorted_vars: Vec<_> = self.v.path_vars.iter().copied().collect();
        sorted_vars.sort_by(|a, b| b.cmp(a));

        for &var in reducible_vars {
            if self.check_omega_conditions(var) {
                target_y = Some(var);
                break;
            }
        }

        let y = match target_y {
            Some(var) => var,
            None => return false,
        };

        // 1. Extract Phi and constant c0
        let mut phi = rustc_hash::FxHashSet::default();
        let mut c0 = Rational::zero();
        let mut y_terms_to_remove = Vec::new();

        for (mono, coeff) in &self.p.terms {
            if mono.contains(&y) {
                y_terms_to_remove.push(mono.clone());
                if mono.len() == 1 {
                    c0 = coeff.constant;
                } else {
                    let mut phi_term = mono.clone();
                    phi_term.retain(|&v| v != y);
                    // Add to Phi using XOR logic
                    if phi.contains(&phi_term) {
                        phi.remove(&phi_term);
                    } else {
                        phi.insert(phi_term);
                    }
                }
            }
        }

        // 2. Remove all terms containing y from P
        for mono in &y_terms_to_remove {
            self.p.terms.remove(mono);
        }

        // 3. Compute new phase and apply to P using algebraic engine
        // If y's coefficient is 1/4, new phase is -1/4 (i.e., 3/4)
        // If y's coefficient is 3/4, new phase is +1/4
        let (base_coeff, const_phase) = if c0.numer == 1 && c0.denom == 4 {
            (
            PhaseCoeff::new_constant(Rational::new(3, 4)),
            PhaseCoeff::new_constant(Rational::new(1, 8))
            )
        } else {
            (
            PhaseCoeff::new_constant(Rational::new(1, 4)),
            PhaseCoeff::new_constant(Rational::new(7, 8))
            )
        };
        self.p += const_phase;
        self.p += (&phi, base_coeff);

        // 4. Garbage collection
        self.v.path_vars.remove(&y);
        println!(">> [Omega Rule] Integrated out variable: {} (generated Phase Gadget)", self.v.fmt_var(y));

        true
    }
}

#[cfg(test)] 
mod tests {
    use super::*;
    use crate::gates::QuantumGates;
    use rustc_hash::FxHashSet;

    /// Set up test environment and disable auto-reduction, allowing us to inspect state
    /// and manually trigger reduction rules step by step
    fn setup_test_env(num_qubits: usize) -> PathSum {
        let mut ps = PathSum::new(num_qubits);
        ps.set_auto_reduce(false); 
        ps
    }

    #[test]
    fn test_elim_rule_dead_variable() {
        let mut ps = setup_test_env(1);
        
        // 1. Simulate creation of a decoupled garbage variable (ID: 999)
        // Since we don't add it to F or P, it physically represents an unused loop
        ps.v.path_vars.insert(999);
        
        // 2. Attempt to execute dead variable elimination
        let reducible_vars = ps.get_reducible_vars();
        let reduced = ps.try_reduce_elim(&reducible_vars);
        assert!(reduced, "Elimination rule should trigger for perfectly isolated variables");
        
        // 3. Verify garbage collection accuracy
        assert!(!ps.v.path_vars.contains(&999), "Garbage variable 999 must be eliminated");
        
        // [Safety Guard] Verify input variable x_0 (ID: 0) is NEVER removed by GC
        assert!(ps.v.path_vars.contains(&0), "Input variable x_0 MUST NOT be removed by GC");
    }

    #[test]
    fn test_hh_rule_h_h_identity() {
        let mut ps = setup_test_env(1);
        
        // 1. Construct H-H circuit
        // Initial: F[0] = x_0 (ID: 0)
        ps.apply_h(0); // Generate y_0 (ID: 1)
        ps.apply_h(0); // Generate y_1 (ID: 2)

        // Before reduction: y_0 and y_1 must exist in the variable pool
        assert!(ps.v.path_vars.contains(&1), "y_0 should exist before reduction");
        assert!(ps.v.path_vars.contains(&2), "y_1 should exist before reduction");

        // 2. Manually trigger HH Rule
        let reducible_vars = ps.get_reducible_vars();
        let reduced = ps.try_reduce_hh(&reducible_vars);
        assert!(reduced, "HH rule must successfully trigger on H-H circuit");

        // 3. Verify algebraic state returns perfectly to Identity (I)
        // Variable pool check: y_0 eliminated by integration, y_1 eliminated by substitution
        assert!(!ps.v.path_vars.contains(&1), "y_0 should be eliminated by integration");
        assert!(!ps.v.path_vars.contains(&2), "y_1 should be eliminated by substitution");

        // Boolean basis check: F[0] must perfectly revert to x_0 (i.e., vec![0])
        let mut expected_f = FxHashSet::default();
        expected_f.insert(vec![0]);
        assert_eq!(ps.f.functions[0], expected_f, "F[0] must perfectly return to initial state x_0");

        // Phase check: Phase polynomial P must be completely empty
        assert!(ps.p.terms.is_empty(), "Phase polynomial P must be completely empty");
    }

    #[test]
    fn test_omega_rule_h_s_h() {
        use crate::gates::QuantumGates;
        
        // System has num_qubits = 1.
        // So x_0 has ID = 0.
        // First get_fresh_var() produces y_0 with ID = 1.
        // Second get_fresh_var() produces y_1 with ID = 2.
        let mut ps = PathSum::new(1);
        ps.set_auto_reduce(true);

        ps.apply_h(0); // Produces y_0 (ID: 1)
        ps.apply_s(0); 
        ps.apply_h(0); // Produces y_1 (ID: 2)

        // 1. Verify that y_0 (ID 1) has been successfully eliminated by Omega Rule
        assert!(!ps.v.path_vars.contains(&1), "y_0 should be eliminated by Omega Rule");
        
        // 2. Verify that y_1 (ID 2) still exists (because the state contains X-basis rotation)
        assert!(ps.v.path_vars.contains(&2), "y_1 must remain to represent the superposition");

        // 3. Verify the algebraic structure of P: 3/4 x_0 + 3/4 y_1 + 1/2 x_0 y_1
        assert!(ps.p.terms[&vec![0]].is_pure_three_quarters()); // Coefficient of x_0
        assert!(ps.p.terms[&vec![2]].is_pure_three_quarters()); // Coefficient of y_1
        
        let mut cross = vec![0, 2];
        cross.sort_unstable();
        assert!(ps.p.terms[&cross].is_pure_half()); // Coefficient of cross term x_0 * y_1
    }
}