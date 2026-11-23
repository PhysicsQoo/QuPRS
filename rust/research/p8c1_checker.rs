//! Standalone, std-only, research-grade P8C1 proof checker.
//! No QuPRS imports, producer implementation, solver, or Cargo dependency.
//! This is a restricted source-bound symbolic replay experiment, NOT
//! general OpenQASM conformance or a certified quantum property verdict.
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::process::ExitCode;
#[path = "p8c1_two_copy_wmc.rs"]
mod two_copy_wmc;
#[path = "p8c1_two_copy_cnf.rs"]
mod two_copy_cnf;
#[path = "p8c1_two_copy_structural.rs"]
mod two_copy_structural;
#[path = "p8c1_two_copy_count_trace.rs"]
mod two_copy_count_trace;
#[path = "p8c1_two_copy_count_dag.rs"]
mod two_copy_count_dag;
#[path = "p8c1_count_to_gram.rs"]
mod count_to_gram;
#[cfg(test)]
#[path = "p8c1_dense_oracle.rs"]
mod dense_oracle;
#[path = "p8c1_f8c1_chain.rs"]
mod f8c1_chain;
#[path = "p8c1_f8g1_property.rs"]
mod f8g1_property;

const MAX_SOURCE_BYTES: usize = 32_768;
const MAX_PROOF_BYTES: usize = 1 << 20;
const MAX_STEPS: usize = 1024;
const MAX_TOTAL_TERMS: usize = 32_768;
const MAX_FRAME_TERMS: usize = 256;
const MAX_PATHS: usize = 24;
const MAX_UPDATES: usize = 50_000;

type Anf = BTreeSet<u64>;
type Phase = BTreeMap<u64, u8>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Error {
    InvalidSource,
    UnsupportedSource,
    InvalidProof,
    UnknownResource,
}
impl Error {
    fn label(self) -> &'static str {
        match self {
            Self::InvalidSource => "INVALID_SOURCE",
            Self::UnsupportedSource => "UNSUPPORTED_SOURCE",
            Self::InvalidProof => "INVALID_PROOF",
            Self::UnknownResource => "UNKNOWN_RESOURCE",
        }
    }
    fn exit_code(self) -> u8 {
        match self {
            Self::InvalidSource => 2,
            Self::UnsupportedSource => 3,
            Self::InvalidProof => 4,
            Self::UnknownResource => 5,
        }
    }
}
type Check<T> = Result<T, Error>;

#[derive(Debug, Clone, Copy)]
enum Gate {
    H(usize), X(usize), Cx(usize, usize), T(usize), S(usize),
    Z(usize), Cz(usize, usize), Global,
}
#[derive(Debug, Clone, PartialEq, Eq)]
struct State {
    n: usize,
    paths: usize,
    outputs: Vec<Anf>,
    phase: Phase,
}
struct Fuel {
    remaining: usize,
}
impl Fuel {
    fn charge(&mut self) -> Check<()> {
        if self.remaining == 0 {
            return Err(Error::UnknownResource);
        }
        self.remaining -= 1;
        Ok(())
    }
}
fn read_limited(path: &str, cap: usize, on_io: Error) -> Check<Vec<u8>> {
    let file = std::fs::File::open(path).map_err(|_| on_io)?;
    let mut data = Vec::new();
    file.take((cap as u64) + 1)
        .read_to_end(&mut data).map_err(|_| on_io)?;
    if data.len() > cap {
        return Err(Error::UnknownResource);
    }
    Ok(data)
}
// Independent SHA-256 implementation, with FIPS 180-4 known-vector tests.
fn sha256(data: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    ];
    let mut h: [u32; 8] = [
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19,
    ];
    let mut bytes = data.to_vec();
    let bit_length = (data.len() as u64).wrapping_mul(8);
    bytes.push(0x80);
    while bytes.len() % 64 != 56 { bytes.push(0); }
    bytes.extend_from_slice(&bit_length.to_be_bytes());
    for block in bytes.chunks_exact(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes(block[4*i..4*i+4].try_into().unwrap());
        }
        for i in 16..64 {
            let s0 = w[i-15].rotate_right(7)^w[i-15].rotate_right(18)^(w[i-15]>>3);
            let s1 = w[i-2].rotate_right(17)^w[i-2].rotate_right(19)^(w[i-2]>>10);
            w[i] = w[i-16].wrapping_add(s0).wrapping_add(w[i-7]).wrapping_add(s1);
        }
        let mut x=h;
        for i in 0..64 {
            let s1=x[4].rotate_right(6)^x[4].rotate_right(11)^x[4].rotate_right(25);
            let ch=(x[4]&x[5])^(!x[4]&x[6]);
            let t1=x[7].wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0=x[0].rotate_right(2)^x[0].rotate_right(13)^x[0].rotate_right(22);
            let maj=(x[0]&x[1])^(x[0]&x[2])^(x[1]&x[2]);
            let t2=s0.wrapping_add(maj);
            x=[t1.wrapping_add(t2),x[0],x[1],x[2],x[3].wrapping_add(t1),x[4],x[5],x[6]];
        }
        for i in 0..8 {h[i]=h[i].wrapping_add(x[i]);}
    }
    let mut digest=[0u8;32];
    for (i,item) in h.iter().enumerate() {
        digest[4*i..4*i+4].copy_from_slice(&item.to_be_bytes());
    }
    digest
}
fn canonical_number(s: &str) -> Check<usize> {
    if s.is_empty() || (s.len()>1 && s.starts_with('0'))
        || !s.bytes().all(|b| b.is_ascii_digit()) {
        return Err(Error::InvalidSource);
    }
    s.parse().map_err(|_|Error::InvalidSource)
}
fn parse_wire(s: &str,n:usize) -> Check<usize> {
    let inner=s.strip_prefix("q[")
        .and_then(|x| x.strip_suffix(']')).ok_or(Error::InvalidSource)?;
    let index=canonical_number(inner)?;
    if index>=n {return Err(Error::InvalidSource);}
    Ok(index)
}
fn parse_source(source: &[u8]) -> Check<(usize,Vec<Gate>)> {
    if source.len()>MAX_SOURCE_BYTES {return Err(Error::UnknownResource);}
    let text=std::str::from_utf8(source).map_err(|_|Error::InvalidSource)?;
    let mut lines=text.lines().map(str::trim).filter(|s|!s.is_empty());
    match lines.next() {
        Some("OPENQASM 3.0;")=>{},
        Some(_)=>return Err(Error::UnsupportedSource),
        None=>return Err(Error::InvalidSource),
    };
    if lines.next()!=Some("include \"stdgates.inc\";") {
        return Err(Error::UnsupportedSource);
    }
    let register=lines.next().ok_or(Error::InvalidSource)?;
    let count=register.strip_prefix("qubit[")
        .and_then(|s|s.strip_suffix("] q;")).ok_or(Error::InvalidSource)?;
    let n=canonical_number(count)?;
    if n==0 {return Err(Error::InvalidSource);}
    if n>16 {return Err(Error::UnsupportedSource);}
    let mut gates=Vec::new();
    for line in lines {
        if gates.len() >= MAX_STEPS {return Err(Error::UnknownResource);}
        let gate=if line=="gphase(pi/4);" {
            Gate::Global
        } else {
            let bare=line.strip_suffix(';').ok_or(Error::InvalidSource)?;
            let (name,args)=bare.split_once(' ').ok_or(Error::InvalidSource)?;
            if args.contains(char::is_whitespace) {
                return Err(Error::InvalidSource);
            }
            match name {
                "h"=>Gate::H(parse_wire(args,n)?),
                "x"=>Gate::X(parse_wire(args,n)?),
                "t"=>Gate::T(parse_wire(args,n)?),
                "s"=>Gate::S(parse_wire(args,n)?),
                "z"=>Gate::Z(parse_wire(args,n)?),
                "cx" | "cz" => {
                    let (lhs,rhs)=args.split_once(',').ok_or(Error::InvalidSource)?;
                    let a=parse_wire(lhs,n)?;
                    let b=parse_wire(rhs,n)?;
                    if a==b {return Err(Error::InvalidSource);}
                    if name=="cx" {Gate::Cx(a,b)} else {Gate::Cz(a,b)}
                }
                _=>return Err(Error::UnsupportedSource),
            }
        };
        gates.push(gate);
    }
    if gates.is_empty() {return Err(Error::InvalidSource);}
    Ok((n,gates))
}
fn phase_add(out:&mut Phase,key:u64,add:u8,fuel:&mut Fuel) -> Check<()> {
    fuel.charge()?;
    let old=out.get(&key).copied().unwrap_or(0);
    let next=(old + add%8)%8;
    if next==0 {out.remove(&key);} else {out.insert(key,next);}
    if out.len()>MAX_FRAME_TERMS {return Err(Error::UnknownResource);}
    Ok(())
}
fn lift_parity(anf:&Anf,fuel:&mut Fuel) -> Check<Phase> {
    let mut phase=Phase::new();
    for &monomial in anf {
        let prior=phase.clone();
        phase_add(&mut phase,monomial,1,fuel)?;
        for (old_key,old_coeff) in prior {
            let coefficient=(8-(2*old_coeff)%8)%8;
            phase_add(&mut phase,old_key|monomial,coefficient,fuel)?;
        }
    }
    Ok(phase)
}
fn xor_insert(set:&mut Anf,monomial:u64,fuel:&mut Fuel) -> Check<()> {
    fuel.charge()?;
    if !set.insert(monomial) {set.remove(&monomial);}
    if set.len()>MAX_FRAME_TERMS {return Err(Error::UnknownResource);}
    Ok(())
}
fn evolve(state:&mut State,gate:Gate,fuel:&mut Fuel) -> Check<()> {
    match gate {
        Gate::H(t)=>{
            if state.paths >= MAX_PATHS || state.n+state.paths>=63 {
                return Err(Error::UnknownResource);
            }
            let fresh=1u64 << (state.n+state.paths);
            for &m in &state.outputs[t] {
                phase_add(&mut state.phase,m|fresh,4,fuel)?;
            }
            state.outputs[t]=BTreeSet::from([fresh]);
            state.paths+=1;
        }
        Gate::X(t)=>xor_insert(&mut state.outputs[t],0,fuel)?,
        Gate::Cx(c,t)=>{
            let old=state.outputs[c].clone();
            for mon in old {xor_insert(&mut state.outputs[t],mon,fuel)?;}
        }
        Gate::T(t) | Gate::S(t) | Gate::Z(t)=>{
            let k=match gate {Gate::T(_)=>1,Gate::S(_)=>2,_=>4};
            let lifted=lift_parity(&state.outputs[t],fuel)?;
            for (m,c) in lifted {phase_add(&mut state.phase,m,(k*c)%8,fuel)?;}
        }
        Gate::Cz(c,t)=>{
            let left=state.outputs[c].clone();
            let right=state.outputs[t].clone();
            for a in left {for &b in &right {
                phase_add(&mut state.phase,a|b,4,fuel)?;
            }}
        }
        Gate::Global=>phase_add(&mut state.phase,0,1,fuel)?,
    }
    let size=state.phase.len()+state.outputs.iter().map(BTreeSet::len).sum::<usize>();
    if size>MAX_FRAME_TERMS {return Err(Error::UnknownResource);}
    Ok(())
}
struct Cursor<'a> {
    input:&'a [u8],
    at:usize,
}
impl<'a> Cursor<'a> {
    fn new(input:&'a [u8])->Self {Self {input,at:0}}
    fn bytes(&mut self,n:usize)->Check<&'a [u8]> {
        let end=self.at.checked_add(n).ok_or(Error::InvalidProof)?;
        let part=self.input.get(self.at..end).ok_or(Error::InvalidProof)?;
        self.at=end;
        Ok(part)
    }
    fn u8(&mut self)->Check<u8>{Ok(self.bytes(1)?[0])}
    fn u16(&mut self)->Check<usize>{
        let b=self.bytes(2)?;
        Ok(u16::from_le_bytes([b[0],b[1]]) as usize)
    }
    fn i64(&mut self)->Check<i64>{
        Ok(i64::from_le_bytes(self.bytes(8)?.try_into().map_err(|_|Error::InvalidProof)?))
    }
    fn u64(&mut self)->Check<u64>{
        let b=self.bytes(8)?;
        Ok(u64::from_le_bytes(b.try_into().map_err(|_|Error::InvalidProof)?))
    }
}
fn read_termset(reader:&mut Cursor<'_>,width:usize,aggregate:&mut usize,
    local:&mut usize)->Check<Anf>
{
    let count=reader.u16()?;
    *aggregate=aggregate.checked_add(count).ok_or(Error::UnknownResource)?;
    *local=local.checked_add(count).ok_or(Error::UnknownResource)?;
    if *aggregate>MAX_TOTAL_TERMS || *local>MAX_FRAME_TERMS {
        return Err(Error::UnknownResource);
    }
    let allowed=(1u64<<width)-1;
    let mut previous=None;
    let mut out=BTreeSet::new();
    for _ in 0..count {
        let mon=reader.u64()?;
        if mon&!allowed!=0 || previous.is_some_and(|p|mon<=p) {
            return Err(Error::InvalidProof);
        }
        out.insert(mon);
        previous=Some(mon);
    }
    Ok(out)
}
fn read_phase(reader:&mut Cursor<'_>,width:usize,aggregate:&mut usize,
    local:&mut usize)->Check<Phase>
{
    let count=reader.u16()?;
    *aggregate=aggregate.checked_add(count).ok_or(Error::UnknownResource)?;
    *local=local.checked_add(count).ok_or(Error::UnknownResource)?;
    if *aggregate>MAX_TOTAL_TERMS || *local>MAX_FRAME_TERMS {
        return Err(Error::UnknownResource);
    }
    let allowed=(1u64<<width)-1;
    let mut previous=None;
    let mut out=Phase::new();
    for _ in 0..count {
        let mon=reader.u64()?;
        let c=reader.u8()?;
        if mon&!allowed!=0 || c==0 || c>=8 ||
            previous.is_some_and(|p|mon<=p) {
            return Err(Error::InvalidProof);
        }
        out.insert(mon,c);
        previous=Some(mon);
    }
    Ok(out)
}
fn replay_state(source:&[u8],proof:&[u8])->Check<(usize,State)> {
    // The caller caps both files while reading. This second guard permits
    // direct calls with already-owned byte slices and fails closed.
    if source.len()>MAX_SOURCE_BYTES || proof.len()>MAX_PROOF_BYTES {
        return Err(Error::UnknownResource);
    }
    let (n,gates)=parse_source(source)?;
    let mut reader=Cursor::new(proof);
    if reader.bytes(4)?!=b"P8C1" {return Err(Error::InvalidProof);}
    if reader.u8()? as usize!=n {return Err(Error::InvalidProof);}
    if reader.u16()?!=gates.len() {return Err(Error::InvalidProof);}
    if reader.bytes(32)?!=sha256(source) {return Err(Error::InvalidProof);}
    let mut state=State {
        n,paths:0,
        outputs:(0..n).map(|i|BTreeSet::from([1u64<<i])).collect(),
        phase:Phase::new(),
    };
    let mut aggregate=0usize;
    let mut fuel=Fuel {remaining:MAX_UPDATES};
    for gate in gates.iter().copied() {
        let paths=reader.u8()? as usize;
        if paths>MAX_PATHS || n+paths>=63 {
            return Err(Error::InvalidProof);
        }
        let width=n+paths;
        let mut local=0usize;
        let mut outputs=Vec::with_capacity(n);
        for _ in 0..n {
            outputs.push(read_termset(&mut reader,width,&mut aggregate,&mut local)?);
        }
        let phase=read_phase(&mut reader,width,&mut aggregate,&mut local)?;
        // No Vec<Claim>, no whole-proof state allocation. The checker
        // processes one bounded prefix at a time.
        evolve(&mut state,gate,&mut fuel)?;
        if paths!=state.paths || outputs!=state.outputs || phase!=state.phase {
            return Err(Error::InvalidProof);
        }
    }
    if reader.at!=proof.len() {return Err(Error::InvalidProof);}
    Ok((gates.len(),state))
}
fn check(source:&[u8],proof:&[u8])->Check<usize> {
    replay_state(source,proof).map(|(steps,_)|steps)
}

