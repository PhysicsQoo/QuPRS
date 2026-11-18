//! Standalone, std-only, research-grade P8C1 proof checker.
//! No QuPRS imports, producer implementation, solver, or Cargo dependency.
//! This is a restricted source-bound symbolic replay experiment, NOT
//! general OpenQASM conformance or a certified quantum property verdict.
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::process::ExitCode;

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
fn check(source:&[u8],proof:&[u8])->Check<usize> {
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
    Ok(gates.len())
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
}
