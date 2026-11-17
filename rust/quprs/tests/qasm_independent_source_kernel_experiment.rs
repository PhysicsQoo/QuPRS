//! Research-only independent OpenQASM source-semantics checker.
//!
//! SOURCE AUTHORITY: the narrow lexer and gate denotations below are built
//! without invoking quprs::qasm, QuantumOp, PathSum, or the production gates.
//! NATIVE OBSERVATION: a separate helper reconstructs native PathSum matrices
//! solely to compare them against the independently checked source values.
//!
//! No complete OpenQASM parser, general theta, independent proof of the
//! underlying rational arithmetic, or product-facing verifier is claimed.

use num_rational::Ratio;
use sha2::{Digest,Sha256};
type Rat=Ratio<i128>;
fn r(n:i128,d:i128)->Rat{Rat::new(n,d)}
#[derive(Clone,Debug,PartialEq,Eq)]
struct Exact {a:Rat,b:Rat,c:Rat,d:Rat}
impl Exact {
    fn new(a:Rat,b:Rat,c:Rat,d:Rat)->Self{Self{a,b,c,d}}
    fn zero()->Self{Self::new(r(0,1),r(0,1),r(0,1),r(0,1))}
    fn one()->Self{Self::real(1)}
    fn real(x:i128)->Self{Self::new(r(x,1),r(0,1),r(0,1),r(0,1))}
    fn imag(x:i128)->Self{Self::new(r(0,1),r(0,1),r(x,1),r(0,1))}
    fn halfsqrt2()->Self{Self::new(r(0,1),r(1,2),r(0,1),r(0,1))}
    fn add(&mut self,z:&Self){
        self.a+=z.a.clone();self.b+=z.b.clone();
        self.c+=z.c.clone();self.d+=z.d.clone();
    }
    fn neg(&self)->Self{Self::new(-self.a.clone(),-self.b.clone(),
        -self.c.clone(),-self.d.clone())}
    fn scaled(&self,n:i128,d:i128)->Self{
        let k=r(n,d);
        Self::new(&self.a*&k,&self.b*&k,&self.c*&k,&self.d*&k)
    }
    fn root2(&self)->Self{Self::new(&self.b*r(2,1),self.a.clone(),
        &self.d*r(2,1),self.c.clone())}
    fn times(&self,z:&Self)->Self {
        Self::new(
          &self.a*&z.a+r(2,1)*(&self.b*&z.b)-&self.c*&z.c-r(2,1)*(&self.d*&z.d),
          &self.a*&z.b+&self.b*&z.a-&self.c*&z.d-&self.d*&z.c,
          &self.a*&z.c+r(2,1)*(&self.b*&z.d)+&self.c*&z.a+r(2,1)*(&self.d*&z.b),
          &self.a*&z.d+&self.b*&z.c+&self.c*&z.b+&self.d*&z.a,
        )
    }
}
fn eighth_root(phase:Rat)->Result<Exact,String>{
    let eighths=phase*r(8,1);
    if *eighths.numer()%*eighths.denom()!=0{
        return Err("source phase not in fixed exact eighth-root profile".into());
    }
    Ok(match eighths.to_integer().rem_euclid(8){
        0=>Exact::one(),
        1=>Exact::new(r(0,1),r(1,2),r(0,1),r(1,2)),
        2=>Exact::imag(1),
        3=>Exact::new(r(0,1),r(-1,2),r(0,1),r(1,2)),
        4=>Exact::real(-1),
        5=>Exact::new(r(0,1),r(-1,2),r(0,1),r(-1,2)),
        6=>Exact::imag(-1),
        7=>Exact::new(r(0,1),r(1,2),r(0,1),r(-1,2)),
        _=>unreachable!(),
    })
}
fn norm(z:Exact,k:usize)->Exact{
    assert!(k<=10);
    if k%2==0 {z.scaled(1,1i128<<(k/2))}
    else{z.root2().scaled(1,1i128<<((k+1)/2))}
}
type M4=[[Exact;4];4];
type M2=[[Exact;2];2];
fn zero()->M4{std::array::from_fn(|_|std::array::from_fn(|_|Exact::zero()))}
fn eye()->M4{std::array::from_fn(|i|std::array::from_fn(|j|
    if i==j{Exact::one()}else{Exact::zero()}))}
fn product(a:&M4,b:&M4)->M4{
    std::array::from_fn(|i|std::array::from_fn(|j|{
        let mut out=Exact::zero();
        for k in 0..4{out.add(&a[i][k].times(&b[k][j]));}
        out
    }))
}
fn scalar(z:&Exact)->M4{std::array::from_fn(|i|std::array::from_fn(|j|
    if i==j {z.clone()}else{Exact::zero()}))}
