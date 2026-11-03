//! Real-QASM source-pinned native RR comparison with NO diagnostic feature.
//! The same crate is copied byte-for-byte into an immutable pre-optimization
//! checkout; only the underlying production pathsum implementation changes.
use std::path::PathBuf;
use std::sync::OnceLock;
use pathsum::ir::QuantumOp;
use pathsum::qasm::parse_file;
use pathsum::{PathSum, VerificationStrategy};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Copy)]
pub enum Case { Qft16, QpeExact8 }
impl Case {
    pub const ALL: [Case; 2] = [Case::Qft16, Case::QpeExact8];
    pub fn id(self) -> &'static str {
        match self { Self::Qft16 => "qft16", Self::QpeExact8 => "qpeexact8" }
    }
    pub fn filename(self) -> &'static str {
        match self {
            Self::Qft16 => "qft_nativegates_ibm_qiskit_opt0_16.qasm",
            Self::QpeExact8 => "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
        }
    }
}

pub struct Source {
    pub n: usize,
    pub left: Vec<QuantumOp>,
    pub right: Vec<QuantumOp>,
    pub qasm_sha256: [String; 2],
}

fn load(case: Case) -> Source {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../MQTBench");
    let original = root.join(case.filename());
    let transpiled = root.join("h,ry,rz,cx").join(case.filename());
    // QFT16 uses the same reversed pair direction as the existing ABBA case.
    let paths = if matches!(case, Case::Qft16) {
        [transpiled, original]
    } else {
        [original, transpiled]
    };
    let (left, n) = parse_file(&paths[0]).expect("valid original/transpiled QASM reference");
    let (right, m) = parse_file(&paths[1]).expect("valid original/transpiled QASM candidate");
    assert_eq!(n, m);
    let qasm_sha256 = paths.map(|p| {
        format!("{:x}", Sha256::digest(std::fs::read(p).expect("QASM bytes")))
    });
    Source { n, left, right, qasm_sha256 }
}

static QFT16: OnceLock<Source> = OnceLock::new();
static QPE_EXACT8: OnceLock<Source> = OnceLock::new();

pub fn source(case: Case) -> &'static Source {
    match case {
        Case::Qft16 => QFT16.get_or_init(|| load(case)),
        Case::QpeExact8 => QPE_EXACT8.get_or_init(|| load(case)),
    }
}

pub fn run(n: usize, left: &[QuantumOp], right: &[QuantumOp]) -> PathSum {
    let mut ps = PathSum::new(n);
    ps.rr_tolerance = 1e-10;
    let mut result = VerificationStrategy::Proportional.run(ps, left, right);
    result.full_reduce();
    result
}

/// Canonical science hash: compares exact final P, Boolean F, live path
/// variables, RR approximation provenance, and HH/Omega/Elim successes.
/// Sorting is essential because FxHashMap iteration order is not a contract.
pub fn canonical_science_digest(state: &PathSum) -> String {
    let mut hash = Sha256::new();
    let mut phase: Vec<_> = state.p.terms.iter().collect();
    phase.sort_by(|(ma, _), (mb, _)| ma.cmp(mb));
    for (mono, coeff) in phase {
        hash.update(format!("P:{mono:?}:{coeff:?}\n").as_bytes());
    }
    for (i, poly) in state.f.functions.iter().enumerate() {
        let mut monomials: Vec<_> = poly.iter().collect();
        monomials.sort();
        hash.update(format!("F{i}:{monomials:?}\n").as_bytes());
    }
    let mut vars: Vec<_> = state.v.path_vars.iter().copied().collect();
    vars.sort_unstable();
    hash.update(format!("V:{vars:?}\n").as_bytes());
    hash.update(format!(
        "RR:{}:HH{}:OM{}:EL{}\n",
        state.rr_approximate, state.stats.hh.successes,
        state.stats.omega.successes, state.stats.elim.successes
    ).as_bytes());
    format!("{:x}", hash.finalize())
}

