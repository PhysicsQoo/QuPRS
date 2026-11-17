//! Independent, deliberately narrow two-qubit source-to-matrix experiment.
 //!
 //! Exact Q(zeta_8) reconstruction from native unreduced PathSum is compared
 //! to a separately specified full 4x4 standard gate matrix, including CP.
 //! No solver, approximate tolerance, or full OpenQASM parser is claimed.

use num_rational::Ratio;
use quprs::{qasm::parse_qasm_str,PathSum};

type Rat=Ratio<i128>;
fn r(n:i128,d:i128)->Rat {Rat::new(n,d)}
#[derive(Clone,Debug,PartialEq,Eq)]
struct Q8 {a:Rat,b:Rat,c:Rat,d:Rat}
impl Q8 {
    fn new(a:Rat,b:Rat,c:Rat,d:Rat)->Self {Self{a,b,c,d}}
    fn zero()->Self {Self::new(r(0,1),r(0,1),r(0,1),r(0,1))}
    fn one()->Self {Self::new(r(1,1),r(0,1),r(0,1),r(0,1))}
    fn integer(n:i128)->Self {Self::new(r(n,1),r(0,1),r(0,1),r(0,1))}
    fn imaginary(n:i128)->Self {Self::new(r(0,1),r(0,1),r(n,1),r(0,1))}
    fn sqrt2_half()->Self {Self::new(r(0,1),r(1,2),r(0,1),r(0,1))}
    fn sum(&mut self,x:Self){self.a+=x.a;self.b+=x.b;self.c+=x.c;self.d+=x.d;}
    fn neg(&self)->Self {Self::new(-self.a.clone(),-self.b.clone(),-self.c.clone(),-self.d.clone())}
    fn scale(&self,n:i128,d:i128)->Self {
        let k=r(n,d);
        Self::new(&self.a*&k,&self.b*&k,&self.c*&k,&self.d*&k)
    }
    fn conjugate(&self)->Self {
        Self::new(self.a.clone(),self.b.clone(),-self.c.clone(),-self.d.clone())
    }
    fn sqrt2(&self)->Self {
        Self::new(&self.b*r(2,1),self.a.clone(),&self.d*r(2,1),self.c.clone())
    }
    fn times(&self,z:&Self)->Self {
        Self::new(
            &self.a*&z.a+r(2,1)*(&self.b*&z.b)-&self.c*&z.c-r(2,1)*(&self.d*&z.d),
            &self.a*&z.b+&self.b*&z.a-&self.c*&z.d-&self.d*&z.c,
            &self.a*&z.c+r(2,1)*(&self.b*&z.d)+&self.c*&z.a+r(2,1)*(&self.d*&z.b),
            &self.a*&z.d+&self.b*&z.c+&self.c*&z.b+&self.d*&z.a)
    }
}
fn eighth_root(cycles:Rat)->Q8 {
    let e=cycles*r(8,1);
    assert_eq!(*e.numer()%*e.denom(),0,"not in exact eighth-root fixture");
    match e.to_integer().rem_euclid(8) {
        0=>Q8::one(),
        1=>Q8::new(r(0,1),r(1,2),r(0,1),r(1,2)),
        2=>Q8::imaginary(1),
        3=>Q8::new(r(0,1),r(-1,2),r(0,1),r(1,2)),
        4=>Q8::integer(-1),
        5=>Q8::new(r(0,1),r(-1,2),r(0,1),r(-1,2)),
        6=>Q8::imaginary(-1),
        7=>Q8::new(r(0,1),r(1,2),r(0,1),r(-1,2)),
        _=>unreachable!()
    }
}
fn normalized(z:Q8,k:usize)->Q8 {
    assert!(k<12);
    if k%2==0 {z.scale(1,1i128<<(k/2))}
    else {z.sqrt2().scale(1,1i128<<((k+1)/2))}
}
type M4=[[Q8;4];4];
fn zero()->M4 {std::array::from_fn(|_|std::array::from_fn(|_|Q8::zero()))}
fn identity()->M4 {
    std::array::from_fn(|row|std::array::from_fn(|col|
        if row==col {Q8::one()} else {Q8::zero()}))
}
fn product(a:&M4,b:&M4)->M4 {
    std::array::from_fn(|row|std::array::from_fn(|col|{
        let mut z=Q8::zero();
        for k in 0..4 {z.sum(a[row][k].times(&b[k][col]));}
        z
    }))
}
fn dagger(a:&M4)->M4 {
    std::array::from_fn(|row|std::array::from_fn(|col|a[col][row].conjugate()))
}
fn mono_true(mono:&[u32],bits:u64)->bool {
    mono.iter().all(|&v|v<62 && (bits&(1u64<<v))!=0)
}
fn actual_source_matrix(source:&str)->Result<M4,String> {
    let (ops,n)=parse_qasm_str(source)?;
    if n!=2 {return Err("requires exactly two declared qubits".into());}
    let mut ps=PathSum::new(2);
    ps.set_auto_reduce(false);
    for op in ops {op.apply(&mut ps,false);}
    let mut fresh:Vec<u32>=ps.v.path_vars.iter().copied().filter(|v|*v>=2).collect();
    fresh.sort_unstable();
    if fresh.len()>=12 {return Err("unbounded internal path variables".into());}
    let mut out=zero();
    for input in 0..4u64 {
        for mask in 0..(1u64<<fresh.len()) {
            let mut bits=input;
            for (j,&v) in fresh.iter().enumerate() {
                if v>=62 {return Err("path variable index too large".into());}
                if mask&(1u64<<j)!=0 {bits|=1u64<<v;}
            }
            let mut output=0usize;
            for q in 0..2 {
                let bit=ps.f.functions[q].iter()
                    .fold(false,|acc,m|acc^mono_true(m,bits));
                if bit {output|=1usize<<q;}
            }
            let mut phase=r(0,1);
            for (monomial,coeff) in &ps.p.terms {
                if coeff.radians.is_some()||!coeff.symbols.is_empty() {
                    return Err("source phase is not an exact rational cycle".into());
                }
                if mono_true(monomial,bits) {
                    phase+=r(coeff.constant.numer as i128,coeff.constant.denom as i128);
                }
            }
            out[output][input as usize].sum(normalized(eighth_root(phase),fresh.len()));
        }
    }
    Ok(out)
}
fn gate_matrix(literal:&str)->Option<M4> {
    let mut out=zero();
    match literal {
        "h q[0];" | "h q[1];" => {
            let bit=if literal=="h q[0];" {1usize} else {2usize};
            for input in 0..4 {
                let lower=input&!bit;
                let upper=lower|bit;
                out[lower][input]=Q8::sqrt2_half();
                out[upper][input]=if input&bit==0
                    {Q8::sqrt2_half()} else {Q8::sqrt2_half().neg()};
            }
        }
        "cx q[0],q[1];" | "cx q[1],q[0];" => {
            let control=if literal=="cx q[0],q[1];" {1usize} else {2usize};
            let target=if control==1 {2usize} else {1usize};
            for input in 0..4 {
                let output=if input&control!=0 {input^target} else {input};
                out[output][input]=Q8::one();
            }
        }
        "cz q[0],q[1];" | "cp(pi) q[0],q[1];" |
        "cp(pi/2) q[0],q[1];" => {
            for input in 0..4 {
                out[input][input]=if input!=3 {Q8::one()}
                    else if literal=="cp(pi/2) q[0],q[1];" {Q8::imaginary(1)}
                    else {Q8::integer(-1)};
            }
        }
        "s q[1];" => {
            for input in 0..4 {
                out[input][input]=if input&2==0 {Q8::one()} else {Q8::imaginary(1)};
            }
        }
        "t q[0];" => {
            for input in 0..4 {
                out[input][input]=if input&1==0 {Q8::one()}
                    else {eighth_root(r(1,8))};
            }
        }
        "p(pi) q[0];" => {
            for input in 0..4 {
                out[input][input]=if input&1==0 {Q8::one()} else {Q8::integer(-1)};
            }
        }
        "gphase(pi);" | "gphase(pi/2);" => {
            let z=if literal=="gphase(pi);" {Q8::integer(-1)} else {Q8::imaginary(1)};
            for j in 0..4 {out[j][j]=z.clone();}
        }
        _=>return None
    }
    Some(out)
}
fn narrow_source(lines:&[&str])->String {
    format!("OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\n{}\n",lines.join("\n"))
}
fn checked_reference(source:&str)->Result<M4,String> {
    // Empty or whitespace-only source lines are not gate operations.
    let lines:Vec<&str>=source.lines().filter(|line|!line.trim().is_empty()).collect();
    if lines.len()<3 || lines[0]!="OPENQASM 3.0;"
        || lines[1]!="include \"stdgates.inc\";" || lines[2]!="qubit[2] q;" {
        return Err("outside versioned source admission".into());
    }
    let statements=&lines[3..];
    if statements.len()>5 {return Err("too many source gates".into())}
    let mut out=identity();
    for &gate in statements {
        let m=gate_matrix(gate).ok_or_else(||format!("unbound or unsupported gate: {gate}"))?;
        out=product(&m,&out);
    }
    Ok(out)
}
fn cases()->Vec<(&'static str,Vec<&'static str>)> {
    vec![
        ("cx01",vec!["cx q[0],q[1];"]),
        ("cx10",vec!["cx q[1],q[0];"]),
        ("cz",vec!["cz q[0],q[1];"]),
        ("cp_half",vec!["cp(pi/2) q[0],q[1];"]),
        ("cp_pi",vec!["cp(pi) q[0],q[1];"]),
        ("bell",vec!["h q[0];","cx q[0],q[1];"]),
        ("reverse_bell",vec!["cx q[0],q[1];","h q[0];"]),
        ("cp_superposition",vec!["h q[0];","h q[1];","cp(pi/2) q[0],q[1];"]),
        ("cp_pi_superposition",vec!["h q[0];","h q[1];","cp(pi) q[0],q[1];"]),
        ("reverse_cx_phases",vec!["s q[1];","cx q[1],q[0];","t q[0];"]),
        ("global_minus_one",vec!["gphase(pi);"]),
        ("global_imaginary",vec!["gphase(pi/2);"]),
        ("controlled_gphase_image",vec!["p(pi) q[0];"]),
    ]
}
fn matrix_differences()->Vec<String> {
    let mut failures=Vec::new();
    for (name,gates) in cases() {
        let s=narrow_source(&gates);
        let expected=checked_reference(&s).expect("reference source admitted");
        match actual_source_matrix(&s) {
            Ok(observed)=>{
                let ok=observed==expected;
                println!("TWOQ_SOURCE_MATRIX case={name} exact={ok} gates={}",gates.len());
                if !ok {failures.push(name.into())}
            }
            Err(e)=>{
                println!("TWOQ_SOURCE_MATRIX case={name} error={e}");
                failures.push(name.into());
            }
        }
    }
    println!("TWOQ_SOURCE_MATRIX_NONCONFORMANCES={}",failures.join(","));
    failures
}
fn exact_squared_overlap(a:&Q8)->Q8 {a.times(&a.conjugate())}
fn bell_risk(m:&M4)->Q8 {
    let mut amp=m[0][0].clone();
    amp.sum(m[3][0].clone());
    exact_squared_overlap(&amp.times(&Q8::sqrt2_half()))
}
fn plus_risk(m:&M4)->Q8 {
    let mut amp=Q8::zero();
    for row in m {amp.sum(row[0].clone());}
    exact_squared_overlap(&amp.scale(1,2))
}
#[test]
fn observed_native_twoqubit_source_matrix_trace() {
    let issues=matrix_differences();
    println!("TWOQ_SOURCE_MATRIX_ISSUES={}",issues.len());
}
#[test]
fn observed_native_twoqubit_effect_risks() {
    let bell=narrow_source(&["h q[0];","cx q[0],q[1];"]);
    let reverse=narrow_source(&["cx q[0],q[1];","h q[0];"]);
    let cp=narrow_source(&["h q[0];","h q[1];","cp(pi/2) q[0],q[1];"]);
    let cp_pi=narrow_source(&["h q[0];","h q[1];","cp(pi) q[0],q[1];"]);
    for (name,source,expected,projector) in [
        ("bell",bell,Q8::one(),0),
        ("reverse_bell",reverse,Q8::new(r(1,4),r(0,1),r(0,1),r(0,1)),0),
        ("cp_half_superposition",cp,Q8::new(r(5,8),r(0,1),r(0,1),r(0,1)),1),
        ("cp_pi_superposition",cp_pi,Q8::new(r(1,4),r(0,1),r(0,1),r(0,1)),1)
    ] {
        let model=checked_reference(&source).expect("reference admission");
        let model_risk=if projector==0 {bell_risk(&model)}else{plus_risk(&model)};
        assert_eq!(model_risk,expected,"independent reference risk wrong: {name}");
        match actual_source_matrix(&source){
            Ok(native)=>{
                let native_risk=if projector==0 {bell_risk(&native)}else{plus_risk(&native)};
                assert_eq!(native_risk,expected,"native two-qubit effect risk: {name}");
                println!("TWOQ_EFFECT_RISK case={name} native_equals_reference=true");
            }
            Err(e)=>panic!("native two-qubit source risk parse failed for {name}: {e}")
        }
    }
}
#[test]
fn strict_contract_twoqubit_source_matrix() {
    let issues=matrix_differences();
    assert!(issues.is_empty(),"strict two-qubit source matrix mismatches: {}",issues.join(","));
}
#[derive(Clone,Copy,Debug)]
enum PropertyTag {StrictOperatorEq,PhaseEq,EffectRiskBound}
fn source_claim_admitted(a:&str,b:&str,claim:&M4,property:PropertyTag)->bool {
    let Ok(reference_a)=checked_reference(a)else{println!("SOURCE_CLAIM_REJECT=reference_a");return false};
    let Ok(reference_b)=checked_reference(b)else{println!("SOURCE_CLAIM_REJECT=reference_b");return false};
    let Ok(native_a)=actual_source_matrix(a)else{println!("SOURCE_CLAIM_REJECT=native_a");return false};
    let Ok(native_b)=actual_source_matrix(b)else{println!("SOURCE_CLAIM_REJECT=native_b");return false};
    // Never mint a source-linked certificate from an unchecked producer matrix.
    if reference_a!=native_a || reference_b!=native_b {println!("SOURCE_CLAIM_REJECT=source_replay reference_a_equal={} reference_b_equal={}",reference_a==native_a,reference_b==native_b);return false;}
    let computed=product(&dagger(&native_a),&native_b);
    if claim!=&computed {println!("SOURCE_CLAIM_REJECT=claimed_miter");return false;}
    match property {
        PropertyTag::StrictOperatorEq=>computed==identity(),
        PropertyTag::PhaseEq=>{
            let z=&computed[0][0];
            for row in 0..4 {
                for col in 0..4 {
                    let target=if row==col {z.clone()}else{Q8::zero()};
                    if computed[row][col]!=target {println!("SOURCE_CLAIM_REJECT=not_scalar row={row} col={col}");return false;}
                }
            }
            let phase_norm=z.times(&z.conjugate());
            println!("SOURCE_CLAIM_PHASE scalar={z:?} norm={phase_norm:?}");
            phase_norm==Q8::one()
        }
        // This proof rule lacks P/B/delta typing and must deny by default.
        PropertyTag::EffectRiskBound=>false,
    }
}
#[test]
fn observed_typed_source_miter_property_and_attack_guards() {
    let blank=narrow_source(&[]);
    let minus_one=narrow_source(&["gphase(pi);"]);
    let reference_minus=checked_reference(&minus_one).unwrap();
    let reference_miter=product(&dagger(&identity()),&reference_minus);
    let raw_identity=identity();
    // Same channel is not proof of strict equality.
    assert!(!source_claim_admitted(&blank,&minus_one,&reference_miter,PropertyTag::StrictOperatorEq));
    assert!(source_claim_admitted(&blank,&minus_one,&reference_miter,PropertyTag::PhaseEq));
    assert!(!source_claim_admitted(&blank,&minus_one,&raw_identity,PropertyTag::PhaseEq));
    assert!(!source_claim_admitted(&blank,&minus_one,&reference_miter,PropertyTag::EffectRiskBound));
    assert!(source_claim_admitted(&blank,&blank,&raw_identity,PropertyTag::StrictOperatorEq));
    assert!(!source_claim_admitted(&blank,&minus_one.replace("gphase","Gphase"),&reference_miter,PropertyTag::PhaseEq));
    assert!(!source_claim_admitted(
        &blank,&minus_one.replace("stdgates.inc","missing.inc"),&reference_miter,PropertyTag::PhaseEq));
    println!("TWOQ_TYPED_MITER phase_eq=true strict_eq=false forged_miter_rejected=true unsupported_risk_rejected=true");
}


