// src/qasm.rs
use std::fs;
use crate::pathsum::PathSum;
use crate::gates::QuantumGates;

impl PathSum {
    pub fn load_from_qasm_file(file_path: &str) -> Result<Self, String> {
        let qasm_str = fs::read_to_string(file_path)
            .map_err(|e| format!("Failed to read file '{}': {}", file_path, e))?;
        
        // Delegate to string parsing function
        Self::load_from_qasm_str(&qasm_str)
    }
    /// Construct and initialize PathSum from OpenQASM 2.0 string
    pub fn load_from_qasm_str(qasm_str: &str) -> Result<Self, String> {
        let mut num_qubits = 0;

        // ==========================================
        // Phase 1: Scan qreg to determine total qubits
        // ==========================================
        for line in qasm_str.lines() {
            let line = line.trim();
            if line.starts_with("qreg") {
                // Parse "qreg q[3];"
                let parts: Vec<&str> = line.split(&['[', ']'][..]).collect();
                if parts.len() >= 2 {
                    if let Ok(n) = parts[1].parse::<usize>() {
                        num_qubits += n; // Support accumulation of multiple qregs (though usually only one)
                    }
                }
            }
        }

        if num_qubits == 0 {
            return Err("No qreg found or num_qubits is 0".to_string());
        }

        // Initialize engine
        let mut ps = PathSum::new(num_qubits);

        // ==========================================
        // Phase 2: Parse each line and apply quantum gates
        // ==========================================
        for line in qasm_str.lines() {
            let line = line.trim();
            
            // Skip comments and headers
            if line.is_empty() || line.starts_with("//") || line.starts_with("OPENQASM") 
               || line.starts_with("include") || line.starts_with("qreg") || line.starts_with("creg") {
                continue;
            }

            // Split using multiple delimiters, e.g., "cx q[0], q[1];" becomes ["cx", "q", "0", "q", "1"]
            let tokens: Vec<&str> = line
                .split(&[' ', ',', ';', '[', ']'][..])
                .filter(|s| !s.is_empty())
                .collect();

            if tokens.is_empty() { continue; }

            let gate = tokens[0].to_lowercase();

            // Extract qubit IDs based on different gate types
            match gate.as_str() {
                // Single-qubit gates (expected tokens[2] to be qubit ID)
                "x" | "y" | "z" | "h" | "s" | "sdg" | "t" | "tdg" => {
                    if tokens.len() >= 3 {
                        let target = tokens[2].parse::<usize>().map_err(|_| format!("Invalid qubit ID in line: {}", line))?;
                        match gate.as_str() {
                            "x" => ps.apply_x(target),
                            "y" => ps.apply_y(target),
                            "z" => ps.apply_z(target),
                            "h" => ps.apply_h(target),
                            "s" => ps.apply_s(target),
                            "sdg" => ps.apply_sdg(target),
                            "t" => ps.apply_t(target),
                            "tdg" => ps.apply_tdg(target),
                            _ => unreachable!(),
                        }
                    }
                }
                // Two-qubit gates (expected tokens[2] is control, tokens[4] is target)
                "cx" | "cz" => {
                    if tokens.len() >= 5 {
                        let ctrl = tokens[2].parse::<usize>().map_err(|_| format!("Invalid control ID in line: {}", line))?;
                        let tgt = tokens[4].parse::<usize>().map_err(|_| format!("Invalid target ID in line: {}", line))?;
                        match gate.as_str() {
                            "cx" => ps.apply_cx(ctrl, tgt),
                            "cz" => ps.apply_cz(ctrl, tgt),
                            _ => unreachable!(),
                        }
                    }
                }
                // Unsupported gates (e.g., rx, u3, measure) return error
                _ => return Err(format!("Unsupported gate: {}", gate)),
            }
        }

        Ok(ps)
    }
}

// ==========================================
// QASM Parser Unit Tests
// ==========================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_qasm_bell_state() {
        let qasm = r#"
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[2];
            h q[0];
            cx q[0],q[1];
        "#;

        let mut ps = PathSum::load_from_qasm_str(qasm).expect("Failed to parse QASM");

        // Verify qubit count
        assert_eq!(ps.v.num_qubits, 2);

        // Verify F basis (H produces y_0, CX makes q1 become x_1 ⊕ y_0)
        assert!(ps.f.functions[0].contains(&vec![2])); // y_0 ID is 2 (num_qubits=2)
        
        let mut expected_q1 = rustc_hash::FxHashSet::default();
        expected_q1.insert(vec![1]); // x_1
        expected_q1.insert(vec![2]); // y_0
        assert_eq!(ps.f.functions[1], expected_q1);
    }
}