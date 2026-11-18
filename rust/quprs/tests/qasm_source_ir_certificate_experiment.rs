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


// Research-only finite Clifford+T local-replay experiment.
// This code is intentionally isolated from the production QASM parser,
// PathSum implementation, solver and public API.
mod phase8_local_step_research {
    use super::source_digest;
    use std::collections::{BTreeMap, BTreeSet};

    type Anf = BTreeSet<u64>;
    type Phase = BTreeMap<u64, u8>;

    #[derive(Clone, Copy, Debug)]
    enum Gate {
        H(usize), X(usize), Cx(usize, usize),
        T(usize), S(usize), Z(usize), Cz(usize, usize), Global(u8),
    }

    #[derive(Clone, Debug, PartialEq, Eq)]
    struct State {
        n: usize,
        paths: usize,
        out: Vec<Anf>,
        phase: Phase,
    }
    #[derive(Clone)]
    struct Claim {
        source_hash: [u8; 32],
        prefixes: Vec<State>,
    }

    fn variable(i: usize) -> Anf {
        BTreeSet::from([1u64 << i])
    }
    fn xor(a: &Anf, b: &Anf) -> Anf {
        let mut result = a.clone();
        for &m in b {
            if !result.insert(m) { result.remove(&m); }
        }
        result
    }
    fn add_phase(dst: &mut Phase, monomial: u64, coefficient: u8) {
        let next = (dst.get(&monomial).copied().unwrap_or(0)
            + coefficient % 8) % 8;
        if next == 0 { dst.remove(&monomial); }
        else { dst.insert(monomial, next); }
    }
    // Exact Boolean parity -> Z8 multilinear lifting.
    // Higher inclusion-exclusion terms vanish modulo 8.
    fn lift8(expr: &Anf) -> Phase {
        let terms: Vec<u64> = expr.iter().copied().collect();
        let mut answer = Phase::new();
        for &a in &terms { add_phase(&mut answer, a, 1); }
        for i in 0..terms.len() {
            for j in i+1..terms.len() {
                add_phase(&mut answer, terms[i] | terms[j], 6);
            }
        }
        for i in 0..terms.len() {
            for j in i+1..terms.len() {
                for k in j+1..terms.len() {
                    add_phase(&mut answer, terms[i] | terms[j] | terms[k], 4);
                }
            }
        }
        answer
    }
    fn initial(n: usize) -> State {
        State {n, paths: 0, out: (0..n).map(variable).collect(),
            phase: Phase::new()}
    }
    fn next(mut state: State, gate: Gate) -> Result<State, String> {
        match gate {
            Gate::H(t) => {
                if t >= state.n || state.n + state.paths >= 63 {
                    return Err("invalid H wire or path limit".into());
                }
                let fresh = 1u64 << (state.n + state.paths);
                for (mon, coeff) in lift8(&state.out[t]) {
                    add_phase(&mut state.phase, mon | fresh, (4 * coeff) % 8);
                }
                state.out[t] = variable(state.n + state.paths);
                state.paths += 1;
            }
            Gate::X(t) => {
                if t >= state.n {return Err("invalid X target".into());}
                state.out[t] = xor(&state.out[t], &BTreeSet::from([0u64]));
            }
            Gate::Cx(c, t) => {
                if c >= state.n || t >= state.n || c == t {
                    return Err("invalid CX operands".into());
                }
                state.out[t] = xor(&state.out[t], &state.out[c]);
            }
            Gate::T(t) | Gate::S(t) | Gate::Z(t) => {
                if t >= state.n {return Err("invalid phase target".into());}
                let factor = match gate {
                    Gate::T(_) => 1, Gate::S(_) => 2, _ => 4
                };
                for (mon, coeff) in lift8(&state.out[t]) {
                    add_phase(&mut state.phase, mon, (factor * coeff) % 8);
                }
            }
            Gate::Cz(c, t) => {
                if c >= state.n || t >= state.n || c == t {
                    return Err("invalid CZ operands".into());
                }
                for (ma, a) in lift8(&state.out[c]) {
                    for (mb, b) in lift8(&state.out[t]) {
                        add_phase(&mut state.phase, ma | mb, (4 * a * b) % 8);
                    }
                }
            }
            Gate::Global(k) => add_phase(&mut state.phase, 0, k % 8),
        }
        Ok(state)
    }

