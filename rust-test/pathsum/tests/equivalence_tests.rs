// tests/equivalence_tests.rs
use pathsum::pathsum::PathSum;
use pathsum::ir::QuantumOp;
use pathsum::strategy::VerificationStrategy;
use pathsum::wmc::WmcManager;
use std::f64::consts::PI;
use num_complex::Complex;

fn verify_equivalence(num_qubits: usize, gates1: &[QuantumOp], gates2: &[QuantumOp]) -> bool {
    let mut ps = PathSum::new(num_qubits);
    ps.set_auto_reduce(false);

    let strategy = VerificationStrategy::Naive;
    let mut ps_miter = strategy.run(ps, gates1, gates2);
    ps_miter.full_reduce();

    if ps_miter.is_identity_up_to_phase() {
        if let Some(phase_coeff) = ps_miter.get_global_phase() {
            let phase_val = (phase_coeff.constant.numer as f64) / (phase_coeff.constant.denom as f64);
            let amplitude = Complex::new((phase_val * PI).cos(), (phase_val * PI).sin());
            return (amplitude.norm() - 1.0).abs() < 1e-9;
        }
    }

    // ---------------------------------------------------------
    println!(">> [Diagnostics] Fast path failed. Residual PathSum state:");
    ps_miter.print_status();
    // ---------------------------------------------------------


    let initial_state = vec![0; num_qubits];
    ps_miter.set_initial_state(&initial_state);
    ps_miter.full_reduce();

    let mut wmc_mgr = WmcManager::new(&ps_miter);
    wmc_mgr.encode_boolean_state_to_zero(&ps_miter); 
    
    // ---------------------------------------------------------
    let cnf_string = wmc_mgr.to_dimacs_string();
    println!(">> [Diagnostics] CNF sent to GPMC:\n{}", cnf_string);
    // ---------------------------------------------------------

    if cnf_string.contains("p cnf 0 0") {
        println!(">> [Diagnostics] Empty CNF detected. Circuit evaluated to 0 amplitude.");
        return false; 
    }

    let raw_amplitude = wmc_mgr.solve_with_gpmc().expect("GPMC Execution Failed");

    let num_active_vars = ps_miter.v.path_vars.len() - num_qubits;
    let normalization_factor = 1.0 / 2.0_f64.powf((num_active_vars as f64) / 2.0);
    let final_amplitude = raw_amplitude * normalization_factor;

    (final_amplitude.norm() - 1.0).abs() < 1e-6
}
#[test]
fn test_h_h_is_identity() {
    // C1: Identity
    let gates1 = vec![]; 
    // C2: H * H
    let gates2 = vec![
        QuantumOp::H(0),
        QuantumOp::H(0),
    ];
    
    assert!(verify_equivalence(1, &gates1, &gates2), "H*H should equal Identity");
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
    
    assert!(verify_equivalence(2, &gates1, &gates2), "CX should equal (I⊗H) CZ (I⊗H)");
}

#[test]
fn test_non_equivalent_circuits() {
    // C1: Identity
    let gates1 = vec![];
    // C2: X
    let gates2 = vec![
        QuantumOp::X(0),
    ];
    
    assert!(!verify_equivalence(1, &gates1, &gates2), "Identity should NOT equal X");
}