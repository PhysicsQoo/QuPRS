// src/wmc.rs
use std::fs::File;
use std::io::{Write};
use std::process::{Command, Stdio};
use std::collections::HashMap;
use std::f64::consts::PI;

use log::{info, debug, trace};

use num_complex::Complex;
use anyhow::{Result, Context, anyhow};

use crate::pathsum::{PathSum};
use crate::pathsum::phase_poly::Monomial;

pub struct WmcManager {
    clauses: Vec<Vec<i32>>,
    weights: Vec<(i32, Complex<f64>)>,
    var_map: HashMap<u32, i32>, // Maps PathSum variable ID to DIMACS variable ID
    next_var_id: i32,
}

impl WmcManager {
    pub fn new(ps: &PathSum) -> Self {
        let mut manager = WmcManager {
            clauses: Vec::new(),
            weights: Vec::new(),
            var_map: HashMap::new(),
            next_var_id: 1, // DIMACS variables are 1-based
        };
        manager.encode_pathsum(ps);
        manager
    }

    /// Retrieve or create a DIMACS variable ID for a given PathSum variable
    fn get_dimacs_var(&mut self, ps_var: u32) -> i32 {
        if let Some(&id) = self.var_map.get(&ps_var) {
            id
        } else {
            let id = self.next_var_id;
            self.next_var_id += 1;
            self.var_map.insert(ps_var, id);
            
            // Default weight for boolean variables is 1.0 for both True and False
            self.weights.push((id, Complex::new(1.0, 0.0)));
            self.weights.push((-id, Complex::new(1.0, 0.0)));
            id
        }
    }

    /// Encode the non-linear Phase Polynomial into CNF via Tseitin Transformation
    fn encode_pathsum(&mut self, ps: &PathSum) {
        for (mono, coeff) in &ps.p.terms {
            // Calculate complex weight: e^{i * pi * (numer/denom)}
            let phase_val = (coeff.constant.numer as f64) / (coeff.constant.denom as f64);
            let angle = phase_val * PI;
            let weight = Complex::new(angle.cos(), angle.sin());

            if mono.is_empty() {
                // Global phase: multiply it directly to a dummy variable that is always true
                let dummy_var = self.next_var_id;
                self.next_var_id += 1;
                self.clauses.push(vec![dummy_var]); // Unit clause forcing it to be true
                self.weights.push((dummy_var, weight));
                self.weights.push((-dummy_var, Complex::new(1.0, 0.0)));
                continue;
            }

            // Map variables
            let dimacs_lits: Vec<i32> = mono.iter().map(|&v| self.get_dimacs_var(v)).collect();

            if dimacs_lits.len() == 1 {
                // Linear term: apply weight directly to the variable
                let var = dimacs_lits[0];
                self.weights.push((var, weight));
                // Negative literal weight remains 1.0 (already set in get_dimacs_var)
            } else {
                // Non-linear term (AND gate): introduce auxiliary variable y
                let y = self.next_var_id;
                self.next_var_id += 1;
                
                // Assign weight to auxiliary variable
                self.weights.push((y, weight));
                self.weights.push((-y, Complex::new(1.0, 0.0)));

                // Add CNF clauses for y <-> (x_1 AND x_2 AND ... AND x_n)
                // 1. y -> (x_i)  ===  -y OR x_i
                let mut long_clause = vec![y];
                for &lit in &dimacs_lits {
                    self.clauses.push(vec![-y, lit]);
                    long_clause.push(-lit); // 2. (x_1 AND ... AND x_n) -> y
                }
                self.clauses.push(long_clause);
            }
        }
        
        // Note: F (Boolean State constraints) encoding should also be added here 
        // to force the output basis state, depending on the equivalence miter definition.
    }
    fn get_monomial_literal(&mut self, mono: &Monomial) -> i32 {
        if mono.is_empty() {
            // Constant 1 (True). Introduce a dummy variable forced to True.
            let dummy = self.next_var_id;
            self.next_var_id += 1;
            self.clauses.push(vec![dummy]);
            // Neutral weight for structural variables
            self.weights.push((dummy, Complex::new(1.0, 0.0)));
            self.weights.push((-dummy, Complex::new(1.0, 0.0)));
            return dummy;
        }

        let dimacs_lits: Vec<i32> = mono.iter().map(|&v| self.get_dimacs_var(v)).collect();
        if dimacs_lits.len() == 1 {
            return dimacs_lits[0];
        }

        // AND gate: y <-> (x_1 AND x_2 AND ... AND x_n)
        let y = self.next_var_id;
        self.next_var_id += 1;
        self.weights.push((y, Complex::new(1.0, 0.0)));
        self.weights.push((-y, Complex::new(1.0, 0.0)));

        let mut long_clause = vec![y];
        for &lit in &dimacs_lits {
            self.clauses.push(vec![-y, lit]);
            long_clause.push(-lit);
        }
        self.clauses.push(long_clause);

        y
    }

