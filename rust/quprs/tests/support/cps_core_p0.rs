
// CORE-1/2 research contract: native PathSum is the sole P/f/variable
// representation. Reuse the existing stable-ID guard frame, with an
// derived signed normalization ledger (not an independent semantic input).
// Canonical CPS scale is 2^(-h/2), h = number of summed variables.
// Rectangular maps are admitted here, not
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
    if c.radians.is_some()||!c.symbols.is_empty()||c.constant.denom<=0||c.constant.denom>8||c.constant.numer<0||c.constant.numer>=c.constant.denom{return None;}
    if c.constant!=quprs::Rational::new(c.constant.numer,c.constant.denom){return None;}
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
    // Only canonical source ingress. Derive k from the declared summed
    // variables, not the number of active/satisfying assignments.
    fn canonical(ps:PathSum,extra:Anf)->Option<Self>{
        let h=ps.v.path_vars.len().checked_sub(ps.v.num_qubits)?;
        Self::from_derived(ps,extra,i32::try_from(h).ok()?)
    }
    // Internal operation result only. k is a receipt of canonical source
    // ingress and legal transformations, not an externally supplied scale.
    // CORE-3 must transport k via checked native RR receipts.
    fn from_derived(ps:PathSum,extra:Anf,k:i32)->Option<Self>{
        let guard=NativeGuardFrame::new(&ps,extra)?;
        Self::from_frame(ps,guard,k)
    }
    fn from_factors(ps:PathSum,factors:Vec<Anf>,k:i32)->Option<Self>{
        let guard=NativeGuardFrame::from_factors(&ps,factors)?;
        Self::from_frame(ps,guard,k)
    }
    fn from_frame(ps:PathSum,guard:NativeGuardFrame,k:i32)->Option<Self>{
        let c=Self{ps,guard,k};if c.valid(){Some(c)}else{None}
    }
    fn n(&self)->usize{self.ps.v.num_qubits}
    fn q(&self)->usize{self.ps.f.functions.len()}
    fn valid(&self)->bool{
        let ps=&self.ps;let n=self.n();let q=self.q();let live=&ps.v.path_vars;
        if n>16||q>16||ps.rr_approximate||ps.rr_tolerance!=0.0||
            !ps.v.continuous_vars.is_empty()||!core_terms_ok(ps)||
            (0..n).any(|i|!live.contains(&(i as u32)))||
            ps.v.next_id>63||live.iter().any(|&v|v>=63||v>=ps.v.next_id)||
            ps.f.registers.iter().map(|r|r.size).sum::<usize>()!=q||
            self.guard.compact_factors(ps).is_none(){return false;}
        let mono_ok=|m:&Vec<u32>|m.windows(2).all(|w|w[0]<w[1])&&m.iter().all(|v|live.contains(v));
        ps.f.functions.iter().all(|p|p.iter().all(&mono_ok))&&
            ps.p.terms.iter().all(|(m,c)|mono_ok(m)&&core_phase8(c).is_some())
    }
    // Explicit raw embedding only. An already reduced PathSum cannot be
    // imported as raw: it must enter via a checked transformation receipt.
    fn circuit(n:usize,ops:&[G])->Option<Self>{
        if !admitted(n,ops){return None;}
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        for g in ops{g.apply(&mut ps,false);if !core_terms_ok(&ps){return None;}}
        let k=i32::try_from(ops.iter().filter(|g|matches!(g,G::H(_))).count()).ok()?;
        if ps.v.path_vars.len()!=n+k as usize{return None;}
        Self::canonical(ps,Anf::from([0]))
    }
    // self=A, next=B, returns B A. Rebase *all* B IDs, including its
    // formal inputs, before any substitution: no sequential capture.
    fn then(&self,next:&Self)->Option<Self>{
        if !self.valid()||!next.valid()||self.q()!=next.n(){return None;}
        let k=self.k.checked_add(next.k)?;
        let mut ps=PathSum::new(self.n());ps.set_auto_reduce(false);
        ps.v=self.ps.v.clone();ps.p=self.ps.p.clone();
        if ps.v.next_id.checked_add(u32::try_from(next.guard.ids.len()).ok()?)?>63{return None;}
        let mut map=BTreeMap::new();
        for &old in &next.guard.ids{
            let id=ps.v.get_fresh_var();core_bit(id)?;map.insert(old,id);
        }
        let (mut p,mut f)=core_rename(&next.ps,&map)?;
        let mut gs=next.guard.factors().map(|g|core_rename_anf(g,&map)).collect::<Option<Vec<_>>>()?;
        for (i,repl) in self.ps.f.functions.iter().enumerate(){
            let v=*map.get(&(i as u32))?;
            // Bound expansion before native substitution, not after an
            // arbitrarily large XOR expansion. This is an admission cap.
            if repl.len()>8{return None;}
            p.substitute_var_with_poly(v,repl);
            f.substitute_var_with_poly(v,repl);
            let repl=core_anf(repl)?;
            gs=gs.iter().map(|g|substitute_guard(g,v,&repl)).collect::<Option<Vec<_>>>()?;
            ps.v.path_vars.remove(&v);
            if p.terms.len()>CORE_TERMS||f.functions.iter().any(|q|q.len()>CORE_TERMS){return None;}
        }
        for (m,c) in p.terms{ps.p.add_term(m,c);}
        ps.f=f;
        let mut factors=self.guard.factors().cloned().collect::<Vec<_>>();factors.extend(gs);
        Self::from_factors(ps,factors,k)
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
        let mut factors=self.guard.factors().map(|g|core_rename_anf(g,&map)).collect::<Option<Vec<_>>>()?;
        for (j,out) in f.functions.iter().enumerate(){
            // equality = 1 XOR f_j XOR z_j
            let mut eq=core_anf(out)?;xor_insert(&mut eq,0);xor_insert(&mut eq,core_bit(j as u32)?);
            factors.push(eq);
        }
        for (m,c) in p.terms{ps.p.add_term(m,c*(-1));}
        ps.f=quprs::pathsum::BooleanState::new(self.n());
        for (i,out) in ps.f.functions.iter_mut().enumerate(){
            out.clear();out.insert(vec![*map.get(&(i as u32))?]);
        }
        Self::from_factors(ps,factors,self.k)
    }
}

