// tests/equivalence_tests.rs
use pathsum::ir::QuantumOp;
use pathsum::{
    check_equivalence, 
    VerificationMethod, 
    VerificationStrategy, 
    EquivalenceStatus
};

#[test]
fn test_h_h_is_identity() {
    // C1: Identity
    let gates1 = vec![]; 
    // C2: H * H
    let gates2 = vec![
        QuantumOp::H(0),
        QuantumOp::H(0),
    ];
    
    let result = check_equivalence(
        1, 
        &gates1, 
        &gates2, 
        VerificationMethod::Hybrid,          
        VerificationStrategy::Difference,    
        0                                    
    ).unwrap();
    
    assert_eq!(result.status, EquivalenceStatus::Equivalent, "H*H should equal Identity");
}

#[test]
fn test_cx_equivalence() {
    // C1: CX(0, 1)
    let gates1 = vec![
        QuantumOp::CX(0, 1),
    ];
    // C2: H(1) * CZ(0, 1) * H(1)
    let gates2 = vec![
        QuantumOp::H(1),
        QuantumOp::CZ(0, 1),
        QuantumOp::H(1),
    ];

    let result = check_equivalence(
        2, 
        &gates1, 
        &gates2, 
        VerificationMethod::Hybrid, 
        VerificationStrategy::Difference, 
        0
    ).unwrap();

    assert_eq!(result.status, EquivalenceStatus::Equivalent, "CX should equal (I⊗H) CZ (I⊗H)");
}

#[test]
fn test_non_equivalent_circuits() {
    // C1: Identity
    let gates1 = vec![];
    // C2: X
    let gates2 = vec![
        QuantumOp::X(0),
    ];
    
    let result = check_equivalence(
        1, 
        &gates1, 
        &gates2, 
        VerificationMethod::Hybrid, 
        VerificationStrategy::Difference, 
        0
    ).unwrap();
    
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent, "Identity should NOT equal X");
}