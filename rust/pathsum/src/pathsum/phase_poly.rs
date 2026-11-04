// src/pathsum/phase_poly.rs
use rustc_hash::{FxHashMap, FxHashSet};
use std::collections::hash_map::Entry;
use std::ops::AddAssign;

use crate::rational::PhaseCoeff;

pub type Monomial = Vec<u32>;

#[derive(Clone, Debug, Default)]
pub struct PhasePolynomial {
    pub terms: FxHashMap<Monomial, PhaseCoeff>,
}

impl PhasePolynomial {
    pub fn new() -> Self {
        Self { terms: FxHashMap::default() }
    }

    pub fn add_term(&mut self, mut monomial: Monomial, coeff: PhaseCoeff) {
        if coeff.is_zero() { return; }
        monomial.sort_unstable();
        monomial.dedup();
        
        match self.terms.entry(monomial) {
            Entry::Occupied(mut entry) => {
                entry.get_mut().add_assign(coeff);
                if entry.get().is_zero() { entry.remove(); }
            }
            Entry::Vacant(entry) => { entry.insert(coeff); }
        }
    }

    pub fn extract_terms_with_var(&self, var_id: u32) -> Vec<(&Monomial, &PhaseCoeff)> {
        self.terms.iter().filter(|(m, _): &(&Vec<u32>, &PhaseCoeff)| m.contains(&var_id)).collect()
    }

    pub fn get_used_vars(&self) -> rustc_hash::FxHashSet<u32> {
        let mut used_vars = rustc_hash::FxHashSet::default();
        for mono in self.terms.keys() {
            used_vars.extend(mono.iter().copied());
        }
        used_vars
    }
    /// Substitute a Boolean polynomial without cloning source phase coefficients.
    ///
    /// Remove every affected term before reinsertion: inserting early can merge
    /// into a term that still needs to be removed, silently losing its phase.
    /// Legacy public API: an unbounded, source-preserving substitution.
    pub fn substitute_var_with_poly(
        &mut self,
        target_var: u32,
        sub_poly: &FxHashSet<Monomial>,
    ) {
        let completed = self.substitute_var_with_poly_checked(target_var, sub_poly, None);
        debug_assert!(completed);
    }