// Independent bounded matrix oracle evaluates the native fields directly;
// no compact()/then()/adjoint() in operand evaluation. Ring numerators are
// compared at their independently checked common scale.
fn core_matrix(c:&CpsCore)->Vec<Vec<Root>>{
    assert!(c.valid());
    let n=c.n();let q=c.q();
    let ids:Vec<_>=c.guard.ids.iter().copied().filter(|&v|v as usize>=n).collect();
    assert!(n<=3&&q<=8&&ids.len()<=18);
    let mut out=vec![vec![[0;4];1usize<<n];1usize<<q];
    for x in 0..1u64<<n{for y in 0..1u64<<ids.len(){
        let a=ids.iter().enumerate().fold(x,|v,(i,&id)|v|(((y>>i)&1)<<id));
        if !c.guard.factors().all(|g|eval(g,a)){continue;}
        let on=|m:&Vec<u32>|m.iter().all(|&id|a&(1u64<<id)!=0);
        let z=c.ps.f.functions.iter().enumerate().fold(0usize,|v,(i,p)|{
            v|((p.iter().filter(|m|on(m)).count()%2)<<i)
        });
        let k=c.ps.p.terms.iter().filter(|(m,_)|on(m)).map(|(_,p)|core_phase8(p).unwrap() as usize).sum::<usize>();
        out[z][x as usize]=add(out[z][x as usize],root(k));
    }}
    out
}
// Test-only proof witness for erasing the ledger. If k>h, fixed padding
// has one extension; if k<h, free padding has 2^(h-k) extensions.
// No canonical expansion is used by the timed/native algebraic route.
fn core_check_canonical_padding(c:&CpsCore){
    let h=i32::try_from(c.ps.v.path_vars.len()-c.n()).unwrap();
    assert!(c.guard.conjuncts.is_empty());
    let mut ps=c.ps.clone();let mut g=c.guard.extra.clone();
    let r=(c.k-h).abs();
    assert!(r<=8);
    for _ in 0..r{
        let v=ps.v.get_fresh_var();assert!(v<63);
        if c.k>h{
            let fixed_zero=Anf::from([0,1u64<<v]);
            g=mul_anf(&g,&fixed_zero).unwrap();
        }
    }
    let canonical=CpsCore::canonical(ps,g).unwrap();
    assert_eq!(canonical.k,h+r);
    let factor=if c.k<h{1i64<<r}else{1};
    assert_eq!(canonical.k-c.k,if c.k<h{2*r}else{0});
    let expected:Vec<Vec<Root>>=core_matrix(c).into_iter()
        .map(|row|row.into_iter().map(|v|v.map(|x|x*factor)).collect()).collect();
    assert_eq!(core_matrix(&canonical),expected);
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
        // Test-only adversarial ledger fixture: validate the compressed
        // representation against its canonical fixed-scale expansion below.
        // This is not a source constructor or a claim of RR reachability.
        CpsCore::from_derived(ps,guard,rand(7) as i32-3).unwrap()
    };
    let(mut comp,mut adj,mut assoc,mut reverse,mut entries,mut rectangular,mut negative,mut zeros)=(0,0,0,0,0,0,0,0);
    let(mut fixed,mut free,mut same)=(0,0,0);
    for i in 0..128{
        let n=i%2;let r=(i/2)%2+1;let q=(i/4)%2;let w=(i/8)%2+1;
        let a=fixture(n,r,i%16==0);let b=fixture(r,q,false);let c=fixture(q,w,false);
        if n!=r||r!=q{rectangular+=1;}if a.k<0||b.k<0{negative+=1;}if i%16==0{zeros+=1;}
        for v in [&a,&b,&c]{
            let h=(v.ps.v.path_vars.len()-v.n()) as i32;
            match v.k.cmp(&h){std::cmp::Ordering::Greater=>fixed+=1,std::cmp::Ordering::Less=>free+=1,std::cmp::Ordering::Equal=>same+=1}
            core_check_canonical_padding(v);
        }
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
    assert!(CpsCore::canonical(unsupported,Anf::from([0])).is_none());
    let mut dangling=PathSum::new(1);dangling.f.functions[0].insert(vec![19]);
    assert!(CpsCore::canonical(dangling,Anf::from([0])).is_none());
    let mut overflow=h.clone();overflow.k=i32::MAX;assert!(overflow.then(&h).is_none());
    let mut bad_id=h.clone();bad_id.ps.v.next_id=u32::MAX;assert!(!bad_id.valid());assert!(bad_id.then(&h).is_none());
    let mut bad_guard=h.clone();bad_guard.guard.extra.insert(1u64<<62);assert!(!bad_guard.valid());
    let mut near_cap=h.clone();near_cap.ps.v.next_id=63;assert!(near_cap.valid());assert!(near_cap.then(&h).is_none());
    let mut malformed=PathSum::new(1);let mut phase=quprs::PhaseCoeff::HALF;phase.constant.numer=2;phase.constant.denom=4;
    malformed.p.terms.insert(vec![0],phase);assert!(CpsCore::canonical(malformed,Anf::from([0])).is_none());
    assert_eq!((comp,adj,assoc,reverse),(128,128,128,128));
    assert_eq!(fixed+free+same,384);assert!(fixed>0&&free>0&&same>0);
    // Guard support changes do not re-normalize the canonical scale.
    let raw=h.ps.clone();let masked=CpsCore::canonical(raw,Anf::new()).unwrap();
    assert_eq!(masked.k,h.k);assert_eq!(core_matrix(&masked),vec![vec![[0;4];2];2]);
    println!("CPS_CORE_CANONICAL padding=384 fixed={fixed} free={free} unchanged={same} zero_guard_scale=PASS");
    println!("CPS_CORE_CLOSURE composition={comp} adjoint={adj} associativity={assoc} reverse={reverse} entries={entries} rectangular={rectangular} negative_scale={negative} zero_guards={zeros} circuit_columns=4 strict_eq=1 rejection_controls=9");
}

// CORE-3: extend the existing guarded RR receipt with the derived scale.
// No new reducer or rule. The current guarded snapshot is square-only;
// rectangular CPS remains representable and composable, not admitted here.
#[derive(Clone,Debug,PartialEq,Eq)]
struct CoreRrReceipt {
    native:GuardedReceipt,
    before_k:i32,
    after_k:i32,
}
impl CpsCore {
    fn rr_step(&self)->Option<(Self,CoreRrReceipt)>{
        if !self.valid()||self.n()!=self.q(){return None;}
        let step=guarded_native_step(&self.ps,self.n(),&self.guard)?;
        let native=guarded_receipt(&self.ps,self.n(),&self.guard,&step)?;
        let decrement=i32::try_from(native.scale2).ok()?;
        let after_k=self.k.checked_sub(decrement)?;
        let next=Self::from_frame(step.ps,step.guard,after_k)?;
        if next.guard.ids.len()>=self.guard.ids.len()||next.n()!=self.n()||next.q()!=self.q(){return None;}
        let receipt=CoreRrReceipt{native,before_k:self.k,after_k};
        Some((next,receipt))
    }
    fn replay_rr(&self,receipts:&[CoreRrReceipt])->Option<Self>{
        if !self.valid()||self.n()!=self.q()||receipts.len()>32{return None;}
        let mut c=self.clone();
        for supplied in receipts{
            let (next,actual)=c.rr_step()?;
            if &actual!=supplied{return None;}
            c=next;
        }
        Some(c)
    }
}
fn core_rr_equal(a:&CpsCore,b:&CpsCore){
    let k=a.k.max(b.k);
    let scale=|c:&CpsCore|->Vec<Vec<Root>>{
        let d=u32::try_from(k-c.k).unwrap();assert!(d<=24);
        core_matrix(c).into_iter().map(|r|r.into_iter()
            .map(|v|scale_guarded_entry(v,d)).collect()).collect()
    };
    assert_eq!(scale(a),scale(b));
}
#[test]
fn hoare_cps_core_guarded_rr(){
    let circuits=[
        vec![G::H(0),G::H(0)],
        vec![G::H(0),G::S(0),G::H(0)],
        vec![G::H(0),G::S(0),G::S(0),G::S(0),G::H(0)],
        vec![G::H(0),G::H(0),G::H(0),G::H(0)],
        vec![G::H(0),G::T(0),G::H(0)],
    ];
    let mut initial=Vec::new();
    for ops in circuits{
        let split=ops.len()/2;
        let a=CpsCore::circuit(1,&ops[..split]).unwrap();
        let b=CpsCore::circuit(1,&ops[split..]).unwrap();
        let c=a.then(&b).unwrap();
        // Genuine composed raw CPS, then guard restrictions (unchanged k).
        let ids=c.guard.ids.clone();
        let mut guards=vec![Anf::from([0]),Anf::new()];
        for &v in &ids{guards.push(Anf::from([1u64<<v]));guards.push(Anf::from([0,1u64<<v]));}
        for g in guards{initial.push(CpsCore::from_derived(c.ps.clone(),g,c.k).unwrap());}
        // Adjoint of a composed map, and composition with that adjoint.
        let d=c.adjoint().unwrap();
        initial.push(d.clone());
        initial.push(c.then(&d).unwrap());
    }
    // Real canonical ingress with an isolated path: Elim creates k=-1.
    // No arbitrary signed source scale is injected.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);let y=ps.v.get_fresh_var();
    let free=CpsCore::canonical(ps.clone(),Anf::from([0])).unwrap();
    let (neg,receipt)=free.rr_step().unwrap();
    assert_eq!(receipt.native.rule,GuardedRule::Elim);assert_eq!(neg.k,-1);
    core_rr_equal(&free,&neg);
    initial.push(free.clone());initial.push(free.adjoint().unwrap());
    initial.push(neg.then(&CpsCore::circuit(1,&[G::H(0),G::H(0)]).unwrap()).unwrap());
    // Same path is no longer eliminable when its guard depends on it.
    let blocked=CpsCore::canonical(ps,Anf::from([1u64<<y])).unwrap();
    assert!(blocked.rr_step().is_none());core_rr_equal(&blocked,&blocked);
    initial.push(blocked);
    // Rectangular maps are explicitly outside this existing RR adapter.
    let mut rect=PathSum::new(1);rect.f=quprs::pathsum::BooleanState::new(0);
    let rect=CpsCore::canonical(rect,Anf::from([0])).unwrap();
    assert!(rect.rr_step().is_none());assert!(rect.replay_rr(&[]).is_none());
    let (mut traces,mut steps,mut elim,mut hh,mut omega,mut multi,mut blocked_count,mut mutants,mut negative)=(0,0,0,0,0,0,0,0,0);
    for start in initial{
        let mut c=start.clone();let mut receipts=Vec::new();
        for _ in 0..16{
            let Some((next,r))=c.rr_step() else{break;};
            core_rr_equal(&c,&next);core_rr_equal(&start,&next);
            assert_eq!(r.before_k-r.after_k,r.native.scale2 as i32);
            assert!(r.native.removed.iter().all(|&v|v as usize>=start.n()));
            match r.native.rule{GuardedRule::Elim=>elim+=1,GuardedRule::Hh=>hh+=1,GuardedRule::Omega=>omega+=1}
            if next.k<0{negative+=1;}
            receipts.push(r);c=next;steps+=1;
        }
        if receipts.is_empty(){blocked_count+=1;}
        if receipts.len()>1{multi+=1;}
        let replay=start.replay_rr(&receipts).unwrap();
        assert_eq!(replay.k,c.k);core_rr_equal(&replay,&c);
        if !receipts.is_empty(){
            for field in 0..3{
                let mut wrong=receipts.clone();
                match field{
                    0=>wrong[0].before_k+=1,
                    1=>wrong[0].after_k+=1,
                    _=>wrong[0].native.scale2+=1,
                }
                assert!(start.replay_rr(&wrong).is_none());mutants+=1;
            }
        }
        traces+=1;
    }
    assert!(elim>0&&hh>0&&omega>0&&multi>0&&blocked_count>0&&negative>0);
    println!("CPS_CORE_RR traces={traces} steps={steps} elim={elim} hh={hh} omega={omega} multi={multi} blocked={blocked_count} scale_mutants={mutants} negative_steps={negative} guard_block=PASS rectangular_reject=PASS");
}

