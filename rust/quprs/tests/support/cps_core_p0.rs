
// CORE-1/2 research contract: native PathSum is the sole P/f/variable
// representation. Reuse the existing stable-ID guard frame, with an
// independent signed scale. Rectangular maps are admitted here, not
// passed to the square-only production reducer or gate API.
#[derive(Clone)]
struct CpsCore {
    ps: PathSum,
    guard: NativeGuardFrame,
    k: i32,
}
type CoreBool = rustc_hash::FxHashSet<Vec<u32>>;
const CORE_TERMS:usize=256;
fn core_bit(v:u32)->Option<u64>{if v<63{Some(1u64<<v)}else{None}}
fn core_mask(m:&[u32])->Option<u64>{
    m.iter().try_fold(0u64,|a,&v|Some(a|core_bit(v)?))
}
fn core_phase8(c:&quprs::PhaseCoeff)->Option<u8>{
    if c.radians.is_some()||!c.symbols.is_empty()||c.constant.denom<=0{return None;}
    let num=8i128*i128::from(c.constant.numer);
    let den=i128::from(c.constant.denom);
    if num%den!=0{return None;}
    Some((num/den).rem_euclid(8) as u8)
}
fn core_terms_ok(ps:&PathSum)->bool{
    ps.p.terms.len()<=CORE_TERMS&&ps.f.functions.iter().all(|p|p.len()<=CORE_TERMS)
}
fn core_anf(p:&CoreBool)->Option<Anf>{
    p.iter().map(|m|core_mask(m)).collect()
}
fn core_rename_anf(p:&Anf,map:&BTreeMap<u32,u32>)->Option<Anf>{
    p.iter().map(|&m|{
        (0..63u32).filter(|&v|m&(1u64<<v)!=0).try_fold(0u64,|a,v|Some(a|core_bit(*map.get(&v)?)?))
    }).collect()
}
fn core_rename(ps:&PathSum,map:&BTreeMap<u32,u32>)->Option<(quprs::pathsum::PhasePolynomial,quprs::pathsum::BooleanState)>{
    let rename=|m:&Vec<u32>|->Option<Vec<u32>>{
        let mut out=m.iter().map(|v|map.get(v).copied()).collect::<Option<Vec<_>>>()?;
        out.sort_unstable();out.dedup();Some(out)
    };
    let mut phase=quprs::pathsum::PhasePolynomial::new();
    for (m,c) in &ps.p.terms{phase.add_term(rename(m)?,c.clone());}
    let mut f=ps.f.clone();
    for p in &mut f.functions{*p=p.iter().map(&rename).collect::<Option<CoreBool>>()?;}
    Some((phase,f))
}
impl CpsCore{
    fn new(ps:PathSum,extra:Anf,k:i32)->Option<Self>{
        let guard=NativeGuardFrame::new(&ps,extra)?;
        let c=Self{ps,guard,k};if c.valid(){Some(c)}else{None}
    }
    fn n(&self)->usize{self.ps.v.num_qubits}
    fn q(&self)->usize{self.ps.f.functions.len()}
    fn valid(&self)->bool{
        let ps=&self.ps;let n=self.n();let q=self.q();let live=&ps.v.path_vars;
        if n>16||q>16||ps.rr_approximate||ps.rr_tolerance!=0.0||
            !ps.v.continuous_vars.is_empty()||!core_terms_ok(ps)||
            (0..n).any(|i|!live.contains(&(i as u32)))||
            live.iter().any(|&v|v>=63||v>=ps.v.next_id)||
            ps.f.registers.iter().map(|r|r.size).sum::<usize>()!=q||
            self.guard.compact(ps).is_none(){return false;}
        let mono_ok=|m:&Vec<u32>|m.windows(2).all(|w|w[0]<w[1])&&m.iter().all(|v|live.contains(v));
        ps.f.functions.iter().all(|p|p.iter().all(&mono_ok))&&
            ps.p.terms.iter().all(|(m,c)|mono_ok(m)&&core_phase8(c).is_some())
    }
    // Explicit raw embedding only: callers must supply the true scale of
    // an already reduced native PathSum via new(), not infer it from h.
    fn circuit(n:usize,ops:&[G])->Option<Self>{
        if !admitted(n,ops){return None;}
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        for g in ops{g.apply(&mut ps,false);if !core_terms_ok(&ps){return None;}}
        let k=i32::try_from(ops.iter().filter(|g|matches!(g,G::H(_))).count()).ok()?;
        if ps.v.path_vars.len()!=n+k as usize{return None;}
        Self::new(ps,Anf::from([0]),k)
    }
    // self=A, next=B, returns B A. Rebase *all* B IDs, including its
    // formal inputs, before any substitution: no sequential capture.
    fn then(&self,next:&Self)->Option<Self>{
        if !self.valid()||!next.valid()||self.q()!=next.n(){return None;}
        let k=self.k.checked_add(next.k)?;
        let mut ps=PathSum::new(self.n());ps.set_auto_reduce(false);
        ps.v=self.ps.v.clone();ps.p=self.ps.p.clone();
        let mut map=BTreeMap::new();
        for &old in &next.guard.ids{
            let id=ps.v.get_fresh_var();core_bit(id)?;map.insert(old,id);
        }
        let (mut p,mut f)=core_rename(&next.ps,&map)?;
        let mut g=core_rename_anf(&next.guard.extra,&map)?;
        for (i,repl) in self.ps.f.functions.iter().enumerate(){
            let v=*map.get(&(i as u32))?;
            // Bound expansion before native substitution, not after an
            // arbitrarily large XOR expansion. This is an admission cap.
            if repl.len()>8{return None;}
            p.substitute_var_with_poly(v,repl);
            f.substitute_var_with_poly(v,repl);
            g=substitute_guard(&g,v,&core_anf(repl)?)?;
            ps.v.path_vars.remove(&v);
            if p.terms.len()>CORE_TERMS||f.functions.iter().any(|q|q.len()>CORE_TERMS){return None;}
        }
        for (m,c) in p.terms{ps.p.add_term(m,c);}
        ps.f=f;
        let guard=mul_anf(&self.guard.extra,&g)?;
        Self::new(ps,guard,k)
    }
    // Old free inputs become bound; fresh free outputs are never
    // captured by the old input/path IDs. Keep k, not k+n.
    fn adjoint(&self)->Option<Self>{
        if !self.valid(){return None;}
        let mut ps=PathSum::new(self.q());ps.set_auto_reduce(false);
        let mut map=BTreeMap::new();
        for &old in &self.guard.ids{
            let id=ps.v.get_fresh_var();core_bit(id)?;map.insert(old,id);
        }
        let (p,f)=core_rename(&self.ps,&map)?;
        let mut guard=core_rename_anf(&self.guard.extra,&map)?;
        for (j,out) in f.functions.iter().enumerate(){
            // equality = 1 XOR f_j XOR z_j
            let mut eq=core_anf(out)?;xor_insert(&mut eq,0);xor_insert(&mut eq,core_bit(j as u32)?);
            guard=mul_anf(&guard,&eq)?;
        }
        for (m,c) in p.terms{ps.p.add_term(m,c*(-1));}
        ps.f=quprs::pathsum::BooleanState::new(self.n());
        for (i,out) in ps.f.functions.iter_mut().enumerate(){
            out.clear();out.insert(vec![*map.get(&(i as u32))?]);
        }
        Self::new(ps,guard,self.k)
    }
}