fn onequbit(bit:usize,m:&M2)->M4{
    let mut output=zero();
    for input in 0..4usize{
        let source=usize::from(input&bit!=0);
        for destination in 0..2{
            let row=(input&!bit)|(destination*bit);
            output[row][input]=m[destination][source].clone();
        }
    }
    output
}
fn controlled(bit:usize,target:usize,m:&M2)->M4 {
    let mut output=zero();
    for input in 0..4usize{
        if input&bit==0 {output[input][input]=Exact::one();}
        else{
            let t=usize::from(input&target!=0);
            for destination in 0..2{
                let row=(input&!target)|(destination*target);
                output[row][input]=m[destination][t].clone();
            }
        }
    }
    output
}
fn cx(c:usize,t:usize)->M4{
    let mut output=zero();
    for input in 0..4usize {
        let row=if input&c!=0{input^t}else{input};
        output[row][input]=Exact::one();
    }
    output
}
fn cz()->M4{
    std::array::from_fn(|i|std::array::from_fn(|j|
        if i!=j{Exact::zero()}else if i==3{Exact::real(-1)}else{Exact::one()}))
}
fn z()->M2{[[Exact::one(),Exact::zero()],
    [Exact::zero(),Exact::real(-1)]]}
fn minus_i_z()->M2{[[Exact::imag(-1),Exact::zero()],
    [Exact::zero(),Exact::imag(1)]]}
fn identity2()->M2{[[Exact::one(),Exact::zero()],
    [Exact::zero(),Exact::one()]]}
fn minus_identity2()->M2{[[Exact::real(-1),Exact::zero()],
    [Exact::zero(),Exact::real(-1)]]}
fn h()->M2{let a=Exact::halfsqrt2();
    [[a.clone(),a.clone()],[a.clone(),a.neg()]]}
fn x()->M2{[[Exact::zero(),Exact::one()],
    [Exact::one(),Exact::zero()]]}
fn s()->M2{[[Exact::one(),Exact::zero()],
    [Exact::zero(),Exact::imag(1)]]}
fn t()->M2{[[Exact::one(),Exact::zero()],
    [Exact::zero(),eighth_root(r(1,8)).unwrap()]]}
fn p_half()->M2{[[Exact::one(),Exact::zero()],
    [Exact::zero(),Exact::imag(1)]]}
