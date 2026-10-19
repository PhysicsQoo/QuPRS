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
        "gpmc",
        600 // Explicit finite test budget; zero is an invalid public timeout.
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
        "gpmc",
        600 // Explicit finite test budget; zero is an invalid public timeout.
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
        "gpmc",
        600 // Explicit finite test budget; zero is an invalid public timeout.
    ).unwrap();
    
    assert_eq!(result.status, EquivalenceStatus::NotEquivalent, "Identity should NOT equal X");
}
#[test]
fn test_zero_timeout_rejected_explicitly() {
    let no_gates: Vec<QuantumOp> = vec![];
    let result = check_equivalence(
        1,
        &no_gates,
        &no_gates,
        VerificationMethod::Hybrid,
        VerificationStrategy::Difference,
        "gpmc",
        0,
    );
    assert!(result.is_err(), "zero must not silently disable the deadline");
}

#[test]
fn test_wmc_only_constrained_trace_is_not_trivial_without_path_vars() {
    // This is a real counting regression, not just a reduction-rules test.
    // Identity and X/Z have no extra path variables but zero trace.
    for solver in ["gpmc", "ganak"] {
        for gate in [QuantumOp::X(0), QuantumOp::Z(0)] {
            let result = check_equivalence(
                1, &[], &[gate],
                VerificationMethod::WmcOnly,
                VerificationStrategy::Difference,
                solver, 60,
            ).unwrap();
            assert_eq!(
                result.status, EquivalenceStatus::NotEquivalent,
                "trace constraints must not be bypassed by WmcOnly for {solver}"
            );
        }
        let identity = check_equivalence(
            1, &[], &[],
            VerificationMethod::WmcOnly,
            VerificationStrategy::Difference,
            solver, 60,
        ).unwrap();
        assert_eq!(identity.status, EquivalenceStatus::Equivalent);
    }
}