// Bounded proof-carrying control-source experiment. The native QASM front end
// deliberately does not parse ctrl @. This independent tiny source checker
// checks an exact, versioned, literal subset, then cross-checks an equivalent
// supported native source decomposition. No general parser is claimed.
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum ControlledSourceGate {BuiltinU,StdlibU3,GlobalPhase}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum ControlledProperty {StrictEq,PhaseEq,UnitaryChannelEq,EffectRiskUpperBound}
struct CheckedControlledSource<'a> {
    original_source: &'a str,
    gate:ControlledSourceGate,
    control:usize,
    target:Option<usize>,
    scalar:Q8,
    target_z:bool,
    expected:M4,
    native_decomposition:M4,
}
struct ClaimedControlledCertificate<'a> {
    original_source:&'a str,
    claimed_gate:ControlledSourceGate,
    claimed_control:usize,
    claimed_target:Option<usize>,
    claimed_scalar:Q8,
    claimed_target_z:bool,
    claimed_matrix:M4,
}
fn control_diagonal(control:usize,scalar:&Q8)->M4 {
    std::array::from_fn(|row|std::array::from_fn(|col| {
        if row!=col {Q8::zero()}
        else if row&(1usize<<control)!=0 {scalar.clone()}
        else {Q8::one()}
    }))
}
fn controlled_diagonal_with_target(control:usize,target:Option<usize>,
    scalar:&Q8,target_z:bool)->M4{
    std::array::from_fn(|row|std::array::from_fn(|col|{
        if row!=col{return Q8::zero();}
        if row & (1usize<<control)==0{return Q8::one();}
        if target_z && target.is_some_and(|t| row & (1usize<<t)!=0) {
            scalar.neg()
        }else{
            scalar.clone()
        }
    }))
}
fn checked_controlled_source(source:&str)->Result<CheckedControlledSource<'_>,String>{
    let raw:Vec<&str>=source.lines().map(str::trim)
        .filter(|line|!line.is_empty()).collect();
    if raw.len()<3 || raw.len()>4 || raw[0]!="OPENQASM 3.0;"{
        return Err("unsupported or missing source version".into());
    }
    let mut pos=1;
    let imported=if raw.get(pos)==Some(&"include \"stdgates.inc\";"){
        pos+=1;true
    }else{false};
    if raw.get(pos)!=Some(&"qubit[2] q;") {
        return Err("only a single explicit qubit[2] q register".into());
    }
    pos+=1;
    if raw.len()!=pos+1{return Err("exactly one controlled operation required".into());}
    let literal=raw[pos];
    let (gate,control,target,scalar,target_z)=match literal{
        "ctrl @ U(2*pi,0,0) q[1],q[0];"=>
            (ControlledSourceGate::BuiltinU,1,Some(0),Q8::one(),false),
        "ctrl @ U(2*pi,0,0) q[0],q[1];"=>
            (ControlledSourceGate::BuiltinU,0,Some(1),Q8::one(),false),
        "ctrl @ u3(2*pi,0,0) q[1],q[0];" if imported=>
            (ControlledSourceGate::StdlibU3,1,Some(0),Q8::integer(-1),false),
        "ctrl @ u3(2*pi,0,0) q[0],q[1];" if imported=>
            (ControlledSourceGate::StdlibU3,0,Some(1),Q8::integer(-1),false),
        "ctrl @ gphase(pi) q[1];"=>
            (ControlledSourceGate::GlobalPhase,1,None,Q8::integer(-1),false),
        "ctrl @ gphase(pi) q[0];"=>
            (ControlledSourceGate::GlobalPhase,0,None,Q8::integer(-1),false),
        "ctrl @ U(0,pi,0) q[1],q[0];"=>
            (ControlledSourceGate::BuiltinU,1,Some(0),Q8::one(),true),
        "ctrl @ u3(0,pi,0) q[1],q[0];" if imported=>
            (ControlledSourceGate::StdlibU3,1,Some(0),Q8::imaginary(-1),true),
        "ctrl @ u3(0,pi,0) q[0],q[1];" if imported=>
            (ControlledSourceGate::StdlibU3,0,Some(1),Q8::imaginary(-1),true),
        "ctrl @ gphase(pi/2) q[1];"=>
            (ControlledSourceGate::GlobalPhase,1,None,Q8::imaginary(1),false),
        "ctrl @ gphase(pi/2) q[0];"=>
            (ControlledSourceGate::GlobalPhase,0,None,Q8::imaginary(1),false),
        _=>return Err("source gate outside pinned controlled subset".into())
    };
    // The controlled gate is exact diagonal for these specified sources.
    let expected=controlled_diagonal_with_target(control,target,&scalar,target_z);
    let phase_gate=if scalar==Q8::one(){None}
        else if scalar==Q8::integer(-1){
            Some(if control==1{"p(pi) q[1];"}else{"p(pi) q[0];"})
        }else if scalar==Q8::imaginary(1){
            Some(if control==1{"p(pi/2) q[1];"}else{"p(pi/2) q[0];"})
        }else if scalar==Q8::imaginary(-1){
            Some(if control==1{"p(-pi/2) q[1];"}else{"p(-pi/2) q[0];"})
        }else{return Err("unadmitted relative phase".into())};
    let mut native_gates=Vec::new();
    if let Some(g)=phase_gate{native_gates.push(g);}
    if target_z{native_gates.push("cz q[0],q[1];");}
    let decomposition=narrow_source(&native_gates);
    let native_decomposition=actual_source_matrix(&decomposition)
        .map_err(|e|format!("native decomposition unavailable: {e}"))?;
    if native_decomposition!=expected {
        return Err("independent standard and native decomposition disagree".into());
    }
    Ok(CheckedControlledSource{
        original_source:source,gate,control,target,scalar,target_z,expected,native_decomposition
    })
}
fn check_controlled_certificate(claim:&ClaimedControlledCertificate<'_>)->bool{
    let Ok(checked)=checked_controlled_source(claim.original_source)else{
        println!("CTRL_CERT_REJECT=source_admission");
        return false;
    };
    if checked.original_source!=claim.original_source
        || checked.gate!=claim.claimed_gate
        || checked.control!=claim.claimed_control
        || checked.target!=claim.claimed_target {
        println!("CTRL_CERT_REJECT=source_binding");
        return false;
    }
    if checked.target_z!=claim.claimed_target_z {
        println!("CTRL_CERT_REJECT=target_operator");
        return false;
    }
    if checked.scalar!=claim.claimed_scalar{
        println!("CTRL_CERT_REJECT=source_scalar");
        return false;
    }
    if claim.claimed_matrix!=checked.expected ||
        claim.claimed_matrix!=checked.native_decomposition{
        println!("CTRL_CERT_REJECT=claimed_controlled_matrix");
        return false;
    }
    true
}
fn checked_controlled_miter(
    left:&ClaimedControlledCertificate<'_>,
    right:&ClaimedControlledCertificate<'_>,
    claimed_miter:&M4,
    property:ControlledProperty,
)->bool{
    if !check_controlled_certificate(left)||!check_controlled_certificate(right){
        println!("CTRL_MITER_REJECT=unverified_source");
        return false;
    }
    let computed=product(&dagger(&left.claimed_matrix),&right.claimed_matrix);
    if &computed!=claimed_miter {
        println!("CTRL_MITER_REJECT=claimed_miter");
        return false;
    }
    match property{
        ControlledProperty::StrictEq=>computed==identity(),
        ControlledProperty::PhaseEq|ControlledProperty::UnitaryChannelEq=>{
            // For unitaries, channel equality is equivalent to scalar miter.
            let scalar=&computed[0][0];
            for row in 0..4{
                for col in 0..4{
                    let expected=if row==col {scalar.clone()}else{Q8::zero()};
                    if computed[row][col]!=expected{return false;}
                }
            }
            scalar.times(&scalar.conjugate())==Q8::one()
        }
        // No typed input subspace, observable and rational delta contract.
        ControlledProperty::EffectRiskUpperBound=>false
    }
}
fn controlled_certificate<'a>(source:&'a str)->ClaimedControlledCertificate<'a>{
    let checked=checked_controlled_source(source).expect("valid narrowed controlled source");
    ClaimedControlledCertificate{
        original_source:source,claimed_gate:checked.gate,
        claimed_control:checked.control,claimed_target:checked.target,
        claimed_scalar:checked.scalar,claimed_target_z:checked.target_z,
        claimed_matrix:checked.expected
    }
}
#[test]
fn observed_checked_controlled_source_certificates_with_native_oracle(){
    for (label,source) in [
        ("builtin_u_control_1","OPENQASM 3.0;\nqubit[2] q;\nctrl @ U(2*pi,0,0) q[1],q[0];"),
        ("stdlib_u3_control_1","OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(2*pi,0,0) q[1],q[0];"),
        ("stdlib_u3_control_0","OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(2*pi,0,0) q[0],q[1];"),
        ("global_phase_control_1","OPENQASM 3.0;\nqubit[2] q;\nctrl @ gphase(pi) q[1];"),
        ("global_phase_control_0","OPENQASM 3.0;\nqubit[2] q;\nctrl @ gphase(pi) q[0];"),
        ("builtin_z_control_1","OPENQASM 3.0;\nqubit[2] q;\nctrl @ U(0,pi,0) q[1],q[0];"),
        ("stdlib_z_phase_control_1","OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(0,pi,0) q[1],q[0];"),
        ("stdlib_z_phase_control_0","OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(0,pi,0) q[0],q[1];"),
        ("global_phase_i_control_1","OPENQASM 3.0;\nqubit[2] q;\nctrl @ gphase(pi/2) q[1];"),
        ("global_phase_i_control_0","OPENQASM 3.0;\nqubit[2] q;\nctrl @ gphase(pi/2) q[0];"),
    ]{
        let claim=controlled_certificate(source);
        assert!(check_controlled_certificate(&claim));
        assert_eq!(
            checked_controlled_source(source).unwrap().native_decomposition,
            claim.claimed_matrix
        );
        println!("CTRL_CERT_SOURCE case={label} exact=true native_equivalent=true");
    }
    println!("CTRL_CERT_ADMITTED_EXACT_CASES=10");
}
#[test]
fn observed_controlled_certificates_reject_forged_provenance(){
    let good="OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(2*pi,0,0) q[1],q[0];";
    let mut claim=controlled_certificate(good);
    assert!(check_controlled_certificate(&claim));
    claim.claimed_scalar=Q8::one();
    assert!(!check_controlled_certificate(&claim),"forged relative phase accepted");
    claim.claimed_scalar=Q8::integer(-1);
    claim.claimed_control=0;
    assert!(!check_controlled_certificate(&claim),"forged wire index accepted");
    claim.claimed_control=1;
    claim.claimed_target=Some(1);
    assert!(!check_controlled_certificate(&claim),"overlapping target accepted");
    claim.claimed_target=Some(0);
    claim.claimed_target_z=true;
    assert!(!check_controlled_certificate(&claim),"forged target operation accepted");
    claim.claimed_target_z=false;
    claim.claimed_matrix=identity();
    assert!(!check_controlled_certificate(&claim),"forged unitary matrix accepted");
    let rejected=[
        good.replace("stdgates.inc","other.inc"),
        good.replace("OPENQASM 3.0;","OPENQASM 3.1;"),
        good.replace("ctrl @ u3","ctrl @ U3"),
        good.replace("ctrl @ u3","negctrl @ u3"),
        good.replace("q[1],q[0]","q[1],q[1]"),
        good.replace("2*pi","pi"),
        good.replace("include \"stdgates.inc\";\n",""),
        format!("{good}\nctrl @ gphase(pi) q[1];"),
    ];
    for (idx,source) in rejected.iter().enumerate(){
        assert!(checked_controlled_source(source).is_err(),
            "invalid or unsupported source allowed: {idx}");
        println!("CTRL_CERT_NEGATIVE_ADMISSION case={idx} refused=true");
    }
    println!("CTRL_CERT_FORGED_FIELDS_REJECTED=5");
    println!("CTRL_CERT_INVALID_SOURCES_REJECTED={}",rejected.len());
}
#[test]
fn observed_controlled_miter_property_typing_and_forgery(){
    let u_source="OPENQASM 3.0;\nqubit[2] q;\nctrl @ U(2*pi,0,0) q[1],q[0];";
    let u3_source="OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(2*pi,0,0) q[1],q[0];";
    let a=controlled_certificate(u_source);
    let b=controlled_certificate(u3_source);
    let exact_miter=product(&dagger(&a.claimed_matrix),&b.claimed_matrix);
    assert_eq!(exact_miter,control_diagonal(1,&Q8::integer(-1)));
    for property in [ControlledProperty::StrictEq,ControlledProperty::PhaseEq,
        ControlledProperty::UnitaryChannelEq,ControlledProperty::EffectRiskUpperBound]{
        assert!(!checked_controlled_miter(&a,&b,&exact_miter,property));
        println!("CTRL_CERT_UNSOUND_PROPERTY_DENIED kind={property:?}");
    }
    assert!(checked_controlled_miter(&a,&a,&identity(),ControlledProperty::StrictEq));
    assert!(checked_controlled_miter(&b,&b,&identity(),ControlledProperty::PhaseEq));
    assert!(checked_controlled_miter(&b,&b,&identity(),ControlledProperty::UnitaryChannelEq));
    assert!(!checked_controlled_miter(&a,&b,&identity(),ControlledProperty::PhaseEq));
    let z_u="OPENQASM 3.0;\nqubit[2] q;\nctrl @ U(0,pi,0) q[1],q[0];";
    let z_u3="OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nctrl @ u3(0,pi,0) q[1],q[0];";
    let a_z=controlled_certificate(z_u);
    let b_z=controlled_certificate(z_u3);
    let relative_phase=product(&dagger(&a_z.claimed_matrix),&b_z.claimed_matrix);
    assert_eq!(relative_phase,control_diagonal(1,&Q8::imaginary(-1)));
    assert!(!checked_controlled_miter(&a_z,&b_z,&relative_phase,
        ControlledProperty::StrictEq));
    assert!(!checked_controlled_miter(&a_z,&b_z,&relative_phase,
        ControlledProperty::PhaseEq));
    assert!(!checked_controlled_miter(&a_z,&b_z,&relative_phase,
        ControlledProperty::UnitaryChannelEq));
    println!("CTRL_CERT_NONTRIVIAL_TARGET_MITER_PHASE=-i verified=true");
    println!("CTRL_CERT_MITER_FORGERY_REJECTED=true");
}