// SPB1: deliberately restricted *computational basis* reachability/risk
// semantics. P and B are bit masks over basis indices, not arbitrary quantum
// subspaces. Only n <= 3 and H path count <= 8 are admitted for this pilot.
// This is not a general property verifier or authoritative QASM frontend.
const MAX_SPEC_BYTES: usize = 256;
const P8S1_BYTES: usize = 4 + 32 + 32 + 32;
#[derive(Debug, Clone, Copy)]
struct BasisRiskSpec {
    n: usize,
    pre_mask: u64,
    bad_mask: u64,
    delta_num: i128,
    delta_den: i128,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PropertyVerdict {
    ScopedSatisfied,
    ScopedViolated { input_basis: usize },
}
fn exact_hex_mask(value: &str) -> Check<u64> {
    let h=value.strip_prefix("0x").ok_or(Error::InvalidSource)?;
    if h.len()!=16 || !h.bytes().all(|b|b.is_ascii_hexdigit()
        && (!b.is_ascii_alphabetic() || b.is_ascii_lowercase())) {
        return Err(Error::InvalidSource);
    }
    u64::from_str_radix(h,16).map_err(|_|Error::InvalidSource)
}
fn parse_basis_spec(data: &[u8]) -> Check<BasisRiskSpec> {
    if data.len()>MAX_SPEC_BYTES {return Err(Error::UnknownResource);}
    let text=std::str::from_utf8(data).map_err(|_|Error::InvalidSource)?;
    let mut lines=text.split_terminator('\n');
    if lines.next()!=Some("SPB1") {return Err(Error::UnsupportedSource);}
    let q=lines.next().and_then(|s|s.strip_prefix("n="))
        .ok_or(Error::InvalidSource)?;
    let n=canonical_number(q)?;
    if n==0 || n>3 {return Err(Error::UnsupportedSource);}
    let pm=lines.next().and_then(|s|s.strip_prefix("basis_pre="))
        .ok_or(Error::InvalidSource)?;
    let bm=lines.next().and_then(|s|s.strip_prefix("basis_bad="))
        .ok_or(Error::InvalidSource)?;
    let delta=lines.next().and_then(|s|s.strip_prefix("delta="))
        .ok_or(Error::InvalidSource)?;
    if lines.next().is_some() || !text.ends_with('\n') {
        return Err(Error::InvalidSource);
    }
    let pre_mask=exact_hex_mask(pm)?;
    let bad_mask=exact_hex_mask(bm)?;
    let allowed=(1u64 << (1usize << n))-1;
    if pre_mask==0 || bad_mask==0 || ((pre_mask|bad_mask)&!allowed)!=0 {
        return Err(Error::InvalidSource);
    }
    let (num,den)=delta.split_once('/').ok_or(Error::InvalidSource)?;
    let a=canonical_number(num)? as i128;
    let b=canonical_number(den)? as i128;
    if b==0 || a>b || b>65_535 {return Err(Error::InvalidSource);}
    // Fractions are in reduced canonical form (0/1 mandatory for zero).
    fn gcd(mut a:i128,mut b:i128)->i128{
        while b!=0 {let rem=a%b;a=b;b=rem;}
        a
    }
    if gcd(a,b)!=1 {return Err(Error::InvalidSource);}
    Ok(BasisRiskSpec {n,pre_mask,bad_mask,delta_num:a,delta_den:b})
}
fn proof_bound_bytes(source:&[u8],proof:&[u8],spec:&[u8]) -> [u8;P8S1_BYTES] {
    let mut bound=[0u8;P8S1_BYTES];
    bound[..4].copy_from_slice(b"P8S1");
    bound[4..36].copy_from_slice(&sha256(source));
    bound[36..68].copy_from_slice(&sha256(spec));
    bound[68..100].copy_from_slice(&sha256(proof));
    bound
}
// Returns true iff C + D sqrt(2) <= 0, using only integer arithmetic.
// Cap on n/path count and fraction denominator ensures no i128 overflow.
// Exact sign in Z[sqrt(2)], but an i128 overflow is UNKNOWN, never
// a panic, a wrapped comparison, or a claimed proof verdict.
fn checked_nonpositive_quadratic(c:i128,d:i128)->Check<bool>{
    if c==0 {return Ok(d<=0);}
    if d==0 {return Ok(c<=0);}
    if c>0 && d>0 {return Ok(false);}
    if c<0 && d<0 {return Ok(true);}
    let c_squared=c.checked_mul(c).ok_or(Error::UnknownResource)?;
    let twice_d_squared=d.checked_mul(d)
        .and_then(|v|v.checked_mul(2)).ok_or(Error::UnknownResource)?;
    Ok(if c>0 {c_squared<=twice_d_squared} else {twice_d_squared<=c_squared})
}
fn checked_nonnegative_quadratic(c:i128,d:i128)->Check<bool>{
    Ok(checked_nonpositive_quadratic(
        c.checked_neg().ok_or(Error::UnknownResource)?,
        d.checked_neg().ok_or(Error::UnknownResource)?
    )?)
}
fn evaluate_monomial(mask:u64,bits:u64)->bool { bits&mask==mask }
// Computes exact squared norms in Z[sqrt(2)] / 2^h. Every path
// contributes one eighth root of unity; no floating point or tolerances.
fn exact_bad_probability(state:&State,input:usize,bad_mask:u64)->Check<(i128,i128)> {
    if state.n>3 || state.paths>8 {return Err(Error::UnknownResource);}
    let size=1usize << state.n;
    let mut freqs=vec![[0i128;8];size];
    for y in 0..(1usize << state.paths) {
        let bits=input as u64 | ((y as u64) << state.n);
        let mut out=0usize;
        for (index,terms) in state.outputs.iter().enumerate() {
            let bit=terms.iter().filter(|&&mon|evaluate_monomial(mon,bits)).count()%2;
            out |= bit<<index;
        }
        let phase=state.phase.iter()
            .filter(|(mon,_)| evaluate_monomial(**mon,bits))
            .map(|(_,coeff)|*coeff as usize).sum::<usize>()%8;
        freqs[out][phase]+=1;
    }
    let(mut A,mut B)=(0i128,0i128);
    for (output,counts) in freqs.iter().enumerate() {
        if (bad_mask >> output)&1==0 {continue;}
        for k in 0..8 {
            A+=counts[k]*counts[k];
            for l in k+1..8 {
                let diff=l-k;
                match diff {
                    1|7 => B+=counts[k]*counts[l],
                    3|5 => B-=counts[k]*counts[l],
                    4 => A-=2*counts[k]*counts[l],
                    _=>{},
                }
            }
        }
    }
    Ok((A,B))
}
fn verify_spb1_property(
    source:&[u8],proof:&[u8],spec_bytes:&[u8],bound:&[u8]
)->Check<PropertyVerdict>{
    if spec_bytes.len()>MAX_SPEC_BYTES {return Err(Error::UnknownResource);}
    if bound.len()!=P8S1_BYTES || bound[..4]!=*b"P8S1" {
        return Err(Error::InvalidProof);
    }
    if bound[4..36]!=sha256(source) || bound[36..68]!=sha256(spec_bytes)
        || bound[68..100]!=sha256(proof) {
        return Err(Error::InvalidProof);
    }
    let spec=parse_basis_spec(spec_bytes)?;
    let (_,state)=replay_state(source,proof)?;
    if state.n!=spec.n {return Err(Error::InvalidProof);}
    if state.paths>8 {return Err(Error::UnknownResource);}
    for input in 0..(1usize<<spec.n) {
        if (spec.pre_mask >> input)&1==0 {continue;}
        let (A,B)=exact_bad_probability(&state,input,spec.bad_mask)?;
        // risk = (A+B sqrt(2))/2^paths, compare to rational delta.
        let c=spec.delta_den*A-spec.delta_num*(1i128<<state.paths);
        let d=spec.delta_den*B;
        if !checked_nonpositive_quadratic(c,d)? {
            return Ok(PropertyVerdict::ScopedViolated{input_basis:input});
        }
    }
    Ok(PropertyVerdict::ScopedSatisfied)
}

// SCG1 / P8G1 are deliberately DISTINCT from SPB1 / P8S1.
// SCG1 quantifies over *all normalized coherent states* in the span
// of exactly TWO selected computational-basis input vectors.
// It is not a general arbitrary-rank/density-operator specification.
const P8G1_BYTES:usize=176;
#[derive(Debug,Clone,Copy)]
struct CoherentSpanSpec {
    n:usize, pre_mask:u64, bad_mask:u64, delta_num:i128, delta_den:i128,
    first:usize,second:usize,
}
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
struct CoherentGram {
    n:u8,h:u8,first:u8,second:u8,bad_mask:u64,
    diag0:(i64,i64),diag1:(i64,i64),off:[i64;4],
}
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
enum CoherentVerdict {
    ScopedSatisfied,
    ScopedViolated{reason:&'static str},
}
fn parse_scg1_spec(data:&[u8])->Check<CoherentSpanSpec>{
    if data.len()>MAX_SPEC_BYTES{return Err(Error::UnknownResource);}
    let text=std::str::from_utf8(data).map_err(|_|Error::InvalidSource)?;
    let mut lines=text.split_terminator('\n');
    if lines.next()!=Some("SCG1"){return Err(Error::UnsupportedSource);}
    let n=canonical_number(lines.next()
        .and_then(|s|s.strip_prefix("n=")).ok_or(Error::InvalidSource)?)?;
    if n==0||n>3{return Err(Error::UnsupportedSource);}
    let pre_mask=exact_hex_mask(lines.next()
        .and_then(|s|s.strip_prefix("span_basis=")).ok_or(Error::InvalidSource)?)?;
    let bad_mask=exact_hex_mask(lines.next()
        .and_then(|s|s.strip_prefix("basis_bad=")).ok_or(Error::InvalidSource)?)?;
    let fraction=lines.next()
        .and_then(|s|s.strip_prefix("delta=")).ok_or(Error::InvalidSource)?;
    if lines.next().is_some()||!text.ends_with('\n'){
        return Err(Error::InvalidSource);
    }
    let valid=(1u64 << (1usize<<n))-1;
    if pre_mask.count_ones()!=2 || bad_mask==0 ||
        (pre_mask|bad_mask)&!valid!=0 {
        return Err(Error::InvalidSource);
    }
    let(a,b)=fraction.split_once('/').ok_or(Error::InvalidSource)?;
    let numerator=canonical_number(a)? as i128;
    let denominator=canonical_number(b)? as i128;
    if denominator==0 || numerator>denominator || denominator>65535{
        return Err(Error::InvalidSource);
    }
    let(mut r,mut t)=(numerator,denominator);
    while t!=0{let remainder=r%t;r=t;t=remainder;}
    if r!=1{return Err(Error::InvalidSource);}
    let mut indices=(0..(1usize<<n)).filter(|i|pre_mask&(1u64<<i)!=0);
    let first=indices.next().ok_or(Error::InvalidSource)?;
    let second=indices.next().ok_or(Error::InvalidSource)?;
    Ok(CoherentSpanSpec{
        n,pre_mask,bad_mask,delta_num:numerator,delta_den:denominator,first,second,
    })
}
fn path_histogram(state:&State,input:usize)->Check<Vec<[i128;8]>>{
    if state.n>3||state.paths>8{return Err(Error::UnknownResource);}
    let mut output=vec![[0i128;8];1usize<<state.n];
    for y in 0..(1usize<<state.paths){
        let bits=(input as u64)|((y as u64)<<state.n);
        let mut out=0usize;
        for(index,terms)in state.outputs.iter().enumerate(){
            let parity=terms.iter().fold(false,|acc,&mon|acc^evaluate_monomial(mon,bits));
            if parity{out|=1usize<<index;}
        }
        let phase=state.phase.iter()
            .filter(|(&mon,_)|evaluate_monomial(mon,bits))
            .map(|(_,c)|*c as usize).sum::<usize>()%8;
        output[out][phase]+=1;
    }
    Ok(output)
}
fn checked_i64(value:i128)->Check<i64>{
    i64::try_from(value).map_err(|_|Error::UnknownResource)
}
fn path_coherent_gram(
    state:&State,first:usize,second:usize,bad_mask:u64
)->Check<CoherentGram>{
    if state.n>3||state.paths>8{return Err(Error::UnknownResource);}
    if first>=1usize<<state.n||second>=1usize<<state.n||first>=second {
        return Err(Error::InvalidSource);
    }
    let left=path_histogram(state,first)?;
    let right=path_histogram(state,second)?;
    let(mut diag0,mut diag1)=((0i128,0i128),(0i128,0i128));
    let mut cross=[0i128;8];
    for output in 0..left.len(){
        if bad_mask&(1u64<<output)==0{continue;}
        // Exact pairwise path interference; intentionally different from
        // the dense oracle's cyclotomic polynomial-norm implementation.
        for k in 0..8 {
            diag0.0+=left[output][k]*left[output][k];
            diag1.0+=right[output][k]*right[output][k];
            for l in k+1..8{
                let diff=l-k;
                let ca=left[output][k]*left[output][l];
                let cb=right[output][k]*right[output][l];
                match diff {
                    1|7=>{diag0.1+=ca;diag1.1+=cb;}
                    3|5=>{diag0.1-=ca;diag1.1-=cb;}
                    4=>{diag0.0-=2*ca;diag1.0-=2*cb;}
                    _=>{},
                }
            }
            for l in 0..8 {
                cross[(l+8-k)%8]+=left[output][k]*right[output][l];
            }
        }
    }
    let off=[
        checked_i64(cross[0]-cross[4])?,
        checked_i64(cross[1]-cross[5])?,
        checked_i64(cross[2]-cross[6])?,
        checked_i64(cross[3]-cross[7])?,
    ];
    Ok(CoherentGram{
        n:state.n as u8,h:state.paths as u8,first:first as u8,
        second:second as u8,bad_mask,
        diag0:(checked_i64(diag0.0)?,checked_i64(diag0.1)?),
        diag1:(checked_i64(diag1.0)?,checked_i64(diag1.1)?),off,
    })
}
// Rank-two Hermitian PSD equivalence: d0>=0, d1>=0, det>=0.
// All comparisons are exact integers in Z[sqrt(2)] after clearing
// the positive common denominator (delta_den*2^h).
fn gram_psd_verdict(gram:&CoherentGram,spec:&CoherentSpanSpec)->Check<CoherentVerdict>{
    // Exactly the same algebraic PSD obligation as before, but all
    // multiplications, additions and signed-surd comparisons are checked.
    // If fixed-width exact arithmetic cannot decide a case, fail closed.
    let(a,b,c)=scalar_gram_matrix(gram,spec)?;
    if !checked_nonnegative_quadratic(a.0,a.1)? {
        return Ok(CoherentVerdict::ScopedViolated{reason:"negative_diagonal_0"});
    }
    if !checked_nonnegative_quadratic(b.0,b.1)? {
        return Ok(CoherentVerdict::ScopedViolated{reason:"negative_diagonal_1"});
    }
    let product=real_mul(a,b)?;
    let off_squared=root_norm(c)?;
    let determinant=(
        product.0.checked_sub(off_squared.0).ok_or(Error::UnknownResource)?,
        product.1.checked_sub(off_squared.1).ok_or(Error::UnknownResource)?,
    );
    if !checked_nonnegative_quadratic(determinant.0,determinant.1)? {
        return Ok(CoherentVerdict::ScopedViolated{reason:"negative_determinant"});
    }
    Ok(CoherentVerdict::ScopedSatisfied)
}
fn encode_p8g1_claim(
    source:&[u8],proof:&[u8],spec:&[u8],gram:&CoherentGram
)->[u8;P8G1_BYTES]{
    let mut bytes=[0u8;P8G1_BYTES];
    bytes[..4].copy_from_slice(b"P8G1");
    bytes[4..36].copy_from_slice(&sha256(source));
    bytes[36..68].copy_from_slice(&sha256(spec));
    bytes[68..100].copy_from_slice(&sha256(proof));
    bytes[100]=gram.n;bytes[101]=gram.h;
    bytes[102]=gram.first;bytes[103]=gram.second;
    bytes[104..112].copy_from_slice(&gram.bad_mask.to_le_bytes());
    let mut offset=112;
    for scalar in [
        gram.diag0.0,gram.diag0.1,gram.diag1.0,gram.diag1.1,
        gram.off[0],gram.off[1],gram.off[2],gram.off[3]
    ] {
        bytes[offset..offset+8].copy_from_slice(&scalar.to_le_bytes());
        offset+=8;
    }
    bytes
}
fn verify_p8g1_coherent(
    source:&[u8],proof:&[u8],spec_bytes:&[u8],claim:&[u8]
)->Check<CoherentVerdict>{
    if claim.len()!=P8G1_BYTES {return Err(Error::InvalidProof);}
    let spec=parse_scg1_spec(spec_bytes)?;
    let mut cursor=Cursor::new(claim);
    if cursor.bytes(4)?!=b"P8G1"
        ||cursor.bytes(32)?!=sha256(source)
        ||cursor.bytes(32)?!=sha256(spec_bytes)
        ||cursor.bytes(32)?!=sha256(proof) {
        return Err(Error::InvalidProof);
    }
    let (n,h,first,second)=(cursor.u8()?,cursor.u8()?,cursor.u8()?,cursor.u8()?);
    let bad=cursor.u64()?;
    let diag0=(cursor.i64()?,cursor.i64()?);
    let diag1=(cursor.i64()?,cursor.i64()?);
    let off=[cursor.i64()?,cursor.i64()?,cursor.i64()?,cursor.i64()?];
    if cursor.at!=P8G1_BYTES{return Err(Error::InvalidProof);}
    if n as usize!=spec.n || first as usize!=spec.first ||
        second as usize!=spec.second || bad!=spec.bad_mask {
        return Err(Error::InvalidProof);
    }
    let (_,state)=replay_state(source,proof)?;
    if state.n!=spec.n || state.paths>8{return Err(Error::UnknownResource);}
    let computed=path_coherent_gram(&state,spec.first,spec.second,spec.bad_mask)?;
    let provided=CoherentGram{n,h,first,second,bad_mask:bad,diag0,diag1,off};
    if provided!=computed {return Err(Error::InvalidProof);}
    gram_psd_verdict(&provided,&spec)
}

// P8W1: separate source/spec/P8C1/P8G1-bound *constructive* violating
// coherent state. Coefficients live in Z[zeta_8] and are normalized by
// the positive square root of the exact Z[sqrt(2)] norm. The verifier
// independently checks that the normalized state's excess risk is > 0.
const P8W1_BYTES:usize=116;
type Cyclo=[i128;4];
type Real=(i128,i128);
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
struct Witness {
    input0:[i64;4], input1:[i64;4], norm: (i64,i64),
}
fn real_add(x:Real,y:Real)->Check<Real>{
    Ok((x.0.checked_add(y.0).ok_or(Error::UnknownResource)?,
        x.1.checked_add(y.1).ok_or(Error::UnknownResource)?))
}
fn real_mul(x:Real,y:Real)->Check<Real>{
    let constant=x.0.checked_mul(y.0)
        .and_then(|a|x.1.checked_mul(y.1)?.checked_mul(2)?.checked_add(a))
        .ok_or(Error::UnknownResource)?;
    let surd=x.0.checked_mul(y.1)
        .and_then(|a|x.1.checked_mul(y.0)?.checked_add(a))
        .ok_or(Error::UnknownResource)?;
    Ok((constant,surd))
}
fn root_conj(x:Cyclo)->Check<Cyclo>{
    Ok([x[0],
        x[3].checked_neg().ok_or(Error::UnknownResource)?,
        x[2].checked_neg().ok_or(Error::UnknownResource)?,
        x[1].checked_neg().ok_or(Error::UnknownResource)?])
}
fn root_mul(x:Cyclo,y:Cyclo)->Check<Cyclo>{
    let mut z=[0i128;4];
    for i in 0..4{
        for j in 0..4{
            let product=x[i].checked_mul(y[j]).ok_or(Error::UnknownResource)?;
            let k=(i+j)%4;
            let term=if i+j>=4{
                product.checked_neg().ok_or(Error::UnknownResource)?
            }else{product};
            z[k]=z[k].checked_add(term).ok_or(Error::UnknownResource)?;
        }
    }
    Ok(z)
}
fn root_add(x:Cyclo,y:Cyclo)->Check<Cyclo>{
    let mut z=[0i128;4];
    for i in 0..4 {z[i]=x[i].checked_add(y[i]).ok_or(Error::UnknownResource)?;}
    Ok(z)
}
fn root_neg(x:Cyclo)->Check<Cyclo>{
    let mut z=[0i128;4];
    for i in 0..4 {z[i]=x[i].checked_neg().ok_or(Error::UnknownResource)?;}
    Ok(z)
}
fn real_to_root(r:Real)->Check<Cyclo>{
    Ok([r.0,r.1,0,r.1.checked_neg().ok_or(Error::UnknownResource)?])
}
fn root_to_real(x:Cyclo)->Check<Real>{
    if x[2]!=0 || x[3]!=x[1].checked_neg().ok_or(Error::UnknownResource)?{
        return Err(Error::InvalidProof);
    }
    Ok((x[0],x[1]))
}
fn root_norm(x:Cyclo)->Check<Real>{
    root_to_real(root_mul(root_conj(x)?,x)?)
}
fn scalar_gram_matrix(g:&CoherentGram,s:&CoherentSpanSpec)->Check<(Real,Real,Cyclo)>{
    let shift=1i128.checked_shl(g.h as u32).ok_or(Error::UnknownResource)?;
    let d=s.delta_den;
    let a=(s.delta_num.checked_mul(shift)
        .and_then(|v|d.checked_mul(g.diag0.0 as i128)?.checked_neg()?.checked_add(v))
        .ok_or(Error::UnknownResource)?,
        d.checked_mul(g.diag0.1 as i128)
            .and_then(|v|v.checked_neg()).ok_or(Error::UnknownResource)?);
    let b=(s.delta_num.checked_mul(shift)
        .and_then(|v|d.checked_mul(g.diag1.0 as i128)?.checked_neg()?.checked_add(v))
        .ok_or(Error::UnknownResource)?,
        d.checked_mul(g.diag1.1 as i128)
            .and_then(|v|v.checked_neg()).ok_or(Error::UnknownResource)?);
    let mut c=[0i128;4];
    for i in 0..4{
        c[i]=d.checked_mul(g.off[i] as i128)
            .and_then(|v|v.checked_neg()).ok_or(Error::UnknownResource)?;
    }
    Ok((a,b,c))
}
fn coherent_witness_quadratic(
    g:&CoherentGram,s:&CoherentSpanSpec,w:&Witness
)->Check<(Real,Real)>{
    let (a,b,c)=scalar_gram_matrix(g,s)?;
    let u=w.input0.map(|v|v as i128);
    let v=w.input1.map(|v|v as i128);
    let norm=real_add(root_norm(u)?,root_norm(v)?)?;
    let actual_norm=(w.norm.0 as i128,w.norm.1 as i128);
    if norm!=actual_norm || checked_nonpositive_quadratic(norm.0,norm.1)?{
        return Err(Error::InvalidProof);
    }
    let cross=root_mul(root_mul(root_conj(u)?,c)?,v)?;
    let twice_real=root_to_real(root_add(cross,root_conj(cross)?)?)?;
    let quadratic=real_add(
        real_add(real_mul(a,root_norm(u)?)?,real_mul(b,root_norm(v)?)?)?,
        twice_real
    )?;
    Ok((norm,quadratic))
}
fn derive_coherent_witness(g:&CoherentGram,s:&CoherentSpanSpec)->Check<Witness>{
    if gram_psd_verdict(g,s)?==CoherentVerdict::ScopedSatisfied{
        return Err(Error::InvalidProof);
    }
    let (a,b,c)=scalar_gram_matrix(g,s)?;
    let basis=[1i128,0,0,0];
    let zero=[0i128;4];
    let (u,v)=if !checked_nonnegative_quadratic(a.0,a.1)?{
        (basis,zero)
    }else if !checked_nonnegative_quadratic(b.0,b.1)?{
        (zero,basis)
    }else{
        // If a>0, w=(-c,a) has w†D'w=a*det(D')<0.
        // If a=0, q=|c|²>0; w=(-c*(b+q),q) has
        // w†D'w=-(b+2q)*q²<0. Both use only Z[zeta8].
        if a!=(0,0){
            (root_neg(c)?,real_to_root(a)?)
        }else{
            let q=root_norm(c)?;
            if checked_nonpositive_quadratic(q.0,q.1)?{return Err(Error::InvalidProof);}
            let factor=real_add(b,q)?;
            (root_neg(root_mul(c,real_to_root(factor)?)?)?,real_to_root(q)?)
        }
    };
    let norm=real_add(root_norm(u)?,root_norm(v)?)?;
    let mut coords=[[0i64;4];2];
    for(i,amp)in [u,v].into_iter().enumerate(){
        for j in 0..4{coords[i][j]=checked_i64(amp[j])?;}
    }
    let w=Witness{
        input0:coords[0],input1:coords[1],
        norm:(checked_i64(norm.0)?,checked_i64(norm.1)?)
    };
    let(_,quadratic)=coherent_witness_quadratic(g,s,&w)?;
    if !checked_nonpositive_quadratic(quadratic.0,quadratic.1)?
        ||quadratic==(0,0){
        return Err(Error::InvalidProof);
    }
    Ok(w)
}
fn encode_p8w1(gram:&[u8],w:&Witness)->[u8;P8W1_BYTES]{
    let mut output=[0u8;P8W1_BYTES];
    output[..4].copy_from_slice(b"P8W1");
    output[4..36].copy_from_slice(&sha256(gram));
    let mut pos=36;
    for v in w.input0.into_iter().chain(w.input1).chain([w.norm.0,w.norm.1]){
        output[pos..pos+8].copy_from_slice(&v.to_le_bytes());
        pos+=8;
    }
    output
}
fn verify_p8w1_witness(
    source:&[u8],proof:&[u8],spec_bytes:&[u8],gram_claim:&[u8],witness:&[u8]
)->Check<(Witness,Real)>{
    if witness.len()!=P8W1_BYTES {return Err(Error::InvalidProof);}
    let spec=parse_scg1_spec(spec_bytes)?;
    let verdict=verify_p8g1_coherent(source,proof,spec_bytes,gram_claim)?;
    if verdict==CoherentVerdict::ScopedSatisfied{
        return Err(Error::InvalidProof);
    }
    let mut cursor=Cursor::new(witness);
    if cursor.bytes(4)?!=b"P8W1" ||cursor.bytes(32)?!=sha256(gram_claim){
        return Err(Error::InvalidProof);
    }
    let mut words=[0i64;10];
    for word in &mut words{*word=cursor.i64()?;}
    if cursor.at!=P8W1_BYTES{return Err(Error::InvalidProof);}
    let w=Witness{
        input0:words[0..4].try_into().map_err(|_|Error::InvalidProof)?,
        input1:words[4..8].try_into().map_err(|_|Error::InvalidProof)?,
        norm:(words[8],words[9])
    };
    let mut gc=Cursor::new(gram_claim);
    gc.bytes(104)?;
    let bad_mask=gc.u64()?;
    let g=CoherentGram{
        n:gram_claim[100],h:gram_claim[101],
        first:gram_claim[102],second:gram_claim[103],bad_mask,
        diag0:(gc.i64()?,gc.i64()?),diag1:(gc.i64()?,gc.i64()?),
        off:[gc.i64()?,gc.i64()?,gc.i64()?,gc.i64()?]
    };
    let(_,quadratic)=coherent_witness_quadratic(&g,&spec,&w)?;
    if !checked_nonpositive_quadratic(quadratic.0,quadratic.1)?
        ||quadratic==(0,0){
        return Err(Error::InvalidProof);
    }
    Ok((w,quadratic))
}

fn cli_coherent(
    source:&str,proof:&str,spec:&str,claim:&str
)->Check<CoherentVerdict>{
    let s=read_limited(source,MAX_SOURCE_BYTES,Error::InvalidSource)?;
    let p=read_limited(proof,MAX_PROOF_BYTES,Error::InvalidProof)?;
    let t=read_limited(spec,MAX_SPEC_BYTES,Error::InvalidSource)?;
    let g=read_limited(claim,P8G1_BYTES,Error::InvalidProof)?;
    verify_p8g1_coherent(&s,&p,&t,&g)
}

fn cli_property(source:&str,proof:&str,spec:&str,binding:&str)
    -> Check<PropertyVerdict>
{
    let s=read_limited(source,MAX_SOURCE_BYTES,Error::InvalidSource)?;
    let p=read_limited(proof,MAX_PROOF_BYTES,Error::InvalidProof)?;
    let t=read_limited(spec,MAX_SPEC_BYTES,Error::InvalidSource)?;
    let b=read_limited(binding,P8S1_BYTES,Error::InvalidProof)?;
    verify_spb1_property(&s,&p,&t,&b)
}

fn cli()->Check<usize> {
    let mut args=std::env::args().skip(1);
    let source=args.next().ok_or(Error::InvalidSource)?;
    let proof=args.next().ok_or(Error::InvalidProof)?;
    if args.next().is_some(){return Err(Error::InvalidProof);}
    let src=read_limited(&source,MAX_SOURCE_BYTES,Error::InvalidSource)?;
    let cert=read_limited(&proof,MAX_PROOF_BYTES,Error::InvalidProof)?;
    check(&src,&cert)
}
fn main()->ExitCode {
    let paths:Vec<_>=std::env::args().skip(1).collect();
    if paths.len()==16 && paths[0]=="--rank2"{
        // Cross-process, multi-artifact source/spec-linked rank-2 property
        // verification. Existing legacy parser/source-trust remains BLOCKED.
        let verdict=(||{
            let src=read_limited(&paths[1],MAX_SOURCE_BYTES,Error::InvalidSource)?;
            let p8=read_limited(&paths[2],MAX_PROOF_BYTES,Error::InvalidProof)?;
            let spec=read_limited(&paths[3],MAX_SPEC_BYTES,Error::InvalidSource)?;
            let read=|s:&str|read_limited(s,65_536,Error::InvalidProof);
            let structures=[read(&paths[4])?,read(&paths[5])?,read(&paths[6])?];
            let traces=[read(&paths[7])?,read(&paths[8])?,read(&paths[9])?];
            let f8=[read(&paths[10])?,read(&paths[11])?,read(&paths[12])?];
            let gram=read_limited(&paths[13],P8G1_BYTES,Error::InvalidProof)?;
            let witness=read_limited(&paths[14],P8W1_BYTES,Error::InvalidProof)?;
            let envelope=read_limited(&paths[15],512,Error::InvalidProof)?;
            f8g1_property::verify(
                &src,&p8,&spec,
                [&structures[0],&structures[1],&structures[2]],
                [&traces[0],&traces[1],&traces[2]],
                [&f8[0],&f8[1],&f8[2]],&gram,&witness,&envelope
            )
        })();
        return match verdict {
            Ok(result)=>{
                match result.verdict{
                    CoherentVerdict::ScopedSatisfied=>{
                        println!(
                            "SCOPED_F8G1_RANK2_PROPERTY_SAT \
                             source_symbolic_checks={} root_symbolic_checks={} assignment_enumeration=0 \
                             proof_methods={} witness=not_required source_trust=BLOCKED",
                            result.prefix_checks,result.root_checks,
                            result.proof_method_mask
                        );
                        ExitCode::SUCCESS
                    },
                    CoherentVerdict::ScopedViolated{reason}=>{
                        println!(
                            "SCOPED_F8G1_RANK2_PROPERTY_VIOLATED reason={reason} \
                             source_symbolic_checks={} root_symbolic_checks={} assignment_enumeration=0 \
                             proof_methods={} witness_checked={} source_trust=BLOCKED",
                            result.prefix_checks,result.root_checks,
                            result.proof_method_mask,
                            result.witness_gap.is_some()
                        );
                        ExitCode::from(6)
                    }
                }
            }
            Err(e)=>{
                println!("{}",e.label());
                ExitCode::from(e.exit_code())
            }
        }
    }

    if paths.len()==6 && paths[0]=="--chain" {
        // Bounded symbolic full-chain admission: raw source -> every P8C1
        // source prefix -> S8C1 Boolean DAG -> exact D8C1/M8D1 count.
        // This does NOT certify arbitrary OpenQASM or third-party WMC.
        let verdict=(||{
            let src=read_limited(&paths[1],MAX_SOURCE_BYTES,Error::InvalidSource)?;
            let p8=read_limited(&paths[2],MAX_PROOF_BYTES,Error::InvalidProof)?;
            let s8=read_limited(&paths[3],65_536,Error::InvalidProof)?;
            let trace=read_limited(&paths[4],65_536,Error::InvalidProof)?;
            let proof=read_limited(&paths[5],256,Error::InvalidProof)?;
            f8c1_chain::verify(&src,&p8,&s8,&trace,&proof)
        })();
        return match verdict{
            Ok(result)=>{
                println!(
                    "SCOPED_F8C1_SOURCE_COUNT_CHAIN_EXACT \
                     source_symbolic_checks={} root_symbolic_checks={} assignment_enumeration=0 buckets=8 method={} \
                     source_trust=BLOCKED",
                    result.prefix_checks,result.root_checks,
                    if result.method==1{"M8D1"}else{"D8C1"}
                );
                ExitCode::SUCCESS
            }
            Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
        };
    }
    if paths.len()==10 {
        // D8C1 certified eight-root counts for (i,i),(j,j),(i,j)
        // compose into a P8G1 Gram/PSD property without enumerating
        // all primary path assignments on the checker side.
        let result=(||{
            let source=read_limited(&paths[0],MAX_SOURCE_BYTES,Error::InvalidSource)?;
            let proof=read_limited(&paths[1],MAX_PROOF_BYTES,Error::InvalidProof)?;
            let spec=read_limited(&paths[2],MAX_SPEC_BYTES,Error::InvalidSource)?;
            let read=|p:&str|read_limited(p,65_536,Error::InvalidProof);
            let structural=[read(&paths[3])?,read(&paths[4])?,read(&paths[5])?];
            let traces=[read(&paths[6])?,read(&paths[7])?,read(&paths[8])?];
            let gram=read_limited(&paths[9],P8G1_BYTES,Error::InvalidProof)?;
            count_to_gram::verify(&source,&proof,&spec,
                [&structural[0],&structural[1],&structural[2]],
                [&traces[0],&traces[1],&traces[2]],&gram)
        })();
        return match result {
            Ok(result)=>{
                let (word,code)=match result.verdict{
                    CoherentVerdict::ScopedSatisfied=>
                        ("SCOPED_COUNT_TO_GRAM_PSD_SAT".to_string(),0u8),
                    CoherentVerdict::ScopedViolated{reason}=>
                        (format!("SCOPED_COUNT_TO_GRAM_PSD_VIOLATED reason={reason}"),6u8),
                };
                println!("{word} proof_nodes={} early_leaves={} source_trust=BLOCKED",
                    result.counted_nodes,result.early_leaves);
                ExitCode::from(code)
            }
            Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
        };
    }
    if paths.len()==3 {
        let result=(||{
            let src=read_limited(&paths[0],MAX_SOURCE_BYTES,Error::InvalidSource)?;
            let proof=read_limited(&paths[1],MAX_PROOF_BYTES,Error::InvalidProof)?;
            let evidence=read_limited(&paths[2],65_536,Error::InvalidProof)?;
            if evidence.starts_with(b"C8C1") {
                let (models,enumerated)=two_copy_cnf::verify(&src,&proof,&evidence)?;
                if models!=enumerated {return Err(Error::InvalidProof);}
                Ok((0u8,models))
            } else if evidence.starts_with(b"S8C1"){
                let models=two_copy_structural::verify(&src,&proof,&evidence)?;
                Ok((1u8,models))
            } else {
                let w=two_copy_wmc::verify_w8c1(&src,&proof,&evidence)?;
                Ok((2u8,w.buckets))
            }
        })();
        return match result {
            Ok((kind,counts))=>{
                let total=counts.iter().map(|&x|x as usize).sum::<usize>();
                match kind {
                    0=>println!("SCOPED_TWO_COPY_CNF_EXHAUSTIVE buckets=8 checked_models={total} source_trust=BLOCKED"),
                    1=>println!("SCOPED_TWO_COPY_STRUCTURAL_UNIQUE_EXTENSION buckets=8 checked_models={total} source_trust=BLOCKED"),
                    _=>println!("SCOPED_TWO_COPY_WMC_ENUM_EXACT buckets=8 total_weighted_pairs={total} source_trust=BLOCKED"),
                }
                ExitCode::SUCCESS
            }
            Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
        };
    }
    if paths.len()==5 {
        let result=(||{
            let src=read_limited(&paths[0],MAX_SOURCE_BYTES,Error::InvalidSource)?;
            let proof=read_limited(&paths[1],MAX_PROOF_BYTES,Error::InvalidProof)?;
            let spec=read_limited(&paths[2],MAX_SPEC_BYTES,Error::InvalidSource)?;
            let gram=read_limited(&paths[3],P8G1_BYTES,Error::InvalidProof)?;
            let witness=read_limited(&paths[4],P8W1_BYTES,Error::InvalidProof)?;
            verify_p8w1_witness(&src,&proof,&spec,&gram,&witness)
        })();
        return match result {
            Ok((w,gap))=>{
                println!("SCOPED_COHERENT_WITNESS_ACCEPTED norm_surd={}:{} negative_gap_surd={}:{} input0={:?} input1={:?} source_trust=BLOCKED",
                    w.norm.0,w.norm.1,gap.0,gap.1,w.input0,w.input1);
                ExitCode::SUCCESS
            },
            Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
        };
    }
    if paths.len()==4 {
        // D8C1 consumes a canonical S8C1 structural proof, NOT a property
        // specification. Its local Shannon rules can certify counts without
        // enumerating every primary path assignment.
        let preliminary=read_limited(&paths[2],65_536,Error::InvalidProof);
        match preliminary {
            Ok(structure) if structure.starts_with(b"S8C1")=>{
                let result:Check<(u8,[u16;8],usize,usize)>=(||{
                    let source=read_limited(&paths[0],MAX_SOURCE_BYTES,Error::InvalidSource)?;
                    let proof=read_limited(&paths[1],MAX_PROOF_BYTES,Error::InvalidProof)?;
                    let trace=read_limited(&paths[3],65_536,Error::InvalidProof)?;
                    if trace.starts_with(b"M8D1"){
                        let dag=two_copy_count_dag::verify(&source,&proof,&structure,&trace)?;
                        Ok((1u8,dag.buckets,dag.nodes,dag.shared_contexts))
                    }else{
                        let tree=two_copy_count_trace::verify(&source,&proof,&structure,&trace)?;
                        Ok((0u8,tree.buckets,tree.stats.nodes,tree.stats.early_leaves))
                    }
                })();
                return match result {
                    Ok((kind,counts,nodes,early_or_shared))=>{
                        let total=counts.iter().map(|&v|v as usize).sum::<usize>();
                        if kind==1{
                            println!("SCOPED_TWO_COPY_SHARED_DAG_EXACT buckets=8 checked_models={total} unique_nodes={nodes} shared_contexts={early_or_shared} source_trust=BLOCKED");
                        }else{
                            println!("SCOPED_TWO_COPY_COUNT_TRACE_EXACT buckets=8 checked_models={total} checker_nodes={nodes} early_leaves={early_or_shared} source_trust=BLOCKED");
                        }
                        ExitCode::SUCCESS
                    }
                    Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
                };
            }
            Err(e)=>{println!("{}",e.label());return ExitCode::from(e.exit_code());}
            _=>{},
        }
    }
    if paths.len()==4 {
        // Do not reinterpret basis-only SPB1 as coherent-span SCG1.
        // A distinct spec magic selects a distinct proof contract.
        let is_coherent=match read_limited(&paths[2],MAX_SPEC_BYTES,Error::InvalidSource){
            Ok(data)=>data.starts_with(b"SCG1\n"),
            Err(e)=>{println!("{}",e.label());return ExitCode::from(e.exit_code());}
        };
        if is_coherent {
            return match cli_coherent(&paths[0],&paths[1],&paths[2],&paths[3]) {
                Ok(CoherentVerdict::ScopedSatisfied)=>{
                    println!("SCOPED_COHERENT_SPAN_SAT source_trust=BLOCKED");
                    ExitCode::SUCCESS
                }
                Ok(CoherentVerdict::ScopedViolated{reason})=>{
                    println!("SCOPED_COHERENT_SPAN_VIOLATED reason={reason} source_trust=BLOCKED");
                    ExitCode::from(6)
                }
                Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
            };
        }
        return match cli_property(&paths[0],&paths[1],&paths[2],&paths[3]) {
            Ok(PropertyVerdict::ScopedSatisfied)=>{
                println!("SCOPED_PROPERTY_SAT source_trust=BLOCKED");
                ExitCode::SUCCESS
            }
            Ok(PropertyVerdict::ScopedViolated{input_basis})=>{
                println!("SCOPED_PROPERTY_VIOLATED input_basis={input_basis} source_trust=BLOCKED");
                ExitCode::from(6)
            }
            Err(e)=>{println!("{}",e.label());ExitCode::from(e.exit_code())}
        };
    }
    match cli() {
        Ok(steps)=>{
            println!("SCOPED_REPLAY_PASS steps={steps} source_trust=BLOCKED");
            ExitCode::SUCCESS
        }
        Err(e)=>{
            println!("{}",e.label());
            ExitCode::from(e.exit_code())
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn write_proof(source:&[u8],n:usize,claims:&[State])->Vec<u8> {
        let mut result=Vec::new();
        result.extend_from_slice(b"P8C1");
        result.push(n as u8);
        result.extend_from_slice(&(claims.len() as u16).to_le_bytes());
        result.extend_from_slice(&sha256(source));
        for state in claims {
            result.push(state.paths as u8);
            for output in &state.outputs {
                result.extend_from_slice(&(output.len() as u16).to_le_bytes());
                for term in output {result.extend_from_slice(&term.to_le_bytes());}
            }
            result.extend_from_slice(&(state.phase.len() as u16).to_le_bytes());
            for (&m,&c) in &state.phase {
                result.extend_from_slice(&m.to_le_bytes());
                result.push(c);
            }
        }
        result
    }
    fn example_h()->(Vec<u8>,Vec<u8>) {
        let source=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n".to_vec();
        let state=State {n:1,paths:1,
            outputs:vec![BTreeSet::from([2])],
            phase:BTreeMap::from([(3,4)])};
        let proof=write_proof(&source,1,&[state]);
        (source,proof)
    }
    fn example_cx_t()->(Vec<u8>,Vec<u8>) {
        let source=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\ncx q[0],q[1];\nt q[1];\n".to_vec();
        let first=State {n:2,paths:0,
            outputs:vec![BTreeSet::from([1]),BTreeSet::from([1,2])],
            phase:Phase::new()};
        let second=State {phase:BTreeMap::from([(1,1),(2,1),(3,6)]),..first.clone()};
        let proof=write_proof(&source,2,&[first,second]);
        (source,proof)
    }
    #[test]
    fn sha256_fips_vector() {
        assert_eq!(
            sha256(b"abc").map(|x|format!("{x:02x}")).concat(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        assert_eq!(
            sha256(b"").map(|x|format!("{x:02x}")).concat(),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    // Binary contract for the source-linked proof parser. These tests
    // exercise the actual Cursor/read_termset/read_phase implementations,
    // not just an independent reimplementation of their semantics.
    fn encoded_termset(masks:&[u64])->Vec<u8>{
        let mut data=(masks.len() as u16).to_le_bytes().to_vec();
        for &m in masks{data.extend_from_slice(&m.to_le_bytes());}
        data
    }
    fn bounded_termset(bytes:&[u8],width:usize)->Check<Anf>{
        let mut cursor=Cursor::new(bytes);
        let mut total=0usize;
        let mut local=0usize;
        let ans=read_termset(&mut cursor,width,&mut total,&mut local)?;
        if cursor.at!=bytes.len(){return Err(Error::InvalidProof);}
        Ok(ans)
    }
    #[test]
    fn p8c1_u16_le_mask_decoder_every_word_exact(){
        let mut words=0usize;
        for word in 0..=u16::MAX{
            let encoded=word.to_le_bytes();
            let mut cursor=Cursor::new(&encoded);
            assert_eq!(cursor.u16().unwrap(),word as usize);
            assert_eq!(cursor.at,2);
            // Term masks in P8C1 are eight bytes, little-endian,
            // independently of the n≤16 symbolic Rust u16 representation.
            let mask=encoded_termset(&[word as u64]);
            let got=bounded_termset(&mask,16).unwrap();
            assert_eq!(got,BTreeSet::from([word as u64]));
            words+=1;
        }
        assert_eq!(words,65_536);
        println!(
            "P8C1_WORD16_LE_DECODER all_words={words} \
             endian=little mask_bits=16 exact=true"
        );
    }
    #[test]
    fn p8c1_mask_sorted_width_count_and_phase_fail_closed(){
        let canonical=encoded_termset(&[0,0x0100,0x8000]);
        assert_eq!(
            bounded_termset(&canonical,16).unwrap(),
            BTreeSet::from([0u64,0x0100,0x8000])
        );
        assert_eq!(
            bounded_termset(&canonical,15),Err(Error::InvalidProof),
            "A 16-bit mask must be rejected under width=15"
        );
        for bad in [
            encoded_termset(&[0,0]),
            encoded_termset(&[0x8000,1]),
            encoded_termset(&[0x10000]),
        ]{
            assert_eq!(bounded_termset(&bad,16),Err(Error::InvalidProof));
        }
        let mut truncated=encoded_termset(&[0x8000]);
        truncated.pop();
        assert_eq!(bounded_termset(&truncated,16),Err(Error::InvalidProof));
        let mut appended=canonical.clone();
        appended.push(0);
        assert_eq!(bounded_termset(&appended,16),Err(Error::InvalidProof));
        let oversized=(MAX_FRAME_TERMS as u16+1).to_le_bytes();
        assert_eq!(
            bounded_termset(&oversized,16),Err(Error::UnknownResource),
            "oversized count must fail before reading further proof bytes"
        );
        // Contrasts 0x0100 with a byte-swapped 0x0001.
        assert_eq!(&canonical[10..18],&0x0100u64.to_le_bytes());
        let mut data=Vec::new();
        data.extend_from_slice(&2u16.to_le_bytes());
        data.extend_from_slice(&0u64.to_le_bytes());
        data.push(1);
        data.extend_from_slice(&0x8000u64.to_le_bytes());
        data.push(7);
        let mut cur=Cursor::new(&data);
        let mut total=0usize;
        let mut local=0usize;
        assert_eq!(
            read_phase(&mut cur,16,&mut total,&mut local),
            Ok(BTreeMap::from([(0u64,1u8),(0x8000u64,7u8)]))
        );
        assert_eq!(cur.at,data.len());
        // Phase coefficients 0 and 8 do not represent canonical Z8
        // monomials; the original decoder must reject them.
        for coeff in [0u8,8u8]{
            let mut bad=Vec::new();
            bad.extend_from_slice(&1u16.to_le_bytes());
            bad.extend_from_slice(&0u64.to_le_bytes());
            bad.push(coeff);
            let mut cur=Cursor::new(&bad);
            let (mut total,mut local)=(0,0);
            assert_eq!(
                read_phase(&mut cur,16,&mut total,&mut local),
                Err(Error::InvalidProof)
            );
        }
        println!(
            "P8C1_MASK_PHASE_BOUNDARY \
             width16_high_bit=true width15_rejected=true \
             strict_sorted=true distinct=true term_count_bound=true \
             little_endian=true noncanonical_phase_rejected=true"
        );
    }

    #[test]
    fn standalone_h_and_cx_t_exact_replay() {
        let (s,h)=example_h();
        assert_eq!(check(&s,&h),Ok(1));
        let (s,cxt)=example_cx_t();
        assert_eq!(check(&s,&cxt),Ok(2));
    }
    #[test]
    fn standalone_one_bit_forgery_is_never_accepted() {
        let (s,p)=example_cx_t();
        let mut accepted=0;
        for i in 0..p.len(){
            for bit in 0..8 {
                let mut b=p.clone();
                b[i]^=1<<bit;
                if check(&s,&b).is_ok(){accepted+=1;}
            }
        }
        assert_eq!(accepted,0);
        println!("STANDALONE_P8C1_BIT_MUTATIONS={} accepted=0",p.len()*8);
    }
    #[test]
    fn rejects_version_sources_truncation_and_limits() {
        let (s,p)=example_h();
        assert_eq!(check(&s,&p),Ok(1));
        let alt=String::from_utf8(s.clone()).unwrap().replace("OPENQASM 3.0","OPENQASM 3.1");
        assert_eq!(check(alt.as_bytes(),&p),Err(Error::UnsupportedSource));
        let alt=String::from_utf8(s.clone()).unwrap().replace("h q[0]","u3(0,0,0) q[0]");
        assert_eq!(check(alt.as_bytes(),&p),Err(Error::UnsupportedSource));
        assert_eq!(check(&s,&p[..p.len()-1]),Err(Error::InvalidProof));
        let mut forged=p.clone();
        forged.push(0);
        assert_eq!(check(&s,&forged),Err(Error::InvalidProof));
        assert_eq!(check(&s,&vec![0;MAX_PROOF_BYTES+1]),Err(Error::UnknownResource));
        assert_eq!(check(&vec![b'a';MAX_SOURCE_BYTES+1],&p),Err(Error::UnknownResource));
    }

    fn spec(n:usize,pre:u64,bad:u64,num:usize,den:usize)->Vec<u8> {
        format!("SPB1\nn={n}\nbasis_pre=0x{pre:016x}\nbasis_bad=0x{bad:016x}\ndelta={num}/{den}\n").into_bytes()
    }
    fn property(src:&[u8],proof:&[u8],sp:&[u8])->Check<PropertyVerdict> {
        verify_spb1_property(src,proof,sp,&proof_bound_bytes(src,proof,sp))
    }
    #[test]
    fn exact_basis_risk_half_and_irrational_thresholds() {
        let (s,p)=example_h();
        assert_eq!(property(&s,&p,&spec(1,1,2,1,2)),
            Ok(PropertyVerdict::ScopedSatisfied));
        assert_eq!(property(&s,&p,&spec(1,1,2,1,3)),
            Ok(PropertyVerdict::ScopedViolated {input_basis:0}));
        assert_eq!(property(&s,&p,&spec(1,1,2,1,1)),
            Ok(PropertyVerdict::ScopedSatisfied));
        let (source,proof)=example_cx_t();
        assert_eq!(property(&source,&proof,&spec(2,1,2,0,1)),
            Ok(PropertyVerdict::ScopedSatisfied));
        // Exact H;T;H on |0>: risk of output |1> =
        // (2 - sqrt(2))/4, strictly between 1/8 and 1/4.
        let src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n";
        let mut state=State {n:1,paths:0,
            outputs:vec![BTreeSet::from([1])],phase:Phase::new()};
        let mut fuel=Fuel {remaining:MAX_UPDATES};
        let mut prefixes=Vec::new();
        for g in [Gate::H(0),Gate::T(0),Gate::H(0)] {
            evolve(&mut state,g,&mut fuel).unwrap();
            prefixes.push(state.clone());
        }
        let proof=write_proof(src,1,&prefixes);
        assert_eq!(property(src,&proof,&spec(1,1,2,1,8)),
            Ok(PropertyVerdict::ScopedViolated{input_basis:0}));
        assert_eq!(property(src,&proof,&spec(1,1,2,1,4)),
            Ok(PropertyVerdict::ScopedSatisfied));
        let (a,b)=exact_bad_probability(&state,0,2).unwrap();
        assert_eq!((a,b),(2,-1));
        println!("SPB1_EXACT_RISK rational_half=true irrational_surd=(2-sqrt2)/4=true thresholds=pass_and_violate");
    }
    #[test]
    fn source_spec_proof_binding_and_claim_mutations_fail_closed() {
        let (source,proof)=example_h();
        let spec_bytes=spec(1,1,2,1,2);
        let binding=proof_bound_bytes(&source,&proof,&spec_bytes);
        assert_eq!(verify_spb1_property(&source,&proof,&spec_bytes,&binding),
            Ok(PropertyVerdict::ScopedSatisfied));
        let mut total=0usize;
        for i in 0..binding.len() {
            for bit in 0..8 {
                let mut forged=binding;
                forged[i]^=1<<bit;
                assert_ne!(verify_spb1_property(&source,&proof,&spec_bytes,&forged),
                    Ok(PropertyVerdict::ScopedSatisfied));
                total+=1;
            }
        }
        let alt=spec(1,1,2,1,3);
        assert_eq!(verify_spb1_property(&source,&proof,&alt,&binding),
            Err(Error::InvalidProof));
        let mut mutated_proof=proof.clone();mutated_proof[15]^=1;
        assert_eq!(verify_spb1_property(&source,&mutated_proof,&spec_bytes,&binding),
            Err(Error::InvalidProof));
        let mut mutated_source=source.clone();mutated_source.push(b' ');
        assert_eq!(verify_spb1_property(&mutated_source,&proof,&spec_bytes,&binding),
            Err(Error::InvalidProof));
        assert_eq!(property(&source,&proof,b"SPB1\nn=1\nbasis_pre=0x0000000000000001\nbasis_bad=0x0000000000000002\ndelta=2/4\n"),
            Err(Error::InvalidSource));
        assert_eq!(property(&source,&proof,b"SPB1\nn=4\nbasis_pre=0x0000000000000001\nbasis_bad=0x0000000000000002\ndelta=1/2\n"),
            Err(Error::UnsupportedSource));
        println!("SPB1_BINDING_MUTATIONS={} accepted=0 source_spec_proof_bound=true",total);
    }


    #[test]
    fn differential_dense_source_risk_oracle_sweep() {
        // Independently decoded dense gate-by-gate amplitudes, rather than
        // parity-polynomial/pathsum replay. Compare *exact* Q(sqrt2)
        // numerators before comparing the typed property verdict.
        let mut cases=0usize;
        let mut probability_pairs=0usize;
        let mut properties=0usize;
        let mut gram_pairs=0usize;
        let mut psd_verdicts=0usize;
        let mut constructive_witnesses=0usize;
        let mut double_path_wmc_obligations=0usize;
        let thresholds=[(0,1),(1,8),(1,4),(1,2),(1,1)];
        for n in 1..=3 {
            let dim=1usize<<n;
            let full=(1u64<<dim)-1;
            let mut masks=vec![1u64,full,1u64<<(dim-1),full&0x55];
            masks.sort_unstable(); masks.dedup();
            for example in 0..12u64 {
                let mut seed=(n as u64).wrapping_mul(0x9e3779b97f4a7c15u64)
                    ^example.wrapping_mul(0xbf58476d1ce4e5b9);
                let mut program=String::new();
                let mut h_count=0usize;
                for step in 0..12 {
                    seed=seed.wrapping_mul(6364136223846793005)
                        .wrapping_add(1442695040888963407);
                    let opcode=((seed>>34)%9) as usize;
                    let a=(seed as usize)%n;
                    let b=(a+1+((seed>>17) as usize)%n.saturating_sub(1).max(1))%n;
                    let gate=match opcode {
                        0 if h_count<5 => {h_count+=1;format!("h q[{a}];")},
                        1 => format!("t q[{a}];"),
                        2 => format!("s q[{a}];"),
                        3 => format!("z q[{a}];"),
                        4 => format!("x q[{a}];"),
                        5 if n>1 => format!("cx q[{a}],q[{b}];"),
                        6 if n>1 => format!("cz q[{a}],q[{b}];"),
                        7 => "gphase(pi/4);".to_string(),
                        _ => format!("x q[{a}];"),
                    };
                    program.push_str(&gate);
                    program.push('\n');
                    if step==0 && n>1 {
                        // Guaranteed non-diagonal example among the corpus.
                        program.push_str("h q[0];\n");
                        h_count+=1;
                    }
                }
                let source=format!("OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[{n}] q;\n{program}");
                let src=source.as_bytes();
                let (_,gates)=parse_source(src).unwrap();
                let mut state=State {
                    n, paths:0,
                    outputs:(0..n).map(|bit|BTreeSet::from([1u64<<bit])).collect(),
                    phase:Phase::new(),
                };
                let mut fuel=Fuel{remaining:MAX_UPDATES};
                let mut frames=Vec::new();
                for gate in gates {
                    evolve(&mut state,gate,&mut fuel).unwrap();
                    frames.push(state.clone());
                }
                let proof=write_proof(src,n,&frames);
                assert_eq!(replay_state(src,&proof).unwrap().1,state);
                for &bad in &masks {
                    // Compare every computational-basis input, not just
                    // inputs selected by a particular specification.
                    for basis in 0..dim {
                        let symbolic=exact_bad_probability(&state,basis,bad).unwrap();
                        let dense=dense_oracle::basis_risk(src,basis,bad).unwrap();
                        assert_eq!(
                            (symbolic.0,symbolic.1,state.paths),dense,
                            "exact dense/ANF mismatch n={n} sample={example} basis={basis} bad={bad:x}"
                        );
                        probability_pairs+=1;
                    }
                    for &pre in &masks {
                        for &(num,den) in &thresholds {
                            let sp=spec(n,pre,bad,num,den);
                            let actual=property(src,&proof,&sp).unwrap();
                            let mut first_failure=None;
                            for basis in 0..dim {
                                if pre&(1u64<<basis)==0 {continue;}
                                let risk=dense_oracle::basis_risk(src,basis,bad).unwrap();
                                if !dense_oracle::risk_at_most(risk,num as i128,den as i128) {
                                    first_failure=Some(basis);
                                    break;
                                }
                            }
                            let expected=match first_failure {
                                Some(input_basis)=>PropertyVerdict::ScopedViolated{input_basis},
                                None=>PropertyVerdict::ScopedSatisfied,
                            };
                            assert_eq!(actual,expected,
                                "dense oracle verdict mismatch n={n} sample={example} pre={pre:x} bad={bad:x} delta={num}/{den}");
                            properties+=1;
                        }
                    }
                }

                for &bad in &masks {
                    for first in 0..dim {
                        for second in first+1..dim {
                            let exact=path_coherent_gram(&state,first,second,bad).unwrap();
                            let independent=dense_oracle::coherent_gram(src,first,second,bad).unwrap();
                            assert_eq!(
                                ((exact.diag0.0 as i128,exact.diag0.1 as i128),
                                 (exact.diag1.0 as i128,exact.diag1.1 as i128),
                                 exact.off.map(|x|x as i128),exact.h as usize),
                                independent,
                                "P8G1 exact matrix coefficients n={n} sample={example} inputs={first},{second} bad={bad:x}"
                            );

                            // A separate, complete two-copy Boolean
                            // assignment enumeration realizes the exact
                            // complex weighted-counting identity for Gram.
                            // This is a bounded oracle, not a CNF solver proof.
                            if example<3 && state.paths<=6 {
                                let counted=two_copy_wmc::enumerate_pairs(
                                    &state,first,second,bad
                                ).unwrap();
                                assert_eq!(
                                    two_copy_wmc::cyclotomic_four(&counted),
                                    exact.off.map(|x|x as i128),
                                    "two-copy WMC cross-phase mismatch n={n} sample={example} pair={first},{second}"
                                );
                                let fixture=two_copy_wmc::encode_w8c1(src,&proof,&counted);
                                assert_eq!(
                                    two_copy_wmc::verify_w8c1(src,&proof,&fixture).unwrap(),
                                    counted
                                );
                                if double_path_wmc_obligations==0 {
                                    let mut forged=fixture;
                                    forged[79]^=1;
                                    assert!(two_copy_wmc::verify_w8c1(src,&proof,&forged).is_err());
                                }
                                double_path_wmc_obligations+=1;
                            }
                            gram_pairs+=1;
                            let pre=(1u64<<first)|(1u64<<second);
                            for &(num,den) in &thresholds {
                                let sp=coherent_spec(n,pre,bad,num,den);
                                let parsed=parse_scg1_spec(&sp).unwrap();
                                let verdict=gram_psd_verdict(&exact,&parsed).unwrap();
                                let dense=dense_oracle::coherent_psd(
                                    independent,num as i128,den as i128
                                );
                                assert_eq!(verdict==CoherentVerdict::ScopedSatisfied,dense,
                                    "P8G1 PSD mismatch n={n} sample={example} span={pre:x} bad={bad:x} delta={num}/{den}");

                                if verdict!=CoherentVerdict::ScopedSatisfied {
                                    let w=derive_coherent_witness(&exact,&parsed)
                                        .unwrap_or_else(|e|panic!(
                                            "witness construction failed {e:?} n={n} sample={example} span={pre:x} bad={bad:x} delta={num}/{den}"
                                        ));
                                    let claim=encode_p8g1_claim(src,&proof,&sp,&exact);
                                    let bytes=encode_p8w1(&claim,&w);
                                    let(_,negative_gap)=verify_p8w1_witness(
                                        src,&proof,&sp,&claim,&bytes
                                    ).unwrap();
                                    let (norm,excess,_)=dense_oracle::coherent_witness_excess(
                                        src,first,second,bad,
                                        num as i128,den as i128,
                                        w.input0.map(|x|x as i128),
                                        w.input1.map(|x|x as i128)
                                    ).unwrap();
                                    assert_eq!(norm,(w.norm.0 as i128,w.norm.1 as i128));
                                    assert_eq!(negative_gap,(-excess.0,-excess.1),
                                        "P8W1 independent dense witness mismatch n={n} sample={example} span={pre:x} bad={bad:x} delta={num}/{den}");
                                    assert!(dense_oracle::coherent_witness_is_violation(
                                        src,first,second,bad,
                                        num as i128,den as i128,
                                        w.input0.map(|x|x as i128),
                                        w.input1.map(|x|x as i128)
                                    ).unwrap());
                                    constructive_witnesses+=1;
                                }

                                psd_verdicts+=1;
                            }
                        }
                    }
                }
                cases+=1;
            }
        }
        assert_eq!(cases,36);
        println!("P8S1_DENSE_DIFFERENTIAL circuits={cases} exact_prob_pairs={probability_pairs} property_verdicts={properties} all_match=true");
        println!("P8G1_DENSE_SWEEP circuits={cases} gram_pairs={gram_pairs} coherent_psd_verdicts={psd_verdicts} all_match=true");
        println!("P8W1_DENSE_WITNESS_SWEEP circuits={cases} constructive_witnesses={constructive_witnesses} independently_verified=true all_negative_gaps_exact=true");
        println!("W8C1_TWO_COPY_ORACLE gram_obligations={double_path_wmc_obligations} exact_pair_weights=true distinct_from_cnf_certification=true");
    }
    #[test]
    fn basis_only_contract_rejects_unjustified_span_inference() {
        let (source,proof)=example_h();
        // |0> and |1> each have Pr(bad=|0>)=1/2 under H.
        let sp=spec(1,3,1,1,2);
        assert_eq!(property(&source,&proof,&sp),
            Ok(PropertyVerdict::ScopedSatisfied));
        // But |+> = (|0>+|1>)/sqrt(2) is mapped by H to |0>
        // and has Pr(bad=|0>)=1. This is a property-semantics
        // counterexample, not a verifier bug in its stated basis-only scope.
        let risk=dense_oracle::plus_state_h_bad_zero().unwrap();
        assert_eq!(risk,(4,0,2));
        assert!(!dense_oracle::risk_at_most(risk,1,2));
        println!("P8S1_BASIS_VS_SPAN basis_only_sat=true superposition_violates=true no_span_claim=true");
    }


    fn coherent_spec(
        n:usize,span_mask:u64,bad:u64,num:usize,den:usize
    )->Vec<u8>{
        format!("SCG1\nn={n}\nspan_basis=0x{span_mask:016x}\nbasis_bad=0x{bad:016x}\ndelta={num}/{den}\n").into_bytes()
    }
    fn source_proof_and_state(source:&[u8])->(Vec<u8>,State){
        let(n,gates)=parse_source(source).unwrap();
        let mut state=State{
            n,paths:0,
            outputs:(0..n).map(|i|BTreeSet::from([1u64<<i])).collect(),
            phase:Phase::new(),
        };
        let mut fuel=Fuel{remaining:MAX_UPDATES};
        let mut frames=Vec::new();
        for gate in gates{
            evolve(&mut state,gate,&mut fuel).unwrap();
            frames.push(state.clone());
        }
        (write_proof(source,n,&frames),state)
    }
    fn coherent_fixture(
        source:&[u8],sp:&[u8]
    )->(Vec<u8>,[u8;P8G1_BYTES],CoherentGram,CoherentSpanSpec){
        let (proof,state)=source_proof_and_state(source);
        let spec=parse_scg1_spec(sp).unwrap();
        let gram=path_coherent_gram(
            &state,spec.first,spec.second,spec.bad_mask
        ).unwrap();
        let claim=encode_p8g1_claim(source,&proof,sp,&gram);
        (proof,claim,gram,spec)
    }
    #[test]
    fn s8c1_structural_unique_auxiliary_extension_exact_vs_blocking(){
        let (source,proof)=example_h();
        let (_,state)=replay_state(&source,&proof).unwrap();
        let bytes=two_copy_structural::encode(&source,&proof,&state,0,1,1).unwrap();
        assert_eq!(
            two_copy_structural::verify(&source,&proof,&bytes),
            Ok([1,0,0,0,0,0,0,0])
        );
        let reference=two_copy_cnf::build(&state,0,1,1).unwrap();
        assert_eq!(
            two_copy_cnf::count_models(&reference).unwrap(),
            two_copy_structural::verify(&source,&proof,&bytes).unwrap()
        );
        for i in [0,4,36,68,70,80,81,bytes.len()/2,bytes.len()-1]{
            let mut forged=bytes.clone();forged[i]^=1;
            assert_eq!(two_copy_structural::verify(&source,&proof,&forged),
                Err(Error::InvalidProof));
        }
        println!("S8C1_EXACT_H source_bound=true unique_extension=true buckets=8 exact_model_count=1 forged_9_rejected=true certificate_bytes={}",bytes.len());
    }
    #[test]
    fn s8c1_structural_sampled_two_copy_phase_correctness(){
        // The XOR path expressions and nontrivial Z8 phase coefficients are
        // interpreted by an independent exhaustive bucket/Boolean oracle.
        let examples=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nt q[0];\nh q[1];\ncz q[0],q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[3] q;\nh q[0];\ncx q[0],q[2];\nh q[1];\nt q[2];\ns q[1];\n".as_slice(),
        ];
        let mut total=0;
        for source in examples {
            let(n,_)=parse_source(source).unwrap();
            let (proof,state)=source_proof_and_state(source);
            let dimension=1usize<<n;
            for &(first,second) in &[(0,0),(0,1),(1,0),(1,1)] {
                for bad in [1u64,1u64<<(dimension-1), (1u64<<dimension)-1]{
                    let bytes=two_copy_structural::encode(source,&proof,&state,first,second,bad).unwrap();
                    let structural=two_copy_structural::verify(source,&proof,&bytes).unwrap();
                    let reference=two_copy_cnf::count_models(
                        &two_copy_cnf::build(&state,first,second,bad).unwrap()
                    ).unwrap();
                    assert_eq!(structural,reference);
                    total+=1;
                }
            }
        }
        assert_eq!(total,36);
        println!("S8C1_STRUCTURAL_DIFFERENTIAL obligations={total} unique_extension=true all_eight_buckets_match=true");
    }
    #[test]
    fn s8c1_structural_h1_to_h4_certificate_size_pilot(){
        // Paired true-source proof bytes and C8C1 canonical blocking bytes
        // at fixed n=1, varying H-path count h=1..4. This is NOT a
        // walltime benchmark nor a proof of polynomial end-to-end size.
        let mut rows=Vec::new();
        for h in 1..=4{
            let mut gates=String::new();
            for _ in 0..h {
                gates.push_str("h q[0];\nt q[0];\n");
            }
            let source=format!(
                "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\n{gates}"
            );
            let (proof,state)=source_proof_and_state(source.as_bytes());
            assert_eq!(state.paths,h);
            let structural=two_copy_structural::encode(
                source.as_bytes(),&proof,&state,0,1,1
            ).unwrap();
            let blocking=two_copy_cnf::encode(
                source.as_bytes(),&proof,
                &two_copy_cnf::build(&state,0,1,1).unwrap()
            ).unwrap();
            let exact_s=two_copy_structural::verify(
                source.as_bytes(),&proof,&structural).unwrap();
            let (exact_b,independent)=two_copy_cnf::verify(
                source.as_bytes(),&proof,&blocking).unwrap();
            assert_eq!(exact_s,exact_b);
            assert_eq!(exact_s,independent);
            let models=exact_s.iter().map(|&v|v as usize).sum::<usize>();
            println!(
                "S8C1_SIZE_PILOT n=1 h={h} primary={} s8c1_bytes={} c8c1_bytes={} counted_pairs={models} exact=true nonbenchmark=true",
                2*h,structural.len(),blocking.len()
            );
            rows.push((structural.len(),blocking.len()));
        }
        assert_eq!(rows.len(),4);
    }
    #[test]
    fn d8c1_local_shannon_trace_exact_and_fail_closed(){
        let (src,proof)=example_h();
        let (_,state)=replay_state(&src,&proof).unwrap();
        let structural=two_copy_structural::encode(&src,&proof,&state,0,1,1).unwrap();
        let trace=two_copy_count_trace::emit(&src,&proof,&structural).unwrap();
        let checked=two_copy_count_trace::verify(&src,&proof,&structural,&trace).unwrap();
        assert_eq!(checked.buckets,[1,0,0,0,0,0,0,0]);
        let canonical=two_copy_cnf::count_models(
            &two_copy_cnf::build(&state,0,1,1).unwrap()
        ).unwrap();
        assert_eq!(checked.buckets,canonical);
        let(mut rejected,mut accepted)=(0usize,0usize);
        for i in 0..trace.len(){
            for bit in 0..8{
                let mut forged=trace.clone();forged[i]^=1u8<<bit;
                if two_copy_count_trace::verify(&src,&proof,&structural,&forged).is_err(){
                    rejected+=1;
                }else{accepted+=1;}
            }
        }
        assert_eq!(accepted,0);
        assert_eq!(rejected,trace.len()*8);
        let mut forged=structural.clone();forged[9]^=1;
        assert_eq!(two_copy_count_trace::verify(&src,&proof,&forged,&trace),
            Err(Error::InvalidProof));
        println!("D8C1_H_EXACT trace_bytes={} proof_nodes={} exhaustive_mutations={} rejected={} accepted=0",
            trace.len(),checked.stats.nodes,rejected,rejected);
    }
    #[test]
    fn d8c1_false_subtree_prunes_all_path_pairs_without_enumeration(){
        // The first and second basis inputs differ on untouched q[1],
        // so none of the 2^(2h) path pairs can share the same output.
        let src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nt q[0];\nh q[0];\nt q[0];\nh q[0];\nt q[0];\nh q[0];\nt q[0];\n";
        let(proof,state)=source_proof_and_state(src);
        assert_eq!(state.paths,4);
        let structural=two_copy_structural::encode(src,&proof,&state,0,2,15).unwrap();
        let trace=two_copy_count_trace::emit(src,&proof,&structural).unwrap();
        let verified=two_copy_count_trace::verify(src,&proof,&structural,&trace).unwrap();
        assert_eq!(verified.buckets,[0;8]);
        assert_eq!(verified.stats.nodes,8);
        assert_eq!(verified.stats.early_leaves,8);
        assert_eq!(verified.stats.forced_splits,0);
        let enumerated=two_copy_cnf::count_models(
            &two_copy_cnf::build(&state,0,2,15).unwrap()
        ).unwrap();
        assert_eq!(verified.buckets,enumerated);
        println!("D8C1_PRUNING h=4 primary_assignments=256 checker_proof_nodes=8 buckets=8 all_zero=true trace_bytes={}",
            trace.len());
    }
    #[test]
    fn g8d1_counts_compose_into_exact_rank_two_gram_psd_without_enumeration(){
        let corpus=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nh q[1];\ncz q[0],q[1];\n".as_slice(),
        ];
        let mut cases=0usize;
        let mut nodes=0usize;
        for src in corpus{
            let (proof,state)=source_proof_and_state(src);
            let dim=1usize<<state.n;
            for second in 1..dim{
                let first=0usize;
                for bad in [1u64,1u64<<(dim-1),(1u64<<dim)-1]{
                    let pair=[(first,first),(second,second),(first,second)];
                    let mut structures=Vec::new();
                    let mut traces=Vec::new();
                    for &(i,j) in &pair{
                        let structure=two_copy_structural::encode(src,&proof,
                            &state,i,j,bad).unwrap();
                        let trace=two_copy_count_trace::emit(src,&proof,&structure).unwrap();
                        structures.push(structure);
                        traces.push(trace);
                    }
                    for (num,den) in [(0,1),(1,2),(1,1)]{
                        let sp=coherent_spec(state.n,(1u64<<first)|(1u64<<second),
                            bad,num,den);
                        let expected_gram=path_coherent_gram(&state,first,second,bad).unwrap();
                        let claim=encode_p8g1_claim(src,&proof,&sp,&expected_gram);
                        let checked=count_to_gram::verify(src,&proof,&sp,
                            [&structures[0],&structures[1],&structures[2]],
                            [&traces[0],&traces[1],&traces[2]],&claim).unwrap();
                        let specification=parse_scg1_spec(&sp).unwrap();
                        assert_eq!(checked.gram,expected_gram);
                        assert_eq!(checked.verdict,
                            gram_psd_verdict(&expected_gram,&specification).unwrap());
                        let dense=dense_oracle::coherent_gram(src,first,second,bad).unwrap();
                        assert_eq!(
                            ((checked.gram.diag0.0 as i128,checked.gram.diag0.1 as i128),
                             (checked.gram.diag1.0 as i128,checked.gram.diag1.1 as i128),
                             checked.gram.off.map(|x|x as i128),checked.gram.h as usize),
                            dense
                        );
                        nodes+=checked.counted_nodes;
                        cases+=1;
                        if cases==1 {
                            let mut forged=claim;forged[112]^=1;
                            assert_eq!(count_to_gram::verify(src,&proof,&sp,
                                [&structures[0],&structures[1],&structures[2]],
                                [&traces[0],&traces[1],&traces[2]],&forged),
                                Err(Error::InvalidProof));
                            let mut forged_trace=traces[0].clone();
                            forged_trace[100]^=1;
                            assert_eq!(count_to_gram::verify(src,&proof,&sp,
                                [&structures[0],&structures[1],&structures[2]],
                                [&forged_trace,&traces[1],&traces[2]],&claim),
                                Err(Error::InvalidProof));
                            assert_eq!(count_to_gram::verify(src,&proof,&sp,
                                [&structures[2],&structures[1],&structures[0]],
                                [&traces[2],&traces[1],&traces[0]],&claim),
                                Err(Error::InvalidProof));
                        }
                    }
                }
            }
        }
        println!("G8D1_COUNT_TO_GRAM circuits=4 exact_compositions={cases} local_proof_nodes={nodes} dense_oracle_matches=true no_enumeration_in_checker=true");
        assert!(cases>=30);
    }
    #[test]
    fn g8d1_export_external_producer_fixtures_when_requested(){
        let Ok(dir)=std::env::var("G8D1_FIXTURE_DIR")else{return;};
        let src=std::fs::read(format!("{dir}/h-1q.qasm")).unwrap();
        let proof=std::fs::read(format!("{dir}/h-1q.p8c1")).unwrap();
        let (_,state)=replay_state(&src,&proof).unwrap();
        let pair=[(0,0),(1,1),(0,1)];
        let mut structures=Vec::new();
        let mut traces=Vec::new();
        for (index,&(i,j)) in pair.iter().enumerate(){
            let structure=two_copy_structural::encode(&src,&proof,&state,i,j,1).unwrap();
            let trace=two_copy_count_trace::emit(&src,&proof,&structure).unwrap();
            std::fs::write(format!("{dir}/gram-{index}.s8c1"),&structure).unwrap();
            std::fs::write(format!("{dir}/gram-{index}.d8c1"),&trace).unwrap();
            structures.push(structure);
            traces.push(trace);
        }
        for (tag,num,den) in [("sat",1,1),("violated",1,2)]{
            let sp=coherent_spec(1,3,1,num,den);
            let gram=path_coherent_gram(&state,0,1,1).unwrap();
            let claim=encode_p8g1_claim(&src,&proof,&sp,&gram);
            std::fs::write(format!("{dir}/gram-{tag}.scg1"),&sp).unwrap();
            std::fs::write(format!("{dir}/gram-{tag}.p8g1"),claim).unwrap();
            let result=count_to_gram::verify(&src,&proof,&sp,
                [&structures[0],&structures[1],&structures[2]],
                [&traces[0],&traces[1],&traces[2]],&claim).unwrap();
            let expected=if tag=="sat" {CoherentVerdict::ScopedSatisfied}
                else {CoherentVerdict::ScopedViolated{reason:"negative_determinant"}};
            assert_eq!(result.verdict,expected);
        }
        println!("G8D1_EXPORTED real_native_source=true verified_count_traces=3 both_property_verdicts=true");
    }
    #[test]
    fn m8d1_symbolic_producer_matches_exhaustive_reference(){
        let examples=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nh q[1];\ncz q[0],q[1];\n".as_slice(),
        ];
        let mut cases=0usize;
        let mut saved=0isize;
        for source in examples{
            let (proof,state)=source_proof_and_state(source);
            let dim=1usize<<state.n;
            for &(first,second) in &[(0,0),(0,1),(1,0),(1,1)]{
                for bad in [1u64,1u64<<(dim-1),(1u64<<dim)-1]{
                    let structure=two_copy_structural::encode(
                        source,&proof,&state,first,second,bad).unwrap();
                    let symbolic=two_copy_count_dag::emit(source,&proof,&structure).unwrap();
                    let exhaustive=two_copy_count_dag::emit_via_exhaustive_tree(
                        source,&proof,&structure).unwrap();
                    let s=two_copy_count_dag::verify(
                        source,&proof,&structure,&symbolic).unwrap();
                    let e=two_copy_count_dag::verify(
                        source,&proof,&structure,&exhaustive).unwrap();
                    assert_eq!(s.buckets,e.buckets);
                    assert_eq!(symbolic,exhaustive,
                        "nonenumerative emitter changed canonical DAG bytes");
                    saved+=exhaustive.len() as isize-symbolic.len() as isize;
                    cases+=1;
                }
            }
        }
        assert_eq!(cases,36);
        assert_eq!(saved,0);
        println!("M8D1_SYMBOLIC_GENERATOR circuits=3 comparisons={cases} exact_canonical_bytes=true no_exhaustive_path_pair_enumeration_in_generator=true");
    }
    #[test]
    fn m8d1_exact_shared_dag_all_root_contexts_and_forgery(){
        let src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nt q[0];\nh q[0];\nt q[0];\nh q[0];\nt q[0];\nh q[0];\nt q[0];\n";
        let (proof,state)=source_proof_and_state(src);
        let structure=two_copy_structural::encode(src,&proof,&state,0,2,15).unwrap();
        let original=two_copy_count_trace::emit(src,&proof,&structure).unwrap();
        let dag=two_copy_count_dag::emit(src,&proof,&structure).unwrap();
        let tree=two_copy_count_trace::verify(src,&proof,&structure,&original).unwrap();
        let checked=two_copy_count_dag::verify(src,&proof,&structure,&dag).unwrap();
        assert_eq!(tree.buckets,[0;8]);
        assert_eq!(checked.buckets,tree.buckets);
        assert_eq!(checked.nodes,1);
        assert_eq!(checked.contexts,8);
        assert_eq!(checked.shared_contexts,7);
        let(mut rejected,mut retained)=(0usize,0usize);
        for i in 0..dag.len(){
            for bit in 0..8{
                let mut forged=dag.clone();forged[i]^=1u8<<bit;
                if two_copy_count_dag::verify(src,&proof,&structure,&forged).is_err(){
                    rejected+=1;
                }else{retained+=1;}
            }
        }
        // The canonical 1-node/8-root proof has no alternate valid
        // single-bit encoding, so all bit-level changes are rejected.
        assert_eq!(retained,0);
        assert_eq!(rejected,dag.len()*8);
        let mut changed=structure.clone();changed[3]^=1;
        assert_eq!(two_copy_count_dag::verify(src,&proof,&changed,&dag),
            Err(Error::InvalidProof));
        println!("M8D1_SHARED_FALSE_CUBE h=4 original_tree_nodes=8 unique_dag_nodes={} contexts={} shared_contexts={} tree_bytes={} dag_bytes={} forged_bits={} accepted=0",checked.nodes,checked.contexts,checked.shared_contexts,original.len(),dag.len(),rejected);
    }
    #[test]
    fn m8d1_exact_counts_differential_vs_d8c1_and_canonical_cnf(){
        let sources=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nh q[1];\ncz q[0],q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[3] q;\nh q[0];\ncx q[0],q[2];\nh q[1];\nt q[2];\ns q[1];\n".as_slice(),
        ];
        let mut cases=0usize;
        let mut contexts=0usize;
        let mut shared=0usize;
        let mut saved_bytes=0isize;
        for src in sources{
            let(proof,state)=source_proof_and_state(src);
            let dim=1usize<<state.n;
            for (first,second) in [(0,0),(0,1),(1,0),(1,1)]{
                for bad in [1u64,1u64<<(dim-1),(1u64<<dim)-1]{
                    let structure=two_copy_structural::encode(src,&proof,
                        &state,first,second,bad).unwrap();
                    let original=two_copy_count_trace::emit(src,&proof,&structure).unwrap();
                    let dag=two_copy_count_dag::emit(src,&proof,&structure).unwrap();
                    let tree=two_copy_count_trace::verify(src,&proof,&structure,&original).unwrap();
                    let checked=two_copy_count_dag::verify(src,&proof,&structure,&dag).unwrap();
                    assert_eq!(checked.buckets,tree.buckets);
                    assert_eq!(checked.buckets,two_copy_cnf::count_models(
                        &two_copy_cnf::build(&state,first,second,bad).unwrap()
                    ).unwrap());
                    cases+=1;
                    contexts+=checked.contexts;
                    shared+=checked.shared_contexts;
                    saved_bytes+=original.len() as isize-dag.len() as isize;
                }
            }
        }
        assert_eq!(cases,48);
        println!("M8D1_COUNT_DAG_DIFF obligations={cases} checked_contexts={contexts} shared_contexts={shared} cumulative_byte_savings={saved_bytes} all_eight_buckets_match=true no_primary_enumeration_in_checker=true");
    }
    #[test]
    fn m8d1_export_external_producer_fixture_when_requested(){
        let Ok(dir)=std::env::var("M8D1_FIXTURE_DIR")else{return;};
        let src=std::fs::read(format!("{dir}/h-1q.qasm")).unwrap();
        let proof=std::fs::read(format!("{dir}/h-1q.p8c1")).unwrap();
        let structure=std::fs::read(format!("{dir}/h-1q.s8c1")).unwrap();
        let dag=two_copy_count_dag::emit(&src,&proof,&structure).unwrap();
        let v=two_copy_count_dag::verify(&src,&proof,&structure,&dag).unwrap();
        assert_eq!(v.buckets,[1,0,0,0,0,0,0,0]);
        std::fs::write(format!("{dir}/h-1q.m8d1"),&dag).unwrap();
        let mut fake=dag.clone();
        fake[40]^=1;
        std::fs::write(format!("{dir}/h-1q-forged.m8d1"),&fake).unwrap();
        println!("M8D1_EXPORTED source_bound=true dag_nodes={} shared_contexts={} dag_bytes={}",v.nodes,v.shared_contexts,dag.len());
    }
    #[test]
    fn d8c1_differential_trace_buckets_vs_canonical_count(){
        let sources=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nh q[1];\ncz q[0],q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[3] q;\nh q[0];\ncx q[0],q[2];\nh q[1];\nt q[2];\ns q[1];\n".as_slice(),
        ];
        let mut cases=0;
        let mut nodes=0;
        for src in sources{
            let (proof,state)=source_proof_and_state(src);
            let dim=1usize<<state.n;
            for (a,b) in [(0,0),(0,1),(1,0),(1,1)]{
                for bad in [1u64,1u64<<(dim-1),(1u64<<dim)-1]{
                    let structural=two_copy_structural::encode(
                        src,&proof,&state,a,b,bad).unwrap();
                    let trace=two_copy_count_trace::emit(
                        src,&proof,&structural).unwrap();
                    let verified=two_copy_count_trace::verify(
                        src,&proof,&structural,&trace).unwrap();
                    let old=two_copy_cnf::count_models(
                        &two_copy_cnf::build(&state,a,b,bad).unwrap()
                    ).unwrap();
                    assert_eq!(verified.buckets,old);
                    cases+=1;nodes+=verified.stats.nodes;
                }
            }
        }
        assert_eq!(cases,48);
        println!("D8C1_DIFF_COUNT_TRACE obligations={cases} checked_local_nodes={nodes} exact_eight_bucket_matches=true nonenumerative_checker=true");
    }
    #[test]
    fn d8c1_export_native_source_linked_fixture_when_requested(){
        let Ok(dir)=std::env::var("D8C1_FIXTURE_DIR")else{return;};
        let src=std::fs::read(format!("{dir}/h-1q.qasm")).unwrap();
        let proof=std::fs::read(format!("{dir}/h-1q.p8c1")).unwrap();
        let structural=std::fs::read(format!("{dir}/h-1q.s8c1")).unwrap();
        let trace=two_copy_count_trace::emit(&src,&proof,&structural).unwrap();
        assert_eq!(two_copy_count_trace::verify(
            &src,&proof,&structural,&trace).unwrap().buckets,
            [1,0,0,0,0,0,0,0]);
        std::fs::write(format!("{dir}/h-1q.d8c1"),&trace).unwrap();
        let mut forged=trace.clone();forged[trace.len()-1]^=1;
        std::fs::write(format!("{dir}/h-1q-forged.d8c1"),&forged).unwrap();
        println!("D8C1_EXPORTED source_linked=true trace_bytes={} all_eight_buckets=true",
            trace.len());
    }
    #[test]
    fn s8c1_export_external_producer_fixtures_when_requested(){
        let Ok(dir)=std::env::var("S8C1_FIXTURE_DIR") else {return;};
        let src=std::fs::read(format!("{dir}/h-1q.qasm")).unwrap();
        let proof=std::fs::read(format!("{dir}/h-1q.p8c1")).unwrap();
        let (_,state)=replay_state(&src,&proof).unwrap();
        let bytes=two_copy_structural::encode(&src,&proof,&state,0,1,1).unwrap();
        assert_eq!(two_copy_structural::verify(&src,&proof,&bytes).unwrap(),
            [1,0,0,0,0,0,0,0]);
        std::fs::write(format!("{dir}/h-1q.s8c1"),&bytes).unwrap();
        let mut corrupted=bytes.clone();
        corrupted[bytes.len()/2]^=1;
        std::fs::write(format!("{dir}/h-1q-forged.s8c1"),&corrupted).unwrap();
        println!("S8C1_EXPORTED real_native_source=true root_bucket=0 proof_bytes={}",bytes.len());
    }
    #[test]
    fn checked_surd_psd_overflow_returns_unknown_not_a_proof(){
        // In the older unguarded determinant check these would overflow
        // i128, potentially panicking or wrapping the proof verdict.
        assert_eq!(
            checked_nonpositive_quadratic(i128::MAX,-i128::MAX),
            Err(Error::UnknownResource)
        );
        assert_eq!(checked_nonpositive_quadratic(1,-1),Ok(true));
        assert_eq!(checked_nonpositive_quadratic(2,-1),Ok(false));
        assert_eq!(checked_nonnegative_quadratic(1,0),Ok(true));
        assert_eq!(checked_nonnegative_quadratic(-1,0),Ok(false));
        let spec=parse_scg1_spec(&coherent_spec(1,3,1,0,1)).unwrap();
        // A single i64::MAX coefficient has a representable i128 square:
        // it is a definite negative determinant, not an overflow.
        let representable=CoherentGram{
            n:1,h:8,first:0,second:1,bad_mask:1,
            diag0:(0,0),diag1:(0,0),
            off:[i64::MAX,0,0,0]
        };
        assert_eq!(
            gram_psd_verdict(&representable,&spec),
            Ok(CoherentVerdict::ScopedViolated{reason:"negative_determinant"})
        );
        // Several such coefficients require a sum of squared terms beyond
        // i128. This must fail closed with UNKNOWN_RESOURCE, never panic.
        let oversized=CoherentGram{
            off:[i64::MAX,i64::MAX,i64::MAX,i64::MAX],
            ..representable
        };
        assert_eq!(gram_psd_verdict(&oversized,&spec),Err(Error::UnknownResource));
        let (src,_) = example_h();
        let half=coherent_spec(1,3,1,1,2);
        let (_,claim,gram,parsed)=coherent_fixture(&src,&half);
        assert_eq!(claim.len(),P8G1_BYTES);
        assert_eq!(
            gram_psd_verdict(&gram,&parsed),
            Ok(CoherentVerdict::ScopedViolated{reason:"negative_determinant"})
        );
        println!("P8G1_FIXED_PRECISION_OVERFLOW=unknown_resource no_wrapped_psd_claim=true");
    }
    #[test]
    fn coherent_rank_two_gram_psd_exact_and_mutations(){
        let (src,_) = example_h();
        let spec_half=coherent_spec(1,3,1,1,2);
        let(proof,claim,gram,parsed)=coherent_fixture(&src,&spec_half);
        assert_eq!(gram.diag0,(1,0));
        assert_eq!(gram.diag1,(1,0));
        assert_eq!(gram.off,[1,0,0,0]);
        assert_eq!(gram.h,1);
        assert_eq!(verify_p8g1_coherent(&src,&proof,&spec_half,&claim),
            Ok(CoherentVerdict::ScopedViolated{reason:"negative_determinant"}));
        assert_eq!(gram_psd_verdict(&gram,&parsed).unwrap(),
            CoherentVerdict::ScopedViolated{reason:"negative_determinant"});
        let spec_full=coherent_spec(1,3,1,1,1);
        let (proof_full,claim_full,_,_)=coherent_fixture(&src,&spec_full);
        assert_eq!(verify_p8g1_coherent(&src,&proof_full,&spec_full,&claim_full),
            Ok(CoherentVerdict::ScopedSatisfied));
        let spec_zero=coherent_spec(1,3,1,0,1);
        let(proof_zero,claim_zero,_,_)=coherent_fixture(&src,&spec_zero);
        assert_eq!(verify_p8g1_coherent(&src,&proof_zero,&spec_zero,&claim_zero),
            Ok(CoherentVerdict::ScopedViolated{reason:"negative_diagonal_0"}));
        // All 1-bit changes of an accepted Gram claim must fail closed.
        let mut changes=0usize;
        for index in 0..claim_full.len(){
            for shift in 0..8 {
                let mut forged=claim_full;
                forged[index]^=1u8<<shift;
                assert!(verify_p8g1_coherent(&src,&proof_full,&spec_full,&forged).is_err(),
                    "rank-two certificate single-bit mutation admitted at {index}:{shift}");
                changes+=1;
            }
        }
        assert_eq!(changes,P8G1_BYTES*8);
        let mut bad=claim_full;
        bad[112]^=1;
        assert_eq!(verify_p8g1_coherent(&src,&proof_full,&spec_full,&bad),
            Err(Error::InvalidProof));
        assert_eq!(verify_p8g1_coherent(&src,&proof_full,&spec_half,&claim_full),
            Err(Error::InvalidProof));
        let wrong=coherent_spec(1,1,1,1,1);
        assert_eq!(parse_scg1_spec(&wrong).unwrap_err(),Error::InvalidSource);
        let wrong=coherent_spec(1,3,1,2,4);
        assert_eq!(parse_scg1_spec(&wrong).unwrap_err(),Error::InvalidSource);
        println!("P8G1_RANK2_H_EXACT diag=1,1 off=1 h=1 delta_half=violation_det delta_one=sat delta_zero=negative_diagonal mutations={changes} accepted=0");
    }
    #[test]
    fn coherent_rank_two_surds_and_independent_dense_gram(){
        let corpus=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\nt q[0];\ns q[1];\ncz q[0],q[1];\n".as_slice(),
        ];
        let mut cases=0;
        for src in corpus {
            let(n,_)=parse_source(src).unwrap();
            let (proof,state)=source_proof_and_state(src);
            let span=3u64;
            let first=0;
            let second=1;
            let bad=if n==1{1u64}else{9u64};
            let gram=path_coherent_gram(&state,first,second,bad).unwrap();
            let dense=dense_oracle::coherent_gram(src,first,second,bad).unwrap();
            assert_eq!(
                ((gram.diag0.0 as i128,gram.diag0.1 as i128),
                 (gram.diag1.0 as i128,gram.diag1.1 as i128),
                 gram.off.map(|x|x as i128),gram.h as usize),
                dense
            );
            for (num,den) in [(0,1),(1,8),(1,4),(1,2),(1,1)]{
                let spec=coherent_spec(n,span,bad,num,den);
                let parsed=parse_scg1_spec(&spec).unwrap();
                let claim=encode_p8g1_claim(src,&proof,&spec,&gram);
                let actual=verify_p8g1_coherent(src,&proof,&spec,&claim).unwrap();
                assert_eq!(
                    actual==CoherentVerdict::ScopedSatisfied,
                    dense_oracle::coherent_psd(dense,num as i128,den as i128)
                );
                assert_eq!(actual,gram_psd_verdict(&gram,&parsed).unwrap());
            }
            cases+=1;
        }
        assert_eq!(cases,3);
        println!("P8G1_DENSE_GRAM_EXACT circuits={cases} risk_thresholds=15 all_match=true");
    }


    #[test]
    fn explicit_coherent_witness_exact_and_dense(){
        let(source,_)=example_h();
        let mut checks=0usize;
        for (num,den,reason) in [
            (0,1,"negative_diagonal_0"),
            (1,2,"negative_determinant"),
            (3,4,"negative_determinant"),
        ] {
            let spec_bytes=coherent_spec(1,3,1,num,den);
            let (proof,gram_bytes,gram,spec)=coherent_fixture(&source,&spec_bytes);
            assert_eq!(verify_p8g1_coherent(&source,&proof,&spec_bytes,&gram_bytes),
                Ok(CoherentVerdict::ScopedViolated{reason}));
            let witness=derive_coherent_witness(&gram,&spec).unwrap();
            let encoded=encode_p8w1(&gram_bytes,&witness);
            let (decoded,gap)=verify_p8w1_witness(
                &source,&proof,&spec_bytes,&gram_bytes,&encoded
            ).unwrap();
            assert_eq!(decoded,witness);
            assert!(checked_nonpositive_quadratic(gap.0,gap.1).unwrap()&&gap!=(0,0));
            let independent=dense_oracle::coherent_witness_excess(
                &source,spec.first,spec.second,spec.bad_mask,
                spec.delta_num,spec.delta_den,
                witness.input0.map(|x|x as i128),
                witness.input1.map(|x|x as i128)
            ).unwrap();
            assert_eq!(independent.0,(
                witness.norm.0 as i128,witness.norm.1 as i128));
            assert_eq!(
                (gap.0,gap.1),
                (-independent.1.0,-independent.1.1)
            );
            assert!(dense_oracle::coherent_witness_is_violation(
                &source,spec.first,spec.second,spec.bad_mask,
                spec.delta_num,spec.delta_den,
                witness.input0.map(|x|x as i128),
                witness.input1.map(|x|x as i128)
            ).unwrap());
            checks+=1;
        }
        // This sound constructor need not output a specific eigenvector.
        // For H/half, 8|0>+4|1> normalizes to
        // (2|0>+|1>)/sqrt(5) and has risk 9/10 > 1/2.
        let spec_bytes=coherent_spec(1,3,1,1,2);
        let(proof,claim,gram,spec)=coherent_fixture(&source,&spec_bytes);
        let w=derive_coherent_witness(&gram,&spec).unwrap();
        assert_eq!(w.input0,[8,0,0,0]);
        assert_eq!(w.input1,[4,0,0,0]);
        assert_eq!(w.norm,(80,0));
        let(_,gap)=verify_p8w1_witness(&source,&proof,&spec_bytes,
            &claim,&encode_p8w1(&claim,&w)).unwrap();
        assert_eq!(gap,(-128,0));
        println!("P8W1_CONSTRUCTIVE_EXACT cases={checks} direct_dense_oracle=true normalized_symbolic=true witness_risk_nine_tenths=true");
    }
    #[test]
    fn explicit_coherent_witness_all_bits_forged_and_sat_rejected(){
        let(source,_)=example_h();
        let spec_bytes=coherent_spec(1,3,1,1,2);
        let(proof,claim,gram,spec)=coherent_fixture(&source,&spec_bytes);
        let witness=derive_coherent_witness(&gram,&spec).unwrap();
        let bytes=encode_p8w1(&claim,&witness);
        assert!(verify_p8w1_witness(&source,&proof,&spec_bytes,&claim,&bytes).is_ok());
        let mut rejects=0usize;
        for byte in 0..P8W1_BYTES{
            for bit in 0..8{
                let mut forged=bytes;
                forged[byte]^=1u8<<bit;
                assert!(verify_p8w1_witness(
                    &source,&proof,&spec_bytes,&claim,&forged
                ).is_err(),"forged P8W1 accepted {byte}:{bit}");
                rejects+=1;
            }
        }
        assert_eq!(rejects,928);
        let spec_sat=coherent_spec(1,3,1,1,1);
        let(proof_sat,claim_sat,gram_sat,parsed_sat)=coherent_fixture(&source,&spec_sat);
        assert_eq!(derive_coherent_witness(&gram_sat,&parsed_sat),
            Err(Error::InvalidProof));
        assert_eq!(verify_p8w1_witness(&source,&proof_sat,&spec_sat,
            &claim_sat,&bytes),Err(Error::InvalidProof));
        let mut fake=bytes;
        fake[36..44].copy_from_slice(&0i64.to_le_bytes());
        assert_eq!(verify_p8w1_witness(&source,&proof,&spec_bytes,
            &claim,&fake),Err(Error::InvalidProof));
        let mut fake=bytes;
        fake[100..108].copy_from_slice(&1i64.to_le_bytes());
        assert_eq!(verify_p8w1_witness(&source,&proof,&spec_bytes,
            &claim,&fake),Err(Error::InvalidProof));
        assert_eq!(verify_p8w1_witness(&source,&proof,&spec_bytes,
            &claim,&bytes[..bytes.len()-1]),Err(Error::InvalidProof));
        println!("P8W1_MUTATION_EXHAUSTIVE bytes=116 flips={rejects} accepted=0 sat_claim_rejected=true");
    }



    #[test]
    fn f8c1_bounded_end_to_end_source_to_exact_count_chain(){
        let cases=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n",
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\nh q[1];\ncz q[0],q[1];\ns q[0];\ngphase(pi/4);\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[3] q;\nh q[0];\ncx q[0],q[2];\nh q[1];\nt q[2];\ns q[1];\nx q[0];\ncz q[0],q[1];\nh q[2];\n".as_slice(),
        ];
        let mut cases_checked=0usize;
        let mut prefixes=0usize;
        let mut root_checks=0usize;
        for src in cases {
            let (p8,state)=source_proof_and_state(src);
            let dim=1usize<<state.n;
            for &(first,second) in &[(0usize,0usize),(0,1),(1,0)]{
                for bad in [1u64,1u64<<(dim-1)]{
                    let s8=two_copy_structural::encode(
                        src,&p8,&state,first,second,bad).unwrap();
                    let dag=two_copy_count_dag::emit(src,&p8,&s8).unwrap();
                    let bundle=f8c1_chain::encode(src,&p8,&s8,&dag).unwrap();
                    let got=f8c1_chain::verify(
                        src,&p8,&s8,&dag,&bundle).unwrap();
                    assert_eq!(got.method,1);
                    assert_eq!((got.first,got.second,got.bad),(first,second,bad));
                    assert_eq!(got.buckets,
                        two_copy_count_dag::verify(src,&p8,&s8,&dag).unwrap().buckets);
                    let tree=two_copy_count_trace::emit(src,&p8,&s8).unwrap();
                    let tree_bundle=f8c1_chain::encode(src,&p8,&s8,&tree).unwrap();
                    let tree_got=f8c1_chain::verify(
                        src,&p8,&s8,&tree,&tree_bundle).unwrap();
                    assert_eq!(got.buckets,tree_got.buckets);
                    assert_eq!(tree_got.method,0);
                    cases_checked+=2;
                    prefixes+=got.prefix_checks;
                    assert_eq!(got.pair_checks,0);
                    root_checks+=got.root_checks;
                }
            }
        }
        assert_eq!(cases_checked,48);
        println!(
            "F8C1_BOUNDED_CHAIN_EXACT bundles={cases_checked} \
             source_symbolic_checks={prefixes} root_symbolic_checks={root_checks} assignment_enumeration=0 \
             methods=M8D1_D8C1 exact_source_semantics=true full_source_trust=BLOCKED"
        );
    }
    #[test]
    fn f8c1_bundle_mutations_and_semantic_scope_fail_closed(){
        let src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n";
        let (proof,state)=source_proof_and_state(src);
        let structural=two_copy_structural::encode(
            src,&proof,&state,0,1,1).unwrap();
        let dag=two_copy_count_dag::emit(src,&proof,&structural).unwrap();
        let accepted=f8c1_chain::encode(src,&proof,&structural,&dag).unwrap();
        assert!(f8c1_chain::verify(
            src,&proof,&structural,&dag,&accepted).is_ok());
        let mut rejections=0usize;
        for i in 0..accepted.len(){
            for bit in 0..8{
                let mut forged=accepted.clone();
                forged[i]^=1<<bit;
                assert_eq!(
                    f8c1_chain::verify(src,&proof,&structural,&dag,&forged),
                    Err(Error::InvalidProof),
                    "single-bit F8C1 forgery accepted at byte {i}, bit {bit}");
                rejections+=1;
            }
        }
        assert!(f8c1_chain::verify(
            &src[..src.len()-1],&proof,&structural,&dag,&accepted).is_err());
        let mut badproof=proof.clone();badproof[8]^=1;
        assert!(f8c1_chain::verify(
            src,&badproof,&structural,&dag,&accepted).is_err());
        let mut bads8=structural.clone();bads8[74]^=1;
        assert!(f8c1_chain::verify(
            src,&proof,&bads8,&dag,&accepted).is_err());
        let mut badcount=dag.clone();badcount[dag.len()-1]^=1;
        assert!(f8c1_chain::verify(
            src,&proof,&structural,&badcount,&accepted).is_err());
        assert_eq!(f8c1_chain::verify(
            src,&proof,&structural,&dag,&accepted[..accepted.len()-1]),
            Err(Error::InvalidProof));
        for unsupported in [
            b"OPENQASM 3.1;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nU(2*pi,0,0) q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nctrl @ x q[0];\n".as_slice(),
        ] {
            assert_eq!(
                f8c1_chain::verify(unsupported,&proof,&structural,&dag,&accepted),
                Err(Error::InvalidProof),
                "changed source must invalidate source-bound envelope");
            assert_eq!(
                f8c1_chain::encode(unsupported,&proof,&structural,&dag),
                Err(Error::UnsupportedSource),
                "unsupported versions or gates must not be re-admitted");
        }
        println!(
            "F8C1_FORGERY_REJECTED bit_flips={rejections} \
             source_proof_structure_count_mutations=true \
             unsupported_source_fail_closed=true"
        );
    }
    #[test]
    fn f8c1_export_source_bound_fixture_when_requested(){
        let Ok(dir)=std::env::var("F8C1_FIXTURE_DIR")else{return;};
        let src=std::fs::read(format!("{dir}/h-1q.qasm")).unwrap();
        let proof=std::fs::read(format!("{dir}/h-1q.p8c1")).unwrap();
        let structure=std::fs::read(format!("{dir}/h-1q.s8c1")).unwrap();
        let trace=std::fs::read(format!("{dir}/h-1q.m8d1")).unwrap();
        let envelope=f8c1_chain::encode(&src,&proof,&structure,&trace).unwrap();
        let checked=f8c1_chain::verify(
            &src,&proof,&structure,&trace,&envelope).unwrap();
        assert_eq!(checked.buckets,[1,0,0,0,0,0,0,0]);
        std::fs::write(format!("{dir}/h-1q.f8c1"),&envelope).unwrap();
        let mut tampered=envelope.clone();tampered[40]^=1;
        std::fs::write(format!("{dir}/h-1q-forged.f8c1"),&tampered).unwrap();
        println!(
            "F8C1_EXPORTED source_symbolic_checks={} root_symbolic_checks={} assignment_enumeration=0 \
             envelope_bytes={} source_trust=BLOCKED",
            checked.prefix_checks,checked.pair_checks,envelope.len()
        );
    }


