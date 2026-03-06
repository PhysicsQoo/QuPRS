// src/qasm.rs
use std::collections::HashMap;
use std::path::Path;
use crate::ir::QuantumOp;
use crate::pathsum::{PathSum, Register};
use crate::rational::{PhaseCoeff, Rational};

/// Parse QASM string into a list of quantum operations
pub fn parse_qasm_str(source: &str) -> Result<(Vec<QuantumOp>, usize), String> {
    let mut ops = Vec::new();
    let mut register_map: HashMap<String, usize> = HashMap::new();
    let mut current_qubit_count = 0;

    for (line_num, line) in source.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with("//") || line.starts_with("OPENQASM") || line.starts_with("include") {
            continue;
        }

        if line.starts_with("qreg") {
            let parts: Vec<&str> = line.split(&[' ', '[', ']', ';'][..]).filter(|s| !s.is_empty()).collect();
            if parts.len() >= 3 {
                let name = parts[1].to_string();
                let size = parts[2].parse::<usize>().map_err(|_| format!("Invalid size at line {}", line_num + 1))?;
                register_map.insert(name, current_qubit_count);
                current_qubit_count += size;
            }
            continue;
        }
        if line.starts_with("creg") { continue; }

        // Split gate parameters and targets using the last closing parenthesis
        let (full_gate_part, targets_part) = if let Some(last_paren_idx) = line.rfind(')') {
            // e.g. "u3(pi, 0, pi) q[0];" -> split at ')'
            let (g, t) = line.split_at(last_paren_idx + 1);
            (g.trim(), t.trim())
        } else {
            // No parentheses, split at first space (e.g. "h q[0];")
            if let Some(space_idx) = line.find(' ') {
                let (g, t) = line.split_at(space_idx);
                (g.trim(), t.trim())
            } else {
                (line.trim_matches(';'), "")
            }
        };

        if full_gate_part.is_empty() { continue; }
        if targets_part.is_empty() || targets_part == ";" { continue; }

        let (gate_name, params) = parse_gate_name_and_params(full_gate_part)?;
        let qubits = parse_targets(targets_part, &register_map)
            .map_err(|e| format!("Line {}: {}", line_num + 1, e))?;

        if qubits.is_empty() { continue; }

        let op = match gate_name.as_str() {
            "h" => QuantumOp::H(qubits[0]),
            "x" => QuantumOp::X(qubits[0]),
            "y" => QuantumOp::Y(qubits[0]),
            "z" => QuantumOp::Z(qubits[0]),
            "s" => QuantumOp::RZ(qubits[0], get_pi_coeff(1, 2)),
            "sdg" => QuantumOp::RZ(qubits[0], get_pi_coeff(-1, 2)),
            "t" => QuantumOp::RZ(qubits[0], get_pi_coeff(1, 4)),
            "tdg" => QuantumOp::RZ(qubits[0], get_pi_coeff(-1, 4)),
            "cx" => QuantumOp::CX(qubits[0], qubits[1]),
            "cz" => QuantumOp::CZ(qubits[0], qubits[1]),
            "ccx" => QuantumOp::CCX(qubits[0], qubits[1], qubits[2]),
            "rx" => QuantumOp::RX(qubits[0], params[0].clone()),
            "ry" => QuantumOp::RY(qubits[0], params[0].clone()),
            "rz" => QuantumOp::RZ(qubits[0], params[0].clone()),
            "u3" => {
                if params.len() != 3 { return Err(format!("U3 expects 3 params, got {}", params.len())); }
                QuantumOp::U3(qubits[0], params[0].clone(), params[1].clone(), params[2].clone())
            },
            _ => continue, // Skip unsupported gates
        };
        ops.push(op);
    }
    let final_qubit_count = if current_qubit_count > 0 {
        current_qubit_count
    } else if ops.is_empty() {
        0
    } else {
        let max_idx = ops.iter().map(|op| op.max_qubit_idx()).max().unwrap_or(0);
        max_idx + 1
    };

    Ok((ops, final_qubit_count))
}
/// Unified entry point for reading and parsing QASM files.
pub fn parse_file(path: &Path) -> Result<(Vec<QuantumOp>, usize), String> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| format!("Failed to read QASM file '{}': {}", path.display(), e))?;
    
    // Simply delegate to parse_qasm_str
    parse_qasm_str(&content)
}
fn parse_gate_name_and_params(token: &str) -> Result<(String, Vec<PhaseCoeff>), String> {
    if let Some(start_idx) = token.find('(') {
        if let Some(end_idx) = token.rfind(')') {
            let name = token[..start_idx].trim().to_lowercase();
            let params_str = &token[start_idx+1..end_idx];
            let mut params = Vec::new();
            if !params_str.trim().is_empty() {
                for p in params_str.split(',') {
                    params.push(parse_phase_str(p.trim())?);
                }
            }
            return Ok((name, params));
        }
    }
    Ok((token.trim().to_lowercase(), vec![]))
}

