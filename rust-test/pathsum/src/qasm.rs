// src/qasm.rs
use std::fs;
use crate::pathsum::{PathSum, Register};
use crate::gates::QuantumGates;

impl PathSum {
    /// Load and initialize PathSum from an OpenQASM 2.0 file.
    pub fn load_from_qasm_file(file_path: &str, initial_state: Option<&[u8]>) -> Result<Self, String> {
        let qasm_str = fs::read_to_string(file_path)
            .map_err(|e| format!("Failed to read file '{}': {}", file_path, e))?;
        
        Self::load_from_qasm_str(&qasm_str, initial_state)
    }

    /// Construct and initialize PathSum from an OpenQASM 2.0 string.
    pub fn load_from_qasm_str(qasm_str: &str, initial_state: Option<&[u8]>) -> Result<Self, String> {
        let mut parsed_regs = Vec::new();

        // ==========================================
        // Phase 1: Scan qreg to map physical registers
        // ==========================================
        for line in qasm_str.lines() {
            let line = line.trim();
            if line.starts_with("qreg") {
                // Parse formats like "qreg q[3];" or "qreg ancilla[2];"
                let parts: Vec<&str> = line.split(&[' ', '[', ']', ';'][..]).filter(|s| !s.is_empty()).collect();
                if parts.len() >= 3 {
                    let reg_name = parts[1];
                    if let Ok(size) = parts[2].parse::<usize>() {
                        parsed_regs.push(Register::new(reg_name, size));
                    }
                }
            }
        }

        if parsed_regs.is_empty() {
            return Err("No qreg found in the provided QASM string.".to_string());
        }

        // ==========================================
        // Phase 2: Initialize engine via our unified API
        // ==========================================
        // We do NOT pass initial_state here yet, because we need to apply gates first
        // on the generic unitary state, then collapse it at the very end.
        let mut ps = PathSum::quantum_circuit(&parsed_regs, None);

        // ==========================================
        // Phase 3: Parse each line and apply quantum gates
        // ==========================================
        for line in qasm_str.lines() {
            let line = line.trim();
            
            // Skip comments and headers
            if line.is_empty() || line.starts_with("//") || line.starts_with("OPENQASM") 
               || line.starts_with("include") || line.starts_with("qreg") || line.starts_with("creg") {
                continue;
            }

            // Extract gate and target IDs
            let tokens: Vec<&str> = line
                .split(&[' ', ',', ';', '[', ']', '(', ')'][..])
                .filter(|s| !s.is_empty())
                .collect();

            if tokens.is_empty() { continue; }

            let gate = tokens[0].to_lowercase();

            match gate.as_str() {
                // Single-qubit gates
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
                // Two-qubit gates
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
                // Triple-qubit gates (e.g., CCX)
                "ccx" => {
                    if tokens.len() >= 7 {
                        let ctrl1 = tokens[2].parse::<usize>().map_err(|_| format!("Invalid control1 ID in line: {}", line))?;
                        let ctrl2 = tokens[4].parse::<usize>().map_err(|_| format!("Invalid control2 ID in line: {}", line))?;
                        let tgt = tokens[6].parse::<usize>().map_err(|_| format!("Invalid target ID in line: {}", line))?;
                        ps.apply_ccx(ctrl1, ctrl2, tgt);
                    }
                }
                _ => return Err(format!("Unsupported gate: {}", gate)),
            }
        }

        // ==========================================
        // Phase 4: Apply state collapse if initial_state is provided
        // ==========================================
        if let Some(state) = initial_state {
            ps.set_initial_state(state);
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
    fn test_parse_qasm_bell_state_generic() {
        // Test parsing generic unitary without initial state
        let qasm = r#"
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[2];
            h q[0];
            cx q[0],q[1];
        "#;

        let mut ps = PathSum::load_from_qasm_str(qasm, None).expect("Failed to parse QASM");
        ps.set_auto_reduce(false); // Disable auto-reduce to inspect raw variables

        assert_eq!(ps.v.num_qubits, 2);
        assert_eq!(ps.f.registers.len(), 1);
        assert_eq!(ps.f.registers[0].name, "q");

        // Verify F basis (H produces y_0, CX makes q1 become x_1 ⊕ y_0)
        assert!(ps.f.functions[0].contains(&vec![2])); // y_0 ID is 2
        
        let mut expected_q1 = rustc_hash::FxHashSet::default();
        expected_q1.insert(vec![1]); // x_1
        expected_q1.insert(vec![2]); // y_0
        assert_eq!(ps.f.functions[1], expected_q1);
    }

    #[test]
    fn test_parse_qasm_multiple_registers() {
        // Test parsing multiple qregs and checking formatting
        let qasm = r#"
            OPENQASM 2.0;
            qreg q[1];
            qreg ancilla[2];
            h q[0];
            cx q[0], ancilla[0];
        "#;

        let ps = PathSum::load_from_qasm_str(qasm, None).expect("Failed to parse multi-reg QASM");
        
        assert_eq!(ps.v.num_qubits, 3);
        assert_eq!(ps.f.registers.len(), 2);
        assert_eq!(ps.f.registers[0].name, "q");
        assert_eq!(ps.f.registers[1].name, "ancilla");

        // Flat index 1 should map to |ancilla_0>
        assert_eq!(ps.f.format_qubit_name(1), "|ancilla_0>");
    }

    #[test]
    fn test_parse_qasm_with_initial_state() {
        // Test parsing with an initial state collapse (|00>)
        let qasm = r#"
            OPENQASM 2.0;
            qreg q[2];
            h q[0];
            cx q[0],q[1];
        "#;

        // Apply |00> as initial state
        let ps = PathSum::load_from_qasm_str(qasm, Some(&[0, 0])).expect("Failed to parse QASM");
        
        // After substituting x_0 = 0 and x_1 = 0, the input variables should be gone from F
        // F[0] should just be {y_0}
        assert_eq!(ps.f.functions[0].len(), 1);
        assert!(ps.f.functions[0].contains(&vec![2])); // only y_0 remains
        
        // F[1] should also just be {y_0} because x_1 was 0
        assert_eq!(ps.f.functions[1].len(), 1);
        assert!(ps.f.functions[1].contains(&vec![2])); // only y_0 remains
    }
}