    fn wire(token: &str, n: usize) -> Result<usize, String> {
        let decimal = token.strip_prefix("q[")
            .and_then(|s| s.strip_suffix(']'))
            .ok_or("bad wire syntax")?;
        if decimal.is_empty() || (decimal.starts_with('0') && decimal.len() > 1)
            || !decimal.bytes().all(|c| c.is_ascii_digit()) {
            return Err("noncanonical wire index".into());
        }
        let i: usize = decimal.parse().map_err(|_| "wire overflow")?;
        if i >= n {return Err("wire out of bounds".into());}
        Ok(i)
    }
    // Deliberately closed and versioned source grammar; never invoke
    // production parse_qasm_str or accept a claimed source operation.
    fn parse(source: &str) -> Result<(usize, Vec<Gate>), String> {
        if source.len() > 32768 {return Err("source length cap".into());}
        let lines: Vec<_> = source.lines().map(str::trim)
            .filter(|line| !line.is_empty()).collect();
        if lines.len() < 4 || lines[0] != "OPENQASM 3.0;"
            || lines[1] != "include \"stdgates.inc\";" {
            return Err("unsupported source version/import".into());
        }
        let decimal = lines[2].strip_prefix("qubit[")
            .and_then(|s| s.strip_suffix("] q;"))
            .ok_or("unsupported register declaration")?;
        if decimal.is_empty() || (decimal.len() > 1 && decimal.starts_with('0'))
            || !decimal.bytes().all(|c| c.is_ascii_digit()) {
            return Err("noncanonical qubit count".into());
        }
        let n: usize = decimal.parse().map_err(|_| "qubit count overflow")?;
        if n == 0 || n > 16 || lines.len() > 1027 {
            return Err("source resource limit".into());
        }
        let mut gates = Vec::new();
        for line in &lines[3..] {
            if *line == "gphase(pi/4);" {
                gates.push(Gate::Global(1)); continue;
            }
            let bare = line.strip_suffix(';').ok_or("missing semicolon")?;
            let (op, args) = bare.split_once(' ').ok_or("unsupported gate")?;
            if args.contains(' ') || args.contains('\t') {
                return Err("noncanonical operands".into());
            }
            let gate = match op {
                "h" => Gate::H(wire(args, n)?),
                "x" => Gate::X(wire(args, n)?),
                "t" => Gate::T(wire(args, n)?),
                "s" => Gate::S(wire(args, n)?),
                "z" => Gate::Z(wire(args, n)?),
                "cx" | "cz" => {
                    let (a, b) = args.split_once(',').ok_or("missing two wires")?;
                    let a = wire(a, n)?;
                    let b = wire(b, n)?;
                    if a == b {return Err("overlapping control and target".into());}
                    if op == "cx" {Gate::Cx(a, b)} else {Gate::Cz(a, b)}
                }
                _ => return Err("gate outside exact whitelist".into()),
            };
            gates.push(gate);
        }
        Ok((n, gates))
    }
    fn emit(source: &str) -> Result<Claim, String> {
        let (n, gates) = parse(source)?;
        let mut state = initial(n);
        let mut prefixes = Vec::new();
        for gate in gates {
            state = next(state, gate)?;
            prefixes.push(state.clone());
        }
        Ok(Claim {source_hash: source_digest(source), prefixes})
    }
    fn check(source: &str, claim: &Claim, budget: usize)
        -> Result<Option<State>, String>
    {
        let (n, gates) = parse(source)?;
        if claim.source_hash != source_digest(source) {
            return Err("source digest mismatch".into());
        }
        if claim.prefixes.len() != gates.len() {
            return Err("incomplete step chain".into());
        }
        let cost = gates.len().checked_mul((n + 16) * (n + 16))
            .ok_or("work limit overflow")?;
        if cost > budget {return Ok(None);}
        let mut state = initial(n);
        for (i, gate) in gates.into_iter().enumerate() {
            state = next(state, gate)?;
            if state != claim.prefixes[i] {
                return Err(format!("invalid exact symbolic step {i}"));
            }
        }
        Ok(Some(state))
    }
    fn anf_eval(expr: &Anf, bits: u64) -> usize {
        (expr.iter().filter(|m| bits & **m == **m).count() & 1) as usize
    }
    fn path_multiset(state: &State) -> Vec<BTreeMap<(usize, u8), u32>> {
        let mut result = Vec::new();
        for x in 0..(1usize << state.n) {
            let mut bag = BTreeMap::new();
            for y in 0..(1usize << state.paths) {
                let bits = x as u64 | ((y as u64) << state.n);
                let output = state.out.iter().enumerate()
                    .map(|(i, f)| anf_eval(f, bits) << i).sum();
                let phase = (state.phase.iter()
                    .filter(|(m, _)| bits & **m == **m)
                    .map(|(_, c)| *c as usize).sum::<usize>() % 8) as u8;
                *bag.entry((output, phase)).or_insert(0) += 1;
            }
            result.push(bag);
        }
        result
    }
    // Structurally independent source-gate branch semantics: no ANF or
    // phase polynomial, and no native QuPRS PathSum operations.
    fn oracle_step(
        previous: Vec<BTreeMap<(usize, u8), u32>>, gate: Gate
    ) -> Vec<BTreeMap<(usize, u8), u32>> {
        previous.into_iter().map(|bag| {
            let mut next_bag = BTreeMap::new();
            for ((bits, phase), count) in bag {
                let bit = |i| (bits >> i) & 1;
                let mut push = |out: usize, exp: u8| {
                    *next_bag.entry((out, exp % 8)).or_insert(0) += count;
                };
                match gate {
                    Gate::H(t) => {
                        let z = bit(t) as u8;
                        push(bits & !(1 << t), phase);
                        push(bits | (1 << t), phase + 4 * z);
                    }
                    Gate::X(t) => push(bits ^ (1 << t), phase),
                    Gate::Cx(c,t) => push(bits ^ (bit(c) << t), phase),
                    Gate::T(t) => push(bits, phase + bit(t) as u8),
                    Gate::S(t) => push(bits, phase + (2 * bit(t)) as u8),
                    Gate::Z(t) => push(bits, phase + (4 * bit(t)) as u8),
                    Gate::Cz(c,t) => push(bits, phase + (4 * bit(c) * bit(t)) as u8),
                    Gate::Global(k) => push(bits, phase + k),
                }
            }
            next_bag
        }).collect()
    }
    fn source(n: usize, body: &str) -> String {
        format!("OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[{n}] q;\n{body}")
    }

