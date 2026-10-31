// src/reduction.rs
use rustc_hash::FxHashSet;
use log::{debug, trace};
use crate::pathsum::{PathSum, Monomial};
use crate::rational::{PhaseCoeff, Rational};
use crate::stats::RuleType;

impl PathSum {
    /// Match a Clifford phase in cycles without rounding the source angle.
    /// The binary64 estimate is only a cheap rejection filter; acceptance
    /// always uses a certified rational interval for the original source.
    fn rr_matches(&self, coeff: &PhaseCoeff, target: Rational) -> bool {
        if !coeff.symbols.is_empty() { return false; }
        if coeff.radians.is_none() && coeff.constant == target { return true; }
        if self.rr_tolerance == 0.0 { return false; }

        // Avoid arbitrary-precision work for the common far-from-Clifford case.
        let radians = coeff.radians.as_ref().and_then(num_traits::ToPrimitive::to_f64);
        if coeff.radians.is_none() || radians.is_some_and(f64::is_finite) {
            let cycles = coeff.constant.numer as f64 / coeff.constant.denom as f64
                + radians.unwrap_or(0.0) / std::f64::consts::PI;
            let expected = target.numer as f64 / target.denom as f64;
            if cycles.is_finite() && cycles.abs() < 1e12 {
                let delta = (cycles - expected).rem_euclid(1.0);
                let distance = delta.min(1.0 - delta);
                let uncertainty = 256.0 * f64::EPSILON * (1.0 + cycles.abs());
                if distance > self.rr_tolerance + uncertainty { return false; }
            }
        }

        let Some(tolerance) = num_rational::BigRational::from_float(self.rr_tolerance) else {
            return false;
        };
        crate::phase_cycles_upper_target(coeff, target) <= tolerance
    }

    /// Python-equivalent normalization of non-global phase terms.  Global
    /// phase is kept exact, and dropping a nonzero coefficient is recorded.
    fn normalize_rr_non_global(&mut self) {
        if self.rr_tolerance == 0.0 { return; }
        let removable: Vec<Monomial> = self.p.terms.iter()
            .filter(|(monomial, coeff)| {
                !monomial.is_empty() && self.rr_matches(coeff, Rational::ZERO)
            })
            .map(|(monomial, _)| monomial.clone())
            .collect();
        if !removable.is_empty() {
            self.rr_approximate = true;
            for monomial in removable { self.p.terms.remove(&monomial); }
        }
    }

    pub fn get_reducible_vars(&self) -> Vec<u32> {
        let mut timer = crate::diagnostics::time_rule("candidate_discovery", 0);
        let f_used_vars = self.f.get_used_vars();
        let mut reducible_vars: Vec<u32> = self.v.path_vars.iter()
            .copied()
            .filter(|&v| (v as usize) >= self.v.num_qubits && !f_used_vars.contains(&v))
            .collect();
        
        reducible_vars.sort_unstable_by(|a, b| b.cmp(a));
        if let Some(clock) = timer.as_mut() {
            clock.set_candidates(reducible_vars.len());
            if !reducible_vars.is_empty() { clock.mark_success(); }
        }
        reducible_vars
    }