// Reuse the existing guarded two-copy exact CNF encoder. No source
// reconstruction and no re-normalization from residual hidden count.
impl CpsCore{
    fn wmc_norm_plan(&self)->Option<(Cnf,[Lit;3],usize,i32)>{
        if !self.valid()||self.n()!=self.q(){return None;}
        let s=compact(&self.ps,self.n())?;
        let primary=s.n.checked_add(s.h.checked_mul(2)?)?;
        if primary>63{return None;}
        let guard=self.guard.compact_factors(&self.ps)?;
        let (cnf,phase)=guarded_pair_factors(&s,&guard);
        Some((cnf,phase,primary,self.k))
    }
}
fn core_norm_numerator(c:&CpsCore)->(i64,i64){
    let mut total=[0;4];
    for v in core_matrix(c).into_iter().flatten(){
        total=add(total,rus_mul(v,rus_conj(v)));
    }
    assert_eq!(total[2],0);assert_eq!(total[1],-total[3]);
    (total[0],total[1])
}
#[test]
fn hoare_cps_core_wmc_export(){
    let dir=std::path::PathBuf::from(std::env::var("CPS_CORE_WMC_DIR").unwrap());
    std::fs::create_dir_all(&dir).unwrap();
    let mut cases=Vec::new();
    for (name,ops) in [
        ("hh",vec![G::H(0),G::H(0)]),
        ("omega",vec![G::H(0),G::S(0),G::H(0)]),
        ("nonclifford",vec![G::H(0),G::T(0),G::H(0)]),
        ("multi",vec![G::H(0),G::H(0),G::H(0),G::H(0)]),
    ]{
        let split=ops.len()/2;
        let c=CpsCore::circuit(1,&ops[..split]).unwrap().then(&CpsCore::circuit(1,&ops[split..]).unwrap()).unwrap();
        let mut g=Anf::from([0]);let y=*c.guard.ids.iter().find(|&&v|v>=1).unwrap();
        xor_insert(&mut g,1u64<<y);
        cases.push((format!("{name}-guard"),CpsCore::from_derived(c.ps.clone(),g,c.k).unwrap()));
        if name=="hh"{cases.push(("adjoint".into(),c.adjoint().unwrap()));}
        cases.push((name.into(),c));
    }
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    let y=ps.v.get_fresh_var();
    cases.push(("negative-scale".into(),CpsCore::canonical(ps.clone(),Anf::from([0])).unwrap()));
    cases.push(("fixed-guard".into(),CpsCore::canonical(ps.clone(),Anf::from([1u64<<y])).unwrap()));
    cases.push(("zero-guard".into(),CpsCore::canonical(ps.clone(),Anf::new()).unwrap()));
    // Same output fibre, nonzero path count but exact cancellation.
    ps.p.add_term(vec![y],quprs::PhaseCoeff::HALF);ps.v.get_fresh_var();
    cases.push(("cancellation".into(),CpsCore::canonical(ps.clone(),Anf::from([0])).unwrap()));
    // Nonzero sqrt(2) coefficient: 1+omega with independent free path.
    ps.p.terms.clear();ps.p.add_term(vec![y],quprs::PhaseCoeff::new_constant(quprs::Rational::new(1,8)));
    cases.push(("radical".into(),CpsCore::canonical(ps,Anf::from([0])).unwrap()));
    let mut manifest=String::from("case\troute\tk\th\tsteps\tprimary\tvars\tclauses\tphase\ta\tb\n");
    for (name,start) in &cases{
        let mut residual=start.clone();let mut receipts=Vec::new();
        for _ in 0..16{let Some((next,r))=residual.rr_step() else{break;};receipts.push(r);residual=next;}
        core_rr_equal(start,&residual);
        let replay=start.replay_rr(&receipts).unwrap();assert_eq!(replay.k,residual.k);
        for (route,c,steps) in [("raw",start,0),("residual",&residual,receipts.len())]{
            let (cnf,phase,primary,k)=c.wmc_norm_plan().unwrap();
            let h=c.guard.ids.len()-c.n();
            let (a,b)=core_norm_numerator(c);
            let file=dir.join(format!("{name}-{route}.cnf"));
            let mut data=format!("p cnf {} {}\n",cnf.vars,cnf.clauses.len());
            for row in &cnf.clauses{for lit in row{data.push_str(&format!("{lit} "));}data.push_str("0\n");}
            std::fs::write(file,data).unwrap();
            let phase=phase.iter().map(ToString::to_string).collect::<Vec<_>>().join(",");
            manifest.push_str(&format!("{name}\t{route}\t{k}\t{h}\t{steps}\t{primary}\t{}\t{}\t{phase}\t{a}\t{b}\n",cnf.vars,cnf.clauses.len()));
        }
    }
    assert_eq!(cases.len(),14);
    std::fs::write(dir.join("manifest.tsv"),manifest).unwrap();
    println!("CPS_CORE_WMC_EXPORT cases=14 arms=28");
}

// CORE-4: direct HSL -> canonical CPS, using the existing admitted AqState
// parser for coefficient/normalization checks. No family/ket enumeration
// in lowering. The outer label is a free input, not a path variable.
fn core_hsl_lt(bits:&[u32],bound:u64)->Option<Anf>{
    if bound>=1u64<<bits.len(){return Some(Anf::from([0]));}
    let mut lt=Anf::new();
    for (i,&v) in bits.iter().enumerate(){
        let bit=core_bit(v)?;
        if bound>>i&1!=0{
            lt=mul_anf(&Anf::from([bit]),&lt)?;
            xor_insert(&mut lt,0);xor_insert(&mut lt,bit);
        }else{lt=mul_anf(&Anf::from([0,bit]),&lt)?;}
    }
    Some(lt)
}
fn core_hsl_fresh(ps:&mut PathSum)->Option<u32>{
    if ps.v.next_id>=63{return None;}
    Some(ps.v.get_fresh_var())
}
// A fixed ket or a fixed ket plus its complementary part in one
// coordinate cube. Shared coordinates give exactly one support fibre.
// Each signed numerator is a path multiplicity with phase 0 or pi.
fn core_hsl_state(a:&AqState,n:usize,base:Vec<CoreBool>)->Option<CpsCore>{
    core_hsl_state_flat(a,n,base.clone()).or_else(||core_hsl_state_factored(a,n,base))
}
fn core_hsl_state_flat(a:&AqState,n:usize,base:Vec<CoreBool>)->Option<CpsCore>{
    if base.len()!=a.n||n>5||a.k>32{return None;}
    let [first,rest @ ..]=a.terms.as_slice() else{return None;};
    let AqPattern::Fixed(fixed)=first.pattern else{return None;};
    let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
    ps.f=quprs::pathsum::BooleanState::new(a.n);ps.f.functions=base;
    let mut equal=Anf::from([0]);
    if let [second]=rest{
        let AqPattern::Except{offset,width,excluded,outside}=second.pattern else{return None;};
        if fixed!=outside|(excluded<<offset){return None;}
        for i in offset..offset+width{
            let v=core_hsl_fresh(&mut ps)?;
            ps.f.functions[i].insert(vec![v]);
            equal=mul_anf(&equal,&Anf::from([0,core_bit(v)?]))?;
        }
    }else if !rest.is_empty(){return None;}
    let mag=a.terms.iter().map(|t|t.signed.unsigned_abs()).max()?;
    if mag==0{return None;}
    let r=(64-(mag-1).leading_zeros()) as usize;
    let mut count=Vec::new();for _ in 0..r{count.push(core_hsl_fresh(&mut ps)?);}
    let high=mul_anf(&equal,&core_hsl_lt(&count,first.signed.unsigned_abs())?)?;
    let mut guard=high;let mut other=equal.clone();xor_insert(&mut other,0);
    if let [second]=rest{
        let low=mul_anf(&other,&core_hsl_lt(&count,second.signed.unsigned_abs())?)?;
        for m in low{xor_insert(&mut guard,m);}
    }
    // A Boolean sign lifted at phase 1/2 is XOR, since 2*(1/2)=0 mod 1.
    for (i,t) in a.terms.iter().enumerate(){
        if t.signed<0{
            let select=if i==0{&equal}else{&other};
            for &m in select{
                let mono=(0..63u32).filter(|&v|m&(1u64<<v)!=0).collect();
                ps.p.add_term(mono,quprs::PhaseCoeff::HALF);
            }
        }
    }
    // Source normalization is canonical: if fewer coordinates than
    // source k, add fixed paths; if more, add free paths to compensate.
    let h=ps.v.path_vars.len().checked_sub(n)?;
    for _ in 0..h.abs_diff(a.k){
        let v=core_hsl_fresh(&mut ps)?;
        if h<a.k{guard=mul_anf(&guard,&Anf::from([0,core_bit(v)?]))?;}
    }
    CpsCore::canonical(ps,guard)
}