    #[test]
    fn observed_phase8_h_anf_local_steps_match_exact_branch_oracle() {
        let examples = [
            source(1, "h q[0];\nh q[0];\n"),
            source(1, "h q[0];\nt q[0];\nh q[0];\n"),
            source(2, "cx q[0],q[1];\nt q[1];\n"),
            source(2, "h q[0];\ncx q[0],q[1];\nt q[1];\nh q[1];\n"),
            source(2, "s q[1];\nh q[0];\ncz q[0],q[1];\nh q[0];\n"),
            source(3, "h q[0];\ncx q[0],q[1];\nt q[1];\ncx q[1],q[2];\ns q[2];\n"),
            source(3, "x q[0];\nh q[2];\ncx q[2],q[1];\nt q[1];\nh q[2];\n"),
            source(3, "h q[0];\nh q[1];\ncx q[0],q[2];\nt q[2];\ncz q[1],q[2];\ngphase(pi/4);\n"),
        ];
        let mut prefixes = 0;
        for src in examples {
            let (n, gates) = parse(&src).unwrap();
            let claimed = emit(&src).unwrap();
            assert_eq!(claimed.prefixes.len(), gates.len());
            let full = check(&src, &claimed, 100_000).unwrap().unwrap();
            assert_eq!(full, *claimed.prefixes.last().unwrap());
            let mut exact = (0..(1usize << n)).map(|x| {
                BTreeMap::from([((x, 0u8), 1u32)])
            }).collect();
            for (j, gate) in gates.into_iter().enumerate() {
                exact = oracle_step(exact, gate);
                assert_eq!(path_multiset(&claimed.prefixes[j]), exact);
                prefixes += 1;
            }
        }
        let xor_t = source(2, "cx q[0],q[1];\nt q[1];\n");
        let proof = emit(&xor_t).unwrap();
        assert_eq!(proof.prefixes.last().unwrap().phase.get(&3u64), Some(&6));
        println!("SYMBOLIC_Z8_H_STEPCERT examples=8 prefixes={prefixes} exact_branch_multiset=true");
        println!("SYMBOLIC_Z8_XOR_LIFT pair_coefficient=6 correct=true");
    }

    #[test]
    fn observed_phase8_local_step_rejects_forged_chain_and_resource_claims() {
        let src = source(2, "h q[0];\ncx q[0],q[1];\nt q[1];\n");
        let original = emit(&src).unwrap();
        let mut forgeries = 0;
        let mut a = original.clone();
        a.source_hash[0] ^= 1;
        assert!(check(&src, &a, 100_000).is_err()); forgeries += 1;
        let mut b = original.clone();
        b.prefixes[0].paths = 0;
        assert!(check(&src, &b, 100_000).is_err()); forgeries += 1;
        let mut c = original.clone();
        c.prefixes[2].phase.insert(3, 1);
        assert!(check(&src, &c, 100_000).is_err()); forgeries += 1;
        let mut d = original.clone();
        d.prefixes.pop();
        assert!(check(&src, &d, 100_000).is_err()); forgeries += 1;
        let mut e = original.clone();
        e.prefixes[0].out[0] = variable(0);
        assert!(check(&src, &e, 100_000).is_err()); forgeries += 1;
        assert!(check(&src, &original, 0).unwrap().is_none());
        assert!(parse(&src.replace("OPENQASM 3.0;", "OPENQASM 3.1;")).is_err());
        assert!(parse(&source(2, "U(2*pi,0,0) q[0];\n")).is_err());
        assert!(parse(&source(2, "ctrl @ t q[0],q[1];\n")).is_err());
        assert_eq!(forgeries, 5);
        println!("SYMBOLIC_Z8_H_STEPCERT forgeries_rejected={forgeries} resource_unknown=true unsupported_rejected=true");
    }

