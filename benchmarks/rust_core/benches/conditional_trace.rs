//! Same-SHA conditional trace reduction and preparation, solver-free.
// The existing experimental source is shared rather than reimplemented.
extern crate pathsum as quprs;
use std::sync::OnceLock;
use quprs::{PathSum,check_equivalence_with_options,VerificationMethod,VerificationOptions};
use quprs::qasm::parse_qasm_str;
#[allow(dead_code)]
#[path="../../../rust/quprs/tests/support/conditional_trace.rs"]
mod conditional_trace;
const CASES:&[(&str,&str,&str)]=&[
    ("qft_16",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/qft_nativegates_ibm_qiskit_opt0_16.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_16.qasm"))),
    ("qft_20",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/qft_nativegates_ibm_qiskit_opt0_20.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_20.qasm"))),
    ("qft_24",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/qft_nativegates_ibm_qiskit_opt0_24.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/qft_nativegates_ibm_qiskit_opt0_24.qasm"))),
    ("qpeexact_20",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/qpeexact_nativegates_ibm_qiskit_opt0_20.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/qpeexact_nativegates_ibm_qiskit_opt0_20.qasm"))),
    ("qwalk-noancilla_4",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/qwalk-noancilla_nativegates_ibm_qiskit_opt0_4.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/qwalk-noancilla_nativegates_ibm_qiskit_opt0_4.qasm"))),
    ("wstate_8",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/wstate_nativegates_ibm_qiskit_opt0_8.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/wstate_nativegates_ibm_qiskit_opt0_8.qasm"))),
    ("vqe_8",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/vqe_nativegates_ibm_qiskit_opt0_8.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/vqe_nativegates_ibm_qiskit_opt0_8.qasm"))),
    ("qnn_8",include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/qnn_nativegates_ibm_qiskit_opt0_8.qasm")),include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../benchmarks/MQTBench/h,ry,rz,cx/qnn_nativegates_ibm_qiskit_opt0_8.qasm"))),
];
static FIXTURES:OnceLock<Vec<(&'static str,PathSum)>>=OnceLock::new();
fn fixture(name:&str)->&'static PathSum{
    &FIXTURES.get_or_init(||CASES.iter().map(|&(id,source,target)|{
        let (a,n)=parse_qasm_str(source).expect("source parse");
        let (b,m)=parse_qasm_str(target).expect("target parse");assert_eq!(n,m);
        let options=VerificationOptions{method:VerificationMethod::ReductionRules,
            rr_tolerance:0.0,timeout_secs:20,..VerificationOptions::default()};
        let r=check_equivalence_with_options(n,&a,&b,&options).expect("native RR");
        assert!(!r.solver_invoked&&!r.rr_approximate);
        assert_ne!(r.equivalent(),"timeout");
        (id,r.final_pathsum().clone())
    }).collect()).iter().find(|(id,_)|*id==name).expect("fixed case").1
}
fn main(){
    // Untimed structural admission on exact source, using same
    // prepared residual for every arm. Never invokes external solver.
    for &(name,_,_) in CASES{
        let p=fixture(name);
        let (_,av,ac,am,ao,aa)=conditional_trace::benchmark_prepare(p,0);
        let (_,bv,bc,bm,bo,ba)=conditional_trace::benchmark_prepare(p,1);
        let (_,cv,cc,cm,co,ca)=conditional_trace::benchmark_prepare(p,2);
        assert!(!aa&&am==0&&ao==0);
        assert_eq!((bv,bc,bm,bo,ba),(cv,cc,cm,co,ca),"paired structural mismatch {name}");
        let expected=match name{
            "qft_16"=>(55,107,14,0,true),"qft_20"=>(68,132,16,0,true),
            "qft_24"=>(98,202,16,0,true),"qpeexact_20"=>(53,76,0,0,true),
            "qwalk-noancilla_4"=>(24,70,0,0,true),
            _=>(av,ac,0,0,false),
        };
        assert_eq!((cv,cc,cm,co,ca),expected,"CRR-2F structure drift {name}");
        eprintln!("CRR_CODSPEED_FIXTURE case={name} original_vars={av} original_clauses={ac} selected_vars={cv} selected_clauses={cc} multiplier_power={cm} omega={co} selected={ca}");
    }
    divan::main();
}

#[divan::bench(args = ["qft_16", "qft_20", "qft_24", "qpeexact_20", "qwalk-noancilla_4", "wstate_8", "vqe_8", "qnn_8"])]
fn crr_reduce_sequential(case:&str){divan::black_box(conditional_trace::benchmark_candidate(divan::black_box(fixture(case)),false));}

#[divan::bench(args = ["qft_16", "qft_20", "qft_24", "qpeexact_20", "qwalk-noancilla_4", "wstate_8", "vqe_8", "qnn_8"])]
fn crr_reduce_batched(case:&str){divan::black_box(conditional_trace::benchmark_candidate(divan::black_box(fixture(case)),true));}

#[divan::bench(args = ["qft_16", "qft_20", "qft_24", "qpeexact_20", "qwalk-noancilla_4", "wstate_8", "vqe_8", "qnn_8"])]
fn crr_prepare_baseline(case:&str){divan::black_box(conditional_trace::benchmark_prepare(divan::black_box(fixture(case)),0));}

#[divan::bench(args = ["qft_16", "qft_20", "qft_24", "qpeexact_20", "qwalk-noancilla_4", "wstate_8", "vqe_8", "qnn_8"])]
fn crr_prepare_sequential(case:&str){divan::black_box(conditional_trace::benchmark_prepare(divan::black_box(fixture(case)),1));}

#[divan::bench(args = ["qft_16", "qft_20", "qft_24", "qpeexact_20", "qwalk-noancilla_4", "wstate_8", "vqe_8", "qnn_8"])]
fn crr_prepare_batched(case:&str){divan::black_box(conditional_trace::benchmark_prepare(divan::black_box(fixture(case)),2));}
