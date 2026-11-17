//! Independent exact matrix reconstruction of unreduced one-qubit PathSum.
 //!
 //! The tiny oracle evaluates rational phases as exact eighth roots of unity
 //! in Q(i,sqrt(2)), then compares against literal versioned QASM matrices.
 //! It does not call reduction, an external solver, or an equivalence verdict.

use num_rational::Ratio;
use quprs::{qasm::parse_qasm_str, ir::QuantumOp, rational::Angle, PathSum};

type R = Ratio<i128>;

fn rat(n: i128, d: i128) -> R { R::new(n, d) }

/// (a+b*sqrt(2))+i(c+d*sqrt(2)), with rational a,b,c,d.
#[derive(Clone, Debug, PartialEq, Eq)]
struct Q8 {
    a: R, b: R, c: R, d: R,
}
impl Q8 {
    fn new(a: R, b: R, c: R, d: R) -> Self { Self { a, b, c, d } }
    fn zero() -> Self { Self::new(rat(0,1),rat(0,1),rat(0,1),rat(0,1)) }
    fn one() -> Self { Self::new(rat(1,1),rat(0,1),rat(0,1),rat(0,1)) }
    fn real(n: i128) -> Self { Self::new(rat(n,1),rat(0,1),rat(0,1),rat(0,1)) }
    fn imag(n: i128) -> Self { Self::new(rat(0,1),rat(0,1),rat(n,1),rat(0,1)) }
    fn sum_with(&mut self, x: Self) {
        self.a += x.a; self.b += x.b; self.c += x.c; self.d += x.d;
    }
    fn neg(self) -> Self { Self::new(-self.a,-self.b,-self.c,-self.d) }
    fn scaled(self, n: i128, d: i128) -> Self {
        let k=rat(n,d);
        Self::new(self.a*k.clone(),self.b*k.clone(),self.c*k.clone(),self.d*k)
    }
    fn times_sqrt2(self) -> Self {
        Self::new(self.b*rat(2,1),self.a,self.d*rat(2,1),self.c)
    }
    fn multiplied_by(&self, rhs: &Self) -> Self {
        // Exact cyclotomic arithmetic with sqrt(2)^2 = 2 and i^2 = -1.
        let a=&self.a; let b=&self.b; let c=&self.c; let d=&self.d;
        let e=&rhs.a; let f=&rhs.b; let g=&rhs.c; let h=&rhs.d;
        Self::new(
            a*e + rat(2,1)*b*f - c*g - rat(2,1)*d*h,
            a*f + b*e - c*h - d*g,
            a*g + rat(2,1)*b*h + c*e + rat(2,1)*d*f,
            a*h + b*g + c*f + d*e,
        )
    }
}
fn root_of_unity(phase_cycles: R) -> Q8 {
    let eighths = phase_cycles*rat(8,1);
    assert_eq!(*eighths.numer()%*eighths.denom(),0,
        "the fixture must have an exact eighth-root-of-unity phase");
    let k = (eighths.to_integer()).rem_euclid(8);
    match k {
        0 => Q8::one(),
        1 => Q8::new(rat(0,1),rat(1,2),rat(0,1),rat(1,2)),
        2 => Q8::imag(1),
        3 => Q8::new(rat(0,1),rat(-1,2),rat(0,1),rat(1,2)),
        4 => Q8::real(-1),
        5 => Q8::new(rat(0,1),rat(-1,2),rat(0,1),rat(-1,2)),
        6 => Q8::imag(-1),
        7 => Q8::new(rat(0,1),rat(1,2),rat(0,1),rat(-1,2)),
        _ => unreachable!(),
    }
}
fn normalization(value: Q8, paths: usize) -> Q8 {
    // 2^(-paths/2): an exact element of Q(sqrt(2)).
    assert!(paths<12,"bounded standalone matrix enumeration");
    if paths%2==0 {
        value.scaled(1,1i128<<(paths/2))
    } else {
        value.times_sqrt2().scaled(1,1i128<<((paths+1)/2))
    }
}
fn source_matrix(source: &str) -> [[Q8;2];2] {
    let (ops,n) = parse_qasm_str(source).expect("source admission prerequisite");
    assert_eq!(n,1); assert_eq!(ops.len(),1);
    let mut ps=PathSum::new(1);
    ps.set_auto_reduce(false);
    ops[0].apply(&mut ps,false);
    matrix_from_pathsum(&ps)
}
fn matrix_from_pathsum(ps: &PathSum) -> [[Q8;2];2] {
    let mut fresh: Vec<u32> = ps.v.path_vars.iter().copied().filter(|v| *v>=1).collect();
    fresh.sort_unstable();
    assert!(fresh.len()<12);
    let mut result: [[Q8;2];2] = std::array::from_fn(|_|
        std::array::from_fn(|_|Q8::zero()));
    let truth = |monomial: &[u32], assignment: u64| ->
        bool { monomial.iter().all(|&x| x<62 && (assignment & (1u64<<x))!=0) };
    for input in 0..2u64 {
        for mask in 0..(1u64<<fresh.len()) {
            let mut assignment=input;
            for (j,&var) in fresh.iter().enumerate() {
                assert!(var<62);
                if mask & (1u64<<j)!=0 { assignment|=1u64<<var; }
            }
            let output=ps.f.functions[0].iter()
                .fold(false,|parity,monomial|parity^truth(monomial,assignment));
            let mut phase=rat(0,1);
            for (monomial,coeff) in &ps.p.terms {
                assert!(coeff.radians.is_none(), "only rational-pi sources");
                assert!(coeff.symbols.is_empty(), "no free source parameters");
                if truth(monomial,assignment) {
                    phase += rat(coeff.constant.numer as i128,coeff.constant.denom as i128);
                }
            }
            let path=normalization(root_of_unity(phase),fresh.len());
            result[usize::from(output)][input as usize].sum_with(path);
        }
    }
    result
}

