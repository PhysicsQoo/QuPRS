#[cfg(test)]
mod integration_tests {
    use pathsum::pathsum::PathSum; 
    use pathsum::gates::{QuantumGates, Side};
    use pathsum::rational::{PhaseCoeff, Rational};
    
    // Simple deterministic pseudo-random generator (LCG)
    struct Rng {
        state: u64,
    }

    impl Rng {
        fn new(seed: u64) -> Self {
            Self { state: seed }
        }

        fn next_u64(&mut self) -> u64 {
            self.state = self.state.wrapping_mul(6364136223846793005).wrapping_add(1);
            self.state
        }

        fn next_usize(&mut self, limit: usize) -> usize {
            (self.next_u64() as usize) % limit
        }

        fn next_phase(&mut self) -> PhaseCoeff {
            let numer = (self.next_u64() % 4) as i64;
            let sign = if self.next_u64() % 2 == 0 { 1 } else { -1 };
            PhaseCoeff::new_constant(Rational::new(sign * numer, 4))
        }
    }

    #[derive(Debug, Clone)]
    enum Op {
        H(usize),
        CX(usize, usize),
        RX(usize, PhaseCoeff),
        RY(usize, PhaseCoeff),
        U3(usize, PhaseCoeff, PhaseCoeff, PhaseCoeff),
    }

    fn generate_random_circuit(num_qubits: usize, depth: usize, seed: u64) -> Vec<Op> {
        let mut rng = Rng::new(seed);
        let mut ops = Vec::new();

        for _ in 0..depth {
            let gate_type = rng.next_usize(5);
            let q = rng.next_usize(num_qubits);
            
            let op = match gate_type {
                0 => Op::H(q),
                1 => {
                    let target = (q + 1) % num_qubits;
                    Op::CX(q, target)
                },
                2 => Op::RX(q, rng.next_phase()),
                3 => Op::RY(q, rng.next_phase()),
                4 => Op::U3(q, rng.next_phase(), rng.next_phase(), rng.next_phase()),
                _ => unreachable!(),
            };
            ops.push(op);
        }
        ops
    }

    #[test]
    fn test_random_circuit_unitary_annihilation() {
        let num_qubits = 3;
        let depth = 50;
        let num_trials = 10;

        for i in 0..num_trials {
            let seed = 20240304 + i as u64;
            let circuit = generate_random_circuit(num_qubits, depth, seed);
            
            println!(">> [Trial #{}] Testing random circuit with {} gates...", i+1, depth);

            let mut ps = PathSum::new(num_qubits);

            // Apply circuit forward (Ket mode): |ψ_out⟩ = U |ψ_in⟩
            for op in &circuit {
                match op {
                    Op::H(q) => ps.apply_h(*q, Side::Ket),
                    Op::CX(c, t) => ps.apply_cx(*c, *t, Side::Ket),
                    Op::RX(q, theta) => ps.apply_rx(*q, theta.clone(), Side::Ket),
                    Op::RY(q, theta) => ps.apply_ry(*q, theta.clone(), Side::Ket),
                    Op::U3(q, theta, phi, lam) => ps.apply_u3(*q, theta.clone(), phi.clone(), lam.clone(), Side::Ket),
                }
            }

            // Apply circuit in reverse (Bra mode): apply U† from left
            // The apply_* methods in Bra mode automatically perform variable
            // substitution and phase conjugation, equivalent to constructing U†
            for op in &circuit {
                match op {
                    Op::H(q) => ps.apply_h(*q, Side::Bra),
                    Op::CX(c, t) => ps.apply_cx(*c, *t, Side::Bra),
                    Op::RX(q, theta) => ps.apply_rx(*q, theta.clone(), Side::Bra),
                    Op::RY(q, theta) => ps.apply_ry(*q, theta.clone(), Side::Bra),
                    Op::U3(q, theta, phi, lam) => ps.apply_u3(*q, theta.clone(), phi.clone(), lam.clone(), Side::Bra),
                }
            }

            ps.full_reduce();

            let is_id = ps.is_identity();
            
            if !is_id {
                println!("!! Trial #{} FAILED !!", i+1);
                println!("Remaining PathVars: {:?}", ps.v.path_vars);
                println!("P Terms count: {}", ps.p.terms.len());
            }
            assert!(is_id, "Circuit U * U_dagger must reduce to Identity for seed {}", seed);
        }
        
        println!(">> All random circuit trials passed successfully!");
    }
}
