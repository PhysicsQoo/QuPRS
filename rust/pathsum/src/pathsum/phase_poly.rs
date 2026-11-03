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
    pub fn substitute_var_with_poly(
        &mut self,
        target_var: u32,
        sub_poly: &FxHashSet<Monomial>,
    ) {
        // HashMap cannot move out values while iterating borrowed entries.
        // Clone only the keys needed to locate them; move each PhaseCoeff out.
        let keys: Vec<Monomial> = self.terms.keys()
            .filter(|mono| mono.contains(&target_var))
            .cloned()
            .collect();
        if keys.is_empty() { return; }

        let mut extracted = Vec::with_capacity(keys.len());
        for key in keys {
            let (mut monomial, coeff) = self.terms.remove_entry(&key)
                .expect("substituted phase term must still exist");
            monomial.retain(|&x| x != target_var);
            extracted.push((monomial, coeff));
        }

        // x <- 0: terms containing x vanish; the other terms stay intact.
        if sub_poly.is_empty() { return; }

        // x <- monomial: multiplication is a set-union of Boolean variables.
        // No XOR expansion, temporary hash sets, or PhaseCoeff clones needed.
        if sub_poly.len() == 1 {
            let replacement = sub_poly.iter().next().expect("singleton polynomial");
            for (mut monomial, coeff) in extracted {
                monomial.extend_from_slice(replacement);
                self.add_term(monomial, coeff);
            }
            return;
        }

        // For several affected terms, expand the *same* XOR replacement only
        // once per coefficient truncation order.  Over the Boolean ring,
        // rest AND (a XOR b) = (rest AND a) XOR (rest AND b), and the
        // arithmetic expansion distributes through the AND.  The omitted
        // higher-order terms are multiples of 1 in the phase when a
        // power-of-two denominator permits truncation.
        //
        // Keep the original path for singleton sources and large XORs:
        // the pre-expansion can otherwise grow exponentially even when
        // multiplication by 'rest' would cancel many Boolean terms.
        if extracted.len() > 1 && sub_poly.len() <= 12 {
            let mut expansions: FxHashMap<usize, FxHashMap<Monomial, i64>> =
                FxHashMap::default();
            for (rest, phase) in extracted {
                let max_order = phase_xor_max_order(&phase);
                let expanded = expansions.entry(max_order)
                    .or_insert_with(|| expand_xor_to_arithmetic(sub_poly, max_order));
                for (part, &factor) in expanded.iter() {
                    if factor == 0 { continue; }
                    let mut monomial = rest.clone();
                    monomial.extend_from_slice(part);
                    // add_term canonicalizes the Boolean product and merges
                    // collisions, preserving the exact modulo-one phase.
                    self.add_term(monomial, phase.clone() * factor);
                }
            }
            return;
        }

        // Fallback: preserve the established parity-first path.
        for (rest, coeff) in extracted {
            let mut rest_poly = FxHashSet::default();
            rest_poly.insert(rest);
            let product = crate::pathsum::mul_boolean_polys(&rest_poly, sub_poly);
            *self += (&product, coeff);
        }
    }
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
