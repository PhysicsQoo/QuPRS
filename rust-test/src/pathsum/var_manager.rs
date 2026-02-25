// src/pathsum/var_manager.rs
use rustc_hash::FxHashSet;
use super::phase_poly::Monomial;

#[derive(Clone, Debug)]
pub struct VariableManager {
    pub path_vars: FxHashSet<u32>,
    pub continuous_vars: FxHashSet<u32>,
    pub num_qubits: usize, 
    pub next_id: u32,
}

impl VariableManager {
    pub fn new(num_qubits: usize) -> Self {
        let mut path_vars = FxHashSet::default();
        for i in 0..num_qubits { path_vars.insert(i as u32); }
        
        Self {
            path_vars,
            continuous_vars: FxHashSet::default(),
            num_qubits,
            next_id: num_qubits as u32,
        }
    }

    pub fn get_fresh_var(&mut self) -> u32 {
        let var = self.next_id;
        self.next_id += 1;
        self.path_vars.insert(var);
        var
    }

    pub fn fmt_var(&self, var_id: u32) -> String {
        if (var_id as usize) < self.num_qubits {
            format!("x_{}", var_id)
        } else {
            format!("y_{}", var_id - self.num_qubits as u32)
        }
    }

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
}