fn identity() -> [[Q8;2];2] {
    [[Q8::one(),Q8::zero()],[Q8::zero(),Q8::one()]]
}
fn negative_identity() -> [[Q8;2];2] {
    [[Q8::real(-1),Q8::zero()],[Q8::zero(),Q8::real(-1)]]
}
fn z() -> [[Q8;2];2] {
    [[Q8::one(),Q8::zero()],[Q8::zero(),Q8::real(-1)]]
}
fn negative_i_z() -> [[Q8;2];2] {
    [[Q8::imag(-1),Q8::zero()],[Q8::zero(),Q8::imag(1)]]
}
fn qasm3_builtin_u_half_pi() -> [[Q8;2];2] {
    // OpenQASM 3 U(pi/2,0,0) = ((1+i)/2) * [[1,-1],[1,1]].
    let c=Q8::new(rat(1,2),rat(0,1),rat(1,2),rat(0,1));
    [[c.clone(),c.clone().neg()],[c.clone(),c]]
}
fn qasm3_u3_half_pi() -> [[Q8;2];2] {
    // u3(pi/2,0,0) = (sqrt(2)/2) * [[1,-1],[1,1]].
    let c=Q8::new(rat(0,1),rat(1,2),rat(0,1),rat(0,1));
    [[c.clone(),c.clone().neg()],[c.clone(),c]]
}
struct MatrixCase {
    name: &'static str,
    source_params: &'static str,
    theta_over_pi: R,
    phi_over_pi: R,
    lambda_over_pi: R,
    expected_builtin: [[Q8;2];2],
    expected_compat: [[Q8;2];2],
}
fn cases() -> Vec<MatrixCase> {
    vec![
        MatrixCase { name:"theta_zero",source_params:"0,0,0",
            theta_over_pi:rat(0,1),phi_over_pi:rat(0,1),lambda_over_pi:rat(0,1),
            expected_builtin:identity(),expected_compat:identity() },
        MatrixCase { name:"theta_twopi",source_params:"2*pi,0,0",
            theta_over_pi:rat(2,1),phi_over_pi:rat(0,1),lambda_over_pi:rat(0,1),
            expected_builtin:identity(),expected_compat:negative_identity() },
        MatrixCase { name:"phi_pi",source_params:"0,pi,0",
            theta_over_pi:rat(0,1),phi_over_pi:rat(1,1),lambda_over_pi:rat(0,1),
            expected_builtin:z(),expected_compat:negative_i_z() },
        MatrixCase { name:"theta_halfpi",source_params:"pi/2,0,0",
            theta_over_pi:rat(1,2),phi_over_pi:rat(0,1),lambda_over_pi:rat(0,1),
            expected_builtin:qasm3_builtin_u_half_pi(),
            expected_compat:qasm3_u3_half_pi() },
    ]
}
fn source(gate: &str, params: &str) -> String {
    format!("OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\n{gate}({params}) q[0];\n")
}
fn analyze_print() -> Vec<String> {
    let mut differences=Vec::new();
    for case in cases() {
        let builtin=source_matrix(&source("U",case.source_params));
        let compat=source_matrix(&source("u3",case.source_params));
        let builtin_matches = builtin == case.expected_builtin;
        let compat_matches = compat == case.expected_compat;
        println!("EXACT_MATRIX case={} gate=U conforms={} native={builtin:?} expected={:?}",
            case.name,builtin_matches,case.expected_builtin);
        println!("EXACT_MATRIX case={} gate=u3 conforms={} native={compat:?} expected={:?}",
            case.name,compat_matches,case.expected_compat);
        if !builtin_matches {differences.push(format!("{}:U",case.name))}
        if !compat_matches {differences.push(format!("{}:u3",case.name))}
    }
    println!("EXACT_MATRIX_NONCONFORMANCES={}", differences.join(","));
    differences
}
#[test]
fn observed_exact_qasm_unitary_matrix_oracle() {
    let findings=analyze_print();
    println!("EXACT_MATRIX_OBSERVATIONS={}",findings.len());
}
#[test]
fn strict_contract_exact_qasm_unitary_matrices() {
    let findings=analyze_print();
    assert!(findings.is_empty(),
        "strict source unitary matrix mismatches: {}",findings.join(", "));
}


