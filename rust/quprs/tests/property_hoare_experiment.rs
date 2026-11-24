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


// R4: solver-neutral exact Hoare baseline, no new reduction rules.
// ANF p and q represent arbitrary diagonal Boolean projectors.
// Tseitin clauses have unique extension; exact complex WMC is reduced
// to eight ordinary #SAT counts. The small DPLL backend is test-only.
mod exact_property_cnf {
    use super::*;
    type Anf = BTreeSet<u64>;
    type Lit = i32;
    const ONE: Lit = 1;
    const ZERO: Lit = -1;

    #[derive(Clone)]
    struct Cnf { vars: usize, clauses: Vec<Vec<Lit>> }
    impl Cnf {
        fn new(primary: usize) -> Self {
            Self { vars: primary+1, clauses: vec![vec![ONE]] }
        }
        fn fresh(&mut self) -> Lit {
            self.vars += 1;
            self.vars as Lit
        }
        fn and(&mut self,a:Lit,b:Lit)->Lit {
            if a==ZERO||b==ZERO||a == -b{return ZERO;}
            if a==ONE||a==b{return b;}
            if b==ONE{return a;}
            let z=self.fresh();
            self.clauses.extend([vec![-z,a],vec![-z,b],vec![z,-a,-b]]);
            z
        }
        fn xor(&mut self,a:Lit,b:Lit)->Lit {
            if a==b{return ZERO;}
            if a == -b{return ONE;}
            if a==ZERO{return b;}
            if b==ZERO{return a;}
            if a==ONE{return -b;}
            if b==ONE{return -a;}
            let z=self.fresh();
            self.clauses.extend([vec![-a,-b,-z],vec![a,b,-z],vec![a,-b,z],vec![-a,b,z]]);
            z
        }
        fn or(&mut self,a:Lit,b:Lit)->Lit { -self.and(-a,-b) }
        fn monomial(&mut self,m:u64,bits:&[Lit])->Lit {
            bits.iter().enumerate().filter(|(i,_)|m>>i&1!=0)
                .fold(ONE,|a,(_,b)|self.and(a,*b))
        }
        fn anf(&mut self,p:&Anf,bits:&[Lit])->Lit {
            p.iter().fold(ZERO,|a,&m|{let b=self.monomial(m,bits);self.xor(a,b)})
        }
        fn add3(&mut self,a:[Lit;3],b:[Lit;3])->[Lit;3]{
            let mut carry=ZERO;
            let mut out=[ZERO;3];
            for i in 0..3 {
                let t=self.xor(a[i],b[i]);
                out[i]=self.xor(t,carry);
                if i<2{
                    let ab=self.and(a[i],b[i]);
                    let tc=self.and(t,carry);
                    carry=self.or(ab,tc);
                }
            }
            out
        }
        fn phase(&mut self,s:&Symbolic,bits:&[Lit],negative:bool)->[Lit;3]{
            let mut acc=[ZERO;3];
            for (&m,&k) in &s.phase{
                let v=self.monomial(m,bits);
                let k=if negative{(8-k)%8}else{k};
                let term=std::array::from_fn(|i|if k>>i&1!=0{v}else{ZERO});
                acc=self.add3(acc,term);
            }
            acc
        }
        fn enforce(&mut self,l:Lit){self.clauses.push(vec![l]);}
        fn bounded(&self)->bool{self.vars<=512&&self.clauses.len()<=4096}
    }
    fn eval(p:&Anf,x:u64)->bool{p.iter().fold(false,|v,&m|v^(x&m==m))}
    fn lit_value(l:Lit,a:&[i8])->i8{
        let v=a[l.unsigned_abs() as usize];
        if l<0{-v}else{v}
    }
    fn assign(l:Lit,a:&mut [i8])->bool{
        let i=l.unsigned_abs() as usize;
        let v=if l>0{1}else{-1};
        if a[i]!=0&&a[i]!=v{return false;}
        a[i]=v;true
    }
    // Exact DPLL with unit propagation, conflict pruning and free-variable
    // counting. SAT uses the same engine with early success. No floating
    // weights, no assignment-table CNF, no external solver dependency.
    // Fuel counts clause visits across all recursive calls and queries.
    fn dpll(c:&Cnf,mut a:Vec<i8>,fuel:&mut u64,sat_only:bool)->Option<u128>{
        loop{
            let mut changed=false;
            let mut choice=None::<(usize,Lit)>;
            for clause in &c.clauses{
                *fuel=fuel.checked_sub(1)?;
                let mut open=0usize;
                let mut first=0;
                let mut satisfied=false;
                for &l in clause{
                    match lit_value(l,&a){
                        1=>{satisfied=true;break;}
                        0=>{open+=1;if first==0{first=l;}}
                        _=>{}
                    }
                }
                if satisfied{continue;}
                if open==0{return Some(0);}
                if open==1{
                    if !assign(first,&mut a){return Some(0);}
                    changed=true;
                }else if choice.is_none_or(|(n,_)|open<n){choice=Some((open,first));}
            }
            if changed{continue;}
            let Some((_,l))=choice else{
                return if sat_only{Some(1)}else{1u128.checked_shl(a[1..].iter().filter(|&&x|x==0).count() as u32)};
            };
            let mut left=a.clone();assign(l,&mut left);
            let n=dpll(c,left,fuel,sat_only)?;
            if sat_only&&n!=0{return Some(1);}
            assign(-l,&mut a);
            return n.checked_add(dpll(c,a,fuel,sat_only)?);
        }
    }
    fn count(c:&Cnf,assumptions:&[Lit],fuel:&mut u64,sat_only:bool)->Option<u128>{
        if !c.bounded(){return None;}
        let mut a=vec![0;c.vars+1];
        for &l in assumptions{
            if l==0||l.unsigned_abs() as usize>c.vars{return None;}
            if !assign(l,&mut a){return Some(0);}
        }
        dpll(c,a,fuel,sat_only)
    }
    fn guard_cnf(s:&Symbolic,p:&Anf,q:&Anf)->Cnf{
        let mut c=Cnf::new(s.n+s.h);
        let bits:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        let pre=c.anf(p,&bits[..s.n]);c.enforce(pre);
        let z:Vec<_>=s.output.iter().map(|o|c.anf(o,&bits)).collect();
        let post=c.anf(q,&z);c.enforce(-post);
        c
    }
    fn two_copy(s:&Symbolic,p:&Anf,q:&Anf)->(Cnf,[Lit;3]){
        two_copy_conj(s,std::slice::from_ref(p),std::slice::from_ref(q))
    }
    // Conjunction of small ANFs, without expanding products into a single ANF.
    fn two_copy_conj(s:&Symbolic,p:&[Anf],q:&[Anf])->(Cnf,[Lit;3]){
        let mut c=Cnf::new(s.n+2*s.h);
        let left:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        let right:Vec<_>=(0..s.n).map(|i|i as Lit+2)
            .chain((s.n+s.h..s.n+2*s.h).map(|i|i as Lit+2)).collect();
        for condition in p{let pre=c.anf(condition,&left[..s.n]);c.enforce(pre);}
        let z:Vec<_>=s.output.iter().map(|o|c.anf(o,&left)).collect();
        let w:Vec<_>=s.output.iter().map(|o|c.anf(o,&right)).collect();
        for (&a,&b) in z.iter().zip(&w){let d=c.xor(a,b);c.enforce(-d);}
        let post=q.iter().fold(ONE,|acc,condition|{let l=c.anf(condition,&z);c.and(acc,l)});c.enforce(-post);
        let a=c.phase(s,&left,false);
        let b=c.phase(s,&right,true);
        let delta=c.add3(a,b);
        (c,delta)
    }
    fn buckets(c:&Cnf,delta:[Lit;3],prefix:&[Lit],fuel:&mut u64)->Option<[u128;8]>{
        let mut ns=[0;8];
        for (j,n) in ns.iter_mut().enumerate(){
            let mut units=prefix.to_vec();
            units.extend(delta.iter().enumerate().map(|(i,&l)|if j>>i&1!=0{l}else{-l}));
            *n=count(c,&units,fuel,false)?;
        }
        Some(ns)
    }
    fn zero(n:[u128;8])->bool{(0..4).all(|i|n[i]==n[i+4])}
    #[derive(Debug,PartialEq,Eq)]
    enum SolverRoute { SatUnsat, ExactCount, Unknown }
    #[derive(Debug)]
    struct ResultRecord {
        answer:Answer, route:SolverRoute, variables:usize, clauses:usize, visits:u64,
    }
    fn solve_symbolic(s:&Symbolic,p:&Anf,q:&Anf,budget:u64)->ResultRecord{
        let n=s.n;
        let mut fuel=budget;
        let mut size=(0,0);
        let result=(||->Option<(Answer,SolverRoute)>{
            if p.iter().chain(q).any(|&m|m>>n!=0){return None;}
            // Bound experimental input/phase size before CNF construction.
            // The existing native PathSum builder itself is not a resource-certified parser.
            if p.len()+q.len()>128{return None;}
            if s.output.iter().map(|o|o.len()).sum::<usize>()+s.phase.len()>256{return None;}
            let guard=guard_cnf(s,p,q);size=(guard.vars,guard.clauses.len());
            if count(&guard,&[],&mut fuel,true)?==0{return Some((Answer::Proved,SolverRoute::SatUnsat));}
            let (c,d)=two_copy(s,p,q);size=(c.vars,c.clauses.len());
            if zero(buckets(&c,d,&[],&mut fuel)?){return Some((Answer::Proved,SolverRoute::ExactCount));}
            // Condition on input bits. A nonzero parent sum is a sum of
            // nonnegative child risks, so at least one branch is nonzero.
            let mut prefix=Vec::new();let mut x=0u64;
            for i in 0..n{
                let l=i as Lit+2;
                prefix.push(-l);
                if zero(buckets(&c,d,&prefix,&mut fuel)?){
                    *prefix.last_mut()?=l;x|=1u64<<i;
                }
            }
            // Reconfirm the fully fixed counterexample using the solver.
            if !eval(p,x)||zero(buckets(&c,d,&prefix,&mut fuel)?){return None;}
            Some((Answer::Refuted(x),SolverRoute::ExactCount))
        })().unwrap_or((Answer::Unknown,SolverRoute::Unknown));
        ResultRecord{answer:result.0,route:result.1,variables:size.0,clauses:size.1,visits:budget-fuel}
    }
    fn unknown()->ResultRecord{
        ResultRecord{answer:Answer::Unknown,route:SolverRoute::Unknown,variables:0,clauses:0,visits:0}
    }
    fn verify_anf(n:usize,ops:&[G],p:&Anf,q:&Anf,budget:u64)->ResultRecord{
        if !admitted(n,ops)||p.iter().chain(q).any(|&m|m>>n!=0){return unknown();}
        match native(n,ops){
            Some(s)=>solve_symbolic(&s,p,q,budget),
            None=>unknown(),
        }
    }

