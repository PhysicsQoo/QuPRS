
// CORE-1/2 research contract: native PathSum is the sole P/f/variable
// representation. Reuse the existing stable-ID guard frame, with an
// derived signed normalization ledger (not an independent semantic input).
// Canonical CPS scale is 2^(-h/2), h = number of summed variables.
// Rectangular maps are admitted here, not
// passed to the square-only production reducer or gate API.
#[derive(Clone)]
struct CpsCore<F=NativeGuardFrame> {
    ps: PathSum,
    guard: F,
    k: i32,
}
type CoreBool = rustc_hash::FxHashSet<Vec<u32>>;
const CORE_TERMS:usize=256;
// Bounded phase-only admission experiment: MOGrover04 reached 258
// phase terms with max output 27. Keep Boolean and guard caps unchanged.
const CORE_PHASE_TERMS:usize=1024; // bounded MO05 pilot: observed 748 terms
// Preserve the last accepted RR policy separately from construction.
// A larger admitted input may reduce, but must not grow beyond its own
// phase size. This is a bounded policy, not a solver-cost theorem.
const CORE_RR_PHASE_TERMS:usize=512;
fn core_rr_phase_admitted(before:usize,after:usize)->bool{
    after<=CORE_RR_PHASE_TERMS.max(before)
}
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
    ps.p.terms.len()<=CORE_PHASE_TERMS&&ps.f.functions.iter().all(|p|p.len()<=CORE_TERMS)
}
// Keep the same conjunction and existing per-factor bound. Only used
// on factor-count overflow; never expand a successful original layout.
fn core_pack_guard_factors(factors:Vec<Anf>)->Vec<Anf>{
    if factors.len()<=32{return factors;}
    let mut packed=Vec::new();
    let mut acc=Anf::from([0]);
    for g in factors{
        if let Some(next)=mul_anf(&acc,&g){acc=next;}
        else{packed.push(acc);acc=g;}
    }
    packed.push(acc);
    packed
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

use cps_guard_algebra::{GuardMonomial,SparseMono,SparseAnf};
trait CoreGuardStorage:Clone {
    type M:GuardMonomial;
    const ID_LIMIT:u32;
    const PHASE_LIMIT:usize;
    fn ids(&self)->&[u32];
    fn factors_ref(&self)->Vec<&BTreeSet<Self::M>>;
    fn frame_valid(&self,ps:&PathSum)->bool;
    fn from_parts(ps:&PathSum,gs:Vec<BTreeSet<Self::M>>)->Option<Self>;
    fn mono(ids:&[u32])->Option<Self::M>;
    fn mono_ids(m:&Self::M)->Vec<u32>;
}
impl CoreGuardStorage for NativeGuardFrame {
    type M=u64;
    const ID_LIMIT:u32=63;
    const PHASE_LIMIT:usize=CORE_PHASE_TERMS;
    fn ids(&self)->&[u32]{&self.ids}
    fn factors_ref(&self)->Vec<&Anf>{self.factors().collect()}
    fn frame_valid(&self,ps:&PathSum)->bool{self.compact_factors(ps).is_some()}
    fn from_parts(ps:&PathSum,gs:Vec<Anf>)->Option<Self>{Self::from_factors(ps,gs)}
    fn mono(ids:&[u32])->Option<u64>{core_mask(ids)}
    fn mono_ids(m:&u64)->Vec<u32>{(0..63u32).filter(|&id|m&(1u64<<id)!=0).collect()}
}
#[derive(Clone)]
struct SparseGuardFrame {
    ids:Vec<u32>,
    factors:Vec<SparseAnf>,
}
impl CoreGuardStorage for SparseGuardFrame {
    type M=SparseMono;
    // Explicit resource admission, not a machine-word representation limit.
    const ID_LIMIT:u32=512;
    // Scoped admission probe: actual MO05 final phase has 1252 terms.
    const PHASE_LIMIT:usize=1536;
    fn ids(&self)->&[u32]{&self.ids}
    fn factors_ref(&self)->Vec<&SparseAnf>{self.factors.iter().collect()}
    fn frame_valid(&self,ps:&PathSum)->bool{
        let mut ids:Vec<_>=ps.v.path_vars.iter().copied().collect();ids.sort_unstable();
        ids==self.ids&&self.factors.len()<=32&&!self.factors.is_empty()&&
        self.factors.iter().map(|g|g.len()).sum::<usize>()<=4096&&
        self.factors.iter().all(|g|g.len()<=256&&g.iter().all(|m|m.ids().iter().all(|v|ps.v.path_vars.contains(v))))
    }
    fn from_parts(ps:&PathSum,gs:Vec<SparseAnf>)->Option<Self>{
        let mut ids:Vec<_>=ps.v.path_vars.iter().copied().collect();ids.sort_unstable();
        let mut frame=Self{ids,factors:if gs.is_empty(){vec![SparseAnf::from([Self::mono(&[])?])]}else{gs}};
        if !frame.frame_valid(ps){return None;}
        let one=SparseAnf::from([Self::mono(&[])?]);
        if frame.factors.iter().any(|g|g.is_empty()){frame.factors=vec![SparseAnf::new()];}
        else{
            frame.factors.retain(|g|g!=&one);
            if frame.factors.is_empty(){frame.factors.push(one);}
            else if let Some(g)=frame.factors.iter().try_fold(one,|a,g|cps_guard_algebra::guard_mul(&a,g)){frame.factors=vec![g];}
        }
        Some(frame)
    }
    fn mono(ids:&[u32])->Option<SparseMono>{SparseMono::new(ids.to_vec())}
    fn mono_ids(m:&SparseMono)->Vec<u32>{m.ids().to_vec()}
}
fn core_toggle<M:Ord>(p:&mut BTreeSet<M>,m:M){if !p.remove(&m){p.insert(m);}}
// The affine B-adjoint fragment has Z8 coefficients 0 or 4.
// Collect its substituted monomials modulo two before applying them to
// native P. Keep a separate finite scratch budget; final admission
// remains CORE_PHASE_TERMS, and mixed native Z8 coefficients are merged
// using the existing PhasePolynomial::add_term.
const AFFINE_SIGN_SCRATCH:usize=4096;
struct CoreAffineSign<M:Ord>{
    delta:BTreeSet<M>, emitted:usize, peak:usize,
}
impl<M:Ord> CoreAffineSign<M>{
    fn new()->Self{Self{delta:BTreeSet::new(),emitted:0,peak:0}}
    fn push(&mut self,terms:BTreeSet<M>)->Option<()>{
        self.emitted=self.emitted.checked_add(terms.len())?;
        if self.emitted>2_000_000{return None;}
        for m in terms{
            core_toggle(&mut self.delta,m);
            self.peak=self.peak.max(self.delta.len());
            if self.delta.len()>AFFINE_SIGN_SCRATCH{return None;}
        }
        Some(())
    }
}
fn core_merge_affine_sign<F:CoreGuardStorage>(
    p:&mut quprs::pathsum::PhasePolynomial,sign:CoreAffineSign<F::M>
)->Result<String,String>{
    let initial=p.terms.len();
    let distinct=sign.delta.len();
    let cancelled_in_delta=sign.emitted-distinct;
    let mut removed=0usize;let mut added=0usize;let mut changed=0usize;
    let mut peak=initial;
    for v in sign.delta{
        let m=F::mono_ids(&v);
        let before=p.terms.contains_key(&m);
        p.add_term(m.clone(),quprs::PhaseCoeff::HALF);
        match (before,p.terms.contains_key(&m)){
            (true,false)=>removed+=1,
            (false,true)=>added+=1,
            (true,true)=>changed+=1,
            (false,false)=>return Err("sign-merge-invariant".into())
        }
        peak=peak.max(p.terms.len());
    }
    let final_terms=p.terms.len();
    let limit=F::PHASE_LIMIT;
    let detail=format!("initial={initial} emitted={} delta={distinct} delta_cancelled={cancelled_in_delta} delta_peak={} native_removed={removed} native_added={added} native_changed={changed} merge_peak={peak} final_terms={final_terms} limit={limit}",sign.emitted,sign.peak);
    if final_terms>limit{return Err(format!("phase-term-cap {detail}"));}
    Ok(detail)
}

 // Share candidate order, original native RR calls, guard substitution
 // and removed-ID/scale contracts; snapshot storage remains separate.
struct CoreStorageStep<F:CoreGuardStorage>{
    ps:PathSum,guard:F,rule:GuardedRule,removed:Vec<u32>,scale2:u32,
    section:Vec<(u32,BTreeSet<F::M>)>,
}
fn core_guarded_transition<F:CoreGuardStorage>(
    ps:&PathSum,n:usize,g:&F,
    hh:impl Fn(u32)->Option<(u32,BTreeSet<F::M>)>,
    valid_trial:impl Fn(&PathSum)->bool,
)->Option<CoreStorageStep<F>>{
    let factors=g.factors_ref();
    let mut candidates:Vec<_>=ps.get_reducible_vars().into_iter().filter(|&y|
        (y as usize)>=n&&y<F::ID_LIMIT&&factors.iter().all(|f|f.iter().all(|m|!m.contains_id(y)))).collect();
    candidates.sort_unstable();
    for rule in [GuardedRule::Elim,GuardedRule::Omega,GuardedRule::Hh]{
        for &y in &candidates{
            let (extra,mut expected,scale2,section)=match rule{
                GuardedRule::Elim=>(factors.iter().map(|f|(*f).clone()).collect::<Vec<_>>(),vec![y],2,vec![(y,BTreeSet::new())]),
                GuardedRule::Omega=>(factors.iter().map(|f|(*f).clone()).collect::<Vec<_>>(),vec![y],1,vec![(y,BTreeSet::new())]),
                GuardedRule::Hh=>{
                    let Some((target,repl))=hh(y) else{continue;};
                    let Some(extra)=factors.iter().map(|f|cps_guard_algebra::guard_substitute(f,target,&repl)).collect::<Option<Vec<_>>>() else{continue;};
                    (extra,vec![y,target],2,vec![(y,BTreeSet::new()),(target,repl)])
                }
            };
            let mut trial=ps.clone();
            let ok=match rule{
                GuardedRule::Elim=>trial.try_reduce_elim(&[y]),
                GuardedRule::Omega=>trial.try_reduce_omega(&[y]),
                GuardedRule::Hh=>trial.try_reduce_hh(&[y]),
            };
            if !ok{continue;}
            if !valid_trial(&trial){return None;}
            let mut removed:Vec<_>=ps.v.path_vars.difference(&trial.v.path_vars).copied().collect();
            removed.sort_unstable();expected.sort_unstable();
            if removed!=expected||!trial.v.path_vars.is_subset(&ps.v.path_vars){return None;}
            let guard=F::from_parts(&trial,extra)?;
            return Some(CoreStorageStep{ps:trial,guard,rule,removed,scale2,section});
        }
    }
    None
}
fn core_sparse_hh(ps:&PathSum,n:usize,y:u32)->Option<(u32,SparseAnf)>{
    let mut phi=SparseAnf::new();
    for (m,c) in &ps.p.terms{
        if !m.contains(&y){continue;}
        if core_phase8(c)!=Some(4){return None;}
        let term=SparseMono::new(m.iter().copied().filter(|&id|id!=y).collect())?;
        core_toggle(&mut phi,term);
    }
    let target=phi.iter().filter(|m|m.ids().len()==1)
        .map(|m|m.ids()[0]).filter(|&id|phi.iter().all(|m|m.ids()==[id]||!m.contains_id(id))).max()?;
    if (target as usize)<n{return None;}
    phi.remove(&SparseMono::new(vec![target])?);
    Some((target,phi))
}
#[derive(Clone,Debug,PartialEq,Eq)]
struct SparseRrSnapshot{
    n:usize,q:usize,k:i32,next_id:u32,ids:Vec<u32>,
    phase:BTreeMap<Vec<u32>,u8>,output:Vec<BTreeSet<Vec<u32>>>,factors:Vec<SparseAnf>,
}
#[derive(Clone,Debug,PartialEq,Eq)]
struct SparseRrReceipt{
    before:SparseRrSnapshot,after:SparseRrSnapshot,
    rule:GuardedRule,removed:Vec<u32>,scale2:u32,section:Vec<(u32,SparseAnf)>,
}
impl CpsCore<SparseGuardFrame>{
    fn rr_snapshot(&self)->Option<SparseRrSnapshot>{
        if !self.shared_valid(){return None;}
        Some(SparseRrSnapshot{
            n:self.n(),q:self.q(),k:self.k,next_id:self.ps.v.next_id,ids:self.guard.ids.clone(),
            phase:self.ps.p.terms.iter().map(|(m,c)|Some((m.clone(),core_phase8(c)?))).collect::<Option<_>>()?,
            output:self.ps.f.functions.iter().map(|f|f.iter().cloned().collect()).collect(),
            factors:self.guard.factors.clone(),
        })
    }
    fn sparse_rr_step(&self)->Option<(Self,SparseRrReceipt)>{
        let before=self.rr_snapshot()?;
        let step=core_guarded_transition(&self.ps,self.n(),&self.guard,
            |y|core_sparse_hh(&self.ps,self.n(),y),
            |p|p.v.num_qubits==self.n()&&p.f.functions.len()==self.q()&&!p.rr_approximate&&p.rr_tolerance==0.0&&p.v.continuous_vars.is_empty())?;
        if !core_rr_phase_admitted(self.ps.p.terms.len(),step.ps.p.terms.len()){return None;}
        let k=self.k.checked_sub(i32::try_from(step.scale2).ok()?)?;
        let next=Self{ps:step.ps,guard:step.guard,k};
        let after=next.rr_snapshot()?;
        if after.ids.len()>=before.ids.len()||after.n!=before.n||after.q!=before.q{return None;}
        let receipt=SparseRrReceipt{before,after,rule:step.rule,removed:step.removed,scale2:step.scale2,section:step.section};
        Some((next,receipt))
    }
    fn replay_sparse_rr(&self,rs:&[SparseRrReceipt])->Option<Self>{
        self.rr_snapshot()?;if rs.len()>32{return None;}
        let mut c=self.clone();
        for r in rs{
            let (next,actual)=c.sparse_rr_step()?;
            if &actual!=r{return None;}
            c=next;
        }
        Some(c)
    }
}

fn core_storage_anf<F:CoreGuardStorage>(p:&CoreBool)->Option<BTreeSet<F::M>>{
    p.iter().map(|m|F::mono(m)).collect()
}
fn core_storage_rename<F:CoreGuardStorage>(p:&BTreeSet<F::M>,map:&BTreeMap<u32,u32>)->Option<BTreeSet<F::M>>{
    p.iter().map(|m|{
        let mut ids=F::mono_ids(m).iter().map(|v|map.get(v).copied()).collect::<Option<Vec<_>>>()?;
        ids.sort_unstable();ids.dedup();F::mono(&ids)
    }).collect()
}
fn core_storage_pack<F:CoreGuardStorage>(factors:Vec<BTreeSet<F::M>>)->Option<Vec<BTreeSet<F::M>>>{
    if factors.len()<=32{return Some(factors);}
    let mut packed=Vec::new();
    let mut acc=BTreeSet::from([F::mono(&[])?]);
    for g in factors{
        if let Some(next)=cps_guard_algebra::guard_mul(&acc,&g){acc=next;}
        else{packed.push(acc);acc=g;}
    }
    packed.push(acc);Some(packed)
}
impl<F:CoreGuardStorage> CpsCore<F>{
    fn n(&self)->usize{self.ps.v.num_qubits}
    fn q(&self)->usize{self.ps.f.functions.len()}
    fn shared_valid(&self)->bool{
        let ps=&self.ps;let n=self.n();let q=self.q();let live=&ps.v.path_vars;
        if n>16||q>16||ps.rr_approximate||ps.rr_tolerance!=0.0||
            !ps.v.continuous_vars.is_empty()||ps.p.terms.len()>F::PHASE_LIMIT||ps.f.functions.iter().any(|p|p.len()>CORE_TERMS)||
            (0..n).any(|i|!live.contains(&(i as u32)))||
            ps.v.next_id>F::ID_LIMIT||live.iter().any(|&v|v>=F::ID_LIMIT||v>=ps.v.next_id)||
            ps.f.registers.iter().map(|r|r.size).sum::<usize>()!=q||
            !self.guard.frame_valid(ps){return false;}
        let mono_ok=|m:&Vec<u32>|m.windows(2).all(|w|w[0]<w[1])&&m.iter().all(|v|live.contains(v));
        ps.f.functions.iter().all(|p|p.iter().all(&mono_ok))&&
            ps.p.terms.iter().all(|(m,c)|mono_ok(m)&&core_phase8(c).is_some())
    }
    fn shared_from_parts(ps:PathSum,gs:Vec<BTreeSet<F::M>>,k:i32)->Option<Self>{
        let guard=F::from_parts(&ps,gs)?;
        let c=Self{ps,guard,k};c.shared_valid().then_some(c)
    }
    fn shared_then_rebased(&self,next:&Self)->Option<Self>{
        if !self.shared_valid()||!next.shared_valid()||self.q()!=next.n(){return None;}
        let k=self.k.checked_add(next.k)?;
        let mut ps=PathSum::new(self.n());ps.set_auto_reduce(false);
        ps.v=self.ps.v.clone();ps.p=self.ps.p.clone();
        if ps.v.next_id.checked_add(u32::try_from(next.guard.ids().len()).ok()?)?>F::ID_LIMIT{return None;}
        let mut map=BTreeMap::new();
        for &old in next.guard.ids(){
            let id=ps.v.get_fresh_var();map.insert(old,id);
        }
        let (mut p,mut f)=core_rename(&next.ps,&map)?;
        let mut gs=next.guard.factors_ref().into_iter().map(|g|core_storage_rename::<F>(g,&map)).collect::<Option<Vec<_>>>()?;
        for (i,repl) in self.ps.f.functions.iter().enumerate(){
            let v=*map.get(&(i as u32))?;
            if repl.len()>8{return None;}
            p.substitute_var_with_poly(v,repl);
            f.substitute_var_with_poly(v,repl);
            let repl=core_storage_anf::<F>(repl)?;
            gs=gs.iter().map(|g|cps_guard_algebra::guard_substitute(g,v,&repl)).collect::<Option<Vec<_>>>()?;
            ps.v.path_vars.remove(&v);
            if p.terms.len()>F::PHASE_LIMIT||f.functions.iter().any(|q|q.len()>CORE_TERMS){return None;}
        }
        for (m,c) in p.terms{ps.p.add_term(m,c);}
        ps.f=f;
        let mut factors=self.guard.factors_ref().into_iter().cloned().collect::<Vec<_>>();factors.extend(gs);
        Self::shared_from_parts(ps,factors,k)
    }
    fn shared_then_adjoint_affine(&self,b:&Self)->Result<(Self,usize,usize),String>{
        if !self.shared_valid()||!b.shared_valid()||self.q()!=b.q(){return Err("invalid-input".into());}
        if b.ps.p.terms.values().any(|c|core_phase8(c)!=Some(4)&&core_phase8(c)!=Some(0)){
            return Err("non-sign-adjoint".into());
        }
        let mut rows=Vec::<(BTreeSet<u32>,BTreeSet<F::M>)>::new();
        let one=F::mono(&[]).ok_or("constant")?;
        let mut gs=Vec::new();
        let mut pins=0usize;
        for g in b.guard.factors_ref(){
            let nonzero:Vec<_>=g.iter().filter(|m|*m!=&one).map(F::mono_ids).collect();
            if nonzero.len()==1&&nonzero[0].len()==1{
                let rhs=if g.contains(&one){BTreeSet::new()}else{BTreeSet::from([one.clone()])};
                rows.push((BTreeSet::from([nonzero[0][0]]),rhs));pins+=1;
            }else{gs.push(g.clone());}
        }
        for (a,out) in self.ps.f.functions.iter().zip(&b.ps.f.functions){
            if out.iter().any(|m|m.len()>1){return Err("non-affine-output".into());}
            let mut rhs=core_storage_anf::<F>(a).ok_or("lhs-output")?;
            let mut mask=BTreeSet::new();
            for m in out{
                if m.is_empty(){core_toggle(&mut rhs,one.clone());}
                else{core_toggle(&mut mask,m[0]);}
            }
            rows.push((mask,rhs));
        }
        // RREF over B's source IDs only; RHS is a Boolean function in A.
        // Any zero row becomes a guard on A, not a discarded constraint.
        let mut pivots=Vec::new();
        let mut rank=0usize;
        for &id in b.guard.ids(){
            let Some(i)=(rank..rows.len()).find(|&i|rows[i].0.contains(&id)) else{continue;};
            rows.swap(rank,i);
            let (m,r)=rows[rank].clone();
            for (j,(q,t)) in rows.iter_mut().enumerate(){
                if j==rank||!q.contains(&id){continue;}
                for &v in &m{core_toggle(q,v);}
                for v in &r{core_toggle(t,v.clone());}
                if t.len()>CORE_TERMS{return Err("affine-rhs-cap".into());}
            }
            pivots.push(id);rank+=1;
        }
        let free=b.guard.ids().len()-rank;
        let total=(self.ps.v.next_id as usize).checked_add(free).ok_or("id-overflow")?;
        if total>F::ID_LIMIT as usize{return Err(format!("affine-live-cap lhs={} rhs={} rank={rank} pins={pins} free={free} required={total}",self.ps.v.next_id,b.guard.ids().len()));}
        let mut ps=PathSum::new(self.n());ps.set_auto_reduce(false);
        ps.v=self.ps.v.clone();ps.p=self.ps.p.clone();
        let mut repl=BTreeMap::<u32,BTreeSet<F::M>>::new();
        for &id in b.guard.ids(){
            if pivots.contains(&id){continue;}
            let fresh=ps.v.get_fresh_var();
            repl.insert(id,BTreeSet::from([F::mono(&[fresh]).ok_or("bound-id")?]));
        }
        for (i,&id) in pivots.iter().enumerate(){
            let mut rhs=rows[i].1.clone();
            if !rows[i].0.contains(&id){return Err("pivot-id".into());}
            for &j in &rows[i].0{
                if j==id{continue;}
                for m in repl.get(&j).ok_or("unresolved-pivot")?{core_toggle(&mut rhs,m.clone());}
            }
            if rhs.len()>CORE_TERMS{return Err("affine-rhs-cap".into());}
            repl.insert(id,rhs);
        }
        let mut factors=self.guard.factors_ref().into_iter().cloned().collect::<Vec<_>>();
        for (m,r) in rows.iter().skip(rank){
            if !m.is_empty(){return Err("incomplete-rref".into());}
            let mut g=r.clone();core_toggle(&mut g,one.clone());factors.push(g);
        }
        let mut work=0usize;
        let mut subst=|g:&BTreeSet<F::M>|->Option<BTreeSet<F::M>>{
            let mut out=BTreeSet::new();
            for m in g{
                let mut term=BTreeSet::from([one.clone()]);
                for id in F::mono_ids(m){
                    let sub=repl.get(&id)?;
                    work=work.checked_add(term.len().checked_mul(sub.len())?)?;
                    if work>2_000_000{return None;}
                    term=cps_guard_algebra::guard_mul(&term,sub)?;
                    if term.is_empty(){break;}
                }
                for v in term{core_toggle(&mut out,v);}
                if out.len()>CORE_TERMS{return None;}
            }
            Some(out)
        };
        for g in &gs{factors.push(subst(g).ok_or("guard-substitution-cap")?);}
        let mut sign=CoreAffineSign::<F::M>::new();
        let mut phase_terms:Vec<_>=b.ps.p.terms.iter().collect();
        phase_terms.sort_by(|a,b|a.0.cmp(b.0));
        for (m,c) in phase_terms{
            if core_phase8(c)==Some(0){continue;}
            // -pi == pi; XOR sign monomials are exact modulo 2*pi.
            let g=subst(&BTreeSet::from([F::mono(m).ok_or("phase-mask")?])).ok_or("phase-substitution-cap")?;
            sign.push(g).ok_or_else(||format!("phase-sign-scratch-cap emitted={} peak={} limit={AFFINE_SIGN_SCRATCH}",sign.emitted,sign.peak))?;
        }
        let phase_detail=core_merge_affine_sign::<F>(&mut ps.p,sign)?;
        if std::env::var_os("CPS_AFFINE_PHASE_DIAGNOSTIC").is_some(){
            println!("CPS_AFFINE_PHASE {phase_detail}");
        }
        ps.f=quprs::pathsum::BooleanState::new(b.n());
        for (i,out) in ps.f.functions.iter_mut().enumerate(){
            *out=repl.get(&(i as u32)).ok_or("output-map")?.iter().map(F::mono_ids).collect();
        }
        let k=self.k.checked_add(b.k).ok_or("scale-overflow")?;
        let factors=core_storage_pack::<F>(factors).ok_or("guard-pack")?;
        let c=Self::shared_from_parts(ps,factors,k).ok_or("result-invariant")?;
        Ok((c,rank,pins))
    }
    fn shared_adjoint(&self)->Result<Self,String>{
        if !self.shared_valid(){return Err("invalid-input".into());}
        let mut ps=PathSum::new(self.q());ps.set_auto_reduce(false);
        let mut map=BTreeMap::new();
        for &old in self.guard.ids(){
            if ps.v.next_id>=F::ID_LIMIT{return Err(format!("stable-id-cap next_id={} source_live={} q={}",ps.v.next_id,self.guard.ids().len(),self.q()));}
            let id=ps.v.get_fresh_var();map.insert(old,id);
        }
        let (p,f)=core_rename(&self.ps,&map).ok_or("native-rename")?;
        let mut factors=self.guard.factors_ref().into_iter().map(|g|core_storage_rename::<F>(g,&map)).collect::<Option<Vec<_>>>().ok_or("guard-rename")?;
        for (j,out) in f.functions.iter().enumerate(){
            let mut eq=core_storage_anf::<F>(out).ok_or("output-mask")?;
            core_toggle(&mut eq,F::mono(&[]).ok_or("constant")?);
            core_toggle(&mut eq,F::mono(&[j as u32]).ok_or("output-id")?);
            factors.push(eq);
        }
        let raw=factors.len();
        let factors=core_storage_pack::<F>(factors).ok_or("guard-pack")?;
        let packed=factors.len();let terms=factors.iter().map(|g|g.len()).sum::<usize>();
        let max=factors.iter().map(|g|g.len()).max().unwrap_or(0);
        for (m,c) in p.terms{ps.p.add_term(m,c*(-1));}
        ps.f=quprs::pathsum::BooleanState::new(self.n());
        for (i,out) in ps.f.functions.iter_mut().enumerate(){out.clear();out.insert(vec![*map.get(&(i as u32)).ok_or("input-map")?]);}
        Self::shared_from_parts(ps,factors,self.k).ok_or_else(||format!("result-invariant raw_factors={raw} packed_factors={packed} terms={terms} max_factor={max} source_live={} q={}",self.guard.ids().len(),self.q()))
    }
}
impl CpsCore {
    fn to_sparse(&self)->Option<CpsCore<SparseGuardFrame>>{
        if !self.valid(){return None;}
        let gs=self.guard.factors().map(|g|g.iter().map(|m|SparseMono::new(<NativeGuardFrame as CoreGuardStorage>::mono_ids(m))).collect::<Option<SparseAnf>>()).collect::<Option<Vec<_>>>()?;
        CpsCore::<SparseGuardFrame>::shared_from_parts(self.ps.clone(),gs,self.k)
    }
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
    fn valid(&self)->bool{self.shared_valid()}
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
        self.then_diagnostic(next).ok()
    }
    fn then_diagnostic(&self,next:&Self)->Result<Self,String>{
        if let Some(c)=self.then_legacy(next){return Ok(c);}
        self.then_guard_interface(next).map_err(|reason|format!(
            "guard-interface {reason} lhs_next={} lhs_live={} rhs_live={} rhs_inputs={} max_replacement={}",
            self.ps.v.next_id,self.guard.ids.len(),next.guard.ids.len(),next.n(),
            self.ps.f.functions.iter().map(|p|p.len()).max().unwrap_or(0)))
    }
    fn then_legacy(&self,next:&Self)->Option<Self>{
        self.shared_then_rebased(next)
    }
    // Exact fallback when B's formal inputs occur only in its guard.
    // Allocate only B's bound variables. Substitution into G_B is
    // simultaneous in the final namespace, not sequential renaming.
    // Keep native P/f and the derived scale; no extra coherent variables.
    fn then_guard_interface(&self,next:&Self)->Result<Self,&'static str>{
        if !self.valid()||!next.valid()||self.q()!=next.n(){return Err("invalid-input");}
        let n=next.n();
        if next.ps.p.terms.keys().chain(next.ps.f.functions.iter().flat_map(|p|p.iter()))
            .any(|m|m.iter().any(|&id|(id as usize)<n)){return Err("formal-in-native-polynomial");}
        let k=self.k.checked_add(next.k).ok_or("scale-overflow")?;
        let mut ps=PathSum::new(self.n());ps.set_auto_reduce(false);
        ps.v=self.ps.v.clone();ps.p=self.ps.p.clone();
        let mut map=BTreeMap::new();
        let mut repl=BTreeMap::<u32,Anf>::new();
        for (i,f) in self.ps.f.functions.iter().enumerate(){
            repl.insert(i as u32,core_anf(f).ok_or("invalid-replacement")?);
        }
        for &old in next.guard.ids.iter().filter(|&&id|(id as usize)>=n){
            if ps.v.next_id>=63{return Err("bound-id-cap");}
            let id=ps.v.get_fresh_var();
            map.insert(old,id);
            repl.insert(old,Anf::from([core_bit(id).ok_or("bound-id-cap")?]));
        }
        let (p,f)=core_rename(&next.ps,&map).ok_or("native-rename")?;
        let mut factors=self.guard.factors().cloned().collect::<Vec<_>>();
        let mut work=0usize;
        for g in next.guard.factors(){
            let mut out=Anf::new();
            for &m in g{
                let mut term=Anf::from([0]);
                for id in 0..63u32{
                    if m&(1u64<<id)==0{continue;}
                    let sub=repl.get(&id).ok_or("unmapped-guard-id")?;
                    work=work.checked_add(term.len().checked_mul(sub.len()).ok_or("guard-work")?).ok_or("guard-work")?;
                    if work>2_000_000{return Err("guard-work");}
                    term=mul_anf(&term,sub).ok_or("guard-substitution-cap")?;
                    if term.is_empty(){break;}
                }
                for v in term{xor_insert(&mut out,v);}
                if out.len()>CORE_TERMS{return Err("guard-substitution-cap");}
            }
            factors.push(out);
        }
        for (m,c) in p.terms{ps.p.add_term(m,c);}
        ps.f=f;
        Self::from_factors(ps,factors,k).ok_or("result-invariant")
    }
    // Overflow-only exact composition with B-dagger, for affine B outputs
    // and sign-only B phases. Solve source-side equality/pin pivots before
    // allocating IDs. The remaining variables stay native PathSum paths;
    // every removed variable has exactly one extension, so k is unchanged.
    fn then_adjoint_affine(&self,b:&Self)->Result<(Self,usize,usize),String>{
        self.shared_then_adjoint_affine(b)
    }
    // Old free inputs become bound; fresh free outputs are never
    // captured by the old input/path IDs. Keep k, not k+n.
    fn adjoint(&self)->Option<Self>{
        self.adjoint_diagnostic().ok()
    }
    fn adjoint_diagnostic(&self)->Result<Self,String>{self.shared_adjoint()}
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
        let sa=a.to_sparse().unwrap();let sb=b.to_sparse().unwrap();
        let sc=sa.shared_then_rebased(&sb).expect("sparse closure");
        assert_eq!(sc.k,a.k+b.k);assert_eq!(sparse_core_matrix(&sc),core_product(&am,&bm));
        let sd=sa.shared_adjoint().expect("sparse adjoint");
        assert_eq!(sd.k,a.k);assert_eq!(sparse_core_matrix(&sd),core_dagger(&am));
        let ba=a.then(&b).unwrap();assert_eq!(ba.k,a.k+b.k);
        assert_eq!(core_matrix(&ba),core_product(&am,&bm));comp+=1;entries+=(1<<n)*(1<<q);
        let ad=a.adjoint().unwrap();assert_eq!(ad.k,a.k);
        assert_eq!(core_matrix(&ad),core_dagger(&am));adj+=1;
        let l=ba.then(&c).unwrap();let r=a.then(&b.then(&c).unwrap()).unwrap();
        assert_eq!(l.k,r.k);assert_eq!(core_matrix(&l),core_matrix(&r));assoc+=1;
        let left=ba.adjoint().unwrap();let right=b.adjoint().unwrap().then(&ad).unwrap();
        assert_eq!(left.k,right.k);assert_eq!(core_matrix(&left),core_matrix(&right));reverse+=1;
    }
    // Guard-only simultaneous substitution is checked against independent
    // exact matrix multiplication, including a transient-ID overflow and
    // a >8-term replacement (neither affects B's phase/output).
    let small=CpsCore::circuit(1,&[G::H(0)]).unwrap();
    let bd=small.adjoint().unwrap();
    let direct=small.then_guard_interface(&bd).unwrap();
    assert_eq!(direct.k,small.k+bd.k);
    assert_eq!(core_matrix(&direct),core_matrix(&small.then_legacy(&bd).unwrap()));
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    for _ in 0..3{ps.v.get_fresh_var();}
    ps.f.functions[0]=(0..9u64).map(|m|(0..4u32).filter(|&i|m&(1u64<<i)!=0).collect()).collect();
    let a=CpsCore::canonical(ps,Anf::from([0])).unwrap();
    assert!(a.then_legacy(&bd).is_none());
    let c=a.then(&bd).unwrap();
    assert_eq!(c.k,a.k+bd.k);
    assert_eq!(core_matrix(&c),core_product(&core_matrix(&a),&core_matrix(&bd)));
    let mut near=a.clone();near.ps.v.next_id=61;
    assert!(near.valid()&&near.then_legacy(&bd).is_none());
    let c=near.then(&bd).unwrap();
    assert_eq!(c.ps.v.next_id,63);
    assert_eq!(core_matrix(&c),core_product(&core_matrix(&near),&core_matrix(&bd)));
    assert!(a.then_guard_interface(&small).is_err());
    assert!(a.then(&small).is_none());
    println!("CPS_GUARD_INTERFACE small_parity=PASS wide_replacement=PASS transient_id=PASS formal_native_reject=PASS");
    // Independent exact matrix product for affine output and fixed pin.
    // y is uniquely determined by x xor y=z, padding is forced zero.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    let y=ps.v.get_fresh_var();let pad=ps.v.get_fresh_var();
    ps.f.functions[0].insert(vec![y]);
    ps.p.add_term(vec![y],quprs::PhaseCoeff::HALF);
    let b=CpsCore::canonical(ps,Anf::from([0,1u64<<pad])).unwrap();
    let (c,rank,pins)=small.then_adjoint_affine(&b).unwrap();
    assert_eq!((rank,pins),(2,1));
    assert_eq!(c.k,small.k+b.k);
    assert_eq!(core_matrix(&c),core_product(&core_matrix(&small),&core_matrix(&b.adjoint().unwrap())));
    // Overdetermined output equations must survive as a guard.
    let mut ps=b.ps.clone();
    ps.f=quprs::pathsum::BooleanState::new(2);
    for out in &mut ps.f.functions{*out=CoreBool::from_iter([vec![0],vec![y]]);}
    let rect=CpsCore::canonical(ps,b.guard.extra.clone()).unwrap();
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    ps.f=quprs::pathsum::BooleanState::new(2);
    ps.f.functions[0]=CoreBool::from_iter([vec![0]]);
    ps.f.functions[1]=CoreBool::from_iter([vec![]]);
    let a=CpsCore::canonical(ps,Anf::from([0])).unwrap();
    let (c,_,_)=a.then_adjoint_affine(&rect).unwrap();
    assert_eq!(core_matrix(&c),core_product(&core_matrix(&a),&core_matrix(&rect.adjoint().unwrap())));
    let mut nonaffine=b.clone();nonaffine.ps.f.functions[0].insert(vec![0,y]);
    assert!(nonaffine.valid()&&small.then_adjoint_affine(&nonaffine).is_err());
    let mut nonreal=b.clone();nonreal.ps.p.add_term(vec![0],quprs::PhaseCoeff::new_constant(quprs::Rational::new(1,8)));
    assert!(nonreal.valid()&&small.then_adjoint_affine(&nonreal).is_err());
    println!("CPS_AFFINE_ADJOINT matrix=PASS unique_extension=PASS zero_row=PASS reject=PASS");
    let (sc,srank,spins)=small.to_sparse().unwrap().shared_then_adjoint_affine(&b.to_sparse().unwrap()).unwrap();
    assert_eq!((srank,spins,sc.k),(rank,pins,small.k+b.k));
    assert_eq!(sparse_core_matrix(&sc),core_product(&core_matrix(&small),&core_matrix(&b.adjoint().unwrap())));
    let (sc,_,_)=a.to_sparse().unwrap().shared_then_adjoint_affine(&rect.to_sparse().unwrap()).unwrap();
    assert_eq!(sparse_core_matrix(&sc),core_product(&core_matrix(&a),&core_matrix(&rect.adjoint().unwrap())));
    assert!(small.to_sparse().unwrap().shared_then_adjoint_affine(&nonaffine.to_sparse().unwrap()).is_err());
    assert!(small.to_sparse().unwrap().shared_then_adjoint_affine(&nonreal.to_sparse().unwrap()).is_err());
    // Force an actual high ID into the affine pivot and phase replacement.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    ps.v.next_id=128;let y=ps.v.get_fresh_var();
    ps.f.functions[0]=CoreBool::from_iter([vec![y]]);
    ps.p.add_term(vec![0,y],quprs::PhaseCoeff::HALF);
    let wide=CpsCore::<SparseGuardFrame>::shared_from_parts(ps,vec![SparseAnf::from([SparseMono::new(vec![]).unwrap()])],1).unwrap();
    let (sc,rank,pins)=small.to_sparse().unwrap().shared_then_adjoint_affine(&wide).unwrap();
    assert_eq!((rank,pins,sc.k),(1,0,2));
    assert_eq!(sparse_core_matrix(&sc),core_product(&core_matrix(&small),&core_dagger(&sparse_core_matrix(&wide))));
    println!("CPS_SHARED_AFFINE matrix=PASS zero_row=PASS high_id=PASS reject=PASS");
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
        if self.n()!=self.q(){return None;}
        self.rr_step_shape()
    }
    // Scoped rectangular pre-composition lane. Same native RR and
    // guard substitution, phase budget and exact receipt fields.
    fn rr_step_shape(&self)->Option<(Self,CoreRrReceipt)>{
        if !self.valid(){return None;}
        let step=guarded_native_step_shape(&self.ps,self.n(),self.q(),&self.guard)?;
        if !core_rr_phase_admitted(self.ps.p.terms.len(),step.ps.p.terms.len()){return None;}
        let native=guarded_receipt_shape(&self.ps,self.n(),self.q(),&self.guard,&step)?;
        let decrement=i32::try_from(native.scale2).ok()?;
        let after_k=self.k.checked_sub(decrement)?;
        let next=Self::from_frame(step.ps,step.guard,after_k)?;
        if next.guard.ids.len()>=self.guard.ids.len()||next.n()!=self.n()||next.q()!=self.q(){return None;}
        let receipt=CoreRrReceipt{native,before_k:self.k,after_k};
        Some((next,receipt))
    }
    fn replay_rr(&self,receipts:&[CoreRrReceipt])->Option<Self>{
        if self.n()!=self.q(){return None;}
        self.replay_rr_shape(receipts)
    }
    fn replay_rr_shape(&self,receipts:&[CoreRrReceipt])->Option<Self>{
        if !self.valid()||receipts.len()>32{return None;}
        let mut c=self.clone();
        for supplied in receipts{
            let (next,actual)=c.rr_step_shape()?;
            if &actual!=supplied{return None;}
            c=next;
        }
        Some(c)
    }
}
// Alpha-renaming only after receipt replay: close stable-ID holes
// without changing any variable role, guard, phase or scale.
impl CpsCore{
    fn dense_ids(&self)->Option<Self>{
        if !self.valid(){return None;}
        let mut ps=PathSum::new(self.n());ps.set_auto_reduce(false);
        let mut map=BTreeMap::new();
        for &old in &self.guard.ids{
            let v=if (old as usize)<self.n(){old}else{ps.v.get_fresh_var()};
            map.insert(old,v);
        }
        let (p,f)=core_rename(&self.ps,&map)?;
        ps.p=p;ps.f=f;
        let gs=self.guard.factors().map(|g|core_rename_anf(g,&map)).collect::<Option<Vec<_>>>()?;
        Self::from_factors(ps,gs,self.k)
    }
    // Only invoked after whole-UA precomposition failed the live budget.
    // Reuse the same original native rules at earlier gate boundaries.
    // Stop rewriting as soon as the requested live saving is achieved.
    fn prefix_rr(&self,ops:&[G],target:usize)->Result<(Self,Vec<(usize,CoreRrReceipt)>,usize),String>{
        if target==0||target>16||ops.len()>256{return Err("prefix-budget".into());}
        let mut a=self.clone();
        let mut receipts=Vec::new();
        let mut removed=0usize;
        let mut boundaries=0usize;
        for (i,g) in ops.iter().enumerate(){
            a=a.then_circuit_diagnostic(std::slice::from_ref(g)).map_err(|e|format!("prefix gate_index={i} {e}"))?;
            if !matches!(g,G::H(_))||removed>=target||receipts.len()>=16{continue;}
            boundaries+=1;
            while removed<target&&receipts.len()<16{
                let Some((next,r))=a.rr_step_shape() else{break;};
                let replay=a.replay_rr_shape(std::slice::from_ref(&r)).ok_or("prefix-replay")?;
                if replay.k!=next.k||guarded_snapshot_shape(&replay.ps,replay.n(),replay.q(),&replay.guard)!=guarded_snapshot_shape(&next.ps,next.n(),next.q(),&next.guard){return Err("prefix-replay-mismatch".into());}
                removed+=a.guard.ids.len()-next.guard.ids.len();
                receipts.push((i,r));a=next;
            }
        }
        if removed<target{return Err(format!("prefix-insufficient target={target} removed={removed} steps={} boundaries={boundaries} live={}",receipts.len(),a.guard.ids.len()));}
        let dense=a.dense_ids().ok_or("prefix-dense-ids")?;
        Ok((dense,receipts,boundaries))
    }
    fn precompose_affine_rr(&self,b:&Self)->Result<(Self,usize,usize,Vec<CoreRrReceipt>,usize),String>{
        let mut a=self.clone();let mut receipts=Vec::new();
        let mut last="no-admitted-step".to_owned();
        for _ in 0..16{
            let Some((next,r))=a.rr_step_shape() else{break;};
            receipts.push(r);a=next;
            let dense=a.dense_ids().ok_or("dense-ids")?;
            if !core_label_support(&dense,b){return Err("label-certificate-after-rr".into());}
            match dense.then_adjoint_affine(b){
                Ok((c,rank,pins))=>{
                    let replay=self.replay_rr_shape(&receipts).ok_or("pre-rr-replay")?;
                    if replay.k!=a.k||guarded_snapshot_shape(&replay.ps,replay.n(),replay.q(),&replay.guard)!=guarded_snapshot_shape(&a.ps,a.n(),a.q(),&a.guard){return Err("pre-rr-replay-mismatch".into());}
                    return Ok((c,rank,pins,receipts,dense.guard.ids.len()));
                },
                Err(e)=>{last=e;if !last.contains("affine-live-cap"){break;}}
            }
        }
        Err(format!("pre-rr steps={} live={} last={last}",receipts.len(),a.guard.ids.len()))
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
    assert!(core_rr_phase_admitted(300,512));
    assert!(!core_rr_phase_admitted(300,513));
    assert!(core_rr_phase_admitted(748,748));
    assert!(core_rr_phase_admitted(748,600));
    assert!(!core_rr_phase_admitted(748,749));
    println!("CPS_RR_PHASE_ADMISSION=PASS legacy512=PASS wide_non_growth=PASS");
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
    // A rectangular map with two original H gates, and an additional
    // constant output, exercises the real HH on non-square signatures.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    G::H(0).apply(&mut ps,false);G::H(0).apply(&mut ps,false);
    let old=ps.f.functions[0].clone();
    ps.f=quprs::pathsum::BooleanState::new(2);
    ps.f.functions[0]=old;ps.f.functions[1]=CoreBool::default();
    let a=CpsCore::canonical(ps,Anf::from([0])).unwrap();
    let (next,r)=a.rr_step_shape().unwrap();
    assert_eq!((next.n(),next.q()),(1,2));
    core_rr_equal(&a,&next);
    let replay=a.replay_rr_shape(&[r.clone()]).unwrap();core_rr_equal(&a,&replay);
    let dense=next.dense_ids().unwrap();assert_eq!(dense.k,next.k);
    assert_eq!(dense.ps.v.next_id as usize,dense.guard.ids.len());
    core_rr_equal(&a,&dense);
    let mut bad=r;bad.after_k+=1;
    assert!(a.replay_rr_shape(&[bad]).is_none());
    println!("CPS_RECTANGULAR_RR matrix=PASS replay=PASS dense_ids=PASS scale_mutant=REJECTED");
    // Gate-boundary replay must preserve the complete later circuit,
    // not merely the reduced prefix. Include a rectangular output.
    let mut start=PathSum::new(1);start.set_auto_reduce(false);
    start.f=quprs::pathsum::BooleanState::new(2);
    start.f.functions[0]=CoreBool::from_iter([vec![0]]);
    start.f.functions[1]=CoreBool::default();
    let start=CpsCore::canonical(start,Anf::from([0])).unwrap();
    let ops=[G::H(0),G::H(0),G::CX(0,1),G::H(1),G::H(1),G::Z(0)];
    let raw=start.then_circuit_diagnostic(&ops).unwrap();
    let (prefix,rs,_)=start.prefix_rr(&ops,2).unwrap();
    assert!(!rs.is_empty()&&raw.guard.ids.len()-prefix.guard.ids.len()>=2);
    core_rr_equal(&raw,&prefix);
    assert!(start.prefix_rr(&[G::H(0)],2).is_err());
    println!("CPS_PREFIX_RR full_matrix=PASS replay=PASS insufficient=REJECTED");
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
        // Each ANF mask indexes one copy only; CNF literals index both copies.
        if s.n+s.h>63||primary>126{return None;}
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
            let sparse=c.to_sparse().unwrap();
            for dag in [false,true]{
                let plan=sparse.sparse_norm_plan(dag);
                if dag&&c.ps.p.terms.values().any(|v|core_phase8(v)!=Some(4)){assert!(plan.is_none());continue;}
                let (wide,d,p,sk)=plan.expect("sparse norm parity");
                assert_eq!((p,sk),(primary,k));
                let tag=if dag{"sparse-dag"}else{"sparse-flat"};
                let mut data=format!("p cnf {} {}\n",wide.vars,wide.clauses.len());
                for row in &wide.clauses{for lit in row{data.push_str(&format!("{lit} "));}data.push_str("0\n");}
                std::fs::write(dir.join(format!("{name}-{route}.{tag}.cnf")),data).unwrap();
                std::fs::write(dir.join(format!("{name}-{route}.{tag}.phase")),d.iter().map(ToString::to_string).collect::<Vec<_>>().join(",")).unwrap();
            }
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
        self.then_circuit_diagnostic(ops).ok()
    }
    fn then_circuit_diagnostic(&self,ops:&[G])->Result<Self,String>{
        if !self.valid()||self.q()==0{return Err("invalid-input".into());}
        // Bounded 05 source admission experiment; keep all per-gate
        // and CPS structural budgets. This is not a new reduction rule.
        const GATE_LIMIT:usize=256;
        if ops.len()>GATE_LIMIT{return Err(format!("gate-count gates={} limit={GATE_LIMIT}",ops.len()));}
        let mut ps=self.ps.clone();ps.set_auto_reduce(false);
        let mut k=self.k;
        for (i,g) in ops.iter().enumerate(){
            let detail=|reason:&str,ps:&PathSum|format!(
                "{reason} gate_index={i} gate={g:?} next_id={} live={} phase_terms={} max_output_terms={}",
                ps.v.next_id,ps.v.path_vars.len(),ps.p.terms.len(),ps.f.functions.iter().map(|p|p.len()).max().unwrap_or(0));
            if !admitted(self.q(),std::slice::from_ref(g)){return Err(detail("gate-admission",&ps));}
            let h=matches!(g,G::H(_));
            if h&&ps.v.next_id>=63{return Err(detail("stable-id-cap",&ps));}
            let before=ps.v.path_vars.len();
            g.apply(&mut ps,false);
            if ps.v.path_vars.len()!=before+usize::from(h){return Err(detail("path-count-contract",&ps));}
            if ps.p.terms.len()>CORE_PHASE_TERMS{return Err(detail("phase-term-cap",&ps));}
            if ps.f.functions.iter().any(|p|p.len()>CORE_TERMS){return Err(detail("boolean-term-cap",&ps));}
            if h{k=k.checked_add(1).ok_or_else(||detail("scale-overflow",&ps))?;}
        }
        let guard=NativeGuardFrame::from_factors(&ps,self.guard.factors().cloned().collect())
            .ok_or_else(||"guard-frame".to_owned())?;
        Self::from_frame(ps,guard,k).ok_or_else(||"result-invariant".to_owned())
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
        stage="native-gate-composition";let ua=match a.then_circuit_diagnostic(&ops){
            Ok(v)=>v,Err(detail)=>{println!("CPS_COMPOSITION_DETAIL {detail}");return None;}
        };
        stage="label-certificate";if !core_label_support(&ua,&b){return None;}
        stage="adjoint";let bd=match b.adjoint_diagnostic(){
            Ok(v)=>v,Err(detail)=>{println!("CPS_COMPOSITION_DETAIL {detail}");return None;}
        };
        stage="composition";let mut c=match ua.then_diagnostic(&bd){
            Ok(v)=>v,Err(detail)=>{
                if !detail.contains("bound-id-cap"){println!("CPS_COMPOSITION_DETAIL {detail}");return None;}
                match ua.then_adjoint_affine(&b){
                    Ok((v,rank,pins))=>{
                        println!("CPS_AFFINE_INTERFACE rank={rank} pins={pins} lhs_live={} rhs_live={} result_live={} k={}",ua.guard.ids.len(),b.guard.ids.len(),v.guard.ids.len(),v.k);
                        v
                    },
                    Err(e)=>{
                        // The same overflow-only sparse affine CPS is used
                        // for every policy. Pure WMC performs no RR.
                        if e.contains("affine-live-cap"){
                            match ua.to_sparse()?.shared_then_adjoint_affine(&b.to_sparse()?){
                                Ok((v,rank,pins))=>{
                                    println!("CPS_AFFINE_INTERFACE rank={rank} pins={pins} lhs_live={} rhs_live={} result_live={} k={}",ua.guard.ids.len(),b.guard.ids.len(),v.guard.ids.len(),v.k);
                                    println!("CPS_SPARSE_MATCHED initial_live={} phase_terms={}",v.guard.ids.len(),v.ps.p.terms.len());
                                    return sparse_matched_finish(v,&dir,policy,dag,t.elapsed().as_nanos(),&mut stage);
                                },
                                Err(f)=>{println!("CPS_COMPOSITION_DETAIL {detail}; affine {e}; sparse {f}");return None;}
                            }
                        }
                        println!("CPS_COMPOSITION_DETAIL {detail}; affine {e}");return None;
                    }
                }
            }
        };
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
        // Each ANF mask indexes one copy only; CNF literals index both copies.
        if s.n+s.h>63||primary>126{return None;}
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
            let adj=c.adjoint_diagnostic().expect("held-out adjoint");
            assert_eq!((adj.n(),adj.q(),adj.k),(c.q(),c.n(),c.k));
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
                // The original source IDs are contiguous, and adjoint
                // allocates their images after its fresh formal inputs.
                let za=z|(a<<c.q());
                assert!(adj.guard.factors().all(|g|eval(g,za)));
                for j in 0..c.q(){
                    assert!(!adj.guard.factors().all(|g|eval(g,za^(1u64<<j))));
                }
                let adj_on=|m:&Vec<u32>|m.iter().all(|&id|za&(1u64<<id)!=0);
                let x_back=adj.ps.f.functions.iter().enumerate().fold(0u64,|v,(j,p)|v|(((p.iter().filter(|m|adj_on(m)).count()%2) as u64)<<j));
                let adj_phase=adj.ps.p.terms.iter().filter(|(m,_)|adj_on(m)).map(|(_,p)|core_phase8(p).unwrap() as usize).sum::<usize>()%8;
                assert_eq!(x_back,x);assert_eq!((phase+adj_phase)%8,0);
                // A forbidden source padding assignment remains forbidden
                // under adjoint, even with the correct output equality.
                let padding=n+width+r;
                if padding<n+k{assert!(!adj.guard.factors().all(|g|eval(g,za|(1u64<<(c.q()+padding)))));}
            }}
            println!("CPS_HELDOUT_ADJOINT family={family} width={width} variant={variant} source_factors={} raw_factors={} retained_factors={} k={}",c.guard.factors().count(),c.guard.factors().count()+c.q(),adj.guard.factors().count(),adj.k);
            println!("CPS_HELDOUT_PREDICATE family={family} width={width} variant={variant} h={k} factors={} terms={} counter_checks={} materialized_columns=0",c.guard.factors().count(),c.guard.factors().map(|g|g.len()).sum::<usize>(),2*(1usize<<r));
            predicates+=1;
        }
    }}
    assert_eq!(predicates,12);
    println!("CPS_HELDOUT_PREDICATE_SUMMARY predicates={predicates} comparisons={comparisons} source_counter_checks={checks}");
}

