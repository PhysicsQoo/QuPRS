//! Experimental Hoare verification over native, unreduced QuPRS PathSum.
//! Boolean cube projectors; exact Clifford+T subset, zero violation only.
//! No source-parser certification, production API or external solver claim.
use quprs::{ir::QuantumOp as G, PathSum};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug)]
struct Cube { mask: u64, value: u64 }
impl Cube {
    fn valid(self, n: usize) -> bool {
        self.mask < (1u64 << n) && self.value & !self.mask == 0
    }
    fn accepts(self, x: u64) -> bool { x & self.mask == self.value }
}
#[derive(Debug, PartialEq, Eq)]
enum Answer { Proved, Refuted(u64), Unknown }
#[derive(Debug, PartialEq, Eq)]
enum Route { EmptyPre, Guard, PhaseOracle, ExactResidual, Resource, Unsupported }
type Report = (Answer, Route);
type Root = [i64; 4]; // Z[omega], omega^4=-1; independent basis.
fn add(a: Root, b: Root) -> Root { std::array::from_fn(|i| a[i]+b[i]) }
fn root(k: usize) -> Root {
    let mut r = [0; 4]; r[k%4] = if k%8 < 4 {1} else {-1}; r
}
fn shift(a: Root, k: usize) -> Root {
    let mut r = [0;4];
    for (i, v) in a.into_iter().enumerate() {
        let j = (i+k)%8;
        r[j%4] += if j<4 {v} else {-v};
    }
    r
}
fn admitted(n: usize, ops: &[G]) -> bool {
    n>0 && n<=16 && ops.len()<=128 &&
    ops.iter().filter(|g| matches!(g,G::H(_))).count()<=10 &&
    ops.iter().all(|g| match *g {
        G::H(q)|G::X(q)|G::Z(q)|G::S(q)|G::T(q) => q<n,
        G::CX(c,t)|G::CZ(c,t) => c<n && t<n && c!=t,
        G::CCX(a,b,t) => a<n && b<n && t<n && a!=b && a!=t && b!=t,
        _ => false,
    })
}
fn diagonal(g: &G) -> bool { matches!(g,G::Z(_)|G::S(_)|G::T(_)|G::CZ(_, _)) }
struct Symbolic { n: usize, h: usize, output: Vec<BTreeSet<u64>>, phase: BTreeMap<u64,u8> }
fn native(n: usize, ops: &[G]) -> Option<Symbolic> {
    let mut ps = PathSum::new(n);
    ps.set_auto_reduce(false);
    for op in ops { op.apply(&mut ps,false); }
    let h = ops.iter().filter(|g|matches!(g,G::H(_))).count();
    if ps.v.path_vars.len()!=n+h || (0..n+h).any(|i| !ps.v.path_vars.contains(&(i as u32))) ||
        ps.rr_approximate || !ps.v.continuous_vars.is_empty() { return None; }
    let mask = |m: &[u32]| -> Option<u64> {
        if m.iter().any(|&i| i as usize>=n+h) { return None; }
        Some(m.iter().fold(0, |a,&i| a | (1u64<<i)))
    };
    let output = ps.f.functions.iter().map(|p| p.iter().map(|m|mask(m)).collect::<Option<BTreeSet<_>>>()).collect::<Option<Vec<_>>>()?;
    if output.len()!=n {return None;}
    let mut phase=BTreeMap::new();
    for (m,c) in &ps.p.terms {
        if c.radians.is_some() || !c.symbols.is_empty() {return None;}
        let num=8i128*(c.constant.numer as i128);
        let den=c.constant.denom as i128;
        if den==0 || num%den!=0 {return None;}
        let k=(num/den).rem_euclid(8) as u8;
        if k!=0 { phase.insert(mask(m)?,k); }
    }
    Some(Symbolic{n,h,output,phase})
}
fn restrict(m: u64, p: Cube) -> Option<u64> {
    if m & p.mask & !p.value != 0 {None} else {Some(m & !p.mask)}
}
fn specialize_bool(terms: &BTreeSet<u64>, p: Cube) -> BTreeSet<u64> {
    let mut out=BTreeSet::new();
    for m in terms.iter().filter_map(|&m|restrict(m,p)) {
        if !out.insert(m) {out.remove(&m);}
    }
    out
}
fn specialize_phase(terms: &BTreeMap<u64,u8>,p:Cube)->BTreeMap<u64,u8>{
    let mut out=BTreeMap::<u64,u8>::new();
    for (&m,&k) in terms {
        if let Some(m)=restrict(m,p) {
            let v=(out.get(&m).copied().unwrap_or(0)+k)%8;
            if v==0 {out.remove(&m);} else {out.insert(m,v);}
        }
    }
    out
}
fn guard_unsat(s:&Symbolic,p:Cube,q:Cube)->bool{
    (0..s.n).filter(|&i|q.mask>>i&1!=0).all(|i|{
        let terms=specialize_bool(&s.output[i],p);
        if q.value>>i&1==0 {terms.is_empty()} else {terms.len()==1 && terms.contains(&0)}
    })
}
fn phase_oracle_safe(n:usize,ops:&[G],p:Cube,q:Cube)->bool{
    // H_a D H_a, D diagonal, a initially zero, assertion a=0.
    let Some(G::H(a))=ops.first() else {return false;};
    if ops.len()<2 || ops.last()!=Some(&G::H(*a)) ||
        !ops[1..ops.len()-1].iter().all(diagonal) ||
        q.mask!=1u64<<a || q.value!=0 || p.mask&q.mask==0 || p.value&q.mask!=0 {
        return false;
    }
    let Some(s)=native(n,&ops[..ops.len()-1]) else {return false;};
    // Phase coefficients are in Z8. After cube substitution, absence
    // of the Hadamard variable implies constant phase across its two paths.
    !specialize_phase(&s.phase,p).keys().any(|m|m>>n&1!=0)
}
fn path(s:&Symbolic,x:u64,y:u64)->(u64,usize){
    let a=x|(y<<s.n);
    let z=s.output.iter().enumerate().fold(0,|z,(i,t)|{
        let b=t.iter().fold(false,|b,m|b^(a&m==*m));
        z|((b as u64)<<i)
    });
    let k=s.phase.iter().filter(|(m,_)|a&**m==**m).map(|(_,k)|*k as usize).sum::<usize>()%8;
    (z,k)
}
fn verify(n:usize,ops:&[G],pre:Option<Cube>,q:Cube,budget:u64)->Report{
    if !admitted(n,ops) || !q.valid(n) || pre.is_some_and(|p|!p.valid(n)) {
        return (Answer::Unknown,Route::Unsupported);
    }
    let Some(p)=pre else {return (Answer::Proved,Route::EmptyPre);};
    // Suffix diagonal gates commute with computational-basis projector Q.
    let end=ops.iter().rposition(|g|!diagonal(g)).map_or(0,|i|i+1);
    let ops=&ops[..end];
    let Some(s)=native(n,ops) else {return (Answer::Unknown,Route::Unsupported);};
    if guard_unsat(&s,p,q) {return (Answer::Proved,Route::Guard);}
    if phase_oracle_safe(n,ops,p,q) {return (Answer::Proved,Route::PhaseOracle);}
    let free:Vec<_>=(0..n).filter(|&i|p.mask>>i&1==0).collect();
    let work=1u64<<(free.len()+s.h);
    if work>budget {return (Answer::Unknown,Route::Resource);}
    // Exact bounded residual: group forbidden outputs and sum cyclotomic
    // amplitudes before deciding zero. Common nonzero normalization omitted.
    for t in 0..(1u64<<free.len()){
        let x=free.iter().enumerate().fold(p.value,|x,(j,&i)|x|((t>>j&1)<<i));
        let mut sums=BTreeMap::<u64,Root>::new();
        for y in 0..(1u64<<s.h){
            let (z,k)=path(&s,x,y);
            if !q.accepts(z) { let v=sums.entry(z).or_default(); *v=add(*v,root(k)); }
        }
        if sums.values().any(|v|*v!=[0;4]) {return (Answer::Refuted(x),Route::ExactResidual);}
    }
    (Answer::Proved,Route::ExactResidual)
}
// Direct two-copy count (bounded oracle for future WMC encoding).
fn pair_zero(s:&Symbolic,p:Cube,q:Cube)->bool{
    let mut total=[0;4];
    for x in (0..1u64<<s.n).filter(|&x|p.accepts(x)){
        let bad:Vec<_>=(0..1u64<<s.h).map(|y|path(s,x,y)).filter(|(z,_)|!q.accepts(*z)).collect();
        for &(z,k) in &bad {
            for &(w,l) in &bad {
                if z==w {total=add(total,root((k+8-l)%8));}
            }
        }
    }
    total==[0;4]
}
// Independent direct gate-by-gate state vector, same exact ring but no PathSum.
fn dense(n:usize,ops:&[G],x:u64,q:Cube)->bool{
    let mut v=vec![[0;4];1<<n];v[x as usize]=root(0);
    for g in ops{
        let old=v.clone();
        for (z,dst) in v.iter_mut().enumerate(){
            let bit=|i:usize|z>>i&1;
            *dst=match *g{
                G::H(i)=>add(old[z&!(1<<i)],shift(old[z|(1<<i)],4*bit(i))),
                G::X(i)=>old[z^(1<<i)],
                G::CX(c,t)=>old[z^(bit(c)<<t)],
                G::CCX(a,b,t)=>old[z^((bit(a)&bit(b))<<t)],
                G::Z(i)=>shift(old[z],4*bit(i)),
                G::S(i)=>shift(old[z],2*bit(i)),
                G::T(i)=>shift(old[z],bit(i)),
                G::CZ(c,t)=>shift(old[z],4*(bit(c)&bit(t))),
                _=>unreachable!(),
            };
        }
    }
    v.iter().enumerate().all(|(z,a)|q.accepts(z as u64)||*a==[0;4])
}
#[test]
fn hoare_guard_phase_oracle_and_interference(){
    let a=Cube{mask:2,value:0};
    let p=Cube{mask:3,value:0};
    let ops=[G::H(1),G::CZ(0,1),G::H(1)];
    assert_eq!(verify(2,&ops,Some(p),a,0),(Answer::Proved,Route::PhaseOracle));
    assert_eq!(verify(2,&ops,Some(a),a,16),(Answer::Refuted(1),Route::ExactResidual));
    assert_eq!(verify(2,&[G::H(0),G::H(0)],Some(Cube{mask:1,value:0}),Cube{mask:1,value:0},4),(Answer::Proved,Route::ExactResidual));
    assert_eq!(verify(2,&[G::CX(0,1),G::T(1)],Some(p),a,0),(Answer::Proved,Route::Guard));
    assert_eq!(verify(2,&ops,None,a,0),(Answer::Proved,Route::EmptyPre));
    assert_eq!(verify(2,&ops,Some(a),a,0),(Answer::Unknown,Route::Resource));
    assert_eq!(verify(2,&[G::CX(1,1)],Some(p),a,16),(Answer::Unknown,Route::Unsupported));
    println!("HOARE_ROUTES guard phase_oracle interference empty_pre resource unsupported");
}
#[test]
fn hoare_differential_all_two_qubit_cubes(){
    let gates=[G::H(0),G::H(1),G::X(0),G::X(1),G::CX(0,1),G::CX(1,0),G::CZ(0,1),G::T(0),G::S(1)];
    let cubes:Vec<_>=(0..4).flat_map(|mask|(0..4).filter(move|v|v & !mask==0).map(move|value|Cube{mask,value})).collect();
    let mut cases=0;
    for g in &gates { for h in &gates {
        let ops=[g.clone(),h.clone()];
        let s=native(2,&ops).unwrap();
        for &p in &cubes {for &q in &cubes{
            let expected=(0..4).filter(|&x|p.accepts(x)).find(|&x|!dense(2,&ops,x,q));
            assert_eq!(pair_zero(&s,p,q),expected.is_none());
            let (actual,_)=verify(2,&ops,Some(p),q,64);
            match actual {
                Answer::Proved=>assert!(expected.is_none()),
                Answer::Refuted(x)=>assert!(p.accepts(x)&&!dense(2,&ops,x,q)),
                Answer::Unknown=>panic!("unexpected unknown"),
            }
            cases+=1;
        }}
    }}
    println!("HOARE_DIFFERENTIAL cases={cases} pair_count_and_dense_agree=true");
    assert_eq!(cases,6561);
}
#[test]
fn hoare_large_symbolic_precondition(){
    let ops=[G::H(15),G::CZ(0,15),G::H(15)];
    let p=Cube{mask:(1<<15)|1,value:0};
    let q=Cube{mask:1<<15,value:0};
    assert_eq!(verify(16,&ops,Some(p),q,0),(Answer::Proved,Route::PhaseOracle));
    println!("HOARE_SYMBOLIC_16Q free_inputs=14 baseline_two_copy_assignments=262144 residual_budget=0");
}