    #[test]
    fn f8g1_three_source_count_proofs_to_rank2_exact_psd_and_witness(){
        let sources=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n".as_slice(),
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\n".as_slice(),
        ];
        let mut checks=0usize;
        let mut witness_cases=0usize;
        let mut sat_cases=0usize;
        for src in sources{
            let (p8,state)=source_proof_and_state(src);
            for (num,den) in [(0usize,1usize),(1,1)]{
                let spec=coherent_spec(state.n,3,1,num,den);
                let parsed=parse_scg1_spec(&spec).unwrap();
                let exact=path_coherent_gram(
                    &state,parsed.first,parsed.second,parsed.bad_mask).unwrap();
                let claim=encode_p8g1_claim(src,&p8,&spec,&exact);
                let verdict=gram_psd_verdict(&exact,&parsed).unwrap();
                let witness=match verdict{
                    CoherentVerdict::ScopedSatisfied=>Vec::new(),
                    CoherentVerdict::ScopedViolated{..}=>{
                        encode_p8w1(&claim,&derive_coherent_witness(&exact,&parsed).unwrap()).to_vec()
                    }
                };
                let pair=[
                    (parsed.first,parsed.first),
                    (parsed.second,parsed.second),
                    (parsed.first,parsed.second)
                ];
                for method in 0..3 {
                    // D8C1-only, M8D1-only, and mixed independent
                    // certified counts are all accepted if correctly linked.
                    let mut structures=Vec::new();
                    let mut traces=Vec::new();
                    let mut bundles=Vec::new();
                    for (slot,&(i,j)) in pair.iter().enumerate(){
                        let s8=two_copy_structural::encode(
                            src,&p8,&state,i,j,parsed.bad_mask).unwrap();
                        let use_dag=method==1 || (method==2 && slot!=1);
                        let trace=if use_dag{
                            two_copy_count_dag::emit(src,&p8,&s8).unwrap()
                        }else{
                            two_copy_count_trace::emit(src,&p8,&s8).unwrap()
                        };
                        let f8=f8c1_chain::encode(src,&p8,&s8,&trace).unwrap();
                        structures.push(s8);
                        traces.push(trace);
                        bundles.push(f8);
                    }
                    let ss=[&structures[0][..],&structures[1][..],&structures[2][..]];
                    let tt=[&traces[0][..],&traces[1][..],&traces[2][..]];
                    let ff=[&bundles[0][..],&bundles[1][..],&bundles[2][..]];
                    let f8g=f8g1_property::encode(src,&p8,&spec,ss,tt,ff,&claim,&witness).unwrap();
                    let result=f8g1_property::verify(
                        src,&p8,&spec,ss,tt,ff,&claim,&witness,&f8g).unwrap();
                    assert_eq!(result.verdict,verdict);
                    assert_eq!(f8g.len(),454);
                    assert!(result.prefix_checks>0 && result.root_checks==24);
                    if verdict==CoherentVerdict::ScopedSatisfied{
                        assert_eq!(result.witness_gap,None);
                        sat_cases+=1;
                    }else{
                        assert!(result.witness_gap.is_some());
                        witness_cases+=1;
                    }
                    checks+=1;
                }
            }
        }
        assert_eq!(checks,18);
        assert_eq!((sat_cases,witness_cases),(9,9));
        println!(
            "F8G1_RANK2_SOURCE_SPEC_CHAIN cases={checks} sat={sat_cases} \
             violated_with_normalized_witness={witness_cases} \
             methods=D8C1_M8D1_mixed exact_cyclotomic_psd=true source_trust=BLOCKED"
        );
    }
    #[test]
    fn f8g1_source_spec_three_counts_gram_witness_forgery_fail_closed(){
        let src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n";
        let (p8,state)=source_proof_and_state(src);
        let spec=coherent_spec(1,3,1,1,2);
        let parsed=parse_scg1_spec(&spec).unwrap();
        let gram=path_coherent_gram(&state,0,1,1).unwrap();
        let claim=encode_p8g1_claim(src,&p8,&spec,&gram);
        let witness=encode_p8w1(&claim,&derive_coherent_witness(&gram,&parsed).unwrap());
        let pair=[(0usize,0usize),(1,1),(0,1)];
        let mut structures=Vec::new();
        let mut traces=Vec::new();
        let mut bundles=Vec::new();
        for &(i,j) in &pair{
            let s8=two_copy_structural::encode(src,&p8,&state,i,j,1).unwrap();
            let dag=two_copy_count_dag::emit(src,&p8,&s8).unwrap();
            let f8=f8c1_chain::encode(src,&p8,&s8,&dag).unwrap();
            structures.push(s8);traces.push(dag);bundles.push(f8);
        }
        let ss=[&structures[0][..],&structures[1][..],&structures[2][..]];
        let tt=[&traces[0][..],&traces[1][..],&traces[2][..]];
        let ff=[&bundles[0][..],&bundles[1][..],&bundles[2][..]];
        let envelope=f8g1_property::encode(
            src,&p8,&spec,ss,tt,ff,&claim,&witness).unwrap();
        let accepted=f8g1_property::verify(
            src,&p8,&spec,ss,tt,ff,&claim,&witness,&envelope).unwrap();
        assert!(matches!(accepted.verdict,CoherentVerdict::ScopedViolated{..}));
        let mut flipped=0usize;
        for index in 0..envelope.len(){
            for bit in 0..8{
                let mut forged=envelope.clone();
                forged[index]^=1u8<<bit;
                assert!(f8g1_property::verify(
                    src,&p8,&spec,ss,tt,ff,&claim,&witness,&forged).is_err());
                flipped+=1;
            }
        }
        assert_eq!(flipped,3632);
        assert!(f8g1_property::verify(
            src,&p8,&spec,ss,tt,ff,&claim,&[],&envelope).is_err());
        let changed_spec=coherent_spec(1,3,1,1,1);
        assert!(f8g1_property::verify(
            src,&p8,&changed_spec,ss,tt,ff,&claim,&witness,&envelope).is_err());
        let mut changed_gram=claim;
        changed_gram[112]^=1;
        assert!(f8g1_property::verify(
            src,&p8,&spec,ss,tt,ff,&changed_gram,&witness,&envelope).is_err());
        let mut changed_witness=witness;
        changed_witness[36]^=1;
        assert!(f8g1_property::verify(
            src,&p8,&spec,ss,tt,ff,&claim,&changed_witness,&envelope).is_err());
        let mixed_ss=[ss[2],ss[1],ss[0]];
        assert!(f8g1_property::verify(
            src,&p8,&spec,mixed_ss,tt,ff,&claim,&witness,&envelope).is_err());
        let swapped_traces=[tt[2],tt[1],tt[0]];
        assert!(f8g1_property::verify(
            src,&p8,&spec,ss,swapped_traces,ff,&claim,&witness,&envelope).is_err());
        let mut changed_p8=p8.clone();changed_p8[8]^=1;
        assert!(f8g1_property::verify(
            src,&changed_p8,&spec,ss,tt,ff,&claim,&witness,&envelope).is_err());
        let changed_src=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nx q[0];\n";
        assert!(f8g1_property::verify(
            changed_src,&p8,&spec,ss,tt,ff,&claim,&witness,&envelope).is_err());
        let mut modified_f8=bundles[0].clone();
        modified_f8[37]^=1;
        let changed_ff=[modified_f8.as_slice(),ff[1],ff[2]];
        assert!(f8g1_property::verify(
            src,&p8,&spec,ss,tt,changed_ff,&claim,&witness,&envelope).is_err());
        assert!(f8g1_property::verify(
            src,&p8,&spec,ss,tt,ff,&claim,&witness,&envelope[..envelope.len()-1]).is_err());
        let sat_spec=coherent_spec(1,3,1,1,1);
        let sat_claim=encode_p8g1_claim(src,&p8,&sat_spec,&gram);
        assert!(f8g1_property::encode(
            src,&p8,&sat_spec,ss,tt,ff,&sat_claim,&witness).is_err(),
            "SAT property must not carry an UNSAFE witness");
        println!(
            "F8G1_FORGERY_REJECTION flips={flipped} accepted=0 \
             source_spec_count_order_gram_witness_checked=true \
             missing_witness_rejected=true fail_closed=true"
        );
    }
    #[test]
    fn f8g1_export_cross_binary_rank2_fixtures_when_requested(){
        let Ok(dir)=std::env::var("F8G1_FIXTURE_DIR")else{return;};
        let src=std::fs::read(format!("{dir}/h-1q.qasm")).unwrap();
        let p8=std::fs::read(format!("{dir}/h-1q.p8c1")).unwrap();
        let mut structs=Vec::new();let mut counts=Vec::new();let mut f8s=Vec::new();
        for index in 0..3{
            let ss=std::fs::read(format!("{dir}/gram-{index}.s8c1")).unwrap();
            let dd=std::fs::read(format!("{dir}/gram-{index}.d8c1")).unwrap();
            let ff=f8c1_chain::encode(&src,&p8,&ss,&dd).unwrap();
            std::fs::write(format!("{dir}/gram-{index}.f8c1"),&ff).unwrap();
            structs.push(ss);counts.push(dd);f8s.push(ff);
        }
        let ss=[structs[0].as_slice(),structs[1].as_slice(),structs[2].as_slice()];
        let cc=[counts[0].as_slice(),counts[1].as_slice(),counts[2].as_slice()];
        let ff=[f8s[0].as_slice(),f8s[1].as_slice(),f8s[2].as_slice()];
        let (_,state)=replay_state(&src,&p8).unwrap();
        let gram=path_coherent_gram(&state,0,1,1).unwrap();
        for tag in ["sat","violated"]{
            let spec=std::fs::read(format!("{dir}/gram-{tag}.scg1")).unwrap();
            let claim=std::fs::read(format!("{dir}/gram-{tag}.p8g1")).unwrap();
            let parsed=parse_scg1_spec(&spec).unwrap();
            let witness=if tag=="violated"{
                encode_p8w1(&claim,&derive_coherent_witness(&gram,&parsed).unwrap()).to_vec()
            }else{Vec::new()};
            std::fs::write(format!("{dir}/gram-{tag}.p8w1"),&witness).unwrap();
            let envelope=f8g1_property::encode(
                &src,&p8,&spec,ss,cc,ff,&claim,&witness).unwrap();
            let checked=f8g1_property::verify(
                &src,&p8,&spec,ss,cc,ff,&claim,&witness,&envelope).unwrap();
            assert_eq!(tag=="sat",checked.verdict==CoherentVerdict::ScopedSatisfied);
            std::fs::write(format!("{dir}/gram-{tag}.f8g1"),&envelope).unwrap();
            if tag=="violated"{
                let mut forged=envelope.clone();forged[70]^=1;
                std::fs::write(format!("{dir}/gram-violated-forged.f8g1"),&forged).unwrap();
            }
        }
        println!("F8G1_EXPORTED_SOURCE_SPEC_RANK2 sat=true violated=true independent_full_chain=true");
    }

