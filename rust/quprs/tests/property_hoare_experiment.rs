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
fn dense_state(n:usize,ops:&[G],x:u64)->Vec<Root>{
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
    v
}
fn dense(n:usize,ops:&[G],x:u64,q:Cube)->bool{
    dense_state(n,ops,x).iter().enumerate().all(|(z,a)|q.accepts(z as u64)||*a==[0;4])
}
#[test]
fn hoare_guard_phase_oracle_and_interference(){
    let a=Cube{mask:2,value:0};
    let p=Cube{mask:3,value:0};
    let ops=[G::H(1),G::CZ(0,1),G::H(1)];
    assert_eq!(verify(2,&ops,Some(p),a,0),(Answer::Proved,Route::PhaseOracle));
    assert_eq!(verify(2,&ops,Some(a),a,16),(Answer::Refuted(1),Route::ExactResidual));
    assert_eq!(verify(2,&[G::H(0),G::H(0),G::X(1)],Some(Cube{mask:1,value:0}),Cube{mask:1,value:0},8),(Answer::Proved,Route::ExactResidual));
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


// Fourier-support specialization: for H_A D H_A, affine parity
// assertion r dot z=b holds iff prefix phase f(y xor r)-f(y)=4b mod 8.
// The prefix includes the phase 4 a dot y from the fixed ancilla input.
// This is a symmetry/commutation criterion, not a novelty claim.
fn add_phase(poly:&mut BTreeMap<u64,u8>,m:u64,c:u8){
    let v=(poly.get(&m).copied().unwrap_or(0)+c)%8;
    if v==0{poly.remove(&m);}else{poly.insert(m,v);}
}
fn translation_gap(phase:&BTreeMap<u64,u8>,flip:u64,b:bool)->Option<BTreeMap<u64,u8>>{
    let mut gap=BTreeMap::new();
    let mut work=0u64;
    for (&m,&c) in phase{
        add_phase(&mut gap,m,(8-c)%8);
        // Substitute y_i -> 1-y_i over Z8, not XOR on coefficients.
        let flipped=m&flip;
        work=work.checked_add(1u64<<flipped.count_ones())?;
        if work>1_000_000{return None;}
        let mut sub=flipped;
        loop{
            add_phase(&mut gap,(m&!flip)|sub,
                if sub.count_ones()%2==0{c}else{(8-c)%8});
            if sub==0{break;}
            sub=(sub-1)&flipped;
        }
    }
    if b{add_phase(&mut gap,0,4);}
    Some(gap)
}
fn verify_parity_oracle(n:usize,ops:&[G],p:Cube,anc:&[usize],r:u64,b:bool)->Answer{
    let k=anc.len();
    if !admitted(n,ops)||!p.valid(n)||k==0||k>5||r>=(1u64<<k)
        ||ops.len()<2*k||anc.iter().any(|&a|a>=n)
        ||anc.iter().copied().collect::<BTreeSet<_>>().len()!=k{
        return Answer::Unknown;
    }
    for (j,&a) in anc.iter().enumerate(){
        if ops[j]!=G::H(a)||ops[ops.len()-k+j]!=G::H(a)||p.mask>>a&1==0{
            return Answer::Unknown;
        }
    }
    if !ops[k..ops.len()-k].iter().all(diagonal){return Answer::Unknown;}
    let Some(s)=native(n,&ops[..ops.len()-k]) else{return Answer::Unknown;};
    if s.h!=k{return Answer::Unknown;}
    // Check native output labels before assuming each fresh variable is
    // the corresponding Fourier input and data wires remain unchanged.
    for i in 0..n{
        let id=anc.iter().position(|&a|a==i).map_or(i,|j|n+j);
        if s.output[i]!=BTreeSet::from([1u64<<id]){return Answer::Unknown;}
    }
    let phase=specialize_phase(&s.phase,p);
    let Some(gap)=translation_gap(&phase,r<<n,b) else{return Answer::Unknown;};
    // Uniqueness of multilinear Boolean polynomial over Z8:
    // a minimum-cardinality nonzero monomial m evaluates nonzero at m,
    // because every proper subset coefficient is zero.
    match gap.keys().min_by_key(|m|m.count_ones()).copied(){
        None=>Answer::Proved,
        Some(m)=>Answer::Refuted(p.value|(m&((1u64<<n)-1))),
    }
}
fn parity_dense(n:usize,ops:&[G],x:u64,anc:&[usize],r:u64,b:bool)->bool{
    dense_state(n,ops,x).iter().enumerate().all(|(z,a)|{
        let y=anc.iter().enumerate().fold(0u64,|y,(j,&i)|y|(((z>>i&1) as u64)<<j));
        *a==[0;4]||((y&r).count_ones()%2!=0)==b
    })
}
#[test]
fn hoare_fourier_parity_differential(){
    let anc=[1,2];
    let gates=[G::Z(1),G::S(1),G::T(2),G::CZ(1,2),G::CZ(0,1),G::CZ(0,2),G::T(0)];
    let mut cases=0;let mut proved=0;let mut refuted=0;
    for g in &gates{for h in &gates{
        let ops=[G::H(1),G::H(2),g.clone(),h.clone(),G::H(1),G::H(2)];
        for a in 0..4u64{for (mask,value) in [(0,0),(1,0),(1,1)]{
            let p=Cube{mask:6|mask,value:(a<<1)|value};
            for r in 0..4{for b in [false,true]{
                let expected=(0..8).filter(|&x|p.accepts(x))
                    .find(|&x|!parity_dense(3,&ops,x,&anc,r,b));
                match verify_parity_oracle(3,&ops,p,&anc,r,b){
                    Answer::Proved=>{assert!(expected.is_none());proved+=1;}
                    Answer::Refuted(x)=>{assert!(p.accepts(x)&&!parity_dense(3,&ops,x,&anc,r,b));refuted+=1;}
                    Answer::Unknown=>panic!("admitted parity instance returned unknown"),
                }
                cases+=1;
            }}
        }}
    }}
    assert_eq!(cases,4704);
    println!("HOARE_PARITY_DIFFERENTIAL cases={cases} proved={proved} refuted={refuted} no_path_enumeration_in_verifier=true");
}
#[test]
fn hoare_fourier_parity_16q(){
    let anc=[14,15];
    // Conditional Z on both ancilla gives output (x_0,x_0):
    // parity zero holds for every data input, but either bit individually fails.
    let ops=[G::H(14),G::H(15),G::CZ(0,14),G::CZ(0,15),G::H(14),G::H(15)];
    let p=Cube{mask:(1<<14)|(1<<15),value:0};
    assert_eq!(verify_parity_oracle(16,&ops,p,&anc,3,false),Answer::Proved);
    assert_eq!(verify_parity_oracle(16,&ops,p,&anc,1,false),Answer::Refuted(1));
    assert_eq!(verify_parity_oracle(16,&ops,p,&[14,14],3,false),Answer::Unknown);
    println!("HOARE_PARITY_16Q free_data=14 hadamards=4 direct_two_copy_domain=4194304");
}


// Experimental quadratic output-fiber norm rule. This eliminates a block
// in the probability/zero-verdict domain, not in the amplitude domain.
// All coefficients and GF(2) operations are exact.
fn parity(v:u64)->bool{v.count_ones()%2!=0}
fn affine_solve(mut rows:Vec<(u64,bool)>,n:usize)->Option<(u64,Vec<u64>)>{
    assert!(n<=63);
    let mut pivots=Vec::new();
    for j in 0..n{
        let bit=1u64<<j;
        let i=pivots.len();
        if let Some(k)=(i..rows.len()).find(|&k|rows[k].0&bit!=0){
            rows.swap(i,k);
            let row=rows[i];
            for (l,r) in rows.iter_mut().enumerate(){
                if l!=i && r.0&bit!=0{r.0^=row.0;r.1^=row.1;}
            }
            pivots.push(j);
        }
    }
    if rows.iter().any(|&(m,b)|m==0&&b){return None;}
    let particular=pivots.iter().enumerate().fold(0,|v,(i,&j)|v|((rows[i].1 as u64)<<j));
    let kernel=(0..n).filter(|j|!pivots.contains(j)).map(|j|{
        pivots.iter().enumerate().fold(1u64<<j,|v,(i,&k)|v|(((rows[i].0>>j)&1)<<k))
    }).collect();
    Some((particular,kernel))
}
fn lift(coords:u64,basis:&[u64])->u64{
    basis.iter().enumerate().fold(0,|v,(j,&b)|if coords>>j&1!=0{v^b}else{v})
}
fn q4(poly:&BTreeMap<u64,u8>,v:u64)->u8{
    poly.iter().filter(|(m,_)|v&**m==**m).fold(0,|a,(_,c)|(a+*c)%4)
}
fn quadratic_norm(rows:Vec<(u64,bool)>,h:usize,poly:&BTreeMap<u64,u8>)->Option<u128>{
    // q(0)=0; singleton coefficients arbitrary Z4, quadratic
    // coefficients even. Anything else falls back to the general solver.
    if h>63||rows.iter().any(|&(m,_)|m>>h!=0)||
        poly.iter().any(|(&m,&c)|m==0||m>>h!=0||c>=4||
            m.count_ones()>2||(m.count_ones()==2&&c%2!=0)){return None;}
    let Some((t0,kernel))=affine_solve(rows,h) else{return Some(0);};
    let k=kernel.len();
    let bilinear=|u:u64,v:u64|{
        let b=(q4(poly,u^v)+8-q4(poly,u)-q4(poly,v))%4;
        debug_assert_eq!(b%2,0);
        b==2
    };
    let radical_rows:Vec<_>=kernel.iter().map(|&u|{
        let m=kernel.iter().enumerate().fold(0,|m,(j,&v)|m|((bilinear(u,v) as u64)<<j));
        (m,false)
    }).collect();
    let (_,radical)=affine_solve(radical_rows,k).expect("homogeneous system");
    // The restricted quadratic function is a character on the radical.
    // Checking a basis suffices. The coset offset t0 is essential.
    if radical.iter().any(|&r|q4(poly,t0^lift(r,&kernel))!=q4(poly,t0)){
        return Some(0);
    }
    Some(1u128<<(k+radical.len()))
}
fn native_quadratic_fiber_norm(s:&Symbolic,x:u64,z:u64)->Option<u128>{
    if x>=1u64<<s.n||z>=1u64<<s.n{return None;}
    let p=Cube{mask:(1u64<<s.n)-1,value:x};
    let mut rows=Vec::new();
    for (i,terms) in s.output.iter().enumerate(){
        let terms=specialize_bool(terms,p);
        let mut row=0;
        let mut rhs=z>>i&1!=0;
        for m in terms{
            if m==0{rhs=!rhs;}
            else if m.count_ones()==1{row|=m>>s.n;}
            else{return None;}
        }
        rows.push((row,rhs));
    }
    let mut q=BTreeMap::new();
    for (m,c) in specialize_phase(&s.phase,p){
        // Arbitrary input-only/global phase disappears in the norm.
        if m==0{continue;}
        if c%2!=0{return None;}
        q.insert(m>>s.n,c/2);
    }
    quadratic_norm(rows,s.h,&q)
}
#[test]
fn hoare_radical_all_three_variable_quadratics(){
    let mut cases=0;let mut zeros=0;
    for a in 0..8u64{for b in 0..8u64{
        for linear in 0..64u64{for cross in 0..8u64{
            let mut q=BTreeMap::new();
            for j in 0..3{let c=((linear>>(2*j))&3) as u8;if c!=0{q.insert(1<<j,c);}}
            for (j,m) in [3,5,6].into_iter().enumerate(){if cross>>j&1!=0{q.insert(m,2);}}
            for z in 0..4u64{
                let fiber:Vec<_>=(0..8).filter(|&t|parity(a&t)==(z&1!=0)&&parity(b&t)==(z&2!=0)).collect();
                let mut re=0i64;let mut im=0i64;
                for t in &fiber{
                    match q4(&q,*t){0=>re+=1,1=>im+=1,2=>re-=1,3=>im-=1,_=>unreachable!()}
                }
                let exact=(re*re+im*im) as u128;
                assert_eq!(quadratic_norm(vec![(a,z&1!=0),(b,z&2!=0)],3,&q),Some(exact));
                if !fiber.is_empty(){cases+=1;if exact==0{zeros+=1;}}
            }
        }}
    }}
    assert_eq!((cases,zeros),(108032,27713));
    println!("HOARE_RADICAL_EXHAUSTIVE reachable={cases} zero={zeros} nonzero={} including_unreachable=true",cases-zeros);
}
#[test]
fn hoare_radical_native_pathsum(){
    let gates=[G::H(0),G::H(1),G::X(0),G::CX(0,1),G::S(0),G::CZ(0,1),G::Z(1)];
    let mut cases=0;
    for g in &gates{for h in &gates{for j in &gates{
        let ops=[g.clone(),h.clone(),j.clone()];
        let s=native(2,&ops).unwrap();
        for x in 0..4{
            let dense=dense_state(2,&ops,x);
            for z in 0..4{
                let amp=dense[z as usize];
                // Clifford phases here are even eighth-root indices.
                assert_eq!((amp[1],amp[3]),(0,0));
                let norm=(amp[0]*amp[0]+amp[2]*amp[2]) as u128;
                assert_eq!(native_quadratic_fiber_norm(&s,x,z),Some(norm));
                cases+=1;
            }
        }
    }}}
    assert_eq!(cases,5488);
    let s=native(1,&[G::H(0),G::T(0),G::H(0)]).unwrap();
    assert_eq!(native_quadratic_fiber_norm(&s,0,0),None);
    // Input-only odd phase is safe to drop in a fixed-input norm.
    let s=native(1,&[G::T(0),G::H(0)]).unwrap();
    assert_eq!(native_quadratic_fiber_norm(&s,1,0),Some(1));
    println!("HOARE_RADICAL_NATIVE cases={cases} exact_dense_agreement=true unsupported_odd_path_phase=true");
}
#[test]
fn hoare_radical_large_block(){
    // Abstract affine-quadratic path-sum fiber: not a source-circuit
    // benchmark. 40 path variables, 20 independent bilinear pairs.
    let mut q=BTreeMap::new();
    for j in 0..20{q.insert((1u64<<(2*j))|(1u64<<(2*j+1)),2);}
    assert_eq!(quadratic_norm(vec![],40,&q),Some(1u128<<40));
    assert_eq!(quadratic_norm(vec![],40,&BTreeMap::new()),Some(1u128<<80));
    q.clear();q.insert(1,2);
    assert_eq!(quadratic_norm(vec![],40,&q),Some(0));
    // Offset-dependent radical character on t1 xor t2=1.
    let q=BTreeMap::from([(1,1),(2,1)]);
    assert_eq!(quadratic_norm(vec![(3,false)],2,&q),Some(0));
    assert_eq!(quadratic_norm(vec![(3,true)],2,&q),Some(4));
    println!("HOARE_RADICAL_40V direct_pair_domain=2^80 symbolic_block_no_enumeration=true");
}