    /// An interrupted phase polynomial is intentionally not an RR result:
    /// the parent PathSum discards it on timeout. No coefficient is rounded.
    pub(crate) fn substitute_var_with_poly_checked(
        &mut self,
        target_var: u32,
        sub_poly: &FxHashSet<Monomial>,
        deadline: Option<std::time::Instant>,
    ) -> bool {
        let expired = || deadline.is_some_and(|d| std::time::Instant::now() >= d);
        if expired() { return false; }
        // HashMap cannot move out values while iterating borrowed entries.
        // Clone only the keys needed to locate them; move each PhaseCoeff out.
        let keys: Vec<Monomial> = self.terms.keys()
            .filter(|mono| mono.contains(&target_var))
            .cloned()
            .collect();
        if keys.is_empty() { return !expired(); }

        let mut extracted = Vec::with_capacity(keys.len());
        for (index, key) in keys.into_iter().enumerate() {
            if (index & 63) == 0 && expired() { return false; }
            let (mut monomial, coeff) = self.terms.remove_entry(&key)
                .expect("substituted phase term must still exist");
            monomial.retain(|&x| x != target_var);
            extracted.push((monomial, coeff));
        }

        // x <- 0: terms containing x vanish; the other terms stay intact.
        if sub_poly.is_empty() { return !expired(); }

        // x <- monomial: multiplication is a set-union of Boolean variables.
        // No XOR expansion, temporary hash sets, or PhaseCoeff clones needed.
        if sub_poly.len() == 1 {
            let replacement = sub_poly.iter().next().expect("singleton polynomial");
            for (index, (mut monomial, coeff)) in extracted.into_iter().enumerate() {
                if (index & 63) == 0 && expired() { return false; }
                monomial.extend_from_slice(replacement);
                self.add_term(monomial, coeff);
            }
            return !expired();
        }

        // Split the Boolean and phase domains by their true cost:
        // - Clifford/symbolic-only coefficients can profit from reusing one
        //   bounded integer XOR expansion across affected source terms.
        // - An exact-radian coefficient owns a potentially large BigRational.
        //   First multiply AND/XOR over F_2 so duplicate Boolean monomials
        //   cancel BEFORE cloning/scaling any expensive source phase.
        //
        // Mixing exact radians with cheap coefficients is deliberately kept
        // in the parity-first path as a whole. The native CodSpeed Decimal5
        // and Mixed5 witnesses showed substantial regressions when eagerly
        // expanding before these Boolean cancellations.
        //
        // The legacy 12-term bound is a defensive combinatorial cap; never
        // truncate arbitrary-angle terms or change source precision.
        if should_share_xor_expansion(&extracted, sub_poly.len()) {
            let mut expansions: FxHashMap<usize, FxHashMap<Monomial, i64>> =
                FxHashMap::default();
            for (index, (rest, phase)) in extracted.into_iter().enumerate() {
                if (index & 63) == 0 && expired() { return false; }
                let max_order = phase_xor_max_order(&phase);
                if !expansions.contains_key(&max_order) {
                    let Some(result) = expand_xor_to_arithmetic_checked(sub_poly, max_order, deadline)
                    else { return false; };
                    expansions.insert(max_order, result);
                }
                let expanded = &expansions[&max_order];
                for (part_index, (part, &factor)) in expanded.iter().enumerate() {
                    if (part_index & 63) == 0 && expired() { return false; }
                    if factor == 0 { continue; }
                    let mut monomial = rest.clone();
                    monomial.extend_from_slice(part);
                    // add_term canonicalizes the Boolean product and merges
                    // collisions, preserving the exact modulo-one phase.
                    self.add_term(monomial, phase.clone() * factor);
                }
            }
            return !expired();
        }

        // Parity-first: materialize only the surviving Boolean monomials
        // before the arithmetic phase expansion. The single-monomial
        // product avoids allocating a one-element temporary polynomial.
        for (index, (rest, coeff)) in extracted.into_iter().enumerate() {
            if (index & 63) == 0 && expired() { return false; }
            let product = boolean_monomial_xor_product(&rest, sub_poly);
            if product.is_empty() || coeff.is_zero() { continue; }
            let max_order = phase_xor_max_order(&coeff);
            let Some(expanded) = expand_xor_to_arithmetic_checked(&product, max_order, deadline)
            else { return false; };
            for (term_index, (term, factor)) in expanded.into_iter().enumerate() {
                if (term_index & 63) == 0 && expired() { return false; }
                self.add_term(term, coeff.clone() * factor);
            }
        }
        !expired()
    }
}


#[inline]
fn deadline_due(deadline: Option<std::time::Instant>) -> bool {
    deadline.is_some_and(|d| std::time::Instant::now() >= d)
}

/// Cancellation-aware variant of the existing arithmetic XOR expansion.
/// Successful output is bit-for-bit the same coefficient map as the unbounded
/// routine; on timeout the partial map is never observed by the verifier.
fn checked_generate_combinations_dfs(
    repl: &[&Monomial],
    k: usize,
    start_idx: usize,
    current_mono: &Monomial,
    coeff: i64,
    out: &mut FxHashMap<Monomial, i64>,
    deadline: Option<std::time::Instant>,
    visits: &mut usize,
) -> bool {
    *visits = visits.wrapping_add(1);
    if (*visits & 127) == 0 && deadline_due(deadline) { return false; }
    if k == 0 {
        *out.entry(current_mono.clone()).or_insert(0) += coeff;
        return true;
    }
    for i in start_idx..=(repl.len() - k) {
        if (*visits & 127) == 0 && deadline_due(deadline) { return false; }
        let next_mono = crate::pathsum::mul_monomials(current_mono, repl[i]);
        if !checked_generate_combinations_dfs(
            repl, k - 1, i + 1, &next_mono, coeff, out, deadline, visits,
        ) { return false; }
    }
    true
}