    #[test]
    fn c8c1_source_bound_cnf_cross_checks(){
        let source=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\n";
        let (proof,state)=source_proof_and_state(source);
        let mut count=0usize;
        for first in 0..4 {
            for second in 0..4 {
                for bad_mask in [1u64,2,8,15] {
                    let candidate=two_copy_cnf::build(
                        &state,first,second,bad_mask
                    ).unwrap();
                    let bytes=two_copy_cnf::encode(source,&proof,&candidate).unwrap();
                    let (cnf,enum_counts)=two_copy_cnf::verify(source,&proof,&bytes).unwrap();
                    assert_eq!(cnf,enum_counts);
                    assert_eq!(cnf,two_copy_wmc::enumerate_pairs(
                        &state,first,second,bad_mask
                    ).unwrap().buckets);
                    count+=1;
                    if count==1 {
                        let mut fake=bytes.clone();
                        fake[0]^=1;
                        assert!(two_copy_cnf::verify(source,&proof,&fake).is_err());
                        fake=bytes.clone();
                        fake.pop();
                        assert!(two_copy_cnf::verify(source,&proof,&fake).is_err());
                        fake=bytes.clone();
                        fake[79+2]^=1;
                        assert!(two_copy_cnf::verify(source,&proof,&fake).is_err());
                        fake=bytes.clone();
                        fake.extend_from_slice(&[0,0]);
                        assert!(two_copy_cnf::verify(source,&proof,&fake).is_err());
                    }
                }
            }
        }
        assert_eq!(count,64);
        println!("C8C1_SOURCE_BOUND_CNF obligations={count} checked_exact_models=true tamper_reject=4 non_scalable=true");
    }