fn u_halfpi()->M2{
    // Official OpenQASM 3 built-in U(pi/2,0,0) matrix.
    let k=Exact::new(r(1,2),r(0,1),r(1,2),r(0,1));
    [[k.clone(),k.neg()],[k.clone(),k]]
}
fn u3_halfpi()->M2{
    let k=Exact::halfsqrt2();
    [[k.clone(),k.neg()],[k.clone(),k]]
}
fn qbit(token:&str)->Result<usize,String>{
    match token{"q[0]"=>Ok(1),"q[1]"=>Ok(2),
        _=>Err("source wire outside canonical q[0],q[1] profile".into())}
}
fn source_gate_matrix(statement:&str,has_stdlib:bool)->Result<M4,String>{
    // No lowercasing, broad token substitution or implicit stdlib.
    if statement=="gphase(pi);" {return Ok(scalar(&Exact::real(-1)));}
    if statement=="gphase(pi/2);" {return Ok(scalar(&Exact::imag(1)));}
    if statement=="gphase(-pi/2);" {return Ok(scalar(&Exact::imag(-1)));}
    let code=statement.strip_suffix(';').ok_or("missing statement semicolon")?;
    let (controlled_prefix,body)=match code.strip_prefix("ctrl @ "){
        Some(inner)=>(true,inner),None=>(false,code)
    };
    let (name,operand)=body.split_once(' ').ok_or("missing wire operands")?;
    if operand.contains(' ')||operand.contains('\t') {
        return Err("noncanonical source wire list".into());
    }
    let mut wire_iter=operand.split(',');
    let a=qbit(wire_iter.next().ok_or("missing first wire")?)?;
    let second=wire_iter.next();
    if wire_iter.next().is_some(){return Err("unsupported arity".into());}
    let second=second.map(qbit).transpose()?;
    if second==Some(a){return Err("repeated source operand".into());}
    if !has_stdlib && (name=="h"||name=="x"||name=="z"||
        name=="s"||name=="t"||name=="p(pi/2)"||
        name=="cx"||name=="cz"||name.starts_with("u3(")){
        return Err("stdlib gate is not in scope".into());
    }
    let one=match name{
        "h"=>Some(h()),"x"=>Some(x()),"z"=>Some(z()),
        "s"=>Some(s()),"t"=>Some(t()),"p(pi/2)"=>Some(p_half()),
        "U(0,0,0)"|"U(2*pi,0,0)"=>Some(identity2()),
        "u3(2*pi,0,0)"=>Some(minus_identity2()),
        "U(0,pi,0)"=>Some(z()),
        "u3(0,pi,0)"=>Some(minus_i_z()),
        "U(pi/2,0,0)"=>Some(u_halfpi()),
        "u3(pi/2,0,0)"=>Some(u3_halfpi()),
        _=>None,
    };
    if let Some(unitary)=one{
        return match (controlled_prefix,second){
            (false,None)=>Ok(onequbit(a,&unitary)),
            (true,Some(t))=>Ok(controlled(a,t,&unitary)),
            _=>Err("source modifier arity incompatible with gate".into())
        };
    }
    if controlled_prefix{return Err("unsupported controlled modifier".into());}
    match (name,second){
        ("cx",Some(t))=>Ok(cx(a,t)),
        ("cz",Some(_))=>Ok(cz()),
        _=>Err("unknown or unadmitted source gate".into())
    }
}
#[derive(Clone)]
struct ExactSourceIR{
    digest:[u8;32],steps:Vec<M4>,
}
fn digest_source(text:&str)->[u8;32] {
    let d=Sha256::digest(text.as_bytes());
    let mut x=[0u8;32];x.copy_from_slice(&d);x
}
fn independent_parse(text:&str)->Result<ExactSourceIR,String> {
    if text.len()>8192{return Err("UNKNOWN_RESOURCE_LIMIT: source bytes".into());}
    let lines=text.lines().map(str::trim)
        .filter(|x|!x.is_empty()).collect::<Vec<_>>();
    if lines.len()<3||!["OPENQASM 3.0;","OPENQASM 3.1;"].contains(&lines[0]){
        return Err("source header unsupported".into());
    }
    let mut cursor=1;
    let stdlib=if lines.get(cursor)==Some(&"include \"stdgates.inc\";"){
        cursor+=1;true
    }else{false};
    if lines.get(cursor)!=Some(&"qubit[2] q;"){
        return Err("independent checker requires canonical qubit[2] q".into());
    }
    cursor+=1;
    if lines.len()<=cursor||lines.len()-cursor>16{
        return Err("UNKNOWN_RESOURCE_LIMIT: operation count".into());
    }
    let mut steps=Vec::with_capacity(lines.len()-cursor);
    for &statement in &lines[cursor..]{
        steps.push(source_gate_matrix(statement,stdlib)?);
    }
    Ok(ExactSourceIR{digest:digest_source(text),steps})
}
fn independently_checked_matrix(src:&str)->Result<M4,String>{
    let ir=independent_parse(src)?;
    let mut result=eye();
    for gate in ir.steps {result=product(&gate,&result);}
    Ok(result)
}
#[derive(Clone)]
struct ClaimedSourceTrace{
    source_digest:[u8;32],prefix_matrices:Vec<M4>,
}
fn emit_source_trace(src:&str)->Result<ClaimedSourceTrace,String>{
    let ir=independent_parse(src)?;
    let mut current=eye();
    let mut claim=Vec::new();
    for gate in ir.steps {
        current=product(&gate,&current);
        claim.push(current.clone());
    }
    Ok(ClaimedSourceTrace{
        source_digest:digest_source(src),prefix_matrices:claim,
    })
}
fn checked_source_trace(src:&str,claim:&ClaimedSourceTrace)->Result<M4,String>{
    let ir=independent_parse(src)?;
    if ir.digest!=claim.source_digest{
        return Err("independent source digest mismatch".into());
    }
    if ir.steps.len()!=claim.prefix_matrices.len(){
        return Err("incomplete or extra source trace steps".into());
    }
    let mut current=eye();
    for (i,gate) in ir.steps.iter().enumerate(){
        current=product(gate,&current);
        if current!=claim.prefix_matrices[i]{
            return Err(format!("source-linked prefix-matrix mismatch at step {i}"));
        }
    }
    Ok(current)
}
fn source(statements:&[&str],import_stdlib:bool,version:&str)->String{
    let include=if import_stdlib{"include \"stdgates.inc\";\n"}else{""};
    let mut out=format!("{version}\n{include}qubit[2] q;\n");
    for line in statements {out.push_str(line);out.push('\n');}
    out
}

