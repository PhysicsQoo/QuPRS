//! Experimental exact Bra-CX phase substitution; only used when
//! the `bra-cx-exact` feature is active on the isolated experiment branch.
//!
//! Let M = R*x_t, with R free of x_t. Boolean x_t <- x_t XOR x_c gives
//! M -> R*x_t + R*x_c - 2*R*x_t*x_c in the real phase polynomial.
//! If R already contains x_c, idempotence makes this R - R*x_t.
//! All source terms are extracted before any output is inserted, so a newly
//! merged term can never be inadvertently removed later.
//!
//! No f64, angle approximation or change to modulo-one semantics occurs.
use super::{Monomial, PhasePolynomial};
use crate::rational::PhaseCoeff;

impl PhasePolynomial {
    /// Exact x_t <- x_t XOR x_c, specialized for two distinct Boolean
    /// variables of a valid Bra-CX. F-state must still be substituted by the
    /// caller; this method only rewrites the phase polynomial P.
    pub(crate) fn substitute_bra_cx(&mut self, target: u32, control: u32) {
        let completed = self.substitute_bra_cx_checked(target, control, None);
        debug_assert!(completed);
    }

    /// Keep the specialized, exact Bra-CX algebra and its CodSpeed-tested
    /// fast path; only add bounded safe points for verification requests.
    pub(crate) fn substitute_bra_cx_checked(
        &mut self, target: u32, control: u32,
        deadline: Option<std::time::Instant>,
    ) -> bool {
        assert_ne!(target, control, "Bra-CX requires different control/target");
        let expired = || deadline.is_some_and(|d| std::time::Instant::now() >= d);
        if expired() { return false; }

        // Move PhaseCoeff out of the map rather than clone expensive source
        // BigRationals. Crucially remove *all* sources before reinsertion.
        let keys: Vec<Monomial> = self.terms.keys()
            .filter(|mono| mono.contains(&target))
            .cloned()
            .collect();
        if keys.is_empty() { return !expired(); }

        let mut source = Vec::with_capacity(keys.len());
        for (index, key) in keys.into_iter().enumerate() {
            if (index & 63) == 0 && expired() { return false; }
            let entry = self.terms.remove_entry(&key)
                .expect("Bra-CX phase source key must still exist");
            source.push(entry);
        }

        for (index, (term_t, phase)) in source.into_iter().enumerate() {
            if (index & 63) == 0 && expired() { return false; }
            // Input monomials are canonical sorted sets; add_term preserves
            // this invariant after each insertion, including collisions.
            let contains_control = term_t.contains(&control);
            let mut rest = term_t.clone();
            rest.retain(|&v| v != target);

            if contains_control {
                // R contains x_c: R*x_t XOR R*x_c = R*x_t XOR R.
                // As a phase: +phase*R - phase*R*x_t (mod 1).
                let negative = if phase.is_pure_half() {
                    // -1/2 == +1/2 (mod 1); no coefficient arithmetic.
                    phase.clone()
                } else {
                    phase.clone() * -1
                };
                self.add_term(rest, phase);
                self.add_term(term_t, negative);
                continue;
            }

            // R lacks x_c: use the fixed two-term XOR expansion with no DFS,
            // no temporary XOR HashMap, and no repeated Boolean sort/copy.
            // R*x_c and R*x_t*x_c are both Boolean-set unions.
            let mut term_c = rest;
            term_c.push(control);
            let mut term_tc = term_t.clone();
            term_tc.push(control);

            if phase.is_pure_half() {
                // -2 * (1/2) == 0 mod 1 exactly. No third term needed.
                self.add_term(term_c, phase.clone());
                self.add_term(term_t, phase);
            } else {
                let negative_double = phase.clone() * -2;
                self.add_term(term_tc, negative_double);
                self.add_term(term_c, phase.clone());
                self.add_term(term_t, phase);
            }
        }
        !expired()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gates::{QuantumGates, Side};
    use crate::pathsum::PathSum;
    use crate::rational::{Angle, FreeRational, Rational};
    use rustc_hash::FxHashSet;

    fn exact_decimal() -> PhaseCoeff {
        Angle::from_qasm_str("0.12345678901234567890123456789")
            .expect("valid exact decimal QASM source").to_phase_coeff()
    }

    fn phase_options() -> Vec<PhaseCoeff> {
        vec![
            PhaseCoeff::HALF,
            PhaseCoeff::QUARTER,
            PhaseCoeff::new_constant(Rational::new(1, 8)),
            PhaseCoeff::new_constant(Rational::new(1, 3)),
            exact_decimal(),
            PhaseCoeff::new_symbolic(17, FreeRational::new(2, 3)),
        ]
    }

    fn fixture(style: usize, seed: u32) -> PhasePolynomial {
        let choices = phase_options();
        let mut p = PhasePolynomial::new();
        // Systematic canonical monomial sizes with and without control.
        for bitmask in 0..16usize {
            let mut mono = vec![0];
            for k in 0..4 {
                if bitmask & (1 << k) != 0 { mono.push((k + 1) as u32); }
            }
            p.add_term(mono, choices[(bitmask + style) % choices.len()].clone());
        }
        // Extra terms collide with destinations and with one another.
        for bitmask in 0..8usize {
            let mut mono = Vec::new();
            for k in 0..3 {
                if bitmask & (1 << k) != 0 { mono.push((k + 1) as u32); }
            }
            p.add_term(mono, choices[(bitmask + style + seed as usize) % choices.len()].clone());
        }
        p
    }

    fn generic(mut p: PhasePolynomial, target: u32, control: u32) -> PhasePolynomial {
        let xor: FxHashSet<Monomial> = [vec![target], vec![control]]
            .into_iter().collect();
        p.substitute_var_with_poly(target, &xor);
        p
    }

    #[test]
    fn bra_cx_exact_matches_generic_all_coefficient_types_overlaps_and_collisions() {
        for style in 0..phase_options().len() {
            for control in [1u32, 2, 3, 4, 5] {
                for seed in 0..4 {
                    let mut p = fixture(style, seed);
                    let expected = generic(p.clone(), 0, control);
                    p.substitute_bra_cx(0, control);
                    assert_eq!(p.terms, expected.terms,
                        "style={style} seed={seed} control={control}");
                }
            }
        }
    }

    #[test]
    fn bra_cx_exact_handles_zero_one_or_only_unaffected_sources() {
        for n in 0..=1 {
            let mut p = PhasePolynomial::new();
            if n == 1 { p.add_term(vec![0, 1], exact_decimal()); }
            p.add_term(vec![2], PhaseCoeff::QUARTER);
            let want = generic(p.clone(), 0, 1);
            p.substitute_bra_cx(0, 1);
            assert_eq!(p.terms, want.terms);
        }
    }

    #[test]
    fn bra_cx_whole_pathsum_preserves_boolean_state_and_exact_phase() {
        let mut expected = PathSum::new(6);
        expected.p = fixture(2, 3);
        expected.p.add_term(vec![0, 3], exact_decimal());
        let mut actual = expected.clone();
        let xor: FxHashSet<Monomial> = [vec![0], vec![1]].into_iter().collect();
        expected.substitute_var_with_poly(0, &xor);
        actual.apply_cx(1, 0, Side::Bra);
        assert_eq!(actual.p.terms, expected.p.terms);
        assert_eq!(actual.f.functions, expected.f.functions);
    }
}

#[cfg(test)]
mod cooperative_bra_cx_deadline_tests {
    use super::*;
    use crate::rational::{Angle, Rational};
    use std::time::{Duration, Instant};

    fn fixture() -> PhasePolynomial {
        let mut poly = PhasePolynomial::new();
        poly.add_term(vec![0, 1], PhaseCoeff::HALF);
        poly.add_term(vec![0, 2], PhaseCoeff::new_constant(Rational::new(1, 8)));
        poly.add_term(vec![0, 1, 2],
            Angle::from_qasm_str("0.12345678901234567890123456789")
                .expect("source decimal").to_phase_coeff());
        poly
    }

    #[test]
    fn native_exact_bra_cx_is_identical_with_active_budget() {
        let mut expected = fixture();
        let mut actual = expected.clone();
        expected.substitute_bra_cx(0, 1);
        assert!(actual.substitute_bra_cx_checked(
            0, 1, Some(Instant::now() + Duration::from_secs(30)),
        ));
        assert_eq!(actual.terms, expected.terms);
    }

    #[test]
    fn native_exact_bra_cx_rejects_expired_budget_before_mutation() {
        let mut poly = fixture();
        let unchanged = poly.clone();
        assert!(!poly.substitute_bra_cx_checked(
            0, 1, Some(Instant::now() - Duration::from_millis(1)),
        ));
        assert_eq!(poly.terms, unchanged.terms);
    }
}