// m < bound iff for each zero bit i in bound-1, it is not the
// case that m_i and all higher one bits of bound-1 are set.
// These are monotone forbidden monomials (two-term ANF clauses),
// not expanded lexicographic prefix polynomials.
fn core_hsl_bound_factors(bits:&[u32],bound:u64)->Option<Vec<Anf>>{
    if bits.len()>=63||bound==0||bound>1u64<<bits.len(){return None;}
    let b=bound-1;
    let mut higher=0u64;let mut factors=Vec::new();
    for (i,&v) in bits.iter().enumerate().rev(){
        let bit=core_bit(v)?;
        if b>>i&1!=0{higher|=bit;}
        else{factors.push(Anf::from([0,higher|bit]));}
    }
    Some(factors)
}
// Same canonical source contract, same count bits and signs. Only
// retain already supported conjunctions when old flat ingress overflows.
// For conditional clause g = 1 xor M, E => g is 1 xor E*M.
fn core_hsl_state_factored(a:&AqState,n:usize,base:Vec<CoreBool>)->Option<CpsCore>{
    if base.len()!=a.n||n>5||a.k>32{return None;}
    let [first,rest @ ..]=a.terms.as_slice() else{return None;};
    let AqPattern::Fixed(fixed)=first.pattern else{return None;};
    let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
    ps.f=quprs::pathsum::BooleanState::new(a.n);ps.f.functions=base;
    let mut equal=Anf::from([0]);
    if let [second]=rest{
        let AqPattern::Except{offset,width,excluded,outside}=second.pattern else{return None;};
        if fixed!=(outside|(excluded<<offset)){return None;}
        for i in offset..offset+width{
            let v=core_hsl_fresh(&mut ps)?;
            ps.f.functions[i].insert(vec![v]);
            equal=mul_anf(&equal,&Anf::from([0,core_bit(v)?]))?;
        }
    }else if !rest.is_empty(){return None;}
    let mag=a.terms.iter().map(|t|t.signed.unsigned_abs()).max()?;
    if mag==0{return None;}
    let r=(64-(mag-1).leading_zeros()) as usize;
    let mut count=Vec::new();for _ in 0..r{count.push(core_hsl_fresh(&mut ps)?);}
    let mut other=equal.clone();xor_insert(&mut other,0);
    let mut factors=Vec::new();
    // The stricter interval is conditional; the larger interval is
    // unconditional. This is equivalent to the two disjoint branches
    // and avoids redundant clauses and large conjunctions.
    factors.extend(core_hsl_bound_factors(&count,mag)?);
    for (i,t) in a.terms.iter().enumerate(){
        let select=if i==0{&equal}else{&other};
        if t.signed.unsigned_abs()!=mag{
            for mut g in core_hsl_bound_factors(&count,t.signed.unsigned_abs())?{
                xor_insert(&mut g,0);
                let mut implication=mul_anf(select,&g)?;
                xor_insert(&mut implication,0);
                factors.push(implication);
            }
        }
        if t.signed<0{
            for &m in select{
                let mono=(0..63u32).filter(|&v|m&(1u64<<v)!=0).collect();
                ps.p.add_term(mono,quprs::PhaseCoeff::HALF);
            }
        }
    }
    let h=ps.v.path_vars.len().checked_sub(n)?;
    for _ in 0..h.abs_diff(a.k){
        let v=core_hsl_fresh(&mut ps)?;
        if h<a.k{factors.push(Anf::from([0,core_bit(v)?]));}
    }
    // Same canonical padding as flat ingress, not a new scale parameter.
    let k=i32::try_from(ps.v.path_vars.len().checked_sub(n)?).ok()?;
    CpsCore::from_factors(ps,factors,k)
}
fn core_hsl_lower(src:&str)->Option<CpsCore>{
    let Some((prefix,domain))=src.trim_end().rsplit_once(" : ")else{
        let a=aq_parse(src)?;
        let AqPattern::Fixed(fixed)=a.terms.first()?.pattern else{return None;};
        let base=(0..a.n).map(|i|if fixed>>i&1!=0{CoreBool::from_iter([vec![]])}else{CoreBool::default()}).collect();
        return core_hsl_state(&a,0,base);
    };
    // Symbolic admitted outer binder: one unrestricted bit-vector,
    // fixed ket template and optionally a disjoint complementary cube
    // whose excluded value is the very same outer label.
    let (label,wd)=domain.strip_suffix('}')?.strip_prefix('|')?.split_once("|=")?;
    let n:usize=wd.parse().ok()?;
    if label.len()!=1||!label.as_bytes()[0].is_ascii_lowercase()||n==0||n>5{return None;}
    let (header,expr)=prefix.rsplit_once('\n')?;
    let mut parts=expr.strip_prefix('{')?.split(" + ");
    let (coef,ket)=parts.next()?.split_once(' ')?;
    let fixed=ket.strip_prefix('|')?.strip_suffix('>')?;
    let mut base=Vec::new();
    for ch in fixed.chars(){
        match ch{
            '0'=>base.push(CoreBool::default()),
            '1'=>base.push(CoreBool::from_iter([vec![]])),
            c if c as u8==label.as_bytes()[0]&&c.is_ascii()=>{
                for i in 0..n{base.push(CoreBool::from_iter([vec![i as u32]]));}
            },
            _=>return None,
        }
    }
    if base.len()>16{return None;}
    let zero="0".repeat(n);
    let mut canonical=format!("{{{coef} |{}>",fixed.replace(label,&zero));
    if let Some(part)=parts.next(){
        let (coef2,rest)=part.split_once(" ∑ ")?;
        let (binding,ket)=rest.split_once(" |")?;
        let (decl,except)=binding.split_once(", ")?;
        let (inner,width)=decl.strip_prefix('|')?.split_once("|=")?;
        if inner.len()!=1||!inner.as_bytes()[0].is_ascii_lowercase()||inner==label||width.parse::<usize>().ok()?!=n||except!=format!("{inner}≠{label}"){return None;}
        let (left,right)=ket.strip_suffix('>')?.split_once(inner)?;
        if fixed!=format!("{left}{label}{right}")||right.contains(inner)||left.contains(inner){return None;}
        // Validate one zero template with the existing parser. Syntactic
        // certificate above proves every other column is a bit translation
        // of this template, so support, multiplicity and norm are invariant.
        canonical.push_str(&format!(" + {coef2} ∑ |{inner}|={n}, {inner}≠{zero} |{}{inner}{}>",left.replace(label,&zero),right.replace(label,&zero)));
    }
    if parts.next().is_some(){return None;}
    canonical.push('}');
    let a=aq_parse(&format!("{header}\n{canonical}"))?;
    core_hsl_state(&a,n,base)
}
// The source oracle deliberately enumerates only in this independent
// bounded test, never in the CPS builder. Compare full signed amplitudes,
// not just support or normalization.
fn core_hsl_check(src:&str)->CpsCore{
    let c=core_hsl_lower(src).expect("direct CPS admission");
    let (n,states)=aq_family(src).expect("independent admitted reference");
    assert_eq!(c.n(),n);assert_eq!(states.len(),1usize<<n);
    let actual=core_matrix(&c);
    for (x,a) in states.iter().enumerate(){
        assert_eq!(c.q(),a.n);
        let d=c.k-i32::try_from(a.k).unwrap();
        assert!(d>=0&&d%2==0);
        for (z,row) in actual.iter().enumerate(){
            let expected=a.terms.iter().filter(|t|aq_match(&t.pattern,z as u64)).map(|t|t.signed).sum::<i64>();
            assert_eq!(row[x],[expected*(1i64<<(d/2)),0,0,0]);
        }
    }
    c
}
#[test]
fn hoare_cps_core_source_lowering(){
    let root=std::path::PathBuf::from(std::env::var("CPS_CORE_SOURCE_DIR").unwrap());
    let mut predicates=0;let mut columns=0;let mut entries=0;
    for (case,pre,post,qasm) in AQ_SOURCES{
        let folder=match case{"bv03"=>"BV","grover03"=>"Grover","mogrover03"=>"MOGrover",_=>unreachable!()};
        let folder=root.join("benchmarks").join("all").join(folder).join("03");
        for (file,embedded) in [("pre.hsl",pre),("post.hsl",post),("circuit.qasm",qasm)]{
            let path=folder.join(file);
            let actual=std::fs::read_to_string(&path).unwrap_or_else(|e|panic!("pinned source read {}: {e}",path.display()));
            assert_eq!(actual,embedded,"pinned source mismatch: {}",path.display());
            println!("CPS_CORE_SOURCE_FILE case={case} file={file} bytes={} verified=true",actual.len());
        }
        let a=core_hsl_check(pre);let b=core_hsl_check(post);
        for c in [&a,&b]{
            assert_eq!(c.k,(c.guard.ids.len()-c.n()) as i32);
            predicates+=1;columns+=1usize<<c.n();entries+=(1usize<<c.n())*(1usize<<c.q());
        }
        println!("CPS_CORE_SOURCE case={case} free={} output={} pre_h={} post_h={} post_guard_terms={} materialized_columns=0",a.n(),a.q(),a.guard.ids.len()-a.n(),b.guard.ids.len()-b.n(),b.guard.extra.len());
        if case=="bv03"{
            let (ops,n)=quprs::qasm::parse_qasm_str_source_pinned(qasm).unwrap();
            assert_eq!(ops,factor_source_ops(qasm,n));
            let u=CpsCore::circuit(n,&ops).unwrap();
            // A and B are genuine rectangular CPS, not square placeholders.
            let v=a.then(&u).unwrap().then(&b.adjoint().unwrap()).unwrap();
            assert_eq!((v.n(),v.q()),(0,0));
            let target=core_norm_numerator(&v);
            assert_eq!(target,(1i64<<v.k,0));
            let mut residual=v.clone();let mut receipts=Vec::new();
            for _ in 0..16{let Some((next,r))=residual.rr_step() else{break;};receipts.push(r);residual=next;}
            assert!(!receipts.is_empty());core_rr_equal(&v,&residual);
            assert!(v.replay_rr(&receipts).is_some());
            // Mutated source, still normalized, distinct target; actual
            // composition must have zero overlap, not a support shortcut.
            let wrong=post.replace("|1011>","|0011>");
            assert_ne!(wrong,post);
            let bad=a.then(&u).unwrap().then(&core_hsl_lower(&wrong).unwrap().adjoint().unwrap()).unwrap();
            assert_eq!(core_norm_numerator(&bad),(0,0));
            println!("CPS_CORE_SOURCE_BV composition=PASS relative_target=REFUTED rr_steps={}",receipts.len());
        }
    }
    let (_,_,post,_)=AQ_SOURCES[2];
    assert!(core_hsl_lower(&post.replace("i≠s","i≠000")).is_none());
    assert!(core_hsl_lower(&post.replace("|s|=3","|s|=6")).is_none());
    assert!(core_hsl_lower(&post.replace("aH := 11","aH := 12")).is_none());
    assert_eq!((predicates,columns,entries),(6,20,4192));
    println!("CPS_CORE_SOURCE_SUMMARY predicates={predicates} oracle_columns={columns} oracle_entries={entries} rejection_controls=3 symbolic_families=2 bv_composition=PASS");
}