#[test]
fn hoare_cps_shared_guard_algebra(){
    use cps_guard_algebra::{SparseMono,SparseAnf,guard_mul,guard_substitute,sparse_guard_lit};
    // All 16 ANFs over two variables; RHS substitutions use a disjoint
    // target and an additional variable. Compare with independent truth
    // evaluation, not just the two implementations' internal structure.
    let ids=[0u32,63,128];
    let lift=|p:&Anf|->SparseAnf{p.iter().map(|&m|
        SparseMono::new((0..3).filter(|&i|m&(1u64<<i)!=0).map(|i|ids[i]).collect()).unwrap()
    ).collect()};
    let wide_eval=|p:&SparseAnf,x:u64|->bool{
        p.iter().fold(false,|a,m|a^m.ids().iter().all(|id|
            ids.iter().position(|v|v==id).is_some_and(|i|x&(1u64<<i)!=0)))
    };
    let mut checks=0usize;
    for a in 0..16u64{for b in 0..16u64{
        let p:Anf=(0..4u64).filter(|&m|a&(1u64<<m)!=0).collect();
        let q:Anf=(0..4u64).filter(|&m|b&(1u64<<m)!=0).collect();
        let qp:Anf=q.iter().map(|&m|m<<1).collect();
        let prod=mul_anf(&p,&q).unwrap();
        let wide=guard_mul(&lift(&p),&lift(&q)).unwrap();
        assert_eq!(wide,lift(&prod));
        let sub=substitute_guard(&p,0,&qp).unwrap();
        let wide_sub=guard_substitute(&lift(&p),ids[0],&lift(&qp)).unwrap();
        assert_eq!(wide_sub,lift(&sub));
        for x in 0..8u64{
            assert_eq!(eval(&prod,x),eval(&p,x)&&eval(&q,x));
            assert_eq!(wide_eval(&wide,x),eval(&prod,x));
            let y=(x&!1)|u64::from(eval(&qp,x));
            assert_eq!(eval(&sub,x),eval(&p,y));
            assert_eq!(wide_eval(&wide_sub,x),eval(&sub,x));checks+=2;
        }
    }}
    assert_eq!(checks,4096);
    assert!(SparseMono::new(vec![64,63]).is_none());
    assert!(SparseMono::new(vec![63,63]).is_none());
    assert!(guard_substitute(&lift(&Anf::from([1])),0,&lift(&Anf::from([1]))).is_none());
    let big:Anf=(0..65u64).collect();
    assert!(mul_anf(&big,&big).is_none());
    let big_wide:SparseAnf=(0..65u32).map(|i|SparseMono::new(vec![i+64]).unwrap()).collect();
    assert!(guard_mul(&big_wide,&big_wide).is_none());
    // 67 primary variables, including sparse stable IDs above both
    // machine-word boundaries. Fix only the three relevant variables.
    // The 64 unconstrained primaries contribute exactly 2^64 extensions;
    // all Tseitin auxiliaries must be uniquely determined.
    let mut live:Vec<u32>=(0..66u32).collect();live.push(128);
    let map:BTreeMap<u32,Lit>=live.iter().enumerate().map(|(i,&v)|(v,i as Lit+2)).collect();
    let p=lift(&Anf::from([0,3,4,6]));
    let mut c=Cnf::new(live.len());
    let lit=sparse_guard_lit(&mut c,&p,&map).unwrap();
    let mut fuel=1_000_000u64;
    for x in 0..8u64{
        let mut a:Vec<Lit>=ids.iter().enumerate().map(|(i,id)|if x&(1u64<<i)!=0{map[id]}else{-map[id]}).collect();
        let v=wide_eval(&p,x);
        a.push(if v{lit}else{-lit});
        assert_eq!(count(&c,&a,&mut fuel,false),Some(1u128<<64));
        *a.last_mut().unwrap()*=-1;
        assert_eq!(count(&c,&a,&mut fuel,false),Some(0));
    }
    let missing=SparseAnf::from([SparseMono::new(vec![999]).unwrap()]);
    assert!(sparse_guard_lit(&mut c,&missing,&map).is_none());
    println!("CPS_SHARED_GUARD_ALGEBRA checks={checks} narrow_wide=PASS primary67=PASS unique_extension=PASS malformed_reject=PASS");
}

