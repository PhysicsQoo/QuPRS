// src/main.rs

// 1. Declare modules
mod rational;
mod pathsum;
mod gates;

// 2. Import required items
use pathsum::PathSum;
use gates::QuantumGates; // Must import Trait to use methods like apply_h

fn main() {
    // Simulate circuit: H(0) -> CX(0, 1) -> T(1)
    
    // Initialize 2-qubit system (x0, x1)
    let mut ps = PathSum::new(2);
    
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
}