    // Independent checker implementation. The claim producer above uses
    // triple inclusion-exclusion; this verifier computes parity through
    // the recurrence a XOR b = a + b - 2ab (mod 8).
    // Neither source parsing nor gate transition calls the producer helpers.
    #[derive(Clone, Copy)]
    struct CheckLimits {
        max_terms: usize,
        max_updates: usize,
        max_paths: usize,
    }
    struct Fuel {
        left: usize,
        max_terms: usize,
    }
    fn checked_phase_update(
        phase: &mut Phase, mon: u64, delta: u8, fuel: &mut Fuel,
    ) -> bool {
        if fuel.left == 0 { return false; }
        fuel.left -= 1;
        let old = phase.get(&mon).copied().unwrap_or(0);
        let new = (old + delta % 8) % 8;
        if new == 0 { phase.remove(&mon); } else { phase.insert(mon, new); }
        phase.len() <= fuel.max_terms
    }
    fn checked_parity_lift(expr: &Anf, fuel: &mut Fuel) -> Option<Phase> {
        // Independent sequential construction: each XOR toggles parity.
        // Charging every generated monomial protects against combinatorial
        // expansion; zero work budget never accepts a proof.
        let mut acc = Phase::new();
        for &mon in expr {
            let old = acc.clone();
            if !checked_phase_update(&mut acc, mon, 1, fuel) { return None; }
            for (&key, &coeff) in &old {
                let negative_twice = (8 - (2 * coeff) % 8) % 8;
                if !checked_phase_update(&mut acc, key | mon, negative_twice, fuel) {
                    return None;
                }
            }
        }
        Some(acc)
    }
    fn independently_read_source(source: &str) -> Result<(usize, Vec<Gate>), String> {
        if source.len() > 32768 { return Err("independent source size cap".into()); }
        let mut statements = source.lines().map(str::trim).filter(|v| !v.is_empty());
        if statements.next() != Some("OPENQASM 3.0;")
            || statements.next() != Some("include \"stdgates.inc\";") {
            return Err("independent source version or scope unsupported".into());
        }
        let register = statements.next().ok_or("missing declared source register")?;
        let number = register.strip_prefix("qubit[")
            .and_then(|v| v.strip_suffix("] q;"))
            .ok_or("invalid register")?;
        if number.is_empty() || (number.len() > 1 && number.starts_with('0'))
            || !number.bytes().all(|v| v.is_ascii_digit()) {
            return Err("invalid register count".into());
        }
        let n: usize = number.parse().map_err(|_| "register overflow")?;
        if n == 0 || n > 16 { return Err("unsupported independent register".into()); }
        fn read_wire(token: &str, width: usize) -> Result<usize, String> {
            let value = token.strip_prefix("q[")
                .and_then(|v| v.strip_suffix(']'))
                .ok_or("invalid indexed qubit")?;
            if value.is_empty() || (value.len() > 1 && value.starts_with('0'))
                || !value.bytes().all(|b| b.is_ascii_digit()) {
                return Err("invalid indexed qubit integer".into());
            }
            let index: usize = value.parse().map_err(|_| "qubit index overflow")?;
            if index >= width { return Err("qubit index out of bounds".into()); }
            Ok(index)
        }
        let mut sequence = Vec::new();
        for statement in statements {
            if sequence.len() == 1024 { return Err("independent source gate cap".into()); }
            let statement = statement.strip_suffix(';').ok_or("missing source terminator")?;
            if statement == "gphase(pi/4)" {
                sequence.push(Gate::Global(1));
                continue;
            }
            let (name, operands) = statement.split_once(' ')
                .ok_or("unknown source statement")?;
            if operands.contains(' ') || operands.contains('\t') {
                return Err("unexpected operands".into());
            }
            let gate = match name {
                "h" => Gate::H(read_wire(operands, n)?),
                "x" => Gate::X(read_wire(operands, n)?),
                "t" => Gate::T(read_wire(operands, n)?),
                "s" => Gate::S(read_wire(operands, n)?),
                "z" => Gate::Z(read_wire(operands, n)?),
                "cx" | "cz" => {
                    let (first, second) = operands.split_once(',')
                        .ok_or("missing binary gate operand")?;
                    let control = read_wire(first, n)?;
                    let target = read_wire(second, n)?;
                    if control == target { return Err("binary gate alias".into()); }
                    if name == "cx" { Gate::Cx(control, target) }
                    else { Gate::Cz(control, target) }
                }
                _ => return Err("source gate outside verifier whitelist".into()),
            };
            sequence.push(gate);
        }
        if sequence.is_empty() {return Err("empty source gate sequence".into());}
        Ok((n, sequence))
    }
    fn independent_replay(
        source: &str, claim: &Claim, limits: CheckLimits,
    ) -> Result<Option<State>, String> {
        let (n, source_gates) = independently_read_source(source)?;
        if source_digest(source) != claim.source_hash {
            return Err("verified source digest disagrees with claim".into());
        }
        if source_gates.len() != claim.prefixes.len() {
            return Err("missing/extra source-linked prefix".into());
        }
        // Validate *all* untrusted prefix encodings before resource fallback.
        // Bounds here are on canonical monomial counts, not serialized bytes.
        for alleged in &claim.prefixes {
            if alleged.n != n || alleged.out.len() != n
                || alleged.paths > 63usize.saturating_sub(n) {
                return Err("noncanonical claimed dimension".into());
            }
            let width = n + alleged.paths;
            let permitted = (1u64 << width) - 1;
            if alleged.out.iter().any(|p| p.iter().any(|m| m & !permitted != 0))
                || alleged.phase.iter().any(|(&m, &c)| m & !permitted != 0 || c == 0 || c >= 8) {
                return Err("noncanonical claimed monomial or coefficient".into());
            }
            let count = alleged.phase.len() + alleged.out.iter().map(|o| o.len()).sum::<usize>();
            if count > limits.max_terms {return Ok(None);}
        }
        let mut fuel = Fuel { left: limits.max_updates, max_terms: limits.max_terms };
        let mut current = State {
            n, paths: 0,
            out: (0..n).map(|i| BTreeSet::from([1u64 << i])).collect(),
            phase: Phase::new(),
        };
        if n > limits.max_terms {return Ok(None);}
        for (index, source_gate) in source_gates.into_iter().enumerate() {
            // All verifier-side mutations and allocations use a separate
            // implementation from the producer (no calls to next/lift8/xor).
            match source_gate {
                Gate::H(t) => {
                    if current.paths >= limits.max_paths || n + current.paths >= 63 {
                        return Ok(None);
                    }
                    let fresh = 1u64 << (n + current.paths);
                    let old_output = current.out[t].clone();
                    // 4·parity ≡ 4·sum(monomials) (mod 8).
                    for mon in old_output {
                        if !checked_phase_update(&mut current.phase, fresh | mon, 4, &mut fuel) {
                            return Ok(None);
                        }
                    }
                    current.out[t] = BTreeSet::from([fresh]);
                    current.paths += 1;
                }
                Gate::X(t) => {
                    if fuel.left == 0 {return Ok(None);}
                    fuel.left -= 1;
                    if !current.out[t].insert(0) {current.out[t].remove(&0);}
                }
                Gate::Cx(c, t) => {
                    let control = current.out[c].clone();
                    for mon in control {
                        if fuel.left == 0 {return Ok(None);}
                        fuel.left -= 1;
                        if !current.out[t].insert(mon) {current.out[t].remove(&mon);}
                        if current.out[t].len() > limits.max_terms {return Ok(None);}
                    }
                }
                Gate::T(t) | Gate::S(t) | Gate::Z(t) => {
                    let factor = match source_gate {
                        Gate::T(_) => 1, Gate::S(_) => 2, Gate::Z(_) => 4, _ => unreachable!(),
                    };
                    let Some(lift) = checked_parity_lift(&current.out[t], &mut fuel) else {
                        return Ok(None);
                    };
                    for (m, coeff) in lift {
                        if !checked_phase_update(
                            &mut current.phase, m, (factor * coeff) % 8, &mut fuel,
                        ) { return Ok(None); }
                    }
                }
                Gate::Cz(c,t) => {
                    // 4·(parity_c)(parity_t) mod8 is just a GF2
                    // convolution at coefficient four, including overlaps.
                    let left = current.out[c].clone();
                    let right = current.out[t].clone();
                    for a in left {
                        for &b in &right {
                            if !checked_phase_update(&mut current.phase, a | b, 4, &mut fuel) {
                                return Ok(None);
                            }
                        }
                    }
                }
                Gate::Global(k) => {
                    if !checked_phase_update(&mut current.phase, 0, k, &mut fuel) {
                        return Ok(None);
                    }
                }
            }
            let state_terms = current.phase.len()
                + current.out.iter().map(|v| v.len()).sum::<usize>();
            if state_terms > limits.max_terms {return Ok(None);}
            if claim.prefixes[index] != current {
                return Err(format!("independent symbolic step mismatch at {index}"));
            }
        }
        Ok(Some(current))
    }
    fn limits() -> CheckLimits {
        CheckLimits { max_terms: 256, max_updates: 50000, max_paths: 24 }
    }

