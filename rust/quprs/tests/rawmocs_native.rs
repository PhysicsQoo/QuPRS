//! Native selection must not silently substitute another counter.
use quprs::{check_equivalence_with_options, EquivalenceStatus, VerificationMethod, VerificationOptions};
use quprs::ir::QuantumOp;

#[test]
fn rawmocs_native_explicit_selection() {
    let opt=VerificationOptions{method:VerificationMethod::WmcOnly,tool_name:"rawmocs_rust_native".into(),timeout_secs:10,..Default::default()};
    let result=check_equivalence_with_options(1,&[],&[QuantumOp::H(0)],&opt);
    #[cfg(all(feature="rawmocs-native",not(target_arch="wasm32")))]
    {
        let r=result.unwrap();
        assert_eq!(r.status,EquivalenceStatus::NotEquivalent);
        assert!(r.solver_invoked);
    }
    #[cfg(not(all(feature="rawmocs-native",not(target_arch="wasm32"))))]
    assert!(result.unwrap_err().to_string().contains("RaWMoCS native solver unavailable"));
}
