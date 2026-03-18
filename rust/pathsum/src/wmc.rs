// src/wmc.rs
use std::fs::File;
use std::io::Write;
use std::process::{Command, Stdio};
use std::collections::HashMap;
use std::f64::consts::PI;

use log::{info, debug, trace};
use num_complex::Complex;
use anyhow::{Result, Context, anyhow};

use crate::pathsum::PathSum;
use crate::pathsum::phase_poly::Monomial;

pub struct WmcManager {
    clauses: Vec<Vec<i32>>,
    weights: HashMap<i32, Complex<f64>>, 
    var_map: HashMap<u32, i32>,
    next_var_id: i32,
}

impl WmcManager {
    pub fn new(_ps: &PathSum) -> Self {
        let manager = WmcManager {
            clauses: Vec::new(),
            weights: HashMap::new(),
            var_map: HashMap::new(),
            next_var_id: 1, 
        };
        manager
    }

    fn get_dimacs_var(&mut self, ps_var: u32) -> i32 {
        if let Some(&id) = self.var_map.get(&ps_var) {
            id
        } else {
            let id = self.next_var_id;
            self.next_var_id += 1;
            self.var_map.insert(ps_var, id);
            id
        }
    }

    fn encode_phase_polynomial(&mut self, ps: &PathSum) {
        for (mono, coeff) in &ps.p.terms {
            let phase_val = (coeff.constant.numer as f64) / (coeff.constant.denom as f64);
            let angle = phase_val * 2.0 * PI;
            let weight = Complex::new(angle.cos(), angle.sin());

            let z_i = self.next_var_id;
            self.next_var_id += 1;
            
            self.weights.insert(z_i, weight);

            if mono.is_empty() {
                self.clauses.push(vec![z_i]);
            } else {
                let dimacs_lits: Vec<i32> = mono.iter().map(|&v| self.get_dimacs_var(v)).collect();
                
                if dimacs_lits.len() == 1 {
                    // z_i <-> x
                    let x = dimacs_lits[0];
                    self.clauses.push(vec![-z_i, x]);
                    self.clauses.push(vec![-x, z_i]);
                } else {
                    // z_i <-> AND(x_1, x_2, ...)
                    let mut long_clause = vec![z_i];
                    for &lit in &dimacs_lits {
                        self.clauses.push(vec![-z_i, lit]); // z_i -> lit
                        long_clause.push(-lit);             // AND -> z_i
                    }
                    self.clauses.push(long_clause);
                }
            }
        }
    }

    fn encode_anf(&mut self, anf: &[Monomial]) -> i32 {
        if anf.is_empty() {
            let f_var = self.next_var_id;
            self.next_var_id += 1;
            self.clauses.push(vec![-f_var]); 
            return f_var;
        }

        let mut mono_vars = Vec::new();
        for mono in anf {
            let dimacs_lits: Vec<i32> = mono.iter().map(|&v| self.get_dimacs_var(v)).collect();
            if dimacs_lits.is_empty() {
                let t_var = self.next_var_id;
                self.next_var_id += 1;
                self.clauses.push(vec![t_var]); 
                mono_vars.push(t_var);
            } else if dimacs_lits.len() == 1 {
                mono_vars.push(dimacs_lits[0]);
            } else {
                let and_var = self.next_var_id;
                self.next_var_id += 1;
                let mut long_clause = vec![and_var];
                for &lit in &dimacs_lits {
                    self.clauses.push(vec![-and_var, lit]);
                    long_clause.push(-lit);
                }
                self.clauses.push(long_clause);
                mono_vars.push(and_var);
            }
        }

        if mono_vars.len() == 1 {
            return mono_vars[0];
        }

        // Xor : c <-> a Xor b
        let mut current_var = mono_vars[0];
        for i in 1..mono_vars.len() {
            let next_var = mono_vars[i];
            let c = self.next_var_id;
            self.next_var_id += 1;
            
            //  Xor Tseitin 
            self.clauses.push(vec![-current_var, -next_var, -c]); // Or(Not(a), Not(b), Not(c))
            self.clauses.push(vec![current_var, next_var, -c]);   // Or(a, b, Not(c))
            self.clauses.push(vec![current_var, -next_var, c]);   // Or(a, Not(b), c)
            self.clauses.push(vec![-current_var, next_var, c]);   // Or(Not(a), b, c)
            
            current_var = c;
        }
        current_var
    }

    pub fn encode_trace(&mut self, ps: &PathSum) {
        self.encode_phase_polynomial(ps);

        for i in 0..ps.v.num_qubits {
            let a = self.get_dimacs_var(i as u32);
            
            let anf_vec: Vec<Monomial> = ps.f.functions[i].iter().cloned().collect();
            let b = self.encode_anf(&anf_vec); 
            
            self.clauses.push(vec![-a, b]); // a -> b
            self.clauses.push(vec![a, -b]); // b -> a
        }
    }