#[test]
fn observed_exact_versioned_phase_bridge_oracle() {
    // This is an independently checked scalar translation for a proposed
    // versioned source adapter, not a mutation of the production gate kernels.
    //
    // The existing raw implementation has Qiskit-U-like phase Q.
    // Strict OpenQASM 3: U = exp(i*theta/2) Q;
    // stdgates compatibility u3 = exp(-i*(phi+lambda)/2) Q.
    let mut count=0;
    for case in cases() {
        let native_builtin=source_matrix(&source("U",case.source_params));
        let native_compat=source_matrix(&source("u3",case.source_params));
        let u_phase=root_of_unity(case.theta_over_pi.clone()/rat(4,1));
        let compat_phase=root_of_unity(
            -(case.phi_over_pi.clone()+case.lambda_over_pi.clone())/rat(4,1)
        );
        let translated_builtin=std::array::from_fn(|r|std::array::from_fn(|c|
            native_builtin[r][c].multiplied_by(&u_phase)
        ));
        let translated_compat=std::array::from_fn(|r|std::array::from_fn(|c|
            native_compat[r][c].multiplied_by(&compat_phase)
        ));
        assert_eq!(translated_builtin,case.expected_builtin,
            "source builtin U phase translation failed: {}",case.name);
        assert_eq!(translated_compat,case.expected_compat,
            "source compatibility u3 phase translation failed: {}",case.name);
        println!("VERSIONED_PHASE_BRIDGE case={} exact=true",case.name);
        count+=1;
    }
    println!("VERSIONED_PHASE_BRIDGE_EXACT_CASES={count}");
}


// A research-only, strictly bounded source gate admission layer. This is
// NOT an implementation of the complete QASM grammar and is not a
// production-facing source parser. It deliberately refuses general source.
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
enum SourceKind { Qasm2BuiltinU, Qasm2StdlibU2, Qasm2StdlibU3, Qasm3BuiltinU, Qasm3StdlibU2, Qasm3StdlibU3 }

