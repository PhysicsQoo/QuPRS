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
    pub fn substitute_var_with_poly(
        &mut self, 
        target_var: u32, 
        sub_poly: &FxHashSet<Monomial>
    ) {
        let mut removals = Vec::new();
        let mut additions: Vec<(FxHashSet<Monomial>, PhaseCoeff)> = Vec::new();
        
        for (mono, coeff) in &self.terms {
            if mono.contains(&target_var) {
                removals.push(mono.clone());
                
                let mut rest = mono.clone();
                rest.retain(|&x| x != target_var);
                
                // A singleton Boolean polynomial times sub_poly is just
                // monomial union for each term, with XOR cancellation when
                // multiple unions collapse to the same monomial. Avoid
                // materializing the singleton set and generic nested product.
                let mut boolean_product = FxHashSet::default();
                for sub_term in sub_poly {
                    let product = crate::pathsum::mul_monomials(&rest, sub_term);
                    if !boolean_product.remove(&product) {
                        boolean_product.insert(product);
                    }
                }
                
                // Record the expanded boolean polynomial and corresponding coefficient
                additions.push((boolean_product, coeff.clone()));
            }
        }
        
        // Remove terms containing the old variable
        for m in removals { self.terms.remove(&m); }
        
        // Add back the expanded boolean polynomial to P (will automatically call AddAssign and convert to arithmetic polynomial)
        for (b_poly, coeff) in additions {
            *self += (&b_poly, coeff);
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

impl AddAssign<(&FxHashSet<Monomial>, PhaseCoeff)> for PhasePolynomial {
    fn add_assign(&mut self, (poly, phase): (&FxHashSet<Monomial>, PhaseCoeff)) {
        if poly.is_empty() || phase.is_zero() { return; }

        let max_order = if !phase.symbols.is_empty() || phase.radians.is_some() {
            usize::MAX
        } else {
            let denom_u64 = phase.constant.denom as u64;
            if denom_u64.is_power_of_two() {
                denom_u64.trailing_zeros() as usize
            } else {
                usize::MAX
            }
        };

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
mod substitution_allocation_regressions {
    use super::*;
    use crate::rational::{Angle, FreeRational, Rational};

    // Frozen pre-optimization algorithm: one temporary singleton polynomial,
    // a generic Boolean-ring product and the same arithmetic expansion.
    fn reference_substitution(
        p: &mut PhasePolynomial,
        target: u32,
        replacement: &FxHashSet<Monomial>,
    ) {
        let mut removals = Vec::new();
        let mut additions = Vec::new();
        for (mono, coeff) in &p.terms {
            if mono.contains(&target) {
                removals.push(mono.clone());
                let mut rest = mono.clone();
                rest.retain(|&x| x != target);
                let mut one = FxHashSet::default();
                one.insert(rest);
                additions.push((crate::pathsum::mul_boolean_polys(&one, replacement), coeff.clone()));
            }
        }
        for mono in removals { p.terms.remove(&mono); }
        for (poly, coeff) in additions { *p += (&poly, coeff); }
    }

    fn set(terms: &[&[u32]]) -> FxHashSet<Monomial> {
        terms.iter().map(|mono| mono.to_vec()).collect()
    }

    fn source_polynomial() -> PhasePolynomial {
        let mut p = PhasePolynomial::new();
        p.add_term(vec![0], Angle::from_qasm_str("0.0002").unwrap().to_phase_coeff());
        p.add_term(vec![0, 1], Angle::from_qasm_str("-0.000199999").unwrap().to_phase_coeff());
        p.add_term(vec![0, 2], PhaseCoeff::new_constant(Rational::QUARTER));
        p.add_term(vec![0, 1, 2], Angle::from_qasm_str("pi/8").unwrap().to_phase_coeff());
        p.add_term(vec![1, 3], PhaseCoeff::new_symbolic(19, FreeRational::new(1, 3)));
        p.add_term(vec![0, 3], PhaseCoeff::new_symbolic(20, FreeRational::new(-1, 4)));
        p.add_term(vec![2], Angle::from_qasm_str("1e-100").unwrap().to_phase_coeff());
        p.add_term(vec![], PhaseCoeff::new_constant(Rational::HALF));
        p
    }

    #[test]
    fn phase_substitution_matches_original_for_exact_angles_and_collisions() {
        // Empty/constant/singleton/multi-term replacements, OR collisions,
        // already-present target variables and untouched polynomials.
        for replacement in [
            set(&[]),
            set(&[&[]]),
            set(&[&[1]]),
            set(&[&[1], &[2]]),
            set(&[&[1], &[1, 2]]),
            set(&[&[], &[1], &[2], &[1, 2]]),
            set(&[&[0], &[1]]),
            set(&[&[0, 1], &[1, 2], &[3]]),
        ] {
            for target in [0, 1, 2, 3, 9] {
                let mut expected = source_polynomial();
                let mut optimized = expected.clone();
                reference_substitution(&mut expected, target, &replacement);
                optimized.substitute_var_with_poly(target, &replacement);
                assert_eq!(
                    expected.terms, optimized.terms,
                    "substitution mismatch target={target}, replacement={replacement:?}"
                );
            }
        }
    }

    #[test]
    fn singleton_boolean_product_collisions_cancel_in_gf2() {
        let mut p = PhasePolynomial::new();
        let phase = Angle::from_qasm_str("-1e-100").unwrap().to_phase_coeff();
        p.add_term(vec![0, 1], phase);
        p.substitute_var_with_poly(0, &set(&[&[2], &[1, 2]]));
        assert!(p.terms.is_empty(), "two unions to the same term must cancel");
    }
}
