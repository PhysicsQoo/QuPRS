//! Two-qubit source-QASM -> unreduced PathSum -> complete matrix check.
//! Unlike an equivalence result or a reducer self-comparison, this enumerates
//! every internal path variable and checks each of the 4×4 amplitudes against
//! hand-specified gate matrices. Small enough to be exact in graph structure;
//! complex amplitudes are a separate floating-point numerical cross-check.
use num_complex::Complex64 as C;
use num_traits::ToPrimitive;
use quprs::ir::QuantumOp;
use quprs::qasm::parse_qasm_str;
use quprs::PathSum;
use std::f64::consts::{PI, TAU};

type M = [[C; 4]; 4];

fn qasm(gates: &str) -> String {
    format!("OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\n{gates}")
}

fn matrix_from_unreduced(ps: &PathSum) -> M {
    assert_eq!(ps.v.num_qubits, 2);
    let mut fresh: Vec<u32> = ps.v.path_vars.iter().copied()
        .filter(|&v| v >= 2).collect();
    fresh.sort_unstable();
    assert!(fresh.len() <= 14, "bounded unreduced matrix oracle");
    let mut matrix = [[C::new(0.0, 0.0); 4]; 4];
    let normalization = (1u64 << fresh.len()) as f64;
    for input in 0..4u64 {
        for mask in 0..(1u64 << fresh.len()) {
            let mut assignment = input;
            for (i, &var) in fresh.iter().enumerate() {
                assert!(var < 62);
                if (mask >> i) & 1 == 1 { assignment |= 1u64 << var; }
            }
            let truth = |monomial: &Vec<u32>| -> bool {
                monomial.iter().all(|&v| (assignment >> v) & 1 == 1)
            };
            let mut output = 0usize;
            for (qubit, poly) in ps.f.functions.iter().enumerate() {
                if poly.iter().fold(false, |acc, term| acc ^ truth(term)) {
                    output |= 1 << qubit;
                }
            }
            let mut phase_cycles = 0.0_f64;
            for (monomial, phase) in &ps.p.terms {
                assert!(phase.symbols.is_empty(), "No free parameters in fixture");
                if truth(monomial) {
                    phase_cycles += phase.constant.numer as f64
                        / phase.constant.denom as f64;
                    if let Some(rad) = &phase.radians {
                        phase_cycles += rad.to_f64().expect("bounded QASM radians") / PI;
                    }
                }
            }
            matrix[output][input as usize] += C::from_polar(1.0, TAU * phase_cycles)
                / normalization.sqrt();
        }
    }
    matrix
}
fn ket_source(gates: &str) -> Vec<QuantumOp> {
    let (ops,n)=parse_qasm_str(&qasm(gates)).expect("pinned source syntax");
    assert_eq!(n,2);
    ops
}
fn pathsum_matrix(a: &[QuantumOp], b: &[QuantumOp]) -> M {
    let mut ps=PathSum::new(2);
    ps.set_auto_reduce(false);
    // Bra gates act on the input side, maintaining B^dagger as the right
    // factor; then ket gates act on the output side, making A B^dagger.
    for op in b { op.apply(&mut ps, true); }
    for op in a { op.apply(&mut ps, false); }
    matrix_from_unreduced(&ps)
}
#[derive(Clone,Copy)]
enum Gate { RY(usize,f64), RZ(usize,f64), CX(usize,usize) }
fn direct_operator(ops: &[Gate]) -> M {
    let mut m=[[C::new(0.0,0.0);4];4];
    for i in 0..4 { m[i][i]=C::new(1.0,0.0); }
    for op in ops {
        match *op {
            Gate::RZ(q,theta) => {
                for input in 0..4 {
                    for output in 0..4 {
                        let sign=if (output >> q)&1 == 0 {-1.0} else {1.0};
                        m[output][input] *= C::from_polar(1.0,sign*theta/2.0);
                    }
                }
            }
            Gate::RY(q,theta) => {
                let c=(theta/2.0).cos();
                let s=(theta/2.0).sin();
                for input in 0..4 {
                    for output in 0..4 {
                        if (output >> q)&1 == 0 {
                            let other=output^(1<<q);
                            let a=m[output][input]; let b=m[other][input];
                            m[output][input]=c*a-s*b;
                            m[other][input]=s*a+c*b;
                        }
                    }
                }
            }
            Gate::CX(control,target) => {
                for input in 0..4 {
                    for output in 0..4 {
                        if (output >> control)&1 == 1 && (output >> target)&1 == 0 {
                            let other=output^(1<<target);
                            let tmp=m[output][input];
                            m[output][input]=m[other][input];
                            m[other][input]=tmp;
                        }
                    }
                }
            }
        }
    }
    m
}
fn conjugate_transpose(m:&M)->M {
    let mut r=[[C::new(0.0,0.0);4];4];
    for row in 0..4 { for col in 0..4 {r[row][col]=m[col][row].conj();}}
    r
}
fn matmul(a:&M,b:&M)->M {
    let mut r=[[C::new(0.0,0.0);4];4];
    for i in 0..4 {for j in 0..4 {for k in 0..4 {r[i][j]+=a[i][k]*b[k][j];}}}
    r
}
fn compare(actual:&M,expected:&M,tag:&str) {
    for r in 0..4 {for c in 0..4 {
        assert!((actual[r][c]-expected[r][c]).norm()<1e-10,
            "{tag}: row={r},col={c}, actual={}, expected={}",actual[r][c],expected[r][c]);
    }}
}
const SRC_A:&str = "rz(pi/2) q[0];\nry(2.0330832984526417) q[1];\ncx q[0],q[1];\nrz(1.1085093551371514) q[1];\nry(0.2815705644039938) q[0];";
const SRC_B:&str = "rz(pi/2) q[0];\nry(2.0330832984526417) q[1];\ncx q[0],q[1];\nrz(1.1085093551371514) q[1];\nry(0.2815705634039938) q[0];";
fn ref_ops(delta:bool)->Vec<Gate> {
    vec![
        Gate::RZ(0,PI/2.0),Gate::RY(1,2.0330832984526417),
        Gate::CX(0,1),Gate::RZ(1,1.1085093551371514),
        Gate::RY(0,if delta {0.2815705634039938} else {0.2815705644039938}),
    ]
}
#[test]
fn source_qasm_decimal_pathsum_complete_ket_and_bra_matrix() {
    let a=ket_source(SRC_A);
    let b=ket_source(SRC_B);
    let ua=direct_operator(&ref_ops(false));
    let ub=direct_operator(&ref_ops(true));
    compare(&pathsum_matrix(&a,&[]),&ua,"QASM source → ket PathSum");
    compare(&pathsum_matrix(&[],&b),&conjugate_transpose(&ub),
        "QASM source → bra PathSum");
    compare(&pathsum_matrix(&a,&b),&matmul(&ua,&conjugate_transpose(&ub)),
        "QASM source → two-qubit miter PathSum");
}


