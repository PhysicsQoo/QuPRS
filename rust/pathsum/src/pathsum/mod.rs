// src/pathsum/mod.rs
#![allow(dead_code)]
pub mod phase_poly;
pub mod boolean_state;
pub mod var_manager;

pub use phase_poly::{PhasePolynomial, Monomial};
pub use boolean_state::{BooleanState, Register};
pub use crate::rational::PhaseCoeff;
pub use var_manager::VariableManager;

use rustc_hash::FxHashSet; 
use crate::stats::StatisticsManager;

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
            let m = mul_monomials(m1, m2);
            if result.contains(&m) {
                result.remove(&m);
            } else {
                result.insert(m);
            }
        }
    }
    
    result
}

#[derive(Clone, Debug)]
pub struct PathSum {
    pub p: PhasePolynomial,
    pub f: BooleanState,
    pub v: VariableManager,
    pub stats: StatisticsManager,
}

impl PathSum {
    pub fn new(num_qubits: usize) -> Self {
        Self {
            p: PhasePolynomial::new(),
            f: BooleanState::new(num_qubits),
            v: VariableManager::new(num_qubits),
            stats: StatisticsManager::new(),
        }
    }
    pub fn set_auto_reduce(&mut self, enable: bool) {
        self.stats.set_enabled(enable);
    }

    pub fn is_auto_reduce(&self) -> bool {
        self.stats.is_enabled()
    }
    pub fn quantum_circuit(regs: &[Register], initial_state: Option<&[u8]>) -> Self {
        let total_qubits: usize = regs.iter().map(|r| r.size).sum();
        
        let mut ps = Self {
            p: PhasePolynomial::new(),
            f: BooleanState::new_with_regs(regs),
            v: VariableManager::new(total_qubits),
            stats: StatisticsManager::new(),
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
        if self.is_auto_reduce() {
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
        let mut additions: Vec<(Monomial, PhaseCoeff)> = Vec::new();
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
    pub(crate) fn substitute_var_with_poly(
        &mut self, 
        target_var: u32, 
        sub_poly: &rustc_hash::FxHashSet<crate::pathsum::Monomial>
    ) {
        self.f.substitute_var_with_poly(target_var, sub_poly);
        self.p.substitute_var_with_poly(target_var, sub_poly);
    }

    pub(crate) fn substitute_var(&mut self, old_var: u32, new_var: u32) {
        let mut sub_poly = rustc_hash::FxHashSet::default();
        sub_poly.insert(vec![new_var]);
        self.substitute_var_with_poly(old_var, &sub_poly);
    }

    pub fn is_identity(&self) -> bool {
        // Check if phase polynomial P is empty (phase is 0)
        if !self.p.terms.is_empty() {
            return false;
        }

        // Check if boolean state F is in trivial state
        // Identity means each qubit i has F[i] = x_i (the input variable itself)
        for (qubit_idx, poly) in self.f.functions.iter().enumerate() {
            // Polynomial must contain exactly one term
            if poly.len() != 1 {
            return false;
            }

            // That term must be exactly the input variable x_i
            let x_i = vec![qubit_idx as u32];
            if !poly.contains(&x_i) {
            return false;
            }
        }
        
        true
    }
    pub fn is_identity_up_to_phase(&self) -> bool {
        for monomial in self.p.terms.keys() {
            if !monomial.is_empty() {
                return false; 
            }
        }

        for (qubit_idx, poly) in self.f.functions.iter().enumerate() {
            if poly.len() != 1 {
                return false;
            }
            let x_i = vec![qubit_idx as u32];
            if !poly.contains(&x_i) {
                return false;
            }
        }
        true
    }
    
    pub fn get_global_phase(&self) -> Option<crate::rational::PhaseCoeff> {
        if !self.is_identity_up_to_phase() {
            return None;
        }
        self.p.terms.get(&vec![]).cloned().or_else(|| {
            Some(PhaseCoeff::ZERO)
        })
    }

    pub fn print_status(&self) -> String {
        let mut out = String::new();
        out.push_str("\n=== Residual PathSum State ===\n");
        
        let mut active_path_vars: Vec<u32> = self.v.path_vars.iter()
            .filter(|&&id| (id as usize) >= self.v.num_qubits)
            .cloned()
            .collect();
        active_path_vars.sort_unstable();

        out.push_str(&format!("Active Path Vars (Count: {}): ", active_path_vars.len()));
        if active_path_vars.is_empty() {
            out.push_str("None\n");
        } else {
            let vars_str: Vec<String> = active_path_vars.iter()
                .map(|&id| self.v.fmt_var(id))
                .collect();
            out.push_str(&format!("{{ {} }}\n", vars_str.join(", ")));
        }

        out.push_str("Phase Polynomial P:\n  ");
        if self.p.terms.is_empty() {
            out.push_str("0\n");
        } else {
            out.push_str(&format!("+ {}\n", self.v.fmt_phase_poly(&self.p)));
        }
        
        out.push_str("Basis F:\n");
        for (i, func) in self.f.functions.iter().enumerate() {
            let qubit_name = self.f.format_qubit_name(i); 
            out.push_str(&format!("  {} = {}\n", qubit_name, self.v.fmt_polynomial(func)));
        }
        out.push_str("==============================");
        out
    }
}