    pub fn to_dimacs_string(&self, tool_name: &str) -> String {
        let mut out = String::new();
        let num_vars = self.next_var_id - 1;
        let num_clauses = self.clauses.len();

        out.push_str(&format!("p cnf {} {}\nc t wmc\n", num_vars, num_clauses));
        
        for (var, weight) in &self.weights {
            if tool_name == "gpmc" {
                out.push_str(&format!("c p weight {} {:.9} {:.9} 0\n", var, weight.re, weight.im));
                out.push_str(&format!("c p weight -{} 1.0 0.0 0\n", var));
            } else {
                let op = if weight.im >= 0.0 { "+" } else { "-" };
                out.push_str(&format!("c p weight {} {:.9} {} {:.9}i 0\n", var, weight.re, op, weight.im.abs()));
                out.push_str(&format!("c p weight -{} 1.0 + 0.0i 0\n", var));
            }
        }

        for clause in &self.clauses {
            let clause_str: Vec<String> = clause.iter().map(|lit| lit.to_string()).collect();
            out.push_str(&format!("{} 0\n", clause_str.join(" ")));
        }
        out
    }
    fn find_gpmc_path() -> String {
        if let Ok(path) = std::env::var("QUPRS_GPMC_PATH") {
            return path;
        }

        if let Some(compile_path) = option_env!("GPMC_BIN_PATH") {
            if std::path::Path::new(compile_path).exists() {
                return compile_path.to_string();
            }
        }

        if cfg!(windows) {
            "gpmc.exe".to_string()
        } else {
            "gpmc".to_string()
        }
    }
    fn find_ganak_path() -> String {
        if let Ok(path) = std::env::var("QUPRS_GANAK_PATH") {
            return path;
        }

        if let Some(compile_path) = option_env!("GANAK_BIN_PATH") {
            if std::path::Path::new(compile_path).exists() {
                return compile_path.to_string();
            }
        }

        if cfg!(windows) {
            "ganak.exe".to_string()
        } else {
            "ganak".to_string()
        }
    }

    pub fn solve(&self, tool_name: &str) -> Result<Complex<f64>> {
        use std::io::Read;
        use std::time::{SystemTime, UNIX_EPOCH};

        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
        let pid = std::process::id();
        let temp_cnf_path = std::env::temp_dir().join(format!("temp_eqcheck_{}_{}.cnf", pid, timestamp));
        
        let cnf_content = self.to_dimacs_string(tool_name);
        trace!(target: "wmc", "Generated CNF for {}:\n{}", tool_name, cnf_content);

        let mut file = File::create(&temp_cnf_path)?;
        file.write_all(cnf_content.as_bytes())?;

        let (exe_path, args) = if tool_name == "gpmc" {
            (Self::find_gpmc_path(), vec!["-mode=1"])
        } else if tool_name == "ganak" {
            (Self::find_ganak_path(), vec!["--mode=6"])
        } else {
            return Err(anyhow!("Unsupported tool name: {}", tool_name));
        };
        
        debug!(target: "wmc", "Spawning {} solver: {} {:?} {}", tool_name, exe_path, args, temp_cnf_path.display());

        let mut child = Command::new(&exe_path)
            .args(&args)
            .arg(&temp_cnf_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context(format!("Failed to spawn {} process from path: {}", tool_name, exe_path))?;

        let mut stdout_str = String::new();
        let mut stderr_str = String::new();
        
        if let Some(mut out) = child.stdout.take() {
            out.read_to_string(&mut stdout_str)?;
        }
        if let Some(mut err) = child.stderr.take() {
            err.read_to_string(&mut stderr_str)?;
        }

        child.wait()?;

        trace!(target: "wmc", "{} raw stdout:\n{}", tool_name, stdout_str);
        if !stderr_str.is_empty() {
            trace!(target: "wmc", "{} raw stderr:\n{}", tool_name, stderr_str);
        }

        let _ = std::fs::remove_file(&temp_cnf_path);

        let mut result_val = None;

        for line in stdout_str.lines() {
            let mut prefix_len = 0;
            if line.starts_with("c s exact double prec-sci") {
                prefix_len = "c s exact double prec-sci".len();
            } else if line.starts_with("c s exact arb cpx") {
                prefix_len = "c s exact arb cpx".len();
            } else if line.starts_with("c s exact quadruple float") {
                prefix_len = "c s exact quadruple float".len();
            } else if line.starts_with("c s exact") {
                prefix_len = "c s exact".len();
            }

            if prefix_len > 0 {
                let token_str = &line[prefix_len..];
                let token_clean = token_str.trim().replace(" ", "").replace("+-", "-");
                
                let mut re = 0.0;
                let mut im = 0.0;
                
                if token_clean.ends_with('i') {
                    let s = &token_clean[..token_clean.len()-1];
                    let mut split_idx = None;
                    for (i, c) in s.char_indices().rev() {
                        if (c == '+' || c == '-') && i > 0 {
                            let prev_char = s.as_bytes()[i-1];
                            // Avoid splitting on 'e'/'E' in scientific notation
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
                
                info!(target: "wmc", "{} result parsed: {} + {}i", tool_name, re, im);
                result_val = Some(Complex::new(re, im));
            }
        }

        result_val.ok_or_else(|| {
            anyhow!(
                "{} Error!\nCNF Path: {}\n--- STDOUT ---\n{}\n--- STDERR ---\n{}",
                tool_name,
                temp_cnf_path.display(),
                stdout_str,
                stderr_str
            )
        })
    }
}