    // Finite, test-only proof obligation: unlike the P8C1 replay and S8C1
    // builder, this oracle decodes original source lines and executes
    // *individual coherent paths*, without constructing ANF/Z8 polynomials.
    // Do not promote this bounded audit to general QASM SourceTrust.
    fn raw_source_path_semantics(
        bytes:&[u8],input:usize,path_assignment:usize
    )->(usize,usize,usize){
        fn source_wire(token:&str,n:usize)->usize{
            let digit=token.strip_prefix("q[")
                .and_then(|s|s.strip_suffix(']')).expect("wire grammar");
            let q:usize=digit.parse().expect("wire index");
            assert!(q<n);q
        }
        let text=std::str::from_utf8(bytes).expect("utf8 source");
        let mut lines=text.lines().map(str::trim).filter(|s|!s.is_empty());
        assert_eq!(lines.next(),Some("OPENQASM 3.0;"));
        assert_eq!(lines.next(),Some("include \"stdgates.inc\";"));
        let declaration=lines.next().expect("qubits");
        let n:usize=declaration.strip_prefix("qubit[")
            .and_then(|s|s.strip_suffix("] q;"))
            .expect("register declaration").parse().expect("qubit number");
        assert!((1..=3).contains(&n) && input<(1<<n));
        let mut basis=input;
        let mut phase=0usize;
        let mut fresh=0usize;
        for instruction in lines {
            if instruction=="gphase(pi/4);" {
                phase=(phase+1)%8;
                continue;
            }
            let bare=instruction.strip_suffix(';').expect("semicolon");
            let (op,operand)=bare.split_once(' ').expect("gate operand");
            match op {
                "h"=>{
                    let q=source_wire(operand,n);
                    let before=(basis>>q)&1;
                    let after=(path_assignment>>fresh)&1;
                    phase=(phase+4*before*after)%8;
                    basis=(basis&!(1usize<<q)) | (after<<q);
                    fresh+=1;
                }
                "x"=>{
                    let q=source_wire(operand,n);
                    basis^=1usize<<q;
                }
                "cx"=>{
                    let (l,r)=operand.split_once(',').expect("two wires");
                    let c=source_wire(l,n);let t=source_wire(r,n);
                    assert_ne!(c,t);
                    if (basis>>c)&1==1 {basis^=1usize<<t;}
                }
                "cz"=>{
                    let (l,r)=operand.split_once(',').expect("two wires");
                    let c=source_wire(l,n);let t=source_wire(r,n);
                    assert_ne!(c,t);
                    phase=(phase+4*((basis>>c)&1)*((basis>>t)&1))%8;
                }
                "t" | "s" | "z"=>{
                    let q=source_wire(operand,n);
                    let coefficient=match op {"t"=>1,"s"=>2,_=>4};
                    phase=(phase+coefficient*((basis>>q)&1))%8;
                }
                _=>panic!("unsupported independent source instruction"),
            }
        }
        (basis,phase,fresh)
    }