struct SourcePhaseRecord {
    source_kind: SourceKind,
    operation: QuantumOp,
    phase_correction: Angle,
}
fn admit_source_phase_record(raw: &str) -> Result<SourcePhaseRecord,String> {
    let lines:Vec<&str>=raw.lines().map(str::trim)
        .filter(|line|!line.is_empty()).collect();
    if lines.len()<3 {return Err("incomplete narrow source".into());}
    let version=match lines[0] {
        "OPENQASM 2.0;" => 2,
        "OPENQASM 3.0;" => 3,
        _=>return Err("unsupported source version".into()),
    };
    let mut cursor=1;
    let include=if lines.get(cursor)==Some(&"include \"qelib1.inc\";")&&version==2 {
        cursor+=1;true
    } else if lines.get(cursor)==Some(&"include \"stdgates.inc\";")&&version==3 {
        cursor+=1;true
    } else {false};
    let expected_decl=if version==2 {"qreg q[1];"}else{"qubit[1] q;"};
    if lines.get(cursor).copied()!=Some(expected_decl) {
        return Err("only a single explicit one-qubit register is admitted".into());
    }
    cursor+=1;
    if lines.len()!=cursor+1 {return Err("unexpected statement in bounded source".into());}
    let gate=lines[cursor];
    let (literal_name,remaining)=gate.split_once('(')
        .ok_or("missing gate arguments")?;
    let body=remaining.strip_suffix(") q[0];")
        .ok_or("only indexed source gate q[0] is admitted")?;
    let args:Vec<&str>=body.split(',').map(str::trim).collect();
    // A deliberately finite exact source-angle grammar, not a generic QASM parser.
    if args.iter().any(|a| !matches!(*a,"0"|"pi"|"2*pi"|"pi/2"|"pi/4"|"-pi/2")) {
        return Err("unsupported source angle literal".into());
    }
    let kind=match (version,literal_name,include,args.len()) {
        (2,"U",_,3)=>SourceKind::Qasm2BuiltinU,
        (2,"u3",true,3)=>SourceKind::Qasm2StdlibU3,
        (2,"u2",true,2)=>SourceKind::Qasm2StdlibU2,
        (3,"U",_,3)=>SourceKind::Qasm3BuiltinU,
        (3,"u3",true,3)=>SourceKind::Qasm3StdlibU3,
        (3,"u2",true,2)=>SourceKind::Qasm3StdlibU2,
        _=>return Err("unbound or unsupported source gate".into()),
    };
    let (ops,n)=parse_qasm_str(raw).map_err(|e|format!("native parse: {e}"))?;
    if n!=1||ops.len()!=1{return Err("unexpected native operation structure".into())}
    let operation=ops.into_iter().next().unwrap();
    let phase_correction=match (&kind,&operation) {
        (SourceKind::Qasm2BuiltinU,QuantumOp::U(0,_,phi,lambda))
        | (SourceKind::Qasm2StdlibU3,QuantumOp::U3(0,_,phi,lambda))
        | (SourceKind::Qasm3StdlibU3,QuantumOp::U3(0,_,phi,lambda))
            => (Angle::ZERO-phi.clone()-lambda.clone())/2,
        (SourceKind::Qasm3BuiltinU,QuantumOp::U(0,theta,_,_))
            => theta.clone()/2,
        (SourceKind::Qasm2StdlibU2,QuantumOp::U2(0,phi,lambda))
        | (SourceKind::Qasm3StdlibU2,QuantumOp::U2(0,phi,lambda))
            => (Angle::ZERO-phi.clone()-lambda.clone())/2,
        _=>return Err("source gate-to-native IR mismatch".into()),
    };
    Ok(SourcePhaseRecord{source_kind:kind,operation,phase_correction})
}
fn source_case(version:u8, gate:&str, args:&str, include:bool)->String {
    let header=if version==2 {"OPENQASM 2.0;"} else {"OPENQASM 3.0;"};
    let inc=if include {
        if version==2 {"include \"qelib1.inc\";\n"}
        else {"include \"stdgates.inc\";\n"}
    }else{""};
    let decl=if version==2 {"qreg q[1];"} else {"qubit[1] q;"};
    format!("{header}\n{inc}{decl}\n{gate}({args}) q[0];\n")
}
fn versioned_source_matrix(record:&SourcePhaseRecord,is_bra:bool)->[[Q8;2];2]{
    let mut ps=PathSum::new(1);
    ps.set_auto_reduce(false);
    record.operation.apply(&mut ps,is_bra);
    // Existing public GlobalPhase is the test-only carrier of the exact
    // source-kind-specific scalar. Bra automatically conjugates that scalar.
    QuantumOp::GlobalPhase(record.phase_correction.clone()).apply(&mut ps,is_bra);
    matrix_from_pathsum(&ps)
}
fn dag_q8(matrix:&[[Q8;2];2])->[[Q8;2];2]{
    std::array::from_fn(|r|std::array::from_fn(|c|{
        let z=&matrix[c][r];
        Q8::new(z.a.clone(),z.b.clone(),-z.c.clone(),-z.d.clone())
    }))
}
fn phase_by_reference(phase_pi: R)->Q8 {
    root_of_unity(phase_pi/rat(2,1))
}
fn multiply_matrix_scalar(matrix:&[[Q8;2];2],scalar:&Q8)->[[Q8;2];2] {
    std::array::from_fn(|r|std::array::from_fn(|c|
        matrix[r][c].multiplied_by(scalar)
    ))
}
#[test]
fn observed_versioned_source_phase_records_and_bra_conjugation() {
    struct T {
        version:u8,gate:&'static str,args:&'static str,include:bool,
        kind:SourceKind,reference:[[Q8;2];2],
    }
    let examples=vec![
        T{version:2,gate:"U",args:"0,pi,0",include:false,
          kind:SourceKind::Qasm2BuiltinU,reference:negative_i_z()},
        T{version:2,gate:"U",args:"2*pi,0,0",include:false,
          kind:SourceKind::Qasm2BuiltinU,reference:negative_identity()},
        T{version:2,gate:"u3",args:"0,pi,0",include:true,
          kind:SourceKind::Qasm2StdlibU3,reference:negative_i_z()},
        T{version:2,gate:"u2",args:"0,0",include:true,
          kind:SourceKind::Qasm2StdlibU2,reference:qasm3_u3_half_pi()},
        T{version:3,gate:"U",args:"pi/2,0,0",include:false,
          kind:SourceKind::Qasm3BuiltinU,reference:qasm3_builtin_u_half_pi()},
        T{version:3,gate:"U",args:"2*pi,0,0",include:false,
          kind:SourceKind::Qasm3BuiltinU,reference:identity()},
        T{version:3,gate:"u3",args:"0,pi,0",include:true,
          kind:SourceKind::Qasm3StdlibU3,reference:negative_i_z()},
        T{version:3,gate:"u3",args:"pi/2,0,0",include:true,
          kind:SourceKind::Qasm3StdlibU3,reference:qasm3_u3_half_pi()},
        T{version:3,gate:"u2",args:"0,0",include:true,
          kind:SourceKind::Qasm3StdlibU2,reference:qasm3_u3_half_pi()},
        T{version:3,gate:"u2",args:"pi,0",include:true,
          kind:SourceKind::Qasm3StdlibU2,
          reference:{
            let k=Q8::new(rat(0,1),rat(0,1),rat(0,1),rat(1,2));
            [[k.clone().neg(),k.clone()],[k.clone(),k]]
          }},
    ];
    let mut checks=0;
    for item in examples {
        let src=source_case(item.version,item.gate,item.args,item.include);
        let record=admit_source_phase_record(&src).expect("independent source gate must admit");
        assert_eq!(record.source_kind,item.kind);
        let ket=versioned_source_matrix(&record,false);
        assert_eq!(ket,item.reference,"source strict ket mismatch: {src}");
        let bra=versioned_source_matrix(&record,true);
        assert_eq!(bra,dag_q8(&item.reference),
            "source strict bra mismatch: {src}");
        println!("VERSIONED_SOURCE_MATRIX kind={:?} args={} ket=true bra=true",
            record.source_kind,item.args);
        checks+=2;
    }
    println!("VERSIONED_SOURCE_KET_BRA_EXACT_COMPARISONS={checks}");
}
#[test]
fn observed_narrow_source_rejects_unbound_gates_and_versions() {
    let cases=[
        source_case(3,"u3","pi/2,0,0",false),
        source_case(2,"u3","pi/2,0,0",false),
        source_case(2,"u2","0,0",false),
        source_case(3,"u2","0,0",false),
        source_case(3,"u","0,0,0",false),
        source_case(3,"U3","pi/2,0,0",true),
        source_case(2,"u","0,0,0",true),
        source_case(3,"H","0,0,0",true),
        "OPENQASM 3.1;\nqubit[1] q;\nU(0,0,0) q[0];".into(),
        "OPENQASM 3.0;\nqubit[1] q;\nU(0,0,0) q[0];\nU(0,0,0) q[0];".into(),
    ];
    for (idx,src) in cases.iter().enumerate() {
        assert!(admit_source_phase_record(src).is_err(),
            "invalid or unsupported narrow source admitted at {idx}");
        println!("NARROW_VERSIONED_SOURCE_REJECT index={idx} true");
    }
    println!("NARROW_VERSIONED_SOURCE_REJECTIONS={}",cases.len());
}