// Native production is an OBSERVATION, not the source definition.
// Kept separate from the independent parser and its checked source trace.
fn native_matrix(text:&str)->Result<M4,String>{
    use quprs::{qasm::parse_qasm_str,PathSum};
    let (ops,n)=parse_qasm_str(text)?;
    if n!=2{return Err("native matrix diagnostic requires two qubits".into());}
    let mut pathsum=PathSum::new(2);
    pathsum.set_auto_reduce(false);
    for op in ops{op.apply(&mut pathsum,false);}
    let mut fresh=pathsum.v.path_vars.iter().copied()
        .filter(|&x|x>=2).collect::<Vec<u32>>();
    fresh.sort_unstable();
    if fresh.len()>10||fresh.iter().any(|&x|x>=62){
        return Err("UNKNOWN_RESOURCE_LIMIT: native path variables".into());
    }
    let mut out=zero();
    for input in 0..4u64{
        for mask in 0..(1u64<<fresh.len()){
            let mut assignment=input;
            for (index,&var) in fresh.iter().enumerate(){
                if mask&(1u64<<index)!=0{assignment|=1u64<<var;}
            }
            let truth=|mono:&[u32]| mono.iter().all(|&v|
                v<62&&(assignment&(1u64<<v))!=0);
            let mut output=0usize;
            for (q,terms) in pathsum.f.functions.iter().enumerate(){
                if terms.iter().fold(false,|acc,mono|acc^truth(mono)){
                    output|=1usize<<q;
                }
            }
            let mut cycle=r(0,1);
            for (mono,coefficient) in &pathsum.p.terms{
                if coefficient.radians.is_some()||
                   !coefficient.symbols.is_empty(){
                    return Err("unadmitted source parameterization".into());
                }
                if truth(mono){
                    cycle+=r(coefficient.constant.numer as i128,
                        coefficient.constant.denom as i128);
                }
            }
            let term=norm(eighth_root(cycle)?,fresh.len());
            out[output][input as usize].add(&term);
        }
    }
    Ok(out)
}
#[test]
fn observed_independent_strict_source_phase_and_control(){
    let src=[
        ("U_twopi",source(&["U(2*pi,0,0) q[0];"],false,"OPENQASM 3.1;")),
        ("u3_twopi",source(&["u3(2*pi,0,0) q[0];"],true,"OPENQASM 3.1;")),
        ("ctrl_U_twopi",source(&["ctrl @ U(2*pi,0,0) q[1],q[0];"],false,"OPENQASM 3.1;")),
        ("ctrl_u3_twopi",source(&["ctrl @ u3(2*pi,0,0) q[1],q[0];"],true,"OPENQASM 3.1;")),
        ("ctrl_U_Z",source(&["ctrl @ U(0,pi,0) q[1],q[0];"],false,"OPENQASM 3.1;")),
        ("ctrl_u3_Z",source(&["ctrl @ u3(0,pi,0) q[1],q[0];"],true,"OPENQASM 3.1;")),
    ];
    let ms=src.iter().map(|(_,s)|independently_checked_matrix(s).unwrap())
        .collect::<Vec<M4>>();
    assert_eq!(ms[0],eye());
    assert_eq!(ms[1],onequbit(1,&minus_identity2()));
    assert_eq!(ms[2],eye());
    assert_eq!(ms[3],controlled(2,1,&minus_identity2()));
    assert_eq!(ms[4],controlled(2,1,&z()));
    assert_eq!(ms[5],controlled(2,1,&minus_i_z()));
    assert_ne!(ms[2],ms[3]);
    assert_ne!(ms[4],ms[5]);
    for (name,s) in src{
        let t=emit_source_trace(&s).unwrap();
        assert_eq!(checked_source_trace(&s,&t).unwrap(),
            independently_checked_matrix(&s).unwrap());
        println!("INDEPENDENT_SOURCE_GATE phase_strict_case={name} exact=true");
    }
    println!("INDEPENDENT_SOURCE_STRICT_PHASE_CASES=6");
}
#[test]
fn observed_independent_source_trace_accepts_non_diagonal_and_rejects_forgery(){
    let cases=[
        ("cx_frame",source(&["h q[0];","cz q[0],q[1];","h q[0];"],
            true,"OPENQASM 3.1;")),
        ("order_sensitive",source(&["cx q[0],q[1];","h q[0];"],
            true,"OPENQASM 3.1;")),
        ("global_phase",source(&["gphase(pi/2);","x q[1];"],
            true,"OPENQASM 3.1;")),
        ("non_clifford",source(&["h q[0];","t q[0];","cx q[0],q[1];"],
            true,"OPENQASM 3.1;")),
    ];
    for (name,src) in &cases {
        let claim=emit_source_trace(src).unwrap();
        assert_eq!(checked_source_trace(src,&claim).unwrap(),
            independently_checked_matrix(src).unwrap());
        println!("INDEPENDENT_SOURCE_TRACE case={name} exact=true");
    }
    assert_eq!(independently_checked_matrix(&cases[0].1).unwrap(),cx(2,1));
    let mut altered=emit_source_trace(&cases[0].1).unwrap();
    altered.prefix_matrices[0][0][0].add(&Exact::one());
    assert!(checked_source_trace(&cases[0].1,&altered).is_err());
    altered=emit_source_trace(&cases[0].1).unwrap();
    altered.prefix_matrices.pop();
    assert!(checked_source_trace(&cases[0].1,&altered).is_err());
    altered=emit_source_trace(&cases[0].1).unwrap();
    altered.source_digest[0]^=1;
    assert!(checked_source_trace(&cases[0].1,&altered).is_err());
    let shifted=cases[0].1.replace("h q[0];","h q[1];");
    assert!(checked_source_trace(&shifted,&emit_source_trace(&cases[0].1).unwrap()).is_err());
    let negative=[
        source(&["u3(2*pi,0,0) q[0];"],false,"OPENQASM 3.1;"),
        source(&["H q[0];"],true,"OPENQASM 3.1;"),
        source(&["h q[2];"],true,"OPENQASM 3.1;"),
        source(&["ctrl @ U(0,pi,0) q[1],q[1];"],false,"OPENQASM 3.1;"),
        source(&["ctrl @ gphase(pi) q[1];"],false,"OPENQASM 3.1;"),
        source(&["h q[0];"],true,"OPENQASM 3.2;"),
        source(&["x q[0];"],false,"OPENQASM 3.1;"),
        source(&["U(pi/3,0,0) q[0];"],false,"OPENQASM 3.1;"),
    ];
    for src in &negative{assert!(independent_parse(src).is_err());}
    println!("INDEPENDENT_SOURCE_TRACE_VALID_CASES=4");
    println!("INDEPENDENT_SOURCE_TRACE_TAMPER_REJECTED=4");
    println!("INDEPENDENT_SOURCE_PROFILE_NEGATIVE_REJECTED=8");
}
#[test]
fn observed_independent_source_vs_native_pathsum_strict_diagnostics(){
    let safe=[
        ("bell",source(&["h q[0];","cx q[0],q[1];"],
            true,"OPENQASM 3.0;")),
        ("cx_frame",source(&["h q[0];","cz q[0],q[1];","h q[0];"],
            true,"OPENQASM 3.0;")),
        ("phase_and_cx",source(&["s q[1];","cx q[1],q[0];","t q[0];"],
            true,"OPENQASM 3.0;")),
        ("builtin_u_zero",source(&["U(0,0,0) q[0];"],
            false,"OPENQASM 3.0;")),
        ("stdlib_u3_twopi",source(&["u3(2*pi,0,0) q[0];"],
            true,"OPENQASM 3.0;")),
    ];
    for (name,src) in &safe{
        assert_eq!(independently_checked_matrix(src).unwrap(),
            native_matrix(src).unwrap(),
            "source→PathSum strict mismatch in accepted stable profile: {name}");
        println!("INDEPENDENT_NATIVE_SAFE_SOURCE case={name} exact=true");
    }
    let mismatches=[
        ("builtin_U_twopi",source(&["U(2*pi,0,0) q[0];"],
            false,"OPENQASM 3.0;")),
        ("stdlib_u3_phi",source(&["u3(0,pi,0) q[0];"],
            true,"OPENQASM 3.0;")),
        ("builtin_U_halfpi",source(&["U(pi/2,0,0) q[0];"],
            false,"OPENQASM 3.0;")),
    ];
    for (name,src) in &mismatches {
        assert_ne!(independently_checked_matrix(src).unwrap(),
            native_matrix(src).unwrap(),
            "previously established strict source mismatch disappeared: {name}");
        println!("INDEPENDENT_NATIVE_STRICT_COUNTEREXAMPLE case={name} exact=true");
    }
    let qasm31=source(&["h q[0];"],true,"OPENQASM 3.1;");
    assert!(independent_parse(&qasm31).is_ok());
    assert!(native_matrix(&qasm31).is_err());
    let native_ctrl=source(&["ctrl @ U(0,pi,0) q[1],q[0];"],
        false,"OPENQASM 3.0;");
    assert!(independent_parse(&native_ctrl).is_ok());
    assert!(native_matrix(&native_ctrl).is_err());
    println!("INDEPENDENT_NATIVE_SAFE_EXACT=5 STRICT_COUNTEREXAMPLES=3");
    println!("INDEPENDENT_NATIVE_SOURCE_ADMISSION_GAPS=2");
}
