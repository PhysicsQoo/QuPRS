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
        if !c.bounded(){return None;}
        serialize_external(c,assumptions)
    }
    fn serialize_external(c:&Cnf,assumptions:&[Lit])->Option<String>{
        if c.vars>4096||c.clauses.len()+assumptions.len()>32768||assumptions.iter().any(|&l|l==0||l.unsigned_abs() as usize>c.vars){return None;}
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
        export_hybrid(&dir);
        export_rare_wmc(&dir);
        export_scale_benchmark(&dir);
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

    #[derive(Default,Debug)]
    struct GuardPhaseStats{groups:usize,constant:usize,queries:usize,visits:u64}
    // For each path monomial, its coefficient is a Z8 polynomial in
    // original input bits. Prove constancy under the original precondition
    // using exact SAT, not a sampled input. Preserve input labels and guard.
    fn guard_phase(mut ps:PathSum,n:usize,p:&[Anf],grouped:bool,budget:u64)->Option<(PathSum,GuardPhaseStats)>{
        let s=compact(&ps,n)?;
        if n+s.h>63||(0..n+s.h).any(|i|!ps.v.path_vars.contains(&(i as u32)))||
            p.iter().flatten().any(|&m|m>>n!=0)||s.phase.len()>256{return None;}
        let mask=(1u64<<n)-1;
        let mut base=Cnf::new(n);
        let bits:Vec<_>=(0..n).map(|i|i as Lit+2).collect();
        for pred in p{let l=base.anf(pred,&bits);base.enforce(l);}
        let mut fuel=budget;
        if count(&base,&[],&mut fuel,true)?==0{return None;}
        let mut groups=BTreeMap::<(u64,u64),BTreeMap<u64,u8>>::new();
        for (&m,&k) in &s.phase{
            let key=(m&!mask,if grouped{0}else{m&mask});
            groups.entry(key).or_default().insert(m&mask,k);
        }
        let mut out=BTreeMap::new();
        let mut stats=GuardPhaseStats::default();
        for ((path,_),poly) in groups{
            stats.groups+=1;
            let mut cnf=base.clone();
            let mut value=[ZERO;3];
            for (&m,&k) in &poly{
                let l=cnf.monomial(m,&bits);
                let term=std::array::from_fn(|i|if k>>i&1!=0{l}else{ZERO});
                value=cnf.add3(value,term);
            }
            let mut constant=Some(0u8);
            for (i,&l) in value.iter().enumerate(){
                stats.queries+=2;
                let yes=count(&cnf,&[l],&mut fuel,true)?;
                let no=count(&cnf,&[-l],&mut fuel,true)?;
                if yes==0&&no==0{return None;}
                if yes!=0&&no!=0{constant=None;break;}
                if yes!=0{if let Some(c)=constant.as_mut(){*c|=1<<i;}}
            }
            if let Some(c)=constant{
                stats.constant+=1;
                add_phase(&mut out,path,c);
            }else{
                for (m,k) in poly{add_phase(&mut out,m|path,k);}
            }
        }
        // Rebuild exact native Z8 phase only; leave output and labels intact.
        ps.p.terms.clear();
        for (m,k) in out{
            let mono=(0..n+s.h).filter(|&i|m>>i&1!=0).map(|i|i as u32).collect();
            ps.p.add_term(mono,quprs::PhaseCoeff::new_constant(quprs::Rational::new(k as i64,8)));
        }
        stats.visits=budget-fuel;
        Some((ps,stats))
    }
    fn nonlinear_cases()->Vec<ScaleCase>{
        let mut cases=Vec::new();
        for k in [1usize,2]{
            let n=6*k;
            let mut ops=Vec::new();
            let mut p=Vec::new();
            let mut safe=Vec::new();
            for i in 0..k{
                let j=6*i;let c=j+4;let a=j+5;
                ops.extend([G::CCX(j,j+1,c),G::CCX(j+2,j+3,c),G::H(a),
                    G::T(c),G::T(a),G::CX(c,a)]);
                ops.extend((0..7).map(|_|G::T(a)));
                ops.extend([G::CX(c,a),G::H(a),G::CCX(j+2,j+3,c),G::CCX(j,j+1,c)]);
                p.extend([bit(c,false),bit(a,false)]);
                safe.push(Anf::from([0,3u64<<j,12u64<<j]));
            }
            let q=p.clone();
            safe.extend(p.clone());
            let raw=(1i128<<(2*k))*(16i128.pow(k as u32)-13i128.pow(k as u32));
            cases.push(ScaleCase{name:format!("CS-nonlinear{k}-safe"),n,ops:ops.clone(),p:safe,q:q.clone(),expected:[0,0],known_witness:None});
            cases.push(ScaleCase{name:format!("CS-nonlinear{k}-negative"),n,ops,p,q,expected:[raw,0],known_witness:Some(3)});
        }
        cases
    }
    #[test]
    fn hoare_guard_phase_nonlinear(){
        // Differential admission, including non-affine predicates, and
        // explicitly compare phase at each legal input/path before RR.
        let gates=[G::H(0),G::H(1),G::CZ(0,1),G::CX(0,1),G::T(0),G::S(1)];
        let mut cases=0;
        for m in 1..16u64{
            let p=vec![(0..4).filter(|i|m>>i&1!=0).collect::<Anf>()];
            for g in &gates{for h in &gates{
                let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
                for op in [G::H(0),g.clone(),h.clone()]{op.apply(&mut ps,false);}
                let direct=compact(&ps,2).unwrap();
                for grouped in [false,true]{
                    let (special,_)=guard_phase(ps.clone(),2,&p,grouped,2_000_000).unwrap();
                    let s=compact(&special,2).unwrap();
                    for x in (0..4).filter(|&x|eval_conj(&p,x)){
                        for y in 0..1u64<<s.h{assert_eq!(path(&s,x,y),path(&direct,x,y));}
                    }
                    let (r,stats)=reduce_existing(special,2).unwrap();
                    for q in [Anf::from([0,1]),Anf::from([3])]{
                        let (a,d)=two_copy_conj(&direct,&p,std::slice::from_ref(&q));
                        let (b,e)=two_copy_conj(&r,&p,std::slice::from_ref(&q));
                        assert_eq!(signed(buckets(&a,d,&[],&mut 20_000_000).unwrap()),
                            signed(buckets(&b,e,&[],&mut 20_000_000).unwrap()).map(|v|v*(1i128<<stats.scale2)));
                        cases+=1;
                    }
                }
            }}
        }
        assert_eq!(cases,2160);
        let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
        G::H(0).apply(&mut ps,false);
        assert!(guard_phase(ps.clone(),2,&[Anf::new()],true,2_000_000).is_none());
        assert!(guard_phase(ps,2,&[Anf::from([0])],true,0).is_none());
        for c in nonlinear_cases(){
            if c.name.ends_with("-safe"){assert!(affine_pre(c.n,&c.p).is_none());}
            if let Some(x)=c.known_witness{
                assert!(eval_conj(&c.p,x));
                assert_ne!(raw_for_input(c.n,&c.ops,&c.q,x),[0,0]);
            }
            if c.n<=6{
                let mut total=[0i128;2];
                for x in (0..1u64<<c.n).filter(|&x|eval_conj(&c.p,x)){
                    let a=raw_for_input(c.n,&c.ops,&c.q,x);
                    total[0]+=a[0];total[1]+=a[1];
                }
                assert_eq!(total,c.expected);
            }
            let mut ps=PathSum::new(c.n);ps.set_auto_reduce(false);
            for op in &c.ops{op.apply(&mut ps,false);}
            let (term,_)=guard_phase(ps.clone(),c.n,&c.p,false,2_000_000).unwrap();
            let (group,_)=guard_phase(ps,c.n,&c.p,true,2_000_000).unwrap();
            let (term,_)=reduce_existing(term,c.n).unwrap();
            let (group,_)=reduce_existing(group,c.n).unwrap();
            if c.name.ends_with("-safe"){
                assert!(term.h>0,"termwise baseline unexpectedly eliminates all paths");
                assert_eq!(group.h,0,"grouped guard should unlock HH");
            }else{assert!(group.h>0);}
        }
        println!("HOARE_GUARD_PHASE_DIFFERENTIAL cases={cases} nonlinear_family=true");
    }

    // Stronger falsification baseline: a Boolean equation p=1 permits
    // replacing a complete input monomial M by the XOR of remaining terms.
    // Every replacement is valid only under the unchanged precondition.
    fn xor_insert(f:&mut Anf,m:u64){if !f.insert(m){f.remove(&m);}}
    fn mul_anf(a:&Anf,b:&Anf)->Option<Anf>{
        if a.len().checked_mul(b.len())?>4096{return None;}
        let mut out=Anf::new();
        for &x in a{for &y in b{xor_insert(&mut out,x|y);}}
        if out.len()>256{return None;}Some(out)
    }
    fn lift_anf(a:&Anf)->Option<BTreeMap<u64,u8>>{
        let mut out=BTreeMap::new();
        for &m in a{
            // Boolean XOR lifted exactly to Z8: a+b-2ab.
            let old=out.clone();
            add_phase(&mut out,m,1);
            for (q,k) in old{add_phase(&mut out,q|m,(8-(2*k)%8)%8);}
            if out.len()>256{return None;}
        }
        Some(out)
    }
    fn mono_substitute(mut ps:PathSum,n:usize,p:&[Anf])->Option<PathSum>{
        let mut s=compact(&ps,n)?;
        for pred in p{
            let mut equation=pred.clone();xor_insert(&mut equation,0);
            let Some(m)=equation.iter().copied().filter(|&v|v!=0).max_by_key(|&v|(v.count_ones(),v)) else{
                if equation.contains(&0){return None;}continue;
            };
            if m>>n!=0||equation.iter().any(|&v|v>>n!=0){return None;}
            equation.remove(&m);
            let lifted=lift_anf(&equation)?;
            for output in &mut s.output{
                let old=std::mem::take(output);
                for t in old{
                    if t&m==m{
                        for &r in &equation{xor_insert(output,(t&!m)|r);}
                    }else{xor_insert(output,t);}
                }
                if output.len()>256{return None;}
            }
            let old=std::mem::take(&mut s.phase);
            for (t,k) in old{
                if t&m==m{
                    for (&r,&v) in &lifted{add_phase(&mut s.phase,(t&!m)|r,(k*v)%8);}
                }else{add_phase(&mut s.phase,t,k);}
            }
            if s.phase.len()+s.output.iter().map(|a|a.len()).sum::<usize>()>256{return None;}
        }
        ps.p.terms.clear();
        for (m,k) in s.phase{
            ps.p.add_term((0..n+s.h).filter(|&i|m>>i&1!=0).map(|i|i as u32).collect(),
                quprs::PhaseCoeff::new_constant(quprs::Rational::new(k as i64,8)));
        }
        for (dst,src) in ps.f.functions.iter_mut().zip(s.output){
            *dst=src.into_iter().map(|m|(0..n+s.h).filter(|&i|m>>i&1!=0).map(|i|i as u32).collect()).collect();
        }
        Some(ps)
    }
    // Construct the complete masked map (I-Q)SP using Fourier indicators.
    // Each added path variable contributes 2 times the indicator. For the
    // raw squared norm, divide by 4 per mask variable after standard RR.
    // This is an explicit Fourier-mask baseline, NOT a general SOP package.
    fn compose_anf(f:&Anf,outputs:&[Anf])->Option<Anf>{
        let mut out=Anf::new();
        for &m in f{
            if m>>outputs.len()!=0{return None;}
            let mut prod=Anf::from([0]);
            for (i,o) in outputs.iter().enumerate(){if m>>i&1!=0{prod=mul_anf(&prod,o)?;}}
            for t in prod{xor_insert(&mut out,t);}
            if out.len()>256{return None;}
        }
        Some(out)
    }
    fn masked_map(mut ps:PathSum,n:usize,p:&[Anf],q:&[Anf])->Option<(PathSum,i32)>{
        let s=compact(&ps,n)?;
        let mut post=Anf::from([0]);
        for f in q{post=mul_anf(&post,&compose_anf(f,&s.output)?)?;}
        let mut violations:Vec<Anf>=p.iter().map(|f|{
            let mut f=f.clone();xor_insert(&mut f,0);f
        }).collect();
        violations.push(post);
        let g=violations.len() as i32;
        if n+s.h+g as usize>63{return None;}
        for f in violations{
            let y=ps.v.get_fresh_var();
            for m in f{
                let mut mono:Vec<_>=(0..n+s.h).filter(|&i|m>>i&1!=0).map(|i|i as u32).collect();
                mono.push(y);ps.p.add_term(mono,quprs::PhaseCoeff::HALF);
            }
        }
        Some((ps,2*g))
    }
    fn scaled_eq(a:[i128;4],b:[i128;4],scale:i32){
        if scale>=0{assert_eq!(a,b.map(|v|v*(1i128<<scale)));}
        else{assert_eq!(a.map(|v|v*(1i128<<(-scale))),b);}
    }
    #[test]
    fn hoare_strong_baseline_differential(){
        let gates=[G::H(0),G::H(1),G::CZ(0,1),G::CX(0,1),G::T(0),G::S(1)];
        let mut cases=0;
        for p in [Anf::from([0,3]),Anf::from([1,2]),Anf::from([0,1]),Anf::from([3])]{
            let p=vec![p];
            for g in &gates{for h in &gates{
                let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
                for op in [g.clone(),h.clone()]{op.apply(&mut ps,false);}
                let direct=compact(&ps,2).unwrap();
                let sub=mono_substitute(ps.clone(),2,&p).unwrap();
                let specialized=compact(&sub,2).unwrap();
                for x in (0..4).filter(|&x|eval_conj(&p,x)){
                    for y in 0..1u64<<direct.h{assert_eq!(path(&direct,x,y),path(&specialized,x,y));}
                }
                let (sub,st)=reduce_existing(sub,2).unwrap();
                for q in [vec![Anf::from([0,1])],vec![Anf::from([3])]]{
                    let (a,d)=two_copy_conj(&direct,&p,&q);
                    let exact=signed(buckets(&a,d,&[],&mut 20_000_000).unwrap());
                    let (a,d)=two_copy_conj(&sub,&p,&q);
                    scaled_eq(exact,signed(buckets(&a,d,&[],&mut 20_000_000).unwrap()),st.scale2 as i32);
                    let (masked,den)=masked_map(ps.clone(),2,&p,&q).unwrap();
                    let (masked,ms)=reduce_existing(masked,2).unwrap();
                    let (a,d)=two_copy_conj(&masked,&[],&[Anf::new()]);
                    scaled_eq(exact,signed(buckets(&a,d,&[],&mut 20_000_000).unwrap()),ms.scale2 as i32-den);
                    cases+=1;
                }
            }}
        }
        assert_eq!(cases,288);
        println!("HOARE_STRONG_BASELINE_DIFFERENTIAL cases={cases} exact_masked_and_monomial=true");
    }
    fn export_nonlinear(dir:&std::path::Path,manifest:&mut String){
        for c in nonlinear_cases(){
            let mut ps=PathSum::new(c.n);ps.set_auto_reduce(false);
            for op in &c.ops{op.apply(&mut ps,false);}
            let direct=compact(&ps,c.n).unwrap();
            let t=std::time::Instant::now();
            let (rr,rstats)=reduce_existing(ps.clone(),c.n).unwrap();
            let rr_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (term,tstats)=guard_phase(ps.clone(),c.n,&c.p,false,2_000_000).unwrap();
            let (term,trs)=reduce_existing(term,c.n).unwrap();
            let term_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let sub=mono_substitute(ps.clone(),c.n,&c.p).unwrap();
            let (sub,ss)=reduce_existing(sub,c.n).unwrap();
            let sub_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (masked,den)=masked_map(ps.clone(),c.n,&c.p,&c.q).unwrap();
            let (masked,ms)=reduce_existing(masked,c.n).unwrap();
            let masked_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (group,gstats)=guard_phase(ps,c.n,&c.p,true,2_000_000).unwrap();
            let g=compact(&group,c.n).unwrap();
            let group_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (gr,grs)=reduce_existing(group,c.n).unwrap();
            let gr_us=group_us+t.elapsed().as_micros();
            println!("HOARE_GUARD_PHASE_STATS case={} termwise={tstats:?} grouped={gstats:?}",c.name);
            let empty:Vec<Anf>=vec![];
            let never=vec![Anf::new()];
            for (route,s,scale,prep_us,p,q) in [
                ("direct",&direct,0,0,&c.p,&c.q),("rr",&rr,rstats.scale2 as i32,rr_us,&c.p,&c.q),
                ("term-rr",&term,trs.scale2 as i32,term_us,&c.p,&c.q),("guard",&g,0,group_us,&c.p,&c.q),
                ("guard-rr",&gr,grs.scale2 as i32,gr_us,&c.p,&c.q),
                ("mono-rr",&sub,ss.scale2 as i32,sub_us,&c.p,&c.q),
                ("masked-rr",&masked,ms.scale2 as i32-den,masked_us,&empty,&never)]{
                let t=std::time::Instant::now();
                let (cnf,d)=two_copy_conj(s,p,q);
                let encoding_us=t.elapsed().as_micros();
                let status=if let Some(text)=dimacs(&cnf,&[]){
                    std::fs::write(dir.join(format!("scale-{}-{route}.cnf",c.name)),text).unwrap();
                    "READY"
                }else{"UNKNOWN_ENCODING_LIMIT"};
                let witness=c.known_witness.map(|x|x.to_string()).unwrap_or("-".to_owned());
                manifest.push_str(&format!("{}\t{route}\t{}\t{}\t{scale}\t{},{},{}\t{},{}\t{witness}\t{}\t{}\t{encoding_us}\t{status}\t{witness}\t{prep_us}\t{}\n",
                    c.name,c.n,s.h,d[0],d[1],d[2],c.expected[0],c.expected[1],cnf.vars,cnf.clauses.len(),s.phase.len()));
            }
        }
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
        export_nonlinear(dir,&mut manifest);
        export_partial_fibers(dir,&mut manifest);
        std::fs::write(dir.join("scaled.tsv"),manifest).unwrap();
        println!("HOARE_SCALED_FIXTURES cases=22 variants=96");
    }


    // R12: prove cancellation on complete forbidden output fibers.
    // A failed candidate or exhausted budget is NOT a counterexample.
    #[derive(Default,Debug)]
    struct FiberStats{
        clauses_proved:usize, empty_guards:usize, queries:usize,
        directions:Vec<u64>, visits:u64, peak_vars:usize, peak_clauses:usize,
    }
    fn fiber_candidates(s:&Symbolic,pairs:bool)->Vec<u64>{
        if s.h==0||s.h>32||s.n+s.h>63{return vec![];}
        let imask=(1u64<<s.n)-1;
        let mut rows=Vec::new();
        let mut affine=true;
        for o in &s.output{
            let mut row=0u64;
            for &m in o{
                if m&!imask==0{continue;}
                if m.count_ones()!=1{affine=false;break;}
                row^=m>>s.n;
            }
            if !affine{break;}
            rows.push((row,false));
        }
        let basis=if affine{
            affine_solve(rows,s.h).expect("homogeneous kernel").1
        }else{(0..s.h).map(|i|1u64<<i).collect()};
        let mut out=Vec::new();
        // Singletons first, then kernel generators, then pair combinations.
        for &b in &basis{if b.count_ones()==1{out.push(b);}}
        if pairs{
            for &b in &basis{if b.count_ones()>1{out.push(b);}}
            for i in 0..basis.len(){for j in i+1..basis.len(){
                if out.len()>=64{break;}
                let b=basis[i]^basis[j];
                if b!=0&&!out.contains(&b){out.push(b);}
            }}
        }
        out.truncate(64);
        out
    }
    fn fiber_guard(s:&Symbolic,p:&[Anf],q:&Anf)->(Cnf,Vec<Lit>,Vec<Lit>){
        let mut c=Cnf::new(s.n+s.h);
        let bits:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        for f in p{let l=c.anf(f,&bits[..s.n]);c.enforce(l);}
        let z:Vec<_>=s.output.iter().map(|o|c.anf(o,&bits)).collect();
        let post=c.anf(q,&z);c.enforce(-post);
        (c,bits,z)
    }
    fn fiber_bad(c:&Cnf,bits:&[Lit],z:&[Lit],s:&Symbolic,d:u64)->Option<Cnf>{
        if d==0||d>>s.h!=0{return None;}
        let flip=d<<s.n;
        let gap=translation_gap(&s.phase,flip,true)?;
        if gap.len()>256{return None;}
        let mut c=c.clone();
        let shifted:Vec<_>=bits.iter().enumerate().map(|(i,&b)|if flip>>i&1!=0{-b}else{b}).collect();
        let mut bad=ZERO;
        for (o,&original) in s.output.iter().zip(z){
            let other=c.anf(o,&shifted);
            let neq=c.xor(original,other);
            bad=c.or(bad,neq);
        }
        // translation_gap(...,true) = f(y xor d)-f(y)+4 mod 8.
        // It must be identically zero on the complete forbidden fiber.
        let diff=Symbolic{n:s.n,h:s.h,output:vec![],phase:gap};
        for bit in c.phase(&diff,bits,false){bad=c.or(bad,bit);}
        c.enforce(bad);
        Some(c)
    }
    fn prove_fibers(s:&Symbolic,p:&[Anf],q:&[Anf],pairs:bool,budget:u64)->Option<FiberStats>{
        if s.n==0||s.n+s.h>63||s.h>32||
            p.iter().chain(q).flatten().any(|&m|m>>s.n!=0)||
            p.iter().chain(q).map(|f|f.len()).sum::<usize>()>256||
            s.phase.len()>256{return None;}
        let mut fuel=budget;
        let candidates=fiber_candidates(s,pairs);
        let mut stats=FiberStats::default();
        // Each violated conjunct is a union of complete output fibers.
        // Prove zero separately for each; do NOT add overlapping risks.
        for f in q{
            let (base,bits,z)=fiber_guard(s,p,f);
            stats.queries+=1;
            stats.peak_vars=stats.peak_vars.max(base.vars);
            stats.peak_clauses=stats.peak_clauses.max(base.clauses.len());
            if count(&base,&[],&mut fuel,true)?==0{
                stats.empty_guards+=1;stats.clauses_proved+=1;continue;
            }
            let mut found=false;
            for &d in &candidates{
                let Some(c)=fiber_bad(&base,&bits,&z,s,d) else{continue;};
                if !c.bounded(){continue;}
                stats.queries+=1;
                stats.peak_vars=stats.peak_vars.max(c.vars);
                stats.peak_clauses=stats.peak_clauses.max(c.clauses.len());
                if count(&c,&[],&mut fuel,true)?==0{
                    stats.directions.push(d);stats.clauses_proved+=1;
                    found=true;break;
                }
            }
            if !found{return None;}
        }
        stats.visits=budget-fuel;
        Some(stats)
    }
    fn conditional_post_case(k:usize)->(Vec<G>,Vec<Anf>,Vec<Anf>,Vec<Anf>){
        let mut ops=Vec::new();let mut p=Vec::new();
        let mut q=Vec::new();let mut strict=Vec::new();
        for i in 0..k{
            let j=3*i;let c=j;let a=j+2;
            ops.extend([G::CX(j+1,c),G::H(a),G::T(c),G::T(a),G::CX(c,a)]);
            ops.extend((0..7).map(|_|G::T(a)));
            ops.extend([G::CX(c,a),G::H(a),G::CX(j+1,c)]);
            p.push(bit(a,false));
            strict.push(bit(a,false));
            // Only demand cleanup when the two OUTPUT data bits agree.
            // Data are restored, but p does not constrain their parity.
            q.push(Anf::from([0,1u64<<a,(1u64<<a)|(1u64<<j),(1u64<<a)|(1u64<<(j+1))]));
        }
        (ops,p,q,strict)
    }
    #[test]
    fn hoare_forbidden_fiber_sat(){
        let gates=[G::H(0),G::H(1),G::CX(0,1),G::CZ(0,1),G::T(0),G::S(1)];
        let preds=[Anf::from([0]),Anf::from([0,1]),Anf::from([0,1,2]),Anf::from([3])];
        let mut cases=0;let mut valid=0;let mut proved=0;
        for g in &gates{for h in &gates{
            let ops=[G::H(0),g.clone(),h.clone()];
            let s=native(2,&ops).unwrap();
            for p in &preds{for q in &preds{
                let truth=(0..4).all(|x|!violated(2,&ops,p,q,x));
                if truth{valid+=1;}
                if prove_fibers(&s,std::slice::from_ref(p),std::slice::from_ref(q),true,1_000_000).is_some(){
                    assert!(truth,"unsound fiber proof");
                    proved+=1;
                }
                cases+=1;
            }}
        }}
        assert_eq!(cases,576);
        assert!(proved>0&&proved<=valid);
        println!("HOARE_FIBER_DIFFERENTIAL cases={cases} valid={valid} proved={proved} no_false_proof=true");

        // Non-Clifford Fourier circuit with an invariant joint translation:
        // H^2 exp(i*pi/4*(y0 xor y1)) H^2. Neither singleton works.
        let ops=[G::H(0),G::H(1),G::CX(0,1),G::T(1),G::CX(0,1),G::H(0),G::H(1)];
        let s=native(2,&ops).unwrap();
        let p=vec![bit(0,false),bit(1,false)];let q=vec![equal_bits(0,1)];
        assert_eq!(raw_for_input(2,&ops,&q,0),[0,0]);
        assert!(prove_fibers(&s,&p,&q,false,2_000_000).is_none());
        let joint=prove_fibers(&s,&p,&q,true,2_000_000).expect("joint translation");
        assert_eq!(joint.directions,vec![3]);
        let mut mutant=ops.to_vec();mutant.insert(5,G::T(0));
        let bad=native(2,&mutant).unwrap();
        assert_ne!(raw_for_input(2,&mutant,&q,0),[0,0]);
        assert!(prove_fibers(&bad,&p,&q,true,2_000_000).is_none());
        assert!(prove_fibers(&s,&p,&q,true,0).is_none());
        println!("HOARE_FIBER_JOINT stats={joint:?} mutant_inconclusive=true");

        for k in [1usize,2]{
            let n=3*k;
            let (ops,p,q,strict)=conditional_post_case(k);
            let s=native(n,&ops).unwrap();
            for x in (0..1u64<<n).filter(|&x|eval_conj(&p,x)){
                assert_eq!(raw_for_input(n,&ops,&q,x),[0,0]);
            }
            assert_ne!(raw_for_input(n,&ops,&strict,1),[0,0]);
            let t=std::time::Instant::now();
            let proof=prove_fibers(&s,&p,&q,true,20_000_000).expect("conditional forbidden fibers");
            let proof_us=t.elapsed().as_micros();
            assert_eq!(proof.directions.len(),k);
            assert!(prove_fibers(&s,&p,&strict,true,20_000_000).is_none());
            let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
            for op in &ops{op.apply(&mut ps,false);}
            let (rr,st)=reduce_existing(ps.clone(),n).unwrap();
            let (mono,mt)=reduce_existing(mono_substitute(ps.clone(),n,&p).unwrap(),n).unwrap();
            let (masked,den)=masked_map(ps,n,&p,&q).unwrap();
            let (masked,ms)=reduce_existing(masked,n).unwrap();
            // Independently evaluate baseline exact counts where feasible.
            // Dense truth above is exhaustive, not dependent on these counts.
            for (route,state,pre,post,scale) in [
                ("direct",&s,p.as_slice(),q.as_slice(),0),
                ("rr",&rr,p.as_slice(),q.as_slice(),st.scale2 as i32),
                ("mono-rr",&mono,p.as_slice(),q.as_slice(),mt.scale2 as i32),
                ("masked-rr",&masked,&[][..],&[Anf::new()][..],ms.scale2 as i32-den)]{
                let (cnf,d)=two_copy_conj(state,pre,post);
                let mut fuel=5_000_000;
                let ns=buckets(&cnf,d,&[],&mut fuel);
                if let Some(ns)=ns{assert!(zero(ns));}
                println!("HOARE_FIBER_BASELINE k={k} route={route} h={} vars={} clauses={} visits={} exact_count_completed={} scale={scale}",
                    state.h,cnf.vars,cnf.clauses.len(),5_000_000-fuel,ns.is_some());
            }
            println!("HOARE_FIBER_CONDITIONAL k={k} h={} proof_us={proof_us} stats={proof:?} negative_inconclusive=true",s.h);
        }
    }


    // R13: remove a complete opposite-phase pair, even if other paths in
    // the same fiber survive. The cancellation predicate is invariant
    // under the selected involution. Both copies MUST use the filter.
    fn cancel_lit(c:&mut Cnf,s:&Symbolic,bits:&[Lit],d:u64)->Option<Lit>{
        if d==0||d>>s.h!=0||s.n+s.h>63{return None;}
        let flip=d<<s.n;
        let gap=translation_gap(&s.phase,flip,true)?;
        if gap.len()>256{return None;}
        let shifted:Vec<_>=bits.iter().enumerate().map(|(i,&l)|if flip>>i&1!=0{-l}else{l}).collect();
        let mut good=ONE;
        for o in &s.output{
            let a=c.anf(o,bits);let b=c.anf(o,&shifted);
            let diff=c.xor(a,b);good=c.and(good,-diff);
        }
        let diff=Symbolic{n:s.n,h:s.h,output:vec![],phase:gap};
        for l in c.phase(&diff,bits,false){good=c.and(good,-l);}
        Some(good)
    }
    fn residual_one(s:&Symbolic,p:&[Anf],q:&[Anf],d:u64)->Option<(Cnf,Lit)>{
        let mut c=Cnf::new(s.n+s.h);
        let bits:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        for f in p{let l=c.anf(f,&bits[..s.n]);c.enforce(l);}
        let z:Vec<_>=s.output.iter().map(|o|c.anf(o,&bits)).collect();
        let post=q.iter().fold(ONE,|a,f|{let l=c.anf(f,&z);c.and(a,l)});
        c.enforce(-post);
        let good=cancel_lit(&mut c,s,&bits,d)?;
        Some((c,good))
    }
    fn residual_two(s:&Symbolic,p:&[Anf],q:&[Anf],d:u64)->Option<(Cnf,[Lit;3])>{
        let (mut c,delta)=two_copy_conj(s,p,q);
        let left:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        let right:Vec<_>=(0..s.n).map(|i|i as Lit+2)
            .chain((s.n+s.h..s.n+2*s.h).map(|i|i as Lit+2)).collect();
        for bits in [&left,&right]{
            let good=cancel_lit(&mut c,s,bits,d)?;
            c.enforce(-good);
        }
        Some((c,delta))
    }
    // Bounded candidate selection. SAT only establishes existence of a
    // cancellable pair; it never refutes the property. Prefer full
    // cancellation, otherwise retain the first partial candidate.
    fn select_residual(s:&Symbolic,p:&[Anf],q:&[Anf],fuel:&mut u64)->Option<(u64,bool)>{
        let mut partial=None;
        for d in fiber_candidates(s,true){
            let Some((c,good))=residual_one(s,p,q,d) else{continue;};
            if !c.bounded(){continue;}
            if count(&c,&[good],fuel,true)?==0{continue;}
            if count(&c,&[-good],fuel,true)?==0{return Some((d,true));}
            if partial.is_none(){partial=Some((d,false));}
        }
        partial
    }
    #[test]
    fn hoare_partial_fiber_differential(){
        let gates=[G::H(0),G::H(1),G::CX(0,1),G::CZ(0,1),G::T(0),G::S(1)];
        let preds=[Anf::from([0]),Anf::from([0,1]),Anf::from([0,1,2]),Anf::from([3])];
        let mut cases=0;let mut partial=0;let mut full=0;
        for g in &gates{for h in &gates{
            let ops=[G::H(0),g.clone(),h.clone()];
            let s=native(2,&ops).unwrap();
            for p in &preds{for q in &preds{
                let p=std::slice::from_ref(p);let q=std::slice::from_ref(q);
                let (a,d)=two_copy_conj(&s,p,q);
                let exact=signed(buckets(&a,d,&[],&mut 20_000_000).unwrap());
                for dir in 1..1u64<<s.h{
                    let (r,e)=residual_two(&s,p,q,dir).unwrap();
                    assert_eq!(exact,signed(buckets(&r,e,&[],&mut 20_000_000).unwrap()));
                    // Compare each original basis input separately to
                    // catch accidental cancellation across input labels.
                    for x in 0..4{
                        let prefix=[if x&1!=0{2}else{-2},if x&2!=0{3}else{-3}];
                        assert_eq!(signed(buckets(&a,d,&prefix,&mut 20_000_000).unwrap()),
                            signed(buckets(&r,e,&prefix,&mut 20_000_000).unwrap()));
                    }
                    cases+=1;
                }
                if let Some((dir,all))=select_residual(&s,p,q,&mut 2_000_000){
                    if all{assert_eq!(exact,[0;4]);full+=1;}else{partial+=1;}
                    assert_ne!(dir,0);
                }
            }}
        }}
        assert!(partial+full>0);
        println!("HOARE_PARTIAL_FIBER_DIFFERENTIAL directions={cases} selected_partial={partial} selected_full={full} exact_per_input=true");
        for k in [1usize,2]{
            let (ops,p,_,q)=conditional_post_case(k);
            let s=native(3*k,&ops).unwrap();
            let mut fuel=2_000_000;
            let (dir,all)=select_residual(&s,&p,&q,&mut fuel).expect("partial strict cleanup");
            assert!(!all);
            let (c,d)=two_copy_conj(&s,&p,&q);
            let (r,e)=residual_two(&s,&p,&q,dir).unwrap();
            let mut a=20_000_000;let mut b=a;
            let ca=signed(buckets(&c,d,&[],&mut a).unwrap());
            let cb=signed(buckets(&r,e,&[],&mut b).unwrap());
            assert_eq!(ca,cb);
            assert_eq!(ca,[4i128.pow(k as u32)*(4i128.pow(k as u32)-3i128.pow(k as u32)),0,0,0]);
            assert!(select_residual(&s,&p,&q,&mut 0).is_none());
            println!("HOARE_PARTIAL_FIBER_STRICT k={k} direction={dir} search_visits={} direct_vars={} residual_vars={} direct_clauses={} residual_clauses={} direct_visits={} residual_visits={}",
                2_000_000-fuel,c.vars,r.vars,c.clauses.len(),r.clauses.len(),20_000_000-a,20_000_000-b);
        }
    }
    fn export_partial_fibers(dir:&std::path::Path,manifest:&mut String){
        // Two matched negative cases, four variants only. Existing external
        // regression matrix unchanged; same exact solver and total budget.
        for k in [1usize,2]{
            let n=3*k;
            let (ops,p,_,q)=conditional_post_case(k);
            let s=native(n,&ops).unwrap();
            let t=std::time::Instant::now();
            let (direction,all)=select_residual(&s,&p,&q,&mut 2_000_000).unwrap();
            let prep_us=t.elapsed().as_micros();
            assert!(!all);
            let raw=4i128.pow(k as u32)*(4i128.pow(k as u32)-3i128.pow(k as u32));
            assert_ne!(raw_for_input(n,&ops,&q,1),[0,0]);
            let name=format!("partial-CS{k}-strict");
            for route in ["direct","residual"]{
                let t=std::time::Instant::now();
                let (c,d)=if route=="direct"{two_copy_conj(&s,&p,&q)}
                    else{residual_two(&s,&p,&q,direction).unwrap()};
                let encoding_us=t.elapsed().as_micros();
                let status=if let Some(text)=dimacs(&c,&[]){
                    std::fs::write(dir.join(format!("scale-{name}-{route}.cnf")),text).unwrap();"READY"
                }else{"UNKNOWN_ENCODING_LIMIT"};
                let prep=if route=="direct"{0}else{prep_us};
                manifest.push_str(&format!("{name}\t{route}\t{n}\t{}\t0\t{},{},{}\t{raw},0\t1\t{}\t{}\t{encoding_us}\t{status}\t1\t{prep}\t{}\n",
                    s.h,d[0],d[1],d[2],c.vars,c.clauses.len(),s.phase.len()));
            }
        }
    }


    // R14: bounded memoized survivor DAG. The base predicate is the full
    // fiber (true), since cancellation preserves input and output.
    // Memo keys are (prefix length, XOR shift), not arbitrary assignments.
    // A maximum rank of 3 bounds distinct shifts by eight; at most four
    // directions. This is a bounded optimization, not an unbounded solver.
    fn direction_span(ds:&[u64])->Option<BTreeSet<u64>>{
        if ds.len()>4||ds.iter().any(|&d|d==0){return None;}
        let mut span=BTreeSet::from([0]);
        for &d in ds{
            let next:Vec<_>=span.iter().map(|&v|v^d).collect();
            span.extend(next);
            if span.len()>8{return None;}
        }
        Some(span)
    }
    fn survivor_dag(c:&mut Cnf,s:&Symbolic,bits:&[Lit],ds:&[u64],shift:u64,
                    cache:&mut BTreeMap<(usize,u64),Lit>)->Option<Lit>{
        if ds.is_empty(){return Some(ONE);}
        let key=(ds.len(),shift);
        if let Some(&l)=cache.get(&key){return Some(l);}
        let (&d,prev)=ds.split_last()?;
        let alive=survivor_dag(c,s,bits,prev,shift,cache)?;
        let partner=survivor_dag(c,s,bits,prev,shift^d,cache)?;
        let shifted:Vec<_>=bits.iter().enumerate().map(|(i,&l)|
            if i>=s.n&&shift>>(i-s.n)&1!=0{-l}else{l}).collect();
        let paired=cancel_lit(c,s,&shifted,d)?;
        let remove=c.and(partner,paired);
        let result=c.and(alive,-remove);
        if !c.bounded()||cache.len()>=32{return None;}
        cache.insert(key,result);
        Some(result)
    }
    fn multi_one(s:&Symbolic,p:&[Anf],q:&[Anf],ds:&[u64])->Option<(Cnf,Lit,usize)>{
        direction_span(ds)?;
        if s.n+s.h>63||ds.iter().any(|&d|d>>s.h!=0){return None;}
        let mut c=Cnf::new(s.n+s.h);
        let bits:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        for f in p{let l=c.anf(f,&bits[..s.n]);c.enforce(l);}
        let z:Vec<_>=s.output.iter().map(|o|c.anf(o,&bits)).collect();
        let post=q.iter().fold(ONE,|a,f|{let l=c.anf(f,&z);c.and(a,l)});
        c.enforce(-post);
        let mut cache=BTreeMap::new();
        let l=survivor_dag(&mut c,s,&bits,ds,0,&mut cache)?;
        if !c.bounded(){return None;}
        Some((c,l,cache.len()))
    }
    fn multi_two(s:&Symbolic,p:&[Anf],q:&[Anf],ds:&[u64])->Option<(Cnf,[Lit;3],usize)>{
        direction_span(ds)?;
        if s.n+s.h>63||ds.iter().any(|&d|d>>s.h!=0){return None;}
        let (mut c,delta)=two_copy_conj(s,p,q);
        let left:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        let right:Vec<_>=(0..s.n).map(|i|i as Lit+2)
            .chain((s.n+s.h..s.n+2*s.h).map(|i|i as Lit+2)).collect();
        let mut states=0;
        for bits in [&left,&right]{
            // Literal identities differ between the two path copies.
            let mut cache=BTreeMap::new();
            let l=survivor_dag(&mut c,s,bits,ds,0,&mut cache)?;
            c.enforce(l);states+=cache.len();
        }
        if !c.bounded(){return None;}
        Some((c,delta,states))
    }
    fn small_span_candidates(s:&Symbolic)->Vec<u64>{
        let base=fiber_candidates(s,true);
        // Complete the small span if it has <=64 elements. Otherwise use
        // the existing bounded candidates. This includes joint directions
        // beyond pairwise basis sums for small kernels.
        let mut span=BTreeSet::from([0]);
        for &d in &base{
            let new:Vec<_>=span.iter().map(|&x|x^d).collect();
            span.extend(new);
            if span.len()>64{return base;}
        }
        let mut out:Vec<_>=span.into_iter().filter(|&d|d!=0).collect();
        out.sort_by_key(|&d|(d.count_ones(),d));
        out
    }
    #[derive(Debug)]
    struct MultiChoice{directions:Vec<u64>,full:bool,queries:usize,visits:u64}
    fn choose_multi(s:&Symbolic,p:&[Anf],q:&[Anf],budget:u64)->Option<MultiChoice>{
        let mut fuel=budget;
        let mut ds=Vec::new();
        let mut queries=0;
        let candidates=small_span_candidates(s);
        let (c,l,_)=multi_one(s,p,q,&[])?;
        queries+=1;
        if count(&c,&[l],&mut fuel,true)?==0{
            return Some(MultiChoice{directions:ds,full:true,queries,visits:budget-fuel});
        }
        // At each stage, test whether the new filter actually removes a
        // surviving path. Prefer complete cancellation, else first progress.
        // No full proof after incomplete SAT or a failed candidate.
        for _ in 0..2{
            let mut first=None;
            for &d in &candidates{
                if ds.contains(&d){continue;}
                let mut trial=ds.clone();trial.push(d);
                let Some((mut c,after,_))=multi_one(s,p,q,&trial) else{continue;};
                let bits:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
                let mut cache=BTreeMap::new();
                let Some(before)=survivor_dag(&mut c,s,&bits,&ds,0,&mut cache) else{continue;};
                queries+=1;
                if count(&c,&[before,-after],&mut fuel,true)?==0{continue;}
                queries+=1;
                if count(&c,&[after],&mut fuel,true)?==0{
                    return Some(MultiChoice{directions:trial,full:true,queries,visits:budget-fuel});
                }
                if first.is_none(){first=Some(trial);}
            }
            let Some(next)=first else{break;};
            ds=next;
        }
        if ds.is_empty(){None}else{Some(MultiChoice{directions:ds,full:false,queries,visits:budget-fuel})}
    }
    fn multi_direction_circuit()->Vec<G>{
        // H^3 D H^3 with D phase
        // 3 y0 + 7 y1 + y0 y1 + y0 y2 (mod 8).
        // Scratch is initialized and uncomputed, so D is exact.
        let mut ops=vec![G::H(0),G::H(1),G::H(2)];
        ops.extend((0..3).map(|_|G::T(0)));
        ops.extend((0..7).map(|_|G::T(1)));
        for i in [1,2]{
            ops.extend([G::CCX(0,i,3),G::T(3),G::CCX(0,i,3)]);
        }
        ops.extend([G::H(0),G::H(1),G::H(2)]);
        ops
    }
    #[test]
    fn hoare_multi_fiber_dag(){
        let circuits=[
            vec![G::H(0),G::H(1),G::H(0)],
            vec![G::H(0),G::T(0),G::H(0)],
            vec![G::H(0),G::CZ(0,1),G::H(0)],
            vec![G::H(0),G::H(1),G::H(1)],
        ];
        let preds=[Anf::from([0]),Anf::from([0,1]),Anf::from([0,1,2]),Anf::from([3])];
        let mut cases=0;
        for ops in &circuits{
            let s=native(2,ops).unwrap();
            for p in &preds{for q in &preds{
                let p=std::slice::from_ref(p);let q=std::slice::from_ref(q);
                let (a,d)=two_copy_conj(&s,p,q);
                let exact=signed(buckets(&a,d,&[],&mut 20_000_000).unwrap());
                for first in 1..1u64<<s.h{for second in 1..1u64<<s.h{
                    let (r,e,_)=multi_two(&s,p,q,&[first,second]).unwrap();
                    assert_eq!(exact,signed(buckets(&r,e,&[],&mut 20_000_000).unwrap()));
                    for x in 0..4{
                        let prefix=[if x&1!=0{2}else{-2},if x&2!=0{3}else{-3}];
                        assert_eq!(signed(buckets(&a,d,&prefix,&mut 20_000_000).unwrap()),
                            signed(buckets(&r,e,&prefix,&mut 20_000_000).unwrap()));
                    }
                    cases+=1;
                }}
            }}
        }
        assert_eq!(cases,1856);
        assert!(direction_span(&[1,2,4,8]).is_none());
        let ops=multi_direction_circuit();
        let s=native(4,&ops).unwrap();
        let p:Vec<_>=(0..4).map(|i|bit(i,false)).collect();
        let q=vec![(1..8u64).collect::<Anf>()]; // at least one data bit set
        assert_eq!(raw_for_input(4,&ops,&q,0),[0,0]);
        // Check every possible nonzero direction, not just the heuristic.
        for d in 1..1u64<<s.h{
            let (c,l,_)=multi_one(&s,&p,&q,&[d]).unwrap();
            assert_ne!(count(&c,&[l],&mut 2_000_000,true).unwrap(),0);
        }
        let (c,l,states)=multi_one(&s,&p,&q,&[1,7]).unwrap();
        assert_eq!(count(&c,&[l],&mut 2_000_000,true),Some(0));
        let t=std::time::Instant::now();
        let result=choose_multi(&s,&p,&q,20_000_000).expect("two-direction candidate");
        let elapsed=t.elapsed().as_micros();
        assert!(result.full&&result.directions.len()==2);
        let (r,e,two_states)=multi_two(&s,&p,&q,&result.directions).unwrap();
        assert!(zero(buckets(&r,e,&[],&mut 20_000_000).unwrap()));
        // A mutation changes the zero Fourier coefficient. The solver
        // must not prove it. Check its actual dense norm independently.
        let mut mutant=ops.clone();mutant.insert(mutant.len()-3,G::T(0));
        assert_ne!(raw_for_input(4,&mutant,&q,0),[0,0]);
        let m=native(4,&mutant).unwrap();
        assert!(!choose_multi(&m,&p,&q,20_000_000).is_some_and(|v|v.full));
        assert!(choose_multi(&s,&p,&q,0).is_none());
        println!("HOARE_MULTI_FIBER_DIFFERENTIAL cases={cases} exact_per_input=true");
        println!("HOARE_MULTI_FIBER_WITNESS n=4 h={} explicit_states={states} two_states={two_states} proof_us={elapsed} result={result:?} one_direction_impossible=true",
            s.h);
    }


    // R15: export solver-neutral candidate plans without using DPLL
    // or the expected answer to choose a candidate. The external driver
    // makes all routing decisions from the actual SAT responses.
    // R17: algorithm-level properties, not merely equality to a reference
    // circuit. Each family has an independently specified negative case.
    type AlgorithmCase=(String,usize,Vec<G>,Vec<Anf>,Vec<Anf>,bool);
    fn algorithmic_cases()->Vec<AlgorithmCase>{
        let mut cases=Vec::new();
        for c in scaled_cases().into_iter().filter(|c|c.name=="BV4-correct"||c.name=="BV4-negative"){
            let valid=c.name=="BV4-correct";
            cases.push((c.name,c.n,c.ops,c.p,c.q,valid));
        }
        // Two data qubits, one Grover iteration, unique marked item 11.
        // Oracle CZ; diffusion up to global phase.
        let init2=vec![bit(0,false),bit(1,false)];
        let goal=vec![bit(0,true),bit(1,true)];
        let diffusion=[G::H(0),G::H(1),G::X(0),G::X(1),G::CZ(0,1),
                       G::X(0),G::X(1),G::H(0),G::H(1)];
        for marked in [true,false]{
            let mut ops=vec![G::H(0),G::H(1)];
            if marked{ops.push(G::CZ(0,1));}
            ops.extend(diffusion.iter().cloned());
            cases.push((if marked{"Grover2-marked"}else{"Grover2-no-oracle"}.into(),
                2,ops,init2.clone(),goal.clone(),marked));
        }
        // GHZ+ satisfies X^⊗4=+1. Append H^4 to measure X in the Z basis.
        // Z0 mutation changes that eigenvalue without changing Z correlation.
        let init4=(0..4).map(|i|bit(i,false)).collect::<Vec<_>>();
        let parity=vec![Anf::from([0,1,2,4,8])];
        for positive in [true,false]{
            let mut ops=vec![G::H(0),G::CX(0,1),G::CX(0,2),G::CX(0,3)];
            if !positive{ops.push(G::Z(0));}
            ops.extend((0..4).map(G::H));
            cases.push((if positive{"GHZ4-X-stabilizer"}else{"GHZ4-phase-mutant"}.into(),
                4,ops,init4.clone(),parity.clone(),positive));
        }
        // Reversible half adder: input (a,b,0), output (a,s=a xor b,c=ab).
        // c=a*(1 xor s), equivalently c xor a xor a*s=0.
        for correct in [true,false]{
            let mut ops=vec![];
            if correct{ops.push(G::CCX(0,1,2));}
            ops.push(G::CX(0,1));
            cases.push((if correct{"HalfAdder-arithmetic"}else{"HalfAdder-no-carry"}.into(),
                3,ops,vec![bit(2,false)],vec![Anf::from([0,1,3,4])],correct));
        }
        cases
    }
    #[test]
    fn hoare_algorithmic_property_intent(){
        let cases=algorithmic_cases();
        assert_eq!(cases.len(),8);
        for (name,n,ops,p,q,valid) in cases{
            assert!(admitted(n,&ops));
            let legal:Vec<_>=(0..1u64<<n).filter(|&x|eval_conj(&p,x)).collect();
            assert!(!legal.is_empty());
            let witnesses:Vec<_>=legal.iter().copied().filter(|&x|raw_for_input(n,&ops,&q,x)!=[0,0]).collect();
            assert_eq!(witnesses.is_empty(),valid,"independent property intent {name}");
            if name=="Grover2-no-oracle"{
                // Uniform state: 3 of 4 bad basis outcomes, raw scale 2^6.
                assert_eq!(raw_for_input(n,&ops,&q,0),[48,0]);
            }
            if name=="GHZ4-phase-mutant"{
                // Odd X parity with probability 1, raw scale 2^5.
                assert_eq!(raw_for_input(n,&ops,&q,0),[32,0]);
            }
            if name=="HalfAdder-no-carry"{assert_eq!(witnesses,vec![3]);}
            println!("HOARE_ALGORITHM_PROPERTY name={name} n={n} legal={} violations={} expected_valid={valid}",legal.len(),witnesses.len());
        }
    }

    fn export_hybrid(dir:&std::path::Path){
        let mut cases:Vec<(String,usize,Vec<G>,Vec<Anf>,Vec<Anf>)>=Vec::new();
        cases.push(("GHZ3".into(),3,vec![G::H(0),G::CX(0,1),G::CX(0,2)],
            (0..3).map(|i|bit(i,false)).collect(),vec![equal_bits(0,1),equal_bits(0,2)]));
        cases.push(("HH".into(),1,vec![G::H(0),G::H(0)],vec![bit(0,false)],vec![bit(0,false)]));
        for k in [1usize,2]{
            let (ops,p,q,strict)=conditional_post_case(k);
            if k==2{cases.push(("CS2-strict".into(),3*k,ops.clone(),p.clone(),strict));}
            cases.push((format!("CS{k}-conditional"),3*k,ops,p,q));
        }
        let ops=multi_direction_circuit();
        let p:Vec<_>=(0..4).map(|i|bit(i,false)).collect();
        let q=vec![(1..8u64).collect::<Anf>()];
        cases.push(("joint-two-stage".into(),4,ops.clone(),p.clone(),q.clone()));
        let mut mutant=ops;mutant.insert(mutant.len()-3,G::T(0));
        cases.push(("joint-mutant".into(),4,mutant,p,q));
        let c=scaled_cases().into_iter().find(|c|c.name=="HTH-product4").unwrap();
        cases.push(("HTH4".into(),c.n,c.ops,c.p,c.q));
        cases.extend(algorithmic_cases().into_iter().map(|(name,n,ops,p,q,_)|(name,n,ops,p,q)));
        assert_eq!(cases.len(),16);
        let mut manifest=String::new();let mut plans=String::new();let mut symbolic=String::new();let mut rr_manifest=String::new();let mut residual_manifest=String::new();
        for (name,n,ops,p,q) in cases{
            // Independent small gate oracle: never supplied to dispatcher
            // until its verdict and witness have been produced.
            export_external_property(dir,&name,n,&ops,&p,&q);
            let mut raw=[0i128;2];let mut witnesses=Vec::new();
            for x in (0..1u64<<n).filter(|&x|eval_conj(&p,x)){
                let v=raw_for_input(n,&ops,&q,x);
                raw[0]+=v[0];raw[1]+=v[1];
                if v!=[0,0]{witnesses.push(x.to_string());}
            }
            let witness=if witnesses.is_empty(){"-".to_owned()}else{witnesses.join(",")};
            let input=HoareInput::build(n,&ops,p.clone(),q.clone()).unwrap();
            emit_residual_plans(dir,&name,&input,raw,&witness,&mut residual_manifest,false);
            let t=std::time::Instant::now();
            let s=native(n,&ops).unwrap();
            let build_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (c,d)=two_copy_conj(&s,&p,&q);
            std::fs::write(dir.join(format!("hybrid-{name}-wmc.cnf")),dimacs(&c,&[]).unwrap()).unwrap();
            let direct_us=t.elapsed().as_micros();
            // Matched standard native RR baseline. Charge separate source
            // construction, reduction and CNF serialization to this route.
            let t=std::time::Instant::now();
            let rr=reduced_native(n,&ops).and_then(|(r,stats)|{
                let (c,d)=two_copy_conj(&r,&p,&q);
                let cnf=dimacs(&c,&[])?;
                Some((r.h,stats.scale2,c.vars,c.clauses.len(),d,cnf))
            });
            if let Some((h,scale,vars,clauses,d,cnf))=rr{
                std::fs::write(dir.join(format!("hybrid-{name}-rr.cnf")),cnf).unwrap();
                rr_manifest.push_str(&format!("{name}\tREADY\t{h}\t{scale}\t{},{},{}\t{vars}\t{clauses}\t{}\n",
                    d[0],d[1],d[2],t.elapsed().as_micros()));
            }else{
                rr_manifest.push_str(&format!("{name}\tUNKNOWN_RESOURCE\t0\t0\t-\t0\t0\t{}\n",t.elapsed().as_micros()));
            }
            let t=std::time::Instant::now();
            let anf_text=|fs:&[Anf]|fs.iter().map(|f|if f.is_empty(){"-".to_owned()}else{
                f.iter().map(|m|m.to_string()).collect::<Vec<_>>().join(",")
            }).collect::<Vec<_>>().join(";");
            let phase=s.phase.iter().map(|(m,k)|format!("{m}:{k}")).collect::<Vec<_>>().join(",");
            symbolic.push_str(&format!("{name}\t{n}\t{}\t{}\t{phase}\t{}\t{}\n",
                s.h,anf_text(&s.output),anf_text(&p),anf_text(&q)));
            let candidates=small_span_candidates(&s);
            for (j,f) in q.iter().enumerate(){
                let (base,bits,z)=fiber_guard(&s,&p,f);
                let mut emit=|kind:&str,ds:&str,c:&Cnf,units:&[Lit]|{
                    if let Some(text)=dimacs(c,units){
                        let file=format!("hybrid-{name}-{j}-{kind}-{ds}.cnf");
                        std::fs::write(dir.join(&file),text).unwrap();
                        plans.push_str(&format!("{name}\t{j}\t{kind}\t{ds}\t{file}\n"));
                    }
                };
                emit("guard","0",&base,&[]);
                for &d in candidates.iter().take(8){
                    if let Some(c)=fiber_bad(&base,&bits,&z,&s,d){emit("single",&d.to_string(),&c,&[]);}
                }
                // Bounded precompiled candidates, no oracle-guided order.
                // Include at most 16 ordered pairs for each conjunct.
                let mut pairs=0;
                'outer:for &d in candidates.iter().take(8){
                    for &e in candidates.iter().take(8){
                        if d==e{continue;}
                        if pairs>=16{break 'outer;}
                        pairs+=1;
                        if let Some((c,l,_))=multi_one(&s,&p,std::slice::from_ref(f),&[d,e]){
                            emit("multi",&format!("{d}-{e}"),&c,&[l]);
                        }
                    }
                }
            }
            let plan_us=t.elapsed().as_micros();
            manifest.push_str(&format!("{name}\t{n}\t{}\t{},{},{}\t{},{}\t{witness}\t{build_us}\t{direct_us}\t{plan_us}\n",
                q.len(),d[0],d[1],d[2],raw[0],raw[1]));
        }
        std::fs::write(dir.join("hybrid.tsv"),manifest).unwrap();
        std::fs::write(dir.join("residual.tsv"),residual_manifest).unwrap();
        std::fs::write(dir.join("hybrid-plan.tsv"),plans).unwrap();
        std::fs::write(dir.join("hybrid-symbolic.tsv"),symbolic).unwrap();
        std::fs::write(dir.join("hybrid-rr.tsv"),rr_manifest).unwrap();
        println!("HOARE_HYBRID_FIXTURES cases=16 external_plan_only=true standard_rr=true");
    }


    // Three-mode research contract. The initial native PathSum is shared
    // and never auto-reduced; each route receives the same original spec.
    // This bounded reference uses exact bucket #SAT (not external WMC).
    // Advanced property RR / SAT discovery are deliberately not enabled yet.
    #[derive(Clone,Copy,Debug,PartialEq,Eq)]
    enum HoareMode { RrStandard, Wmc, HybridStandard }
    #[derive(Debug,PartialEq,Eq)]
    enum HoareStop { AlgebraicZero, AlgebraicWitness, RrInconclusive,
        ExactCount, CountLimit, ReductionLimit }
    struct HoareInput { ps:PathSum, initial:Symbolic, pre:Vec<Anf>, post:Vec<Anf> }
    impl HoareInput {
        fn build(n:usize,ops:&[G],pre:Vec<Anf>,post:Vec<Anf>)->Option<Self>{
            if !admitted(n,ops){return None;}
            Self::build_scoped(n,ops,pre,post)
        }
        fn build_scale(n:usize,ops:&[G],pre:Vec<Anf>,post:Vec<Anf>)->Option<Self>{
            let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
            if !admitted(n,&[])||h>48||n+h>63||ops.len()>512||!ops.iter().all(|g|admitted(n,std::slice::from_ref(g))){return None;}
            Self::build_scoped(n,ops,pre,post)
        }
        fn build_scoped(n:usize,ops:&[G],pre:Vec<Anf>,post:Vec<Anf>)->Option<Self>{
            if pre.iter().chain(&post).flatten().any(|&m|m>>n!=0)
                ||pre.iter().chain(&post).map(|f|f.len()).sum::<usize>()>128{return None;}
            let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
            for g in ops{g.apply(&mut ps,false);}
            let initial=compact(&ps,n)?;
            if initial.h!=ops.iter().filter(|g|matches!(g,G::H(_))).count()
                ||initial.output.iter().map(|f|f.len()).sum::<usize>()+initial.phase.len()>256{return None;}
            Some(Self{ps,initial,pre,post})
        }
    }
    #[derive(Debug)]
    struct HoareDecision {
        mode:HoareMode, answer:Answer, stop:HoareStop,
        rr_calls:usize, rr_stats:Option<RrStats>,
        count_batches:usize, count_visits:u64, witness_batches:usize,
        initial_h:usize, residual_h:usize, scale2:u32,
        coefficients:Option<[i128;2]>,
    }
    // Canonical Boolean guard, not a SAT or counting query.
    // Use only a bounded ANF composition; overflow is inconclusive.
    fn algebraic_terminal(s:&Symbolic,p:&[Anf],q:&[Anf])->Option<(Answer,HoareStop)>{
        let mut a=Anf::from([0]);
        for f in p{a=mul_anf(&a,f)?;}
        let mut b=Anf::from([0]);
        for f in q{b=mul_anf(&b,&compose_anf(f,&s.output)?)?;}
        xor_insert(&mut b,0);
        let bad=mul_anf(&a,&b)?;
        if bad.is_empty(){return Some((Answer::Proved,HoareStop::AlgebraicZero));}
        if s.h==0{
            // A minimum-degree monomial supplies an algebraic witness:
            // it is the only monomial contained in that assignment.
            // No enumeration, SAT, or coefficient counting is needed.
            let x=*bad.iter().min_by_key(|&&m|(m.count_ones(),m))?;
            if eval(&bad,x)&&eval_conj(p,x)&&!eval_conj(q,path(s,x,0).0){
                return Some((Answer::Refuted(x),HoareStop::AlgebraicWitness));
            }
        }
        None
    }
    fn exact_pair_coeff(c:&Cnf,d:[Lit;3],prefix:&[Lit],fuel:&mut u64,
                        batches:&mut usize)->Option<[i128;2]>{
        *batches+=1;
        let ns=buckets(c,d,prefix,fuel)?;
        if ns.iter().any(|&v|v>i64::MAX as u128)
            ||(0..8).any(|i|ns[i]!=ns[(8-i)%8]){return None;}
        let a=ns[0] as i128-ns[4] as i128;
        let b=ns[1] as i128-ns[3] as i128;
        // Exact sign of a+b*sqrt(2), with checked bounded integer squares.
        let negative=if a<0&&b<=0{true}else if a<=0&&b<0{true}
            else if a<0&&b>0{a*a>2*b*b}
            else if a>0&&b<0{a*a<2*b*b}else{false};
        if negative{return None;}
        Some([a,b])
    }
    fn count_reference(s:&Symbolic,p:&[Anf],q:&[Anf],scale:u32,
                       budget:u64,r:&mut HoareDecision){
        let (c,d)=two_copy_conj(s,p,q);
        let mut fuel=budget;
        let root=exact_pair_coeff(&c,d,&[],&mut fuel,&mut r.count_batches);
        if let Some(coeff)=root{
            if let Some(factor)=1i128.checked_shl(scale){
                if let (Some(a),Some(b))=(coeff[0].checked_mul(factor),coeff[1].checked_mul(factor)){
                    r.coefficients=Some([a,b]);
                    if coeff==[0,0]{
                        r.answer=Answer::Proved;r.stop=HoareStop::ExactCount;
                    }else{
                        let mut prefix=Vec::new();let mut x=0u64;
                        let mut ok=true;
                        for i in 0..s.n{
                            let l=i as Lit+2;prefix.push(-l);
                            match exact_pair_coeff(&c,d,&prefix,&mut fuel,&mut r.witness_batches){
                                Some([0,0])=>{*prefix.last_mut().unwrap()=l;x|=1u64<<i;},
                                Some(_)=>{},
                                None=>{ok=false;break;}
                            }
                        }
                        if ok&&eval_conj(p,x)&&exact_pair_coeff(&c,d,&prefix,&mut fuel,&mut r.witness_batches)
                            .is_some_and(|v|v!=[0,0]){
                            r.answer=Answer::Refuted(x);r.stop=HoareStop::ExactCount;
                        }
                    }
                }
            }
        }
        r.count_visits=budget-fuel;
    }
    fn run_hoare_mode(input:&HoareInput,mode:HoareMode,budget:u64)->HoareDecision{
        let h=input.initial.h;
        let mut r=HoareDecision{mode,answer:Answer::Unknown,stop:HoareStop::CountLimit,
            rr_calls:0,rr_stats:None,count_batches:0,count_visits:0,witness_batches:0,
            initial_h:h,residual_h:h,scale2:0,coefficients:None};
        if mode==HoareMode::Wmc{
            // No RR, guard fast path, or SAT-only calls.
            count_reference(&input.initial,&input.pre,&input.post,0,budget,&mut r);
            return r;
        }
        r.rr_calls+=1;
        let Some((residual,stats))=reduce_existing(input.ps.clone(),input.initial.n) else{
            r.stop=HoareStop::ReductionLimit;return r;
        };
        r.residual_h=residual.h;r.scale2=stats.scale2;r.rr_stats=Some(stats);
        if let Some((answer,stop))=algebraic_terminal(&residual,&input.pre,&input.post){
            r.answer=answer;r.stop=stop;return r;
        }
        if mode==HoareMode::RrStandard{
            r.stop=HoareStop::RrInconclusive;return r;
        }
        // Same counting implementation, actual RR residual only.
        count_reference(&residual,&input.pre,&input.post,r.scale2,budget,&mut r);
        r
    }
    #[test]
    fn hoare_three_mode_reference_contract(){
        let z=vec![bit(0,false)];let all=vec![];let impossible=vec![Anf::new()];
        let cases=vec![
            ("HH",1,vec![G::H(0),G::H(0)],z.clone(),z.clone()),
            ("X",1,vec![G::X(0)],z.clone(),z.clone()),
            ("H",1,vec![G::H(0)],z.clone(),z.clone()),
            ("HTH",1,vec![G::H(0),G::T(0),G::H(0)],z.clone(),z.clone()),
            ("HHH",1,vec![G::H(0),G::H(0),G::H(0)],z.clone(),z.clone()),
            ("empty-pre",1,vec![G::H(0)],impossible,z.clone()),
            ("all-post",1,vec![G::H(0)],all.clone(),all.clone()),
            ("free-cx",2,vec![G::CX(0,1)],vec![bit(1,false)],vec![bit(1,false)]),
            ("bell",2,vec![G::H(0),G::CX(0,1)],vec![bit(0,false),bit(1,false)],vec![equal_bits(0,1)]),
        ];
        let mut rr_decided=0;let mut hybrid_count=0;let mut reduced_count=0;
        for (name,n,ops,p,q) in cases{
            let input=HoareInput::build(n,&ops,p,q).unwrap();
            let mut expected=[0i128;2];
            for x in (0..1u64<<n).filter(|&x|eval_conj(&input.pre,x)){
                let a=raw_for_input(n,&ops,&input.post,x);
                expected[0]+=a[0];expected[1]+=a[1];
            }
            for mode in [HoareMode::RrStandard,HoareMode::Wmc,HoareMode::HybridStandard]{
                let r=run_hoare_mode(&input,mode,5_000_000);
                assert_eq!(r.mode,mode);
                assert_eq!(r.initial_h,input.initial.h);
                match r.answer{
                    Answer::Proved=>assert_eq!(expected,[0,0],"{name} {mode:?}"),
                    Answer::Refuted(x)=>{assert!(eval_conj(&input.pre,x));assert_ne!(raw_for_input(n,&ops,&input.post,x),[0,0]);},
                    Answer::Unknown=>assert_eq!(mode,HoareMode::RrStandard,"{name} {r:?}"),
                }
                if let Some(v)=r.coefficients{assert_eq!(v,expected,"{name} {mode:?}");}
                match mode{
                    HoareMode::RrStandard=>{
                        assert_eq!((r.rr_calls,r.count_batches,r.witness_batches),(1,0,0));
                        if r.answer!=Answer::Unknown{rr_decided+=1;}
                    },
                    HoareMode::Wmc=>{
                        assert_eq!((r.rr_calls,r.residual_h,r.scale2),(0,r.initial_h,0));
                        assert_eq!(r.count_batches,1);
                        assert_eq!(r.coefficients,Some(expected));
                    },
                    HoareMode::HybridStandard=>{
                        assert_eq!(r.rr_calls,1);
                        if r.count_batches>0{
                            hybrid_count+=1;
                            assert_eq!(r.coefficients,Some(expected));
                            if r.residual_h<r.initial_h{reduced_count+=1;}
                        }else{assert_eq!(r.witness_batches,0);}
                    },
                }
                println!("HOARE_THREE_MODE case={name} {r:?}");
            }
            // The initial representation must not be mutated by either route.
            assert_eq!(input.initial.h,compact(&input.ps,n).unwrap().h);
        }
        assert!(rr_decided>0&&rr_decided<9&&hybrid_count>0&&reduced_count>0);
        let input=HoareInput::build(1,&[G::H(0),G::T(0),G::H(0)],z.clone(),z).unwrap();
        for mode in [HoareMode::Wmc,HoareMode::HybridStandard]{
            let r=run_hoare_mode(&input,mode,0);
            assert_eq!(r.answer,Answer::Unknown);assert_eq!(r.stop,HoareStop::CountLimit);
        }
        assert!(HoareInput::build(1,&[],vec![Anf::from([2])],vec![]).is_none());
        println!("HOARE_THREE_MODE_SUMMARY cases=9 variants=27 rr_decided={rr_decided} hybrid_count={hybrid_count} reduced_count={reduced_count} reference_bucket_backend=true");
    }


    // Independent pure reduction ablation. No calls to two-copy counting,
    // WMC, dense-state enumeration, or exact_pair_coeff in these routes.
    #[derive(Clone,Copy,Debug,PartialEq,Eq)]
    enum PureRrMode { Standard, Property, Sat }
    #[derive(Debug)]
    struct PureRrReport {
        mode:PureRrMode, answer:Answer, reason:&'static str,
        standard_runs:usize, monomial_runs:usize, algebraic_trials:usize,
        algebraic_hits:usize, sat_queries:usize, sat_visits:u64,
        directions:Vec<u64>, residual_h:usize,
    }
    fn anf_xor(a:&Anf,b:&Anf)->Option<Anf>{
        let out=a.symmetric_difference(b).copied().collect::<Anf>();
        (out.len()<=256).then_some(out)
    }
    fn anf_not(a:&Anf)->Option<Anf>{anf_xor(a,&Anf::from([0]))}
    fn anf_shift(a:&Anf,flip:u64)->Option<Anf>{
        let mut out=Anf::new();let mut work=0u64;
        for &m in a{
            let v=m&flip;work=work.checked_add(1u64<<v.count_ones())?;
            if work>4096{return None;}
            let mut t=v;
            loop{xor_insert(&mut out,(m&!flip)|t);if t==0{break;}t=(t-1)&v;}
            if out.len()>256{return None;}
        }
        Some(out)
    }
    // Convert a Z8 polynomial into its three Boolean bit ANFs with exact
    // ripple carry. Every product and sum is bounded; no truth table.
    fn phase_bits(p:&BTreeMap<u64,u8>)->Option<[Anf;3]>{
        let mut bits:[Anf;3]=std::array::from_fn(|_|Anf::new());
        for (&m,&k) in p{
            let mut carry=Anf::new();
            for i in 0..3{
                let term=if k>>i&1!=0{Anf::from([m])}else{Anf::new()};
                let x=anf_xor(&bits[i],&term)?;
                let next=if i<2{
                    anf_xor(&mul_anf(&bits[i],&term)?,&mul_anf(&carry,&x)?)?
                }else{Anf::new()};
                bits[i]=anf_xor(&x,&carry)?;carry=next;
            }
        }
        Some(bits)
    }
    fn property_guard(s:&Symbolic,p:&[Anf],q:&[Anf])->Option<Anf>{
        let mut pre=Anf::from([0]);let mut post=Anf::from([0]);
        for f in p{pre=mul_anf(&pre,f)?;}
        for f in q{post=mul_anf(&post,&compose_anf(f,&s.output)?)?;}
        mul_anf(&pre,&anf_not(&post)?)
    }
    // Remove only currently surviving opposite-phase partners with the
    // same complete output. The unchanged input is not part of the shift.
    fn algebraic_delete(s:&Symbolic,g:&Anf,d:u64)->Option<Anf>{
        if d==0||d>>s.h!=0||s.n+s.h>63{return None;}
        let flip=d<<s.n;
        let mut paired=anf_shift(g,flip)?;
        for o in &s.output{
            let diff=anf_xor(o,&anf_shift(o,flip)?)?;
            paired=mul_anf(&paired,&anf_not(&diff)?)?;
        }
        let gap=translation_gap(&s.phase,flip,true)?;
        for b in phase_bits(&gap)?{paired=mul_anf(&paired,&anf_not(&b)?)?;}
        mul_anf(g,&anf_not(&paired)?)
    }
    fn algebraic_injective_paths(s:&Symbolic)->bool{
        // Sufficient condition: output is affine in y with constant
        // path coefficients, and that linear map has trivial kernel.
        let imask=(1u64<<s.n)-1;let mut rows=Vec::new();
        for o in &s.output{
            let mut row=0u64;
            for &m in o{
                if m&!imask==0{continue;}
                if m.count_ones()!=1{return false;}
                row^=m>>s.n;
            }
            rows.push((row,false));
        }
        affine_solve(rows,s.h).is_some_and(|(_,basis)|basis.is_empty())
    }
    fn residual_guard(s:&Symbolic,p:&[Anf],q:&[Anf],r:&mut PureRrReport)->Option<Anf>{
        let mut g=property_guard(s,p,q)?;
        // Bounded, deterministic algebraic sequence, not exhaustive search.
        // Continue from current survivor, never union stale masks.
        for d in small_span_candidates(s).into_iter().take(24){
            if g.is_empty(){break;}
            r.algebraic_trials+=1;
            let Some(next)=algebraic_delete(s,&g,d) else{continue;};
            if next!=g{r.algebraic_hits+=1;r.directions.push(d);g=next;}
        }
        Some(g)
    }
    fn property_rr(s:&Symbolic,p:&[Anf],q:&[Anf],r:&mut PureRrReport)->Answer{
        let Some(g)=residual_guard(s,p,q,r) else{return Answer::Unknown;};
        guard_terminal(s,p,q,&g,r)
    }
    fn guard_terminal(s:&Symbolic,p:&[Anf],q:&[Anf],g:&Anf,r:&mut PureRrReport)->Answer{
        if g.is_empty(){r.reason="algebraic-survivor-zero";return Answer::Proved;}
        if algebraic_injective_paths(s){
            let a=*g.iter().min_by_key(|&&m|(m.count_ones(),m)).unwrap();
            let x=a&((1u64<<s.n)-1);let y=a>>s.n;
            if eval(&g,a)&&eval_conj(p,x)&&!eval_conj(q,path(s,x,y).0){
                r.reason="injective-path-witness";return Answer::Refuted(x);
            }
        }
        Answer::Unknown
    }
    fn sat_rr(s:&Symbolic,p:&[Anf],q:&[Anf],budget:u64,r:&mut PureRrReport)->Answer{
        // Bounded one-copy SAT-only reference (same DPLL engine, sat_only=true).
        // Each post conjunct is a union of entire fibers. No counting and
        // no interpretation of a surviving path as a quantum counterexample.
        let mut fuel=budget;
        let ds:Vec<_>=small_span_candidates(s).into_iter().take(8).collect();
        let mut proved=true;
        'clauses:for post in q{
            let mut plans=vec![vec![]];
            for &d in &ds{plans.push(vec![d]);}
            let mut pairs=0;
            'pairs:for &d in &ds{for &e in &ds{
                if d==e{continue;}
                if pairs>=16{break 'pairs;}
                pairs+=1;plans.push(vec![d,e]);
            }}
            for plan in plans{
                if fuel==0{proved=false;break 'clauses;}
                let Some((c,l,_))=multi_one(s,p,std::slice::from_ref(post),&plan) else{continue;};
                r.sat_queries+=1;
                match count(&c,&[l],&mut fuel,true){
                    Some(0)=>{r.directions.extend(plan);continue 'clauses;},
                    Some(_)=>{},
                    None=>{proved=false;break 'clauses;},
                }
            }
            proved=false;break;
        }
        r.sat_visits=budget-fuel;
        if proved{r.reason="sat-survivor-unsat";Answer::Proved}
        else{r.reason=if fuel==0{"sat-budget"}else{"sat-inconclusive"};Answer::Unknown}
    }
    fn run_pure_rr(input:&HoareInput,mode:PureRrMode,budget:u64)->PureRrReport{
        let mut r=PureRrReport{mode,answer:Answer::Unknown,reason:"reduction-limit",
            standard_runs:1,monomial_runs:0,algebraic_trials:0,algebraic_hits:0,
            sat_queries:0,sat_visits:0,directions:vec![],residual_h:input.initial.h};
        let Some((s,_))=reduce_existing(input.ps.clone(),input.initial.n) else{return r;};
        r.residual_h=s.h;r.reason="rr-inconclusive";
        if let Some((a,stop))=algebraic_terminal(&s,&input.pre,&input.post){
            r.answer=a;r.reason=if stop==HoareStop::AlgebraicZero{"standard-zero"}else{"standard-witness"};return r;
        }
        if mode==PureRrMode::Standard{return r;}
        // Try existing precondition-relative monomial substitution, then
        // ordinary input-preserving RR. Retain the original guard/labels.
        r.monomial_runs+=1;
        let mut selected=s;
        if let Some(ps)=mono_substitute(input.ps.clone(),input.initial.n,&input.pre){
            r.standard_runs+=1;
            if let Some((special,_))=reduce_existing(ps,input.initial.n){
                if let Some((a,stop))=algebraic_terminal(&special,&input.pre,&input.post){
                    r.answer=a;r.residual_h=special.h;
                    r.reason=if stop==HoareStop::AlgebraicZero{"precondition-zero"}else{"precondition-witness"};
                    return r;
                }
                if special.h<=selected.h{selected=special;}
            }
        }
        r.residual_h=selected.h;
        r.answer=property_rr(&selected,&input.pre,&input.post,&mut r);
        if r.answer==Answer::Unknown&&mode==PureRrMode::Sat{
            r.answer=sat_rr(&selected,&input.pre,&input.post,budget,&mut r);
        }
        r
    }
    #[test]
    fn hoare_pure_rr_matched_corpus(){
        let mut cases:Vec<AlgorithmCase>=algorithmic_cases();
        cases.push(("GHZ3".into(),3,vec![G::H(0),G::CX(0,1),G::CX(0,2)],
            (0..3).map(|i|bit(i,false)).collect(),vec![equal_bits(0,1),equal_bits(0,2)],true));
        cases.push(("HH".into(),1,vec![G::H(0),G::H(0)],vec![bit(0,false)],vec![bit(0,false)],true));
        for k in [1usize,2]{
            let (ops,p,q,strict)=conditional_post_case(k);
            if k==2{cases.push(("CS2-strict".into(),3*k,ops.clone(),p.clone(),strict,false));}
            cases.push((format!("CS{k}-conditional"),3*k,ops,p,q,true));
        }
        let ops=multi_direction_circuit();
        let p:Vec<_>=(0..4).map(|i|bit(i,false)).collect();
        let q=vec![(1..8u64).collect::<Anf>()];
        cases.push(("joint-two-stage".into(),4,ops.clone(),p.clone(),q.clone(),true));
        let mut mutant=ops;mutant.insert(mutant.len()-3,G::T(0));
        cases.push(("joint-mutant".into(),4,mutant,p,q,false));
        let c=scaled_cases().into_iter().find(|c|c.name=="HTH-product4").unwrap();
        cases.push(("HTH4".into(),c.n,c.ops,c.p,c.q,false));
        assert_eq!(cases.len(),16);
        let mut definite=[0usize;3];let mut proofs=[0usize;3];let mut refutes=[0usize;3];
        for (name,n,ops,p,q,valid) in cases{
            let input=HoareInput::build(n,&ops,p,q).expect("common initial IR");
            let expected=(0..1u64<<n).filter(|&x|eval_conj(&input.pre,x))
                .all(|x|raw_for_input(n,&ops,&input.post,x)==[0,0]);
            assert_eq!(valid,expected,"property intent {name}");
            for (i,mode) in [PureRrMode::Standard,PureRrMode::Property,PureRrMode::Sat].into_iter().enumerate(){
                let t=std::time::Instant::now();
                let r=run_pure_rr(&input,mode,200_000);
                let elapsed=t.elapsed().as_micros();
                assert_eq!(r.mode,mode);
                if mode!=PureRrMode::Sat{assert_eq!((r.sat_queries,r.sat_visits),(0,0));}
                match r.answer{
                    Answer::Proved=>{assert!(valid,"{name} {r:?}");proofs[i]+=1;definite[i]+=1;},
                    Answer::Refuted(x)=>{assert!(!valid&&eval_conj(&input.pre,x));
                        assert_ne!(raw_for_input(n,&ops,&input.post,x),[0,0]);refutes[i]+=1;definite[i]+=1;},
                    Answer::Unknown=>{},
                }
                println!("HOARE_PURE_RR case={name} elapsed_us={elapsed} {r:?}");
            }
        }
        assert!(definite[0]<=definite[1]&&definite[1]<=definite[2]);
        println!("HOARE_PURE_RR_SUMMARY cases=16 variants=48 definite={definite:?} proved={proofs:?} refuted={refutes:?} wmc_calls=0 sat_backend=bounded_reference");
    }
    #[test]
    fn hoare_algebraic_survivor_differential(){
        // Independent finite model checks of one/two successive deletions.
        // The oracle is test-only, outside the reduction entry.
        let circuits=[vec![G::H(0),G::H(1),G::H(0)],
            vec![G::H(0),G::T(0),G::H(0)],vec![G::H(0),G::CZ(0,1),G::H(0)]];
        let preds=[Anf::from([0]),Anf::from([0,1]),Anf::from([0,1,2]),Anf::from([3])];
        let mut cases=0;
        for ops in circuits{
            let s=native(2,&ops).unwrap();
            for p in &preds{for q in &preds{
                let guard=property_guard(&s,std::slice::from_ref(p),std::slice::from_ref(q)).unwrap();
                for d in 1..1u64<<s.h{
                    let next=algebraic_delete(&s,&guard,d).unwrap();
                    for e in 1..1u64<<s.h{
                        let last=algebraic_delete(&s,&next,e).unwrap();
                        for x in 0..4{
                            let mut original=BTreeMap::<u64,Root>::new();
                            let mut residual=BTreeMap::<u64,Root>::new();
                            for y in 0..1u64<<s.h{
                                let a=x|(y<<s.n);let (z,k)=path(&s,x,y);
                                let (w,l)=path(&s,x,y^d);
                                let active=eval(p,x)&&!eval(q,z);
                                assert_eq!(eval(&guard,a),active);
                                let remove=active&&eval(&guard,x|((y^d)<<s.n))&&z==w&&(l+8-k)%8==4;
                                assert_eq!(eval(&next,a),active&&!remove);
                                let (w,l)=path(&s,x,y^e);
                                let remove2=eval(&next,a)&&eval(&next,x|((y^e)<<s.n))&&z==w&&(l+8-k)%8==4;
                                assert_eq!(eval(&last,a),eval(&next,a)&&!remove2);
                                if active{let v=original.entry(z).or_default();*v=add(*v,root(k));}
                                if eval(&last,a){let v=residual.entry(z).or_default();*v=add(*v,root(k));}
                            }
                            for z in 0..4{assert_eq!(original.get(&z).copied().unwrap_or_default(),
                                residual.get(&z).copied().unwrap_or_default());}
                        }
                        cases+=1;
                    }
                }
            }}
        }
        assert_eq!(cases,1072);
        // Zero SAT budget must not convert an inconclusive property to proof.
        let input=HoareInput::build(1,&[G::H(0),G::T(0),G::H(0)],vec![bit(0,false)],vec![bit(0,false)]).unwrap();
        let r=run_pure_rr(&input,PureRrMode::Sat,0);
        assert_ne!(r.answer,Answer::Proved);
        assert_eq!(r.sat_queries,0);
        println!("HOARE_ALGEBRAIC_SURVIVOR cases={cases} exact_per_input=true");
    }


    // Rare violations with an analytic exact coefficient and a unique
    // legal input. No reduction or SAT shortcut in the exported CNF.
    // For U=(HTH)^tensor k and B=not(all output bits one),
    // leakage=((2-sqrt(2))/4)^k on |0...0>.
    fn rare_wmc_cases()->Vec<ScaleCase>{
        let mut cases=Vec::new();
        for k in [1usize,4,8,12,16]{
            let mut ops=Vec::new();
            for i in 0..k{ops.extend([G::H(i),G::T(i),G::H(i)]);}
            let p:Vec<_>=(0..k).map(|i|bit(i,false)).collect();
            let (mut a,mut b)=(1i128,0i128);
            for _ in 0..k{(a,b)=(2*a-2*b,2*b-a);}
            let q=vec![Anf::from([0,(1u64<<k)-1])];
            cases.push(ScaleCase{name:format!("rare-HTH{k}"),n:k,ops:ops.clone(),
                p:p.clone(),q,expected:[a,b],known_witness:Some(0)});
            // Positive control: identical circuit and precondition,
            // universal postcondition. Still use the original CNF.
            cases.push(ScaleCase{name:format!("rare-HTH{k}-safe"),n:k,ops,
                p,q:vec![],expected:[0,0],known_witness:None});
        }
        cases
    }
    #[test]
    fn hoare_pure_wmc_rare_intent(){
        for c in rare_wmc_cases().into_iter().filter(|c|c.n<=8){
            assert_eq!(raw_for_input(c.n,&c.ops,&c.q,0),c.expected);
        }
    }
    fn export_rare_wmc(dir:&std::path::Path){
        let mut manifest=String::new();
        for c in rare_wmc_cases(){
            // Explicitly bounded research-scale admission, not production.
            export_external_property(dir,&c.name,c.n,&c.ops,&c.p,&c.q);
            let h=2*c.n;
            assert!(c.n<=16&&h<=32&&c.n+h<=63);
            let t=std::time::Instant::now();
            let s=native(c.n,&c.ops).expect("rare unreduced native IR");
            assert_eq!(s.h,h);
            let build_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (cnf,d)=two_copy_conj(&s,&c.p,&c.q);
            let status=if let Some(file)=dimacs(&cnf,&[]){
                std::fs::write(dir.join(format!("pure-{}.cnf",c.name)),file).unwrap();
                "READY"
            }else{"UNKNOWN_ENCODING_LIMIT"};
            let encoding_us=t.elapsed().as_micros();
            let witness=c.known_witness.map(|x|x.to_string()).unwrap_or("-".to_owned());
            manifest.push_str(&format!("{}\t{}\t{h}\t{},{},{}\t{},{}\t{witness}\t{build_us}\t{encoding_us}\t{status}\n",
                c.name,c.n,d[0],d[1],d[2],c.expected[0],c.expected[1]));
        }
        std::fs::write(dir.join("pure-rare.tsv"),manifest).unwrap();
        println!("HOARE_PURE_WMC_RARE_FIXTURES cases=10");
    }


    // Export the original gate list and independent ANF predicates, not a
    // QuPRS-reduced path sum or an equivalent-circuit surrogate.
    fn export_external_property(dir:&std::path::Path,name:&str,n:usize,ops:&[G],p:&[Anf],q:&[Anf]){
        let anf=|fs:&[Anf]|fs.iter().map(|f|if f.is_empty(){"-".to_owned()}else{
            f.iter().map(|m|m.to_string()).collect::<Vec<_>>().join(",")
        }).collect::<Vec<_>>().join(";");
        let mut s=format!("{n}\t{}\t{}\n",anf(p),anf(q));
        for g in ops{
            let line=match *g{
                G::H(i)=>format!("h {i}"),G::X(i)=>format!("x {i}"),
                G::Z(i)=>format!("z {i}"),G::S(i)=>format!("s {i}"),
                G::T(i)=>format!("t {i}"),G::CX(i,j)=>format!("cx {i} {j}"),
                G::CZ(i,j)=>format!("cz {i} {j}"),G::CCX(i,j,k)=>format!("ccx {i} {j} {k}"),
                _=>panic!("unsupported external property gate"),
            };
            s.push_str(&line);s.push('\n');
        }
        std::fs::write(dir.join(format!("quokka-{name}.tsv")),s).unwrap();
    }


    // R24: preserve the *actual* current survivor on both path copies.
    // No OR over old masks, no original-IR fallback. Keep shared input x.
    fn guarded_pair(s:&Symbolic,g:&Anf)->(Cnf,[Lit;3]){
        let mut c=Cnf::new(s.n+2*s.h);
        let l:Vec<_>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        let r:Vec<_>=(0..s.n).map(|i|i as Lit+2)
            .chain((s.n+s.h..s.n+2*s.h).map(|i|i as Lit+2)).collect();
        let a=c.anf(g,&l);c.enforce(a);
        let b=c.anf(g,&r);c.enforce(b);
        for o in &s.output{
            let a=c.anf(o,&l);let b=c.anf(o,&r);
            let d=c.xor(a,b);c.enforce(-d);
        }
        let a=c.phase(s,&l,false);let b=c.phase(s,&r,true);
        let delta=c.add3(a,b);
        (c,delta)
    }
    struct ResidualPlan{
        answer:Answer,s:Symbolic,scale:u32,g:Option<Anf>,
        hits:usize,trials:usize,reason:&'static str,directions:Vec<u64>,
    }
    fn hybrid_plan(input:&HoareInput,property:bool)->Option<ResidualPlan>{
        let n=input.initial.n;
        let (mut s,mut stats)=reduce_existing(input.ps.clone(),n)?;
        let mut answer=Answer::Unknown;let mut reason="standard-residual";
        if let Some((a,_))=algebraic_terminal(&s,&input.pre,&input.post){
            answer=a;reason="standard-terminal";
        }
        if property&&answer==Answer::Unknown{
            if let Some(ps)=mono_substitute(input.ps.clone(),n,&input.pre){
                if let Some((special,ss))=reduce_existing(ps,n){
                    if let Some((a,_))=algebraic_terminal(&special,&input.pre,&input.post){
                        return Some(ResidualPlan{answer:a,s:special,scale:ss.scale2,g:None,
                            hits:0,trials:0,reason:"precondition-terminal",directions:vec![]});
                    }
                    if special.h<=s.h{s=special;stats=ss;}
                }
            }
            let mut r=PureRrReport{mode:PureRrMode::Property,answer:Answer::Unknown,
                reason:"property-residual",standard_runs:0,monomial_runs:0,
                algebraic_trials:0,algebraic_hits:0,sat_queries:0,sat_visits:0,
                directions:vec![],residual_h:s.h};
            // If bounded ANF construction fails, keep the selected native
            // RR residual with the original predicates, not the original IR.
            let g=residual_guard(&s,&input.pre,&input.post,&mut r);
            if let Some(ref guard)=g{
                answer=guard_terminal(&s,&input.pre,&input.post,guard,&mut r);
            }
            return Some(ResidualPlan{answer,s,scale:stats.scale2,g,
                hits:r.algebraic_hits,trials:r.algebraic_trials,reason:r.reason,directions:r.directions});
        }
        Some(ResidualPlan{answer,s,scale:stats.scale2,g:None,hits:0,trials:0,reason,directions:vec![]})
    }
    fn residual_pair(input:&HoareInput,plan:&ResidualPlan)->(Cnf,[Lit;3]){
        if let Some(ref g)=plan.g{guarded_pair(&plan.s,g)}
        else{two_copy_conj(&plan.s,&input.pre,&input.post)}
    }

    // Bounded representation selection on the selected native RR
    // checkpoint. Every prefix of the cancellation sequence is sound.
    // No rerun on the unreduced input; rejection is explicit telemetry.
    fn adaptive_pair(input:&HoareInput,plan:&ResidualPlan)->(Cnf,[Lit;3],usize,&'static str){
        let (base,delta)=two_copy_conj(&plan.s,&input.pre,&input.post);
        if plan.directions.is_empty(){return (base,delta,0,"native-no-hit");}
        // Pilot structural budget, not a claimed runtime predictor.
        // Keep the DPLL/encoder admission cap; do not enlarge it to hide
        // the explosion. Prefer more retained steps within 2x each dimension.
        let admissible=|c:&Cnf|c.bounded()&&
            (!base.bounded()||(c.vars<=base.vars.saturating_mul(2)&&
                c.clauses.len()<=base.clauses.len().saturating_mul(2)));
        let score=|c:&Cnf|c.vars.saturating_add(c.clauses.len());
        let mut best:Option<(Cnf,[Lit;3],usize,&'static str)>=None;
        let mut consider=|c:Cnf,d:[Lit;3],k:usize,repr:&'static str|{
            if admissible(&c)&&best.as_ref().is_none_or(|(old,_,ok,_)|
                k>*ok||(k==*ok&&score(&c)<score(old))){
                best=Some((c,d,k,repr));
            }
        };
        if let Some(ref g)=plan.g{
            let (c,d)=guarded_pair(&plan.s,g);
            consider(c,d,plan.directions.len(),"anf-full");
        }
        // DAG avoids materializing the expanded Boolean polynomial.
        // Reuse native original predicates on the selected symbolic
        // checkpoint. Cancellation pairs preserve the complete output,
        // hence the forbidden guard is constant on every removed pair.
        for k in 1..=plan.directions.len().min(4){
            if let Some((c,d,_))=multi_two(&plan.s,&input.pre,&input.post,&plan.directions[..k]){
                consider(c,d,k,"dag-prefix");
            }
        }
        best.unwrap_or((base,delta,0,"native-reject-growth"))
    }

    #[test]
    fn hoare_adaptive_pair_exact(){
        let circuits=[
            vec![G::H(0),G::CZ(0,1),G::H(0)],
            vec![G::H(0),G::T(0),G::H(0),G::H(1)],
            vec![G::H(0),G::H(1),G::H(0)],
        ];
        let mut checks=0;
        for ops in circuits{
            let input=HoareInput::build(2,&ops,vec![bit(0,false)],vec![bit(0,false)]).unwrap();
            let plan=hybrid_plan(&input,true).unwrap();
            let (c,d,kept,_)=adaptive_pair(&input,&plan);
            assert!(kept<=plan.hits);
            assert!(c.bounded());
            for x in 0..4u64{
                let prefix:Vec<_>=(0..2).map(|i|if x>>i&1!=0{i as Lit+2}else{-(i as Lit+2)}).collect();
                let v=exact_pair_coeff(&c,d,&prefix,&mut 20_000_000,&mut 0).unwrap();
                let expected=if eval_conj(&input.pre,x){raw_for_input(2,&ops,&input.post,x)}else{[0,0]};
                assert_eq!(v.map(|a|a*(1i128<<plan.scale)),expected);
                checks+=1;
            }
            // Independent comparison of expanded guard and DAG for
            // a real single-direction cancellation, on every legal x.
            let s=&input.initial;
            let g=property_guard(s,&input.pre,&input.post).unwrap();
            for dir in 1..1u64<<s.h{
                let Some(ng)=algebraic_delete(s,&g,dir) else{continue;};
                let Some((dag,dd,_))=multi_two(s,&input.pre,&input.post,&[dir]) else{continue;};
                let (anf,ad)=guarded_pair(s,&ng);
                if !anf.bounded(){continue;}
                for x in 0..4u64{
                    let prefix:Vec<_>=(0..2).map(|i|if x>>i&1!=0{i as Lit+2}else{-(i as Lit+2)}).collect();
                    let a=exact_pair_coeff(&anf,ad,&prefix,&mut 20_000_000,&mut 0).unwrap();
                    let b=exact_pair_coeff(&dag,dd,&prefix,&mut 20_000_000,&mut 0).unwrap();
                    assert_eq!(a,b);checks+=1;
                }
            }
        }
        println!("HOARE_ADAPTIVE_PAIR checks={checks} exact_per_input=true");
    }


    type HybridPair=(Cnf,[Lit;3],usize,&'static str);
    // SAT proof on the same native checkpoint; then optional incremental
    // partial cancellation on the exact ordered prefix retained by adaptive.
    // SAT means a path exists, not that its quantum amplitude is nonzero.
    fn sat_assisted_pair(input:&HoareInput,plan:&ResidualPlan,pair:HybridPair,
                         proof_budget:u64,partial_budget:u64)
        ->(Option<HybridPair>,usize,u64,usize,&'static str){
        let mut report=PureRrReport{mode:PureRrMode::Sat,answer:Answer::Unknown,
            reason:"sat-inconclusive",standard_runs:0,monomial_runs:0,
            algebraic_trials:0,algebraic_hits:0,sat_queries:0,sat_visits:0,
            directions:vec![],residual_h:plan.s.h};
        let answer=if proof_budget==0{Answer::Unknown}else{sat_rr(&plan.s,&input.pre,&input.post,proof_budget,&mut report)};
        let mut queries=report.sat_queries;
        let proof_visits=report.sat_visits;
        if answer==Answer::Proved{
            return (None,queries,proof_visits,0,"sat-full-proof");
        }
        let kept=pair.2;
        if kept>=4||kept>plan.directions.len()||partial_budget==0{
            return (Some(pair),queries,proof_visits,0,"sat-keep-adaptive");
        }
        let prefix=&plan.directions[..kept];
        let (base,_)=two_copy_conj(&plan.s,&input.pre,&input.post);
        let allowed=|c:&Cnf|c.bounded()&&
            (!base.bounded()||(c.vars<=base.vars.saturating_mul(2)&&
                c.clauses.len()<=base.clauses.len().saturating_mul(2)));
        let mut fuel=partial_budget;
        let mut best:Option<HybridPair>=None;
        for d in small_span_candidates(&plan.s).into_iter().take(8){
            if fuel==0{break;}
            if prefix.contains(&d){continue;}
            let mut trial=prefix.to_vec();trial.push(d);
            let Some((mut c,after,_))=multi_one(&plan.s,&input.pre,&input.post,&trial) else{continue;};
            queries+=1;
            match count(&c,&[after],&mut fuel,true){
                Some(0)=>return (None,queries,proof_visits+partial_budget-fuel,0,"sat-prefix-proof"),
                Some(_)=>{},
                None=>break,
            }
            let Some((next,delta,_))=multi_two(&plan.s,&input.pre,&input.post,&trial) else{continue;};
            if !allowed(&next){continue;}
            let bits:Vec<_>=(0..plan.s.n+plan.s.h).map(|i|i as Lit+2).collect();
            let mut cache=BTreeMap::new();
            let Some(before)=survivor_dag(&mut c,&plan.s,&bits,prefix,0,&mut cache) else{continue;};
            queries+=1;
            match count(&c,&[before,-after],&mut fuel,true){
                Some(v) if v>0=>{
                    if best.as_ref().is_none_or(|(old,_,_,_)|
                        next.vars+next.clauses.len()<old.vars+old.clauses.len()){
                        best=Some((next,delta,kept+1,"sat-dag-extension"));
                    }
                },
                Some(_)=>{},
                None=>break,
            }
        }
        let visits=proof_visits+partial_budget-fuel;
        match best{
            Some(next)=>(Some(next),queries,visits,1,"sat-partial-retained"),
            None=>(Some(pair),queries,visits,0,"sat-keep-adaptive"),
        }
    }

    #[test]
    fn hoare_sat_assisted_residual_exact(){
        let cases=[
            (2,vec![G::H(0),G::CZ(0,1),G::H(0)],vec![bit(0,false)],vec![bit(0,false)]),
            (2,vec![G::H(0),G::T(0),G::H(0),G::H(1)],vec![bit(0,false)],vec![bit(0,false)]),
            (4,multi_direction_circuit(),(0..4).map(|i|bit(i,false)).collect(),vec![(1..8u64).collect::<Anf>()]),
        ];
        let mut checks=0;
        for (n,ops,p,q) in cases{
            let input=HoareInput::build(n,&ops,p,q).unwrap();
            let plan=hybrid_plan(&input,true).unwrap();
            for (pb,eb) in [(0,0),(200_000,50_000)]{
                let pair=adaptive_pair(&input,&plan);
                let kept=pair.2;
                let (result,queries,visits,added,_)=sat_assisted_pair(&input,&plan,pair,pb,eb);
                assert!(visits<=pb+eb&&added<=1);
                if pb+eb==0{assert_eq!(queries,0);assert_eq!(result.as_ref().map(|x|x.2),Some(kept));}
                for x in 0..1u64<<n{
                    let expected=if eval_conj(&input.pre,x){raw_for_input(n,&ops,&input.post,x)}else{[0,0]};
                    if let Some((ref c,d,k,_))=result{
                        assert!(k>=kept);
                        let prefix:Vec<_>=(0..n).map(|i|if x>>i&1!=0{i as Lit+2}else{-(i as Lit+2)}).collect();
                        // The larger fixture is only tested on the known
                        // legal input when counting would otherwise exceed
                        // the independent small DPLL budget.
                        if n>2&&!eval_conj(&input.pre,x){continue;}
                        if n<=2{
                            let v=exact_pair_coeff(c,d,&prefix,&mut 20_000_000,&mut 0).unwrap();
                            assert_eq!(v.map(|a|a*(1i128<<plan.scale)),expected);
                        }else{continue;}
                    }else{assert_eq!(expected,[0,0]);}
                    checks+=1;
                }
            }
        }
        println!("HOARE_SAT_ASSISTED_PAIR checks={checks} exact_per_input=true");
    }

    fn emit_residual_plans(dir:&std::path::Path,name:&str,input:&HoareInput,
                           raw:[i128;2],witnesses:&str,manifest:&mut String,scale_export:bool){
        for (mode,property) in [("standard",false),("property",true),("adaptive",true),("sat-assisted",true)]{
            let t=std::time::Instant::now();
            let plan=hybrid_plan(input,property);
            let prep_us=t.elapsed().as_micros();
            let mut h=input.initial.h;let mut scale=0;let mut hits=0;let mut trials=0;
            let mut guard_terms=0;let mut variables=0;let mut clauses=0;
            let mut delta="-".to_owned();let mut witness="-".to_owned();
            let mut encoding_us=0;let mut reason="reduction-limit";
            let mut retained=0;let mut representation="none";
            let mut sat_queries=0;let mut sat_visits=0;let mut sat_us=0;let mut sat_added=0;let mut sat_reason="not-run";
            let mut status="UNKNOWN_REDUCTION_LIMIT";
            if let Some(plan)=plan{
                h=plan.s.h;scale=plan.scale;hits=plan.hits;trials=plan.trials;
                guard_terms=plan.g.as_ref().map_or(0,|g|g.len());reason=plan.reason;
                match plan.answer{
                    Answer::Proved=>status="PROVED",
                    Answer::Refuted(x)=>{status="REFUTED";witness=x.to_string();},
                    Answer::Unknown=>{
                        let start=std::time::Instant::now();
                        let pair=if mode=="adaptive"||mode=="sat-assisted"{adaptive_pair(input,&plan)}else{
                            let (c,d)=residual_pair(input,&plan);
                            (c,d,plan.hits,if plan.g.is_some(){"anf"}else{"native"})
                        };
                        let result=if mode=="sat-assisted"{
                            let st=std::time::Instant::now();
                            let (r,q,v,a,sr)=sat_assisted_pair(input,&plan,pair,200_000,50_000);
                            sat_us=st.elapsed().as_micros();sat_queries=q;sat_visits=v;sat_added=a;sat_reason=sr;
                            r
                        }else{Some(pair)};
                        if let Some((c,d,kept,repr))=result{
                            retained=kept;representation=repr;
                            variables=c.vars;clauses=c.clauses.len();
                            delta=format!("{},{},{}",d[0],d[1],d[2]);
                            status="UNKNOWN_ENCODING_LIMIT";
                            if let Some(text)=if scale_export{serialize_external(&c,&[])}else{dimacs(&c,&[])}{
                                std::fs::write(dir.join(format!("residual-{name}-{mode}.cnf")),text).unwrap();
                                status="READY";
                            }
                        }else{status="PROVED";reason="sat-proof";representation="sat-proof";}
                        encoding_us=start.elapsed().as_micros().saturating_sub(sat_us);
                    }
                }
            }
            manifest.push_str(&format!("{name}\t{mode}\t{}\t{}\t{h}\t{scale}\t{hits}\t{trials}\t{guard_terms}\t{variables}\t{clauses}\t{delta}\t{status}\t{witness}\t{prep_us}\t{encoding_us}\t{reason}\t{},{}\t{witnesses}\t{retained}\t{representation}\t{sat_queries}\t{sat_visits}\t{sat_us}\t{sat_added}\t{sat_reason}\n",
                input.initial.n,input.initial.h,raw[0],raw[1]));
        }
    }
    #[test]
    fn hoare_guarded_residual_pair_exact(){
        // Verify the two-copy guard really constrains both y and y', not
        // just one. Use independent exact dense gate oracle on each x.
        let cases=[
            (2,vec![G::H(0),G::CZ(0,1),G::H(0)],vec![bit(0,false)],vec![bit(0,false)]),
            (2,vec![G::H(0),G::T(0),G::H(0),G::H(1)],vec![bit(0,false)],vec![bit(0,false)]),
            (2,vec![G::H(0),G::H(0),G::H(1)],vec![bit(0,false)],vec![bit(1,false)]),
        ];
        let mut checks=0;
        for (n,ops,p,q) in cases{
            let input=HoareInput::build(n,&ops,p,q).unwrap();
            for property in [false,true]{
                let plan=hybrid_plan(&input,property).unwrap();
                let (c,d)=residual_pair(&input,&plan);
                for x in 0..1u64<<n{
                    let prefix:Vec<_>=(0..n).map(|i|if x>>i&1!=0{i as Lit+2}else{-(i as Lit+2)}).collect();
                    let mut batches=0;
                    let coeff=exact_pair_coeff(&c,d,&prefix,&mut 20_000_000,&mut batches).unwrap();
                    let expected=if eval_conj(&input.pre,x){raw_for_input(n,&ops,&input.post,x)}else{[0,0]};
                    assert_eq!(coeff.map(|v|v*(1i128<<plan.scale)),expected);
                    checks+=1;
                }
            }
            // Directly exercise partial cancellation on the original guard,
            // independent of the planner's early terminal decisions.
            let s=&input.initial;
            let g=property_guard(s,&input.pre,&input.post).unwrap();
            for dir in 1..1u64<<s.h{
                let Some(g)=algebraic_delete(s,&g,dir) else{continue;};
                let (c,d)=guarded_pair(s,&g);
                for x in 0..1u64<<n{
                    let prefix:Vec<_>=(0..n).map(|i|if x>>i&1!=0{i as Lit+2}else{-(i as Lit+2)}).collect();
                    let coeff=exact_pair_coeff(&c,d,&prefix,&mut 20_000_000,&mut 0).unwrap();
                    let expected=if eval_conj(&input.pre,x){raw_for_input(n,&ops,&input.post,x)}else{[0,0]};
                    assert_eq!(coeff,expected);checks+=1;
                }
            }
        }
        println!("HOARE_GUARDED_PAIR checks={checks} exact_per_input=true");
    }


    // Predeclared scale ladder. Exact dense Z8 gate oracle uses a unique
    // legal input and no PathSum or WMC. Do not select by observed speed.
    fn scale_mixing(n:usize,layers:usize)->Vec<G>{
        let mut ops=Vec::new();
        for layer in 0..layers{
            ops.extend((0..n).map(G::H));
            if layer+1==layers{break;}
            for i in 0..n{
                ops.push(G::T(i));
                if (i+layer)%3==0{ops.push(G::S(i));}
            }
            let mut edges=BTreeSet::new();
            for i in 0..n{
                for j in [(i+1)%n,(i+2+layer)%n,(i+n/2)%n]{
                    if i!=j{edges.insert((i.min(j),i.max(j)));}
                }
            }
            ops.extend(edges.into_iter().map(|(i,j)|G::CZ(i,j)));
        }
        ops
    }
    fn scale_inverse(ops:&[G])->Vec<G>{
        let mut out=Vec::new();
        for g in ops.iter().rev(){
            match *g{
                G::T(i)=>out.extend((0..7).map(|_|G::T(i))),
                G::S(i)=>out.extend((0..3).map(|_|G::S(i))),
                _=>out.push(g.clone()),
            }
        }
        out
    }

    // Backward support of a diagonal output projector. The whole
    // diagonal block commutes, so support must not grow transitively
    // inside a block merely because of the gate serialization order.
    fn gate_support(g:&G)->Option<u64>{
        Some(match *g{
            G::H(i)|G::X(i)|G::Z(i)|G::S(i)|G::T(i)=>1u64<<i,
            G::CX(i,j)|G::CZ(i,j)=>(1u64<<i)|(1u64<<j),
            G::CCX(i,j,k)=>(1u64<<i)|(1u64<<j)|(1u64<<k),
            _=>return None,
        })
    }
    fn property_cone(n:usize,ops:&[G],q:&[Anf])->Option<Vec<G>>{
        if n==0||n>16||q.iter().flatten().any(|&m|m>>n!=0)
            ||!ops.iter().all(|g|admitted(n,std::slice::from_ref(g))){return None;}
        let mut support=q.iter().flatten().fold(0u64,|a,&m|a|m);
        let mut out=Vec::new();
        let mut i=ops.len();
        while i>0{
            if diagonal(&ops[i-1]){
                let entry=support;
                let mut expanded=entry;
                while i>0&&diagonal(&ops[i-1]){
                    i-=1;
                    let mask=gate_support(&ops[i])?;
                    if mask&entry!=0{out.push(ops[i].clone());expanded|=mask;}
                }
                support=expanded;
            }else{
                i-=1;
                let mask=gate_support(&ops[i])?;
                if mask&support!=0{out.push(ops[i].clone());support|=mask;}
            }
        }
        out.reverse();Some(out)
    }
    #[test]
    fn hoare_property_cone_exact(){
        let mut checks=0;
        let posts=[vec![],vec![Anf::new()],vec![bit(0,false)],vec![bit(2,true)],
            vec![equal_bits(0,2)],vec![Anf::from([0,3])],vec![bit(0,false),bit(1,true)]];
        let circuits=[
            vec![G::H(0),G::H(1),G::H(2),G::CZ(0,1),G::CZ(1,2),G::T(1),G::H(0)],
            vec![G::H(0),G::T(2),G::CCX(0,1,2),G::CX(2,0),G::H(1),G::S(2)],
            scale_mixing(3,3),
            vec![G::X(2),G::H(1),G::CZ(1,2),G::S(0),G::H(2),G::H(0)],
        ];
        for ops in circuits{
            let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
            for q in &posts{
                let cone=property_cone(3,&ops,q).unwrap();
                let hc=cone.iter().filter(|g|matches!(g,G::H(_))).count();
                for x in 0..8{
                    assert_eq!(raw_for_input(3,&cone,q,x).map(|v|v*(1i128<<(h-hc))),
                               raw_for_input(3,&ops,q,x));
                    checks+=1;
                }
            }
        }
        // Do not introduce dependence on a spectator via transitive CZ
        // closure: CZ(1,2) commutes with the whole diagonal block.
        let ops=vec![G::H(0),G::H(1),G::H(2),G::CZ(1,2),G::CZ(0,1),G::H(0)];
        let cone=property_cone(3,&ops,&[bit(0,false)]).unwrap();
        assert!(!cone.contains(&G::CZ(1,2))&&!cone.contains(&G::H(2)));
        println!("HOARE_PROPERTY_CONE checks={checks} exact_per_input=true");
    }

    // Exact bijective quotient of the two-copy Boolean domain. Restricted
    // to constant/single-variable output ANFs and cube preconditions.
    // Each shared output identifies the two path slots, never projects
    // away an unconstrained summation variable. No multiplicity factor.
    fn literal_output(f:&Anf)->Option<(Option<usize>,bool)>{
        let nonconstant:Vec<_>=f.iter().copied().filter(|&m|m!=0).collect();
        let neg=f.contains(&0);
        match nonconstant.as_slice(){
            []=>Some((None,neg)),
            [m] if m.count_ones()==1=>Some((Some(m.trailing_zeros() as usize),neg)),
            _=>None,
        }
    }
    fn quotient_pair(s:&Symbolic,p:&[Anf],q:&[Anf])->Option<(Cnf,[Lit;3],usize,usize)>{
        let mut fixed=BTreeMap::<usize,bool>::new();
        for f in p{
            let (i,neg)=literal_output(f)?;
            if let Some(i)=i{
                if i>=s.n{return None;}
                let v=!neg;
                if fixed.insert(i,v).is_some_and(|old|old!=v){return None;}
            }else if !neg{return None;}
        }
        let mut shared=BTreeSet::new();
        for o in &s.output{
            if let Some(i)=literal_output(o)?.0{
                if i>=s.n+s.h{return None;}
                shared.insert(i);
            }
        }
        // Single literal post: violation fixes its output variable, before
        // either phase is compiled. All other predicates remain explicit.
        if q.len()==1{
            if let Some((Some(i),neg))=literal_output(&q[0]){
                if i>=s.n{return None;}
                if let (Some(j),out_neg)=literal_output(&s.output[i])?{
                    let v=neg^out_neg;
                    if fixed.insert(j,v).is_some_and(|old|old!=v){
                        let mut c=Cnf::new(0);c.enforce(ZERO);
                        return Some((c,[ZERO;3],0,0));
                    }
                }
            }
        }
        let mut c=Cnf::new(0);
        let mut left=Vec::new();let mut right=Vec::new();
        for i in 0..s.n+s.h{
            let l=match fixed.get(&i){Some(true)=>ONE,Some(false)=>ZERO,None=>c.fresh()};
            let r=if i<s.n||shared.contains(&i){l}else{c.fresh()};
            left.push(l);right.push(r);
        }
        let primary=c.vars-1;
        let z:Vec<_>=s.output.iter().map(|o|c.anf(o,&left)).collect();
        let post=q.iter().fold(ONE,|acc,f|{let v=c.anf(f,&z);c.and(acc,v)});
        c.enforce(-post);
        // Combine both phase polynomials after alias/fixed-bit substitution.
        // Keys are sorted variable IDs, not masks, to admit >64 pair slots.
        let mut phase=BTreeMap::<Vec<Lit>,u8>::new();
        for (bits,negative) in [(&left,false),(&right,true)]{
            for (&m,&k) in &s.phase{
                let mut key=Vec::new();let mut zero=false;
                for (i,&l) in bits.iter().enumerate(){
                    if m>>i&1==0{continue;}
                    if l==ZERO{zero=true;break;}
                    if l!=ONE{key.push(l);}
                }
                if zero{continue;}
                key.sort_unstable();key.dedup();
                let v=(phase.get(&key).copied().unwrap_or(0)+if negative{(8-k)%8}else{k})%8;
                if v==0{phase.remove(&key);}else{phase.insert(key,v);}
            }
        }
        let terms=phase.len();
        let mut delta=[ZERO;3];
        for (key,k) in phase{
            let m=key.into_iter().fold(ONE,|a,b|c.and(a,b));
            let term=std::array::from_fn(|i|if k>>i&1!=0{m}else{ZERO});
            delta=c.add3(delta,term);
        }
        Some((c,delta,primary,terms))
    }
    #[test]
    fn hoare_quotient_pair_exact(){
        let cases=[
            vec![G::H(0),G::T(0),G::H(0),G::H(1)],
            vec![G::H(0),G::CZ(0,1),G::H(0)],
            vec![G::H(0),G::X(0),G::H(1),G::CZ(0,1)],
            vec![G::H(0),G::H(1),G::CZ(0,1),G::H(0),G::H(1)],
        ];
        let posts=[vec![],vec![Anf::new()],vec![bit(0,false)],vec![bit(1,true)],
            vec![equal_bits(0,1)],vec![Anf::from([3])],vec![bit(0,false),bit(1,false)]];
        let mut checks=0;
        for ops in cases{
            let s=native(2,&ops).unwrap();
            for q in &posts{
                for x in 0..4{
                    let p:Vec<_>=(0..2).map(|i|bit(i,x>>i&1!=0)).collect();
                    let (c,d,_,_)=quotient_pair(&s,&p,q).unwrap();
                    let v=exact_pair_coeff(&c,d,&[],&mut 20_000_000,&mut 0).unwrap();
                    assert_eq!(v,raw_for_input(2,&ops,q,x));checks+=1;
                }
                // Non-fixed original inputs remain shared and counted once.
                let (c,d,_,_)=quotient_pair(&s,&[],q).unwrap();
                let mut expected=[0i128;2];
                for x in 0..4{let v=raw_for_input(2,&ops,q,x);expected[0]+=v[0];expected[1]+=v[1];}
                assert_eq!(exact_pair_coeff(&c,d,&[],&mut 20_000_000,&mut 0).unwrap(),expected);
                checks+=1;
            }
        }
        let s=native(2,&[G::CX(0,1)]).unwrap();
        assert!(quotient_pair(&s,&[],&[bit(1,false)]).is_none());
        println!("HOARE_QUOTIENT_PAIR checks={checks} exact=true");
    }


    type AffForm=(u128,bool);
    fn linear_form(f:&Anf,n:usize)->Option<AffForm>{
        let mut mask=0u128;
        for &m in f{
            if m==0{continue;}
            if m.count_ones()!=1||m.trailing_zeros() as usize>=n{return None;}
            mask|=m as u128;
        }
        Some((mask,f.contains(&0)))
    }
    // RREF over original paired slots (x,y,y'). A free coordinate
    // describes exactly one satisfying assignment, never a projection.
    fn pair_rref(mut rows:Vec<AffForm>,width:usize)->Option<Vec<AffForm>>{
        assert!(width<128);
        let mut pivots=Vec::new();
        // Prefer eliminating right-copy slots before left and input.
        for j in (0..width).rev(){
            let bit=1u128<<j;
            let i=pivots.len();
            if let Some(k)=(i..rows.len()).find(|&k|rows[k].0&bit!=0){
                rows.swap(i,k);let row=rows[i];
                for (l,r) in rows.iter_mut().enumerate(){
                    if l!=i&&r.0&bit!=0{r.0^=row.0;r.1^=row.1;}
                }
                pivots.push(j);
            }
        }
        if rows.iter().any(|&(m,b)|m==0&&b){return None;}
        let mut forms=vec![(0,false);width];
        let mut k=0;
        for j in 0..width{
            if !pivots.contains(&j){forms[j]=(1u128<<k,false);k+=1;}
        }
        for (i,&j) in pivots.iter().enumerate(){
            let (m,b)=rows[i];
            forms[j]=(0,b);
            for t in 0..width{
                if t!=j&&m>>t&1!=0{forms[j].0^=forms[t].0;}
            }
        }
        Some(forms)
    }
    fn form_compose(mask:u128,constant:bool,forms:&[AffForm])->AffForm{
        forms.iter().enumerate().filter(|(i,_)|mask>>i&1!=0)
            .fold((0,constant),|(a,b),(_,f)|(a^f.0,b^f.1))
    }
    fn form_lit(c:&mut Cnf,cache:&mut BTreeMap<AffForm,Lit>,f:AffForm)->Lit{
        if let Some(&l)=cache.get(&f){return l;}
        let mut l=if f.1{ONE}else{ZERO};
        for i in 0..128{
            if f.0>>i&1!=0{l=c.xor(l,i as Lit+2);}
        }
        cache.insert(f,l);l
    }
    type PhaseProducts=BTreeMap<Vec<AffForm>,u8>;
    struct AffPair{cnf:Cnf,delta:[Lit;3],inputs:Vec<Lit>,primary:usize,terms:usize,phase:Option<PhaseProducts>,unsat:bool,input_forms:Vec<AffForm>}
    fn affine_quotient_pair(s:&Symbolic,p:&[Anf],q:&[Anf])->Option<AffPair>{
        affine_quotient_pair_prefix(s,p,q,&[])
    }
    fn affine_quotient_pair_prefix(s:&Symbolic,p:&[Anf],q:&[Anf],prefix:&[Anf])->Option<AffPair>{
        let width=s.n+2*s.h;
        if width>=128{return None;}
        let input_mask=(1u128<<s.n)-1;
        let right_mask=|m:u128|(m&input_mask)|((m&!input_mask)<<s.h);
        let mut rows=Vec::new();
        for f in p{let (m,b)=linear_form(f,s.n)?;rows.push((m,!b));}
        let outputs:Vec<_>=s.output.iter().map(|f|linear_form(f,s.n+s.h)).collect::<Option<_>>()?;
        for &(m,_) in &outputs{rows.push((m^right_mask(m),false));}
        for f in prefix{
            let (m,b)=linear_form(f,s.n)?;
            let (mask,c)=form_compose(m,b,&outputs);
            rows.push((mask,!c));
        }
        // A single affine postcondition can be absorbed as one affine
        // violation equation. Nonlinear or conjunction posts stay in CNF.
        if q.len()==1{
            if let Some((m,b))=linear_form(&q[0],s.n){
                let (mask,c)=form_compose(m,b,&outputs);
                rows.push((mask,c));
            }
        }
        let Some(forms)=pair_rref(rows,width) else{
            let mut cnf=Cnf::new(0);cnf.enforce(ZERO);
            return Some(AffPair{cnf,delta:[ZERO;3],inputs:vec![ZERO;s.n],primary:0,terms:0,phase:None,unsat:true,input_forms:vec![]});
        };
        let primary=forms.iter().fold(0u128,|a,f|a|f.0).count_ones() as usize;
        let mut cnf=Cnf::new(primary);
        let mut cache=BTreeMap::new();
        let inputs=forms[..s.n].iter().map(|&f|form_lit(&mut cnf,&mut cache,f)).collect();
        let output_forms:Vec<_>=outputs.iter().map(|&(m,b)|form_compose(m,b,&forms)).collect();
        let z:Vec<_>=output_forms.iter().map(|&f|form_lit(&mut cnf,&mut cache,f)).collect();
        let post=q.iter().fold(ONE,|acc,f|{let v=cnf.anf(f,&z);cnf.and(acc,v)});
        cnf.enforce(-post);
        // Canonical products of affine Boolean forms. Products with
        // complementary factors vanish; identical factors are idempotent.
        // No potentially exponential ANF expansion is necessary.
        let mut phase=BTreeMap::<Vec<AffForm>,u8>::new();
        for negative in [false,true]{
            for (&m,&k) in &s.phase{
                let mask=if negative{right_mask(m as u128)}else{m as u128};
                let mut key=Vec::new();let mut zero=false;
                for (i,&f) in forms.iter().enumerate(){
                    if mask>>i&1==0{continue;}
                    if f==(0,false){zero=true;break;}
                    if f!=(0,true){
                        if key.contains(&(f.0,!f.1)){zero=true;break;}
                        key.push(f);
                    }
                }
                if zero{continue;}
                key.sort_unstable();key.dedup();
                let v=(phase.get(&key).copied().unwrap_or(0)+if negative{(8-k)%8}else{k})%8;
                if v==0{phase.remove(&key);}else{phase.insert(key,v);}
            }
        }
        let terms=phase.len();
        let mut delta=[ZERO;3];
        for (key,&k) in &phase{
            let mut m=ONE;
            for &f in key{let l=form_lit(&mut cnf,&mut cache,f);m=cnf.and(m,l);}
            let term=std::array::from_fn(|i|if k>>i&1!=0{m}else{ZERO});
            delta=cnf.add3(delta,term);
        }
        // Only export a guard-free phase model if the complete violation
        // predicate was absorbed by the affine equations.
        let phase=if q.len()==1&&linear_form(&q[0],s.n).is_some(){Some(phase)}else{None};
        Some(AffPair{cnf,delta,inputs,primary,terms,phase,unsat:false,input_forms:forms[..s.n].to_vec()})
    }
    #[test]
    fn hoare_affine_quotient_exact(){
        let circuits=[
            vec![G::H(0),G::H(1),G::CX(0,1),G::T(1),G::H(0)],
            vec![G::H(0),G::CZ(0,1),G::H(0),G::CX(0,1),G::X(1)],
            vec![G::H(0),G::H(1),G::CX(1,0),G::S(0)],
            vec![G::CX(0,1),G::CX(1,0),G::H(1),G::T(1),G::H(1)],
        ];
        let pres=[vec![],vec![bit(0,false)],vec![equal_bits(0,1)],vec![Anf::new()],
            vec![bit(0,true),bit(0,false)],vec![Anf::from([1,2])]];
        let posts=[vec![],vec![Anf::new()],vec![bit(0,false)],vec![equal_bits(0,1)],
            vec![Anf::from([3])],vec![bit(0,false),bit(1,true)]];
        let mut checks=0;
        for ops in circuits{
            let s=native(2,&ops).unwrap();
            for p in &pres{for q in &posts{
                let plan=affine_quotient_pair(&s,p,q).unwrap();
                let (base,d)=two_copy_conj(&s,p,q);
                let expected=buckets(&base,d,&[],&mut 20_000_000).unwrap();
                assert_eq!(buckets(&plan.cnf,plan.delta,&[],&mut 20_000_000).unwrap(),expected);
                checks+=1;
                for x in 0..4u64{
                    let units:Vec<_>=plan.inputs.iter().enumerate().map(|(i,&l)|if x>>i&1!=0{l}else{-l}).collect();
                    let v=exact_pair_coeff(&plan.cnf,plan.delta,&units,&mut 20_000_000,&mut 0).unwrap();
                    let expected=if eval_conj(p,x){raw_for_input(2,&ops,q,x)}else{[0,0]};
                    assert_eq!(v,expected);checks+=1;
                }
            }}
        }
        let s=native(3,&[G::CCX(0,1,2)]).unwrap();
        assert!(affine_quotient_pair(&s,&[],&[bit(2,false)]).is_none());
        let s=native(2,&[G::H(0)]).unwrap();
        assert!(affine_quotient_pair(&s,&[Anf::from([3])],&[]).is_none());
        println!("HOARE_AFFINE_QUOTIENT checks={checks} bucket_and_conditioned_exact=true");
    }


    // The first failed postcondition partitions the violating output
    // subspace into disjoint projectors. Unlike summing all failures,
    // no basis output (or paired assignment) can be counted twice.
    fn first_failure_plans(s:&Symbolic,p:&[Anf],q:&[Anf])->Option<Vec<AffPair>>{
        if q.is_empty(){return Some(vec![]);}
        if q.len()>16||p.iter().any(|f|linear_form(f,s.n).is_none())
            ||q.iter().any(|f|linear_form(f,s.n).is_none())
            ||s.output.iter().any(|f|linear_form(f,s.n+s.h).is_none()){return None;}
        (0..q.len()).map(|i|affine_quotient_pair_prefix(s,p,&q[i..i+1],&q[..i])).collect()
    }
    #[test]
    fn hoare_first_failure_partition_exact(){
        let circuits=[
            vec![G::H(0),G::H(1),G::CX(0,1),G::T(1),G::H(0)],
            vec![G::H(0),G::CZ(0,1),G::H(0),G::CX(0,1),G::X(1)],
            vec![G::H(0),G::H(1),G::CX(1,0),G::S(0)],
        ];
        let pres=[vec![],vec![bit(0,false)],vec![equal_bits(0,1)],vec![Anf::new()]];
        let posts=[vec![],vec![bit(0,false)],vec![bit(0,false),bit(1,true)],
            vec![bit(0,false),bit(0,false)],vec![bit(0,false),bit(0,true)],
            vec![equal_bits(0,1),bit(1,false),Anf::new()],vec![Anf::from([0])]];
        let mut checks=0;
        for ops in circuits{
            let s=native(2,&ops).unwrap();
            for p in &pres{for q in &posts{
                let plans=first_failure_plans(&s,p,q).unwrap();
                let (base,d)=two_copy_conj(&s,p,q);
                let expected=buckets(&base,d,&[],&mut 20_000_000).unwrap();
                let mut sum=[0u128;8];
                for a in &plans{
                    let v=buckets(&a.cnf,a.delta,&[],&mut 20_000_000).unwrap();
                    for i in 0..8{sum[i]+=v[i];}
                }
                assert_eq!(sum,expected);checks+=1;
                for x in 0..4u64{
                    let mut sum=[0i128;2];
                    for a in &plans{
                        let units:Vec<_>=a.inputs.iter().enumerate().map(|(i,&l)|if x>>i&1!=0{l}else{-l}).collect();
                        let v=exact_pair_coeff(&a.cnf,a.delta,&units,&mut 20_000_000,&mut 0).unwrap();
                        sum[0]+=v[0];sum[1]+=v[1];
                    }
                    let expected=if eval_conj(p,x){raw_for_input(2,&ops,q,x)}else{[0,0]};
                    assert_eq!(sum,expected);checks+=1;
                }
            }}
        }
        let s=native(2,&[G::H(0)]).unwrap();
        assert!(first_failure_plans(&s,&[],&[Anf::from([3])]).is_none());
        println!("HOARE_FIRST_FAILURE checks={checks} disjoint_exact=true");
    }
    fn export_property_factor_benchmark(dir:&std::path::Path){
        let mut cases=Vec::new();
        for (name,n,ops,p,q,valid) in algorithmic_cases(){
            let mut expected=[0i128;2];
            for x in 0..1u64<<n{
                if eval_conj(&p,x){let v=raw_for_input(n,&ops,&q,x);expected[0]+=v[0];expected[1]+=v[1];}
            }
            assert_eq!(expected==[0,0],valid);
            cases.push((name,n,ops,p,q,expected,"dense-all-inputs"));
        }
        for c in scaled_cases().into_iter().filter(|c|
            c.name.starts_with("GHZ16-")||c.name.starts_with("BV8-")||c.name.starts_with("CS-parity4-")){
            // GHZ/BV have exactly one legal input. CS-parity uses the
            // independently derived family identity and witness contract.
            let source=if c.name.starts_with("CS-parity"){"analytic-family"}else{"dense-unique-input"};
            if source=="dense-unique-input"{
                assert_eq!((0..1u64<<c.n).filter(|&x|eval_conj(&c.p,x)).count(),1);
                assert!(eval_conj(&c.p,0));
                assert_eq!(raw_for_input(c.n,&c.ops,&c.q,0),c.expected);
            }else if let Some(x)=c.known_witness{
                assert!(eval_conj(&c.p,x));assert_ne!(raw_for_input(c.n,&c.ops,&c.q,x),[0,0]);
            }
            cases.push((c.name,c.n,c.ops,c.p,c.q,c.expected,source));
        }
        assert_eq!(cases.len(),14);
        for n in [10usize,13,15]{
            for affine in [false,true]{
                let mut ops=scale_mixing(n,3);
                let q=if affine{ops.push(G::CX(1,0));vec![equal_bits(0,1)]}else{vec![bit(0,false)]};
                let name=if affine{format!("affine-mixing-{n}")}else{format!("mixing-{n}-3layer")};
                let p=(0..n).map(|i|bit(i,false)).collect::<Vec<_>>();
                let expected=raw_for_input(n,&ops,&q,0);
                cases.push((name,n,ops,p,q,expected,"dense-unique-input"));
            }
        }
        assert_eq!(cases.len(),20);
        let mut manifest=String::new();let mut branches=String::new();
        for (name,n,ops,p,q,raw,oracle) in cases{
            let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
            export_external_property(dir,&name,n,&ops,&p,&q);
            let t=std::time::Instant::now();
            let reduced=property_cone(n,&ops,&q).unwrap();
            let s=native(n,&reduced).unwrap();
            let scale=h-s.h;
            let common_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (c,d)=two_copy_conj(&s,&p,&q);
            let cnf_status=if let Some(data)=serialize_external(&c,&[]){
                std::fs::write(dir.join(format!("property-base-{name}.cnf")),data).unwrap();"READY"
            }else{"UNKNOWN_ENCODING_LIMIT"};
            let base_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let (status,count)=if let Some(plans)=first_failure_plans(&s,&p,&q){
                let count=plans.len();
                for (i,a) in plans.into_iter().enumerate(){
                    let status=if a.unsat{"UNSAT_AFFINE"}else{
                        let mut data=String::new();
                        for (key,k) in a.phase.expect("fully absorbed first-failure branch"){
                            data.push_str(&k.to_string());
                            for (m,b) in key{data.push_str(&format!("\t{m}:{}",b as u8));}
                            data.push('\n');
                        }
                        std::fs::write(dir.join(format!("property-factor-{name}-{i}.tsv")),data).unwrap();
                        let map=a.input_forms.iter().map(|&(m,b)|format!("{m}:{}",b as u8)).collect::<Vec<_>>().join("\t");
                        std::fs::write(dir.join(format!("property-input-{name}-{i}.tsv")),map).unwrap();
                        "READY"
                    };
                    branches.push_str(&format!("{name}\t{i}\t{status}\t{}\t{}\n",a.primary,a.terms));
                }
                ("READY",count)
            }else{("UNSUPPORTED",0)};
            let factor_us=t.elapsed().as_micros();
            manifest.push_str(&format!("{name}\t{n}\t{h}\t{}\t{scale}\t{}\t{count}\t{status}\t{cnf_status}\t{}\t{}\t{},{},{}\t{common_us}\t{base_us}\t{factor_us}\t{},{}\t{oracle}\n",
                s.h,q.len(),c.vars,c.clauses.len(),d[0],d[1],d[2],raw[0],raw[1]));
        }
        std::fs::write(dir.join("property-factor.tsv"),manifest).unwrap();
        std::fs::write(dir.join("property-factor-branches.tsv"),branches).unwrap();
    }

    fn export_phase_factors(dir:&std::path::Path,name:&str,s:&Symbolic,p:&[Anf],q:&[Anf],
                            scale:usize,raw:[i128;2],prep_us:u128,manifest:&mut String){
        let t=std::time::Instant::now();
        let plan=affine_quotient_pair(s,p,q).expect("affine factor admission");
        let mut data=String::new();
        let status=if plan.unsat{"UNSAT_AFFINE"}else if let Some(phase)=&plan.phase{
            for (key,k) in phase{
                data.push_str(&k.to_string());
                for &(mask,b) in key{data.push_str(&format!("\t{mask}:{}",b as u8));}
                data.push('\n');
            }
            std::fs::write(dir.join(format!("factors-{name}.tsv")),data).unwrap();
            "READY"
        }else{"UNSUPPORTED_GUARD"};
        let prep=prep_us+t.elapsed().as_micros();
        manifest.push_str(&format!("{name}\t{}\t{scale}\t{}\t{}\t{status}\t{prep}\t{},{}\n",
            s.h,plan.primary,plan.terms,raw[0],raw[1]));
    }
    fn export_factor_controls(dir:&std::path::Path,manifest:&mut String){
        let cases=[
            ("factor-HTH",1,vec![G::H(0),G::T(0),G::H(0)],vec![bit(0,false)],vec![bit(0,false)]),
            ("factor-HH-safe",1,vec![G::H(0),G::H(0)],vec![bit(0,false)],vec![bit(0,false)]),
            ("factor-parity-free",2,vec![G::H(0),G::T(0),G::CX(0,1),G::H(0)],vec![equal_bits(0,1)],vec![equal_bits(0,1)]),
            ("factor-inconsistent",1,vec![G::H(0)],vec![bit(0,false),bit(0,true)],vec![bit(0,false)]),
            ("factor-universal-post",1,vec![G::H(0)],vec![],vec![Anf::from([0])]),
        ];
        for (name,n,ops,p,q) in cases{
            let mut raw=[0i128;2];
            for x in 0..1u64<<n{if eval_conj(&p,x){let v=raw_for_input(n,&ops,&q,x);raw[0]+=v[0];raw[1]+=v[1];}}
            let t=std::time::Instant::now();
            let s=native(n,&ops).unwrap();
            export_phase_factors(dir,name,&s,&p,&q,0,raw,t.elapsed().as_micros(),manifest);
        }
    }

    fn export_affine_benchmark(dir:&std::path::Path,factors:&mut String){
        let mut manifest=String::new();
        for n in [10usize,13,15]{
            // Invertible output relabeling, so the original property is
            // now parity(z0,z1)=0 rather than a literal. Both modes use
            // this same actual circuit and predicate, not a surrogate.
            let mut ops=scale_mixing(n,3);ops.push(G::CX(1,0));
            let p:Vec<_>=(0..n).map(|i|bit(i,false)).collect();
            let q=vec![equal_bits(0,1)];
            let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
            let raw=raw_for_input(n,&ops,&q,0);
            assert_eq!(raw,raw_for_input(n,&scale_mixing(n,3),&[bit(0,false)],0));
            let name=format!("affine-mixing-{n}");
            export_external_property(dir,&name,n,&ops,&p,&q);
            let t=std::time::Instant::now();
            let reduced=property_cone(n,&ops,&q).unwrap();
            let cone_us=t.elapsed().as_micros();
            let t=std::time::Instant::now();
            let s=native(n,&reduced).unwrap();
            let build_us=t.elapsed().as_micros();
            let scale=h-s.h;
            assert_eq!(raw_for_input(n,&reduced,&q,0).map(|v|v*(1i128<<scale)),raw);
            assert!(quotient_pair(&s,&p,&q).is_none());
            export_phase_factors(dir,&name,&s,&p,&q,scale,raw,cone_us+build_us,factors);
            for mode in ["cone","affine"]{
                let t=std::time::Instant::now();
                let (c,d,primary,terms)=if mode=="affine"{
                    let a=affine_quotient_pair(&s,&p,&q).unwrap();
                    (a.cnf,a.delta,a.primary,a.terms)
                }else{let (c,d)=two_copy_conj(&s,&p,&q);(c,d,s.n+2*s.h,s.phase.len()*2)};
                let status=if let Some(text)=serialize_external(&c,&[]){
                    std::fs::write(dir.join(format!("{mode}-{name}.cnf")),text).unwrap();"READY"
                }else{"UNKNOWN_ENCODING_LIMIT"};
                let enc_us=t.elapsed().as_micros();
                manifest.push_str(&format!("{name}\t{mode}\t{h}\t{}\t{scale}\t{}\t{}\t{primary}\t{terms}\t{},{},{}\t{status}\t{cone_us}\t{build_us}\t{enc_us}\t{},{}\n",
                    s.h,c.vars,c.clauses.len(),d[0],d[1],d[2],raw[0],raw[1]));
            }
        }
        std::fs::write(dir.join("affine.tsv"),manifest).unwrap();
    }

    fn export_cone_case(dir:&std::path::Path,name:&str,n:usize,ops:&[G],p:&[Anf],q:&[Anf],
                        raw:[i128;2],manifest:&mut String,quotients:&mut String,factors:&mut String){
        let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
        let t=std::time::Instant::now();
        let reduced=property_cone(n,ops,q).unwrap();
        let cone_us=t.elapsed().as_micros();
        let hr=reduced.iter().filter(|g|matches!(g,G::H(_))).count();
        let scale=h-hr;
        // Unique legal input in the frozen scale cohort; oracle is not
        // part of either solver's decision or timing.
        assert_eq!(raw_for_input(n,&reduced,q,0).map(|v|v*(1i128<<scale)),raw);
        let t=std::time::Instant::now();
        let s=native(n,&reduced).unwrap();
        let build_us=t.elapsed().as_micros();
        assert_eq!(s.h,hr);
        export_phase_factors(dir,name,&s,p,q,scale,raw,cone_us+build_us,factors);
        let t=std::time::Instant::now();
        let (c,d)=two_copy_conj(&s,p,q);
        let status=if let Some(text)=serialize_external(&c,&[]){
            std::fs::write(dir.join(format!("cone-{name}.cnf")),text).unwrap();"READY"
        }else{"UNKNOWN_ENCODING_LIMIT"};
        let encoding_us=t.elapsed().as_micros();
        manifest.push_str(&format!("{name}\t{h}\t{hr}\t{}\t{}\t{scale}\t{}\t{}\t{},{},{}\t{status}\t{cone_us}\t{build_us}\t{encoding_us}\t{},{}\n",
            ops.len(),reduced.len(),c.vars,c.clauses.len(),d[0],d[1],d[2],raw[0],raw[1]));
        let t=std::time::Instant::now();
        let (qc,qd,primary,terms)=quotient_pair(&s,p,q).expect("scale literal output quotient");
        let qs=if let Some(text)=serialize_external(&qc,&[]){
            std::fs::write(dir.join(format!("quotient-{name}.cnf")),text).unwrap();"READY"
        }else{"UNKNOWN_ENCODING_LIMIT"};
        let qus=t.elapsed().as_micros();
        quotients.push_str(&format!("{name}\t{h}\t{hr}\t{}\t{}\t{scale}\t{}\t{}\t{},{},{}\t{qs}\t{cone_us}\t{build_us}\t{qus}\t{},{}\t{primary}\t{terms}\n",
            ops.len(),reduced.len(),qc.vars,qc.clauses.len(),qd[0],qd[1],qd[2],raw[0],raw[1]));
    }

    fn export_scale_benchmark(dir:&std::path::Path){
        let dir=dir.join("scale-discovery");
        std::fs::create_dir_all(&dir).unwrap();
        let mut direct=String::new();let mut residual=String::new();let mut cones=String::new();let mut quotients=String::new();let mut factors=String::new();
        let mut cases=Vec::new();
        for n in [8usize,10,12]{
            let v=scale_mixing(n,2);
            let inverse=scale_inverse(&v);
            for mutant in [false,true]{
                let mut ops=v.clone();
                if mutant{ops.push(G::Z(0));}
                ops.extend(inverse.clone());
                let name=format!("uncompute-{n}-{}",if mutant{"mutant"}else{"safe"});
                let q=(0..n).map(|i|bit(i,false)).collect::<Vec<_>>();
                cases.push((name,n,ops,q,Some(mutant)));
            }
        }
        for n in [10usize,13,15]{
            cases.push((format!("mixing-{n}-3layer"),n,scale_mixing(n,3),vec![bit(0,false)],None));
        }
        for (name,n,ops,q,intent) in cases{
            let p:Vec<_>=(0..n).map(|i|bit(i,false)).collect();
            let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
            assert!(h<=48&&n+h<=63&&ops.len()<=512);
            let t=std::time::Instant::now();
            let raw=raw_for_input(n,&ops,&q,0);
            let oracle_us=t.elapsed().as_micros();
            if let Some(bad)=intent{assert_eq!(raw!=[0,0],bad,"{name}");}
            let witness=if raw==[0,0]{"-"}else{"0"};
            let t=std::time::Instant::now();
            let s=native(n,&ops).expect("scaled original exact IR");
            let build_us=t.elapsed().as_micros();
            assert_eq!(s.h,h);
            let t=std::time::Instant::now();
            let (c,d)=two_copy_conj(&s,&p,&q);
            let status=if let Some(text)=serialize_external(&c,&[]){
                std::fs::write(dir.join(format!("direct-{name}.cnf")),text).unwrap();"READY"
            }else{"UNKNOWN_ENCODING_LIMIT"};
            let encoding_us=t.elapsed().as_micros();
            direct.push_str(&format!("{name}\t{n}\t{h}\t{}\t{}\t{}\t{},{},{}\t{status}\t{build_us}\t{encoding_us}\t{oracle_us}\t{},{}\t{witness}\n",
                ops.len(),c.vars,c.clauses.len(),d[0],d[1],d[2],raw[0],raw[1]));
            if name.starts_with("mixing"){export_cone_case(&dir,&name,n,&ops,&p,&q,raw,&mut cones,&mut quotients,&mut factors);}
            if let Some(input)=HoareInput::build_scale(n,&ops,p,q){
                emit_residual_plans(&dir,&name,&input,raw,witness,&mut residual,true);
            }else{
                for mode in ["standard","property","adaptive","sat-assisted"]{
                    residual.push_str(&format!("{name}\t{mode}\t{n}\t{h}\t{h}\t0\t0\t0\t0\t0\t0\t-\tUNKNOWN_REDUCTION_LIMIT\t-\t0\t0\tscale-admission\t{},{}\t{witness}\t0\tnone\t0\t0\t0\t0\tnot-run\n",raw[0],raw[1]));
                }
            }
            export_external_property(&dir,&name,n,&ops,&(0..n).map(|i|bit(i,false)).collect::<Vec<_>>(),
                // Export same predicate from independently declared family.
                &if name.starts_with("uncompute"){(0..n).map(|i|bit(i,false)).collect()}else{vec![bit(0,false)]});
        }
        std::fs::write(dir.join("direct.tsv"),direct).unwrap();
        std::fs::write(dir.join("residual.tsv"),residual).unwrap();
        std::fs::write(dir.join("cone.tsv"),cones).unwrap();
        std::fs::write(dir.join("quotient.tsv"),quotients).unwrap();
        export_affine_benchmark(&dir,&mut factors);
        export_factor_controls(&dir,&mut factors);
        std::fs::write(dir.join("factors.tsv"),factors).unwrap();
        export_property_factor_benchmark(&dir);
        println!("HOARE_SCALE_DISCOVERY_FIXTURES cases=9 routes=45 cone_cases=3");
    }

}