    #[test]
    fn observed_phase8_independent_checker_replays_source_and_triples() {
        let examples = [
            source(2, "h q[0];\ncx q[0],q[1];\nt q[1];\nh q[1];\n"),
            source(3, "h q[0];\ncx q[0],q[1];\ns q[1];\ncz q[0],q[2];\nt q[2];\n"),
            source(4, "cx q[0],q[3];\ncx q[1],q[3];\ncx q[2],q[3];\nt q[3];\n"),
            source(4, "h q[1];\ncx q[1],q[3];\ncx q[0],q[3];\nt q[3];\nh q[3];\n"),
        ];
        let mut prefixes = 0;
        for s in &examples {
            let claim = emit(s).unwrap();
            let expected = claim.prefixes.last().unwrap();
            assert_eq!(independent_replay(s, &claim, limits()).unwrap().unwrap(), *expected);
            prefixes += claim.prefixes.len();
        }
        let triple = emit(&examples[2]).unwrap();
        let phase = &triple.prefixes.last().unwrap().phase;
        assert_eq!(phase.get(&0b111u64), Some(&4));
        assert_eq!(phase.get(&0b11u64), Some(&6));
        println!("INDEPENDENT_Z8_STEPCERT circuits=4 prefixes={prefixes} parity_triple_verified=true");
    }
    #[test]
    fn observed_phase8_independent_replay_scales_structurally_and_fails_closed() {
        let mut body = String::new();
        for t in 0..16 {
            body.push_str(&format!("h q[{t}];\n"));
        }
        for j in 0..112 {
            let t = j % 16;
            let gate = if j % 2 == 0 { "t" } else { "x" };
            body.push_str(&format!("{gate} q[{t}];\n"));
        }
        let large = source(16, &body);
        let claim = emit(&large).unwrap();
        assert_eq!(claim.prefixes.len(), 128);
        assert!(independent_replay(&large, &claim, limits()).unwrap().is_some());
        let mut changed = claim.clone();
        changed.prefixes[12].paths = 2; // wrong intermediate path count
        assert!(independent_replay(&large, &changed, limits()).is_err());
        let mut changed = claim.clone();
        changed.prefixes[27].phase.insert(0, 3);
        assert!(independent_replay(&large, &changed, limits()).is_err());
        let mut changed = claim.clone();
        changed.prefixes[31].out[0].insert(1u64 << 62);
        assert!(independent_replay(&large, &changed, limits()).is_err());
        let mut changed = claim.clone();
        changed.prefixes.pop();
        assert!(independent_replay(&large, &changed, limits()).is_err());
        assert!(independent_replay(&large, &claim, CheckLimits {
            max_terms: 256, max_updates: 0, max_paths: 24,
        }).unwrap().is_none());
        assert!(independent_replay(&large, &claim, CheckLimits {
            max_terms: 2, max_updates: 50000, max_paths: 24,
        }).unwrap().is_none());
        assert!(independent_replay(&large, &claim, CheckLimits {
            max_terms: 256, max_updates: 50000, max_paths: 2,
        }).unwrap().is_none());
        assert!(independent_replay(
            &large.replace("OPENQASM 3.0;", "OPENQASM 3.1;"), &claim, limits(),
        ).is_err());
        println!("INDEPENDENT_Z8_STEPCERT_STRUCTURAL n=16 prefixes=128 exact=true unknown_budgets=3 forged_rejected=4");
    }