// Shared small two-qubit operator witnesses exercise the full Path-sum IR
// before and after reduction, preserving output maps and global phase.
// The Rust and Python suites consume the same independent numerical fixtures.
#[test]
fn reduced_and_unreduced_ir_match_shared_operator_witnesses() {
    use std::collections::BTreeMap;

    let mut references: BTreeMap<String, [[C; 2]; 2]> = BTreeMap::new();
    for line in include_str!("../../../test/fixtures/pathsum_ir_small_semantics.tsv").lines() {
        if line.is_empty() || line.starts_with('#') { continue; }
        let fields: Vec<&str> = line.split_whitespace().collect();
        assert_eq!(fields.len(), 5, "Malformed operator fixture");
        let row: usize = fields[1].parse().expect("Fixture output bit");
        let column: usize = fields[2].parse().expect("Fixture input bit");
        assert!(row < 2 && column < 2);
        let real: f64 = fields[3].parse().expect("Fixture real");
        let imag: f64 = fields[4].parse().expect("Fixture imaginary");
        let matrix = references.entry(fields[0].to_string())
            .or_insert([[C::new(f64::NAN, f64::NAN); 2]; 2]);
        assert!(matrix[row][column].re.is_nan(), "Duplicate fixture entry");
        matrix[row][column] = C::new(real, imag);
    }
    assert_eq!(references.len(), 4);
    for (name, oracle) in references {
        for row in oracle {
            for value in row { assert!(value.re.is_finite() && value.im.is_finite()); }
        }
        let gates: Vec<QuantumOp> = match name.as_str() {
            "h" => vec![QuantumOp::H(0)],
            "hh" => vec![QuantumOp::H(0), QuantumOp::H(0)],
            "hsh" => vec![QuantumOp::H(0), QuantumOp::S(0), QuantumOp::H(0)],
            "xzxz" => vec![QuantumOp::X(0), QuantumOp::Z(0),
                           QuantumOp::X(0), QuantumOp::Z(0)],
            _ => panic!("Unknown operator witness: {name}"),
        };
        for reduced in [false, true] {
            let mut ps = PathSum::new(2);
            ps.set_auto_reduce(reduced);
            for gate in &gates { gate.apply(&mut ps, false); }
            if reduced { ps.full_reduce(); }
            // Reuse the source-independent full path enumeration above, not
            // the reducer verdict or the IR textual formatting.
            let actual = matrix_from_unreduced(&ps);
            for output in 0..4 {
                for input in 0..4 {
                    let expected = if (output & 2) == (input & 2) {
                        oracle[output & 1][input & 1]
                    } else { C::new(0.0, 0.0) };
                    assert!(
                        (actual[output][input] - expected).norm() < 2e-11,
                        "{name} reduced={reduced}: output={output} input={input}, actual={} expected={expected}",
                        actual[output][input],
                    );
                }
            }
        }
    }
}