// CORE-5 entry: composition with a circuit is the existing native ket
// gate application, not construction of another circuit IR. In particular
// the input signature of a source predicate remains unchanged.
// Reuse the original one-gate admission, but bound total live path IDs
// and native polynomials instead of the early synthetic <=10 H cap.
impl CpsCore {
    fn then_circuit(&self,ops:&[G])->Option<Self>{
        if !self.valid()||ops.len()>128||self.q()==0{return None;}
        let mut ps=self.ps.clone();ps.set_auto_reduce(false);
        let mut k=self.k;
        for g in ops{
            if !admitted(self.q(),std::slice::from_ref(g)){return None;}
            let h=matches!(g,G::H(_));
            if h&&ps.v.next_id>=63{return None;}
            let before=ps.v.path_vars.len();
            g.apply(&mut ps,false);
            if ps.v.path_vars.len()!=before+usize::from(h)||!core_terms_ok(&ps){return None;}
            if h{k=k.checked_add(1)?;}
        }
        let guard=NativeGuardFrame::from_factors(&ps,self.guard.factors().cloned().collect())?;
        Self::from_frame(ps,guard,k)
    }
}
// A source-only obligation admission experiment, not an alternate
// verifier. Test the actual three variants and retain explicit UNKNOWN
// at the first existing resource/admission boundary.
#[test]
fn hoare_cps_core_source_obligation_admission(){
    let root=std::path::PathBuf::from(std::env::var("CPS_CORE_SOURCE_DIR").unwrap());
    let mut cases=0;let mut ready=0;let mut blocked=0;let mut gate_ok=0;let mut exact=0;
    let export=std::env::var_os("CPS_CORE_DECISION_DIR").map(std::path::PathBuf::from);
    if let Some(d)=&export{std::fs::create_dir_all(d).unwrap();}
    let mut manifest=String::from("case\tvariant\tmode\tlabel\tinitial\tn\tk\th\tsteps\tstatus\tprimary\tvars\tclauses\tphase\toracle_a\toracle_b\toracle_k\texpected\trr_ns\tencode_ns\n");
    for (case,pre,post,qasm) in AQ_SOURCES{
        let family=match case{"bv03"=>"BV","grover03"=>"Grover","mogrover03"=>"MOGrover",_=>unreachable!()};
        let folder=root.join("benchmarks").join("all").join(family).join("03");
        for (file,embedded) in [("pre.hsl",pre),("post.hsl",post),("circuit.qasm",qasm)]{
            assert_eq!(std::fs::read_to_string(folder.join(file)).unwrap(),embedded);
        }
        let a=core_hsl_lower(pre).unwrap();
        let (ops,n)=quprs::qasm::parse_qasm_str_source_pinned(qasm).unwrap();
        assert_eq!(ops,factor_source_ops(qasm,n));
        let ua=a.then_circuit(&ops).expect("native gate composition");
        let h=ops.iter().filter(|g|matches!(g,G::H(_))).count();
        assert_eq!(ua.k,a.k+h as i32);assert_eq!((ua.n(),ua.q()),(a.n(),a.q()));
        assert_eq!(ua.guard.factors().collect::<Vec<_>>(),a.guard.factors().collect::<Vec<_>>());
        gate_ok+=1;
        // Cross-check specialized circuit composition with the already
        // admitted generic operation where the original cap permits it.
        if let Some(u)=CpsCore::circuit(n,&ops){
            let direct=a.then(&u).unwrap();core_rr_equal(&direct,&ua);
        }
        // Independent dense *gate* oracle and existing finite HSL reference,
        // used only to certify expected results for this source cohort.
        let (_,pre_ref)=aq_family(pre).unwrap();
        let variants=[
            ("source",post.to_owned(),true),
            ("relative",if case=="bv03"{post.replace("|1011>","|0011>")}else{post.replace("aH := 11 /","aH := -11 /")},false),
            ("global",if case=="bv03"{post.replace("c1 := 1","c1 := -1")}else{post.replace("aH := 11 /","aH := -11 /").replace("aL := -1 /","aL := 1 /")},true),
        ];
        for (variant,src,expected) in variants{
            let b=core_hsl_lower(&src).unwrap();
            let (_,post_ref)=aq_family(&src).unwrap();
            // StateSet semantics: check every input against every target
            // in the oracle, not merely the same index. In this cohort
            // the family has disjoint classical label supports.
            let mut all=true;
            let oracle_k=h+post_ref[0].k;
            let mut oracle_mass=[0;4];
            for x in &pre_ref{
                let state=dense_state(n,&ops,aq_fixed_input(x).unwrap());
                let mut any=false;
                for t in &post_ref{
                    let mut dot=[0;4];
                    for (z,v) in state.iter().enumerate(){
                        let coeff=t.terms.iter().filter(|p|aq_match(&p.pattern,z as u64)).map(|p|p.signed).sum::<i64>();
                        dot=add(dot,v.map(|q|q*coeff));
                    }
                    let norm=rus_mul(dot,rus_conj(dot));
                    assert_eq!(h+t.k,oracle_k);
                    oracle_mass=add(oracle_mass,norm);
                    any|=norm==[1i64<<(h+t.k),0,0,0];
                }
                all&=any;
            }
            assert_eq!(all,expected,"independent source oracle {case}/{variant}");
            assert_eq!(oracle_mass[2],0);assert_eq!(oracle_mass[1],-oracle_mass[3]);
            cases+=1;
            let Some(bd)=b.adjoint() else{
                blocked+=1;
                println!("CPS_CORE_OBLIGATION case={case} variant={variant} oracle={expected} stage=adjoint verdict=UNKNOWN ua_h={} ua_phase={} post_guard={} post_h={}",ua.guard.ids.len()-ua.n(),ua.ps.p.terms.len(),b.guard.extra.len(),b.guard.ids.len()-b.n());
                continue;
            };
            let Some(v)=ua.then(&bd) else{
                blocked+=1;
                println!("CPS_CORE_OBLIGATION case={case} variant={variant} oracle={expected} stage=composition verdict=UNKNOWN ua_h={} ua_phase={} adjoint_guard={}",ua.guard.ids.len()-ua.n(),ua.ps.p.terms.len(),bd.guard.factors().map(|g|g.len()).sum::<usize>());
                continue;
            };
            let Some((cnf,_,primary,_))=v.wmc_norm_plan() else{
                blocked+=1;
                println!("CPS_CORE_OBLIGATION case={case} variant={variant} oracle={expected} stage=wmc-admission verdict=UNKNOWN overlap_h={}",v.guard.ids.len()-v.n());
                continue;
            };
            ready+=1;
            if let Some(dir)=&export{
                // All columns are normalized by the admitted HSL parser and
                // unitary source gate construction. For each free label s,
                // UA's first n output bits are deterministic functions of s;
                // B's first n bits are exactly its free label t. Consequently
                // at most one target can overlap per input, even without
                // assuming the same-index pairing. The sum of overlaps is a
                // valid universal ray-membership criterion for this cohort.
                let label=core_label_support(&ua,&b);
                if label{
                    assert_eq!(v.n(),v.q());
                    core_export_decision(dir,case,variant,&v,
                        (oracle_mass[0],oracle_mass[1],oracle_k),expected,&mut manifest);
                }else{
                    println!("CPS_CORE_LABEL_SUPPORT case={case} variant={variant} status=UNSUPPORTED");
                }
            }
            // Only assert a definite result here for the already bounded
            // scalar BV witness. No dense enumeration of large CPS.
            if case=="bv03"{
                let norm=core_norm_numerator(&v);
                assert_eq!(norm,(if expected{1i64<<v.k}else{0},0));
                exact+=1;
            }
            println!("CPS_CORE_OBLIGATION case={case} variant={variant} oracle={expected} stage=ready verdict=NOT_RUN overlap_h={} overlap_guard_terms={} guard_factors={} primary={primary} vars={} clauses={}",v.guard.ids.len()-v.n(),v.guard.factors().map(|g|g.len()).sum::<usize>(),v.guard.factors().count(),cnf.vars,cnf.clauses.len());
        }
    }
    assert_eq!((cases,gate_ok,exact),(9,3,3));
    assert_eq!(ready+blocked,cases);
    if let Some(dir)=export{
        assert_eq!(ready,9,"source cohort admission regression");
        assert_eq!(manifest.lines().count(),28,"all source label certificates required");
        std::fs::write(dir.join("manifest.tsv"),manifest).unwrap();
        println!("CPS_CORE_DECISION_EXPORT cases=9 arms=27 label_certificates=9");
    }
    println!("CPS_CORE_OBLIGATION_SUMMARY cases={cases} gate_composition={gate_ok} bv_exact={exact} ready={ready} blocked={blocked}");
}


