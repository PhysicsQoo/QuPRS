// src/pathsum.rs
use rustc_hash::{FxHashMap, FxHashSet};
use std::collections::hash_map::Entry;
use crate::rational::Rational; // Import rational module

use num_traits::Zero;   
use std::ops::AddAssign;

pub type Monomial = Vec<u32>;

pub struct PathSum {
    pub phase_poly: FxHashMap<Monomial, Rational>,
    pub boolean_functions: Vec<FxHashSet<Monomial>>,
    pub path_vars: FxHashSet<u32>, // Contains all variables (x and y)
    
    // Used to distinguish x (input) and y (path)
    // ID < num_qubits is x
    // ID >= num_qubits is y
    pub num_qubits: usize, 
    pub next_var_id: u32,
}

impl PathSum {
    pub fn new(num_qubits: usize) -> Self {
        let phase_poly = FxHashMap::default();
        let mut path_vars = FxHashSet::default();
        let mut boolean_functions = Vec::with_capacity(num_qubits);

        // Initialize input variables x_0 to x_{n-1}
        for i in 0..num_qubits {
            let mut poly = FxHashSet::default();
            poly.insert(vec![i as u32]);
            boolean_functions.push(poly);
            path_vars.insert(i as u32);
        }

        PathSum {
            phase_poly,
            boolean_functions,
            path_vars,
            num_qubits, // Record boundary
            next_var_id: num_qubits as u32,
        }
    }

    /// Helper display function: decide to display x_i or y_j based on ID
    pub fn fmt_var(&self, var_id: u32) -> String {
        if (var_id as usize) < self.num_qubits {
            format!("x{}", var_id)
        } else {
            // y index starts from 0 (ID - num_qubits)
            format!("y{}", var_id - self.num_qubits as u32)
        }
    }

    /// Helper display function: format monomial as string
    pub fn fmt_monomial(&self, mono: &Monomial) -> String {
        if mono.is_empty() {
            "1".to_string()
        } else {
            mono.iter()
                .map(|&id| self.fmt_var(id))
                .collect::<Vec<_>>()
                .join("*")
        }
    }

    pub fn get_fresh_var(&mut self) -> u32 {
        let var = self.next_var_id;
        self.next_var_id += 1;
        self.path_vars.insert(var);
        var
    }

    pub fn mul_monomials(m1: &Monomial, m2: &Monomial) -> Monomial {
        let mut result = m1.clone();
        result.extend_from_slice(m2);
        result.sort_unstable(); 
        result.dedup();
        result
    }

    pub fn add_phase(&mut self, mut monomial: Monomial, coeff: Rational) {
        if coeff.is_zero() { return; }
        monomial.sort_unstable();
        monomial.dedup();
        
        match self.phase_poly.entry(monomial) {
            Entry::Occupied(mut entry) => {
                entry.get_mut().add_assign(coeff);
                if entry.get().is_zero() { entry.remove(); }
            }
            Entry::Vacant(entry) => { entry.insert(coeff); }
        }
    }

    pub fn print_status(&self) {
        println!("=== PathSum State ===");
        
        // 1. List current Path Variables (y)
        // Filter variables with ID >= num_qubits
        let mut active_path_vars: Vec<u32> = self.path_vars.iter()
            .filter(|&&id| (id as usize) >= self.num_qubits)
            .cloned()
            .collect();
        active_path_vars.sort_unstable();

        print!("Active Path Vars: ");
        if active_path_vars.is_empty() {
            println!("None");
        } else {
            let vars_str: Vec<String> = active_path_vars.iter()
                .map(|&id| self.fmt_var(id))
                .collect();
            println!("{{ {} }}", vars_str.join(", "));
        }

        // 2. Display Phase Polynomial P
        println!("Phase Polynomial P:");
        if self.phase_poly.is_empty() { 
            println!("  0"); 
        } else {
            let mut keys: Vec<_> = self.phase_poly.keys().collect();
            keys.sort(); 
            for mono in keys {
                let coeff = &self.phase_poly[mono];
                println!("  + ({}) * [{}]", coeff, self.fmt_monomial(mono));
            }
        }
        
        // 3. Display Basis State F
        println!("Basis F:");
        for (q, poly) in self.boolean_functions.iter().enumerate() {
            if poly.is_empty() { 
                println!("  |q{}> = 0", q); 
                continue; 
            }
            let mut terms: Vec<String> = poly.iter()
                .map(|m| self.fmt_monomial(m))
                .collect();
            terms.sort(); 
            println!("  |q{}> = {}", q, terms.join(" ⊕ "));
        }
        println!("=====================");
    }
}
