// src/pathsum/mod.rs
#![allow(dead_code)]
pub mod phase_poly;
pub mod boolean_state;
pub mod var_manager;

pub use phase_poly::{PhasePolynomial, Monomial};
pub use boolean_state::BooleanState;
pub use var_manager::VariableManager;

pub fn mul_monomials(m1: &Monomial, m2: &Monomial) -> Monomial {
    let mut result = m1.clone();
    result.extend_from_slice(m2);
    result.sort_unstable(); 
    result.dedup();
    result
}

pub struct PathSum {
    pub p: PhasePolynomial,
    pub f: BooleanState,
    pub v: VariableManager,
}

impl PathSum {
    pub fn new(num_qubits: usize) -> Self {
        Self {
            p: PhasePolynomial::new(),
            f: BooleanState::new(num_qubits),
            v: VariableManager::new(num_qubits),
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
        for (q, poly) in self.f.functions.iter().enumerate() {
            if poly.is_empty() { 
                println!("  |q_{}> = 0", q); 
                continue; 
            }
            let mut terms: Vec<String> = poly.iter()
                .map(|m| self.v.fmt_monomial(m))
                .collect();
            terms.sort(); 
            println!("  |q_{}> = {}", q, terms.join(" ⊕ "));
        }
        println!("=====================");
    }
}