// The following composition checks stay inside a deliberately bounded,
// version-pinned source grammar. They do not claim general QASM3 support.
type M2 = [[Q8;2];2];

fn product_q8(left:&M2,right:&M2)->M2 {
    std::array::from_fn(|r|std::array::from_fn(|c|{
        let mut total=Q8::zero();
        for k in 0..2 { total.sum_with(left[r][k].multiplied_by(&right[k][c])); }
        total
    }))
}
fn conjugate_q8(value:&Q8)->Q8 {
    Q8::new(value.a.clone(),value.b.clone(),-value.c.clone(),-value.d.clone())
}
fn bounded_sequence_source(version:u8,gates:&[&str])->String {
    let header=if version==2 {"OPENQASM 2.0;"} else {"OPENQASM 3.0;"};
    let inc=if version==2 {"include \"qelib1.inc\";"} else {"include \"stdgates.inc\";"};
    let decl=if version==2 {"qreg q[1];"} else {"qubit[1] q;"};
    format!("{header}\n{inc}\n{decl}\n{}\n",gates.join("\n"))
}
fn admit_bounded_sequence(raw:&str)->Result<Vec<SourcePhaseRecord>,String> {
    let lines:Vec<&str>=raw.lines().map(str::trim)
        .filter(|line|!line.is_empty()).collect();
    if lines.len()<5 {return Err("short bounded source sequence".into());}
    let version=match lines[0] {
        "OPENQASM 2.0;"=>2,
        "OPENQASM 3.0;"=>3,
        _=>return Err("unsupported source version".into())
    };
    let inc=if version==2 {"include \"qelib1.inc\";"}
        else {"include \"stdgates.inc\";"};
    let decl=if version==2 {"qreg q[1];"}
        else {"qubit[1] q;"};
    if lines[1]!=inc||lines[2]!=decl {
        return Err("unbound or unexpected source declaration".into())
    }
    let gate_lines=&lines[3..];
    if !(2..=3).contains(&gate_lines.len()) {
        return Err("only 2 or 3 explicit source gates are admitted".into());
    }
    let mut records=Vec::new();
    for &literal_gate in gate_lines {
        // Reuse one-instruction checked gate provenance, while requiring
        // a complete, identical sequence at the actual Rust parse boundary.
        let single=format!("{}\n{}\n{}\n{}\n",
            lines[0],lines[1],lines[2],literal_gate);
        records.push(admit_source_phase_record(&single)?);
    }
    let (ops,n)=parse_qasm_str(raw).map_err(|e|format!("native parse: {e}"))?;
    if n!=1||ops.len()!=records.len()||
       !ops.iter().zip(records.iter()).all(|(op,rec)|op==&rec.operation) {
        return Err("ordered native source-to-IR replay is incomplete".into())
    }
    Ok(records)
}
fn composed_native_matrix(records:&[SourcePhaseRecord],bra:bool)->M2 {
    let mut ps=PathSum::new(1);
    ps.set_auto_reduce(false);
    if bra {
        // PathSum's Bra-side gate application composes on the right.
        // The source order therefore gives G_1^dagger ... G_m^dagger,
        // the adjoint of the Ket-side G_m ... G_1 sequence.
        // Reversing here would produce G_m^dagger ... G_1^dagger.
        for rec in records.iter() {
            rec.operation.apply(&mut ps,true);
            QuantumOp::GlobalPhase(rec.phase_correction.clone())
                .apply(&mut ps,true);
        }
    } else {
        for rec in records {
            rec.operation.apply(&mut ps,false);
            QuantumOp::GlobalPhase(rec.phase_correction.clone())
                .apply(&mut ps,false);
        }
    }
    matrix_from_pathsum(&ps)
}
fn seq_expected(matrices:&[M2])->M2 {
    let mut acc=identity();
    for matrix in matrices {
        acc=product_q8(matrix,&acc);
    }
    acc
}
#[test]
fn observed_exact_multigate_source_composition_and_bra() {
    let uhalf=qasm3_builtin_u_half_pi();
    let minusiz=negative_i_z();
    let cases: Vec<(&str,u8,Vec<&str>,Vec<M2>)> = vec![
        ("h_then_z_source",3,
            vec!["U(pi/2,0,0) q[0];","u3(0,pi,0) q[0];"],
            vec![uhalf.clone(),minusiz.clone()]),
        ("z_then_h_source",3,
            vec!["u3(0,pi,0) q[0];","U(pi/2,0,0) q[0];"],
            vec![minusiz.clone(),uhalf.clone()]),
        ("strict_minus_identity",3,
            vec!["U(2*pi,0,0) q[0];","u3(2*pi,0,0) q[0];"],
            vec![identity(),negative_identity()]),
        ("strict_plus_identity",3,
            vec!["u3(2*pi,0,0) q[0];","u3(2*pi,0,0) q[0];"],
            vec![negative_identity(),negative_identity()]),
        ("three_gates_keep_phase",3,
            vec!["u2(0,0) q[0];","U(pi/2,0,0) q[0];","u3(2*pi,0,0) q[0];"],
            vec![qasm3_u3_half_pi(),uhalf.clone(),negative_identity()]),
        ("qasm2_mixed_library",2,
            vec!["U(0,pi,0) q[0];","u2(0,0) q[0];","u3(2*pi,0,0) q[0];"],
            vec![minusiz,qasm3_u3_half_pi(),negative_identity()]),
    ];
    let mut exact_checks=0;
    let mut first:Option<M2>=None;
    let mut second:Option<M2>=None;
    for (label,version,gate_lines,reference_matrices) in cases {
        let raw=bounded_sequence_source(version,&gate_lines);
        let records=admit_bounded_sequence(&raw)
            .unwrap_or_else(|e|panic!("sequence admission {label}: {e}"));
        let expectation=seq_expected(&reference_matrices);
        let actual=composed_native_matrix(&records,false);
        assert_eq!(actual,expectation,"source-ordered ket mismatch: {label}");
        let bra=composed_native_matrix(&records,true);
        assert_eq!(bra,dag_q8(&expectation),"source-reversed bra mismatch: {label}");
        if label=="h_then_z_source" {first=Some(actual.clone())}
        if label=="z_then_h_source" {second=Some(actual.clone())}
        println!("EXACT_SOURCE_COMPOSITION case={label} ket=true bra=true");
        exact_checks+=2;
    }
    // Noncommutative source order must not be silently canonicalized.
    assert_ne!(first.unwrap(),second.unwrap());
    println!("EXACT_SOURCE_NONCOMMUTING_ORDER_DIFFERENT=true");
    println!("EXACT_SOURCE_COMPOSITION_KET_BRA_CHECKS={exact_checks}");
}
#[test]
fn observed_exact_strict_source_miter_and_controlled_phase_witness() {
    // These two sources have the same quantum channel but different strict
    // source unitaries. Their uncorrected QuPRS PathSums were identical
    // before the source-phase ledger, giving a false strict-equivalence risk.
    let source_u=source_case(3,"U","2*pi,0,0",false);
    let source_u3=source_case(3,"u3","2*pi,0,0",true);
    let u=admit_source_phase_record(&source_u).unwrap();
    let u3=admit_source_phase_record(&source_u3).unwrap();
    let correct_u=versioned_source_matrix(&u,false);
    let correct_u3=versioned_source_matrix(&u3,false);
    assert_eq!(correct_u,identity());
    assert_eq!(correct_u3,negative_identity());
    let strict_miter=product_q8(&dag_q8(&correct_u),&correct_u3);
    assert_eq!(strict_miter,negative_identity());
    assert_ne!(strict_miter,identity());

    let mut raw_u=PathSum::new(1);raw_u.set_auto_reduce(false);
    u.operation.apply(&mut raw_u,false);
    let mut raw_u3=PathSum::new(1);raw_u3.set_auto_reduce(false);
    u3.operation.apply(&mut raw_u3,false);
    let uncorrected_miter=product_q8(
        &dag_q8(&matrix_from_pathsum(&raw_u)),&matrix_from_pathsum(&raw_u3)
    );
    assert_eq!(uncorrected_miter,identity());
    println!("SOURCE_MITER_UNCORRECTED_STRICT_EQ=true CORRECTED_STRICT_EQ=false");
    println!("SOURCE_MITER_CORRECTED_PROJECTIVE_EQ=true");

    // Only a mathematical controlled-context witness is tested here:
    // ctrl@ syntax is not claimed to be supported by the native QASM parser.
    // Start |+>_control |0>_target and postselect |- >_control |0>_target.
    // For a strictly diagonal miter, risk = |(1 - miter[0][0])/2|^2.
    assert_eq!(strict_miter[1][0],Q8::zero());
    let negative_amp=Q8::one();
    let mut b=negative_amp;
    b.sum_with(strict_miter[0][0].clone().neg());
    let amp=b.scaled(1,2);
    let risk=amp.multiplied_by(&conjugate_q8(&amp));
    assert_eq!(risk,Q8::one());
    // With a phase-erased identity miter the same risk is exactly zero.
    let mut b_identity=Q8::one();
    b_identity.sum_with(uncorrected_miter[0][0].clone().neg());
    let identity_amp=b_identity.scaled(1,2);
    assert_eq!(identity_amp.multiplied_by(&conjugate_q8(&identity_amp)),
        Q8::zero());
    println!("SOURCE_MITER_CONTROLLED_WITNESS corrected_bad_risk=1 phase_erased_bad_risk=0");
}