fn expand_xor_to_arithmetic_checked(
    xor_terms: &FxHashSet<Monomial>,
    max_order: usize,
    deadline: Option<std::time::Instant>,
) -> Option<FxHashMap<Monomial, i64>> {
    if deadline_due(deadline) { return None; }
    let mut result = FxHashMap::default();
    if xor_terms.is_empty() { return Some(result); }
    let repl_vec: Vec<&Monomial> = xor_terms.iter().collect();
    let max_k = std::cmp::min(max_order, repl_vec.len());
    let mut coeff = 1_i64;
    let mut visits = 0usize;
    for k in 1..=max_k {
        if deadline_due(deadline) { return None; }
        if !checked_generate_combinations_dfs(
            &repl_vec, k, 0, &vec![], coeff, &mut result, deadline, &mut visits,
        ) { return None; }
        coeff *= -2;
    }
    if deadline_due(deadline) { None } else { Some(result) }
}

// The shared path must be cheap for *every* affected term. Otherwise a
// single exact-radian coefficient can force a full expensive expansion
// before Boolean XOR cancellations, as established by native CodSpeed.
#[inline]
fn should_share_xor_expansion(
    extracted: &[(Monomial, PhaseCoeff)],
    xor_terms: usize,
) -> bool {
    extracted.len() > 1
        && xor_terms <= 12
        && extracted.iter().all(|(_, phase)| phase.radians.is_none())
}

// Preserve F_2 parity before invoking any exact-radian phase arithmetic.
// Multiplication by one monomial distributes over XOR. If two products
// coincide by Boolean idempotence, they cancel, not add.
fn boolean_monomial_xor_product(
    rest: &Monomial,
    xor_terms: &FxHashSet<Monomial>,
) -> FxHashSet<Monomial> {
    let mut product = FxHashSet::default();
    for part in xor_terms {
        let combined = crate::pathsum::mul_monomials(rest, part);
        if !product.remove(&combined) {
            product.insert(combined);
        }
    }
    product
}

impl AddAssign<PhaseCoeff> for PhasePolynomial {
    fn add_assign(&mut self, rhs: PhaseCoeff) {
        if !rhs.is_zero() {
            self.add_term(vec![], rhs);
        }
    }
}

// This is also used by the shared XOR expansion above.  Keep the
// truncation rule identical to the original PhasePolynomial AddAssign path.
#[inline]
fn phase_xor_max_order(phase: &PhaseCoeff) -> usize {
    if !phase.symbols.is_empty() || phase.radians.is_some() {
        usize::MAX
    } else {
        let denom_u64 = phase.constant.denom as u64;
        if denom_u64.is_power_of_two() {
            denom_u64.trailing_zeros() as usize
        } else {
            usize::MAX
        }
    }
}

impl AddAssign<(&FxHashSet<Monomial>, PhaseCoeff)> for PhasePolynomial {
    fn add_assign(&mut self, (poly, phase): (&FxHashSet<Monomial>, PhaseCoeff)) {
        if poly.is_empty() || phase.is_zero() { return; }

        let max_order = phase_xor_max_order(&phase);
        let arith_poly = expand_xor_to_arithmetic(poly, max_order);

        for (term, coeff) in arith_poly {
            let final_coeff = phase.clone() * coeff;
            self.add_term(term, final_coeff); 
        }
    }
}

impl AddAssign<(Monomial, PhaseCoeff)> for PhasePolynomial {
    fn add_assign(&mut self, (mono, coeff): (Monomial, PhaseCoeff)) {
        self.add_term(mono, coeff); 
    }
}
fn generate_combinations_dfs(
    repl: &[&Monomial],
    k: usize,
    start_idx: usize,
    current_mono: &Monomial,
    coeff: i64,
    arith_r: &mut FxHashMap<Monomial, i64>,
) {
    if k == 0 {
        *arith_r.entry(current_mono.clone()).or_insert(0) += coeff;
        return;
    }
    for i in start_idx..=(repl.len() - k) {
        let next_mono = crate::pathsum::mul_monomials(current_mono, repl[i]);
        generate_combinations_dfs(repl, k - 1, i + 1, &next_mono, coeff, arith_r);
    }
}