#[test]
fn hoare_cps_core_factored_guard(){
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    let ids=(0..10).map(|_|ps.v.get_fresh_var()).collect::<Vec<_>>();
    ps.v.get_fresh_var(); // independent integration path
    let factor=|vs:&[u32]|->Anf{
        (0..1usize<<vs.len()).map(|m|vs.iter().enumerate().fold(0u64,|acc,(i,&v)|acc|((((m>>i)&1) as u64)<<v))).collect()
    };
    let f=factor(&ids[..5]);let g=factor(&ids[5..]);
    assert_eq!(f.len(),32);assert_eq!(g.len(),32);assert!(mul_anf(&f,&g).is_none());
    let k=(ps.v.path_vars.len()-ps.v.num_qubits) as i32;
    let c=CpsCore::from_factors(ps,vec![f,g],k).unwrap();
    assert!(!c.guard.conjuncts.is_empty());assert!(c.guard.compact(&c.ps).is_none());
    assert_eq!(core_norm_numerator(&c),(8,0));
    let (next,r)=c.rr_step().unwrap();
    assert_eq!(r.native.rule,GuardedRule::Elim);assert_eq!(next.k,9);
    core_rr_equal(&c,&next);assert!(c.replay_rr(&[r.clone()]).is_some());
    let mut bad=r.clone();xor_insert(&mut bad.native.after.conjuncts[0],0);
    assert!(c.replay_rr(&[bad]).is_none());
    let (cnf,_,primary,_)=c.wmc_norm_plan().unwrap();assert_eq!(primary,23);assert!(cnf.vars>=primary);
    println!("CPS_CORE_FACTORED_GUARD matrix=PASS native_rr=PASS replay_mutant=REJECTED wmc_plan=PASS");
}