fn sparse_core_matrix(c:&CpsCore<SparseGuardFrame>)->Vec<Vec<Root>>{
    assert!(c.shared_valid());
    let n=c.n();let q=c.q();
    let ids:Vec<_>=c.guard.ids.iter().copied().filter(|&v|v as usize>=n).collect();
    assert!(n<=3&&q<=8&&ids.len()<=18);
    let mut out=vec![vec![[0;4];1usize<<n];1usize<<q];
    for x in 0..1u64<<n{for y in 0..1u64<<ids.len(){
        let mut on_ids:BTreeSet<u32>=(0..n as u32).filter(|&i|x&(1u64<<i)!=0).collect();
        on_ids.extend(ids.iter().enumerate().filter_map(|(i,&v)|(y&(1u64<<i)!=0).then_some(v)));
        if !c.guard.factors.iter().all(|g|g.iter().fold(false,|v,m|v^m.ids().iter().all(|id|on_ids.contains(id)))){continue;}
        let on=|m:&Vec<u32>|m.iter().all(|id|on_ids.contains(id));
        let z=c.ps.f.functions.iter().enumerate().fold(0usize,|v,(i,p)|v|((p.iter().filter(|m|on(m)).count()%2)<<i));
        let k=c.ps.p.terms.iter().filter(|(m,_)|on(m)).map(|(_,p)|core_phase8(p).unwrap() as usize).sum::<usize>();
        out[z][x as usize]=add(out[z][x as usize],root(k));
    }}
    out
}
#[test]
fn hoare_cps_sparse_frame(){
    // A real high stable ID, with only one summed path; no wide-bit
    // matrix enumeration or hand-selected scale.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    ps.v.next_id=128;let v=ps.v.get_fresh_var();
    ps.f.functions[0]=CoreBool::from_iter([vec![v]]);
    ps.p.add_term(vec![0,v],quprs::PhaseCoeff::HALF);
    let a=CpsCore::<SparseGuardFrame>::shared_from_parts(ps,vec![SparseAnf::from([SparseMono::new(vec![]).unwrap()])],1).unwrap();
    let h=CpsCore::circuit(1,&[G::H(0)]).unwrap();
    assert_eq!(sparse_core_matrix(&a),core_matrix(&h));
    let b=h.to_sparse().unwrap();
    let ab=a.shared_then_rebased(&b).unwrap();
    assert_eq!(ab.k,2);assert_eq!(sparse_core_matrix(&ab),core_product(&core_matrix(&h),&core_matrix(&h)));
    let ad=a.shared_adjoint().unwrap();assert_eq!(sparse_core_matrix(&ad),core_dagger(&core_matrix(&h)));
    let bad=SparseAnf::from([SparseMono::new(vec![127]).unwrap()]);
    assert!(CpsCore::<SparseGuardFrame>::shared_from_parts(a.ps.clone(),vec![bad],a.k).is_none());
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    for _ in 0..66{ps.v.get_fresh_var();}
    let gs=vec![SparseAnf::from([SparseMono::new(vec![]).unwrap(),SparseMono::new(vec![66]).unwrap()])];
    let wide=CpsCore::<SparseGuardFrame>::shared_from_parts(ps,gs,66).unwrap();
    let wd=wide.shared_adjoint().unwrap();
    let prod=wide.shared_then_rebased(&wd).unwrap();
    assert_eq!(prod.guard.ids.len(),134);assert_eq!(prod.k,132);
    println!("CPS_SPARSE_FRAME high_id=PASS matrix=PASS adjoint=PASS live134=PASS missing_id=REJECTED");
}
// Diagnostic-only bounded unique guard section. A factor y XOR r = 1
// with y absent from r determines exactly one path bit for each survivor.
// This is a substitution of a constraint, not a factor-of-two Elim;
// k stays unchanged. No matched route uses this pilot.
fn sparse_guard_sections(c:&CpsCore<SparseGuardFrame>)->Vec<(usize,u32,SparseAnf)>{
    let mut out=Vec::new();
    let one=SparseMono::new(vec![]).unwrap();
    for (i,g) in c.guard.factors.iter().enumerate(){
        for m in g{
            if m.ids().len()!=1{continue;}
            let y=m.ids()[0];
            if (y as usize)<c.n()||g.iter().any(|t|t!=m&&t.contains_id(y)){continue;}
            let mut rhs=g.clone();rhs.remove(m);core_toggle(&mut rhs,one.clone());
            out.push((i,y,rhs));
        }
    }
    out.sort_by_key(|(i,y,rhs)|(rhs.len(),*y,*i));
    out
}
fn sparse_guard_section_trial(c:&CpsCore<SparseGuardFrame>,i:usize,y:u32,rhs:&SparseAnf)->Option<CpsCore<SparseGuardFrame>>{
    if rhs.len()>8||!c.shared_valid()||c.ps.p.terms.values().any(|p|core_phase8(p)!=Some(4)){return None;}
    if !sparse_guard_sections(c).iter().any(|(j,v,r)|*j==i&&*v==y&&r==rhs){return None;}
    // Bound the work before native substitution; the admitted CPS caps
    // and exact native sign semantics remain unchanged.
    let uses=c.ps.p.terms.keys().filter(|m|m.contains(&y)).count()
        +c.ps.f.functions.iter().map(|f|f.iter().filter(|m|m.contains(&y)).count()).sum::<usize>();
    if uses.checked_mul(rhs.len().max(1))?>16_384{return None;}
    let gs=c.guard.factors.iter().enumerate().filter(|(j,_)|*j!=i)
        .map(|(_,g)|cps_guard_algebra::guard_substitute(g,y,rhs)).collect::<Option<Vec<_>>>()?;
    let native:CoreBool=rhs.iter().map(|m|m.ids().to_vec()).collect();
    let mut ps=c.ps.clone();
    ps.p.substitute_var_with_poly(y,&native);ps.f.substitute_var_with_poly(y,&native);
    if !ps.v.path_vars.remove(&y){return None;}
    let next=CpsCore::<SparseGuardFrame>::shared_from_parts(ps,gs,c.k)?;
    if next.guard.ids.len()+1!=c.guard.ids.len(){return None;}
    Some(next)
}
fn sparse_reducibility_probe(c:&CpsCore<SparseGuardFrame>,stage:&str){
    let support:BTreeSet<u32>=c.guard.factors.iter().flat_map(|g|g.iter()).flat_map(|m|m.ids().iter().copied()).collect();
    let mut candidates:Vec<_>=c.ps.get_reducible_vars().into_iter().filter(|&v|(v as usize)>=c.n()).collect();
    candidates.sort_unstable();
    let blocked=candidates.iter().filter(|v|support.contains(v)).count();
    // Native RR trials on copies only: these are diagnostic opportunities,
    // not legal guarded transitions or quantum verdicts.
    let mut counts=[0usize;3];let mut blocked_counts=[0usize;3];
    for &v in &candidates{
        for rule in 0..3{
            let mut p=c.ps.clone();
            let ok=match rule{0=>p.try_reduce_elim(&[v]),1=>p.try_reduce_omega(&[v]),_=>p.try_reduce_hh(&[v])};
            if ok{counts[rule]+=1;if support.contains(&v){blocked_counts[rule]+=1;}}
        }
    }
    let sections=sparse_guard_sections(c);
    let bounded=sections.iter().filter(|(_,_,r)|r.len()<=8).count();
    let guard_terms=c.guard.factors.iter().map(|g|g.len()).sum::<usize>();
    let output_terms=c.ps.f.functions.iter().map(|f|f.len()).sum::<usize>();
    println!("CPS_CORE8_STRUCTURE stage={stage} live={} k={} guard_factors={} guard_terms={guard_terms} guard_support={} output_terms={output_terms} phase_terms={} native_candidates={} guard_blocked={blocked} native_elim={} native_omega={} native_hh={} blocked_elim={} blocked_omega={} blocked_hh={} unique_sections={} bounded_sections={bounded}",
        c.guard.ids.len(),c.k,c.guard.factors.len(),support.len(),c.ps.p.terms.len(),candidates.len(),counts[0],counts[1],counts[2],blocked_counts[0],blocked_counts[1],blocked_counts[2],sections.len());
}
#[test]
fn hoare_cps_sparse_guard_section(){
    // Nontrivial section y = x XOR z, with y used in phase/output and
    // a second guard. Exact raw matrices are identical: k does not change.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    let y=ps.v.get_fresh_var();let z=ps.v.get_fresh_var();
    ps.p.add_term(vec![0,y],quprs::PhaseCoeff::HALF);
    ps.f.functions[0]=CoreBool::from_iter([vec![y]]);
    let m=|v:Vec<u32>|SparseMono::new(v).unwrap();
    let g=SparseAnf::from([m(vec![]),m(vec![y]),m(vec![0]),m(vec![z])]);
    let h=SparseAnf::from([m(vec![]),m(vec![0,y])]);
    // Preserve the separate source factors for this section test; the
    // trial itself uses the ordinary shared constructor/canonicalizer.
    let c=CpsCore{guard:SparseGuardFrame{ids:vec![0,y,z],factors:vec![g,h]},ps,k:2};
    assert!(c.shared_valid());
    let (i,v,r)=sparse_guard_sections(&c).into_iter().find(|(_,v,_)|*v==y).unwrap();
    let next=sparse_guard_section_trial(&c,i,v,&r).unwrap();
    assert_eq!(next.k,c.k);assert_eq!(sparse_core_matrix(&next),sparse_core_matrix(&c));
    assert!(sparse_guard_section_trial(&c,i,v,&SparseAnf::new()).is_none());
    println!("CPS_CORE8_SECTION matrix=PASS scale=PASS mutant=REJECTED");
}