// The same fixed, exact-source coefficient fixtures are compiled unchanged
// against the preceding guarded shared-XOR implementation and the new
// Bra-CX specialization. Their `apply_cx` semantics are compared against
// the independent general Boolean/P substitution routine.
#[derive(Clone, Copy, Debug)]
pub enum CoeffCase { Decimal, Mixed }
impl CoeffCase {
    pub const ALL: [CoeffCase; 2] = [CoeffCase::Decimal, CoeffCase::Mixed];
    pub fn id(self) -> &'static str {
        match self { Self::Decimal => "decimal", Self::Mixed => "mixed" }
    }
}

pub fn bra_cx_fixture(case: CoeffCase) -> PathSum {
    use pathsum::rational::{Angle, FreeRational, Rational};
    use pathsum::PhaseCoeff;

    let mut state = PathSum::new(6);
    let exact_decimal = Angle::from_qasm_str("0.12345678901234567890123456789")
        .expect("exact source-QASM decimal").to_phase_coeff();
    let symbolic = PhaseCoeff::new_symbolic(17, FreeRational::new(2, 3));
    for mask in 0..16usize {
        let mut mono = vec![0];
        for bit in 0..4 {
            if mask & (1 << bit) != 0 { mono.push((bit + 1) as u32); }
        }
        let coeff = match case {
            CoeffCase::Decimal => exact_decimal.clone(),
            CoeffCase::Mixed => match mask % 5 {
                0 => PhaseCoeff::HALF,
                1 => PhaseCoeff::QUARTER,
                2 => PhaseCoeff::new_constant(Rational::new(1, 8)),
                3 => exact_decimal.clone(),
                _ => symbolic.clone(),
            },
        };
        state.p.add_term(mono, coeff);
    }
    for mono in [vec![], vec![1], vec![2], vec![1, 2], vec![2, 4]] {
        state.p.add_term(mono, PhaseCoeff::QUARTER);
    }
    state
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn source_exact_native_rr_oracles_for_base_and_head() {
        for case in Case::ALL {
            let c = source(case);
            let residual = run(c.n, &c.left, &c.right);
            let digest = canonical_science_digest(&residual);
            println!(
                "RR_CX_NATIVE_PAIRED_ORACLE={{\"case\":\"{}\",\"qubits\":{},\"left_gates\":{},\"right_gates\":{},\"sha_left\":\"{}\",\"sha_right\":\"{}\",\"residual_digest\":\"{}\"}}",
                case.id(), c.n, c.left.len(), c.right.len(),
                c.qasm_sha256[0], c.qasm_sha256[1], digest
            );
        }
    }

    #[test]
    fn fixed_decimal_and_mixed_bra_cx_match_generic_and_are_source_exact() {
        use pathsum::gates::{QuantumGates, Side};
        use pathsum::pathsum::Monomial;
        use rustc_hash::FxHashSet;
        for case in CoeffCase::ALL {
            let initial = bra_cx_fixture(case);
            let mut original = initial.clone();
            let xor: FxHashSet<Monomial> = [vec![0], vec![1]].into_iter().collect();
            original.f.substitute_var_with_poly(0, &xor);
            original.p.substitute_var_with_poly(0, &xor);
            let mut candidate = initial;
            candidate.apply_cx(1, 0, Side::Bra);
            assert_eq!(original.p.terms, candidate.p.terms,
                "Bra-CX exact P mismatch in {:?} case", case);
            assert_eq!(original.f.functions, candidate.f.functions,
                "Bra-CX Boolean F mismatch in {:?} case", case);
            println!(
                "RR_CX_NATIVE_COEFF_ORACLE={{\"case\":\"{}\",\"digest\":\"{}\",\"terms\":{}}}",
                case.id(), canonical_science_digest(&candidate),
                candidate.p.terms.len(),
            );
        }
    }
}
