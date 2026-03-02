// src/pathsum/mod.rs
#![allow(dead_code)]
pub mod phase_poly;
pub mod boolean_state;
pub mod var_manager;

pub use phase_poly::{PhasePolynomial, Monomial};
pub use boolean_state::{BooleanState, Register};
pub use var_manager::VariableManager;

use rustc_hash::FxHashSet; 

pub fn mul_monomials(m1: &Monomial, m2: &Monomial) -> Monomial {
    let mut result = m1.clone();
    result.extend_from_slice(m2);
    result.sort_unstable(); 
    result.dedup();
    result
}

pub fn mul_boolean_polys(poly1: &FxHashSet<Monomial>, poly2: &FxHashSet<Monomial>) -> FxHashSet<Monomial> {
    let mut result = FxHashSet::default();
    
    for m1 in poly1 {
        for m2 in poly2 {
            let m = crate::pathsum::mul_monomials(m1, m2);
            if result.contains(&m) {
                result.remove(&m);
            } else {
                result.insert(m);
            }
        }
    }
    
    result
}

use std::sync::atomic::{AtomicBool, Ordering};
pub static GLOBAL_AUTO_REDUCE: AtomicBool = AtomicBool::new(true);
pub struct PathSum {
    pub p: PhasePolynomial,
    pub f: BooleanState,
    pub v: VariableManager,
    pub auto_reduce: bool,
}

impl PathSum {
    pub fn new(num_qubits: usize) -> Self {
        Self {
            p: PhasePolynomial::new(),
            f: BooleanState::new(num_qubits),
            v: VariableManager::new(num_qubits),
            auto_reduce: GLOBAL_AUTO_REDUCE.load(Ordering::Relaxed),
        }
    }
    pub fn set_global_auto_reduce(enable: bool) {
        GLOBAL_AUTO_REDUCE.store(enable, Ordering::Relaxed);
    }
    pub fn set_auto_reduce(&mut self, enable: bool) {
        self.auto_reduce = enable;
        if enable {
            self.full_reduce();
        }
    }
    pub fn quantum_circuit(regs: &[Register], initial_state: Option<&[u8]>) -> Self {
        let total_qubits: usize = regs.iter().map(|r| r.size).sum();
        
        let mut ps = Self {
            p: PhasePolynomial::new(),
            f: BooleanState::new_with_regs(regs),
            v: VariableManager::new(total_qubits),
            auto_reduce: GLOBAL_AUTO_REDUCE.load(std::sync::atomic::Ordering::Relaxed),
        };

        if let Some(state) = initial_state {
            ps.set_initial_state(state);
        }
        ps
    }
    /// Set the initial quantum state (e.g., |010> passed as &[0, 1, 0]).
    /// This triggers algebraic substitution across both Phase Polynomial (P) and Boolean State (F).
    pub fn set_initial_state(&mut self, state: &[u8]) {
        assert_eq!(state.len(), self.v.num_qubits, "Length of initial state must match total number of qubits.");

        for (i, &val) in state.iter().enumerate() {
            let x_i = i as u32; // The ID of the input variable x_i is exactly i
            
            match val {
                0 => self.substitute_zero(x_i),
                1 => self.substitute_one(x_i),
                _ => panic!("Initial state values must be 0 or 1."),
            }
        }

        // Trigger full reduction to perform garbage collection on newly isolated internal variables.
        if self.auto_reduce {
            self.full_reduce();
        }
    }

    /// Perform algebraic substitution: x_i = 0
    fn substitute_zero(&mut self, var: u32) {
        // 1. Update Boolean State (F): Remove any term containing x_i (since AND with 0 is 0)
        for poly in &mut self.f.functions {
            poly.retain(|term| !term.contains(&var));
        }

        // 2. Update Phase Polynomial (P): Remove any monomial containing x_i
        let mut keys_to_remove = Vec::new();
        for mono in self.p.terms.keys() {
            if mono.contains(&var) {
                keys_to_remove.push(mono.clone());
            }
        }
        for key in keys_to_remove {
            self.p.terms.remove(&key);
        }
    }

    /// Perform algebraic substitution: x_i = 1
    fn substitute_one(&mut self, var: u32) {
        // 1. Update Boolean State (F): Remove x_i from the term, applying XOR cancellation
        for poly in &mut self.f.functions {
            let mut new_poly = rustc_hash::FxHashSet::default();
            for term in poly.iter() {
                let mut new_term = term.clone();
                if new_term.contains(&var) {
                    new_term.retain(|&v| v != var); // x_i = 1 acts as identity in AND
                }
                
                // XOR cancellation: if term exists, remove it; otherwise, insert it.
                if new_poly.contains(&new_term) {
                    new_poly.remove(&new_term);
                } else {
                    new_poly.insert(new_term);
                }
            }
            *poly = new_poly;
        }

        // 2. Update Phase Polynomial (P): Down-degree monomials containing x_i
        let mut additions = Vec::new();
        let mut removals = Vec::new();
        
        for (mono, coeff) in &self.p.terms {
            if mono.contains(&var) {
                removals.push(mono.clone());
                
                let mut new_mono = mono.clone();
                new_mono.retain(|&v| v != var);
                additions.push((new_mono, coeff.clone()));
            }
        }
        
        for mono in removals {
            self.p.terms.remove(&mono);
        }
        
        for (mono, coeff) in additions {
            // Assumes self.p.add_term() correctly handles modulo 1 and merges like terms
            self.p.add_term(mono, coeff); 
        }
    }
    pub fn print_status(&self) {
        println!("=== PathSum State ===");
        
        let mut active_path_vars: Vec<u32> = self.v.path_vars.iter()
            .filter(|&&id| (id as usize) >= self.v.num_qubits)
            .cloned()
            .collect();
        active_path_vars.sort_unstable();

        print!("Active Path Vars: ");
        if active_path_vars.is_empty() {
            println!("None");
        } else {
            let vars_str: Vec<String> = active_path_vars.iter()
                .map(|&id| self.v.fmt_var(id))
                .collect();
            println!("{{ {} }}", vars_str.join(", "));
        }

        println!("Phase Polynomial P:");
        if self.p.terms.is_empty() { 
            println!("  0"); 
        } else {
            let mut keys: Vec<_> = self.p.terms.keys().collect();
            keys.sort(); 
            for mono in keys {
                let coeff = &self.p.terms[mono];
                println!("  + ({}) * [{}]", coeff.constant, self.v.fmt_monomial(mono));
            }
        }
        
        println!("Basis F:");
        for (i, poly) in self.f.functions.iter().enumerate() {
            let qubit_name = self.f.format_qubit_name(i); 
            let poly_str = self.v.fmt_polynomial(poly);
            println!("  {} = {}", qubit_name, poly_str);
        }
        println!("=====================\n");
    }
}