    // Same existing native rules, but only accept HH when both eliminated
    // labels are internal. Trial on a clone; never retain an input pivot.
    // Reduction is applied before building the property guard.
    // scale2 is the exponent of the factor multiplying squared UNNORMALIZED
    // residual amplitudes to obtain squared UNNORMALIZED original amplitudes.
    #[derive(Default,Debug)]
    struct RrStats { elim:usize, hh:usize, omega:usize, input_pivot_rejected:usize, scale2:u32 }
    fn compact(ps:&PathSum,n:usize)->Option<Symbolic>{
        if ps.rr_approximate||ps.rr_tolerance!=0.0||!ps.v.continuous_vars.is_empty(){return None;}
        let live=&ps.v.path_vars;
        if (0..n).any(|i|!live.contains(&(i as u32))){return None;}
        let mut ids:Vec<u32>=live.iter().copied().collect();ids.sort_unstable();
        if ids.len()>63||ids.len()<n{return None;}
        let map:BTreeMap<_,_>=ids.iter().enumerate().map(|(i,&v)|(v,i)).collect();
        let mask=|m:&[u32]|->Option<u64>{
            let mut out=0;
            for v in m{out|=1u64<<*map.get(v)?;}
            Some(out)
        };
        let output=ps.f.functions.iter().map(|p|p.iter().map(|m|mask(m)).collect::<Option<BTreeSet<_>>>()).collect::<Option<Vec<_>>>()?;
        if output.len()!=n{return None;}
        let mut phase=BTreeMap::new();
        for (m,c) in &ps.p.terms{
            if c.radians.is_some()||!c.symbols.is_empty(){return None;}
            let num=8i128*c.constant.numer as i128;
            let den=c.constant.denom as i128;
            if den==0||num%den!=0{return None;}
            let k=(num/den).rem_euclid(8) as u8;
            if k!=0{phase.insert(mask(m)?,k);}
        }
        Some(Symbolic{n,h:ids.len()-n,output,phase})
    }
    fn reduce_existing(mut ps:PathSum,n:usize)->Option<(Symbolic,RrStats)>{
        let mut stats=RrStats::default();
        for _ in 0..32{
            let before=ps.v.path_vars.len();
            let snapshot=compact(&ps,n)?;
            if snapshot.output.iter().map(|p|p.len()).sum::<usize>()+snapshot.phase.len()>256{return None;}
            let candidates=ps.get_reducible_vars();
            if candidates.is_empty(){return Some((snapshot,stats));}
            if ps.try_reduce_elim(&candidates){
                let removed=before.checked_sub(ps.v.path_vars.len())?;
                if removed==0{return None;}
                stats.elim+=removed;stats.scale2+=2*removed as u32;continue;
            }
            if ps.try_reduce_omega(&candidates){
                if before.checked_sub(ps.v.path_vars.len())?!=1{return None;}
                stats.omega+=1;stats.scale2+=1;continue;
            }
            let mut accepted=false;
            for y in candidates{
                let mut trial=ps.clone();
                if trial.try_reduce_hh(&[y]){
                    let removed:Vec<_>=ps.v.path_vars.difference(&trial.v.path_vars).copied().collect();
                    if removed.len()==1{
                        // Existing HH may pivot on original input x_i.
                        // It substitutes x_i but leaves its label live.
                        // Reject this trial; use unchanged original state.
                        stats.input_pivot_rejected+=1;
                        continue;
                    }
                    if removed.len()!=2||!removed.contains(&y)||removed.iter().any(|&v|(v as usize)<n)
                        ||!trial.v.path_vars.is_subset(&ps.v.path_vars){return None;}
                    ps=trial;stats.hh+=1;stats.scale2+=2;accepted=true;break;
                }
            }
            if !accepted{return Some((snapshot,stats));}
        }
        None
    }
    fn reduced_native(n:usize,ops:&[G])->Option<(Symbolic,RrStats)>{
        if !admitted(n,ops){return None;}
        let mut ps=PathSum::new(n);
        ps.set_auto_reduce(false);
        for g in ops{g.apply(&mut ps,false);}
        reduce_existing(ps,n)
    }
    fn signed(ns:[u128;8])->[i128;4]{
        std::array::from_fn(|i|ns[i] as i128-ns[i+4] as i128)
    }
    fn compare_rr(n:usize,ops:&[G],p:&Anf,q:&Anf)->(ResultRecord,ResultRecord,RrStats,usize,usize){
        let direct=native(n,ops).unwrap();
        let (reduced,stats)=reduced_native(n,ops).unwrap();
        let (c,d)=two_copy(&direct,p,q);
        let (cr,dr)=two_copy(&reduced,p,q);
        let a=signed(buckets(&c,d,&[],&mut 20_000_000).unwrap());
        let b=signed(buckets(&cr,dr,&[],&mut 20_000_000).unwrap());
        assert_eq!(a,b.map(|v|v*(1i128<<stats.scale2)));
        let x=solve_symbolic(&direct,p,q,20_000_000);
        let y=solve_symbolic(&reduced,p,q,20_000_000);
        let expected=(0..1u64<<n).any(|x|violated(n,ops,p,q,x));
        for r in [&x,&y]{
            match r.answer{
                Answer::Proved=>assert!(!expected),
                Answer::Refuted(w)=>assert!(expected&&violated(n,ops,p,q,w)),
                Answer::Unknown=>panic!("unexpected unknown: {r:?}"),
            }
        }
        (x,y,stats,direct.h,reduced.h)
    }
    // Standard unweighted DIMACS per bucket and conditioned input prefix.
    // No projected counting is necessary because gate auxiliaries have
    // unique extension. External exact solver integration remains separate.
    fn dimacs(c:&Cnf,assumptions:&[Lit])->Option<String>{
        if !c.bounded()||assumptions.iter().any(|&l|l==0||l.unsigned_abs() as usize>c.vars){return None;}
        let mut out=format!("p cnf {} {}\n",c.vars,c.clauses.len()+assumptions.len());
        for clause in &c.clauses{
            for l in clause{out.push_str(&format!("{l} "));}
            out.push_str("0\n");
        }
        for l in assumptions{out.push_str(&format!("{l} 0\n"));}
        Some(out)
    }
    fn parse_own_dimacs(text:&str)->Cnf{
        let mut lines=text.lines();
        let header:Vec<_>=lines.next().unwrap().split_whitespace().collect();
        assert_eq!(&header[..2],["p","cnf"]);
        let vars=header[2].parse().unwrap();
        let expected:usize=header[3].parse().unwrap();
        let clauses:Vec<Vec<Lit>>=lines.map(|line|{
            let mut row:Vec<Lit>=line.split_whitespace().map(|l|l.parse().unwrap()).collect();
            assert_eq!(row.pop(),Some(0));
            assert!(row.iter().all(|l|*l!=0&&l.unsigned_abs() as usize<=vars));
            row
        }).collect();
        assert_eq!(clauses.len(),expected);Cnf{vars,clauses}
    }
    #[test]
    fn hoare_standard_rr_and_dimacs(){
        let all=Anf::from([0]);let zero=Anf::from([0,1]);
        let cases=[
            ("HH",1,vec![G::H(0),G::H(0)],zero.clone(),zero.clone()),
            ("omega",1,vec![G::H(0),G::S(0),G::H(0)],zero.clone(),zero.clone()),
            ("HTH",1,vec![G::H(0),G::T(0),G::H(0)],zero.clone(),zero.clone()),
            ("BV",3,vec![G::X(2),G::H(0),G::H(1),G::H(2),G::CX(0,2),G::H(0),G::H(1)],
                Anf::from([0,1,2,3,4,5,6,7]),Anf::from([1,3])),
            ("GHZ",3,vec![G::H(0),G::CX(0,1),G::CX(0,2)],Anf::from([0,1,2,3,4,5,6,7]),Anf::from([0,1,2,4,3,5,6])),
        ];
        for (name,n,ops,p,q) in cases{
            let (a,b,stats,h,hr)=compare_rr(n,&ops,&p,&q);
            if name=="HH"{assert_eq!((h,hr,stats.hh),(2,0,1));}
            if name=="omega"{assert_eq!((h,hr,stats.omega),(2,1,1));}
            let s=native(n,&ops).unwrap();let (c,d)=two_copy(&s,&p,&q);
            let expected=buckets(&c,d,&[],&mut 20_000_000).unwrap();
            for j in 0..8{
                let units:Vec<_>=d.iter().enumerate().map(|(i,&l)|if j>>i&1!=0{l}else{-l}).collect();
                let serialized=dimacs(&c,&units).unwrap();
                let parsed=parse_own_dimacs(&serialized);
                assert_eq!(count(&parsed,&[],&mut 20_000_000,false),Some(expected[j]));
            }
            println!("HOARE_RR_BASELINE case={name} h={h}->{hr} vars={}->{} clauses={}->{} visits={}->{} stats={stats:?}",a.variables,b.variables,a.clauses,b.clauses,a.visits,b.visits);
        }
        // Synthetic input-dependent projector, not a unitary circuit.
        // S|x>=Σ_y(-1)^(xy)|x>; removing y without preserving [x=0]
        // would lose the zero column. Existing input pivot must be rejected.
        let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
        let y=ps.v.get_fresh_var();
        ps.p.add_term(vec![0,y],quprs::pathsum::PhaseCoeff::HALF);
        let (s,stats)=reduce_existing(ps,1).unwrap();
        assert_eq!(s.h,1);assert_eq!(stats.input_pivot_rejected,1);
        let (c,d)=two_copy(&s,&all,&zero);
        assert!(zero_buckets_for_test(&c,d));
    }
    fn zero_buckets_for_test(c:&Cnf,d:[Lit;3])->bool{
        zero(buckets(c,d,&[],&mut 20_000_000).unwrap())
    }
    #[test]
    fn hoare_standard_rr_differential(){
        let gates=[G::H(0),G::H(1),G::CX(0,1),G::CZ(0,1),G::T(0),G::S(1)];
        let preds:Vec<Anf>=(0..16).map(|mask|(0..4).filter(|i|mask>>i&1!=0).collect()).collect();
        let mut cases=0;
        for g in &gates{for h in &gates{
            let ops=[G::H(0),g.clone(),h.clone()];
            for p in &preds{for q in &preds{
                compare_rr(2,&ops,p,q);cases+=1;
            }}
        }}
        assert_eq!(cases,9216);
        println!("HOARE_RR_DIFFERENTIAL cases={cases} exact_scaled_violation_and_witness=true");
    }
    fn direct_buckets(s:&Symbolic,p:&Anf,q:&Anf)->[u128;8]{
        let mut n=[0;8];
        for x in (0..1u64<<s.n).filter(|&x|eval(p,x)){
            for y in 0..1u64<<s.h{
                let (z,k)=path(s,x,y);
                if eval(q,z){continue;}
                for w in 0..1u64<<s.h{
                    let (z2,l)=path(s,x,w);
                    if z==z2{n[(k+8-l)%8]+=1;}
                }
            }
        }
        n
    }
    fn violated(n:usize,ops:&[G],p:&Anf,q:&Anf,x:u64)->bool{
        eval(p,x)&&dense_state(n,ops,x).iter().enumerate().any(|(z,a)|!eval(q,z as u64)&&*a!=[0;4])
    }
    fn check_case(n:usize,ops:&[G],p:&Anf,q:&Anf)->ResultRecord{
        let s=native(n,ops).unwrap();
        let (c,d)=two_copy(&s,p,q);
        let exact=buckets(&c,d,&[],&mut 20_000_000).expect("exact baseline fuel");
        assert_eq!(exact,direct_buckets(&s,p,q));
        let expected=(0..1u64<<n).any(|x|violated(n,ops,p,q,x));
        let r=verify_anf(n,ops,p,q,20_000_000);
        match r.answer{
            Answer::Proved=>assert!(!expected),
            Answer::Refuted(x)=>assert!(expected&&violated(n,ops,p,q,x)),
            Answer::Unknown=>panic!("unexpected unknown: {r:?}"),
        }
        assert_eq!(zero(exact),!expected);
        r
    }
    #[test]
    fn hoare_cnf_backend_truth_tables(){
        let mut c=Cnf::new(2);
        let a=2;let b=3;
        let and=c.and(a,b);let xor=c.xor(a,b);
        for x in 0..4{
            let assumptions=[if x&1!=0{a}else{-a},if x&2!=0{b}else{-b}];
            assert_eq!(count(&c,&assumptions,&mut 1000,false),Some(1));
            for (l,v) in [(and,x==3),(xor,x==1||x==2)]{
                let mut units=assumptions.to_vec();units.push(if v{l}else{-l});
                assert_eq!(count(&c,&units,&mut 1000,false),Some(1));
                *units.last_mut().unwrap() *= -1;
                assert_eq!(count(&c,&units,&mut 1000,false),Some(0));
            }
        }
        assert_eq!(count(&c,&[],&mut 1000,false),Some(4));
        assert_eq!(count(&c,&[],&mut 0,false),None);
    }
    #[test]
    fn hoare_cnf_all_two_qubit_anf_pairs(){
        let gates=[G::H(0),G::H(1),G::X(0),G::CX(0,1),G::T(0),G::S(1)];
        let predicates:Vec<Anf>=(0..16).map(|mask|(0..4).filter(|i|mask>>i&1!=0).collect()).collect();
        // All 16 Boolean functions on two bits; 12 representative circuits.
        let circuits:Vec<Vec<G>>=gates.iter().cloned().map(|g|vec![g])
            .chain(gates.iter().cloned().map(|g|vec![G::H(0),g])).collect();
        let mut sat=0;let mut counted=0;let mut cases=0;
        for ops in circuits{for p in &predicates{for q in &predicates{
            let r=check_case(2,&ops,p,q);
            match r.route{SolverRoute::SatUnsat=>sat+=1,SolverRoute::ExactCount=>counted+=1,_=>unreachable!()}
            cases+=1;
        }}}
        assert_eq!(cases,3072);
        println!("HOARE_CNF_ANF cases={cases} sat_unsat={sat} exact_count={counted}");
    }
    #[test]
    fn hoare_cnf_property_corpus(){
        let all=Anf::from([0]);
        let zero0=Anf::from([0,1]);
        let zero3=Anf::from([0,8]);
        let ghz=vec![G::H(0),G::CX(0,1),G::CX(0,2)];
        let pghz=Anf::from([0,1,2,4,3,5,6,7]); // |000>
        let equal=Anf::from([0,1,2,4,3,5,6]); // 000 or 111
        let bv=vec![G::X(2),G::H(0),G::H(1),G::H(2),G::CX(0,2),G::H(0),G::H(1)];
        let pbv=pghz.clone();
        let bv_out=Anf::from([1,3]); // bit0=1, bit1=0
        let adder=vec![G::CCX(0,1,2),G::CX(0,1)];
        let pa=Anf::from([0,4]); // carry initially zero
        let qa=Anf::from([0,6]); // not (sum AND carry)
        let uncompute=vec![G::CCX(0,1,3),G::CX(3,2),G::CCX(0,1,3)];
        let cases=[
            ("GHZ-correlation",3,ghz.clone(),pghz.clone(),equal,true),
            ("GHZ-negative",3,ghz,pghz,zero0.clone(),false),
            ("BV-output",3,bv.clone(),pbv.clone(),bv_out,true),
            ("BV-negative",3,bv,pbv,zero0.clone(),false),
            ("half-adder",3,adder.clone(),pa.clone(),qa,true),
            ("half-adder-negative",3,adder,pa,Anf::from([0,4]),false),
            ("uncompute",4,uncompute.clone(),zero3.clone(),zero3.clone(),true),
            ("uncompute-omitted",4,uncompute[..2].to_vec(),zero3.clone(),zero3,false),
            ("HH-interference",1,vec![G::H(0),G::H(0)],zero0.clone(),zero0.clone(),true),
            ("HTH-nonzero",1,vec![G::H(0),G::T(0),G::H(0)],zero0.clone(),zero0,false),
            ("empty-pre",1,vec![G::H(0)],Anf::new(),all.clone(),true),
        ];
        for (name,n,ops,p,q,valid) in cases{
            let r=check_case(n,&ops,&p,&q);
            assert_eq!(r.answer==Answer::Proved,valid,"{name}");
            if name=="HH-interference"||name=="BV-output"{assert_eq!(r.route,SolverRoute::ExactCount);}
            println!("HOARE_CNF_CORPUS case={name} answer={:?} route={:?} vars={} clauses={} visits={}",r.answer,r.route,r.variables,r.clauses,r.visits);
        }
        assert_eq!(verify_anf(1,&[G::H(0)],&all,&Anf::new(),0).answer,Answer::Unknown);
        assert_eq!(verify_anf(1,&[G::H(0)],&Anf::from([2]),&all,1000).answer,Answer::Unknown);
    }

