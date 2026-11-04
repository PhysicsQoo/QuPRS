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

    /// Purely native round-to-nearest binary64 enclosure for the common
    /// source-radian case; the source representation is not changed.
    /// Each i64->f64 cast, rational division, PI constant, sum and nearest-
    /// integer subtraction is bounded by the conservative accumulated error.
    /// We only evaluate inputs whose exact integer numerator and denominator
    /// are representable as i64. All other cases take the certified path.
    /// The distance to the nearest integer is 1-Lipschitz, including wrap.
    fn rr_fast_float_decision(
        coeff: &PhaseCoeff, target: Rational, tolerance: f64,
    ) -> Option<bool> {
        use num_traits::ToPrimitive;
        if tolerance <= 0.0 || !tolerance.is_finite() { return None; }
        if !coeff.symbols.is_empty() { return Some(false); }

        let radians = if let Some(r) = &coeff.radians {
            let numer = r.numer().to_i64()?;
            let denom = r.denom().to_i64()?;
            if denom <= 0 { return None; }
            (numer as f64 / denom as f64) / std::f64::consts::PI
        } else {
            0.0
        };

        let constant = coeff.constant.numer as f64 / coeff.constant.denom as f64;
        let target_cycles = target.numer as f64 / target.denom as f64;
        let delta = (constant + radians) - target_cycles;

        // Avoid integer-spacing amplification and exceptional floating values.
        if !delta.is_finite() || delta.abs() > 1e12 { return None; }
        let distance = (delta - delta.round()).abs();
        // 64*EPSILON comfortably encloses the rounding of two integer casts,
        // division, pi, addition, subtraction and nearest-integer subtraction
        // for finite i64 input fractions and bounded delta. Failure to
        // separate the interval from the configured threshold is NOT a verdict.
        let error = 64.0 * f64::EPSILON
            * (1.0 + constant.abs() + radians.abs() + target_cycles.abs() + delta.abs());
        if !error.is_finite() { return None; }
        if distance + error < tolerance { return Some(true); }
        if distance > tolerance + error { return Some(false); }
        None
    }

    /// Match without rounding the original source. Numeric tolerance is the
    /// policy; the arbitrary-precision pi interval is only a boundary fallback.
    fn rr_matches(&self, coeff: &PhaseCoeff, target: Rational) -> bool {
        if !coeff.symbols.is_empty() { return false; }
        if coeff.radians.is_none() && coeff.constant == target { return true; }
        if self.rr_tolerance == 0.0 { return false; }

        if let Some(classified) =
            Self::rr_fast_float_decision(coeff, target, self.rr_tolerance)
        {
            return classified;
        }

        // Unrepresentable inputs and any boundary overlap preserve the
        // existing full-source certified decision exactly.
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
        crate::phase_cycles_within_tolerance(coeff, target, &tolerance)
    }

    /// Python-equivalent normalization of non-global phase terms.  Global
    /// phase is kept exact, and dropping a nonzero coefficient is recorded.
    fn normalize_rr_non_global(&mut self) {
        if self.rr_tolerance == 0.0 { return; }
        let mut removable: Vec<Monomial> = Vec::new();
        for (index, (monomial, coeff)) in self.p.terms.iter().enumerate() {
            if (index & 63) == 0 && self.verification_deadline.is_some_and(
                |deadline| std::time::Instant::now() >= deadline
            ) {
                self.deadline_exceeded = true;
                return;
            }
            if !monomial.is_empty() && self.rr_matches(coeff, Rational::ZERO) {
                removable.push(monomial.clone());
            }
        }
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
        // The public reduction signature stays unchanged; native verification
        // observes deadline_exceeded and discards the partial residual.
        if !self.poll_verification_deadline() { return; }
        let _timed_reduction = crate::diagnostics::span("reduction");
        // Skip if stats disabled
        if !self.stats.is_enabled() {
            return;
        }

        let mut reduced = true;
        let mut iterations = 0;

        while reduced {
            if !self.poll_verification_deadline() { return; }
            reduced = false;

            // Normalize first: an almost-zero y term may unlock Elim,
            // Omega or HH.  Do not normalize the scalar global phase.
            self.normalize_rr_non_global();
            if !self.poll_verification_deadline() { return; }

            let reducible_vars = self.get_reducible_vars();

            if reducible_vars.is_empty() {
                break;
            }

            if !self.poll_verification_deadline() { return; }
            // Match the Python Path-sum reduction priority: Elim -> Omega -> HH.
            // Restart after each success, so higher-priority rules see the new state.
            if self.try_reduce_elim(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if !self.poll_verification_deadline() { return; }
            if self.try_reduce_omega(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if !self.poll_verification_deadline() { return; }
            if self.try_reduce_hh(&reducible_vars) { reduced = true; iterations += 1; continue; }
            if !self.poll_verification_deadline() { return; }

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
            if !self.poll_verification_deadline() { return false; }
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
            if !self.poll_verification_deadline() { return false; }
            // Step 1: Extract Phi polynomial and verify coefficients
            let mut phi: FxHashSet<Monomial> = FxHashSet::default();
            let mut is_valid_hh = true;
            let mut y_terms_to_remove = Vec::new();
            let mut approximate_match = false;

            for (index, (mono, coeff)) in self.p.terms.iter().enumerate() {
                if (index & 63) == 0 && self.verification_deadline.is_some_and(
                    |deadline| std::time::Instant::now() >= deadline
                ) {
                    self.deadline_exceeded = true;
                    return false;
                }
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
            if self.deadline_exceeded { return false; }

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
        // A quarter-cycle singleton on y is necessary for omega.
        // Reject impossible candidates before scanning unrelated terms.
        let Some(coeff) = self.p.terms.get(&vec![y]) else { return false; };
        if !self.rr_matches(coeff, Rational::QUARTER)
            && !self.rr_matches(coeff, Rational::THREE_QUARTERS)
        {
            return false;
        }
        for (mono, coeff) in &self.p.terms {
            if mono.len() > 1 && mono.contains(&y)
                && !self.rr_matches(coeff, Rational::HALF)
            {
                return false;
            }
        }
        true
    }

    /// Attempt to execute ω-rule (Phase Gadget simplification)
    pub fn try_reduce_omega(&mut self, reducible_vars: &[u32]) -> bool {
        self.stats.record_attempt(RuleType::Omega);
        let mut timer = crate::diagnostics::time_rule("omega", reducible_vars.len());

        let mut target_y = None;
        
        for &var in reducible_vars {
            if !self.poll_verification_deadline() { return false; }
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

        for (index, (mono, coeff)) in self.p.terms.iter().enumerate() {
            if (index & 63) == 0 && self.verification_deadline.is_some_and(
                |deadline| std::time::Instant::now() >= deadline
            ) {
                self.deadline_exceeded = true;
                return false;
            }
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
    fn rr_fast_float_has_positive_negative_and_boundary_paths() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        let below = PhaseCoeff {
            constant: Rational::ZERO,
            radians: Some(BigRational::new(BigInt::from(1), BigInt::from(1_000_000_000_000_i64))),
            symbols: Default::default(),
        };
        let above = PhaseCoeff {
            constant: Rational::ZERO,
            radians: Some(BigRational::new(BigInt::from(1), BigInt::from(1_000_000_i64))),
            symbols: Default::default(),
        };
        assert_eq!(PathSum::rr_fast_float_decision(&below, Rational::ZERO, 1e-10), Some(true));
        assert_eq!(PathSum::rr_fast_float_decision(&above, Rational::ZERO, 1e-10), Some(false));
        let borderline = PhaseCoeff {
            constant: Rational::ZERO,
            // 3.14159265e-10 radians, within <1e-17 cycles of threshold.
            radians: Some(BigRational::new(
                BigInt::from(314_159_265), BigInt::from(1_000_000_000_000_000_000_i64)
            )),
            symbols: Default::default(),
        };
        assert_eq!(PathSum::rr_fast_float_decision(&borderline, Rational::ZERO, 1e-10), None);
    }

    #[test]
    fn rr_fast_float_matches_old_certified_clifford_decisions() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        // Compare against the pre-optimization public math predicate for a
        // varied bounded corpus, including negative phase and wraparound.
        let mut coefficients = vec![
            PhaseCoeff::ZERO, PhaseCoeff::HALF,
            PhaseCoeff::QUARTER, PhaseCoeff::THREE_QUARTERS,
            PhaseCoeff::new_constant(Rational::new(1, 2_000_000_000)),
            PhaseCoeff::new_constant(Rational::new(499_999_999, 1_000_000_000)),
        ];
        for (n, d) in [
            (1_i64, 1_000_000_000_000_i64),
            (-1, 1_000_000_000_000), (1, 1_000_000_000),
            (31415926535897931, 10_000_000_000_000_000),
            (-31415926535897931, 10_000_000_000_000_000),
            (1_619_883_712_007_237, 1_000_000_000_000_000),
            (-2_580_205_812_676_381, 1_000_000_000_000_000),
            (1, 9_000_000_000_000_000_000),
        ] {
            for exact in [Rational::ZERO, Rational::HALF, Rational::QUARTER] {
                coefficients.push(PhaseCoeff {
                    constant: exact,
                    radians: Some(BigRational::new(BigInt::from(n), BigInt::from(d))),
                    symbols: Default::default(),
                });
            }
        }
        let targets = [Rational::ZERO, Rational::HALF,
                       Rational::QUARTER, Rational::THREE_QUARTERS];
        let mut tested = 0;
        let mut fast_accept = 0;
        let mut fast_reject = 0;
        let mut slow_fallback = 0;
        let mut ps = setup_test_env(1);
        for coeff in &coefficients {
            for &target in &targets {
                for tol in [0_f64, 1e-3, 1e-6, 1e-8, 1e-10,
                            1e-12, 1e-16, 1e-20, 1e-35] {
                    ps.rr_tolerance = tol;
                    let baseline = if !coeff.symbols.is_empty() {
                        false
                    } else if coeff.radians.is_none() && coeff.constant == target {
                        true
                    } else if tol == 0.0 {
                        false
                    } else {
                        crate::phase_cycles_within_tolerance(
                            coeff, target,
                            &BigRational::from_float(tol).unwrap(),
                        )
                    };
                    let candidate = ps.rr_matches(coeff, target);
                    assert_eq!(candidate, baseline,
                        "source={:?} target={:?} tol={:?}", coeff, target, tol);
                    if let Some(fast) = PathSum::rr_fast_float_decision(coeff, target, tol) {
                        if fast { fast_accept += 1; } else { fast_reject += 1; }
                    } else { slow_fallback += 1; }
                    tested += 1;
                }
            }
        }
        eprintln!("RR_FAST_PATH_COVERAGE total={tested} accepted={fast_accept} rejected={fast_reject} fallback={slow_fallback}");
        assert!(fast_accept > 20 && fast_reject > 20 && slow_fallback > 20);
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
    fn approximate_hh_reduces_only_when_rr_tolerance_allows_it() {
        let mut ps = setup_test_env(1);
        ps.v.path_vars.insert(1);
        ps.v.path_vars.insert(2);
        ps.p.add_term(
            vec![1, 2],
            PhaseCoeff::new_constant(Rational::new(500_000_001, 1_000_000_000)),
        );
        let candidates = ps.get_reducible_vars();
        let mut exact = ps.clone();
        assert!(!exact.try_reduce_hh(&candidates));
        assert!(!exact.rr_approximate);
        ps.rr_tolerance = 1e-8;
        assert!(ps.try_reduce_hh(&candidates));
        assert!(ps.rr_approximate);
        assert!(ps.p.terms.is_empty());
    }

    #[test]
    fn approximate_omega_respects_exact_zero_tolerance() {
        let mut ps = setup_test_env(1);
        ps.v.path_vars.insert(1);
        ps.p.add_term(
            vec![1],
            PhaseCoeff::new_constant(Rational::new(250_000_001, 1_000_000_000)),
        );
        let candidates = ps.get_reducible_vars();
        let mut exact = ps.clone();
        assert!(!exact.try_reduce_omega(&candidates));
        assert!(!exact.rr_approximate);
        ps.rr_tolerance = 1e-8;
        assert!(ps.try_reduce_omega(&candidates));
        assert!(ps.rr_approximate);
        assert_eq!(
            ps.p.terms.get(&Vec::new()),
            Some(&PhaseCoeff::new_constant(Rational::new(1, 8))),
        );
    }

    #[test]
    fn rr_normalization_drops_non_global_but_keeps_scalar_phase() {
        let mut ps = setup_test_env(1);
        ps.v.path_vars.insert(1);
        let near = PhaseCoeff::new_constant(Rational::new(1, 1_000_000_000));
        ps.p.add_term(vec![1], near.clone());
        ps.p.add_term(vec![], near.clone());
        let mut exact = ps.clone();
        exact.set_auto_reduce(true);
        exact.full_reduce();
        assert!(!exact.rr_approximate);
        assert!(exact.p.terms.contains_key(&vec![1]));

        ps.rr_tolerance = 1e-8;
        ps.set_auto_reduce(true);
        ps.full_reduce();
        assert!(ps.rr_approximate);
        assert!(!ps.p.terms.contains_key(&vec![1]));
        assert_eq!(ps.p.terms.get(&Vec::new()), Some(&near));
        assert!(!ps.v.path_vars.contains(&1));
    }

    #[test]
    fn mixed_radian_source_uses_certified_matching() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        let mut ps = setup_test_env(1);
        let coeff = PhaseCoeff {
            constant: Rational::QUARTER,
            radians: Some(BigRational::new(BigInt::from(1), BigInt::from(10_000_000_000_i64))),
            symbols: Default::default(),
        };
        assert!(!ps.rr_matches(&coeff, Rational::QUARTER));
        ps.rr_tolerance = 1e-10;
        assert!(ps.rr_matches(&coeff, Rational::QUARTER));
        ps.rr_tolerance = 1e-12;
        assert!(!ps.rr_matches(&coeff, Rational::QUARTER));
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

#[cfg(test)]
mod omega_singleton_candidate_tests {
    use super::*;
    fn old_check(ps: &PathSum, y: u32) -> bool {
        let mut has_c0 = false;
        for (m, c) in &ps.p.terms {
            if m.contains(&y) {
                if m.len() == 1 {
                    if ps.rr_matches(c, Rational::QUARTER) ||
                        ps.rr_matches(c, Rational::THREE_QUARTERS) { has_c0 = true; }
                    else { return false; }
                } else if !ps.rr_matches(c, Rational::HALF) { return false; }
            }
        }
        has_c0
    }
    #[test]
    fn eligibility_matches_old_full_scan() {
        let vals = [Rational::ZERO, Rational::HALF, Rational::QUARTER,
            Rational::THREE_QUARTERS,
            Rational::new(250000001, 1000000000),
            Rational::new(500000001, 1000000000)];
        for tol in [0.0, 1e-10, 1e-8] {
            for single in std::iter::once(None).chain(vals.iter().copied().map(Some)) {
                for extra in std::iter::once(None).chain(vals.iter().copied().map(Some)) {
                    let mut ps = PathSum::new(2);
                    ps.rr_tolerance = tol;
                    ps.v.path_vars.insert(2);
                    if let Some(c) = single { ps.p.add_term(vec![2], PhaseCoeff::new_constant(c)); }
                    if let Some(c) = extra { ps.p.add_term(vec![0,2], PhaseCoeff::new_constant(c)); }
                    ps.p.add_term(vec![0], PhaseCoeff::QUARTER);
                    assert_eq!(ps.check_omega_conditions(2), old_check(&ps,2),
                        "tol={tol}, single={single:?}, extra={extra:?}");
                }
            }
        }
    }
}