pub fn expand_xor_to_arithmetic(
    xor_terms: &FxHashSet<Monomial>,
    max_order: usize,
) -> FxHashMap<Monomial, i64> {
    let mut arith_poly = FxHashMap::default();
    if xor_terms.is_empty() {
        return arith_poly;
    }

    let repl_vec: Vec<&Monomial> = xor_terms.iter().collect();
    let n = repl_vec.len();
    
    let max_k = std::cmp::min(max_order, n);

    let mut current_coeff = 1_i64;
    for k in 1..=max_k {
        generate_combinations_dfs(&repl_vec, k, 0, &vec![], current_coeff, &mut arith_poly);
        current_coeff *= -2; 
    }

    arith_poly
}
#[cfg(test)]
mod substitution_tests {
    use super::*;
    use crate::rational::{Angle, FreeRational, Rational};

    // Unoptimized algorithm preserved as a test-only semantic oracle.
    fn legacy_substitute(
        poly: &mut PhasePolynomial,
        target: u32,
        substitution: &FxHashSet<Monomial>,
    ) {
        let mut removals = Vec::new();
        let mut additions: Vec<(FxHashSet<Monomial>, PhaseCoeff)> = Vec::new();
        for (monomial, coeff) in &poly.terms {
            if monomial.contains(&target) {
                removals.push(monomial.clone());
                let mut rest = monomial.clone();
                rest.retain(|&id| id != target);
                let mut rest_poly = FxHashSet::default();
                rest_poly.insert(rest);
                additions.push((
                    crate::pathsum::mul_boolean_polys(&rest_poly, substitution),
                    coeff.clone(),
                ));
            }
        }
        for monomial in removals {
            poly.terms.remove(&monomial);
        }
        for (product, coeff) in additions {
            *poly += (&product, coeff);
        }
    }

    fn source_polynomial() -> PhasePolynomial {
        let mut poly = PhasePolynomial::new();
        poly.add_term(vec![0], PhaseCoeff::HALF);
        poly.add_term(
            vec![0, 1],
            Angle::from_qasm_str("0.12345678901234567890123456789")
                .expect("exact decimal").to_phase_coeff(),
        );
        poly.add_term(
            vec![0, 2],
            PhaseCoeff::new_symbolic(17, FreeRational::new(2, 3)),
        );
        poly.add_term(vec![0, 1, 2], PhaseCoeff::QUARTER);
        poly.add_term(vec![1], PhaseCoeff::THREE_QUARTERS);
        poly.add_term(vec![2], PhaseCoeff::new_constant(Rational::new(1, 8)));
        poly
    }

    #[test]
    fn substituted_polynomials_match_original_for_zero_singleton_and_xor() {
        let substitutions: Vec<Vec<Monomial>> = vec![
            vec![],                      // x <- 0
            vec![vec![]],                 // x <- 1
            vec![vec![2]],                // x <- z (collisions)
            vec![vec![1, 2]],             // x <- yz (overlap)
            vec![vec![], vec![1]],        // x <- 1 XOR y
            vec![vec![1], vec![2]],       // x <- y XOR z
            vec![vec![1], vec![1, 2]],    // x <- y XOR yz
            vec![vec![], vec![1], vec![2]],
        ];
        for target in [0, 1, 2, 3] {
            for terms in &substitutions {
                let substitution: FxHashSet<Monomial> =
                    terms.iter().cloned().collect();
                let mut expected = source_polynomial();
                let mut candidate = expected.clone();
                legacy_substitute(&mut expected, target, &substitution);
                candidate.substitute_var_with_poly(target, &substitution);
                assert_eq!(
                    candidate.terms, expected.terms,
                    "target={target}, substitution={terms:?}",
                );
            }
        }
    }