    #[test]
    fn independent_raw_source_to_s8c1_bucket_audit(){
        // Every primary assignment, every ordered pair of basis inputs,
        // eight phase buckets, and three bad masks are checked end-to-end.
        // Reuse only the untrusted fixture emitter and the decoded Boolean
        // network; the comparison oracle does not reuse P8C1/ANF/Z8 states.
        let cases:[&[u8];4]=[
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n",
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\nt q[1];\nh q[1];\ncz q[0],q[1];\ns q[0];\ngphase(pi/4);\n",
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[3] q;\nh q[0];\ncx q[0],q[2];\nh q[1];\nt q[2];\ns q[1];\nx q[0];\ncz q[0],q[1];\nh q[2];\n",
            b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\nt q[0];\nh q[0];\nh q[0];\n",
        ];
        let mut obligations=0usize;
        let mut primary_assignments=0usize;
        let mut bucket_assertions=0usize;
        for source in cases {
            let (proof,state)=source_proof_and_state(source);
            let h=state.paths;
            assert!(h<=4 && state.n<=3);
            let dim=1usize<<state.n;
            let masks=[1u64,1u64<<(dim-1),(1u64<<dim)-1];
            let path_mask=(1usize<<h)-1;
            for first in 0..dim {
                for second in 0..dim {
                    for bad in masks {
                        let claimed=two_copy_structural::encode(
                            source,&proof,&state,first,second,bad
                        ).unwrap();
                        let network=two_copy_structural::verify_schema_without_enumeration(
                            source,&proof,&claimed
                        ).unwrap();
                        assert_eq!(network.primary,2*h);
                        for pair_paths in 0..(1usize<<(2*h)){
                            let (left,p_left,left_h)=raw_source_path_semantics(
                                source,first,pair_paths&path_mask);
                            let (right,p_right,right_h)=raw_source_path_semantics(
                                source,second,pair_paths>>h);
                            assert_eq!(left_h,h);
                            assert_eq!(right_h,h);
                            let phase_difference=(p_right+8-p_left)%8;
                            let eligible=left==right && (bad&(1u64<<left))!=0;
                            let values=two_copy_structural::evaluate(
                                &network,pair_paths
                            ).unwrap();
                            let mut matches=0;
                            for bucket in 0..8 {
                                let observed=values[network.bucket[bucket] as usize];
                                let expected=eligible && phase_difference==bucket;
                                assert_eq!(observed,expected,
                                    "source path and structural bucket diverged");
                                matches+=usize::from(observed);
                                bucket_assertions+=1;
                            }
                            assert_eq!(matches,usize::from(eligible));
                            primary_assignments+=1;
                        }
                        obligations+=1;
                    }
                }
            }
        }
        assert_eq!(obligations,264);
        // Soundness negative control: omitting the non-Clifford T phase in
        // H;T;H would incorrectly change the eligible bucket from 5 to 4.
        let source=cases[0];
        let (proof,state)=source_proof_and_state(source);
        let claimed=two_copy_structural::encode(
            source,&proof,&state,0,0,2
        ).unwrap();
        let network=two_copy_structural::verify_schema_without_enumeration(
            source,&proof,&claimed
        ).unwrap();
        let left_path=2usize;let right_path=3usize;
        let values=two_copy_structural::evaluate(
            &network,left_path|(right_path<<2)
        ).unwrap();
        assert!(values[network.bucket[5] as usize]);
        assert!(!values[network.bucket[4] as usize]);
        println!(
            "SOURCE_TO_S8C1_INDEPENDENT_EXACT obligations={obligations} \
             primary_assignments={primary_assignments} bucket_checks={bucket_assertions} \
             h_max=4 nonclifford_phase_omission_detected=true source_trust=BLOCKED"
        );
    }

}
