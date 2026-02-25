// src/reduction.rs
use rustc_hash::FxHashSet;
use crate::pathsum::{PathSum, Monomial, mul_monomials};

impl PathSum {
    pub fn full_reduce(&mut self) {
        let mut reduced = true;
        let mut iterations = 0;

        while reduced {
            reduced = false;
            if self.try_reduce_elim() {
                reduced = true;
                iterations += 1;
                continue; 
            }

            if self.try_reduce_hh() {
                reduced = true;
                iterations += 1;
                continue;
            }
            if iterations > 0 {
            println!(">> [Full Reduce] System converged after {} reduction steps.", iterations);
            }
        }
    }

    pub fn try_reduce_elim(&mut self) -> bool {
        // 1. Collect all truly "active" variables in the system
        let mut active_vars = rustc_hash::FxHashSet::default();

        // Scan Boolean State (F)
        for poly in &self.f.functions {
            for term in poly {
            active_vars.extend(term.iter().copied());
            }
        }

        // Scan Phase Polynomial (P)
        for mono in self.p.terms.keys() {
            active_vars.extend(mono.iter().copied());
        }

        // 2. Find completely isolated internal variables (y_i)
        let mut vars_to_remove = Vec::new();
        for &var in &self.v.path_vars {
            // Constraint 1: Only internal path variables (y_i, ID >= num_qubits) can be eliminated, not input variables (x_i)
            // Constraint 2: The variable is not in the active_vars set
            if (var as usize) >= self.v.num_qubits && !active_vars.contains(&var) {
            vars_to_remove.push(var);
            }
        }

        // 3. Perform elimination
        if vars_to_remove.is_empty() {
            return false;
        }

        for var in &vars_to_remove {
            self.v.path_vars.remove(var);
            println!(">> [Elimination] Removed decoupled path variable: {}", self.v.fmt_var(*var));
            
        }

        true
    }
    /// Attempt to execute HH Rule (Feynman path cancellation)
    /// Scan globally for isolated path variables and perform substitution.
    /// Return true if simplification was successful.
    pub fn try_reduce_hh(&mut self) -> bool {
        // ==========================================
        // Step 1: Find all variables used in F
        // ==========================================
        let mut f_used_vars = FxHashSet::default();
        for poly in &self.f.functions {
            for term in poly {
                f_used_vars.extend(term.iter().copied());
            }
        }

        // ==========================================
        // Step 2: Find isolated path variable y (not in F)
        // To ensure deterministic behavior, check from the largest ID variable
        // ==========================================
        let mut target_y = None;
        let mut sorted_vars: Vec<_> = self.v.path_vars.iter().copied().collect();
        sorted_vars.sort_by(|a, b| b.cmp(a)); // Sort in descending order

        for y in sorted_vars {
            if (y as usize) >= self.v.num_qubits && !f_used_vars.contains(&y) {
                target_y = Some(y);
                break;
            }
        }

        let y = match target_y {
            Some(var) => var,
            None => return false,
        };

        // ==========================================
        // Step 3: Extract Phi polynomial and verify coefficients
        // ==========================================
        let mut phi: FxHashSet<Monomial> = FxHashSet::default();
        let mut is_valid_hh = true;
        let mut y_terms_to_remove = Vec::new();

        for (mono, coeff) in &self.p.terms {
            if mono.contains(&y) {
                if !coeff.is_pure_half() {
                    is_valid_hh = false;
                    break;
                }
                y_terms_to_remove.push(mono.clone());
                
                let mut phi_term = mono.clone();
                phi_term.retain(|&var| var != y);
                
                // Add to Phi using XOR logic
                if phi.contains(&phi_term) {
                    phi.remove(&phi_term);
                } else {
                    phi.insert(phi_term);
                }
            }
        }

        if !is_valid_hh || phi.is_empty() {
            return false;
        }

        // ==========================================
        // Step 4: Select substitution variable v from Phi
        // Condition: Must be a linear term (len == 1), prioritize largest ID
        // ==========================================
        let mut target_v = None;
        for term in &phi {
            if term.len() == 1 {
                let var = term[0];
                match target_v {
                    None => target_v = Some(var),
                    Some(max_var) => {
                        if var > max_var {
                            target_v = Some(var);
                        }
                    }
                }
            }
        }

        let v = match target_v {
            Some(var) => var,
            None => return false, // No linear variable in Phi, cannot perform substitution
        };

        // Substitution expression R = Phi \ {v}
        let mut replacement = phi.clone();
        replacement.remove(&vec![v]);

        println!(">> [HH Rule] Integrator y: {}, Target v: {} -> {}", 
                 self.v.fmt_var(y), 
                 self.v.fmt_var(v), 
                 self.v.fmt_polynomial(&replacement)); // Brief output

        // ==========================================
        // Step 5: Perform variable substitution (Substitution) v -> R
        // ==========================================

        // 5a. Remove all terms containing y from P (path integral cancelled y)
        for mono in &y_terms_to_remove {
            self.p.terms.remove(mono);
        }

        // 5b. Substitute v in Boolean State (F)
        for poly in &mut self.f.functions {
            let mut new_poly = FxHashSet::default();
            for term in poly.iter() {
                if term.contains(&v) {
                    // If term contains v, split as v * U and expand to R * U
                    let mut u = term.clone();
                    u.retain(|&x| x != v);
                    for r_term in &replacement {
                        let new_term = mul_monomials(&u, r_term);
                        if new_poly.contains(&new_term) {
                            new_poly.remove(&new_term);
                        } else {
                            new_poly.insert(new_term);
                        }
                    }
                } else {
                    // If v not present, keep directly (follow XOR logic)
                    if new_poly.contains(term) {
                        new_poly.remove(term);
                    } else {
                        new_poly.insert(term.clone());
                    }
                }
            }
            *poly = new_poly;
        }

        // 5c. Substitute v in Phase Polynomial (P)
        let mut p_additions = Vec::new();
        let mut p_removals = Vec::new();

        for (mono, coeff) in &self.p.terms {
            if mono.contains(&v) {
                p_removals.push(mono.clone());
                let mut u = mono.clone();
                u.retain(|&x| x != v);
                for r_term in &replacement {
                    let new_term = mul_monomials(&u, r_term);
                    p_additions.push((new_term, coeff.clone()));
                }
            }
        }

        for mono in &p_removals {
            self.p.terms.remove(mono);
        }
        for (mono, coeff) in p_additions {
            self.p.add_term(mono, coeff); // Auto handles term merging and Modulo 1
        }

        // ==========================================
        // Step 6: Garbage Collection
        // ==========================================
        self.v.path_vars.remove(&y);
        
        if (v as usize) >= self.v.num_qubits {
            self.v.path_vars.remove(&v);
        }

        true
    }
}