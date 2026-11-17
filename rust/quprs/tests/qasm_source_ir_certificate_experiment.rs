//! Research-only source-linked diagonal control proof certificates.
//!
//! This test checks a deliberately narrow subset of OPENQASM 3.0, not the
//! general QASM grammar and not production parser acceptance. Every source
//! operation is a positive controlled I/Z target with an exact phase in
//! {1, i, -1, -i}. A Z4 multilinear normal form is checked against an
//! independently enumerated computational-basis oracle at small sizes.
//!
//! The source bytes must come from a trusted caller: SHA-256 protects equality
//! to those supplied bytes, and is not proof of origin or authenticity.

use sha2::{Digest, Sha256};
use std::{hint::black_box,time::Instant};

const MAX_QUBITS: usize=16;
const MAX_STEPS: usize=4096;
const MAX_SOURCE_BYTES:usize=512*1024;
const CERT_MAGIC: &[u8;4]=b"QSC1";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OpKind { U=1, U3=2, GPhase=3 }
impl OpKind {
    fn from_byte(b:u8)->Result<Self,String>{
        match b {1=>Ok(Self::U),2=>Ok(Self::U3),3=>Ok(Self::GPhase),
            _=>Err("unknown certificate operation kind".into())}
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct SourceOp {
    kind:OpKind,control:u8,target:Option<u8>,
    phase_quarters:u8,target_z:bool,
}
#[derive(Clone,Debug,PartialEq,Eq)]
struct ProofCertificate {
    digest:[u8;32],
    qubits:u8,
    steps:Vec<SourceOp>,
}
fn source_digest(source:&str)->[u8;32]{
    let output=Sha256::digest(source.as_bytes());
    let mut out=[0u8;32];out.copy_from_slice(&output);out
}
fn parse_wire(s:&str,n:usize)->Result<u8,String>{
    let digits=s.strip_prefix("q[")
        .and_then(|v|v.strip_suffix(']'))
        .ok_or("wire must be q[<index>]")?;
    if digits.is_empty() || (digits.len()>1&&digits.starts_with('0'))
        || !digits.bytes().all(|x|x.is_ascii_digit()){
        return Err("wire index is not canonical decimal".into());
    }
    let val:usize=digits.parse().map_err(|_|"wire overflow")?;
    if val>=n{return Err("wire out of bounds".into())}
    Ok(val as u8)
}
fn parse_op(line:&str,n:usize,stdlib:bool)->Result<SourceOp,String>{
    let instruction=line.strip_prefix("ctrl @ ")
        .and_then(|s|s.strip_suffix(';'))
        .ok_or("unsupported controlled statement")?;
    let (gate,operand_text)=instruction.split_once(' ')
        .ok_or("missing indexed operands")?;
    if operand_text.contains(' ') ||operand_text.contains('\t'){
        return Err("noncanonical operand layout".into());
    }
    let wires=operand_text.split(',').collect::<Vec<_>>();
    let (kind,phase_quarters,target_z,needs_target)=match gate{
        "U(2*pi,0,0)"=>(OpKind::U,0,false,true),
        "U(0,pi,0)"=>(OpKind::U,0,true,true),
        "u3(2*pi,0,0)" if stdlib=>(OpKind::U3,2,false,true),
        "u3(0,pi,0)" if stdlib=>(OpKind::U3,3,true,true),
        "gphase(pi)"=>(OpKind::GPhase,2,false,false),
        "gphase(pi/2)"=>(OpKind::GPhase,1,false,false),
        "gphase(-pi/2)"=>(OpKind::GPhase,3,false,false),
        _=>return Err("gate or angle outside exact source whitelist".into())
    };
    if wires.len()!=if needs_target{2}else{1} {
        return Err("wrong control/target arity".into());
    }
    let control=parse_wire(wires[0],n)?;
    let target=if needs_target {
        let target=parse_wire(wires[1],n)?;
        if control==target{return Err("control and target overlap".into())}
        Some(target)
    } else {None};
    Ok(SourceOp{kind,control,target,phase_quarters,target_z})
}
fn parse_source(source:&str)->Result<ProofCertificate,String>{
    if source.len()>MAX_SOURCE_BYTES {return Err("source byte limit".into())}
    let lines=source.lines().map(str::trim).filter(|x|!x.is_empty()).collect::<Vec<_>>();
    if lines.len()<3||lines[0]!="OPENQASM 3.0;"{
        return Err("unsupported source version".into());
    }
    let mut cursor=1;
    let stdlib=if lines.get(cursor)==Some(&"include \"stdgates.inc\";"){
        cursor+=1;true
    }else{false};
    let declaration=lines.get(cursor).ok_or("missing register declaration")?;
    let size_literal=declaration.strip_prefix("qubit[")
        .and_then(|x|x.strip_suffix("] q;"))
        .ok_or("unsupported source register")?;
    if size_literal.is_empty() ||(size_literal.len()>1&&size_literal.starts_with('0'))
        || !size_literal.bytes().all(|b|b.is_ascii_digit()) {
        return Err("noncanonical register size".into());
    }
    let n:usize=size_literal.parse().map_err(|_|"register size overflow")?;
    if !(2..=MAX_QUBITS).contains(&n){
        return Err("source qubit count outside bounded checker".into())
    }
    cursor+=1;
    let body=&lines[cursor..];
    if body.is_empty()||body.len()>MAX_STEPS{return Err("source operation limit".into())}
    let mut steps=Vec::with_capacity(body.len());
    for &line in body {steps.push(parse_op(line,n,stdlib)?);}
    Ok(ProofCertificate{digest:source_digest(source),qubits:n as u8,steps})
}
fn encode_certificate(cert:&ProofCertificate)->Vec<u8>{
    let mut out=Vec::with_capacity(41+cert.steps.len()*5);
    out.extend_from_slice(CERT_MAGIC);
    out.extend_from_slice(&cert.digest);
    out.push(cert.qubits);
    out.extend_from_slice(&(cert.steps.len() as u32).to_le_bytes());
    for step in &cert.steps {
        out.push(step.kind as u8);
        out.push(step.control);
        out.push(step.target.unwrap_or(255));
        out.push(step.phase_quarters);
        out.push(u8::from(step.target_z));
    }
    out
}
fn decode_certificate(bytes:&[u8])->Result<ProofCertificate,String>{
    if bytes.len()<41 ||bytes.get(0..4)!=Some(CERT_MAGIC.as_slice()){
        return Err("unknown or truncated certificate envelope".into())
    }
    let mut digest=[0u8;32];digest.copy_from_slice(&bytes[4..36]);
    let qubits=bytes[36];
    if !(2..=MAX_QUBITS as u8).contains(&qubits){
        return Err("certificate qubit limit".into())
    }
    let count=u32::from_le_bytes(bytes[37..41].try_into()
        .map_err(|_|"missing certificate length")?) as usize;
    if count==0 ||count>MAX_STEPS ||bytes.len()!=41+count*5 {
        return Err("truncated, oversized or trailing certificate bytes".into())
    }
    let mut steps=Vec::with_capacity(count);
    for chunk in bytes[41..].chunks_exact(5){
        let kind=OpKind::from_byte(chunk[0])?;
        let control=chunk[1];
        let target=if chunk[2]==255{None}else{Some(chunk[2])};
        let phase_quarters=chunk[3];
        let target_z=match chunk[4]{0=>false,1=>true,_=>return Err("bad operator bit".into())};
        if control>=qubits ||target.is_some_and(|t|t>=qubits||t==control)
            ||phase_quarters>=4{
            return Err("invalid certificate control, target or phase".into())
        }
        if (kind==OpKind::GPhase)!=(target.is_none())
           || (kind==OpKind::GPhase &&target_z) {
            return Err("gate type and operands do not agree".into())
        }
        steps.push(SourceOp{kind,control,target,phase_quarters,target_z});
    }
    Ok(ProofCertificate{digest,qubits,steps})
}
fn verify_certificate(source:&str,bytes:&[u8])->Result<ProofCertificate,String>{
    let supplied=decode_certificate(bytes)?;
    if source_digest(source)!=supplied.digest {
        return Err("source bytes do not match certificate digest".into())
    }
    let recomputed=parse_source(source)?;
    if supplied!=recomputed {
        return Err("claimed source IR differs from checker source replay".into())
    }
    Ok(recomputed)
}

/// Z4 polynomial f(x)=sum a_c x_c + sum b_ct x_c x_t, with x in {0,1}^n.
/// All admitted controlled source gates are diagonal and evaluate as i^f(x).
#[derive(Clone,Debug,PartialEq,Eq)]
struct DiagonalNormalForm {
    n:usize,singles:Vec<u8>,pairs:Vec<u8>,
}
fn normal_form(cert:&ProofCertificate)->DiagonalNormalForm{
    let n=cert.qubits as usize;
    let mut singles=vec![0u8;n];
    let mut pairs=vec![0u8;n*n];
    for step in &cert.steps{
        let c=step.control as usize;
        singles[c]=(singles[c]+step.phase_quarters)%4;
        if step.target_z {
            let t=step.target.expect("source replay validated target") as usize;
            let (a,b)=if c<t{(c,t)}else{(t,c)};
            pairs[a*n+b]=(pairs[a*n+b]+2)%4;
        }
    }
    DiagonalNormalForm{n,singles,pairs}
}
fn from_form_for_basis(form:&DiagonalNormalForm,basis:usize)->u8{
    let mut out=0u8;
    for i in 0..form.n{
        if basis & (1usize<<i)!=0 {out=(out+form.singles[i])%4;}
        for j in i+1..form.n{
            if basis & (1usize<<i)!=0 && basis & (1usize<<j)!=0{
                out=(out+form.pairs[i*form.n+j])%4;
            }
        }
    }
    out
}
fn direct_basis_oracle(cert:&ProofCertificate,basis:usize)->u8 {
    let mut out=0u8;
    for step in &cert.steps {
        if basis & (1usize<<step.control)!=0{
            out=(out+step.phase_quarters)%4;
            if step.target_z
              && step.target.is_some_and(|t|basis & (1usize<<t)!=0) {
                out=(out+2)%4;
            }
        }
    }
    out
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum Property {StrictEq,PhaseEq,UnitaryChannelEq,EffectRiskBound}
fn verify_source_miter(
    source_a:&str,proof_a:&[u8],source_b:&str,proof_b:&[u8],
    property:Property
)->Result<bool,String>{
    let a=verify_certificate(source_a,proof_a)?;
    let b=verify_certificate(source_b,proof_b)?;
    if a.qubits!=b.qubits {return Err("different register dimensions".into())}
    if property==Property::EffectRiskBound{return Ok(false)}
    // All accepted gates fix |0...0> with phase 1, so a possible
    // global miter scalar is forced to 1. Thus, in this *narrow fragment*
    // PhaseEq and unitary ChannelEq coincide with StrictEq.
    Ok(normal_form(&a)==normal_form(&b))
}
fn literal_step(idx:usize,n:usize)->String{
    let c=idx%n;
    let target=(c+1+(idx/n)%(n-1))%n;
    let target=if target==c {(c+1)%n}else{target};
    match idx%7{
        0=>format!("ctrl @ U(2*pi,0,0) q[{c}],q[{target}];"),
        1=>format!("ctrl @ u3(2*pi,0,0) q[{c}],q[{target}];"),
        2=>format!("ctrl @ U(0,pi,0) q[{c}],q[{target}];"),
        3=>format!("ctrl @ u3(0,pi,0) q[{c}],q[{target}];"),
        4=>format!("ctrl @ gphase(pi/2) q[{c}];"),
        5=>format!("ctrl @ gphase(-pi/2) q[{c}];"),
        _=>format!("ctrl @ gphase(pi) q[{c}];")
    }
}
fn make_source(n:usize,steps:usize)->String{
    let mut out=format!(
       "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[{n}] q;\n"
    );
    for i in 0..steps{
        out.push_str(&literal_step(i,n));
        out.push('\n');
    }
    out
}
#[test]
fn observed_source_ir_roundtrip_and_forgery_rejection(){
    let source=make_source(4,21);
    let cert=parse_source(&source).unwrap();
    let bytes=encode_certificate(&cert);
    assert_eq!(decode_certificate(&bytes).unwrap(),cert);
    assert_eq!(verify_certificate(&source,&bytes).unwrap(),cert);
    assert_eq!(bytes.len(),41+21*5);

    // Source provenance mutation and reordered operations must fail even when
    // a pair of diagonal gates would commute as matrices.
    let mut shuffled=source.lines().map(String::from).collect::<Vec<_>>();
    shuffled.swap(3,4);
    assert!(verify_certificate(&format!("{}\n",shuffled.join("\n")),&bytes).is_err());
    let mut claimed=cert.clone();
    claimed.digest=source_digest(&source);
    claimed.steps.swap(0,1);
    assert!(verify_certificate(&source,&encode_certificate(&claimed)).is_err());

    let mut forged=cert.clone();
    forged.steps[1].phase_quarters=0;
    assert!(verify_certificate(&source,&encode_certificate(&forged)).is_err());
    forged=cert.clone();forged.steps[1].control=(forged.steps[1].control+1)%4;
    assert!(verify_certificate(&source,&encode_certificate(&forged)).is_err());
    forged=cert.clone();forged.steps[2].target_z=false;
    assert!(verify_certificate(&source,&encode_certificate(&forged)).is_err());
    forged=cert.clone();forged.qubits=3;
    assert!(verify_certificate(&source,&encode_certificate(&forged)).is_err());

    let mut tampered=bytes.clone();
    tampered[0]=b'X';
    assert!(decode_certificate(&tampered).is_err());
    tampered=bytes.clone();tampered[41]=100;
    assert!(decode_certificate(&tampered).is_err());
    tampered=bytes.clone();tampered[43]=255;
    assert!(decode_certificate(&tampered).is_err());
    tampered=bytes.clone();tampered[44]=4;
    assert!(decode_certificate(&tampered).is_err());
    tampered=bytes.clone();tampered[45]=2;
    assert!(decode_certificate(&tampered).is_err());
    tampered=bytes.clone();tampered.pop();
    assert!(decode_certificate(&tampered).is_err());
    tampered=bytes.clone();tampered.push(0);
    assert!(decode_certificate(&tampered).is_err());

    let invalid=[
        source.replace("OPENQASM 3.0;","OPENQASM 3.1;"),
        source.replace("stdgates.inc","other.inc"),
        source.replace("include \"stdgates.inc\";\n",""),
        source.replace("ctrl @","negctrl @"),
        source.replace("u3(2*pi,0,0)","U3(2*pi,0,0)"),
        source.replace("U(2*pi,0,0)","U(pi/2,0,0)"),
        source.replace("q[0],q[1]","q[0],q[0]"),
        source.replace("qubit[4] q;","qubit[17] q;"),
        source.replace("qubit[4] q;","qubit[04] q;"),
        source.replace("ctrl @ gphase(pi)","x"),
        "OPENQASM 3.0;\nqubit[2] q;\n".to_string()
    ];
    let mut rejected=0;
    for item in invalid {
        if parse_source(&item).is_err(){rejected+=1;}
    }
    assert_eq!(rejected,11);
    println!("SOURCE_IR_CERT_BOUND_BYTES={} SOURCE_BYTES={} STEPS={}",
        bytes.len(),source.len(),cert.steps.len());
    println!("SOURCE_IR_CERT_MUTATION_REJECTED=13");
    println!("SOURCE_IR_INVALID_SOURCE_REJECTED={rejected}");
}
#[test]
fn observed_source_ir_polynomial_miter_matches_independent_basis_oracle(){
    let mut total_checks=0usize;
    for (n,steps) in [(2,24),(4,80),(8,192),(12,384)]{
        let source=make_source(n,steps);
        let cert=parse_source(&source).unwrap();
        let bytes=encode_certificate(&cert);
        let verified=verify_certificate(&source,&bytes).unwrap();
        let form=normal_form(&verified);
        for basis in 0..(1usize<<n){
            assert_eq!(from_form_for_basis(&form,basis),
                direct_basis_oracle(&verified,basis),
                "Z4 normal form must equal independent direct product");
            total_checks+=1;
        }
        let identical=verify_source_miter(
            &source,&bytes,&source,&bytes,Property::StrictEq
        ).unwrap();
        assert!(identical);
        assert!(verify_source_miter(
            &source,&bytes,&source,&bytes,Property::PhaseEq
        ).unwrap());
        assert!(verify_source_miter(
            &source,&bytes,&source,&bytes,Property::UnitaryChannelEq
        ).unwrap());
        assert!(!verify_source_miter(
            &source,&bytes,&source,&bytes,Property::EffectRiskBound
        ).unwrap());
        // A distinct relative phase is caught even if target-only channels
        // would be equal when the source loses its control provenance.
        let other=format!(
            "OPENQASM 3.0;\nqubit[{n}] q;\nctrl @ gphase(pi/2) q[0];\n"
        );
        let other_proof=encode_certificate(&parse_source(&other).unwrap());
        let blank=format!(
            "OPENQASM 3.0;\nqubit[{n}] q;\nctrl @ U(2*pi,0,0) q[0],q[1];\n"
        );
        let blank_proof=encode_certificate(&parse_source(&blank).unwrap());
        assert!(!verify_source_miter(
            &blank,&blank_proof,&other,&other_proof,Property::StrictEq
        ).unwrap());
        assert!(!verify_source_miter(
            &blank,&blank_proof,&other,&other_proof,Property::PhaseEq
        ).unwrap());
        println!("SOURCE_IR_Z4_CROSSCHECK n={n} steps={steps} basis={} exact=true",
            1usize<<n);
    }
    println!("SOURCE_IR_EXACT_BASIS_CROSSCHECKS={total_checks}");
}
#[test]
fn observed_source_ir_certificate_cost_profile(){
    // Timings are observational with a shared source-specific task, *not*
    // benchmarks against production QuPRS or a general dense matrix engine.
    for (n,steps) in [(2,32),(4,128),(8,256),(12,512),(16,512)]{
        let source=make_source(n,steps);
        let cert=parse_source(&source).unwrap();
        let bytes=encode_certificate(&cert);
        let repeat=20usize;
        let start=Instant::now();
        for _ in 0..repeat {
            let verified=verify_certificate(black_box(&source),black_box(&bytes))
                .unwrap();
            let polynomial=normal_form(&verified);
            black_box(polynomial);
        }
        let local_ns=(start.elapsed().as_nanos()/repeat as u128) as u64;
        // The materialized-diagonal baseline replays every literal source
        // operation per basis vector.  n=16 is intentionally not materialized:
        // the local checker has no dependence on 2^n basis enumeration.
        let diagonal=if n<=12 {
            let begin=Instant::now();
            let reference=(0..(1usize<<n))
                .map(|basis|direct_basis_oracle(&cert,basis))
                .collect::<Vec<_>>();
            let elapsed=begin.elapsed().as_nanos() as u64;
            assert_eq!(reference.len(),1usize<<n);
            for (basis,phase) in reference.iter().enumerate(){
                assert_eq!(*phase,from_form_for_basis(&normal_form(&cert),basis));
            }
            Some(elapsed)
        }else{None};
        println!(
            "SOURCE_IR_COST n={n} steps={steps} source_bytes={} certificate_bytes={} \
             local_check_ns={local_ns} diagonal_enumerate_ns={} diagonal_entries={} \
             local_excludes_dense=true",
            source.len(),bytes.len(),
            diagonal.map_or("SKIPPED".into(),|v|v.to_string()),
            if n<=12 {(1usize<<n).to_string()}else{"NOT_MATERIALIZED".into()},
        );
    }
}


fn reversed_source_with_same_diagonal_semantics(source:&str)->String {
    let lines=source.lines().collect::<Vec<_>>();
    assert!(lines.len()>=4);
    let mut out=lines[..3].join("\n");
    out.push('\n');
    for &line in lines[3..].iter().rev() {
        out.push_str(line);
        out.push('\n');
    }
    out
}
fn median_ns(mut samples:Vec<u128>)->u128{
    samples.sort_unstable();
    samples[samples.len()/2]
}
#[test]
fn observed_source_ir_same_task_equivalence_cost_comparison(){
    // Both paths solve the same strict *source-circuit equality* question:
    // (A) replay two source-bound certificates, normalize each and compare;
    // (B) parse two sources and compare exact action on every basis input.
    //
    // B does not verify signed source certificate envelopes, while A does:
    // therefore the numbers are not fully matched TCBs or an end-to-end
    // benchmark, and no solver speedup claim follows. All operations are
    // diagonal, so reverse source order preserves exact operator semantics.
    for (n,steps) in [(2,32usize),(4,128),(8,256),(12,512),(16,512)]{
        let source_a=make_source(n,steps);
        let source_b=reversed_source_with_same_diagonal_semantics(&source_a);
        assert_ne!(source_a,source_b);
        let cert_a=encode_certificate(&parse_source(&source_a).unwrap());
        let cert_b=encode_certificate(&parse_source(&source_b).unwrap());
        assert!(verify_source_miter(&source_a,&cert_a,&source_b,&cert_b,
            Property::StrictEq).unwrap());
        let repeats=if n==12 {5}else{9};
        let mut compact_samples=Vec::with_capacity(repeats);
        let mut diagonal_samples=Vec::with_capacity(repeats);
        for _ in 0..repeats{
            let begin=Instant::now();
            let checked_a=verify_certificate(
                black_box(&source_a),black_box(&cert_a)).unwrap();
            let checked_b=verify_certificate(
                black_box(&source_b),black_box(&cert_b)).unwrap();
            let equality=normal_form(&checked_a)==normal_form(&checked_b);
            black_box(equality);
            assert!(equality);
            compact_samples.push(begin.elapsed().as_nanos());
            if n<=12{
                let begin=Instant::now();
                let checked_a=parse_source(black_box(&source_a)).unwrap();
                let checked_b=parse_source(black_box(&source_b)).unwrap();
                let equal=(0..(1usize<<n)).all(|basis|
                    direct_basis_oracle(&checked_a,basis)
                      == direct_basis_oracle(&checked_b,basis)
                );
                black_box(equal);
                assert!(equal);
                diagonal_samples.push(begin.elapsed().as_nanos());
            }
        }
        let normalized_ns=median_ns(compact_samples);
        let enumeration_ns=if diagonal_samples.is_empty(){None}
            else{Some(median_ns(diagonal_samples))};
        println!(
            "SOURCE_IR_EQUIVALENCE_BENCH n={n} steps={steps} \
              source_a_bytes={} source_b_bytes={} \
              cert_a_bytes={} cert_b_bytes={} \
              source_bound_normal_form_median_ns={normalized_ns} \
              source_parsed_basis_enumeration_median_ns={} \
              basis_tested={} semantically_equal=true",
            source_a.len(),source_b.len(),cert_a.len(),cert_b.len(),
            enumeration_ns.map_or("SKIPPED".to_owned(),|x|x.to_string()),
            if n<=12 {(1usize<<n).to_string()}else{"NOT_ENUMERATED".into()},
        );
    }
}


// An independently replayed *symbolic* local step checker for the bounded
// diagonal Z4 fragment. No 2^n dense matrix, no native PathSum builder.
// A claimed transition is checked against the source-derived operation,
// not against another producer-supplied operation list.
#[derive(Clone)]
struct ClaimedZ4StepTrace {
    source_digest:[u8;32],
    prefixes:Vec<DiagonalNormalForm>,
}
fn independent_z4_step(
    before:&DiagonalNormalForm,gate:&SourceOp
)->Result<DiagonalNormalForm,String>{
    let n=before.n;
    let c=gate.control as usize;
    if c>=n{return Err("control outside symbolic normal form".into());}
    let mut after=before.clone();
    after.singles[c]=(after.singles[c]+gate.phase_quarters)%4;
    if gate.target_z{
        let t=gate.target.ok_or("Z phase without target")? as usize;
        if t>=n||t==c{return Err("invalid target for controlled phase".into());}
        let lo=c.min(t);let hi=c.max(t);
        after.pairs[lo*n+hi]=(after.pairs[lo*n+hi]+2)%4;
    }else if gate.target.is_none() && gate.kind!=OpKind::GPhase{
        return Err("missing target for source gate".into());
    }
    Ok(after)
}
fn emit_z4_step_trace(source:&str)->Result<ClaimedZ4StepTrace,String>{
    let cert=parse_source(source)?;
    let n=cert.qubits as usize;
    let mut form=DiagonalNormalForm{
        n,singles:vec![0;n],pairs:vec![0;n*n]
    };
    let mut prefixes=Vec::with_capacity(cert.steps.len());
    for gate in &cert.steps{
        form=independent_z4_step(&form,gate)?;
        prefixes.push(form.clone());
    }
    Ok(ClaimedZ4StepTrace{
        source_digest:cert.digest,prefixes
    })
}
fn verify_z4_step_trace(
    source:&str,claim:&ClaimedZ4StepTrace,max_work:usize
)->Result<Option<DiagonalNormalForm>,String>{
    let cert=parse_source(source)?;
    let n=cert.qubits as usize;
    if claim.source_digest!=cert.digest{
        return Err("symbolic trace source digest mismatch".into());
    }
    if claim.prefixes.len()!=cert.steps.len(){
        return Err("symbolic trace incomplete/extra prefixes".into());
    }
    // Deterministic checker-side cost bound, before allocating step matrices.
    let work=cert.steps.len().checked_mul(
        n.checked_mul(n).ok_or("symbolic cost overflow")?
    ).ok_or("symbolic cost overflow")?;
    if work>max_work{return Ok(None);}
    let mut form=DiagonalNormalForm{
        n,singles:vec![0;n],pairs:vec![0;n*n]
    };
    for (i,gate) in cert.steps.iter().enumerate(){
        form=independent_z4_step(&form,gate)?;
        let alleged=&claim.prefixes[i];
        if alleged.n!=n||alleged.singles.len()!=n
            ||alleged.pairs.len()!=n*n{
            return Err(format!("malformed symbolic step {i}"));
        }
        if alleged!=&form{
            return Err(format!("symbolic step mismatch at gate {i}"));
        }
    }
    Ok(Some(form))
}
#[test]
fn observed_symbolic_z4_step_certificate_matches_independent_basis_oracle(){
    for n in [2usize,4,8,16]{
        let src=make_source(n,128);
        let cert=parse_source(&src).unwrap();
        let proof=emit_z4_step_trace(&src).unwrap();
        let form=verify_z4_step_trace(&src,&proof,128*n*n)
            .unwrap().unwrap();
        assert_eq!(form,normal_form(&cert));
        // A fixed basis sample is an independent direct gate-evaluation
        // oracle. It is not a proof for all assignments, which follows
        // instead from the exact Z4 coefficient replay.
        for basis in 0..(1usize<<n.min(8)){
            assert_eq!(from_form_for_basis(&form,basis),
                direct_basis_oracle(&cert,basis));
        }
        assert!(verify_z4_step_trace(&src,&proof,0).unwrap().is_none());
        println!("SYMBOLIC_Z4_STEPCERT n={n} steps=128 verified=true resource_unknown=true");
    }
}
#[test]
fn observed_symbolic_z4_step_certificate_rejects_hidden_cancelled_errors(){
    // Two equal controlled gphase(pi) gates cancel in Z4. A corrupted
    // first prefix could be masked by a correct final normal form.
    let src="OPENQASM 3.0;\nqubit[2] q;\nctrl @ gphase(pi) q[1];\nctrl @ gphase(pi) q[1];\n";
    let mut claim=emit_z4_step_trace(src).unwrap();
    assert_eq!(claim.prefixes.last().unwrap().singles[1],0);
    claim.prefixes[0].singles[1]=0; // wrong first prefix
    assert!(verify_z4_step_trace(src,&claim,100).is_err());
    let mut claim=emit_z4_step_trace(src).unwrap();
    claim.prefixes.pop();
    assert!(verify_z4_step_trace(src,&claim,100).is_err());
    let mut claim=emit_z4_step_trace(src).unwrap();
    claim.source_digest[0]^=1;
    assert!(verify_z4_step_trace(src,&claim,100).is_err());
    let mut claim=emit_z4_step_trace(src).unwrap();
    claim.prefixes[0].pairs[0]=1;
    assert!(verify_z4_step_trace(src,&claim,100).is_err());
    println!("SYMBOLIC_Z4_STEPCERT_HIDDEN_FINAL_ERROR_CAUGHT=true");
    println!("SYMBOLIC_Z4_STEPCERT_FORGERIES_REJECTED=4");
}