// Independent bounded matrix oracle evaluates the native fields directly;
// no compact()/then()/adjoint() in operand evaluation. Ring numerators are
// compared at their independently checked common scale.
fn core_matrix(c:&CpsCore)->Vec<Vec<Root>>{
    assert!(c.valid());
    let n=c.n();let q=c.q();
    let ids:Vec<_>=c.guard.ids.iter().copied().filter(|&v|v as usize>=n).collect();
    assert!(n<=3&&q<=3&&ids.len()<=18);
    let mut out=vec![vec![[0;4];1usize<<n];1usize<<q];
    for x in 0..1u64<<n{for y in 0..1u64<<ids.len(){
        let a=ids.iter().enumerate().fold(x,|v,(i,&id)|v|(((y>>i)&1)<<id));
        if !eval(&c.guard.extra,a){continue;}
        let on=|m:&Vec<u32>|m.iter().all(|&id|a&(1u64<<id)!=0);
        let z=c.ps.f.functions.iter().enumerate().fold(0usize,|v,(i,p)|{
            v|((p.iter().filter(|m|on(m)).count()%2)<<i)
        });
        let k=c.ps.p.terms.iter().filter(|(m,_)|on(m)).map(|(_,p)|core_phase8(p).unwrap() as usize).sum::<usize>();
        out[z][x as usize]=add(out[z][x as usize],root(k));
    }}
    out
}
fn core_product(a:&[Vec<Root>],b:&[Vec<Root>])->Vec<Vec<Root>>{
    assert_eq!(a.len(),b[0].len());
    let mut c=vec![vec![[0;4];a[0].len()];b.len()];
    for z in 0..b.len(){for x in 0..a[0].len(){for j in 0..a.len(){
        for (k,&coef) in a[j][x].iter().enumerate(){
            let v=shift(b[z][j],k);c[z][x]=add(c[z][x],v.map(|t|t*coef));
        }
    }}}
    c
}
fn core_dagger(a:&[Vec<Root>])->Vec<Vec<Root>>{
    (0..a[0].len()).map(|x|a.iter().map(|row|{let v=row[x];[v[0],-v[3],-v[2],-v[1]]}).collect()).collect()
}
#[test]
fn hoare_cps_core_closure(){
    let mut state=20261127u64;
    let mut rand=|n:usize|->usize{state^=state<<13;state^=state>>7;state^=state<<17;(state%n as u64) as usize};
    let mut fixture=|n:usize,q:usize,zero:bool|->CpsCore{
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        // Stable IDs with holes, overlapping IDs between operands, and
        // rectangular output signatures are intentional.
        let hole=ps.v.get_fresh_var();ps.v.path_vars.remove(&hole);
        for _ in 0..2{ps.v.get_fresh_var();}
        let ids=native_ids(&ps).unwrap();
        let mut mono=||->Vec<u32>{let mut m=Vec::new();for &id in &ids{if rand(3)==0{m.push(id);}}m};
        ps.f=quprs::pathsum::BooleanState::new(q);
        for p in &mut ps.f.functions{p.clear();for _ in 0..2{let m=mono();if !p.remove(&m){p.insert(m);}}}
        let phases:Vec<_>=(0..4).map(|_|mono()).collect();drop(mono);
        for m in phases{ps.p.add_term(m,quprs::PhaseCoeff::new_constant(quprs::Rational::new(rand(8) as i64,8)));}
        let mut guard=Anf::from([0]);
        if zero{guard.clear();}else{xor_insert(&mut guard,1u64<<ids[rand(ids.len())]);}
        CpsCore::new(ps,guard,rand(7) as i32-3).unwrap()
    };
    let(mut comp,mut adj,mut assoc,mut reverse,mut entries,mut rectangular,mut negative,mut zeros)=(0,0,0,0,0,0,0,0);
    for i in 0..128{
        let n=i%2;let r=(i/2)%2+1;let q=(i/4)%2;let w=(i/8)%2+1;
        let a=fixture(n,r,i%16==0);let b=fixture(r,q,false);let c=fixture(q,w,false);
        if n!=r||r!=q{rectangular+=1;}if a.k<0||b.k<0{negative+=1;}if i%16==0{zeros+=1;}
        let am=core_matrix(&a);let bm=core_matrix(&b);
        let ba=a.then(&b).unwrap();assert_eq!(ba.k,a.k+b.k);
        assert_eq!(core_matrix(&ba),core_product(&am,&bm));comp+=1;entries+=(1<<n)*(1<<q);
        let ad=a.adjoint().unwrap();assert_eq!(ad.k,a.k);
        assert_eq!(core_matrix(&ad),core_dagger(&am));adj+=1;
        let l=ba.then(&c).unwrap();let r=a.then(&b.then(&c).unwrap()).unwrap();
        assert_eq!(l.k,r.k);assert_eq!(core_matrix(&l),core_matrix(&r));assoc+=1;
        let left=ba.adjoint().unwrap();let right=b.adjoint().unwrap().then(&ad).unwrap();
        assert_eq!(left.k,right.k);assert_eq!(core_matrix(&left),core_matrix(&right));reverse+=1;
    }
    // Original circuit embedding and gate lowering agree on each column.
    // Include an XOR output substitution with exact Z8 coefficient.
    let aops=vec![G::H(0),G::CX(0,1),G::H(1)];
    let bops=vec![G::T(1),G::CZ(0,1),G::H(0)];
    let a=CpsCore::circuit(2,&aops).unwrap();let b=CpsCore::circuit(2,&bops).unwrap();
    let p=a.then(&b).unwrap();let mut ops=aops;ops.extend(bops);
    let m=core_matrix(&p);assert_eq!(p.k,3);
    for x in 0..4{let oracle=dense_state(2,&ops,x as u64);for z in 0..4{assert_eq!(m[z][x],oracle[z]);}}
    // Known strict original EQ result, unchanged production gate API.
    use quprs::{check_equivalence_with_options,EquivalenceStatus,VerificationOptions,VerificationMethod,VerificationStrategy};
    let h=CpsCore::circuit(1,&[G::H(0)]).unwrap();let hh=h.then(&h).unwrap();
    assert_eq!(hh.k,2);assert_eq!(core_matrix(&hh),vec![vec![[2,0,0,0],[0;4]],vec![[0;4],[2,0,0,0]]]);
    let opt=VerificationOptions{method:VerificationMethod::ReductionRules,
        strategy:VerificationStrategy::Difference,rr_tolerance:0.0,tool_name:"gpmc".into(),timeout_secs:1,..VerificationOptions::default()};
    let eq=check_equivalence_with_options(1,&[G::H(0),G::H(0)],&[],&opt).unwrap();
    assert_eq!(eq.status,EquivalenceStatus::Equivalent);assert!(!eq.rr_approximate&&!eq.solver_invoked);
    // Reject shape, stale guard, phase admission, dangling ID, signed overflow.
    assert!(a.then(&h).is_none());
    let mut stale=a.clone();stale.ps.v.get_fresh_var();assert!(!stale.valid());assert!(stale.adjoint().is_none());
    let mut unsupported=PathSum::new(1);unsupported.p.add_term(vec![0],quprs::PhaseCoeff::new_constant(quprs::Rational::new(1,3)));
    assert!(CpsCore::new(unsupported,Anf::from([0]),0).is_none());
    let mut dangling=PathSum::new(1);dangling.f.functions[0].insert(vec![19]);
    assert!(CpsCore::new(dangling,Anf::from([0]),0).is_none());
    let mut overflow=h.clone();overflow.k=i32::MAX;assert!(overflow.then(&h).is_none());
    assert_eq!((comp,adj,assoc,reverse),(128,128,128,128));
    println!("CPS_CORE_CLOSURE composition={comp} adjoint={adj} associativity={assoc} reverse={reverse} entries={entries} rectangular={rectangular} negative_scale={negative} zero_guards={zeros} circuit_columns=4 strict_eq=1 rejection_controls=5");
}