    #[test]
    fn hoare_export_external_exact_fixtures(){
        let Some(dir)=std::env::var_os("HOARE_EXACT_FIXTURE_DIR") else{return;};
        let dir=std::path::PathBuf::from(dir);
        std::fs::create_dir_all(&dir).unwrap();
        let zero_pred=Anf::from([0,1]);let all=Anf::from([0]);
        let init3=Anf::from([0,1,2,3,4,5,6,7]);
        let cases=[
            ("HH",1,vec![G::H(0),G::H(0)],zero_pred.clone(),zero_pred.clone()),
            ("omega",1,vec![G::H(0),G::S(0),G::H(0)],zero_pred.clone(),zero_pred.clone()),
            ("HTH",1,vec![G::H(0),G::T(0),G::H(0)],zero_pred.clone(),zero_pred.clone()),
            ("BV",3,vec![G::X(2),G::H(0),G::H(1),G::H(2),G::CX(0,2),G::H(0),G::H(1)],init3.clone(),Anf::from([1,3])),
            ("GHZ",3,vec![G::H(0),G::CX(0,1),G::CX(0,2)],init3.clone(),Anf::from([0,1,2,3,4,5,6])),
            ("GHZ-negative",3,vec![G::H(0),G::CX(0,1),G::CX(0,2)],init3,zero_pred.clone()),
            ("free-input-negative",2,vec![G::CX(0,1)],all,Anf::from([0,2])),
        ];
        let mut manifest=String::new();
        for (name,n,ops,p,q) in cases{
            let direct=native(n,&ops).unwrap();
            let (reduced,stats)=reduced_native(n,&ops).unwrap();
            let witnesses:Vec<_>=(0..1u64<<n).filter(|&x|violated(n,&ops,&p,&q,x)).map(|x|x.to_string()).collect();
            assert_eq!(witnesses.is_empty(),matches!(name,"HH"|"BV"|"GHZ"),"fixture property intent: {name}");
            let witness_list=if witnesses.is_empty(){"-".to_owned()}else{witnesses.join(",")};
            for (route,s,scale) in [("direct",&direct,0),("rr",&reduced,stats.scale2)]{
                let (c,d)=two_copy(s,&p,&q);
                let ns=buckets(&c,d,&[],&mut 20_000_000).unwrap();
                assert_eq!(ns,direct_buckets(s,&p,&q));
                assert_eq!(zero(ns),witnesses.is_empty());
                let id=format!("{name}-{route}");
                std::fs::write(dir.join(format!("{id}.cnf")),dimacs(&c,&[]).unwrap()).unwrap();
                let counts=ns.iter().map(|x|x.to_string()).collect::<Vec<_>>().join(",");
                manifest.push_str(&format!("{name}\t{route}\t{n}\t{scale}\t{},{},{}\t{counts}\t{witness_list}\n",d[0],d[1],d[2]));
            }
        }
        std::fs::write(dir.join("manifest.tsv"),manifest).unwrap();
        println!("HOARE_EXTERNAL_FIXTURES cases=7 variants=14");
        export_scaled(&dir);
    }