    // Source-to-native producer bridge, kept distinct from the independent
    // source decoder and symbolic checker. Observes the *unreduced* real
    // QuPRS PathSum, including exact rational-cycle phase coefficients.
    fn native_prefix_branches(
        source_text: &str, n: usize,
    ) -> Result<(usize, Vec<BTreeMap<(usize,u8),u32>>), String> {
        use quprs::{qasm::parse_qasm_str, PathSum};
        let (ops, parsed_n) = parse_qasm_str(source_text)?;
        if parsed_n != n || n > 3 {
            return Err("native bounded source register mismatch".into());
        }
        let mut native = PathSum::new(n);
        native.set_auto_reduce(false);
        for gate in ops { gate.apply(&mut native, false); }
        let mut paths: Vec<u32> = native.v.path_vars.iter().copied()
            .filter(|&v| v >= n as u32).collect();
        paths.sort_unstable();
        if paths.len() > 8 || paths.iter().any(|&v| v >= 62) {
            return Err("native branch oracle path cap".into());
        }
        let mut result = Vec::new();
        for input in 0..(1usize << n) {
            let mut bag = BTreeMap::new();
            for path_bits in 0..(1usize << paths.len()) {
                let mut bits = input as u64;
                for (index, &variable) in paths.iter().enumerate() {
                    if (path_bits >> index) & 1 == 1 {
                        bits |= 1u64 << variable;
                    }
                }
                let true_mono = |monomial: &[u32]| -> bool {
                    monomial.iter().all(|&v| v < 62 && bits & (1u64 << v) != 0)
                };
                let mut output = 0usize;
                for (q, f) in native.f.functions.iter().enumerate() {
                    if f.iter().fold(false, |old, mon| old ^ true_mono(mon)) {
                        output |= 1usize << q;
                    }
                }
                let mut exp = 0u8;
                for (mon, coefficient) in &native.p.terms {
                    if coefficient.radians.is_some() || !coefficient.symbols.is_empty() {
                        return Err("native phase is outside exact eighth-root domain".into());
                    }
                    if true_mono(mon) {
                        let numerator = (coefficient.constant.numer as i128)
                            .checked_mul(8).ok_or("phase numerator overflow")?;
                        let denominator = coefficient.constant.denom as i128;
                        if denominator == 0 || numerator % denominator != 0 {
                            return Err("native phase is not a Z8 coefficient".into());
                        }
                        exp = ((exp as i128 + numerator / denominator)
                            .rem_euclid(8)) as u8;
                    }
                }
                *bag.entry((output, exp)).or_insert(0u32) += 1;
            }
            result.push(bag);
        }
        Ok((paths.len(),result))
    }
    #[test]
    fn observed_independent_z8_checker_matches_native_unreduced_pathsum_prefixes() {
        let cases: &[&[&str]] = &[
            &["h q[0];", "cx q[0],q[1];"],
            &["cx q[0],q[1];", "t q[1];"],
            &["h q[0];", "t q[0];", "cx q[0],q[1];"],
            &["s q[1];", "h q[0];", "cz q[0],q[1];", "h q[0];"],
        ];
        let mut prefixes = 0;
        for (index, gates) in cases.iter().enumerate() {
            for end in 1..=gates.len() {
                let src = source(2, &(gates[..end].join("\n") + "\n"));
                let claim = emit(&src).expect("supported source should produce certificate");
                let verified = independent_replay(&src, &claim, limits())
                    .expect("independent source verifier")
                    .expect("bounded symbolic proof should be checked");
                let (native_paths, native_bag) = native_prefix_branches(&src, 2)
                    .expect("genuinely native PathSum should parse bounded source");
                assert_eq!(verified.paths,native_paths,
                    "normalization path count mismatch at case={index} prefix={end}");
                assert_eq!(path_multiset(&verified),native_bag,
                    "source-linked exact phase/path branch mismatch at case={index} prefix={end}");
                prefixes += 1;
            }
        }
        println!("INDEPENDENT_Z8_NATIVE_PATHSUM cases={} prefixes={prefixes} exact_unreduced=true",cases.len());
    }


