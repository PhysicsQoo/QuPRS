// src/main.rs
#![allow(dead_code)]

use pathsum::PathSum;
use pathsum::gates::{QuantumGates, Side}; 

fn main() {
    // Simulate circuit: H(0) -> CX(0, 1) -> T(1)
    
    // Initialize 2-qubit system (x0, x1)
    let mut ps = PathSum::new(2);
    println!("Initial state:");
    println!("{}", ps.print_status());
    // 1. H(0) -> Generate path variable y0
    // P should add (1/2)*x0*y0
    println!("\n[Step 1] Applying H(0)...");
    ps.apply_h(0, Side::Ket);
    println!("{}", ps.print_status());

    // 2. CX(0, 1) -> Entangle
    // q1 should become x1 ⊕ y0
    println!("\n[Step 2] Applying CX(0, 1)...");
    ps.apply_cx(0, 1, Side::Ket);
    println!("{}", ps.print_status());
    
    // 3. Extra test: Apply H(1) again -> Generate path variable y1
    // This will be very complex because F[1] is (x1 ⊕ y0)
    // P should add (1/2)*(x1 ⊕ y0)*y1 = (1/2)x1*y1 + (1/2)y0*y1
    println!("\n[Step 3] Applying H(1)...");
    ps.apply_h(1, Side::Ket);
    println!("{}", ps.print_status());

    println!("\n[Step 4] Applying H(0)...");
    ps.apply_h(0, Side::Ket);
    println!("{}", ps.print_status());

    println!("\n=== Full Reduction ===");
    ps.full_reduce();
    println!("{}", ps.print_status());

    let qasm_string = r#"
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        h q[0];
        cx q[0],q[1];
        s q[1];
        cx q[0],q[1];
        h q[0];
    "#;

    println!("Loading circuit from QASM...");    
    match pathsum::qasm::parse_qasm_str(qasm_string) {
        Ok((ops, num_qubits)) => {
            let mut ps_qasm = PathSum::new(num_qubits);
            ps_qasm.set_auto_reduce(false);

            for op in ops {
                op.apply(&mut ps_qasm, false);
            }

            println!("Circuit loaded successfully!");
            println!("\n=== Before Reduction ===");
            println!("{}", ps_qasm.print_status());
            println!("\n=== After Full Reduction ===");
            ps_qasm.set_auto_reduce(true);
            ps_qasm.full_reduce();
            ps_qasm.print_status();
        }
        Err(e) => {
            eprintln!("Error parsing QASM: {}", e);
        }
    }
}
