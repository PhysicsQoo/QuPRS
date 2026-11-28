"""R4 experiment only: typed exact numeric scalar transport via existing IR.

No source-QASM rewrite, post-verdict relabel, hidden Python fallback or
production modification. Qiskit float is encoded as its exact rational
radian value; compare against historical Python cycle normalization.
"""
from pathlib import Path
import sys
stage,evidence=map(Path,sys.argv[1:])
def edit(path,fn):
    p=stage/path
    p.write_text(fn(p.read_text()))
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)
def python_api(s):
    a=s.index("def _validate_rust_qasm_global_phase_contract(")
    b=s.index("# =============================================================================",a)
    s=s[:a]+'''def _rust_qiskit_scalar_options(circuit1, circuit2):
    """Encode only unequal explicit finite Qiskit scalars, without QASM loss."""
    def phase_of(circuit):
        if not isinstance(circuit, QuantumCircuit):
            return 0.0
        try:
            phase = float(circuit.global_phase)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Rust backend requires a bound numeric QuantumCircuit.global_phase") from exc
        if not math.isfinite(phase):
            raise ValueError("Rust backend requires a finite QuantumCircuit.global_phase")
        return phase
    first, second = phase_of(circuit1), phase_of(circuit2)
    if first == second:
        return {}
    def encoded(value):
        n, d = value.as_integer_ratio()
        return f"{n}/{d}"
    return {key: encoded(value) for key, value in
            (("scalar1_radians", first), ("scalar2_radians", second)) if value != 0.0}


'''+s[b:]
    s=once(s,"        _validate_rust_qasm_global_phase_contract(circuit1, circuit2)","        scalar_options = _rust_qiskit_scalar_options(circuit1, circuit2)")
    s=once(s,'                        "timeout": remaining,\n                    },','                        "timeout": remaining,\n                        **scalar_options,\n                    },')
    a="                    gpmc_precision_digits=gpmc_precision_digits,\n                )"
    s=once(s,a,"                    gpmc_precision_digits=gpmc_precision_digits,\n                    **scalar_options,\n                )")
    a="                                        gpmc_precision_digits=gpmc_precision_digits,\n                                    )"
    s=once(s,a,"                                        gpmc_precision_digits=gpmc_precision_digits,\n                                        **scalar_options,\n                                    )")
    return s
def worker(s):
    a='            gpmc_precision_digits=options["gpmc_precision_digits"],'
    return once(s,a,a+'\n            **{k: options[k] for k in ("scalar1_radians", "scalar2_radians") if k in options},')
def ffi(s):
    s=once(s,"gpmc_precision_digits=30))]","gpmc_precision_digits=30, scalar1_radians=None, scalar2_radians=None))]")
    s=once(s,"    gpmc_precision_digits: u32,\n)","    gpmc_precision_digits: u32,\n    scalar1_radians: Option<&str>,\n    scalar2_radians: Option<&str>,\n)")
    a="    let (ops1, num_qubits1) = extract_circuit(circuit1)?;\n    let (ops2, num_qubits2) = extract_circuit(circuit2)?;"
    s=once(s,a,'''    let (mut ops1, num_qubits1) = extract_circuit(circuit1)?;
    let (mut ops2, num_qubits2) = extract_circuit(circuit2)?;
    // Numeric Qiskit phase is independent of gate count and QASM source.
    let gate_count1 = ops1.len();
    let gate_count2 = ops2.len();
    for (ops, value) in [(&mut ops1, scalar1_radians), (&mut ops2, scalar2_radians)] {
        if let Some(value) = value {
            let angle = pathsum::rational::Angle::from_qasm_str(value)
                .map_err(PyValueError::new_err)?;
            ops.push(QuantumOp::GlobalPhase(angle));
        }
    }''')
    for old,new in [('dict.set_item("gates1", ops1.len())?;','dict.set_item("gates1", gate_count1)?;'),('dict.set_item("gates2", ops2.len())?;','dict.set_item("gates2", gate_count2)?;'),('dict.set_item("gates1", result.gate_num1)?;','dict.set_item("gates1", gate_count1)?;'),('dict.set_item("gates2", result.gate_num2)?;','dict.set_item("gates2", gate_count2)?;')]:
        s=once(s,old,new)
    return s
for name,fn in [("src/QuPRS/interface/load_qiskit.py",python_api),("src/QuPRS/interface/rust_worker_standalone.py",worker),("rust/python_ffi/src/api.rs",ffi)]:
    edit(name,fn)
    (evidence/("r4-phase-"+Path(name).name)).write_bytes((stage/name).read_bytes())
print("R4_SCALAR_TRANSPORT_STAGED")