    /// Enforce that a linear combination (XOR sum) of literals evaluates to False (0)
    /// Uses a chained encoding to prevent exponential clause blowup: O(N) clauses
    fn enforce_xor_sum_is_false(&mut self, literals: Vec<i32>) {
        if literals.is_empty() {
            return; // 0 == 0, trivially true
        }
        if literals.len() == 1 {
            self.clauses.push(vec![-literals[0]]); // Must be False
            return;
        }
        
        let mut current_var = literals[0];
        for i in 1..literals.len() - 1 {
            let next_var = literals[i];
            let aux = self.next_var_id;
            self.next_var_id += 1;
            
            // aux <-> current_var XOR next_var
            self.clauses.push(vec![-aux, current_var, next_var]);
            self.clauses.push(vec![-aux, -current_var, -next_var]);
            self.clauses.push(vec![aux, -current_var, next_var]);
            self.clauses.push(vec![aux, current_var, -next_var]);
            
            // Neutral weights for auxiliary variables
            self.weights.push((aux, Complex::new(1.0, 0.0)));
            self.weights.push((-aux, Complex::new(1.0, 0.0)));
            
            current_var = aux;
        }
        
        // The final XOR must be false: current_var XOR last_var = 0  => current_var == last_var
        let last_var = literals.last().unwrap();
        self.clauses.push(vec![-current_var, *last_var]);
        self.clauses.push(vec![current_var, -last_var]);
    }

    /// Encode the Boolean state F to force output |0...0>
    pub fn encode_boolean_state_to_zero(&mut self, ps: &PathSum) {
        for poly in &ps.f.functions {
            let mut literals = Vec::new();
            for mono in poly {
                literals.push(self.get_monomial_literal(mono));
            }
            self.enforce_xor_sum_is_false(literals);
        }
    }
    /// Export the state to a standard DIMACS string format
    pub fn to_dimacs_string(&self) -> String {
        let mut out = String::new();
        let num_vars = self.next_var_id - 1;
        let num_clauses = self.clauses.len();

        out.push_str(&format!("p cnf {} {}\n", num_vars, num_clauses));
        
        for (var, weight) in &self.weights {
            out.push_str(&format!("c w {} {:.9} {:.9}\n", var, weight.re, weight.im));
        }

        for clause in &self.clauses {
            let clause_str: Vec<String> = clause.iter().map(|lit| lit.to_string()).collect();
            out.push_str(&format!("{} 0\n", clause_str.join(" ")));
        }
        out
    }

    pub fn solve_with_gpmc(&self) -> Result<Complex<f64>> {
        use std::io::Read;
        use std::time::{SystemTime, UNIX_EPOCH};

        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
        let pid = std::process::id();
        let temp_cnf_path = std::env::temp_dir().join(format!("temp_eqcheck_{}_{}.cnf", pid, timestamp));
        
        let cnf_content = self.to_dimacs_string();
        trace!(target: "wmc", "Generated CNF for GPMC:\n{}", cnf_content);

        let mut file = File::create(&temp_cnf_path)?;
        file.write_all(cnf_content.as_bytes())?;

        let gpmc_exe = env!("GPMC_BIN_PATH");
        
        debug!(target: "wmc", "Spawning GPMC solver: {} -mode=1 {}", gpmc_exe, temp_cnf_path.display());

        let mut child = Command::new(gpmc_exe)
            .arg("-mode=1")
            .arg(&temp_cnf_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context("Failed to spawn GPMC process")?;

        let mut stdout_str = String::new();
        let mut stderr_str = String::new();
        
        if let Some(mut out) = child.stdout.take() {
            out.read_to_string(&mut stdout_str)?;
        }
        if let Some(mut err) = child.stderr.take() {
            err.read_to_string(&mut stderr_str)?;
        }

        child.wait()?;

        trace!(target: "wmc", "GPMC raw stdout:\n{}", stdout_str);
        if !stderr_str.is_empty() {
            trace!(target: "wmc", "GPMC raw stderr:\n{}", stderr_str);
        }

        let _ = std::fs::remove_file(&temp_cnf_path);

        let mut result_val = None;

        for line in stdout_str.lines() {
            if line.contains("s UNSATISFIABLE") || line.contains("UNSAT") {
                debug!(target: "wmc", "GPMC result: UNSATISFIABLE (Amplitude = 0)");
                return Ok(Complex::new(0.0, 0.0));
            }

            if line.starts_with("c s exact") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if let Some(token) = parts.last() {
                    let mut re = 0.0;
                    let mut im = 0.0;
                    let token_clean = token.trim();
                    
                    if token_clean.ends_with('i') {
                        let s = &token_clean[..token_clean.len()-1];
                        let mut split_idx = None;
                        for (i, c) in s.char_indices().rev() {
                            if (c == '+' || c == '-') && i > 0 {
                                let prev_char = s.as_bytes()[i-1];
                                if prev_char != b'e' && prev_char != b'E' {
                                    split_idx = Some(i);
                                    break;
                                }
                            }
                        }

                        if let Some(idx) = split_idx {
                            re = s[..idx].parse().unwrap_or(0.0);
                            let im_str = &s[idx..];
                            im = if im_str == "+" { 1.0 } else if im_str == "-" { -1.0 } else { im_str.parse().unwrap_or(0.0) };
                        } else {
                            im = if s == "" { 1.0 } else if s == "-" { -1.0 } else { s.parse().unwrap_or(0.0) };
                        }
                    } else {
                        re = token_clean.parse().unwrap_or(0.0);
                    }
                    
                    info!(target: "wmc", "GPMC result parsed: {} + {}i", re, im);
                    result_val = Some(Complex::new(re, im));
                }
            }
        }

        result_val.ok_or_else(|| {
            anyhow!(
                "GPMC Error!\nCNF Path: {}\n--- STDOUT ---\n{}\n--- STDERR ---\n{}",
                temp_cnf_path.display(),
                stdout_str,
                stderr_str
            )
        })
    }
}