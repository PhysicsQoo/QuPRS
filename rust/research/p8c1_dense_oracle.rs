//! Independent exact *dense-state* gate oracle for the restricted Clifford+T
//! source fragment. No QuPRS, P8C1 decoder, ANF or PathSum dependencies.
//!
//! Integer amplitudes use the eight roots of unity before the common
//! Hadamard normalization 2^(-h/2). This is a finite n<=3 research oracle,
//! not a replacement for standardized OpenQASM source semantics.
#[derive(Clone, Copy, Debug)]
enum DenseGate {
    H(usize), X(usize), T(usize), S(usize), Z(usize),
    Cx(usize,usize), Cz(usize,usize), Global,
}
type Amplitude=[i128;8];

fn read_wire(token:&str,n:usize)->Result<usize,String>{
    let str_index=token.strip_prefix("q[")
        .and_then(|value|value.strip_suffix(']'))
        .ok_or("invalid dense-oracle wire bracket")?;
    if str_index.is_empty()
        || (str_index.starts_with('0')&&str_index.len()>1)
        || !str_index.bytes().all(|c|c.is_ascii_digit()) {
        return Err("noncanonical dense-oracle wire".into());
    }
    let index:usize=str_index.parse().map_err(|_|"invalid wire integer")?;
    if index>=n{return Err("out-of-bounds dense-oracle wire".into());}
    Ok(index)
}
fn parse_source(bytes:&[u8])->Result<(usize,Vec<DenseGate>),String>{
    let text=std::str::from_utf8(bytes).map_err(|_|"non UTF8 source")?;
    let mut statements=text.lines().map(str::trim).filter(|s|!s.is_empty());
    if statements.next()!=Some("OPENQASM 3.0;")
        || statements.next()!=Some("include \"stdgates.inc\";") {
        return Err("unsupported source header/import".into());
    }
    let decl=statements.next().ok_or("missing dense-oracle qubit register")?;
    let count=decl.strip_prefix("qubit[")
        .and_then(|s|s.strip_suffix("] q;")).ok_or("bad register")?;
    if count.is_empty() || (count.starts_with('0') && count.len()>1)
        || !count.bytes().all(|b|b.is_ascii_digit()) {
        return Err("noncanonical qubit count".into());
    }
    let n:usize=count.parse().map_err(|_|"invalid qubit count")?;
    if n==0||n>3{return Err("outside dense oracle n<=3".into());}
    let mut gates=Vec::new();
    for statement in statements {
        if gates.len()>=64{return Err("dense oracle source too long".into());}
        if statement=="gphase(pi/4);" {gates.push(DenseGate::Global);continue;}
        let expr=statement.strip_suffix(';').ok_or("missing semicolon")?;
        let (name,operands)=expr.split_once(' ').ok_or("invalid gate expression")?;
        if operands.bytes().any(|b|b.is_ascii_whitespace()) {
            return Err("noncanonical wire delimiters".into());
        }
        let unary=||read_wire(operands,n);
        let binary=|| -> Result<(usize,usize),String> {
            let (a,b)=operands.split_once(',').ok_or("missing binary operands")?;
            let c=read_wire(a,n)?;
            let t=read_wire(b,n)?;
            if c==t{return Err("control aliases target".into());}
            Ok((c,t))
        };
        let gate=match name {
            "h"=>DenseGate::H(unary()?),
            "x"=>DenseGate::X(unary()?),
            "t"=>DenseGate::T(unary()?),
            "s"=>DenseGate::S(unary()?),
            "z"=>DenseGate::Z(unary()?),
            "cx"=>{let (c,t)=binary()?;DenseGate::Cx(c,t)},
            "cz"=>{let (c,t)=binary()?;DenseGate::Cz(c,t)},
            _=>return Err("gate outside dense oracle fragment".into()),
        };
        gates.push(gate);
    }
    if gates.is_empty(){return Err("no admitted dense oracle gate".into());}
    Ok((n,gates))
}
fn rotate_phase(amplitude:Amplitude,shift:usize)->Amplitude{
    let mut result=[0i128;8];
    for k in 0..8{result[(k+shift)%8]+=amplitude[k];}
    result
}
fn simulate(bytes:&[u8],initial:&[(usize,i128)])->Result<(Vec<Amplitude>,usize),String>{
    let (n,steps)=parse_source(bytes)?;
    let dim=1usize<<n;
    let mut amplitudes=vec![[0i128;8];dim];
    for &(index,integer_weight) in initial {
        if index>=dim{return Err("bad initial basis index".into());}
        amplitudes[index][0]+=integer_weight;
    }
    let mut h_count=0;
    for gate in steps {
        match gate {
            DenseGate::H(wire)=>{
                if h_count==8{return Err("dense oracle H cap".into());}
                let bit=1usize<<wire;
                let mut updated=vec![[0i128;8];dim];
                for a in 0..dim {
                    if a&bit!=0{continue;}
                    let low=amplitudes[a];
                    let high=amplitudes[a|bit];
                    for k in 0..8 {
                        updated[a][k]=low[k]+high[k];
                        updated[a|bit][k]=low[k]-high[k];
                    }
                }
                amplitudes=updated;
                h_count+=1;
            }
            DenseGate::X(wire)=>{
                let bit=1usize<<wire;
                let mut updated=vec![[0i128;8];dim];
                for input in 0..dim {updated[input^bit]=amplitudes[input];}
                amplitudes=updated;
            }
            DenseGate::Cx(c,t)=>{
                let cbit=1usize<<c;
                let tbit=1usize<<t;
                let mut updated=vec![[0i128;8];dim];
                for input in 0..dim {
                    let output=if input&cbit!=0{input^tbit}else{input};
                    updated[output]=amplitudes[input];
                }
                amplitudes=updated;
            }
            DenseGate::T(wire)|DenseGate::S(wire)|DenseGate::Z(wire)=>{
                let shift=match gate {
                    DenseGate::T(_)=>1,
                    DenseGate::S(_)=>2,
                    _=>4,
                };
                let bit=1usize<<wire;
                for output in 0..dim {
                    if output&bit!=0 {
                        amplitudes[output]=rotate_phase(amplitudes[output],shift);
                    }
                }
            }
            DenseGate::Cz(c,t)=>{
                let mask=(1usize<<c)|(1usize<<t);
                for output in 0..dim {
                    if output&mask==mask{
                        amplitudes[output]=rotate_phase(amplitudes[output],4);
                    }
                }
            }
            DenseGate::Global=>{
                for value in &mut amplitudes {
                    *value=rotate_phase(*value,1);
                }
            }
        }
    }
    Ok((amplitudes,h_count))
}
// Independent cyclotomic-number norm formula rather than the path-frequency
// pairwise cosine summation in the symbolic Checker.
// Let a_j = c_j - c_(j+4), j=0..3. For z=sum c_k*zeta8^k:
// |z|² = (a0²+a1²+a2²+a3²)
//        + (a0(a1-a3)+a2(a1+a3))*sqrt(2).
fn norm_coeff(c:&Amplitude)->(i128,i128){
    let a:[i128;4]=std::array::from_fn(|j|c[j]-c[j+4]);
    let constant=a.iter().map(|v|v*v).sum();
    let surd=a[0]*(a[1]-a[3])+a[2]*(a[1]+a[3]);
    (constant,surd)
}
pub(crate) fn basis_risk(
    bytes:&[u8],basis_input:usize,bad_mask:u64
)->Result<(i128,i128,usize),String>{
    let (states,h_count)=simulate(bytes,&[(basis_input,1)])?;
    let(mut constant,mut surd)=(0,0);
    for (index,a) in states.iter().enumerate(){
        if bad_mask&(1u64<<index)==0{continue;}
        let(x,y)=norm_coeff(a);
        constant+=x;
        surd+=y;
    }
    Ok((constant,surd,h_count))
}
pub(crate) fn risk_at_most(
    risk:(i128,i128,usize),threshold_num:i128,threshold_den:i128
)->bool{
    let (a,b,h)=risk;
    let c=threshold_den*a-threshold_num*(1i128<<h);
    let d=threshold_den*b;
    // Branch on sign first to compare squares exactly.
    if d==0{return c<=0;}
    if c==0{return d<=0;}
    if c>0 && d>0{return false;}
    if c<0 && d<0{return true;}
    if c>0 {c*c<=2*d*d}
    else {c*c>=2*d*d}
}
pub(crate) fn plus_state_h_bad_zero()->Result<(i128,i128,usize),String>{
    // Initially |0>+|1>, with an additional known factor 1/sqrt2.
    // H maps |+> to |0>. (4 + 0sqrt2)/2² = 1.
    let bytes=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n";
    let (vector,h_count)=simulate(bytes,&[(0,1),(1,1)])?;
    let(a,b)=norm_coeff(&vector[0]);
    Ok((a,b,h_count+1))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_dense_oracle_fixtures(){
        let h=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n";
        let hth=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\nt q[0];\nh q[0];\n";
        let bell=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nh q[0];\ncx q[0],q[1];\n";
        assert_eq!(basis_risk(h,0,2).unwrap(),(1,0,1));
        assert_eq!(basis_risk(hth,0,2).unwrap(),(2,-1,2));
        assert_eq!(basis_risk(bell,0,8).unwrap(),(1,0,1));
        assert!(risk_at_most((2,-1,2),1,4));
        assert!(!risk_at_most((2,-1,2),1,8));
        println!("DENSE_EXACT_ORACLE rational_half=true irrational_surd=true bell=true");
    }
    #[test]
    fn basis_only_does_not_quantify_superpositions(){
        let h=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[1] q;\nh q[0];\n";
        for basis in 0..2 {
            assert!(risk_at_most(basis_risk(h,basis,1).unwrap(),1,2));
        }
        assert_eq!(plus_state_h_bad_zero().unwrap(),(4,0,2));
        assert!(!risk_at_most(plus_state_h_bad_zero().unwrap(),1,2));
        println!("DENSE_SPAN_COUNTEREXAMPLE basis_inputs_both_le_half=true superposition_risk_one=true");
    }
    #[test]
    fn phase_global_and_cz_gate_have_expected_exact_semantics(){
        let phase=b"OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\ngphase(pi/4);\nt q[0];\ns q[1];\ncz q[0],q[1];\n";
        let (v,h)=simulate(phase,&[(3,1)]).unwrap();
        assert_eq!(h,0);
        assert_eq!(v[3][0],1);
        assert_eq!(v[3][4],0);
        assert_eq!(norm_coeff(&v[3]),(1,0));
        assert_eq!(basis_risk(phase,3,8).unwrap(),(1,0,0));
    }
}