#[test]
fn hoare_cps_sparse_source_admission(){
    let root=std::path::PathBuf::from(std::env::var("CPS_CORE_SOURCE_DIR").unwrap());
    let dir=root.join("benchmarks/all/MOGrover/05");
    let a=core_hsl_lower(&std::fs::read_to_string(dir.join("pre.hsl")).unwrap()).unwrap();
    let b=core_hsl_lower(&std::fs::read_to_string(dir.join("post.hsl")).unwrap()).unwrap();
    let (ops,_)=quprs::qasm::parse_qasm_str_source_pinned(&std::fs::read_to_string(dir.join("circuit.qasm")).unwrap()).unwrap();
    let ua=a.then_circuit_diagnostic(&ops).unwrap();
    assert!(core_label_support(&ua,&b));
    let su=ua.to_sparse().unwrap();let sb=b.to_sparse().unwrap();
    let bd=sb.shared_adjoint().unwrap();
    assert_eq!((bd.n(),bd.q(),bd.k),(b.q(),b.n(),b.k));
    match su.shared_then_rebased(&bd){
        Some(c)=>{
            assert_eq!((c.n(),c.q(),c.k),(ua.n(),b.n(),ua.k+b.k));
            assert_eq!(c.guard.ids.len(),86);
            println!("CPS_SPARSE_SOURCE_ADMISSION case=MOGrover05 status=READY live={} next_id={} k={} factors={} phase_terms={}",c.guard.ids.len(),c.ps.v.next_id,c.k,c.guard.factors.len(),c.ps.p.terms.len());
        },
        None=>println!("CPS_SPARSE_SOURCE_ADMISSION case=MOGrover05 status=BLOCKED stage=rebased-composition")
    }
    match su.shared_then_adjoint_affine(&sb){
        Ok((c,rank,pins))=>{
            assert_eq!((rank,pins,c.guard.ids.len(),c.n(),c.q(),c.k),(19,9,67,ua.n(),b.n(),ua.k+b.k));
            println!("CPS_SPARSE_AFFINE_ADMISSION case=MOGrover05 status=READY rank={rank} pins={pins} live={} next_id={} k={} factors={} phase_terms={}",c.guard.ids.len(),c.ps.v.next_id,c.k,c.guard.factors.len(),c.ps.p.terms.len());
            let mut residual=c.clone();let mut receipts=Vec::new();
            for _ in 0..32{
                let Some((next,r))=residual.sparse_rr_step() else{break;};
                receipts.push(r);residual=next;
            }
            assert_eq!(c.replay_sparse_rr(&receipts).unwrap().rr_snapshot(),residual.rr_snapshot());
            println!("CPS_SPARSE_SOURCE_RR case=MOGrover05 steps={} live_before={} live_after={} k_before={} k_after={} phase_before={} phase_after={} replay=PASS",receipts.len(),c.guard.ids.len(),residual.guard.ids.len(),c.k,residual.k,c.ps.p.terms.len(),residual.ps.p.terms.len());
            sparse_reducibility_probe(&c,"initial");
            sparse_reducibility_probe(&residual,"residual");
            // Explore at most eight unique sections, each followed by the
            // original guarded RR and checked replay. Diagnostic only.
            let mut pilot=residual.clone();let mut sections=0usize;let mut native_steps=0usize;
            for _ in 0..8{
                let next=sparse_guard_sections(&pilot).into_iter()
                    .filter(|(_,_,r)|r.len()<=8).take(16)
                    .find_map(|(i,y,r)|sparse_guard_section_trial(&pilot,i,y,&r));
                let Some(next)=next else{break;};
                assert_eq!(next.k,pilot.k);
                sections+=1;let before=next.clone();pilot=next;let mut rr=Vec::new();
                for _ in 0..32{
                    let Some((next,r))=pilot.sparse_rr_step() else{break;};
                    rr.push(r);pilot=next;
                }
                assert_eq!(before.replay_sparse_rr(&rr).unwrap().rr_snapshot(),pilot.rr_snapshot());
                native_steps+=rr.len();
            }
            sparse_reducibility_probe(&pilot,"section-pilot");
            let dag=pilot.sparse_norm_plan(true).map(|(cnf,_,primary,_)|(primary,cnf.vars,cnf.clauses.len()));
            println!("CPS_CORE8_SECTION_PILOT case=MOGrover05 sections={sections} native_steps={native_steps} live_before={} live_after={} k_before={} k_after={} dag={dag:?}",residual.guard.ids.len(),pilot.guard.ids.len(),residual.k,pilot.k);
        },
        Err(e)=>println!("CPS_SPARSE_AFFINE_ADMISSION case=MOGrover05 status=BLOCKED detail={e}")
    }
}