    // Research-only canonical P8C1 proof envelope. The producer exports
    // complete prefixes; the decoder is separately written and validates
    // source provenance, canonical order, per-frame terms and total budget
    // before any semantic admission. It is not a production proof format.
    #[derive(Clone, Copy)]
    struct ProofByteLimits {
        max_bytes: usize,
        max_total_terms: usize,
        symbolic: CheckLimits,
    }
    fn proof_byte_limits() -> ProofByteLimits {
        ProofByteLimits {
            max_bytes: 1 << 20, max_total_terms: 32_768,
            symbolic: CheckLimits {
                max_terms: 256, max_updates: 50_000, max_paths: 24,
            },
        }
    }
    fn serialize_p8c1_untrusted(claim: &Claim) -> Result<Vec<u8>, String> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(b"P8C1");
        let n = claim.prefixes.first().ok_or("empty claim")?.n;
        bytes.push(u8::try_from(n).map_err(|_| "oversized width")?);
        bytes.extend_from_slice(
            &u16::try_from(claim.prefixes.len()).map_err(|_| "too many prefixes")?.to_le_bytes()
        );
        bytes.extend_from_slice(&claim.source_hash);
        for state in &claim.prefixes {
            if state.n != n || state.out.len() != n {
                return Err("producer inconsistent state dimension".into());
            }
            bytes.push(u8::try_from(state.paths).map_err(|_| "oversized path count")?);
            for anf in &state.out {
                bytes.extend_from_slice(
                    &u16::try_from(anf.len()).map_err(|_| "too many ANF terms")?.to_le_bytes()
                );
                for &monomial in anf {
                    bytes.extend_from_slice(&monomial.to_le_bytes());
                }
            }
            bytes.extend_from_slice(
                &u16::try_from(state.phase.len()).map_err(|_| "too many phase terms")?.to_le_bytes()
            );
            for (&monomial, &coefficient) in &state.phase {
                bytes.extend_from_slice(&monomial.to_le_bytes());
                bytes.push(coefficient);
            }
        }
        Ok(bytes)
    }
    struct ProofCursor<'a> {
        bytes: &'a [u8],
        position: usize,
    }
    impl<'a> ProofCursor<'a> {
        fn new(bytes: &'a [u8]) -> Self {
            Self { bytes, position: 0 }
        }
        fn take(&mut self, count: usize) -> Result<&'a [u8], String> {
            let end = self.position.checked_add(count).ok_or("cursor overflow")?;
            let result = self.bytes.get(self.position..end)
                .ok_or("truncated source-bound proof")?;
            self.position = end;
            Ok(result)
        }
        fn byte(&mut self) -> Result<u8, String> {
            Ok(self.take(1)?[0])
        }
        fn short(&mut self) -> Result<usize, String> {
            let data = self.take(2)?;
            Ok(u16::from_le_bytes([data[0],data[1]]) as usize)
        }
        fn word(&mut self) -> Result<u64, String> {
            let data = self.take(8)?;
            Ok(u64::from_le_bytes(
                data.try_into().map_err(|_| "incorrect fixed word")?
            ))
        }
    }
    fn verify_p8c1_serialized(
        source: &str, proof_bytes: &[u8], budget: ProofByteLimits,
    ) -> Result<Option<State>, String> {
        // Admission is independent of the producer's source parser.
        let (n, independent_gates) = independently_read_source(source)?;
        if proof_bytes.len() > budget.max_bytes { return Ok(None); }
        let mut reader = ProofCursor::new(proof_bytes);
        if reader.take(4)? != b"P8C1" {
            return Err("unsupported or forged proof encoding version".into());
        }
        let width = reader.byte()? as usize;
        let steps = reader.short()?;
        let source_hash = reader.take(32)?;
        if width != n || steps != independent_gates.len() {
            return Err("proof register or gate coverage mismatch".into());
        }
        if source_hash != source_digest(source) {
            return Err("proof source bytes/digest mismatch".into());
        }
        let mut claim = Claim {
            source_hash: source_digest(source),
            prefixes: Vec::with_capacity(steps),
        };
        let mut total_terms = 0usize;
        for _ in 0..steps {
            let paths = reader.byte()? as usize;
            let num_vars = n.checked_add(paths).ok_or("path count overflow")?;
            if num_vars >= 63 {
                return Err("invalid symbolic variable width".into());
            }
            let legal_bits = (1u64 << num_vars) - 1;
            let mut out = Vec::with_capacity(n);
            let mut frame_terms = 0usize;
            for _ in 0..n {
                let count = reader.short()?;
                frame_terms = frame_terms.checked_add(count)
                    .ok_or("frame monomial count overflow")?;
                total_terms = total_terms.checked_add(count)
                    .ok_or("total monomial count overflow")?;
                if frame_terms > budget.symbolic.max_terms
                    || total_terms > budget.max_total_terms {
                    return Ok(None);
                }
                let mut anf = BTreeSet::new();
                let mut previous = None;
                for _ in 0..count {
                    let monomial = reader.word()?;
                    if monomial & !legal_bits != 0
                        || previous.is_some_and(|p| monomial <= p) {
                        return Err("noncanonical ANF term ordering or variable".into());
                    }
                    anf.insert(monomial);
                    previous = Some(monomial);
                }
                out.push(anf);
            }
            let count = reader.short()?;
            frame_terms = frame_terms.checked_add(count)
                .ok_or("frame phase count overflow")?;
            total_terms = total_terms.checked_add(count)
                .ok_or("total phase count overflow")?;
            if frame_terms > budget.symbolic.max_terms
                || total_terms > budget.max_total_terms {
                return Ok(None);
            }
            let mut phase = Phase::new();
            let mut previous = None;
            for _ in 0..count {
                let monomial = reader.word()?;
                let coefficient = reader.byte()?;
                if monomial & !legal_bits != 0 || coefficient == 0 || coefficient >= 8
                    || previous.is_some_and(|p| monomial <= p) {
                    return Err("noncanonical Z8 phase ordering/coefficient".into());
                }
                phase.insert(monomial,coefficient);
                previous=Some(monomial);
            }
            claim.prefixes.push(State {n, paths, out, phase});
        }
        if reader.position != proof_bytes.len() {
            return Err("trailing unbound proof payload".into());
        }
        // This is a separate checker implementation, not producer next().
        independent_replay(source,&claim,budget.symbolic)
    }
    #[test]
    fn observed_phase8_serialized_proof_decodes_and_replays_native_prefixes() {
        let examples = [
            source(2, "h q[0];\ncx q[0],q[1];\nt q[1];\n"),
            source(3, "h q[0];\ncx q[0],q[1];\nt q[1];\ncz q[1],q[2];\n"),
            source(4, "cx q[0],q[3];\ncx q[1],q[3];\ncx q[2],q[3];\nt q[3];\n"),
        ];
        let mut total_steps = 0usize;
        let mut bytes = 0usize;
        for example in examples {
            let producer = emit(&example).unwrap();
            let canonical = serialize_p8c1_untrusted(&producer).unwrap();
            let replayed = verify_p8c1_serialized(&example,&canonical,proof_byte_limits())
                .unwrap().unwrap();
            assert_eq!(replayed,*producer.prefixes.last().unwrap());
            assert_eq!(serialize_p8c1_untrusted(&producer).unwrap(),canonical);
            total_steps += producer.prefixes.len();
            bytes += canonical.len();
        }
        println!("P8C1_SERIALIZED_NATIVE_EXACT samples=3 steps={total_steps} bytes_total={bytes} replay=true");
    }
    #[test]
    fn observed_phase8_serialized_proof_rejects_forgery_and_unknown_budget() {
        let src=source(2,"x q[0];\ncx q[0],q[1];\nt q[1];\n");
        let claim=emit(&src).unwrap();
        let proof=serialize_p8c1_untrusted(&claim).unwrap();
        assert!(verify_p8c1_serialized(&src,&proof,proof_byte_limits()).unwrap().is_some());
        let mut rejects=0;
        let mut m=proof.clone();m[0]=b'X';
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let mut m=proof.clone();m[4]=4;
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let mut m=proof.clone();m[5]=0;
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let mut m=proof.clone();m[7]^=1;
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let mut m=proof.clone();m.pop();
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let mut m=proof.clone();m.push(0);
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        // The first X prefix has a two-monomial ANF output, represented
        // as canonical 0,1 u64 terms. Duplicate and descending order fail.
        let mut m=proof.clone();m[50..58].copy_from_slice(&0u64.to_le_bytes());
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let mut m=proof.clone();m[42..50].copy_from_slice(&9u64.to_le_bytes());
        assert!(verify_p8c1_serialized(&src,&m,proof_byte_limits()).is_err());
        rejects+=1;
        let different=source(2,"x q[0];\ncx q[0],q[1];\ns q[1];\n");
        assert!(verify_p8c1_serialized(&different,&proof,proof_byte_limits()).is_err());
        rejects+=1;
        assert!(verify_p8c1_serialized(&src,&proof,ProofByteLimits {
            max_bytes:proof.len()-1,..proof_byte_limits()
        }).unwrap().is_none());
        assert!(verify_p8c1_serialized(&src,&proof,ProofByteLimits {
            max_total_terms:1,..proof_byte_limits()
        }).unwrap().is_none());
        assert!(verify_p8c1_serialized(&src,&proof,ProofByteLimits {
            symbolic:CheckLimits { max_updates:0,..proof_byte_limits().symbolic },
            ..proof_byte_limits()
        }).unwrap().is_none());
        println!("P8C1_SERIALIZED_NEGATIVE rejects={rejects} unknown_limits=3 no_unchecked_proof=true");
    }


    #[test]
    fn observed_p8c1_every_single_bit_mutation_is_fail_closed() {
        // Deterministic exhaustive 1-bit flips of the *entire serialized
        // proof*, including header, length, digest, ANF and phase entries.
        // Mutations may reject or return UNKNOWN, but never certify.
        let source_text = source(2, "h q[0];\ncx q[0],q[1];\nt q[1];\n");
        let bytes = serialize_p8c1_untrusted(&emit(&source_text).unwrap()).unwrap();
        assert!(verify_p8c1_serialized(&source_text,&bytes,proof_byte_limits())
            .unwrap().is_some());
        let mut fail_closed = 0usize;
        let mut unknown = 0usize;
        for byte_index in 0..bytes.len() {
            for bit_index in 0..8 {
                let mut forged = bytes.clone();
                forged[byte_index] ^= 1u8 << bit_index;
                match verify_p8c1_serialized(&source_text,&forged,proof_byte_limits()) {
                    Ok(Some(_)) => panic!(
                        "single-bit forged proof accepted at byte {byte_index} bit {bit_index}"
                    ),
                    Ok(None) => {fail_closed += 1; unknown += 1;},
                    Err(_) => {fail_closed += 1;},
                }
            }
        }
        println!("P8C1_MUTATION_EXHAUSTIVE original_bytes={} single_bit_changes={} rejected_or_unknown={} unknown={} accepted=0",
            bytes.len(), bytes.len()*8, fail_closed, unknown);
        assert_eq!(fail_closed,bytes.len()*8);
    }
    #[test]
    fn observed_p8c1_large_structural_128_step_size_and_admission() {
        use std::time::Instant;
        let mut body = String::new();
        for wire in 0..16 {
            body.push_str(&format!("h q[{wire}];\n"));
        }
        for j in 0..112 {
            let wire = j % 16;
            body.push_str(&format!(
                "{} q[{wire}];\n", if j % 2 == 0 { "t" } else { "x" }
            ));
        }
        let source_text = source(16,&body);
        let claim = emit(&source_text).unwrap();
        assert_eq!(claim.prefixes.len(),128);
        let bytes = serialize_p8c1_untrusted(&claim).unwrap();
        let started = Instant::now();
        let last = verify_p8c1_serialized(&source_text,&bytes,proof_byte_limits())
            .unwrap().unwrap();
        let wall_us = started.elapsed().as_micros();
        assert_eq!(&last,claim.prefixes.last().unwrap());
        assert!(bytes.len() < (1 << 20));
        let input_limit = ProofByteLimits {
            max_bytes: bytes.len()-1,..proof_byte_limits()
        };
        assert!(verify_p8c1_serialized(&source_text,&bytes,input_limit)
            .unwrap().is_none());
        let terms_limit = ProofByteLimits {
            max_total_terms: 64,..proof_byte_limits()
        };
        assert!(verify_p8c1_serialized(&source_text,&bytes,terms_limit)
            .unwrap().is_none());
        println!("P8C1_SIZE_PILOT n=16 steps=128 proof_bytes={} source_bytes={} checker_wall_us={} exact=true unknown_resource_cases=2 nonbenchmark=true",
            bytes.len(),source_text.len(),wall_us);
    }


    #[test]
    fn observed_p8c1_exports_cross_binary_fixtures_when_requested() {
        // An opt-in test fixture producer. The standalone CLI has no access
        // to this module, its types, or its implementation at compile time.
        let Ok(target) = std::env::var("P8C1_FIXTURE_DIR") else {
            println!("P8C1_STANDALONE_FIXTURE_EXPORT=disabled");
            return;
        };
        std::fs::create_dir_all(&target).unwrap();
        let mut structural = String::new();
        for wire in 0..16 {
            structural.push_str(&format!("h q[{wire}];\n"));
        }
        for j in 0..112 {
            let wire = j % 16;
            structural.push_str(&format!(
                "{} q[{wire}];\n",if j%2==0 {"t"}else{"x"}
            ));
        }
        let cases = [
            ("h-cx-t",source(2,"h q[0];\ncx q[0],q[1];\nt q[1];\n")),
            ("cx-t-parity",source(2,"cx q[0],q[1];\nt q[1];\n")),
            ("mixed-3q",source(3,
                "h q[0];\ncx q[0],q[1];\nt q[1];\ncz q[1],q[2];\n")),
            ("structural-16q",source(16,&structural)),
        ];
        let mut total_bytes=0usize;
        for (name,src) in cases {
            let claim=emit(&src).unwrap();
            let proof=serialize_p8c1_untrusted(&claim).unwrap();
            assert!(verify_p8c1_serialized(&src,&proof,proof_byte_limits())
                .unwrap().is_some());
            std::fs::write(format!("{target}/{name}.qasm"),src).unwrap();
            std::fs::write(format!("{target}/{name}.p8c1"),&proof).unwrap();
            if name=="h-cx-t" {
                let mut bad=proof.clone();
                bad[0]^=0x01;
                std::fs::write(format!("{target}/forged.p8c1"),bad).unwrap();
            }
            total_bytes+=proof.len();
        }
        println!("P8C1_CROSS_BINARY_EXPORTED fixtures=4 proof_bytes_total={total_bytes}");
    }

}
