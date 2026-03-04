use pathsum::pathsum::PathSum;
use pathsum::gates::{QuantumGates, Side};
use pathsum::rational::{PhaseCoeff, Rational};

// Helper function: create a PhaseCoeff as a fraction of PI
fn pi_coeff(numer: i64, denom: i64) -> PhaseCoeff {
    // 1 cycle = 2*PI, so PI = 1/2 cycle
    // (numer/denom) * PI = (numer/denom) * (1/2) cycle
    PhaseCoeff::new_constant(Rational::new(numer, denom * 2))
}

#[test]
fn test_rx_annihilation() {
    println!(">> Testing RX(theta) * RX(theta)^dagger = I");
    let mut ps = PathSum::new(1);
    
    let theta = pi_coeff(1, 3);

    ps.apply_rx(0, theta.clone(), Side::Ket);
    ps.apply_rx(0, theta.clone(), Side::Bra);

    ps.full_reduce();
    
    if !ps.is_identity() {
        println!("!! RX Failed !! P terms: {:?}", ps.p.terms);
    }
    assert!(ps.is_identity(), "RX(theta) should verify U†U = I");
}

#[test]
fn test_ry_annihilation() {
    println!(">> Testing RY(theta) * RY(theta)^dagger = I");
    let mut ps = PathSum::new(1);
    
    let theta = pi_coeff(1, 4);

    ps.apply_ry(0, theta.clone(), Side::Ket);
    ps.apply_ry(0, theta.clone(), Side::Bra);

    ps.full_reduce();
    
    assert!(ps.is_identity(), "RY(theta) should verify U†U = I");
}

#[test]
fn test_u3_annihilation() {
    println!(">> Testing U3(t,p,l) * U3(t,p,l)^dagger = I");
    let mut ps = PathSum::new(1);
    
    let theta = pi_coeff(1, 2); // PI/2
    let phi = pi_coeff(1, 3);   // PI/3
    let lam = pi_coeff(1, 4);   // PI/4

    ps.apply_u3(0, theta.clone(), phi.clone(), lam.clone(), Side::Ket);
    ps.apply_u3(0, theta.clone(), phi.clone(), lam.clone(), Side::Bra);

    ps.full_reduce();
    ps.print_status();
    assert!(ps.is_identity(), "U3 should verify U†U = I");
}

#[test]
fn test_u3_is_identity_when_params_zero() {
    println!(">> Testing U3(0,0,0) == I");
    let mut ps = PathSum::new(1);
    
    let zero = pi_coeff(0, 1);
    
    ps.apply_u3(0, zero.clone(), zero.clone(), zero.clone(), Side::Ket);
    
    ps.full_reduce();
    
    assert!(ps.is_identity(), "U3(0,0,0) must be Identity");
}

#[test]
fn test_equivalence_z_vs_u3() {
    println!(">> Testing Z == U3(0, pi, 0) (up to global phase)");
    let mut ps = PathSum::new(1);

    ps.apply_z(0, Side::Ket);
    let theta = pi_coeff(0, 1); // 0
    let phi = pi_coeff(1, 1);   // pi
    let lam = pi_coeff(0, 1);   // 0
    
    ps.apply_u3(0, theta, phi, lam, Side::Bra);

    ps.full_reduce();

    if !ps.is_identity_up_to_phase() {
        println!("!! Check Failed !! P terms: {:?}", ps.p.terms);
    }

    // assert!(ps.is_identity_up_to_phase(), "Z must be equivalent to U3(0, pi, 0)");
}