#[test]
fn hoare_cps_affine_phase_cancellation(){
    // A final-size bound must not reject a transient additional term.
    // The narrow sorted delta visits the absent constant before the
    // existing largest monomial. Use exact native Z8 coefficients.
    let mut p=quprs::pathsum::PhasePolynomial::new();
    for m in 1..=1024u64{
        p.add_term(<NativeGuardFrame as CoreGuardStorage>::mono_ids(&m),quprs::PhaseCoeff::HALF);
    }
    let mut sign=CoreAffineSign::<u64>::new();
    sign.push(Anf::from([0,1024,2048])).unwrap();
    sign.push(Anf::from([2048])).unwrap();
    let detail=core_merge_affine_sign::<NativeGuardFrame>(&mut p,sign).unwrap();
    assert!(detail.contains("merge_peak=1025")&&detail.contains("final_terms=1024")&&detail.contains("delta_cancelled=2"));
    assert_eq!(p.terms.len(),1024);
    assert!(p.terms.contains_key(&Vec::<u32>::new())&&!p.terms.contains_key(&vec![10]));
    for m in 1..1024u64{
        assert_eq!(core_phase8(&p.terms[&<NativeGuardFrame as CoreGuardStorage>::mono_ids(&m)]),Some(4));
    }
    let mut overflow=CoreAffineSign::<u64>::new();
    overflow.push(Anf::from([1024])).unwrap();
    let e=core_merge_affine_sign::<NativeGuardFrame>(&mut p.clone(),overflow).unwrap_err();
    assert!(e.contains("final_terms=1025")&&e.contains("limit=1024"));
    // Mixed Z8 phase must be added modulo 8, not XOR-deleted.
    let mut p=quprs::pathsum::PhasePolynomial::new();
    p.add_term(vec![128],quprs::PhaseCoeff::new_constant(quprs::Rational::new(1,8)));
    let mut sign=CoreAffineSign::<SparseMono>::new();
    sign.push(SparseAnf::from([SparseMono::new(vec![128]).unwrap()])).unwrap();
    core_merge_affine_sign::<SparseGuardFrame>(&mut p,sign).unwrap();
    assert_eq!(core_phase8(&p.terms[&vec![128]]),Some(5));
    // A separate scratch cap rejects genuinely unbounded expansion.
    let mut sign=CoreAffineSign::<u64>::new();
    assert!(sign.push((0..=AFFINE_SIGN_SCRATCH as u64).collect()).is_none());
    println!("CPS_AFFINE_PHASE_CANCELLATION transient=PASS final_cap=PASS mixed_z8=PASS scratch_reject=PASS");
}