// Source-independent sufficient support certificate for an admitted pair
// of normalized CPS column families. This is not a general StateSet solver.
fn core_label_support(ua:&CpsCore,b:&CpsCore)->bool{
    let n=b.n();
    ua.valid()&&b.valid()&&ua.n()==n&&ua.q()==b.q()&&n<=b.q()&&
    (0..n).all(|j|
        b.ps.f.functions[j]==CoreBool::from_iter([vec![j as u32]])&&
        ua.ps.f.functions[j].iter().all(|m|m.iter().all(|&v|(v as usize)<n)))
}
// Sufficient algebraic terminal for the already certified normalized
// source obligation. No finite input or path enumeration in decision.
fn core_ray_rr_terminal(c:&CpsCore)->Option<&'static str>{
    if c.guard.factors().any(|g|g.is_empty()){return Some("REFUTED");}
    if c.guard.ids.len()!=c.n(){return None;}
    if c.k>0{return Some("REFUTED");}
    if c.k!=0{return None;}
    Some(if c.guard.factors().all(|g|g==&Anf::from([0])){"PROVED"}else{"REFUTED"})
}
fn core_export_decision(dir:&std::path::Path,case:&str,variant:&str,start:&CpsCore,
                        oracle:(i64,i64,usize),expected:bool,manifest:&mut String){
    // Store a deterministic serialization of the actual shared initial
    // CPS fields. All three policy arms refer to this same object.
    let key=format!("{case}-{variant}");
    let snap=guarded_snapshot(&start.ps,start.n(),&start.guard).unwrap();
    let initial=format!("{key}.initial.txt");
    std::fs::write(dir.join(&initial),format!("k={}\n{snap:?}\n",start.k)).unwrap();
    let begin=std::time::Instant::now();
    let mut residual=start.clone();let mut receipts=Vec::new();
    for _ in 0..32{
        let Some((next,r))=residual.rr_step() else{break;};
        receipts.push(r);residual=next;
    }
    let rr_ns=begin.elapsed().as_nanos();
    let replay=start.replay_rr(&receipts).unwrap();
    assert_eq!(replay.k,residual.k);
    assert_eq!(guarded_snapshot(&replay.ps,replay.n(),&replay.guard),
               guarded_snapshot(&residual.ps,residual.n(),&residual.guard));
    std::fs::write(dir.join(format!("{key}.rr.txt")),format!("{receipts:?}\n")).unwrap();
    let terminal=core_ray_rr_terminal(&residual);
    for mode in ["rr","wmc","hybrid"]{
        let (c,steps,time)=if mode=="wmc"{(start,0,0)}else{(&residual,receipts.len(),rr_ns)};
        let mut status=if mode=="wmc"{"READY"}else if let Some(t)=terminal{t}else if mode=="rr"{"UNKNOWN"}else{"READY"};
        let mut primary=0;let mut vars=0;let mut clauses=0;let mut phase=String::new();let mut encode_ns=0;
        if status=="READY"{
            let t=std::time::Instant::now();
            if let Some((cnf,d,p,k))=c.wmc_norm_plan(){
                assert_eq!(k,c.k);primary=p;vars=cnf.vars;clauses=cnf.clauses.len();
                phase=d.iter().map(ToString::to_string).collect::<Vec<_>>().join(",");
                let mut data=format!("p cnf {vars} {clauses}\n");
                for row in cnf.clauses{for l in row{data.push_str(&format!("{l} "));}data.push_str("0\n");}
                encode_ns=t.elapsed().as_nanos();
                std::fs::write(dir.join(format!("{key}-{mode}.cnf")),data).unwrap();
            }else{status="UNKNOWN";}
        }
        let h=c.guard.ids.len()-c.n();let n=c.n();let k=c.k;
        let (a,b,ok)=oracle;
        let expect=if expected{"PROVED"}else{"REFUTED"};
        manifest.push_str(&format!("{case}\t{variant}\t{mode}\tPASS\t{initial}\t{n}\t{k}\t{h}\t{steps}\t{status}\t{primary}\t{vars}\t{clauses}\t{phase}\t{a}\t{b}\t{ok}\t{expect}\t{time}\t{encode_ns}\n"));
    }
    println!("CPS_CORE_LABEL_SUPPORT case={case} variant={variant} status=PASS");
}


// Timed source-only worker: no dense oracle, no precomputed obligations,
// no other policy arm. The driver includes this process and GPMC in the
// same outer deadline as AutoQ. Prior gates independently qualify semantics.
#[test]
fn hoare_cps_core_matched_worker(){
    let dir=std::path::PathBuf::from(std::env::var("CPS_CORE_MATCHED_DIR").unwrap());
    let mode=std::env::var("CPS_CORE_MATCHED_MODE").unwrap();
    assert!(["rr","wmc","hybrid","wmc-dag","hybrid-dag"].contains(&mode.as_str()));
    let dag=mode.ends_with("-dag");
    let policy=mode.strip_suffix("-dag").unwrap_or(&mode);
    let mut stage="source-read";
    let run=(||->Option<()>{
        let pre=std::fs::read_to_string(dir.join("pre.hsl")).ok()?;
        let post=std::fs::read_to_string(dir.join("post.hsl")).ok()?;
        let src=std::fs::read_to_string(dir.join("circuit.qasm")).ok()?;
        let t=std::time::Instant::now();
        stage="pre-lowering";let a=core_hsl_lower(&pre)?;
        stage="post-lowering";let b=core_hsl_lower(&post)?;
        stage="qasm-parse";let (ops,n)=quprs::qasm::parse_qasm_str_source_pinned(&src).ok()?;
        if n!=a.q()||n!=b.q(){return None;}
        stage="native-gate-composition";let ua=a.then_circuit(&ops)?;
        stage="label-certificate";if !core_label_support(&ua,&b){return None;}
        stage="adjoint";let bd=b.adjoint()?;
        stage="composition";let mut c=ua.then(&bd)?;
        let build_ns=t.elapsed().as_nanos();
        stage="initial-snapshot";let snap=guarded_snapshot(&c.ps,c.n(),&c.guard)?;
        std::fs::write(dir.join("initial.txt"),format!("k={}\n{snap:?}\n",c.k)).ok()?;
        let initial_h=c.guard.ids.len()-c.n();
        let t=std::time::Instant::now();
        let mut steps=0;
        if policy!="wmc"{
            for _ in 0..32{
                let Some((next,_))=c.rr_step() else{break;};
                c=next;steps+=1;
            }
        }
        let rr_ns=t.elapsed().as_nanos();
        let status=if policy=="wmc"{"READY"}else if let Some(v)=core_ray_rr_terminal(&c){v}else if policy=="rr"{"UNKNOWN"}else{"READY"};
        let mut primary=0;let mut vars=0;let mut clauses=0;let mut phase="-".to_owned();let mut encode_ns=0;
        if status=="READY"{
            let t=std::time::Instant::now();
            // Explicit experimental arm. No silent fallback: a DAG
            // admission failure must be reported as unsupported.
            stage=if dag{"dag-encoder"}else{"flat-encoder"};
            let (cnf,d,p,k)=if dag{c.wmc_norm_factored_plan()}else{c.wmc_norm_plan()}?;
            if k!=c.k{return None;}
            primary=p;vars=cnf.vars;clauses=cnf.clauses.len();
            phase=d.iter().map(ToString::to_string).collect::<Vec<_>>().join(",");
            let mut data=format!("p cnf {vars} {clauses}\n");
            for row in &cnf.clauses{for l in row{data.push_str(&format!("{l} "));}data.push_str("0\n");}
            std::fs::write(dir.join("base.cnf"),data).ok()?;
            encode_ns=t.elapsed().as_nanos();
        }
        println!("CPS_MATCHED_NATIVE {status} {} {} {} {initial_h} {steps} {primary} {vars} {clauses} {phase} {build_ns} {rr_ns} {encode_ns}",c.n(),c.k,c.guard.ids.len()-c.n());
        Some(())
    })();
    if run.is_none(){println!("CPS_MATCHED_NATIVE UNSUPPORTED {stage}");}
}


