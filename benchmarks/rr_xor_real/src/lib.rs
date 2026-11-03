//! Real-world OpenQASM 2.0 pair RR evidence, with no GPMC/Ganak process.
//! Uses the native verifier's Proportional strategy, automatic on-gate RR,
//! final RR normalization, and the exact source Angle representation.
use std::path::PathBuf;
use std::sync::OnceLock;
use pathsum::qasm::parse_file;
use pathsum::ir::QuantumOp;
use pathsum::rr_xor_witness::{self, Witness};
use pathsum::{PathSum, VerificationStrategy};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Copy)]
pub enum Case {
    Qft16,
    QpeExact8,
    QpeInexact8,
    Vqe4,
}
impl Case {
    pub const ALL: [Case; 4] = [
        Case::Qft16, Case::QpeExact8, Case::QpeInexact8, Case::Vqe4
    ];
    pub fn id(self) -> &'static str {
        match self {
            Self::Qft16 => "qft16",
            Self::QpeExact8 => "qpeexact8",
            Self::QpeInexact8 => "qpeinexact8",
            Self::Vqe4 => "vqe4",
        }
    }
    pub fn filename(self) -> &'static str {
        match self {
            Self::Qft16 => "qft_nativegates_ibm_qiskit_opt0_16.qasm",
            Self::QpeExact8 => "qpeexact_nativegates_ibm_qiskit_opt0_8.qasm",
            Self::QpeInexact8 => "qpeinexact_nativegates_ibm_qiskit_opt0_8.qasm",
            Self::Vqe4 => "vqe_nativegates_ibm_qiskit_opt0_4.qasm",
        }
    }
    // Case registry matches the existing solver-inclusive benchmark's
    // direction when defined. QPE uses the usual original -> transpiled pair.
    pub fn reverse(self) -> bool { matches!(self, Self::Qft16) }
}

pub struct RealCircuit {
    pub n: usize,
    pub base: Vec<QuantumOp>,
    pub candidate: Vec<QuantumOp>,
    pub qasm_sha256: [String; 2],
}

fn load_case(case: Case) -> RealCircuit {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../MQTBench");
    let source = root.join(case.filename());
    let transpiled = root.join("h,ry,rz,cx").join(case.filename());
    let mut paths = [source, transpiled];
    if case.reverse() { paths.swap(0, 1); }
    let (a, na) = parse_file(&paths[0]).expect("real-QASM parse first source");
    let (b, nb) = parse_file(&paths[1]).expect("real-QASM parse second source");
    assert_eq!(na, nb, "qubits differ for {:?}", case);
    let hashes = paths.map(|p| {
        let contents = std::fs::read(p).expect("source QASM bytes");
        format!("{:x}", Sha256::digest(contents))
    });
    RealCircuit { n: na, base: a, candidate: b, qasm_sha256: hashes }
}

static QFT16: OnceLock<RealCircuit> = OnceLock::new();
static QPE_EXACT8: OnceLock<RealCircuit> = OnceLock::new();
static QPE_INEXACT8: OnceLock<RealCircuit> = OnceLock::new();
static VQE4: OnceLock<RealCircuit> = OnceLock::new();

pub fn case_data(case: Case) -> &'static RealCircuit {
    match case {
        Case::Qft16 => QFT16.get_or_init(|| load_case(case)),
        Case::QpeExact8 => QPE_EXACT8.get_or_init(|| load_case(case)),
        Case::QpeInexact8 => QPE_INEXACT8.get_or_init(|| load_case(case)),
        Case::Vqe4 => VQE4.get_or_init(|| load_case(case)),
    }
}

/// This is the same miter + on-gate/final RR execution as the native verifier,
/// without post-RR WMC solver invocation. No source angle is rounded.
pub fn execute_rr(n: usize, left: &[QuantumOp], right: &[QuantumOp]) -> PathSum {
    let mut state = PathSum::new(n);
    state.rr_tolerance = 1e-10;
    let mut residual = VerificationStrategy::Proportional.run(state, left, right);
    residual.full_reduce();
    residual
}

pub fn collect(case: Case) -> (PathSum, Witness) {
    let inputs = case_data(case);
    rr_xor_witness::begin(4096);
    let output = execute_rr(inputs.n, &inputs.base, &inputs.candidate);
    let witness = rr_xor_witness::finish();
    assert_eq!(output.stats.hh.successes, witness.counts.hh_substitutions,
        "every HH rule must produce one captured HH substitution");
    (output, witness)
}

static TRACE_QFT16: OnceLock<Witness> = OnceLock::new();
static TRACE_QPE_EXACT8: OnceLock<Witness> = OnceLock::new();
static TRACE_QPE_INEXACT8: OnceLock<Witness> = OnceLock::new();
static TRACE_VQE4: OnceLock<Witness> = OnceLock::new();