    #[test]
    fn shared_xor_expansion_matches_legacy_for_exact_and_symbolic_phases() {
        // Multiple source terms force the shared-expansion path.  The
        // substitutions include collisions under AND, an empty monomial,
        // and three-plus XOR terms.  Coefficients cover all truncation
        // orders, exact decimal radians, and free phase symbols.
        let substitutions: Vec<Vec<Monomial>> = vec![
            vec![vec![], vec![1], vec![2]],
            vec![vec![1], vec![2], vec![3]],
            vec![vec![1], vec![1, 2], vec![2, 3], vec![3]],
            vec![vec![], vec![1], vec![2], vec![3], vec![1, 3]],
            vec![vec![1], vec![1, 2], vec![2, 3], vec![1, 3], vec![3]],
        ];
        for target in [0, 1, 2, 3] {
            for terms in &substitutions {
                let replacement: FxHashSet<Monomial> =
                    terms.iter().cloned().collect();
                let mut expected = source_polynomial();
                // Vary the number of affected terms and force term merges
                // across both the original and replacement variables.
                expected.add_term(vec![target, 4],
                    PhaseCoeff::new_constant(Rational::new(1, 16)));
                expected.add_term(vec![target, 5],
                    PhaseCoeff::new_constant(Rational::new(1, 3)));
                expected.add_term(vec![target, 1, 6],
                    Angle::from_qasm_str("0.00000000000000000000000012345")
                        .expect("exact decimal").to_phase_coeff());
                expected.add_term(vec![target, 2, 7],
                    PhaseCoeff::new_symbolic(19, FreeRational::new(5, 7)));
                let mut candidate = expected.clone();
                legacy_substitute(&mut expected, target, &replacement);
                candidate.substitute_var_with_poly(target, &replacement);
                assert_eq!(candidate.terms, expected.terms,
                    "target={target}, replacement={terms:?}");
            }
        }
    }

    #[test]
    fn parity_first_gate_avoids_expensive_exact_radians() {
        let exact = Angle::from_qasm_str("0.12345678901234567890123456789")
            .expect("exact QASM decimal").to_phase_coeff();
        let symbolic = PhaseCoeff::new_symbolic(17, FreeRational::HALF);
        let clifford = PhaseCoeff::HALF;

        let cheap = vec![(vec![1], clifford.clone()), (vec![2], symbolic.clone())];
        assert!(should_share_xor_expansion(&cheap, 5));
        assert!(!should_share_xor_expansion(&cheap, 13));
        assert!(!should_share_xor_expansion(&cheap[..1], 5));

        let exact_only = vec![(vec![1], exact.clone()), (vec![2], exact.clone())];
        let mixed = vec![(vec![1], clifford), (vec![2], exact), (vec![3], symbolic)];
        assert!(!should_share_xor_expansion(&exact_only, 5));
        assert!(!should_share_xor_expansion(&mixed, 5));
    }

    #[test]
    fn parity_first_monomial_product_matches_boolean_ring_with_collisions() {
        let substitutions: Vec<Vec<Monomial>> = vec![
            vec![vec![1], vec![2], vec![1, 2]],
            vec![vec![], vec![1], vec![2], vec![1, 2]],
            vec![vec![1], vec![1, 3], vec![2, 3], vec![3], vec![1, 2, 3]],
        ];
        for terms in substitutions {
            let sub_poly: FxHashSet<Monomial> = terms.into_iter().collect();
            for rest in [vec![], vec![1], vec![1, 3], vec![2, 3], vec![1, 2, 3]] {
                let direct = boolean_monomial_xor_product(&rest, &sub_poly);
                let singleton: FxHashSet<Monomial> = [rest.clone()].into_iter().collect();
                let reference = crate::pathsum::mul_boolean_polys(&singleton, &sub_poly);
                assert_eq!(direct, reference, "rest={rest:?}");
            }
        }
    }

