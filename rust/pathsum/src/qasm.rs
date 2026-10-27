// src/qasm.rs
use std::collections::HashMap;
use std::path::Path;
use crate::ir::QuantumOp;
use crate::pathsum::{PathSum, Register};
use crate::rational::{Angle};

/// Parse QASM string into a list of quantum operations
pub fn parse_qasm_str(source: &str) -> Result<(Vec<QuantumOp>, usize), String> {
    let mut ops = Vec::new();
    let mut register_map: HashMap<String, usize> = HashMap::new();
    let mut register_sizes: HashMap<String, usize> = HashMap::new();
    let mut current_qubit_count = 0;

    for (line_num, line) in source.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with("//") { continue; }
        if line.starts_with("OPENQASM") {
            if line != "OPENQASM 2.0;" {
                return Err(format!("Unsupported QASM header at line {}: only OPENQASM 2.0 is supported", line_num + 1));
            }
            continue;
        }
        if line.starts_with("include") {
            if line != "include \"qelib1.inc\";" {
                return Err(format!("Unsupported QASM include at line {}", line_num + 1));
            }
            continue;
        }

        if line.starts_with("qreg ") {
            let parts: Vec<&str> = line.split(&[' ', '[', ']', ';'][..]).filter(|s| !s.is_empty()).collect();
            if parts.len() != 3 || parts[0] != "qreg" || !line.ends_with(';') {
                return Err(format!("Invalid qreg at line {}", line_num + 1));
            }
            let name = parts[1].to_string();
            let size = parts[2].parse::<usize>().map_err(|_| format!("Invalid qreg size at line {}", line_num + 1))?;
            if size == 0 || register_map.contains_key(&name) {
                return Err(format!("Empty or duplicate quantum register at line {}", line_num + 1));
            }
            register_map.insert(name.clone(), current_qubit_count);
            register_sizes.insert(name, size);
            current_qubit_count = current_qubit_count.checked_add(size)
                .ok_or_else(|| format!("Qubit count overflow at line {}", line_num + 1))?;
            continue;
        }
        if line.starts_with("creg ") { continue; }

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

        if full_gate_part.is_empty() || targets_part.is_empty() || targets_part == ";" {
            return Err(format!("Missing QASM gate or targets at line {}", line_num + 1));
        }
        if !line.ends_with(';') {
            return Err(format!("Missing QASM semicolon at line {}", line_num + 1));
        }

        let (gate_name, params) = parse_gate_name_and_params(full_gate_part)?;
        // Identify unsupported operations *before* parsing their operands:
        // measure/reset/conditional syntax is not unitary target syntax.
        if !matches!(gate_name.as_str(),
            "h" | "x" | "y" | "z" | "s" | "sdg" | "t" | "tdg" | "sx" | "sxdg" | "id"
            | "cx" | "cz" | "swap" | "ccx" | "rx" | "ry" | "rz"
            | "p" | "cp" | "u1" | "u2" | "u3" | "u" | "barrier") {
            return Err(format!("Unsupported QASM gate '{}' at line {}", gate_name, line_num + 1));
        }
        let qubits = parse_targets(targets_part, &register_map, &register_sizes)
            .map_err(|e| format!("Line {}: {}", line_num + 1, e))?;
        // Reject malformed parameter/arity combinations instead of silently
        // constructing a different quantum operation or indexing past a Vec.
        let arity = match gate_name.as_str() {
            "h" | "x" | "y" | "z" | "s" | "sdg" | "t" | "tdg" | "sx" | "sxdg" | "id" => (1, 0),
            "cx" | "cz" | "swap" => (2, 0),
            "ccx" => (3, 0),
            "rx" | "ry" | "rz" | "p" | "u1" => (1, 1),
            "cp" => (2, 1),
            "u2" => (1, 2),
            "u3" | "u" => (1, 3),
            "barrier" => (qubits.len(), 0), // Unitary no-op, validated targets.
            _ => return Err(format!("Unsupported QASM gate '{}' at line {}", gate_name, line_num + 1)),
        };
        if qubits.len() != arity.0 || params.len() != arity.1 {
            return Err(format!(
                "Invalid QASM arity for '{}' at line {}: {} qubits, {} parameters",
                gate_name, line_num + 1, qubits.len(), params.len()
            ));
        }
        if (gate_name == "cx" || gate_name == "cz" || gate_name == "swap" || gate_name == "ccx" || gate_name == "cp")
            && qubits.iter().enumerate().any(|(i, &q)| qubits[..i].contains(&q)) {
            return Err(format!("Duplicate qubit operand at line {}", line_num + 1));
        }
        if gate_name == "barrier" || gate_name == "id" { continue; }
        if gate_name == "cp" {
            // Controlled-P(theta) is exactly:
            //   P(theta/2) on control, CX, P(-theta/2) on target, CX,
            //   P(theta/2) on target.
            // This is an algebraic identity for the parsed Angle, not
            // an approximate transpiler rewrite, and adds no scalar phase.
            let control = qubits[0];
            let target = qubits[1];
            let half = params[0].clone() / 2;
            let negative_half = Angle::ZERO - half.clone();
            ops.push(QuantumOp::P(control, half.clone()));
            ops.push(QuantumOp::CX(control, target));
            ops.push(QuantumOp::P(target, negative_half));
            ops.push(QuantumOp::CX(control, target));
            ops.push(QuantumOp::P(target, half));
            continue;
        }
        if gate_name == "sx" || gate_name == "sxdg" {
            // Qiskit SX = H S H and SXdg = H SDG H exactly, including
            // scalar phase. Do not lower with floating rotation synthesis.
            let q = qubits[0];
            ops.push(QuantumOp::H(q));
            ops.push(if gate_name == "sx" { QuantumOp::S(q) } else { QuantumOp::SDG(q) });
            ops.push(QuantumOp::H(q));
            continue;
        }

        let op = match gate_name.as_str() {
            "h" => QuantumOp::H(qubits[0]),
            "x" => QuantumOp::X(qubits[0]),
            "y" => QuantumOp::Y(qubits[0]),
            "z" => QuantumOp::Z(qubits[0]),
            "s" => QuantumOp::S(qubits[0]),
            "sdg" => QuantumOp::SDG(qubits[0]),
            "t" => QuantumOp::T(qubits[0]),
            "tdg" => QuantumOp::TDG(qubits[0]),
            "cx" => QuantumOp::CX(qubits[0], qubits[1]),
            "cz" => QuantumOp::CZ(qubits[0], qubits[1]),
            "swap" => QuantumOp::SWAP(qubits[0], qubits[1]),
            "ccx" => QuantumOp::CCX(qubits[0], qubits[1], qubits[2]),
            "rx" => QuantumOp::RX(qubits[0], params[0].clone()),
            "ry" => QuantumOp::RY(qubits[0], params[0].clone()),
            "rz" => QuantumOp::RZ(qubits[0], params[0].clone()),
            "p" => QuantumOp::P(qubits[0], params[0].clone()),
            "u1" => QuantumOp::U1(qubits[0], params[0].clone()),
            "u2" => QuantumOp::U2(qubits[0], params[0].clone(), params[1].clone()),
            "u3" => QuantumOp::U3(qubits[0], params[0].clone(), params[1].clone(), params[2].clone()),
            "u" => QuantumOp::U(qubits[0], params[0].clone(), params[1].clone(), params[2].clone()),
            _ => unreachable!("All gate names validated above"),
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
fn parse_gate_name_and_params(token: &str) -> Result<(String, Vec<Angle>), String> {
    if let Some(start_idx) = token.find('(') {
        if let Some(end_idx) = token.rfind(')') {
            let name = token[..start_idx].trim().to_lowercase();
            let params_str = &token[start_idx+1..end_idx];
            let mut params = Vec::new();
            if !params_str.trim().is_empty() {
                for p in params_str.split(',') {
                    params.push(Angle::from_qasm_str(p.trim())?);
                }
            }
            return Ok((name, params));
        }
    }
    Ok((token.trim().to_lowercase(), vec![]))
}

fn parse_targets(targets_str: &str, reg_map: &HashMap<String, usize>, sizes: &HashMap<String, usize>) -> Result<Vec<usize>, String> {
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
        let size = sizes.get(reg_name).ok_or_else(|| format!("Unknown register size: {}", reg_name))?;
        if local_idx >= *size { return Err(format!("Qubit index {} out of bounds for {}", local_idx, reg_name)); }
        if part[close_bracket+1..].trim().len() > 0 {
            return Err(format!("Unexpected suffix in target '{}'", part));
        }
        indices.push(offset + local_idx);
    }
    Ok(indices)
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
    #[test]
    fn decimal_angles_retain_exact_source_or_fail_closed() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        for (theta, numerator, denominator) in [
            ("1e-12", 1_i64, 1_000_000_000_000_i64),
            ("-1e-12", -1_i64, 1_000_000_000_000_i64),
            ("1e-10", 1_i64, 10_000_000_000_i64),
            ("4e-10", 4_i64, 10_000_000_000_i64),
            ("1e-9", 1_i64, 1_000_000_000_i64),
        ] {
            let qasm = format!(
                "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nrz({theta}) q[0];"
            );
            let (ops, count) = parse_qasm_str(&qasm).expect("bounded nonzero angle must survive");
            assert_eq!(count, 1);
            match &ops[0] {
                QuantumOp::RZ(0, angle) => {
                    assert_eq!(angle.constant.numer, 0);
                    assert_eq!(
                        angle.radians,
                        Some(BigRational::new(
                            BigInt::from(numerator), BigInt::from(denominator)
                        ))
                    );
                }
                op => panic!("expected RZ, got {op:?}"),
            }
        }
        for theta in ["0", "0.0", "0e-1000", "-0e-1000", "pi", "pi/2", "0.001"] {
            let qasm = format!(
                "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nrz({theta}) q[0];"
            );
            assert!(parse_qasm_str(&qasm).is_ok(), "must accept {theta}");
        }
        for theta in ["1e-1000", "1/0", "1e999", "1e-2147483648", "pi*pi"] {
            let qasm = format!(
                "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nrz({theta}) q[0];"
            );
            assert!(parse_qasm_str(&qasm).is_err(), "must reject unsupported {theta}");
        }
    }

    #[test]
    fn reject_unsupported_qasm_gates_instead_of_discarding_them() {
        for (qasm, expected) in [
            ("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncsx q[0],q[1];", "Unsupported QASM gate 'csx'"),
            ("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncrx(0.1) q[0],q[1];", "Unsupported QASM gate 'crx'"),
            ("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nmeasure q[0] -> c[0];", "Unsupported QASM gate 'measure'"),
            ("OPENQASM 3.0;\nqubit[1] q;\nx q[0];", "Unsupported QASM header"),
            ("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nreset q[0];", "Unsupported QASM gate 'reset'"),
        ] {
            let msg = parse_qasm_str(qasm).unwrap_err();
            assert!(msg.contains(expected), "expected {expected}, got: {msg}");
        }
    }

    #[test]
    fn reject_bad_qubit_index_parameter_count_and_operand_count() {
        for qasm in [
            "qreg q[1];\nx q[9];",
            "qreg q[1];\nx q[0],q[0];",
            "qreg q[2];\ncx q[0];",
            "qreg q[2];\ncx q[0],q[0];",
            "qreg q[1];\nrz q[0];",
            "qreg q[1];\nrz(0.1,0.2) q[0];",
            "qreg q[1];\nx q[0]",
            "qreg q[0];\nx q[0];",
        ] {
            assert!(parse_qasm_str(qasm).is_err(), "unexpectedly accepted: {qasm}");
        }
    }

    #[test]
    fn supported_phase_aliases_and_swap_create_real_operations() {
        let qasm = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\np(0.125) q[0];\nu1(0.25) q[0];\nu2(0.1,0.2) q[1];\nu3(0.1,0.2,0.3) q[0];\nu(0.1,0.2,0.3) q[1];\nswap q[0],q[1];\nbarrier q[0],q[1];";
        let (ops, qubits) = parse_qasm_str(qasm).expect("supported QASM should parse");
        assert_eq!(qubits, 2);
        assert_eq!(ops.len(), 6, "barrier alone may be omitted");
        assert!(matches!(ops[0], QuantumOp::P(0, _)));
        assert!(matches!(ops[1], QuantumOp::U1(0, _)));
        assert!(matches!(ops[2], QuantumOp::U2(1, _, _)));
        assert!(matches!(ops[3], QuantumOp::U3(0, _, _, _)));
        assert!(matches!(ops[4], QuantumOp::U(1, _, _, _)));
        assert!(matches!(ops[5], QuantumOp::SWAP(0, 1)));
    }

    #[test]
    fn sx_sxdg_exact_clifford_decomposition() {
        let qasm = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nsx q[0];\nsxdg q[0];";
        let (ops, n) = parse_qasm_str(qasm).unwrap();
        assert_eq!(n, 1);
        assert_eq!(ops, vec![
            QuantumOp::H(0), QuantumOp::S(0), QuantumOp::H(0),
            QuantumOp::H(0), QuantumOp::SDG(0), QuantumOp::H(0),
        ]);
    }

    #[test]
    fn cp_phase_is_exact_five_gate_decomposition() {
        let qasm = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncp(pi) q[0],q[1];";
        let (ops, qubits) = parse_qasm_str(qasm).unwrap();
        assert_eq!(qubits, 2);
        let half = Angle::from_qasm_str("pi").unwrap() / 2;
        assert_eq!(ops, vec![
            QuantumOp::P(0, half.clone()),
            QuantumOp::CX(0, 1),
            QuantumOp::P(1, Angle::ZERO - half.clone()),
            QuantumOp::CX(0, 1),
            QuantumOp::P(1, half),
        ]);
    }

    #[test]
    fn cp_invalid_arity_and_repeated_qubits_fail_closed() {
        for source in [
            "cp(pi) q[0];",
            "cp(pi) q[0],q[0];",
            "cp(pi,0.1) q[0],q[1];",
            "cp(pi) q[0],q[2];",
        ] {
            let qasm = format!("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\n{source}");
            assert!(parse_qasm_str(&qasm).is_err(), "must reject: {source}");
        }
    }

    #[test]
    fn preserve_qasm2_subset_bell_gate_semantics() {
        let qasm = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg a[1];\nqreg b[1];\nh a[0];\ncx a[0],b[0];";
        let (ops, n) = parse_qasm_str(qasm).unwrap();
        assert_eq!(n, 2);
        assert_eq!(ops, vec![QuantumOp::H(0), QuantumOp::CX(0,1)]);
    }

    /// Audits full two-qubit CP source semantics from the *unreduced* native
    /// PathSum instead of comparing two aliases or relying on a WMC verdict.
    /// Every Boolean phase term is evaluated using exact modular rationals.
    /// This finite, rational-pi gate subset does not certify arbitrary
    /// decimal-radian QASM input parsing.
    fn cp_unreduced_basis_phases(qasm: &str, bra: bool) -> [crate::rational::Rational; 4] {
        use crate::rational::Rational;
        let (ops, qubits) = parse_qasm_str(qasm).expect("supported controlled phase");
        assert_eq!(qubits, 2);
        let mut ps = PathSum::new(2);
        ps.set_auto_reduce(false);
        if bra {
            for op in ops.iter().rev() {
                op.apply(&mut ps, true);
            }
        } else {
            for op in &ops {
                op.apply(&mut ps, false);
            }
        }
        assert_eq!(ps.v.path_vars.len(), 2, "CP cannot introduce fresh path variables");
        assert_eq!(ps.f.functions.len(), 2);
        let mut measured = [Rational::ZERO; 4];
        for basis in 0..4usize {
            let monomial_true = |vars: &Vec<u32>| -> bool {
                vars.iter().all(|&v| {
                    assert!(v < 2, "unexpected non-source phase variable: {v}");
                    (basis & (1usize << v)) != 0
                })
            };
            let mut output = 0usize;
            for (qubit, terms) in ps.f.functions.iter().enumerate() {
                let bit = terms.iter().fold(false, |acc, monomial| {
                    acc ^ monomial_true(monomial)
                });
                if bit { output |= 1usize << qubit; }
            }
            assert_eq!(output, basis, "CP must preserve every computational basis state");

            let mut accumulated = Rational::ZERO;
            for (monomial, coefficient) in &ps.p.terms {
                assert!(coefficient.symbols.is_empty(), "Only exact rational-pi source phases");
                if monomial_true(monomial) {
                    accumulated += coefficient.constant;
                }
            }
            measured[basis] = accumulated;
        }
        measured
    }

    #[test]
    fn cp_unreduced_two_qubit_exact_diagonal_phase_and_bra_conjugation() {
        use crate::rational::Rational;
        // These expected CP phases come from diag(1,1,1,e^(i*theta)),
        // independently of the native P/CX decomposition.
        for (angle, expected) in [
            ("pi", Rational::HALF),
            ("pi/2", Rational::QUARTER),
            ("pi/4", Rational::new(1, 8)),
            ("-pi/2", Rational::new(3, 4)),
        ] {
            for (control, target) in [(0, 1), (1, 0)] {
                let source = format!(
                    "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncp({angle}) q[{control}],q[{target}];"
                );
                let ket = cp_unreduced_basis_phases(&source, false);
                let bra = cp_unreduced_basis_phases(&source, true);
                assert_eq!(ket, [Rational::ZERO, Rational::ZERO, Rational::ZERO, expected],
                           "wrong exact Ket diagonal CP phase for {angle}, {control}->{target}");
                assert_eq!(bra, [Rational::ZERO, Rational::ZERO, Rational::ZERO,
                                 Rational::ZERO - expected],
                           "wrong exact Bra diagonal CP phase for {angle}, {control}->{target}");
                if expected != Rational::ZERO {
                    assert_ne!(ket, [Rational::ZERO; 4], "CP was silently erased");
                }
            }
        }
    }

    #[test]
    fn cp_unreduced_cancellation_and_cz_source_semantics() {
        use crate::rational::Rational;
        let preamble = "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\n";
        let cancel = format!(
            "{preamble}cp(pi/2) q[0],q[1];\ncp(-pi/2) q[0],q[1];"
        );
        let cz = format!("{preamble}cz q[0],q[1];");
        let cp_pi = format!("{preamble}cp(pi) q[0],q[1];");
        assert_eq!(cp_unreduced_basis_phases(&cancel, false), [Rational::ZERO;4]);
        assert_eq!(cp_unreduced_basis_phases(&cancel, true), [Rational::ZERO;4]);
        // Check the source CP(pi) phase agrees with the *independently
        // implemented* CZ source gate, not merely another P/CX sequence.
        assert_eq!(cp_unreduced_basis_phases(&cp_pi, false),
                   cp_unreduced_basis_phases(&cz, false));
        assert_eq!(cp_unreduced_basis_phases(&cp_pi, true),
                   cp_unreduced_basis_phases(&cz, true));
    }

}