#[test]
fn hoare_cps_sparse_rr(){
    let h=CpsCore::circuit(1,&[G::H(0),G::H(0)]).unwrap();
    let omega=CpsCore::circuit(1,&[G::H(0),G::S(0),G::H(0)]).unwrap();
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);ps.v.get_fresh_var();
    let elim=CpsCore::canonical(ps,Anf::from([0])).unwrap();
    for (a,rule) in [(h,GuardedRule::Hh),(omega,GuardedRule::Omega),(elim,GuardedRule::Elim)]{
        let (b,r)=a.rr_step().unwrap();assert_eq!(r.native.rule,rule);
        let sa=a.to_sparse().unwrap();let (sb,sr)=sa.sparse_rr_step().unwrap();
        assert_eq!((sr.rule,&sr.removed,sr.scale2,sb.k),(rule,&r.native.removed,r.native.scale2,b.k));
        assert_eq!(sparse_core_matrix(&sb),core_matrix(&b));
        assert_eq!(sa.replay_sparse_rr(&[sr.clone()]).unwrap().rr_snapshot(),sb.rr_snapshot());
        let mut bad=sr;bad.after.k+=1;assert!(sa.replay_sparse_rr(&[bad]).is_none());
    }
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);ps.v.next_id=128;
    let y=ps.v.get_fresh_var();let v=ps.v.get_fresh_var();
    ps.f.functions[0]=CoreBool::from_iter([vec![v]]);
    ps.p.add_term(vec![0,y],quprs::PhaseCoeff::HALF);
    ps.p.add_term(vec![y,v],quprs::PhaseCoeff::HALF);
    let a=CpsCore::<SparseGuardFrame>::shared_from_parts(ps,vec![SparseAnf::from([SparseMono::new(vec![]).unwrap()])],2).unwrap();
    let (b,r)=a.sparse_rr_step().unwrap();
    assert_eq!((r.rule,r.removed.as_slice(),b.k),(GuardedRule::Hh,[128u32,129].as_slice(),0));
    assert_eq!(sparse_core_matrix(&a),sparse_core_matrix(&b).into_iter().map(|row|row.into_iter().map(|v|scale_guarded_entry(v,2)).collect::<Vec<_>>()).collect::<Vec<_>>());
    assert_eq!(a.replay_sparse_rr(&[r]).unwrap().rr_snapshot(),b.rr_snapshot());
    println!("CPS_SPARSE_RR elim=PASS hh=PASS omega=PASS high_id=PASS replay=PASS mutant=REJECTED");
}