    #[test]
    fn singleton_substitution_merges_only_after_all_sources_are_removed() {
        let mut poly = PhasePolynomial::new();
        poly.add_term(vec![0], PhaseCoeff::HALF);
        poly.add_term(vec![0, 2], PhaseCoeff::HALF);
        poly.add_term(vec![2], PhaseCoeff::QUARTER);
        let substitution: FxHashSet<Monomial> = [vec![2]].into_iter().collect();
        poly.substitute_var_with_poly(0, &substitution);
        assert_eq!(poly.terms.len(), 1);
        assert_eq!(poly.terms.get(&vec![2]), Some(&PhaseCoeff::QUARTER));
    }

    #[test]
    fn xor_product_cancels_duplicate_boolean_monomials() {
        let mut poly = PhasePolynomial::new();
        poly.add_term(vec![0, 2], PhaseCoeff::HALF);
        let substitution: FxHashSet<Monomial> =
            [vec![1], vec![1, 2]].into_iter().collect();
        // (z AND y) XOR (z AND y AND z) = 0 in Boolean algebra.
        poly.substitute_var_with_poly(0, &substitution);
        assert!(poly.terms.is_empty());
    }
}

#[cfg(test)]
mod cooperative_phase_substitution_tests {
    use super::*;
    use crate::rational::{Angle, Rational};
    use std::time::{Duration, Instant};

    #[test]
    fn bounded_exact_decimal_and_clifford_xor_match_original() {
        let replacement: FxHashSet<Monomial> = [
            vec![], vec![1], vec![2], vec![1, 2],
        ].into_iter().collect();
        let mut original = PhasePolynomial::new();
        original.add_term(vec![0, 1], PhaseCoeff::HALF);
        original.add_term(vec![0, 2], PhaseCoeff::new_constant(Rational::new(1, 8)));
        original.add_term(vec![0, 3],
            Angle::from_qasm_str("0.12345678901234567890123456789")
                .expect("source decimal").to_phase_coeff());
        let mut checked = original.clone();
        original.substitute_var_with_poly(0, &replacement);
        assert!(checked.substitute_var_with_poly_checked(
            0, &replacement, Some(Instant::now() + Duration::from_secs(30)),
        ));
        assert_eq!(checked.terms, original.terms);
    }

    #[test]
    fn expired_phase_expansion_fails_closed() {
        let mut poly = PhasePolynomial::new();
        poly.add_term(vec![0], PhaseCoeff::HALF);
        let original = poly.clone();
        let replacement: FxHashSet<Monomial> =
            [vec![1], vec![2]].into_iter().collect();
        assert!(!poly.substitute_var_with_poly_checked(
            0, &replacement, Some(Instant::now() - Duration::from_millis(1)),
        ));
        assert_eq!(poly.terms, original.terms);
    }

    #[test]
    fn recursive_xor_expansion_observes_budget() {
        let terms: FxHashSet<Monomial> =
            (1..=20).map(|v| vec![v]).collect();
        // With twenty independent Boolean terms, a full expansion has
        // 2^20-1 subsets. An expired budget must never return a partial map.
        let expired = Instant::now() - Duration::from_millis(1);
        assert!(expand_xor_to_arithmetic_checked(
            &terms, usize::MAX, Some(expired),
        ).is_none());

        // Force the deadline to expire *inside* the recursive traversal.
        // Its first check occurs at the 128th visited node, not at entry.
        let refs: Vec<&Monomial> = terms.iter().collect();
        let mut visited = 0usize;
        let mut partial = FxHashMap::default();
        assert!(!checked_generate_combinations_dfs(
            &refs, 10, 0, &vec![], 1, &mut partial, Some(expired), &mut visited,
        ));
        assert!(visited >= 128 && visited < 256, "visited={visited}");

        let small: FxHashSet<Monomial> =
            [vec![1], vec![2], vec![1, 2]].into_iter().collect();
        let reference = expand_xor_to_arithmetic(&small, usize::MAX);
        let candidate = expand_xor_to_arithmetic_checked(
            &small, usize::MAX, Some(Instant::now() + Duration::from_secs(30)),
        ).expect("unexpired exact expansion");
        assert_eq!(candidate, reference);
    }
}