// Two-qubit experiment: real native PathSum matrix extraction. This checks
// a source-level decomposition of controlled global phase using standard
// one-qubit phase on the control, not native ctrl @ modifier support.
type M4 = [[Q8;4];4];
fn matrix4_from_native_source(source:&str)->M4 {
    let (ops,n)=parse_qasm_str(source).expect("native two-qubit source parse");
    assert_eq!(n,2);
    let mut ps=PathSum::new(2);
    ps.set_auto_reduce(false);
    for operation in &ops {operation.apply(&mut ps,false);}
    let mut fresh:Vec<u32>=ps.v.path_vars.iter().copied()
        .filter(|v|*v>=2).collect();
    fresh.sort_unstable();
    assert!(fresh.len()<12);
    let truth=|monomial:&[u32],assignment:u64|->bool{
        monomial.iter().all(|&v| v<62&&(assignment&(1u64<<v))!=0)
    };
    let mut matrix:M4=std::array::from_fn(|_|
        std::array::from_fn(|_|Q8::zero()));
    for input in 0..4usize {
        for path_mask in 0..(1usize<<fresh.len()) {
            let mut assignment=input as u64;
            for (j,&var) in fresh.iter().enumerate() {
                assert!(var<62);
                if path_mask & (1usize<<j)!=0 {
                    assignment|=1u64<<var;
                }
            }
            let mut output=0;
            for (q,terms) in ps.f.functions.iter().enumerate() {
                let parity=terms.iter().fold(false,|acc,monomial|
                    acc^truth(monomial,assignment));
                if parity {output|=1usize<<q;}
            }
            assert!(output<4);
            let mut phase=rat(0,1);
            for (monomial,coefficient) in &ps.p.terms {
                assert!(coefficient.radians.is_none());
                assert!(coefficient.symbols.is_empty());
                if truth(monomial,assignment) {
                    phase+=rat(coefficient.constant.numer as i128,
                        coefficient.constant.denom as i128);
                }
            }
            matrix[output][input].sum_with(normalization(
                root_of_unity(phase),fresh.len()));
        }
    }
    matrix
}
fn matrix4_diagonal(values:[Q8;4])->M4 {
    std::array::from_fn(|r|std::array::from_fn(|c|
        if r==c {values[r].clone()} else {Q8::zero()}))
}
fn matrix4_identity()->M4 {
    matrix4_diagonal([Q8::one(),Q8::one(),Q8::one(),Q8::one()])
}
fn matrix4_controlled_target(target:&M2)->M4 {
    // Source basis |q1 q0>. q1 is control, q0 the target.
    std::array::from_fn(|r|std::array::from_fn(|c|{
        if r<2&&c<2 {
            if r==c {Q8::one()}else{Q8::zero()}
        }else if r>=2&&c>=2 {
            target[r-2][c-2].clone()
        }else {Q8::zero()}
    }))
}
#[test]
fn observed_native_two_qubit_controlled_global_phase_witness() {
    let ctrl_minus_identity=matrix4_controlled_target(&negative_identity());
    let source="OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\np(pi) q[1];\n";
    let native=matrix4_from_native_source(source);
    assert_eq!(native,ctrl_minus_identity,
        "physical controlled -I must be equivalent to Z on the control");
    assert_ne!(native,matrix4_identity());
    println!("NATIVE_TWOQ_CONTROLLED_MINUS_I_MATRIX_EXACT=true");

    let plus="OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[1];\np(pi) q[1];\nh q[1];\n";
    let minus="OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[1];\nh q[1];\n";
    let phase_kept=matrix4_from_native_source(plus);
    let phase_erased=matrix4_from_native_source(minus);
    // H Z H = X on the control; for input |00>, bad effect |10><10|.
    assert_eq!(phase_kept[2][0],Q8::one());
    assert_eq!(phase_erased[2][0],Q8::zero());
    let risk_kept=phase_kept[2][0].multiplied_by(
        &conjugate_q8(&phase_kept[2][0]));
    let risk_erased=phase_erased[2][0].multiplied_by(
        &conjugate_q8(&phase_erased[2][0]));
    assert_eq!(risk_kept,Q8::one());
    assert_eq!(risk_erased,Q8::zero());
    println!("NATIVE_TWOQ_PHASE_CONTEXT_BAD_RISK retained=1 erased=0");
}
#[test]
fn observed_native_modifier_admission_separate_from_decomposition() {
    let source="OPENQASM 3.0;\nqubit[2] q;\nctrl @ U(2*pi,0,0) q[1], q[0];";
    let native= parse_qasm_str(source);
    assert!(native.is_err(),"modifier requires a separate source validator");
    println!("NATIVE_QASM_CTRL_MODIFIER_CURRENTLY_UNSUPPORTED=true");
}
#[test]
fn observed_typed_phase_equivalence_not_control_congruence() {
    let a=identity();
    let b=negative_identity();
    // A and B have equal channels but not equal strict matrices.
    assert_ne!(a,b);
    let ca=matrix4_controlled_target(&a);
    let cb=matrix4_controlled_target(&b);
    assert_ne!(ca,cb);
    assert_eq!(ca,matrix4_identity());
    assert_eq!(cb,matrix4_diagonal([
        Q8::one(),Q8::one(),Q8::real(-1),Q8::real(-1)]));
    println!("PHASE_EQ_NOT_CONGRUENT_UNDER_CONTROL=true");
}