fn parse_targets(targets_str: &str, reg_map: &HashMap<String, usize>) -> Result<Vec<usize>, String> {
    let clean_str = targets_str.trim().trim_matches(';');
    if clean_str.is_empty() { return Ok(vec![]); }
    
    let parts: Vec<&str> = clean_str.split(',').collect();
    let mut indices = Vec::new();

    for part in parts {
        let part = part.trim();
        let open_bracket = part.find('[').ok_or_else(|| format!("Missing '[' in target '{}'", part))?;
        let close_bracket = part.find(']').ok_or_else(|| format!("Missing ']' in target '{}'", part))?;
        
        let reg_name = &part[..open_bracket];
        let idx_str = &part[open_bracket+1..close_bracket];
        
        let offset = reg_map.get(reg_name).ok_or_else(|| format!("Unknown register: {}", reg_name))?;
        let local_idx = idx_str.parse::<usize>().map_err(|_| format!("Invalid index: {}", idx_str))?;
        
        indices.push(offset + local_idx);
    }
    Ok(indices)
}

fn parse_phase_str(s: &str) -> Result<PhaseCoeff, String> {
    // 1. Convert to lowercase and trim. This creates a new String.
    let s_owned = s.trim().to_lowercase();
    let s = s_owned.as_str(); // Use a slice reference for consistent types
    
    if s == "0" || s == "0.0" {
        return Ok(PhaseCoeff::new_constant(Rational::zero()));
    }

    // 2. Extract sign and the rest of the string
    // FIX: Ensure both branches return (bool, &str)
    let (is_negative, rest) = if s.starts_with('-') {
        (true, &s[1..])
    } else {
        (false, s) // 's' is already a &str here
    };

    // 3. Handle division (e.g., "3*pi / 4")
    let multiplier: f64 = if rest.contains('/') {
        let parts: Vec<&str> = rest.split('/').collect();
        if parts.len() != 2 {
            return Err(format!("Invalid division in phase: {}", s));
        }
        let num = eval_simple_expression(parts[0])?;
        // Use parse::<f64>() directly on the slice
        let den = parts[1].trim().parse::<f64>()
            .map_err(|_| format!("Invalid denominator in phase: {}", s))?;
        num / den
    } else {
        eval_simple_expression(rest)?
    };

    let final_val = if is_negative { -multiplier } else { multiplier };

    // 4. Final conversion via Continued Fraction
    Ok(PhaseCoeff::new_constant(Rational::from_f64(final_val)))
}


// Ensure these helpers are present as well
fn eval_simple_expression(s: &str) -> Result<f64, String> {
    let s = s.trim();
    if s.is_empty() { return Ok(1.0); }

    if s.contains('*') {
        let parts: Vec<&str> = s.split('*').collect();
        let mut res = 1.0;
        for p in parts {
            res *= parse_single_token(p)?;
        }
        Ok(res)
    } else {
        parse_single_token(s)
    }
}

fn parse_single_token(s: &str) -> Result<f64, String> {
    let s = s.trim();
    if s == "pi" {
        Ok(1.0)
    } else if let Ok(val) = s.parse::<f64>() {
        Ok(val)
    } else if s.is_empty() {
        Ok(1.0)
    } else {
        Err(format!("Invalid token in phase expression: '{}'", s))
    }
}

fn get_pi_coeff(numer: i64, denom: i64) -> PhaseCoeff {
    PhaseCoeff::new_constant(Rational::new(numer, denom * 2))
}

impl PathSum {
    pub fn load_from_qasm_file(file_path: &str, initial_state: Option<&[u8]>) -> Result<Self, String> {
        let qasm_str = std::fs::read_to_string(file_path)
            .map_err(|e| format!("Failed to read file '{}': {}", file_path, e))?;
        Self::load_from_qasm_str(&qasm_str, initial_state)
    }

    pub fn load_from_qasm_str(qasm_str: &str, initial_state: Option<&[u8]>) -> Result<Self, String> {
        let (ops, num_qubits) = parse_qasm_str(qasm_str)?;

        let regs = vec![Register::new("q", num_qubits)];
        let mut ps = PathSum::quantum_circuit(&regs, None);

        for op in ops {
            op.apply(&mut ps, false);
        }

        if let Some(state) = initial_state {
            ps.set_initial_state(state);
        }

        if ps.is_auto_reduce() {
            ps.full_reduce();
        }

        Ok(ps)
    }
}

// ==========================================
// Unit Tests
// ==========================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_qasm_bell_state_ir() {
        let qasm = r#"
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[2];
            h q[0];
            cx q[0],q[1];
        "#;
        
        let (ops, num_qubits) = parse_qasm_str(qasm).expect("IR Parse failed");
        assert_eq!(ops.len(), 2);
        assert_eq!(ops[0], QuantumOp::H(0));
        assert_eq!(ops[1], QuantumOp::CX(0, 1));
        assert_eq!(num_qubits, 2);
        
        let ps = PathSum::load_from_qasm_str(qasm, None).expect("Load failed");
        assert_eq!(ps.v.num_qubits, 2);
    }
}