// Same exact two-copy norm obligation, indexed by stable native IDs.
// Use existing Cnf gates and FactorPilot gate interning. Sparse factoring
// uses the same Shannon identity p=p0 XOR (x AND p1).
fn sparse_factor_anf(f:&mut FactorPilot,p:&SparseAnf,map:&BTreeMap<u32,Lit>,
                     cache:&mut BTreeMap<(Vec<Lit>,SparseAnf),Lit>,key_bits:&[Lit])->Option<Lit>{
    f.work=f.work.checked_add(p.len().max(1))?;
    if f.work>2_000_000{return None;}
    let key=(key_bits.to_vec(),p.clone());
    if let Some(&v)=cache.get(&key){return Some(v);}
    let out=if p.len()<=1{
        let mut acc=ZERO;
        for m in p{
            let mut t=ONE;
            for id in m.ids(){t=f.gate(false,t,*map.get(id)?)?;}
            acc=f.gate(true,acc,t)?;
        }
        acc
    }else{
        let id=*p.iter().flat_map(|m|m.ids()).min()?;
        let mut a=SparseAnf::new();let mut b=SparseAnf::new();
        for m in p{
            if m.contains_id(id){b.insert(m.without_id(id));}
            else{a.insert(m.clone());}
        }
        let x=sparse_factor_anf(f,&a,map,cache,key_bits)?;
        let y=sparse_factor_anf(f,&b,map,cache,key_bits)?;
        let t=f.gate(false,*map.get(&id)?,y)?;
        f.gate(true,x,t)?
    };
    cache.insert(key,out);Some(out)
}
impl CpsCore<SparseGuardFrame>{
    fn sparse_norm_plan(&self,dag:bool)->Option<(Cnf,[Lit;3],usize,i32)>{
        if !self.shared_valid()||self.n()!=self.q(){println!("CPS_SPARSE_ENCODER_DETAIL invalid-core-or-shape");return None;}
        let n=self.n();let h=self.guard.ids.len().checked_sub(n)?;
        let primary=n.checked_add(h.checked_mul(2)?)?;
        // Scoped encoder budget, not a count precision limit.
        if primary>1024{println!("CPS_SPARSE_ENCODER_DETAIL primary-cap primary={primary} limit=1024");return None;}
        let l:Vec<Lit>=(0..n+h).map(|i|i as Lit+2).collect();
        let r:Vec<Lit>=(0..n).map(|i|i as Lit+2).chain((n+h..primary).map(|i|i as Lit+2)).collect();
        let maps:Vec<BTreeMap<u32,Lit>>=[&l,&r].iter().map(|bits|self.guard.ids.iter().copied().zip(bits.iter().copied()).collect()).collect();
        let output=self.ps.f.functions.iter().map(core_storage_anf::<SparseGuardFrame>).collect::<Option<Vec<_>>>().or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL output-anf");None})?;
        let phase:BTreeMap<Vec<u32>,u8>=self.ps.p.terms.iter().map(|(m,c)|Some((m.clone(),core_phase8(c)?))).collect::<Option<_>>().or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL phase-domain");None})?;
        if dag{
            if phase.values().any(|&k|k!=4){return None;}
            let mut f=FactorPilot{c:Cnf::new(primary),gates:BTreeMap::new(),polys:BTreeMap::new(),work:0};
            let mut cache=BTreeMap::new();
            for g in &self.guard.factors{
                for (map,bits) in maps.iter().zip([&l,&r]){
                    let v=sparse_factor_anf(&mut f,g,map,&mut cache,bits)?;f.c.enforce(v);
                }
            }
            for o in &output{
                let a=sparse_factor_anf(&mut f,o,&maps[0],&mut cache,&l)?;
                let b=sparse_factor_anf(&mut f,o,&maps[1],&mut cache,&r)?;
                let d=f.gate(true,a,b)?;f.c.enforce(-d);
            }
            let sign:SparseAnf=phase.keys().cloned().map(SparseMono::new).collect::<Option<_>>()?;
            let a=sparse_factor_anf(&mut f,&sign,&maps[0],&mut cache,&l)?;
            let b=sparse_factor_anf(&mut f,&sign,&maps[1],&mut cache,&r)?;
            let d=f.gate(true,a,b)?;
            if !f.bounded(){return None;}
            Some((f.c,[ZERO,ZERO,d],primary,self.k))
        }else{
            let mut c=Cnf::new(primary);
            for g in &self.guard.factors{
                for map in &maps{
                    let v=cps_guard_algebra::sparse_guard_lit(&mut c,g,map).or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL flat-guard-literal");None})?;c.enforce(v);
                }
            }
            for o in &output{
                let a=cps_guard_algebra::sparse_guard_lit(&mut c,o,&maps[0]).or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL flat-output-left");None})?;
                let b=cps_guard_algebra::sparse_guard_lit(&mut c,o,&maps[1]).or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL flat-output-right");None})?;
                let d=c.xor(a,b);c.enforce(-d);
            }
            let guard_output_vars=c.vars;let guard_output_clauses=c.clauses.len();
            let mut accs=Vec::new();
            for (j,map) in maps.iter().enumerate(){
                let mut acc=[ZERO;3];
                for (m,&k) in &phase{
                    let mono=SparseMono::new(m.clone()).or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL flat-phase-monomial");None})?;
                    let v=cps_guard_algebra::sparse_guard_lit(&mut c,&SparseAnf::from([mono]),map).or_else(||{println!("CPS_SPARSE_ENCODER_DETAIL flat-phase-literal");None})?;
                    let k=if j==0{k}else{(8-k)%8};
                    let term=std::array::from_fn(|i|if k>>i&1!=0{v}else{ZERO});
                    acc=c.add3(acc,term);
                }
                accs.push(acc);
            }
            let d=c.add3(accs[0],accs[1]);
            if c.vars>10_000||c.clauses.len()>40_000{
                println!("CPS_SPARSE_ENCODER_DETAIL flat-final-cap primary={primary} vars={} clauses={} var_limit=10000 clause_limit=40000 guard_output_vars={guard_output_vars} guard_output_clauses={guard_output_clauses} phase_terms={}",c.vars,c.clauses.len(),phase.len());
                return None;
            }
            Some((c,d,primary,self.k))
        }
    }
    fn sparse_terminal(&self)->Option<&'static str>{
        if self.guard.factors.iter().any(|g|g.is_empty()){return Some("REFUTED");}
        if self.guard.ids.len()!=self.n(){return None;}
        if self.k>0{return Some("REFUTED");}
        if self.k!=0{return None;}
        Some(if self.guard.factors.iter().all(|g|g==&SparseAnf::from([SparseMono::new(vec![]).unwrap()])){"PROVED"}else{"REFUTED"})
    }
}
fn sparse_matched_finish(mut c:CpsCore<SparseGuardFrame>,dir:&std::path::Path,policy:&str,dag:bool,
                         build_ns:u128,stage:&mut &str)->Option<()>{
    *stage="initial-snapshot";
    let snap=c.rr_snapshot()?;
    std::fs::write(dir.join("initial.txt"),format!("k={}\n{snap:?}\n",c.k)).ok()?;
    let initial_h=c.guard.ids.len()-c.n();let t=std::time::Instant::now();
    let mut receipts=Vec::new();
    if policy!="wmc"{
        let start=c.clone();
        for _ in 0..32{
            let Some((next,r))=c.sparse_rr_step() else{break;};
            receipts.push(r);c=next;
        }
        if start.replay_sparse_rr(&receipts)?.rr_snapshot()!=c.rr_snapshot(){return None;}
        std::fs::write(dir.join("sparse-rr.txt"),format!("{receipts:?}")).ok()?;
    }
    let rr_ns=t.elapsed().as_nanos();let steps=receipts.len();
    let status=if policy=="wmc"{"READY"}else if let Some(v)=c.sparse_terminal(){v}else if policy=="rr"{"UNKNOWN"}else{"READY"};
    let mut primary=0;let mut vars=0;let mut clauses=0;let mut phase="-".to_owned();let mut encode_ns=0;
    if status=="READY"{
        let t=std::time::Instant::now();
        *stage=if dag{"dag-encoder"}else{"flat-encoder"};
        let (cnf,d,p,k)=c.sparse_norm_plan(dag)?;
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
}