    pub fn full_reduce(&mut self) {
        let _timed_reduction = crate::diagnostics::span("reduction");
        // Skip if stats disabled
        if !self.stats.is_enabled() {
            return;
        }

        let mut reduced = true;
        let mut iterations = 0;

        while reduced {
            reduced = false;

            // Normalize first: an almost-zero y term may unlock Elim,
            // Omega or HH.  Do not normalize the scalar global phase.
            self.normalize_rr_non_global();

            let reducible_vars = self.get_reducible_vars();

            if reducible_vars.is_empty() {
                break;
            }

            // Match the Python Path-sum reduction priority: Elim -> Omega -> HH.
            // Restart after each success, so higher-priority rules see the new state.
            if self.try_reduce_elim(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if self.try_reduce_omega(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if self.try_reduce_hh(&reducible_vars) { reduced = true; iterations += 1; continue; }

            if iterations > 0 {
                trace!(">> [Full Reduce] System converged after {} reduction steps.", iterations);
            }
        }
    }

    pub fn try_reduce_elim(&mut self, reducible_vars: &[u32]) -> bool {
        self.stats.record_attempt(RuleType::Elim);
        let mut timed_elim = crate::diagnostics::observe_elim_attempt(|| {
            let k_r = reducible_vars.len();
            let d_r = self.p.terms.len();
            let l_r = self.p.terms.keys().map(|mono| mono.len()).sum();
            // Count live internal IDs directly; total set size can shrink.
            let v_r = self.v.path_vars.iter()
                .filter(|&&id| (id as usize) >= self.v.num_qubits)
                .count();
            (k_r, l_r, v_r, d_r)
        });

        // Find completely isolated internal variables
        let mut vars_to_remove = Vec::new();
        // The phase polynomial is unchanged while scanning candidates.
        // Build the used-variable set once per Elim attempt, not once per variable.
        let used_vars = self.p.get_used_vars();
        for &var in reducible_vars {
            if !used_vars.contains(&var) {
                vars_to_remove.push(var);
            }
        }

        if vars_to_remove.is_empty() {
            return false;
        }

        for var in &vars_to_remove {
            self.v.path_vars.remove(var);
            debug!("[Elimination] Removed decoupled path variable: {}", self.v.fmt_var(*var));
        }

        self.stats.record_success(RuleType::Elim);
        if let Some(timer) = timed_elim.as_mut() {
            timer.mark_success();
        }
        true
    }

    /// Attempt to execute HH Rule (Feynman path cancellation)
    pub fn try_reduce_hh(&mut self, reducible_vars: &[u32]) -> bool {
        self.stats.record_attempt(RuleType::HH);
        let mut timer = crate::diagnostics::time_rule("hh", reducible_vars.len());

        for &var in reducible_vars {
            // Step 1: Extract Phi polynomial and verify coefficients
            let mut phi: FxHashSet<Monomial> = FxHashSet::default();
            let mut is_valid_hh = true;
            let mut y_terms_to_remove = Vec::new();
            let mut approximate_match = false;

            for (mono, coeff) in &self.p.terms {
                if mono.contains(&var) {
                    if !self.rr_matches(coeff, Rational::HALF) {
                        is_valid_hh = false;
                        break;
                    }
                    approximate_match |= !coeff.is_pure_half();
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

            // Step 2: Select substitution variable v from Phi
            let mut target_v = None;
            for term in &phi {
                if term.len() == 1 {
                    let var = term[0];
                    
                    // Validate: v cannot be present in other terms of phi.
                    // If it is, `replacement` would depend on `v`, causing infinite recursion
                    // or leaving `v` un-eliminated in F.
                    let mut var_in_replacement = false;
                    for other_term in &phi {
                        if other_term != term && other_term.contains(&var) {
                            var_in_replacement = true;
                            break;
                        }
                    }
                    
                    if !var_in_replacement {
                        if target_v.map_or(true, |max_v| var > max_v) {
                            target_v = Some(var);
                        }
                    }
                }
            }

            let v = match target_v {
                Some(var) => var,
                None => continue,
            };

            // Substitution expression R = Phi \ {v}
            let mut replacement = phi.clone();
            replacement.remove(&vec![v]);

            debug!("[HH Rule] Integrator y: {}, Target v: {} -> {}", 
                    self.v.fmt_var(var), 
                    self.v.fmt_var(v), 
                    self.v.fmt_polynomial(&replacement));

            // Step 3: Perform variable substitution
            for mono in &y_terms_to_remove {
                self.p.terms.remove(mono);
            }

            self.substitute_var_with_poly(v, &replacement);
            
            // Step 4: Garbage collection
            self.v.path_vars.remove(&var);
            
            if (v as usize) >= self.v.num_qubits {
                self.v.path_vars.remove(&v);
            }
            
            self.rr_approximate |= approximate_match;
            self.stats.record_success(RuleType::HH);
            if let Some(clock) = timer.as_mut() { clock.mark_success(); }
            return true;
        }
        false
    }

    fn check_omega_conditions(&self, y: u32) -> bool {
        let mut has_c0 = false;
        for (mono, coeff) in &self.p.terms {
            if mono.contains(&y) {
                if mono.len() == 1 {
                    if self.rr_matches(coeff, Rational::QUARTER) || self.rr_matches(coeff, Rational::THREE_QUARTERS) {
                        has_c0 = true;
                    } else {
                        return false; 
                    }
                } else {
                    if !self.rr_matches(coeff, Rational::HALF) {
                        return false; 
                    }
                }
            }
        }
        has_c0
    }

    /// Attempt to execute ω-rule (Phase Gadget simplification)
    pub fn try_reduce_omega(&mut self, reducible_vars: &[u32]) -> bool {
        self.stats.record_attempt(RuleType::Omega);
        let mut timer = crate::diagnostics::time_rule("omega", reducible_vars.len());

        let mut target_y = None;
        
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
        let mut c0 = Rational::ZERO;
        let mut y_terms_to_remove = Vec::new();
        let mut approximate_match = false;

        for (mono, coeff) in &self.p.terms {
            if mono.contains(&y) {
                y_terms_to_remove.push(mono.clone());
                if mono.len() == 1 {
                    c0 = if self.rr_matches(coeff, Rational::QUARTER) { Rational::QUARTER } else { Rational::THREE_QUARTERS };
                    approximate_match |= !coeff.is_pure_fraction(c0.numer, c0.denom);
                } else {
                    approximate_match |= !coeff.is_pure_half();
                    let mut phi_term = mono.clone();
                    phi_term.retain(|&v| v != y);
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

        // 3. Compute new phase
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
        
        debug!("[Omega Rule] Integrated out variable: {} (generated Phase Gadget)", self.v.fmt_var(y));

        self.rr_approximate |= approximate_match;
        self.stats.record_success(RuleType::Omega);
        if let Some(clock) = timer.as_mut() { clock.mark_success(); }
        true
    }
}

#[cfg(test)] 
mod tests {
    use super::*;
    use crate::gates::{QuantumGates, Side};
    use rustc_hash::FxHashSet;

    /// Set up test environment with auto-reduction disabled
    fn setup_test_env(num_qubits: usize) -> PathSum {
        let mut ps = PathSum::new(num_qubits);
        ps.set_auto_reduce(false); 
        ps
    }

    #[test]
    fn rr_tolerance_zero_is_exact_and_positive_tolerance_matches() {
        let mut ps = setup_test_env(1);
        let near = PhaseCoeff::new_constant(Rational::new(500_000_001, 1_000_000_000));
        assert!(!ps.rr_matches(&near, Rational::HALF));
        ps.rr_tolerance = 1e-8;
        assert!(ps.rr_matches(&near, Rational::HALF));
        ps.rr_tolerance = 1e-12;
        assert!(!ps.rr_matches(&near, Rational::HALF));
        assert!(ps.rr_matches(&PhaseCoeff::HALF, Rational::HALF));
    }

    #[test]
    fn rr_tolerance_never_matches_unbound_symbolic_phase() {
        use crate::rational::FreeRational;
        let mut ps = setup_test_env(1);
        ps.rr_tolerance = 0.1;
        let symbolic = PhaseCoeff::new_symbolic(17, FreeRational::HALF);
        assert!(!ps.rr_matches(&symbolic, Rational::HALF));
    }

    #[test]
    fn test_elim_rule_dead_variable() {
        let mut ps = setup_test_env(1);
        
        // Create a decoupled garbage variable (ID: 999)
        ps.v.path_vars.insert(999);
        
        let reducible_vars = ps.get_reducible_vars();
        let reduced = ps.try_reduce_elim(&reducible_vars);
        assert!(reduced, "Elimination rule should trigger for isolated variables");
        
        assert!(!ps.v.path_vars.contains(&999), "Garbage variable 999 must be eliminated");
        assert!(ps.v.path_vars.contains(&0), "Input variable x_0 MUST NOT be removed");
    }

    #[test]
    fn test_hh_rule_h_h_identity() {
        let mut ps = setup_test_env(1);
        
        // Construct H-H circuit
        ps.apply_h(0, Side::Ket); // Generate y_0 (ID: 1)
        ps.apply_h(0, Side::Ket); // Generate y_1 (ID: 2)

        assert!(ps.v.path_vars.contains(&1), "y_0 should exist before reduction");
        assert!(ps.v.path_vars.contains(&2), "y_1 should exist before reduction");

        let reducible_vars = ps.get_reducible_vars();
        let reduced = ps.try_reduce_hh(&reducible_vars);
        assert!(reduced, "HH rule must successfully trigger on H-H circuit");

        assert!(!ps.v.path_vars.contains(&1), "y_0 should be eliminated");
        assert!(!ps.v.path_vars.contains(&2), "y_1 should be eliminated");

        let mut expected_f = FxHashSet::default();
        expected_f.insert(vec![0]);
        assert_eq!(ps.f.functions[0], expected_f, "F[0] must return to x_0");

        assert!(ps.p.terms.is_empty(), "Phase polynomial P must be empty");
    }

    #[test]
    fn test_omega_rule_h_s_h() {
        use crate::gates::QuantumGates;
        
        let mut ps = PathSum::new(1);
        ps.set_auto_reduce(true);

        ps.apply_h(0, Side::Ket); // Produces y_0 (ID: 1)
        ps.apply_s(0, Side::Ket); 
        ps.apply_h(0, Side::Ket); // Produces y_1 (ID: 2)

        assert!(!ps.v.path_vars.contains(&1), "y_0 should be eliminated by Omega Rule");
        assert!(ps.v.path_vars.contains(&2), "y_1 must remain for superposition");

        assert!(ps.p.terms[&vec![0]].is_pure_three_quarters());
        assert!(ps.p.terms[&vec![2]].is_pure_three_quarters());
        
        let mut cross = vec![0, 2];
        cross.sort_unstable();
        assert!(ps.p.terms[&cross].is_pure_half());
    }
}
