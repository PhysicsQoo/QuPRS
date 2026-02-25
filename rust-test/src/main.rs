// src/main.rs
#![allow(dead_code)]
// 1. Declare modules
mod rational;
mod pathsum;
mod gates;
mod reduction;
mod qasm;

// 2. Import required items
use pathsum::PathSum;
use gates::QuantumGates; // Must import Trait to use methods like apply_h

fn main() {
    // Simulate circuit: H(0) -> CX(0, 1) -> T(1)
    
    // Initialize 2-qubit system (x0, x1)
    let mut ps = PathSum::new(2);
    println!("Initial state:");
    ps.print_status();
    // 1. H(0) -> Generate path variable y0
    // P should add (1/2)*x0*y0
    println!("\n[Step 1] Applying H(0)...");
    ps.apply_h(0);
    ps.print_status();

    // 2. CX(0, 1) -> Entangle
    // q1 should become x1 ⊕ y0
    println!("\n[Step 2] Applying CX(0, 1)...");
    ps.apply_cx(0, 1);
    ps.print_status();

    // 3. Extra test: Apply H(1) again -> Generate path variable y1
    // This will be very complex because F[1] is (x1 ⊕ y0)
    // P should add (1/2)*(x1 ⊕ y0)*y1 = (1/2)x1*y1 + (1/2)y0*y1
    println!("\n[Step 3] Applying H(1)...");
    ps.apply_h(1);
    ps.print_status();

    println!("\n[Step 4] Applying H(0)...");
    ps.apply_h(0);
    ps.print_status();

    println!("\n=== try_reduce_hh ===");
    ps.full_reduce();
    ps.print_status();

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
    PathSum::set_global_auto_reduce(false); 
    match PathSum::load_from_qasm_str(qasm_string, None) {
        Ok(mut ps) => {
            println!("Circuit loaded successfully!");
            println!("\n=== Before Reduction ===");
            ps.print_status();

            println!("\n=== Applying Full Reduction ===");
            ps.full_reduce();
            ps.print_status();
        }
        Err(e) => {
            eprintln!("Error parsing QASM: {}", e);
        }
    }
}