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
            out[output][input].sum(normalized(eighth_root(phase),fresh.len()));
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
    let lines:Vec<&str>=source.lines().collect();
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
                println!("TWOQ_EFFECT_RISK case={name} native_equals_reference={}",native_risk==expected);
            }
            Err(e)=>println!("TWOQ_EFFECT_RISK case={name} native_error={e}")
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
    let Ok(reference_a)=checked_reference(a)else{return false};
    let Ok(reference_b)=checked_reference(b)else{return false};
    let Ok(native_a)=actual_source_matrix(a)else{return false};
    let Ok(native_b)=actual_source_matrix(b)else{return false};
    // Never mint a source-linked certificate from an unchecked producer matrix.
    if reference_a!=native_a || reference_b!=native_b {return false;}
    let computed=product(&dagger(&native_a),&native_b);
    if claim!=&computed {return false;}
    match property {
        PropertyTag::StrictOperatorEq=>computed==identity(),
        PropertyTag::PhaseEq=>{
            let z=&computed[0][0];
            for row in 0..4 {
                for col in 0..4 {
                    let target=if row==col {z.clone()}else{Q8::zero()};
                    if computed[row][col]!=target {return false;}
                }
            }
            z.times(&z.conjugate())==Q8::one()
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