// Test-only, source-bound non-diagonal proof rule: H_c D H_c.
// This does not parse general OpenQASM modifiers. It validates a small
// independent grammar, replays all source operations, and cross-checks a
// supported native decomposition using unreduced PathSum and exact Q8.
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum FrameGate { UZ=1,U3Z=2,CtrlPhase=3,U3MinusI=4,UGate=5 }
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
struct FrameStep{
    gate:FrameGate,control:u8,target:Option<u8>,quarters:u8,z:bool,
}
#[derive(Clone,Debug,PartialEq,Eq)]
struct FrameClaim{
    source_digest:[u8;32],hadamard_wire:u8,
    steps:Vec<FrameStep>,phase_singles:[u8;2],phase_pair:u8,
}
fn sha_source(src:&str)->[u8;32]{
    use sha2::{Digest,Sha256};
    let value=Sha256::digest(src.as_bytes());
    let mut d=[0u8;32];d.copy_from_slice(&value);d
}
fn frame_step(line:&str)->Result<FrameStep,String>{
    let (gate,control,target,quarters,z)=match line {
        "ctrl @ U(0,pi,0) q[1],q[0];"=>
            (FrameGate::UZ,1,Some(0),0,true),
        "ctrl @ U(0,pi,0) q[0],q[1];"=>
            (FrameGate::UZ,0,Some(1),0,true),
        "ctrl @ u3(0,pi,0) q[1],q[0];"=>
            (FrameGate::U3Z,1,Some(0),3,true),
        "ctrl @ u3(0,pi,0) q[0],q[1];"=>
            (FrameGate::U3Z,0,Some(1),3,true),
        "ctrl @ gphase(pi/2) q[1];"=>
            (FrameGate::CtrlPhase,1,None,1,false),
        "ctrl @ gphase(pi/2) q[0];"=>
            (FrameGate::CtrlPhase,0,None,1,false),
        "ctrl @ gphase(-pi/2) q[1];"=>
            (FrameGate::CtrlPhase,1,None,3,false),
        "ctrl @ gphase(pi) q[1];"=>
            (FrameGate::CtrlPhase,1,None,2,false),
        "ctrl @ u3(2*pi,0,0) q[1],q[0];"=>
            (FrameGate::U3MinusI,1,Some(0),2,false),
        "ctrl @ U(2*pi,0,0) q[1],q[0];"=>
            (FrameGate::UGate,1,Some(0),0,false),
        _=>return Err("unsupported exact controlled diagonal source literal".into()),
    };
    Ok(FrameStep{gate,control,target,quarters,z})
}
fn frame_polynomial(steps:&[FrameStep])->([u8;2],u8){
    let mut singles=[0u8;2];
    let mut pair=0u8;
    for step in steps{
        singles[step.control as usize]=(singles[step.control as usize]+step.quarters)%4;
        if step.z{pair=(pair+2)%4;}
    }
    (singles,pair)
}
fn parse_h_frame_source(src:&str)->Result<FrameClaim,String>{
    if src.len()>8192 {return Err("source too large".into());}
    let lines=src.lines().map(str::trim).filter(|line|!line.is_empty())
        .collect::<Vec<_>>();
    if lines.len()<6 ||lines.len()>18
       ||lines[0]!="OPENQASM 3.0;"
       ||lines[1]!="include \"stdgates.inc\";"
       ||lines[2]!="qubit[2] q;"{
        return Err("invalid or unsupported source frame".into());
    }
    let wire=match lines[3]{
        "h q[0];"=>0u8,
        "h q[1];"=>1u8,
        _=>return Err("missing exact leading H".into()),
    };
    if lines.last()!=Some(&lines[3]){
        return Err("source H frame mismatched or open".into());
    }
    let mut steps=Vec::new();
    for line in &lines[4..lines.len()-1]{
        steps.push(frame_step(line)?);
    }
    if steps.is_empty()||steps.len()>12{
        return Err("empty or oversized source frame".into());
    }
    let (phase_singles,phase_pair)=frame_polynomial(&steps);
    Ok(FrameClaim{
        source_digest:sha_source(src),hadamard_wire:wire,
        steps,phase_singles,phase_pair
    })
}
fn encode_h_frame_cert(c:&FrameClaim)->Vec<u8>{
    let mut output=Vec::with_capacity(41+5*c.steps.len());
    output.extend_from_slice(b"HFC1");
    output.extend_from_slice(&c.source_digest);
    output.push(c.hadamard_wire);
    output.push(c.steps.len() as u8);
    for s in &c.steps{
        output.push(s.gate as u8);
        output.push(s.control);
        output.push(s.target.unwrap_or(255));
        output.push(s.quarters);
        output.push(u8::from(s.z));
    }
    output.extend_from_slice(&c.phase_singles);
    output.push(c.phase_pair);
    output
}
fn decode_h_frame_cert(bytes:&[u8])->Result<FrameClaim,String>{
    if bytes.len()<46||bytes.get(..4)!=Some(b"HFC1".as_slice()){
        return Err("invalid certificate envelope".into());
    }
    let wire=bytes[36];
    let count=bytes[37] as usize;
    if wire>1||count==0||count>12||bytes.len()!=41+5*count{
        return Err("invalid frame wire/length".into());
    }
    let mut digest=[0u8;32];digest.copy_from_slice(&bytes[4..36]);
    let mut steps=Vec::with_capacity(count);
    for b in bytes[38..38+5*count].chunks_exact(5){
        let gate=match b[0]{
            1=>FrameGate::UZ,2=>FrameGate::U3Z,3=>FrameGate::CtrlPhase,
            4=>FrameGate::U3MinusI,5=>FrameGate::UGate,
            _=>return Err("unknown source gate kind".into())
        };
        let target=if b[2]==255{None}else{Some(b[2])};
        if b[1]>1||target.is_some_and(|t|t>1||t==b[1])
            ||b[3]>3||b[4]>1{
            return Err("invalid phase/control/target/boolean fields".into());
        }
        if (gate==FrameGate::CtrlPhase)!=target.is_none(){
            return Err("wrong number of source operands".into());
        }
        steps.push(FrameStep{gate,control:b[1],target,quarters:b[3],z:b[4]==1});
    }
    let singles=[bytes[38+5*count],bytes[39+5*count]];
    let pair=bytes[40+5*count];
    if singles.iter().any(|&x|x>3)||!matches!(pair,0|2){
        return Err("illegal polynomial coefficient".into());
    }
    if (singles,pair)!=frame_polynomial(&steps){
        return Err("forged phase normal form".into());
    }
    Ok(FrameClaim{source_digest:digest,hadamard_wire:wire,steps,
        phase_singles:singles,phase_pair:pair})
}
fn replay_h_frame_cert(src:&str,bytes:&[u8])->Result<FrameClaim,String>{
    let claimed=decode_h_frame_cert(bytes)?;
    if claimed.source_digest!=sha_source(src){
        return Err("claimed source bytes differ".into());
    }
    let replayed=parse_h_frame_source(src)?;
    if claimed!=replayed {return Err("source IR certificate replay mismatch".into());}
    Ok(replayed)
}
fn h_frame_source(lines:&[&str],h_wire:usize)->String{
    format!(
        "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[{h_wire}];\n{}\nh q[{h_wire}];\n",
        lines.join("\n")
    )
}
fn native_h_frame_lowering(c:&FrameClaim)->String{
    let mut lines=vec![format!("h q[{}];",c.hadamard_wire)];
    for s in &c.steps{
        let wire=s.control;
        match s.quarters {
            0=>(),
            1=>lines.push(format!("p(pi/2) q[{wire}];")),
            2=>lines.push(format!("p(pi) q[{wire}];")),
            3=>lines.push(format!("p(-pi/2) q[{wire}];")),
            _=>unreachable!()
        }
        if s.z {
            lines.push("cz q[0],q[1];".to_owned());
        }
    }
    lines.push(format!("h q[{}];",c.hadamard_wire));
    let texts=lines.iter().map(String::as_str).collect::<Vec<_>>();
    narrow_source(&texts)
}
fn diagonal_quarter(c:&FrameClaim,basis:usize)->u8 {
    let x0=u8::from(basis&1!=0);
    let x1=u8::from(basis&2!=0);
    (c.phase_singles[0]*x0+c.phase_singles[1]*x1
        +c.phase_pair*x0*x1)%4
}
fn reference_h_frame_matrix(c:&FrameClaim)->M4 {
    let mut diag=zero();
    for basis in 0..4{
        let phase=diagonal_quarter(c,basis);
        diag[basis][basis]=match phase {
            0=>Q8::one(),1=>Q8::imaginary(1),
            2=>Q8::integer(-1),3=>Q8::imaginary(-1),
            _=>unreachable!()
        };
    }
    let h=gate_matrix(if c.hadamard_wire==0{"h q[0];"}
        else{"h q[1];"}).unwrap();
    product(&h,&product(&diag,&h))
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum FrameProperty {StrictEq,PhaseEq,UnitaryChannelEq,EffectRisk}
fn checked_h_frame_pair(
    source_a:&str,proof_a:&[u8],source_b:&str,proof_b:&[u8],
    property:FrameProperty,
)->Result<bool,String>{
    let a=replay_h_frame_cert(source_a,proof_a)?;
    let b=replay_h_frame_cert(source_b,proof_b)?;
    if a.hadamard_wire!=b.hadamard_wire{
        return Err("different H frames need a different proof rule".into());
    }
    if property==FrameProperty::EffectRisk{return Ok(false);}
    // All admitted cores fix |00> with scalar 1. An identical H frame
    // preserves both global scalar and strict-equality invariants.
    Ok((a.phase_singles,a.phase_pair)==(b.phase_singles,b.phase_pair))
}
fn strict_inequality_witness_basis(a:&FrameClaim,b:&FrameClaim)->Option<usize>{
    if a.hadamard_wire!=b.hadamard_wire {return None;}
    (0..4).find(|&basis|diagonal_quarter(a,basis)!=diagonal_quarter(b,basis))
}
#[test]
fn observed_source_bound_non_diagonal_h_frame_oracle(){
    let a=h_frame_source(&[
        "ctrl @ u3(0,pi,0) q[1],q[0];",
        "ctrl @ gphase(pi/2) q[1];",
    ],0);
    let b=h_frame_source(&["ctrl @ U(0,pi,0) q[1],q[0];"],0);
    let c=h_frame_source(&["ctrl @ u3(0,pi,0) q[1],q[0];"],0);
    let d=h_frame_source(&["ctrl @ U(0,pi,0) q[0],q[1];"],1);
    let ca=parse_h_frame_source(&a).unwrap();
    let cb=parse_h_frame_source(&b).unwrap();
    let cc=parse_h_frame_source(&c).unwrap();
    let cd=parse_h_frame_source(&d).unwrap();
    let claims=[
        ("phase_cancelled_source_a",&ca),
        ("strict_builtin_u_source_b",&cb),
        ("phase_sensitive_source_c",&cc),
        ("opposite_h_wire_source_d",&cd),
    ];
    for (name,claim) in claims{
        let lowered=native_h_frame_lowering(claim);
        let native=actual_source_matrix(&lowered)
            .expect("native PathSum must accept exact supported decomposition");
        let independent=reference_h_frame_matrix(claim);
        assert_eq!(native,independent,
            "native PathSum and independent H-D-H matrices disagree: {name}");
        println!("HFRAME_NATIVE_EXACT_MATRIX case={name} equal=true");
    }
    let cx_1to0=gate_matrix("cx q[1],q[0];").unwrap();
    assert_eq!(reference_h_frame_matrix(&ca),cx_1to0);
    assert_eq!(reference_h_frame_matrix(&cb),cx_1to0);
    assert_ne!(reference_h_frame_matrix(&cc),cx_1to0);
    let cx_0to1=gate_matrix("cx q[0],q[1];").unwrap();
    assert_eq!(reference_h_frame_matrix(&cd),cx_0to1);
    println!("HFRAME_NONDIAGONAL_CX_WITNESS=true");

    let pa=encode_h_frame_cert(&ca);
    let pb=encode_h_frame_cert(&cb);
    let pc=encode_h_frame_cert(&cc);
    let pd=encode_h_frame_cert(&cd);
    assert!(checked_h_frame_pair(&a,&pa,&b,&pb,FrameProperty::StrictEq).unwrap());
    assert!(checked_h_frame_pair(&a,&pa,&b,&pb,FrameProperty::PhaseEq).unwrap());
    assert!(checked_h_frame_pair(&a,&pa,&b,&pb,FrameProperty::UnitaryChannelEq).unwrap());
    assert!(!checked_h_frame_pair(&a,&pa,&c,&pc,FrameProperty::StrictEq).unwrap());
    assert!(!checked_h_frame_pair(&a,&pa,&c,&pc,FrameProperty::PhaseEq).unwrap());
    assert!(!checked_h_frame_pair(&a,&pa,&c,&pc,FrameProperty::UnitaryChannelEq).unwrap());
    assert!(!checked_h_frame_pair(&a,&pa,&b,&pb,FrameProperty::EffectRisk).unwrap());
    assert!(checked_h_frame_pair(&a,&pa,&d,&pd,FrameProperty::StrictEq).is_err());
    let witness=strict_inequality_witness_basis(&ca,&cc).unwrap();
    assert_eq!(witness,2);
    // The exact strict-inequality input state is H_c |10>; it is not
    // necessarily a computational basis vector of the full circuit.
    println!("HFRAME_TYPED_MITER strict_equal=true phase_sensitive_refuted=true witness_basis={witness}");
    println!("HFRAME_CERT_BYTES first={} second={} source_bytes_first={}",
        pa.len(),pb.len(),a.len());
}
#[test]
fn observed_source_bound_non_diagonal_certificate_attacks(){
    let src=h_frame_source(&[
        "ctrl @ u3(0,pi,0) q[1],q[0];",
        "ctrl @ gphase(pi/2) q[1];",
    ],0);
    let c=parse_h_frame_source(&src).unwrap();
    let bytes=encode_h_frame_cert(&c);
    assert_eq!(decode_h_frame_cert(&bytes).unwrap(),c);
    assert_eq!(replay_h_frame_cert(&src,&bytes).unwrap(),c);
    assert_eq!(bytes.len(),41+5*c.steps.len());
    let mutants=[
        src.replace("h q[0];\nctrl @","h q[1];\nctrl @"),
        src.replace("ctrl @ u3","ctrl @ U3"),
        src.replace("include \"stdgates.inc\";","include \"other.inc\";"),
        src.replace("OPENQASM 3.0;","OPENQASM 3.1;"),
        src.replace("ctrl @ u3","negctrl @ u3"),
        src.replace("q[1],q[0]","q[1],q[1]"),
        src.replace("gphase(pi/2)","gphase(pi)"),
        src.replace("h q[0];\n", "h q[1];\n"),
        format!("{src}ctrl @ gphase(pi) q[1];\n"),
    ];
    for (index,item) in mutants.iter().enumerate(){
        assert!(replay_h_frame_cert(item,&bytes).is_err(),
            "source mutation accepted: {index}");
    }
    let mut tampered=bytes.clone();
    tampered[36]=1;
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    tampered=bytes.clone();tampered[38+3]=2;
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    tampered=bytes.clone();tampered[38+4]=0;
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    tampered=bytes.clone();let end=tampered.len()-1;tampered[end]=0;
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    tampered=bytes.clone();tampered.push(0);
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    tampered=bytes.clone();tampered.pop();
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    tampered=bytes.clone();tampered[0]=b'X';
    assert!(replay_h_frame_cert(&src,&tampered).is_err());
    println!("HFRAME_SOURCE_MUTATIONS_REJECTED={}",mutants.len());
    println!("HFRAME_CERT_MUTATIONS_REJECTED=7");
}


// A property-typed rank-one effect-risk proof, not merely circuit equality.
// The caller supplies the intended (trusted) input projector, bad projector,
// and delta; the source certificate only binds source semantics. A claimed
// verdict and claimed exact risk are independently reconstructed and checked.
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum FrameRiskVerdict {Proved,Refuted}
type Ket4=[Q8;4];
fn ket4_normalized(psi:&Ket4)->bool {
    let mut norm=Q8::zero();
    for z in psi {
        norm.sum(z.conjugate().times(z));
    }
    norm==Q8::one()
}
fn risk_from_rank_one_effect(matrix:&M4,input:&Ket4,bad:&Ket4)->Q8{
    let mut output:Ket4=std::array::from_fn(|_|Q8::zero());
    for row in 0..4{
        for col in 0..4{
            output[row].sum(matrix[row][col].times(&input[col]));
        }
    }
    let mut bad_amplitude=Q8::zero();
    for row in 0..4{
        bad_amplitude.sum(bad[row].conjugate().times(&output[row]));
    }
    bad_amplitude.times(&bad_amplitude.conjugate())
}
fn check_rank_one_frame_risk_claim(
    source:&str, source_cert:&[u8],
    trusted_input:&Ket4,trusted_bad:&Ket4,trusted_delta:&Rat,
    claimed_risk:&Q8,claimed_verdict:FrameRiskVerdict
)->Result<bool,String>{
    let frame=replay_h_frame_cert(source,source_cert)?;
    if !ket4_normalized(trusted_input)||!ket4_normalized(trusted_bad){
        return Err("input or bad projector does not have a unit norm generator".into());
    }
    if trusted_delta<&r(0,1)||trusted_delta>&r(1,1){
        return Err("outside declared rational probability threshold".into());
    }
    let risk=risk_from_rank_one_effect(&reference_h_frame_matrix(&frame),
        trusted_input,trusted_bad);
    if &risk!=claimed_risk{
        return Ok(false);
    }
    if risk.b!=r(0,1)||risk.c!=r(0,1)||risk.d!=r(0,1){
        return Err("rank-one risk outside this rational-result proof profile".into());
    }
    if risk.a<r(0,1)||risk.a>r(1,1){
        return Err("calculated risk outside [0,1]".into());
    }
    let expected=if risk.a<=*trusted_delta{
        FrameRiskVerdict::Proved
    }else{
        FrameRiskVerdict::Refuted
    };
    Ok(expected==claimed_verdict)
}
#[test]
fn observed_source_bound_nondiagonal_effect_risk_proved_and_refuted(){
    // Independent trusted specification:
    // AllDensityOn(|psi><psi|), psi=(|00>+|11>)/sqrt(2);
    // bad-effect B=|bad><bad|, bad=(|00>-|10>)/sqrt(2).
    // The only admitted density on the rank-one support is |psi><psi|.
    let s=Q8::sqrt2_half();
    let psi=[s.clone(),Q8::zero(),Q8::zero(),s.clone()];
    let bad=[s.clone(),Q8::zero(),s.neg(),Q8::zero()];
    assert!(ket4_normalized(&psi)&&ket4_normalized(&bad));
    let a=h_frame_source(&[
        "ctrl @ u3(0,pi,0) q[1],q[0];",
        "ctrl @ gphase(pi/2) q[1];",
    ],0);
    let c=h_frame_source(&["ctrl @ u3(0,pi,0) q[1],q[0];"],0);
    let ca=parse_h_frame_source(&a).unwrap();
    let cc=parse_h_frame_source(&c).unwrap();
    let cert_a=encode_h_frame_cert(&ca);
    let cert_c=encode_h_frame_cert(&cc);
    let reference_a=reference_h_frame_matrix(&ca);
    let reference_c=reference_h_frame_matrix(&cc);
    let native_a=actual_source_matrix(&native_h_frame_lowering(&ca)).unwrap();
    let native_c=actual_source_matrix(&native_h_frame_lowering(&cc)).unwrap();
    assert_eq!(reference_a,native_a);
    assert_eq!(reference_c,native_c);
    let zero=Q8::zero();
    let half=Q8::new(r(1,2),r(0,1),r(0,1),r(0,1));
    assert_eq!(risk_from_rank_one_effect(&native_a,&psi,&bad),zero);
    assert_eq!(risk_from_rank_one_effect(&native_c,&psi,&bad),half);
    let delta_zero=r(0,1);
    let delta_half=r(1,2);
    assert!(check_rank_one_frame_risk_claim(&a,&cert_a,&psi,&bad,
        &delta_zero,&zero,FrameRiskVerdict::Proved).unwrap());
    assert!(check_rank_one_frame_risk_claim(&c,&cert_c,&psi,&bad,
        &delta_zero,&half,FrameRiskVerdict::Refuted).unwrap());
    assert!(check_rank_one_frame_risk_claim(&c,&cert_c,&psi,&bad,
        &delta_half,&half,FrameRiskVerdict::Proved).unwrap());
    assert!(!check_rank_one_frame_risk_claim(&c,&cert_c,&psi,&bad,
        &delta_zero,&half,FrameRiskVerdict::Proved).unwrap());
    assert!(!check_rank_one_frame_risk_claim(&c,&cert_c,&psi,&bad,
        &delta_zero,&zero,FrameRiskVerdict::Proved).unwrap());
    let invalid_delta=r(3,2);
    assert!(check_rank_one_frame_risk_claim(&a,&cert_a,&psi,&bad,
        &invalid_delta,&zero,FrameRiskVerdict::Proved).is_err());
    let mut forged_cert=cert_c.clone();
    forged_cert[36]=1;
    assert!(check_rank_one_frame_risk_claim(&c,&forged_cert,&psi,&bad,
        &delta_zero,&half,FrameRiskVerdict::Refuted).is_err());
    println!("HFRAME_RANK_ONE_EFFECT_RISK source_a=0 source_c=1/2 exact_native=true");
    println!("HFRAME_RISK_VERDICTS proved=2 refuted=1 forged_proved_rejected=2 invalid_spec_rejected=1 forged_source_rejected=1");
}