    fn bit(i:usize,value:bool)->Anf {
        if value{Anf::from([1u64<<i])}else{Anf::from([0,1u64<<i])}
    }
    fn equal_bits(i:usize,j:usize)->Anf{Anf::from([0,1u64<<i,1u64<<j])}
    fn eval_conj(p:&[Anf],x:u64)->bool{p.iter().all(|f|eval(f,x))}
    struct ScaleCase{
        name:String,n:usize,ops:Vec<G>,p:Vec<Anf>,q:Vec<Anf>,
        expected:[i128;2],known_witness:Option<u64>,
    }
    fn scaled_cases()->Vec<ScaleCase>{
        let mut cases=Vec::new();
        for n in [8usize,16]{
            let mut ops=vec![G::H(0)];
            ops.extend((1..n).map(|i|G::CX(0,i)));
            let p=(0..n).map(|i|bit(i,false)).collect::<Vec<_>>();
            let q=(1..n).map(|i|equal_bits(0,i)).collect::<Vec<_>>();
            cases.push(ScaleCase{name:format!("GHZ{n}-correlation"),n,ops:ops.clone(),p:p.clone(),q,expected:[0,0],known_witness:None});
            cases.push(ScaleCase{name:format!("GHZ{n}-negative"),n,ops,p,q:vec![bit(0,false)],expected:[1,0],known_witness:Some(0)});
        }
        for k in [4usize,8]{
            let n=k+1;
            let secret=(0..k).map(|i|i%2==0).collect::<Vec<_>>();
            let mut ops=vec![G::X(k)];
            ops.extend((0..n).map(G::H));
            ops.extend((0..k).filter(|&i|secret[i]).map(|i|G::CX(i,k)));
            ops.extend((0..k).map(G::H));
            let p=(0..n).map(|i|bit(i,false)).collect::<Vec<_>>();
            let q=(0..k).map(|i|bit(i,secret[i])).collect::<Vec<_>>();
            let mut bad=q.clone();bad[0]=bit(0,!secret[0]);
            cases.push(ScaleCase{name:format!("BV{k}-correct"),n,ops:ops.clone(),p:p.clone(),q,expected:[0,0],known_witness:None});
            cases.push(ScaleCase{name:format!("BV{k}-negative"),n,ops,p,q:bad,expected:[1i128<<(2*k+1),0],known_witness:Some(0)});
        }
        for k in [2usize,4,5]{
            // Controlled-S on each parity/ancilla pair, implemented using
            // T(c) T(a) CX(c,a) Tdg(a) CX(c,a) between two H(a).
            // c = x_i xor x_(i+k), computed/uncomputed reversibly.
            let n=3*k;
            let mut ops=Vec::new();
            for i in 0..k{
                let c=i;let a=2*k+i;
                ops.extend([G::CX(i+k,c),G::H(a),G::T(c),G::T(a),G::CX(c,a)]);
                ops.extend((0..7).map(|_|G::T(a)));
                ops.extend([G::CX(c,a),G::H(a),G::CX(i+k,c)]);
            }
            let p=(2*k..n).map(|i|bit(i,false)).collect::<Vec<_>>();
            let mut safe=p.clone();safe.extend((0..k).map(|i|equal_bits(i,i+k)));
            let q=p.clone();
            // Each parity vector has 2^k input preimages. Survival for
            // fixed parity s is 2^-wt(s); raw violation over all data
            // assignments = 2^k * (2^(3k) - 2^k 3^k).
            let raw=(1i128<<k)*((1i128<<(3*k))-(1i128<<k)*3i128.pow(k as u32));
            cases.push(ScaleCase{name:format!("CS-parity{k}-safe"),n,ops:ops.clone(),p:safe,q:q.clone(),expected:[0,0],known_witness:None});
            cases.push(ScaleCase{name:format!("CS-parity{k}-negative"),n,ops,p,q,expected:[raw,0],known_witness:Some(1)});
        }
        for k in [4usize,8]{
            let n=k;
            let mut ops=Vec::new();
            for i in 0..k{ops.extend([G::H(i),G::T(i),G::H(i)]);}
            let p=(0..n).map(|i|bit(i,false)).collect::<Vec<_>>();
            // Independent HTH survival raw norm = 2+sqrt(2).
            let (mut a,mut b)=(1i128,0i128);
            for _ in 0..k{(a,b)=(2*a+2*b,a+2*b);}
            let expected=[(1i128<<(2*k))-a,-b];
            cases.push(ScaleCase{name:format!("HTH-product{k}"),n,ops,p:p.clone(),q:p,expected,known_witness:Some(0)});
        }
        cases
    }
    fn raw_for_input(n:usize,ops:&[G],q:&[Anf],x:u64)->[i128;2]{
        let mut a=0i128;let mut b=0i128;
        for (z,v) in dense_state(n,ops,x).into_iter().enumerate(){
            if eval_conj(q,z as u64){continue;}
            // |v0+v1*w+v2*i+v3*w^3|² = A+B sqrt(2).
            let [u,v,w,t]=v.map(i128::from);
            a+=u*u+v*v+w*w+t*t;
            b+=u*(v-t)+w*(v+t);
        }
        [a,b]
    }
    #[test]
    fn hoare_scaled_property_contracts(){
        // Named cases must have independent specified validity and
        // counterexample expectations, not merely solver agreement.
        for c in scaled_cases(){
            assert!(c.n<=16&&c.ops.len()<=128);
            if let Some(x)=c.known_witness{
                assert!(eval_conj(&c.p,x));
                assert_ne!(raw_for_input(c.n,&c.ops,&c.q,x),[0,0],"{}",c.name);
            }else{
                assert_eq!(c.expected,[0,0]);
                // Positive universal cases checked by their analytic
                // family identity; also independently check representative legal inputs.
                for x in [0u64,1,(1u64<<c.n)-1]{
                    if eval_conj(&c.p,x){assert_eq!(raw_for_input(c.n,&c.ops,&c.q,x),[0,0],"{}",c.name);}
                }
            }
            // Exhaustive independent gate oracle for small representatives.
            if c.n<=6{
                let mut a=[0i128;2];
                for x in 0..1u64<<c.n{
                    if eval_conj(&c.p,x){
                        let v=raw_for_input(c.n,&c.ops,&c.q,x);
                        a[0]+=v[0];a[1]+=v[1];
                    }
                }
                assert_eq!(a,c.expected,"{}",c.name);
            }
        }
    }
    // Exact affine input parameterization. Keep original input label slots
    // so existing RR still protects them. Fix unused pivot slots to zero:
    // each legal original input has exactly one encoded input.
    struct AffinePre{offset:u64,basis:Vec<u64>,free:Vec<usize>,n:usize}
    impl AffinePre{
        fn free_mask(&self)->u64{self.free.iter().fold(0,|m,&i|m|(1u64<<i))}
        fn decode(&self,encoded:u64)->u64{
            self.free.iter().zip(&self.basis).fold(self.offset,|x,(&i,&b)|if encoded>>i&1!=0{x^b}else{x})
        }
        fn guard(&self)->Vec<Anf>{
            let m=self.free_mask();
            (0..self.n).filter(|&i|m>>i&1==0).map(|i|bit(i,false)).collect()
        }
    }
    fn affine_pre(n:usize,p:&[Anf])->Option<AffinePre>{
        if n==0||n>16{return None;}
        let mut rows=Vec::new();
        for f in p{
            let mut mask=0;
            for &m in f{
                if m>>n!=0||m.count_ones()>1{return None;}
                mask|=m;
            }
            rows.push((mask,!f.contains(&0)));
        }
        let (offset,basis)=affine_solve(rows,n)?;
        // affine_solve uses ascending pivot columns. Each kernel basis
        // vector has its distinguished free bit as the highest set bit.
        let free:Vec<_>=basis.iter().map(|&b|(63-b.leading_zeros()) as usize).collect();
        let model=AffinePre{offset,basis,free,n};
        let mask=model.free_mask();
        if model.free.len()!=mask.count_ones() as usize||model.offset&mask!=0||
            model.free.iter().zip(&model.basis).any(|(&i,&b)|b&mask!=1u64<<i) {return None;}
        Some(model)
    }
    fn specialize_affine(mut ps:PathSum,n:usize,p:&[Anf])->Option<(PathSum,AffinePre)>{
        let model=affine_pre(n,p)?;
        for i in 0..n{
            if model.free_mask()>>i&1!=0{continue;}
            let mut replacement=rustc_hash::FxHashSet::default();
            if model.offset>>i&1!=0{replacement.insert(vec![]);}
            for (&j,&v) in model.free.iter().zip(&model.basis){
                if v>>i&1!=0{replacement.insert(vec![j as u32]);}
            }
            // Guard against dense affine substitution and term growth.
            if replacement.len()>8{return None;}
            ps.f.substitute_var_with_poly(i as u32,&replacement);
            ps.p.substitute_var_with_poly(i as u32,&replacement);
            let state=compact(&ps,n)?;
            if state.phase.len()+state.output.iter().map(|f|f.len()).sum::<usize>()>256{return None;}
        }
        Some((ps,model))
    }
    #[test]
    fn hoare_affine_pre_parameterization(){
        // All subsets of the six nontrivial equations on two input bits.
        // Validate the representation, including inconsistent preconditions,
        // against direct truth evaluation rather than just the same RREF.
        let eqs:Vec<Anf>=(1..4u64).flat_map(|m|{
            let f:Anf=(0..2).filter(|&i|m>>i&1!=0).map(|i|1u64<<i).collect();
            let mut g=f.clone();g.insert(0);[f,g]
        }).collect();
        let gates=[G::H(0),G::H(1),G::CX(0,1),G::CZ(0,1),G::T(0),G::S(1)];
        let posts=[Anf::from([0,1]),Anf::from([0,2]),Anf::from([0,1,2]),Anf::from([3])];
        let mut cases=0;let mut consistent=0;
        for m in 0..64u64{
            let p:Vec<_>=eqs.iter().enumerate().filter(|(i,_)|m>>i&1!=0).map(|(_,f)|f.clone()).collect();
            let legal:BTreeSet<_>=(0..4).filter(|&x|eval_conj(&p,x)).collect();
            let Some(model)=affine_pre(2,&p) else{assert!(legal.is_empty());continue;};
            let coded:Vec<_>=(0..4).filter(|&x|x&!model.free_mask()==0).collect();
            assert_eq!(coded.len(),legal.len());
            assert_eq!(coded.iter().map(|&x|model.decode(x)).collect::<BTreeSet<_>>(),legal);
            consistent+=1;
            for g in &gates{for h in &gates{
                let ops=[G::H(0),g.clone(),h.clone()];
                let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
                for op in &ops{op.apply(&mut ps,false);}
                let direct=compact(&ps,2).unwrap();
                let (special,model)=specialize_affine(ps,2,&p).unwrap();
                let a=compact(&special,2).unwrap();
                for &x in &coded{for y in 0..1u64<<a.h{
                    assert_eq!(path(&direct,model.decode(x),y),path(&a,x,y));
                }}
                let (r,stats)=reduce_existing(special,2).unwrap();
                for q in &posts{
                    let (c,d)=two_copy_conj(&direct,&p,std::slice::from_ref(q));
                    let orig=signed(buckets(&c,d,&[],&mut 20_000_000).unwrap());
                    for (s,scale) in [(&a,0),(&r,stats.scale2)]{
                        let (c,d)=two_copy_conj(s,&model.guard(),std::slice::from_ref(q));
                        let res=signed(buckets(&c,d,&[],&mut 20_000_000).unwrap());
                        assert_eq!(orig,res.map(|v|v*(1i128<<scale)));
                        for &x in &coded{
                            let prefix:Vec<_>=(0..2).map(|i|if x>>i&1!=0{i as i32+2}else{-(i as i32+2)}).collect();
                            let coeff=signed(buckets(&c,d,&prefix,&mut 20_000_000).unwrap());
                            assert_eq!(coeff==[0;4],!violated(2,&ops,&Anf::from([0]),q,model.decode(x)));
                        }
                    }
                    cases+=1;
                }
            }}
        }
        assert_eq!(cases,consistent*36*4);
        assert!(affine_pre(2,&[Anf::from([3])]).is_none());
        println!("HOARE_AFFINE_PRE_DIFFERENTIAL cases={cases} consistent_constraint_subsets={consistent} exact_paths_coefficients_witness=true");
    }
    fn export_scaled(dir:&std::path::Path){
        let mut manifest=String::new();
        for c in scaled_cases(){
            // A separate bounded admission for the named benchmark family,
            // not a widening of production or general verifier admission.
            let h=c.ops.iter().filter(|g|matches!(g,G::H(_))).count();
            assert!(c.n<=16&&h<=32&&c.n+h<=63&&c.ops.len()<=128);
            let mut ps=PathSum::new(c.n);ps.set_auto_reduce(false);
            for g in &c.ops{g.apply(&mut ps,false);}
            let direct=compact(&ps,c.n).unwrap();
            assert_eq!(direct.h,h);
            let t=std::time::Instant::now();
            let (rr,stats)=reduce_existing(ps.clone(),c.n).expect("bounded benchmark RR");
            let rr_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (special,model)=specialize_affine(ps,c.n,&c.p).expect("affine benchmark precondition");
            let pre=compact(&special,c.n).unwrap();
            let pre_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (pre_rr,pre_stats)=reduce_existing(special,c.n).expect("bounded precondition RR");
            let pre_rr_us=pre_us+t.elapsed().as_micros();
            let guard=model.guard();
            if let Some(x)=c.known_witness{
                assert_eq!(model.decode(x&model.free_mask()),x);
            }
            for (route,s,scale,p,prep_us,param) in [
                ("direct",&direct,0,&c.p,0,false),
                ("rr",&rr,stats.scale2,&c.p,rr_us,false),
                ("pre",&pre,0,&guard,pre_us,true),
                ("pre-rr",&pre_rr,pre_stats.scale2,&guard,pre_rr_us,true)]{
                let start=std::time::Instant::now();
                let (cnf,d)=two_copy_conj(s,p,&c.q);
                let encoding_us=start.elapsed().as_micros();
                // Resource limit is a reported outcome, not a pass.
                let text=dimacs(&cnf,&[]);
                let status=if let Some(text)=text{
                    std::fs::write(dir.join(format!("scale-{}-{route}.cnf",c.name)),text).unwrap();
                    "READY"
                }else{"UNKNOWN_ENCODING_LIMIT"};
                let witness=c.known_witness.map(|x|x.to_string()).unwrap_or("-".to_owned());
                let query_witness=c.known_witness.map(|x|if param{x&model.free_mask()}else{x}).map(|x|x.to_string()).unwrap_or("-".to_owned());
                manifest.push_str(&format!("{}\t{route}\t{}\t{}\t{scale}\t{},{},{}\t{},{}\t{witness}\t{}\t{}\t{encoding_us}\t{status}\t{query_witness}\t{prep_us}\t{}\n",
                    c.name,c.n,s.h,d[0],d[1],d[2],c.expected[0],c.expected[1],cnf.vars,cnf.clauses.len(),s.phase.len()));
            }
        }
        std::fs::write(dir.join("scaled.tsv"),manifest).unwrap();
        println!("HOARE_SCALED_FIXTURES cases=16 variants=64");
    }

}