/// Source-faithful replay samples. The collection is performed once in Divan
/// setup, never under official CodSpeed measurement.
pub fn trace(case: Case) -> &'static Witness {
    match case {
        Case::Qft16 => TRACE_QFT16.get_or_init(|| collect(case).1),
        Case::QpeExact8 => TRACE_QPE_EXACT8.get_or_init(|| collect(case).1),
        Case::QpeInexact8 => TRACE_QPE_INEXACT8.get_or_init(|| collect(case).1),
        Case::Vqe4 => TRACE_VQE4.get_or_init(|| collect(case).1),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn real_qasm_hh_witness_is_reproducible_and_semantically_inert() {
        for case in Case::ALL {
            let source = case_data(case);
            let (observed, witness) = collect(case);
            let plain = execute_rr(source.n, &source.base, &source.candidate);
            assert_eq!(observed.p.terms, plain.p.terms, "phase changed for {:?}", case);
            assert_eq!(observed.f.functions, plain.f.functions, "Boolean F changed for {:?}", case);
            assert_eq!(observed.stats.hh.successes, plain.stats.hh.successes);
            assert_eq!(witness.counts.hh_substitutions, observed.stats.hh.successes);
            assert_eq!(witness.samples.len() + witness.counts.sample_truncations,
                witness.counts.phase_affected);
            let bra = &witness.bra_cx;
            let expected_cx = source.candidate.iter()
                .filter(|op| matches!(**op, QuantumOp::CX(_, _))).count();
            assert_eq!(bra.calls, expected_cx,
                "each real Bra-CX must be counted once for {:?}", case);
            assert_eq!(bra.calls, bra.touched_calls + bra.unaffected_calls);
            assert_eq!(bra.calls, bra.affected_histogram.iter().sum());
            assert_eq!(bra.affected_terms, bra.affected_per_call.iter().sum());
            assert!(bra.exact_radian_terms <= bra.affected_terms);
            assert!(bra.symbolic_terms <= bra.affected_terms);
            assert!(bra.control_overlap_terms <= bra.affected_terms);
            assert_eq!(bra.shared_xor_calls + bra.parity_xor_calls, bra.touched_calls);
            assert_eq!(bra.shared_affected_terms + bra.parity_affected_terms,
                bra.affected_terms);
            assert_eq!(bra.shared_call_indices.len(), bra.shared_xor_calls);
            assert!(bra.exact_radian_parity_calls <= bra.parity_xor_calls);
            println!(
                "RR_CX_REAL_WITNESS={{\"case\":\"{}\",\"bra_cx_calls\":{},\"touched_calls\":{},\"unaffected_calls\":{},\"total_affected\":{},\"shared_xor_calls\":{},\"shared_affected_terms\":{},\"shared_call_indices\":{:?},\"parity_xor_calls\":{},\"parity_affected_terms\":{},\"exact_radian_parity_calls\":{},\"radian_terms\":{},\"symbolic_terms\":{},\"control_overlap_terms\":{},\"peak_phase_terms\":{},\"peak_affected_terms\":{},\"affected_histogram\":{:?},\"affected_per_call\":{:?}}}",
                case.id(), bra.calls, bra.touched_calls,
                bra.unaffected_calls, bra.affected_terms,
                bra.shared_xor_calls, bra.shared_affected_terms, bra.shared_call_indices,
                bra.parity_xor_calls, bra.parity_affected_terms, bra.exact_radian_parity_calls,
                bra.exact_radian_terms, bra.symbolic_terms, bra.control_overlap_terms,
                bra.peak_phase_terms, bra.peak_affected_terms,
                bra.affected_histogram, bra.affected_per_call,
            );
            let c = witness.counts;
            assert_eq!(c.hh_substitutions, c.phase_affected + c.no_affected_terms);
            assert_eq!(c.phase_affected,
                c.zero_replacements + c.singleton_replacements
                + c.shared_xor_hits + c.parity_xor_hits);
            println!(
                "RR_XOR_REAL_WITNESS={{\"case\":\"{}\",\"qubits\":{},\"gates_reference\":{},\"gates_candidate\":{},\"sha_reference\":\"{}\",\"sha_candidate\":\"{}\",\"hh_attempts\":{},\"hh_successes\":{},\"hh_substitutions\":{},\"affected\":{},\"no_affected\":{},\"shared_xor_hits\":{},\"shared_symbolic_hits\":{},\"parity_xor_hits\":{},\"parity_exact_radian_hits\":{},\"zero\":{},\"singleton\":{},\"max_affected\":{},\"max_xor\":{},\"total_affected_terms\":{},\"snapshots\":{},\"truncated\":{}}}",
                case.id(), source.n, source.base.len(), source.candidate.len(),
                source.qasm_sha256[0], source.qasm_sha256[1],
                observed.stats.hh.attempts, observed.stats.hh.successes,
                c.hh_substitutions, c.phase_affected, c.no_affected_terms,
                c.shared_xor_hits, c.shared_symbolic_hits,
                c.parity_xor_hits, c.parity_exact_radian_hits,
                c.zero_replacements, c.singleton_replacements,
                c.max_affected_terms, c.max_replacement_terms, c.total_affected_terms,
                witness.samples.len(), c.sample_truncations,
            );
        }
    }
}
