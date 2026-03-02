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
        self.terms.iter().filter(|(m, _)| m.contains(&var_id)).collect()
    }

    pub fn get_used_vars(&self) -> rustc_hash::FxHashSet<u32> {
        let mut used_vars = rustc_hash::FxHashSet::default();
        for mono in self.terms.keys() {
            used_vars.extend(mono.iter().copied());
        }
        used_vars
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