// Reuse the existing generic Boolean FactorPilot DAG implementation only.
// Keep the exact guarded two-copy obligation, primary domain and Z8 phase
// convention. No new reduction or change to PathSum/Guard semantics.
impl CpsCore{
    fn wmc_norm_factored_plan(&self)->Option<(Cnf,[Lit;3],usize,i32)>{
        if !self.valid()||self.n()!=self.q(){return None;}
        let s=compact(&self.ps,self.n())?;
        let primary=s.n.checked_add(s.h.checked_mul(2)?)?;
        if primary>63{return None;}
        // Exact sign-only fast fragment; other Z8 phases retain the
        // existing general phase adder rather than silently approximating.
        if s.phase.values().any(|&k|k!=4){return None;}
        let gs=self.guard.compact_factors(&self.ps)?;
        let mut f=FactorPilot{c:Cnf::new(primary),gates:BTreeMap::new(),polys:BTreeMap::new(),work:0};
        let l:Vec<Lit>=(0..s.n+s.h).map(|i|i as Lit+2).collect();
        let r:Vec<Lit>=(0..s.n).map(|i|i as Lit+2)
            .chain((s.n+s.h..primary).map(|i|i as Lit+2)).collect();
        for g in &gs{
            for bits in [&l,&r]{
                let v=f.anf(g,bits,true)?;f.c.enforce(v);
            }
        }
        for o in &s.output{
            let a=f.anf(o,&l,true)?;let b=f.anf(o,&r,true)?;
            let d=f.gate(true,a,b)?;f.c.enforce(-d);
        }
        let sign:Anf=s.phase.keys().copied().collect();
        let a=f.anf(&sign,&l,true)?;let b=f.anf(&sign,&r,true)?;
        let d=f.gate(true,a,b)?;
        if !f.bounded(){return None;}
        Some((f.c,[ZERO,ZERO,d],primary,self.k))
    }
}
#[test]
fn hoare_cps_core_encoding_ab(){
    let root=std::path::PathBuf::from(std::env::var("CPS_CORE_SOURCE_DIR").unwrap());
    let dir=std::path::PathBuf::from(std::env::var("CPS_CORE_ENCODING_DIR").unwrap());
    std::fs::create_dir_all(&dir).unwrap();
    let mut manifest=String::from("case\tvariant\troute\tencoding\tn\tk\th\tsteps\tprimary\tvars\tclauses\tphase\tencode_ns\n");
    let mut count=0;
    for (case,pre,post,qasm) in AQ_SOURCES{
        let family=match case{"bv03"=>"BV","grover03"=>"Grover","mogrover03"=>"MOGrover",_=>unreachable!()};
        let folder=root.join("benchmarks").join("all").join(family).join("03");
        for (file,embedded) in [("pre.hsl",pre),("post.hsl",post),("circuit.qasm",qasm)]{
            assert_eq!(std::fs::read_to_string(folder.join(file)).unwrap(),embedded);
        }
        let a=core_hsl_lower(pre).unwrap();
        let (ops,n)=quprs::qasm::parse_qasm_str_source_pinned(qasm).unwrap();
        assert_eq!(ops,factor_source_ops(qasm,n));
        let ua=a.then_circuit(&ops).unwrap();
        for (variant,src) in [
            ("source",post.to_owned()),
            ("relative",if case=="bv03"{post.replace("|1011>","|0011>")}else{post.replace("aH := 11 /","aH := -11 /")}),
            ("global",if case=="bv03"{post.replace("c1 := 1","c1 := -1")}else{post.replace("aH := 11 /","aH := -11 /").replace("aL := -1 /","aL := 1 /")}),
        ]{
            let b=core_hsl_lower(&src).unwrap();assert!(core_label_support(&ua,&b));
            let start=ua.then(&b.adjoint().unwrap()).unwrap();
            let mut residual=start.clone();let mut receipts=Vec::new();
            for _ in 0..32{let Some((next,r))=residual.rr_step() else{break;};receipts.push(r);residual=next;}
            let replay=start.replay_rr(&receipts).unwrap();
            assert_eq!(replay.k,residual.k);
            assert_eq!(guarded_snapshot(&replay.ps,replay.n(),&replay.guard),guarded_snapshot(&residual.ps,residual.n(),&residual.guard));
            for (route,c,steps) in [("raw",&start,0),("residual",&residual,receipts.len())]{
                let key=format!("{case}-{variant}-{route}");
                let snap=guarded_snapshot(&c.ps,c.n(),&c.guard).unwrap();
                std::fs::write(dir.join(format!("{key}.ir")),format!("k={}\n{snap:?}\n",c.k)).unwrap();
                for encoding in ["flat","dag"]{
                    let t=std::time::Instant::now();
                    let (cnf,phase,primary,k)=if encoding=="flat"{c.wmc_norm_plan()}else{c.wmc_norm_factored_plan()}.expect("sign-only source encoder admission");
                    let ns=t.elapsed().as_nanos();let h=c.guard.ids.len()-c.n();
                    assert_eq!(k,c.k);assert_eq!(primary,c.n()+2*h);
                    let vars=cnf.vars;let clauses=cnf.clauses.len();
                    let mut data=format!("p cnf {vars} {clauses}\n");
                    for row in &cnf.clauses{for lit in row{data.push_str(&format!("{lit} "));}data.push_str("0\n");}
                    std::fs::write(dir.join(format!("{key}-{encoding}.cnf")),data).unwrap();
                    let phase=phase.iter().map(ToString::to_string).collect::<Vec<_>>().join(",");
                    manifest.push_str(&format!("{case}\t{variant}\t{route}\t{encoding}\t{}\t{k}\t{h}\t{steps}\t{primary}\t{vars}\t{clauses}\t{phase}\t{ns}\n",c.n()));
                    count+=1;
                }
            }
        }
    }
    // Non-real Z8 phase must not enter the sign-only implementation.
    let t=CpsCore::circuit(1,&[G::T(0)]).unwrap();
    assert!(t.wmc_norm_factored_plan().is_none());assert!(t.wmc_norm_plan().is_some());
    assert_eq!(count,36);
    std::fs::write(dir.join("manifest.tsv"),manifest).unwrap();
    println!("CPS_ENCODING_EXPORT arms=36 pairs=18 nonreal_reject=PASS");
}


#[test]
fn hoare_cps_core_heldout_predicates(){
    // Exhaustive comparator semantics for all small bounds; larger
    // actual source magnitudes are tested below across the full counter.
    let mut comparisons=0;
    for r in 0..=7{
        let bits=(0..r as u32).collect::<Vec<_>>();
        for bound in 1..=1u64<<r{
            let factors=core_hsl_bound_factors(&bits,bound).unwrap();
            for m in 0..1u64<<r{
                assert_eq!(factors.iter().all(|g|eval(g,m)),m<bound);
                comparisons+=1;
            }
        }
    }
    let root=std::path::PathBuf::from(std::env::var("CPS_CORE_SOURCE_DIR").unwrap());
    let mut predicates=0;let mut checks=0;
    // Tests only: enumerate counter values at one representative of
    // each relative-coordinate class. Independently verify every actual
    // coordinate/label output, support class and padding constraint.
    for family in ["Grover","MOGrover"]{for width in [4usize,5]{
        let path=root.join("benchmarks").join("all").join(family).join(format!("{width:02}")).join("post.hsl");
        let src=std::fs::read_to_string(path).unwrap();
        let hi=if width==4{251}else{23161};
        let lo=if width==4{13}else{119};
        for (variant,post) in [
            ("source",src.clone()),
            ("relative",src.replace(&format!("aH := {hi} /"),&format!("aH := -{hi} /"))),
            ("global",src.replace(&format!("aH := {hi} /"),&format!("aH := -{hi} /")).replace(&format!("aL := -{lo} /"),&format!("aL := {lo} /"))),
        ]{
            let c=core_hsl_lower(&post).expect("held-out source lowering");
            let n=if family=="MOGrover"{width}else{0};
            let r=if width==4{8}else{15};
            let k=if width==4{16}else{29};
            assert_eq!(c.n(),n);assert_eq!(c.k,k as i32);
            assert_eq!(c.guard.ids.len(),n+k);
            assert!(!c.guard.conjuncts.is_empty());
            let label=(1u64<<n)-1;
            // Both coefficient classes; verify all counter values,
            // including forbidden ones. Padding is zero here.
            for u in [0u64,1]{
                let want=if u==0{hi}else{lo};
                let mut accepted=0;
                for m in 0..1u64<<r{
                    let a=label|(u<<n)|(m<<(n+width));
                    let ok=c.guard.factors().all(|g|eval(g,a));
                    assert_eq!(ok,m<want as u64);
                    if ok{accepted+=1;}
                    checks+=1;
                }
                assert_eq!(accepted,want);
                // Any nonzero padding bit forbids the witness.
                for p in n+width+r..n+k{
                    assert!(!c.guard.factors().all(|g|eval(g,label|(u<<n)|(1u64<<p))));
                }
            }
            // Exhaustive label and relative coordinate checks, not
            // enumeration of prepared states in the verification path.
            let target=if n==0{if width==4{10u64}else{10u64}}else{0};
            for x in 0..1u64<<n{for u in 0..1u64<<width{
                let a=x|(u<<n); // m=0 always accepted
                assert!(c.guard.factors().all(|g|eval(g,a)));
                let on=|m:&Vec<u32>|m.iter().all(|&v|a&(1u64<<v)!=0);
                let z=c.ps.f.functions.iter().enumerate().fold(0u64,|v,(j,p)|v|(((p.iter().filter(|m|on(m)).count()%2) as u64)<<j));
                let expected=if n==0{(target^u)|(1u64<<(c.q()-1))}else{x|((x^u)<<n)|(1u64<<(c.q()-1))};
                assert_eq!(z,expected);
                let phase=c.ps.p.terms.iter().filter(|(m,_)|on(m)).map(|(_,p)|core_phase8(p).unwrap() as usize).sum::<usize>()%8;
                let negative=if u==0{variant!="source"}else{variant!="global"};
                assert_eq!(phase,if negative{4}else{0});
            }}
            println!("CPS_HELDOUT_PREDICATE family={family} width={width} variant={variant} h={k} factors={} terms={} counter_checks={} materialized_columns=0",c.guard.factors().count(),c.guard.factors().map(|g|g.len()).sum::<usize>(),2*(1usize<<r));
            predicates+=1;
        }
    }}
    assert_eq!(predicates,12);
    println!("CPS_HELDOUT_PREDICATE_SUMMARY predicates={predicates} comparisons={comparisons} source_counter_checks={checks}");
}
