//! Research-only source admission pilot. No new amplitude representation
//! in the verification path; native P/f/v are kept until the residual.
//! Exact finite enumeration is a bounded reference oracle, not WMC.
#[path="support/native_dyadic_cnf.rs"]
mod native_dyadic_cnf;
use native_dyadic_cnf::{Anf,native_dyadic_projection_variant};
use quprs::PathSum;
use quprs::ir::QuantumOp;
use quprs::qasm::{parse_qasm_str,parse_qasm_str_source_pinned};
use quprs::rational::{Angle,FreeRational};
use std::collections::BTreeMap;
use rustc_hash::FxHashSet;

const TERM_CAP:usize=8192;
fn h(ps:&PathSum)->usize {ps.v.path_vars.len()-ps.v.num_qubits}
fn terms(ps:&PathSum)->usize{ps.p.terms.len()+ps.f.functions.iter().map(|f|f.len()).sum::<usize>()}
fn admitted(ps:&PathSum)->bool{
    let n=ps.v.num_qubits;
    !ps.rr_approximate&&ps.rr_tolerance==0.0&&ps.v.continuous_vars.is_empty()
        &&(0..n).all(|i|ps.v.path_vars.contains(&(i as u32)))
        &&ps.f.functions.len()==n&&terms(ps)<=TERM_CAP
        &&ps.p.terms.iter().all(|(m,c)|c.radians.is_none()&&c.symbols.is_empty()
            &&c.constant.denom>0&&m.iter().all(|v|ps.v.path_vars.contains(v)))
        &&ps.f.functions.iter().flatten().all(|m|m.iter().all(|v|ps.v.path_vars.contains(v)))
}
// No compact bit masks or Z8 admission before RR. Restrict HH to
// internal targets, reconstruct its exact matcher and cap substitution.
fn hh_target(ps:&PathSum,y:u32)->Option<u32>{
    let mut phi:FxHashSet<Vec<u32>>=FxHashSet::default();
    for (m,c) in &ps.p.terms{
        if !m.contains(&y){continue;}
        if !c.is_pure_half(){return None;}
        let t:Vec<_>=m.iter().copied().filter(|&v|v!=y).collect();
        if !phi.insert(t.clone()){phi.remove(&t);}
    }
    let target=phi.iter().filter(|m|m.len()==1)
        .filter(|m|phi.iter().all(|t|t==*m||!t.contains(&m[0])))
        .map(|m|m[0]).max()?;
    if (target as usize)<ps.v.num_qubits||phi.len()>9{return None;}
    Some(target)
}
#[derive(Default)]
struct Receipt{scale2:u32,elim:usize,hh:usize,omega:usize,limit:bool}
fn reduce(mut ps:PathSum)->(PathSum,Receipt){
    let mut r=Receipt::default();
    for _ in 0..512{
        if !admitted(&ps){r.limit=true;return (ps,r);}
        let mut ids=ps.get_reducible_vars();ids.sort_unstable();
        let mut chosen=None;
        for &y in &ids{
            for rule in 0..3{
                if rule==2&&hh_target(&ps,y).is_none(){continue;}
                let target=if rule==2{hh_target(&ps,y)}else{None};
                let mut t=ps.clone();
                let ok=match rule{0=>t.try_reduce_elim(&[y]),1=>t.try_reduce_omega(&[y]),_=>t.try_reduce_hh(&[y])};
                if !ok{continue;}
                let mut removed:Vec<_>=ps.v.path_vars.difference(&t.v.path_vars).copied().collect();
                removed.sort_unstable();
                let mut expected=vec![y];if let Some(v)=target{expected.push(v);}expected.sort_unstable();
                assert_eq!(removed,expected);
                assert!(t.v.path_vars.is_subset(&ps.v.path_vars));
                if !admitted(&t){r.limit=true;continue;}
                chosen=Some((t,rule));break;
            }
            if chosen.is_some(){break;}
        }
        let Some((next,rule))=chosen else{return (ps,r);};
        match rule{0=>{r.elim+=1;r.scale2+=2;},1=>{r.omega+=1;r.scale2+=1;},_=>{r.hh+=1;r.scale2+=2;}}
        ps=next;
    }
    r.limit=true;(ps,r)
}
fn reduce_until(mut ps:PathSum,deadline:std::time::Instant)->(PathSum,Receipt,usize,bool){
    let mut attempts=0usize;
    let mut r=Receipt::default();
    for _ in 0..512{
        if std::time::Instant::now()>=deadline{return (ps,r,attempts,true);}
        if !admitted(&ps){r.limit=true;return (ps,r,attempts,false);}
        let mut ids=ps.get_reducible_vars();ids.sort_unstable();
        let mut chosen=None;
        for &y in &ids{
            for rule in 0..3{
                if rule==2&&hh_target(&ps,y).is_none(){continue;}
                let target=if rule==2{hh_target(&ps,y)}else{None};
                if std::time::Instant::now()>=deadline{return (ps,r,attempts,true);}
                attempts+=1;
                let mut t=ps.clone();
                let ok=match rule{0=>t.try_reduce_elim(&[y]),1=>t.try_reduce_omega(&[y]),_=>t.try_reduce_hh(&[y])};
                if !ok{continue;}
                let mut removed:Vec<_>=ps.v.path_vars.difference(&t.v.path_vars).copied().collect();
                removed.sort_unstable();
                let mut expected=vec![y];if let Some(v)=target{expected.push(v);}expected.sort_unstable();
                assert_eq!(removed,expected);
                assert!(t.v.path_vars.is_subset(&ps.v.path_vars));
                if !admitted(&t){r.limit=true;continue;}
                chosen=Some((t,rule));break;
            }
            if chosen.is_some(){break;}
        }
        let Some((next,rule))=chosen else{return (ps,r,attempts,false);};
        match rule{0=>{r.elim+=1;r.scale2+=2;},1=>{r.omega+=1;r.scale2+=1;},_=>{r.hh+=1;r.scale2+=2;}}
        ps=next;
    }
    r.limit=true;(ps,r,attempts,false)
}


#[derive(Default)]
struct HhScanMetrics{calls:usize,visits:usize,incidences:usize}
type HhIncident<'a>=BTreeMap<u32,Vec<(&'a Vec<u32>,&'a quprs::PhaseCoeff)>>;
fn hh_target_counted<'a>(n:usize,y:u32,terms:impl IntoIterator<Item=(&'a Vec<u32>,&'a quprs::PhaseCoeff)>,
    metrics:&mut HhScanMetrics)->Option<u32>{
    metrics.calls+=1;
    let mut phi:FxHashSet<Vec<u32>>=FxHashSet::default();
    for (m,c) in terms{
        metrics.visits+=1;
        if !m.contains(&y){continue;}
        if !c.is_pure_half(){return None;}
        let t:Vec<_>=m.iter().copied().filter(|&v|v!=y).collect();
        if !phi.insert(t.clone()){phi.remove(&t);}
    }
    let target=phi.iter().filter(|m|m.len()==1)
        .filter(|m|phi.iter().all(|t|t==*m||!t.contains(&m[0])))
        .map(|m|m[0]).max()?;
    if (target as usize)<n||phi.len()>9{return None;}
    Some(target)
}
fn reduce_indexed(ps:PathSum,deadline:std::time::Instant,indexed:bool)->(PathSum,Receipt,usize,usize,bool,Vec<(u32,usize,Option<u32>)>){
    reduce_indexed_hh(ps,deadline,indexed,false,&mut HhScanMetrics::default())
}
fn reduce_indexed_hh(mut ps:PathSum,deadline:std::time::Instant,indexed:bool,hh_indexed:bool,metrics:&mut HhScanMetrics)->(PathSum,Receipt,usize,usize,bool,Vec<(u32,usize,Option<u32>)>){
    let mut skipped=0usize;let mut trace=Vec::new();
    let mut attempts=0usize;
    let mut r=Receipt::default();
    for _ in 0..512{
        if std::time::Instant::now()>=deadline{return (ps,r,attempts,skipped,true,trace);}
        if !admitted(&ps){r.limit=true;return (ps,r,attempts,skipped,false,trace);}
        let mut ids=ps.get_reducible_vars();ids.sort_unstable();
        let mut chosen=None;
        // Index is rebuilt after every accepted rewrite, never reused stale.
        let mut used=FxHashSet::default();
        let mut nonhalf=FxHashSet::default();
        let mut incident:HhIncident<'_>=BTreeMap::new();
        if indexed{
            for (mono,c) in &ps.p.terms{
                for &v in mono{
                    used.insert(v);
                    if hh_indexed{incident.entry(v).or_default().push((mono,c));metrics.incidences+=1;}
                    if mono.len()>1&&c.constant!=quprs::Rational::HALF{nonhalf.insert(v);}
                }
            }
        }
        for &y in &ids{
            for rule in 0..3{
                let target=if rule==2{
                    if hh_indexed{
                        hh_target_counted(ps.v.num_qubits,y,incident.get(&y).into_iter().flatten().copied(),metrics)
                    }else{hh_target_counted(ps.v.num_qubits,y,&ps.p.terms,metrics)}
                }else{None};
                if rule==2&&target.is_none(){continue;}
                // Necessary conditions only, derived from exact native matcher.
                // admitted() has excluded symbolic/approximate/radian inputs.
                if indexed{
                    let impossible=match rule{
                        0=>used.contains(&y),
                        1=>nonhalf.contains(&y)||!ps.p.terms.get(&vec![y]).is_some_and(|c|
                            c.constant==quprs::Rational::QUARTER||c.constant==quprs::Rational::THREE_QUARTERS),
                        _=>false,
                    };
                    if impossible{skipped+=1;continue;}
                }
                if std::time::Instant::now()>=deadline{return (ps,r,attempts,skipped,true,trace);}
                attempts+=1;
                let mut t=ps.clone();
                let ok=match rule{0=>t.try_reduce_elim(&[y]),1=>t.try_reduce_omega(&[y]),_=>t.try_reduce_hh(&[y])};
                if !ok{continue;}
                let mut removed:Vec<_>=ps.v.path_vars.difference(&t.v.path_vars).copied().collect();
                removed.sort_unstable();
                let mut expected=vec![y];if let Some(v)=target{expected.push(v);}expected.sort_unstable();
                assert_eq!(removed,expected);
                assert!(t.v.path_vars.is_subset(&ps.v.path_vars));
                if !admitted(&t){r.limit=true;continue;}
                trace.push((y,rule,target));chosen=Some((t,rule));break;
            }
            if chosen.is_some(){break;}
        }
        let Some((next,rule))=chosen else{return (ps,r,attempts,skipped,false,trace);};
        match rule{0=>{r.elim+=1;r.scale2+=2;},1=>{r.omega+=1;r.scale2+=1;},_=>{r.hh+=1;r.scale2+=2;}}
        drop(incident);
        ps=next;
    }
    r.limit=true;(ps,r,attempts,skipped,false,trace)
}


// Strict narrow independent parser for these immutable source files.
// All lines are accounted for. Compare operation-by-operation against
// the native compatibility parser; do not silently flatten registers.
fn source_ops(src:&str)->(Vec<QuantumOp>,usize,usize){
    let mut regs=BTreeMap::<String,(usize,usize)>::new();
    let mut n=0usize;let mut rx=0usize;let mut ops=Vec::new();
    let mut header=false;let mut include=false;
    for raw in src.lines(){
        let l=raw.split("//").next().unwrap().trim();if l.is_empty(){continue;}
        if l=="OPENQASM 2.0;"{assert!(!header&&regs.is_empty());header=true;continue;}
        if l=="include \"qelib1.inc\";"{assert!(header&&!include&&regs.is_empty());include=true;continue;}
        assert!(header&&include);
        let l=l.strip_suffix(';').unwrap();
        if let Some(reg)=l.strip_prefix("qreg "){
            assert!(ops.is_empty());let (name,count)=reg.split_once('[').unwrap();
            let count:usize=count.strip_suffix(']').unwrap().parse().unwrap();
            assert!(count>0&&regs.insert(name.to_owned(),(n,count)).is_none());n+=count;continue;
        }
        let (gate,args)=l.split_once(' ').unwrap();
        let wires:Vec<_>=args.split(',').map(|a|{
            let (reg,i)=a.trim().split_once('[').unwrap();
            let i:usize=i.strip_suffix(']').unwrap().parse().unwrap();
            let &(offset,size)=regs.get(reg).unwrap();assert!(i<size);offset+i
        }).collect();
        let q=wires[0];assert_eq!(wires.len(),if gate=="cx"{2}else{1});
        let angle=|num,den|Angle::new_constant(FreeRational::new(num,den));
        let op=match gate{
            "s"=>QuantumOp::S(q),"t"=>QuantumOp::T(q),"tdg"=>QuantumOp::TDG(q),
            "x"=>QuantumOp::X(q),"cx"=>{assert_ne!(q,wires[1]);QuantumOp::CX(q,wires[1])},
            "rx(pi/2)"=>{rx+=1;QuantumOp::RX(q,Angle::HALF)},
            "rz(-3*pi/2)"=>QuantumOp::RZ(q,angle(-3,2)),
            "rz(pi/8)"=>QuantumOp::RZ(q,angle(1,8)),
            "rz(-pi/8)"=>QuantumOp::RZ(q,angle(-1,8)),
            "rz(pi/16)"=>QuantumOp::RZ(q,angle(1,16)),
            "rz(-pi/16)"=>QuantumOp::RZ(q,angle(-1,16)),
            _=>panic!("unexpected source gate {gate}"),
        };ops.push(op);
    }
    assert!(header&&include);(ops,n,rx)
}

 // Phase-congruence quotient, a count-preserving transformation on
 // the two-copy native phase polynomial, NOT an amplitude encoding.
 // It consumes a mandatory low-bit-zero condition of the projected
 // counting problem. Transport every Boolean equality simultaneously.
 type Poly=FxHashSet<Vec<u32>>;
 use quprs::pathsum::PhasePolynomial;
 struct PairPhase{
     phase:PhasePolynomial, constraints:Vec<Poly>, live:std::collections::BTreeSet<u32>, n:usize
 }
 fn toggle(p:&mut Poly,mut m:Vec<u32>){
     m.sort_unstable();m.dedup();if !p.insert(m.clone()){p.remove(&m);}
 }
 fn quotient_den(p:&PhasePolynomial)->Option<u32>{
     let mut d=2u32;
     for c in p.terms.values(){
         if c.radians.is_some()||!c.symbols.is_empty(){return None;}
         let v=u32::try_from(c.constant.denom).ok()?;
         if !v.is_power_of_two()||v>64{return None;}
         d=d.max(v);
     }
     Some(d)
 }
 fn paired_phase(ps:&PathSum)->Option<PairPhase>{
     if !admitted(ps)||ps.v.num_qubits!=5{return None;}
     let n=ps.v.num_qubits;
     let mut ids:Vec<_>=ps.v.path_vars.iter().copied().collect();ids.sort_unstable();
     let h=ids.len()-n;
     let l:BTreeMap<_,_>=ids.iter().enumerate().map(|(i,&id)|(id,i as u32)).collect();
     let r:BTreeMap<_,_>=ids.iter().enumerate().map(|(i,&id)|(id,(if i<n{i}else{i+h}) as u32)).collect();
     let mut phase=PhasePolynomial::new();
     for (m,c) in &ps.p.terms{
         for (map,k) in [(&l,1),(&r,-1)]{
             let mut a=c.clone();a.mul_scalar_logic(k);
             phase.add_term(m.iter().map(|id|map[id]).collect(),a);
         }
     }
     let mut constraints=vec![Poly::from_iter([vec![4]])]; // x4=0
     for o in &ps.f.functions{
         let mut eq=Poly::default();
         for m in o{for map in [&l,&r]{toggle(&mut eq,m.iter().map(|id|map[id]).collect());}}
         constraints.push(eq);
     }
     let mut bad=Poly::from_iter([vec![]]); // output4=1
     for m in &ps.f.functions[4]{toggle(&mut bad,m.iter().map(|id|l[id]).collect());}
     constraints.push(bad);
     Some(PairPhase{phase,constraints,live:(0..(n+2*h) as u32).collect(),n})
 }
 fn lowbit_candidates(p:&PairPhase,d:u32)->(Poly,Vec<u32>){
     let odd:Poly=p.phase.terms.iter().filter(|(_,c)|
         (d as i128*c.constant.numer as i128/c.constant.denom as i128).rem_euclid(2)==1)
         .map(|(m,_)|m.clone()).collect();
     let mut ids:Vec<_>=odd.iter().filter(|m|m.len()==1&&(m[0] as usize)>=p.n)
         .filter(|m|odd.iter().all(|q|q==*m||!q.contains(&m[0])))
         .map(|m|m[0]).collect();ids.sort_unstable();
     (odd,ids)
 }
 fn quotient_step(p:&mut PairPhase)->Option<(u32,u32,usize)>{
     let d=quotient_den(&p.phase)?;
     if d<=2{return None;} // no mandatory low bit remains
     let (mut odd,ids)=lowbit_candidates(p,d);
     let y=*ids.first()?;
     odd.remove(&vec![y]);
     if odd.len()>8{return None;}
     let affected=p.phase.terms.keys().filter(|m|m.contains(&y)).count();
     if affected.checked_mul(1usize<<odd.len())?>32768{return None;}
     let work=p.constraints.iter().map(|g|g.iter().filter(|m|m.contains(&y)).count()).sum::<usize>();
     if work.checked_mul(odd.len().max(1))?>32768{return None;}
     let mut phase=p.phase.clone();
     phase.substitute_var_with_poly(y,&odd);
     if phase.terms.len()>8192||quotient_den(&phase)?>d/2{return None;}
     let mut constraints=Vec::new();
     for g in &p.constraints{
         let mut q=Poly::default();
         for m in g{
             if m.contains(&y){
                 let base:Vec<_>=m.iter().copied().filter(|&v|v!=y).collect();
                 for a in &odd{let mut term=base.clone();term.extend(a);toggle(&mut q,term);}
             }else{toggle(&mut q,m.clone());}
         }
         if q.len()>8192{return None;}
         constraints.push(q);
     }
     assert!(phase.terms.keys().all(|m|!m.contains(&y)));
     assert!(constraints.iter().flatten().all(|m|!m.contains(&y)));
     assert!(p.live.remove(&y));p.phase=phase;p.constraints=constraints;
     Some((y,d,odd.len()))
 }
 fn quotient_profile(ps:&PathSum,name:&str,specialized:bool){
     let Some(mut p)=paired_phase(ps) else{return;};
     let d0=quotient_den(&p.phase).unwrap();
     let (odd,ids)=lowbit_candidates(&p,d0);
     let t0=p.phase.terms.len();let g0=p.constraints.iter().map(|g|g.len()).sum::<usize>();let v0=p.live.len();
     let mut steps=0;let mut selector_max=0;
     for _ in 0..6{let Some((_,_,size))=quotient_step(&mut p) else{break;};steps+=1;selector_max=selector_max.max(size);}
     println!("HOARE_PAPER_PHASE_QUOTIENT name={name} specialized={specialized} d0={d0} odd_terms={} isolated_pivots={} steps={steps} d1={} primary_before={v0} primary_after={} phase_before={t0} phase_after={} guard_before={g0} guard_after={} selector_max={selector_max}",
         odd.len(),ids.len(),quotient_den(&p.phase).unwrap(),p.live.len(),p.phase.terms.len(),p.constraints.iter().map(|g|g.len()).sum::<usize>());
 }
 fn test_pair_counts(p:&PairPhase,fixed:Option<bool>)->[usize;2]{
     let ids:Vec<_>=p.live.iter().copied().collect();
     let map:BTreeMap<_,_>=ids.iter().enumerate().map(|(i,&v)|(v,i)).collect();
     let d=quotient_den(&p.phase).unwrap() as i128;
     let mut counts=[0usize;2];
     for x in 0..1u64<<ids.len(){
         if fixed.is_some_and(|v|v!=(x&1!=0)){continue;}
         let truth=|m:&Vec<u32>|m.iter().all(|v|x>>map[v]&1!=0);
         if p.constraints.iter().any(|g|g.iter().fold(false,|a,m|a^truth(m))){continue;}
         let v=p.phase.terms.iter().filter(|(m,_)|truth(m)).map(|(_,c)|d*c.constant.numer as i128/c.constant.denom as i128).sum::<i128>().rem_euclid(d);
         if v==0{counts[0]+=1;}else if v==d/2{counts[1]+=1;}
     }
     counts
 }
 #[test]
 fn native_phase_congruence_quotient(){
     use quprs::{Rational,PhaseCoeff};
     let mut seed=20261125u32;let mut next=||{seed=seed.wrapping_mul(1664525).wrapping_add(1013904223);seed>>16};
     let mut checks=0;let mut nonlinear=0;
     for d in [4i64,8,16,32,64]{
         for _ in 0..64{
             let ids=[0u32,1,70,71];let mut phase=PhasePolynomial::new();
             for m in 0..16usize{
                 let mut k=next() as i64%d;
                 if m&8!=0{k=if m==8{k|1}else{k&!1};}
                 let mono=(0..4).filter(|&i|m>>i&1!=0).map(|i|ids[i]).collect();
                 phase.add_term(mono,PhaseCoeff::new_constant(Rational::new(k,d)));
             }
             let mut g=Poly::default();
             for m in 0..16usize{if next()&1!=0{toggle(&mut g,(0..4).filter(|&i|m>>i&1!=0).map(|i|ids[i]).collect());}}
             let mut p=PairPhase{phase,constraints:vec![g],live:ids.into_iter().collect(),n:71};
             // The only internal candidates are high IDs (0/1 remain
             // fixed labels). Other odd terms may depend on ID70; force
             // the specified pivot71 by excluding 70 as an input-like
             // coordinate from pivot admission for this finite oracle.
             let before=[None,Some(false),Some(true)].map(|v|test_pair_counts(&p,v));
             let (odd,_)=lowbit_candidates(&p,d as u32);
             if odd.iter().any(|m|m.len()>1){nonlinear+=1;}
             let (y,old,_)=quotient_step(&mut p).unwrap();assert_eq!((y,old),(71,d as u32));
             assert_eq!(p.live.len(),3);
             assert!(quotient_den(&p.phase).unwrap()<=d as u32/2);
             for (i,v) in [None,Some(false),Some(true)].into_iter().enumerate(){
                 assert_eq!(before[i],test_pair_counts(&p,v));checks+=2;
             }
         }
     }
     println!("HOARE_NATIVE_PHASE_QUOTIENT cases=320 buckets={checks} nonlinear={nonlinear} high_ids=true");
 }

type Root=[i64;32];
// Compact only a bounded FINAL residual using dense local positions.
// The original stable IDs may exceed 64; no bit shift uses those IDs.
fn entries(ps:&PathSum)->Option<Vec<Root>>{
    let n=ps.v.num_qubits;let h=h(ps);
    if n>5||h>16||!admitted(ps){return None;}
    let work=(1usize<<n).checked_mul(1usize<<h)?.checked_mul(terms(ps).max(1))?;
    if work>30_000_000{return None;}
    let mut ids:Vec<_>=ps.v.path_vars.iter().copied().collect();ids.sort_unstable();
    let map:BTreeMap<_,_>=ids.iter().enumerate().map(|(i,&v)|(v,i)).collect();
    let mask=|m:&[u32]|m.iter().fold(0u64,|a,v|a|(1u64<<map[v]));
    let mut phase=Vec::new();
    for (m,c) in &ps.p.terms{
        let k=64i128*c.constant.numer as i128;let d=c.constant.denom as i128;
        if k%d!=0{return None;}
        phase.push((mask(m),(k/d).rem_euclid(64) as usize));
    }
    let f:Vec<Vec<_>>=ps.f.functions.iter().map(|p|p.iter().map(|m|mask(m)).collect()).collect();
    let mut out=vec![[0;32];1usize<<(2*n)];
    for x in 0..1u64<<n{
        for y in 0..1u64<<h{
            let a=x|(y<<n);
            let z=f.iter().enumerate().fold(0usize,|z,(i,p)|z|((p.iter().fold(false,|b,&m|b^(a&m==m)) as usize)<<i));
            let k=phase.iter().filter(|(m,_)|a&*m==*m).map(|(_,k)|*k).sum::<usize>()%64;
            out[((x as usize)<<n)|z][k%32]+=if k<32{1}else{-1};
        }
    }
    Some(out)
}
#[test]
fn native_rr_stable_ids_beyond_64(){
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    for _ in 0..96{QuantumOp::H(0).apply(&mut ps,false);}
    assert_eq!(h(&ps),96);
    let (ps,r)=reduce(ps);
    assert!(!r.limit);assert_eq!(h(&ps),0);assert_eq!(r.scale2,96);
    assert!(ps.v.path_vars.contains(&0));
    assert_eq!(ps.f.functions[0],FxHashSet::from_iter([vec![0]]));
    // One residual variable with stable ID greater than 64.
    let y=ps.v.path_vars.iter().copied().max().unwrap();
    assert_eq!(y,0);
    let mut ps=ps;QuantumOp::H(0).apply(&mut ps,false);
    assert!(ps.v.path_vars.iter().any(|&v|v>64));
    assert!(entries(&ps).is_some());
    println!("HOARE_NATIVE_WIDE_ID_PASS initial_h=96 residual_h=0 scale2=96 high_residual_id=true");
}

// All routes use identical encoder caps. The raw Pure WMC checkpoint is
// never reduced. The expected verdict is checked only after solving.
fn export_projected(dir:&std::path::Path,name:&str,mode:&str,ps:&PathSum,h0:usize,
                    scale2:u32,build_ns:u128,rr_ns:u128,expected_bad:bool,rows:&mut String){
    let pred=vec![Anf::from([0,16])]; // q4=0, both original pre/post
    let t=std::time::Instant::now();
    let plan=native_dyadic_projection_variant(ps,&pred,&pred,32768,262144,mode.ends_with("-heap"));
    let enc_ns=t.elapsed().as_nanos();
    let (status,vars,clauses,sign,d)=if let Some((c,sign,d))=plan{
        let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
        for row in &c.clauses{
            for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");
        }
        std::fs::write(dir.join(format!("paper-{name}-{mode}.cnf")),text).unwrap();
        ("READY",c.vars,c.clauses.len(),sign,d)
    }else{("ENCODING_LIMIT_OR_UNSUPPORTED",0,0,0,0)};
    let width=ps.v.num_qubits;let residual=h(ps);
    rows.push_str(&format!("{name}\t{mode}\t{width}\t{h0}\t{residual}\t{scale2}\t{vars}\t{clauses}\t{sign}\t{d}\t{status}\t{build_ns}\t{rr_ns}\t{enc_ns}\t{expected_bad}\n"));
    println!("HOARE_PAPER_PROJECTED_EXPORT name={name} mode={mode} h={residual} vars={vars} clauses={clauses} denominator={d} status={status} encoding_ns={enc_ns}");
}

// The original labels are fixed before the single-copy encoder runs.
// Oracle-known witnesses are explicit controls, not discovery results.
fn export_single_fibres(dir:&std::path::Path,name:&str,ps:&PathSum,scale2:u32,
                        build_ns:u128,rr_ns:u128,rows:&mut String){
    let probes:&[(u64,u64,&str,bool)]=if name=="vchain"{
        &[(0,16,"blind",false)]
    }else{
        &[(0,16,"blind",false),(0,17,"blind",false),(0,28,"oracle-control",true)]
    };
    for &(x,z,kind,expected) in probes{
        assert_eq!(x&16,0);assert_eq!(z&16,16);
        for affine in [false,true]{
            let route=if affine{"affine"}else{"fixed"};
            let key=format!("single-{name}-{x}-{z}-{route}");
            let t=std::time::Instant::now();
            let result=native_dyadic_cnf::native_dyadic_fibre(ps,x,z,affine,32768,262144);
            let enc=t.elapsed().as_nanos();
            let (status,vars,clauses,phase,d,primary)=if let Some((c,bits,d,primary))=result{
                let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                for row in &c.clauses{
                    for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");
                }
                std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                let phase=bits.iter().map(|l|l.to_string()).collect::<Vec<_>>().join(",");
                ("READY",c.vars,c.clauses.len(),phase,d,primary)
            }else{("ENCODING_LIMIT_OR_UNSUPPORTED",0,0,String::new(),0,0)};
            rows.push_str(&format!("{key}\t{name}\t{x}\t{z}\t{kind}\t{route}\t{status}\t{primary}\t{vars}\t{clauses}\t{phase}\t{d}\t{scale2}\t{build_ns}\t{rr_ns}\t{enc}\t{expected}\n"));
        }
    }
}


// Condition in native P/f/v, not only in Tseitin literals. Input
// labels remain in the domain; every eliminated hidden pivot has a
// unique assignment. A nonlinear selector is admitted only if the
// pivot occurs as an isolated singleton in the chosen output row.
fn fixed_input(mut ps:PathSum,x:u64)->PathSum{
    for i in 0..ps.v.num_qubits{
        let p=if x>>i&1==1{Poly::from_iter([vec![]])}else{Poly::default()};
        ps.f.substitute_var_with_poly(i as u32,&p);
        ps.p.substitute_var_with_poly(i as u32,&p);
    }
    ps
}
fn output_pivot(ps:&PathSum,z:u64)->Option<(PathSum,usize)>{
    output_pivot_mask(ps,(1u64<<ps.v.num_qubits)-1,z)
}
fn output_pivot_mask(ps:&PathSum,mask:u64,z:u64)->Option<(PathSum,usize)>{
    let n=ps.v.num_qubits;
    let mut candidates=Vec::new();
    for (i,row) in ps.f.functions.iter().enumerate(){
        if mask>>i&1==0{continue;}
        for m in row.iter().filter(|m|m.len()==1&&(m[0] as usize)>=n){
            let y=m[0];
            if row.iter().any(|q|q!=m&&q.contains(&y)){continue;}
            let mut sel=row.clone();sel.remove(m);
            if z>>i&1==1{toggle(&mut sel,vec![]);}
            if sel.len()>8{continue;}
            let affected=ps.p.terms.keys().filter(|m|m.contains(&y)).count();
            let work=affected.checked_mul(1usize<<sel.len())?;
            let boolwork=ps.f.functions.iter().flatten().filter(|m|m.contains(&y)).count()
                .checked_mul(sel.len().max(1))?;
            if work>32768||boolwork>32768{continue;}
            candidates.push((work+boolwork,sel.len(),i,y,sel));
        }
    }
    candidates.sort_by_key(|c|(c.0,c.1,c.2,c.3));
    for (_,size,i,y,sel) in candidates{
        let mut t=ps.clone();
        t.f.substitute_var_with_poly(y,&sel);
        t.p.substitute_var_with_poly(y,&sel);
        assert!(t.v.path_vars.remove(&y));
        let expect=if z>>i&1==1{Poly::from_iter([vec![]])}else{Poly::default()};
        assert_eq!(t.f.functions[i],expect);
        if admitted(&t){return Some((t,size));}
    }
    None
}
fn condition_and_reduce(mut ps:PathSum,x:u64,z:u64,early:bool)->(PathSum,u32,usize,usize,bool){
    ps=fixed_input(ps,x);
    let mut scale=0;let mut pivots=0;let mut steps=0;let mut limited=false;
    // Interleave output equation elimination and native RR. The
    // complete output remains enforced at export, including rows
    // not eligible for elimination and contradictory constant rows.
    for round in 0..=ps.v.num_qubits{
        if early||round>0{
            let (t,r)=reduce(ps);ps=t;scale+=r.scale2;
            steps+=r.elim+r.hh+r.omega;limited|=r.limit;
        }
        if let Some((t,_))=output_pivot(&ps,z){ps=t;pivots+=1;}
        else{
            if !early&&round==0{
                let (t,r)=reduce(ps);ps=t;scale+=r.scale2;
                steps+=r.elim+r.hh+r.omega;limited|=r.limit;
                if let Some((t,_))=output_pivot(&ps,z){ps=t;pivots+=1;continue;}
            }
            break;
        }
    }
    assert!(admitted(&ps));
    (ps,scale,pivots,steps,limited)
}
#[test]
fn native_output_conditioned_rr_exact(){
    use quprs::{Rational,PhaseCoeff};
    let mut checks=0;let mut pivots=0;let mut nonlinear=0;let mut rr_steps=0;
    // Synthetic path sums with nonlinear isolated selectors, high
    // stable IDs and exact D64 phase. Full coefficient-vector equality
    // for the substitutions before RR; signed coefficient norm after RR.
    for d in [2i64,8,64]{
        for mutant in [false,true]{
            let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
            for _ in 0..70{let id=ps.v.get_fresh_var();assert!(ps.v.path_vars.remove(&id));}
            let a=ps.v.get_fresh_var();let b=ps.v.get_fresh_var();
            let c=ps.v.get_fresh_var();let y=ps.v.get_fresh_var();
            ps.f.functions[0]=Poly::from_iter([vec![0],vec![a],vec![b,c]]);
            ps.f.functions[1]=Poly::from_iter([vec![1],vec![b],vec![c]]);
            for (m,w) in [(vec![a],1),(vec![b,c],-1),(vec![a,c],2)]{
                ps.p.add_term(m,PhaseCoeff::new_constant(Rational::new(w,d)));
            }
            if !mutant{ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new(1,2)));}
            let raw=entries(&ps).unwrap();
            for x in 0..4u64{for z in 0..4u64{
                let want=raw[(x*4+z) as usize];
                let mut t=fixed_input(ps.clone(),x);
                while let Some((next,size))=output_pivot(&t,z){
                    t=next;pivots+=1;nonlinear+=usize::from(size>1);
                }
                assert_eq!(entries(&t).unwrap()[(x*4+z) as usize],want);
                for early in [false,true]{
                    let (t,scale,_,steps,limited)=condition_and_reduce(ps.clone(),x,z,early);
                    assert!(!limited);rr_steps+=steps;
                    let got=entries(&t).unwrap()[(x*4+z) as usize];
                    let norm=|r:Root|r.into_iter().map(|v|i128::from(v)*i128::from(v)).sum::<i128>();
                    assert_eq!(norm(got).checked_shl(scale).unwrap(),norm(want));
                    checks+=1;
                }
            }}
        }
    }
    assert!(pivots>0&&nonlinear>0&&rr_steps>0);
    println!("HOARE_NATIVE_OUTPUT_CONDITIONED checks={checks} pivots={pivots} multi_term_selectors={nonlinear} rr_steps={rr_steps}");
}
fn export_conditioned_fibres(dir:&std::path::Path,name:&str,raw:&PathSum,residual:&PathSum,
    raw_scale:u32,build_ns:u128,rr_ns:u128,rows:&mut String){
    // Same predeclared probes, but run only one blind and one known
    // positive for noancilla. No source-oracle-based search policy.
    let probes:&[(u64,u64,&str,bool)]=if name=="vchain"{&[(0,16,"blind",false)]}
        else{&[(0,16,"blind",false),(0,28,"oracle-control",true)]};
    for &(x,z,kind,expected) in probes{
        for (route,base,base_scale,base_ns,early) in [
            ("condition-first",raw,0u32,0u128,false),
            ("rr-first",residual,raw_scale,rr_ns,true)]{
            let t=std::time::Instant::now();
            let (ps,scale,pivots,steps,limited)=condition_and_reduce(base.clone(),x,z,early);
            let cond_ns=t.elapsed().as_nanos();
            let scale=scale+base_scale;
            let key=format!("condition-{name}-{x}-{z}-{route}");
            if let Some(a)=entries(&ps){
                assert_eq!(a[(x*32+z) as usize].iter().any(|&v|v!=0),expected);
            }
            let t=std::time::Instant::now();
            let plan=native_dyadic_cnf::native_dyadic_fibre(&ps,x,z,false,32768,262144);
            let enc=t.elapsed().as_nanos();
            let (status,vars,clauses,phase,d,primary)=if let Some((c,bits,d,primary))=plan{
                let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                ("READY",c.vars,c.clauses.len(),bits.iter().map(|l|l.to_string()).collect::<Vec<_>>().join(","),d,primary)
            }else{("ENCODING_LIMIT_OR_UNSUPPORTED",0,0,String::new(),0,0)};
            rows.push_str(&format!("{key}\t{name}\t{x}\t{z}\t{kind}\t{route}\t{status}\t{primary}\t{vars}\t{clauses}\t{phase}\t{d}\t{scale}\t{build_ns}\t{}\t{enc}\t{expected}\n",base_ns+cond_ns));
            println!("HOARE_PAPER_CONDITIONED name={name} route={route} x={x} z={z} h_before={} h_after={} pivots={pivots} rr_steps={steps} scale2={scale} terms={} limited={limited} status={status} vars={vars} clauses={clauses} conditioning_ns={cond_ns}",h(base),h(&ps),terms(&ps));
        }
    }
}


// Freeze x before looking at any amplitudes. Reuse this exact input
// checkpoint for every forbidden output; no oracle-selected output list.
fn export_blind_fibres(dir:&std::path::Path,name:&str,raw:&PathSum,residual:&PathSum,
    raw_scale:u32,build_ns:u128,rr_ns:u128,rows:&mut String){
    let x=0u64; // first lexicographic legal input, q4=0
    for (route,base,base_scale,base_ns) in [
        ("input-first",raw,0u32,0u128),
        ("rr-first",residual,raw_scale,rr_ns)]{
        let t=std::time::Instant::now();
        let (prefix,r)=reduce(fixed_input(base.clone(),x));
        let prefix_ns=t.elapsed().as_nanos();
        let common_scale=base_scale+r.scale2;
        let common_ns=build_ns+base_ns+prefix_ns;
        println!("HOARE_PAPER_BLIND_PREFIX name={name} route={route} x={x} h_before={} h_after={} scale2={common_scale} common_ns={common_ns} prefix_ns={prefix_ns} limited={}",h(base),h(&prefix),r.limit);
        for z in 16..32u64{
            let t=std::time::Instant::now();
            let (out,s,pivots,steps,limited)=condition_and_reduce(prefix.clone(),x,z,false);
            let prep=t.elapsed().as_nanos();
            let scale=common_scale+s;
            let key=format!("blind-{name}-{route}-{x}-{z}");
            let t=std::time::Instant::now();
            let plan=native_dyadic_cnf::native_dyadic_fibre(&out,x,z,false,32768,262144);
            let enc=t.elapsed().as_nanos();
            let (status,vars,clauses,phase,d,primary)=if let Some((c,bits,d,primary))=plan{
                let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                ("READY",c.vars,c.clauses.len(),bits.iter().map(|l|l.to_string()).collect::<Vec<_>>().join(","),d,primary)
            }else{("ENCODING_LIMIT_OR_UNSUPPORTED",0,0,String::new(),0,0)};
            rows.push_str(&format!("{key}\t{name}\t{route}\t{x}\t{z}\t{status}\t{primary}\t{vars}\t{clauses}\t{phase}\t{d}\t{scale}\t{common_ns}\t{prep}\t{enc}\t{pivots}\t{steps}\t{}\t{limited}\n",h(&prefix)));
        }
    }
}
#[test]
fn native_shared_input_checkpoint_exact(){
    use quprs::{Rational,PhaseCoeff};
    let mut checks=0usize;
    for d in [2i64,8,64]{
        for cancel in [false,true]{
            let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
            let a=ps.v.get_fresh_var();let b=ps.v.get_fresh_var();let y=ps.v.get_fresh_var();
            ps.f.functions[0]=Poly::from_iter([vec![0],vec![a],vec![0,b]]);
            ps.f.functions[1]=Poly::from_iter([vec![1],vec![b]]);
            for (m,w) in [(vec![a,b],1),(vec![a],-1),(vec![0,y],2)]{
                ps.p.add_term(m,PhaseCoeff::new_constant(Rational::new(w,d)));
            }
            if cancel{ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new(1,2)));}
            let raw=entries(&ps).unwrap();
            let norm=|r:Root|r.into_iter().map(|v|i128::from(v)*i128::from(v)).sum::<i128>();
            for x in 0..4u64{
                let (prefix,r)=reduce(fixed_input(ps.clone(),x));
                assert!(!r.limit);
                for z in 0..4u64{
                    let (out,s,_,_,limited)=condition_and_reduce(prefix.clone(),x,z,false);
                    assert!(!limited);
                    let got=entries(&out).unwrap()[(x*4+z) as usize];
                    assert_eq!(norm(got).checked_shl(r.scale2+s).unwrap(),norm(raw[(x*4+z) as usize]));
                    checks+=1;
                }
            }
        }
    }
    println!("HOARE_NATIVE_SHARED_INPUT_CHECKPOINT checks={checks}");
}


// Condition only the output coordinates belonging to the sector.
// Every unselected output remains part of the native output map;
// the paired encoder must still enforce equality of ALL outputs.
fn condition_sector(mut ps:PathSum,mask:u64,z:u64)->(PathSum,u32,usize,usize,bool){
    assert!(z&!mask==0&&mask>>ps.v.num_qubits==0);
    let mut scale=0;let mut pivots=0;let mut steps=0;let mut limited=false;
    for _ in 0..mask.count_ones(){
        let Some((t,_))=output_pivot_mask(&ps,mask,z) else{break;};
        ps=t;pivots+=1;
        let (t,r)=reduce(ps);ps=t;scale+=r.scale2;
        steps+=r.elim+r.hh+r.omega;limited|=r.limit;
    }
    assert!(admitted(&ps));
    (ps,scale,pivots,steps,limited)
}
#[test]
fn native_partial_output_sector_exact(){
    use quprs::{Rational,PhaseCoeff};
    let norm=|a:&[Root],x:usize,mask:u64,z:u64|->i128{
        (0..4).filter(|&i|i as u64&mask==z)
            .flat_map(|i|a[4*x+i]).map(|v|i128::from(v)*i128::from(v)).sum()
    };
    let mut checks=0;let mut pivots=0;
    for d in [2i64,8,64]{
        for cancel in [false,true]{
            let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
            let a=ps.v.get_fresh_var();let b=ps.v.get_fresh_var();let c=ps.v.get_fresh_var();
            ps.f.functions[0]=Poly::from_iter([vec![0],vec![a],vec![b,c]]);
            ps.f.functions[1]=Poly::from_iter([vec![1],vec![b]]);
            for (m,w) in [(vec![a],1),(vec![b,c],-1),(vec![a,c],2)]{
                ps.p.add_term(m,PhaseCoeff::new_constant(Rational::new(w,d)));
            }
            if cancel{
                let y=ps.v.get_fresh_var();
                ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new(1,2)));
            }
            let raw=entries(&ps).unwrap();
            for x in 0..4u64{
                let (prefix,r)=reduce(fixed_input(ps.clone(),x));
                assert!(!r.limit);
                for mask in 0..4u64{for z in 0..4u64{
                    if z&!mask!=0{continue;}
                    let (out,s,p,_,limited)=condition_sector(prefix.clone(),mask,z);
                    assert!(!limited);pivots+=p;
                    let got=entries(&out).unwrap();
                    assert_eq!(norm(&got,x as usize,mask,z).checked_shl(r.scale2+s).unwrap(),
                        norm(&raw,x as usize,mask,z));
                    checks+=1;
                }}
            }
        }
    }
    // Distinct output labels must not cancel: H then Z at x=0.
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    QuantumOp::H(0).apply(&mut ps,false);QuantumOp::Z(0).apply(&mut ps,false);
    let a=entries(&ps).unwrap();
    assert!(a[0].iter().zip(a[1]).all(|(&u,v)|u+v==0));
    assert!(a[0].iter().any(|&v|v!=0)&&a[1].iter().any(|&v|v!=0));
    assert!(pivots>0);
    println!("HOARE_NATIVE_PARTIAL_OUTPUT_SECTOR checks={checks} pivots={pivots} distinct_output_control=true");
}
fn export_sector_inputs(dir:&std::path::Path,name:&str,residual:&PathSum,raw_scale:u32,
    build_ns:u128,rr_ns:u128,rows:&mut String){
    let common_ns=build_ns+rr_ns;
    // Complete legal input partition, no oracle-driven ordering.
    for x in 0..16u64{
        let t=std::time::Instant::now();
        let (prefix,r)=reduce(fixed_input(residual.clone(),x));
        let prefix_ns=t.elapsed().as_nanos();
        let pre:Vec<Anf>=(0..5).map(|i|if x>>i&1==1{Anf::from([1u64<<i])}
            else{Anf::from([0,1u64<<i])}).collect();
        let post=vec![Anf::from([0,16])]; // forbidden sector q4=1
        for sector in [false,true]{
            let t=std::time::Instant::now();
            let (out,s,pivots,steps,limited)=if sector{condition_sector(prefix.clone(),16,16)}
                else{(prefix.clone(),0,0,0,false)};
            let prep_ns=t.elapsed().as_nanos();
            let scale=raw_scale+r.scale2+s;
            let route=if sector{"sector-rr"}else{"input-only"};
            let key=format!("sector-{name}-{route}-{x}");
            let t=std::time::Instant::now();
            let plan=native_dyadic_projection_variant(&out,&pre,&post,32768,262144,true);
            let enc=t.elapsed().as_nanos();
            let (status,vars,clauses,sign,d)=if let Some((c,sign,d))=plan{
                let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                ("READY",c.vars,c.clauses.len(),sign,d)
            }else{("ENCODING_LIMIT_OR_UNSUPPORTED",0,0,0,0)};
            rows.push_str(&format!("{key}\t{name}\t{route}\t{x}\t{status}\t{}\t{}\t{vars}\t{clauses}\t{sign}\t{d}\t{scale}\t{common_ns}\t{prefix_ns}\t{prep_ns}\t{enc}\t{pivots}\t{steps}\t{}\n",
                h(&prefix),h(&out),r.limit||limited));
        }
    }
}


// Compose a bounded Boolean output predicate with the complete native
// output map. A single false postcondition is one exact forbidden guard.
fn composed_post(ps:&PathSum,post:&Anf)->Option<Poly>{
    if post.iter().any(|m|m>>ps.v.num_qubits!=0){return None;}
    let mut out=Poly::default();
    for &m in post{
        let mut term=Poly::from_iter([vec![]]);
        for i in 0..ps.v.num_qubits{
            if m>>i&1==0{continue;}
            let f=&ps.f.functions[i];
            if term.len().checked_mul(f.len())?>32768{return None;}
            let mut next=Poly::default();
            for a in &term{for b in f{
                let mut p=a.clone();p.extend(b);toggle(&mut next,p);
            }}
            if next.len()>8192{return None;}
            term=next;
        }
        for p in term{toggle(&mut out,p);}
        if out.len()>8192{return None;}
    }
    Some(out)
}
fn predicate_pivot(ps:&PathSum,post:&Anf)->Option<(PathSum,usize)>{
    let guard=composed_post(ps,post)?;
    let mut candidates=Vec::new();
    for m in guard.iter().filter(|m|m.len()==1&&(m[0] as usize)>=ps.v.num_qubits){
        let y=m[0];
        if guard.iter().any(|p|p!=m&&p.contains(&y)){continue;}
        let mut sel=guard.clone();sel.remove(m); // post(f)=0, so y=sel
        if sel.len()>8{continue;}
        let work=ps.p.terms.keys().filter(|m|m.contains(&y)).count().checked_mul(1usize<<sel.len())?;
        let bw=ps.f.functions.iter().flatten().filter(|m|m.contains(&y)).count().checked_mul(sel.len().max(1))?;
        if work>32768||bw>32768{continue;}
        candidates.push((work+bw,sel.len(),y,sel));
    }
    candidates.sort_by_key(|c|(c.0,c.1,c.2));
    for (_,size,y,sel) in candidates{
        let mut t=ps.clone();
        t.f.substitute_var_with_poly(y,&sel);t.p.substitute_var_with_poly(y,&sel);
        assert!(t.v.path_vars.remove(&y));
        if admitted(&t)&&composed_post(&t,post).is_some_and(|g|g.is_empty()){
            return Some((t,size));
        }
    }
    None
}
fn anf_value(p:&Anf,x:u64)->bool{
    p.iter().fold(false,|a,&m|a^(x&m==m))
}
#[test]
fn native_general_predicate_gate_cohort(){
    use QuantumOp as G;
    // Generated gate families, not a claim of reproduction of external
    // artifacts. Pre/post are independently specified Boolean ANFs.
    let qft_like=vec![G::H(0),G::T(0),G::T(1),G::CX(0,1),G::TDG(1),G::CX(0,1),G::H(1),
        G::H(1),G::CX(0,1),G::T(1),G::CX(0,1),G::TDG(1),G::TDG(0),G::H(0)];
    let families=[
        ("ghz",vec![G::H(0),G::CX(0,1),G::CX(0,2)],G::X(1),
            Anf::from([0,2]),Anf::from([0,1,2])),
        ("ancilla-and",vec![G::H(0),G::H(1),G::CCX(0,1,2)],G::X(2),
            Anf::from([0,4]),Anf::from([0,3,4])),
        ("bv",vec![G::H(0),G::H(1),G::Z(0),G::Z(1),G::H(0),G::H(1)],G::X(1),
            Anf::from([0,1,2]),Anf::from([0,1,2])),
        ("fourier-echo",qft_like,G::X(2),
            Anf::from([0,3,4]),Anf::from([0,3,4])),
        // Positive admission control: H on the computed ancilla exposes
        // an isolated hidden bit in a nonlinear forbidden predicate.
        ("ancilla-mixing",vec![G::H(0),G::H(1),G::CCX(0,1,2)],G::H(2),
            Anf::from([0,4]),Anf::from([0,3,4])),
    ];
    let mut rows=String::new();let mut checks=0;let mut hits=0;let mut positive=0;let mut zero=0;
    let dir=std::env::var_os("HOARE_PAPER_PROJECTED_DIR").map(std::path::PathBuf::from);
    for (family,ops,mutation,pre,post) in families{
        for mutant in [false,true]{
            let case=format!("{family}-{}",if mutant{"mutant"}else{"valid"});
            let t=std::time::Instant::now();
            let mut raw=PathSum::new(3);raw.set_auto_reduce(false);
            for op in &ops{op.apply(&mut raw,false);}
            if mutant{mutation.apply(&mut raw,false);}
            let build_ns=t.elapsed().as_nanos();
            let original=entries(&raw).unwrap();
            let norm=|a:&[Root],x:usize|->i128{
                (0..8).filter(|&z|!anf_value(&post,z as u64))
                    .flat_map(|z|a[8*x+z]).map(|v|i128::from(v)*i128::from(v)).sum()
            };
            let legal:Vec<_>=(0..8u64).filter(|&x|anf_value(&pre,x)).collect();
            assert_eq!(legal.len(),4);
            let t=std::time::Instant::now();let (general,gr)=reduce(raw);
            let common_ns=build_ns+t.elapsed().as_nanos();
            assert!(!gr.limit);
            let mut bad=0;let mut case_hits=0;
            for x in legal{
                let want=norm(&original,x as usize);
                if want>0{bad+=1;positive+=1;}else{zero+=1;}
                let t=std::time::Instant::now();
                let (prefix,pr)=reduce(fixed_input(general.clone(),x));
                let prefix_ns=t.elapsed().as_nanos();
                assert!(!pr.limit);
                let fixed:Vec<Anf>=(0..3).map(|i|if x>>i&1==1{Anf::from([1u64<<i])}
                    else{Anf::from([0,1u64<<i])}).collect();
                for conditioned in [false,true]{
                    let t=std::time::Instant::now();
                    let (out,s,hit,steps)=if conditioned{
                        if let Some((t,_))=predicate_pivot(&prefix,&post){
                            let (out,r)=reduce(t);assert!(!r.limit);
                            (out,r.scale2,1usize,r.elim+r.hh+r.omega)
                        }else{(prefix.clone(),0,0,0)}
                    }else{(prefix.clone(),0,0,0)};
                    let prep_ns=t.elapsed().as_nanos();
                    hits+=hit;case_hits+=hit;
                    let scale=gr.scale2+pr.scale2+s;
                    assert_eq!(norm(&entries(&out).unwrap(),x as usize).checked_shl(scale).unwrap(),want);
                    checks+=1;
                    if let Some(dir)=&dir{
                        let route=if conditioned{"predicate-rr"}else{"input-only"};
                        let key=format!("predicate-{case}-{route}-{x}");
                        let t=std::time::Instant::now();
                        let (c,sign,d)=native_dyadic_projection_variant(&out,&fixed,&[post.clone()],32768,262144,true).unwrap();
                        let enc=t.elapsed().as_nanos();
                        let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                        for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                        std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                        rows.push_str(&format!("{key}\t{case}\t{route}\t{x}\t{}\t{}\t{}\t{}\t{sign}\t{d}\t{scale}\t{common_ns}\t{prefix_ns}\t{prep_ns}\t{enc}\t{hit}\t{steps}\t{want}\n",
                            h(&prefix),h(&out),c.vars,c.clauses.len()));
                    }
                }
            }
            println!("HOARE_NATIVE_GENERAL_PREDICATE_CASE case={case} hits={case_hits} bad_inputs={bad}");
            assert_eq!(bad>0,mutant,"{case}");
            if family=="ancilla-mixing"&&mutant{assert_eq!(case_hits,4,"positive pivot admission control");}
        }
    }
    println!("HOARE_NATIVE_GENERAL_PREDICATE_DIAGNOSTIC checks={checks} hits={hits} positive={positive} zero={zero}");
    assert!(hits>0&&positive>0&&zero>0);
    if let Some(dir)=dir{std::fs::write(dir.join("general-predicate.tsv"),rows).unwrap();}
    println!("HOARE_NATIVE_GENERAL_PREDICATE checks={checks} hits={hits} positive={positive} zero={zero}");
}


// First failed conjuncts are disjoint and cover exactly NOT(all Q_i).
// Encode each branch as a single good predicate R_j whose false set is
// (all earlier Q_i) AND NOT(Q_j). Preserve the complete output map.
fn anf_product(a:&Anf,b:&Anf)->Option<Anf>{
    if a.len().checked_mul(b.len())?>32768{return None;}
    let mut p=Anf::new();
    for &u in a{for &v in b{
        let m=u|v;if !p.insert(m){p.remove(&m);}
    }}
    if p.len()>8192{return None;}Some(p)
}
fn anf_not(p:&Anf)->Anf{
    let mut r=p.clone();if !r.insert(0){r.remove(&0);}r
}
fn first_failed_post(q:&[Anf])->Option<Vec<Anf>>{
    let mut prefix=Anf::from([0]);let mut branches=Vec::new();
    for p in q{
        branches.push(anf_not(&anf_product(&prefix,&anf_not(p))?));
        prefix=anf_product(&prefix,p)?;
    }
    Some(branches)
}
#[test]
fn native_disjoint_predicate_partition(){
    use QuantumOp as G;
    let qs=[Anf::from([0,1,2]),Anf::from([0,3,4]),Anf::from([0,4])];
    // All orderings and degenerate guards (false, true, repeated).
    let lists=vec![qs.to_vec(),vec![qs[1].clone(),qs[0].clone(),qs[2].clone()],
        vec![qs[0].clone(),qs[0].clone()],vec![Anf::new(),qs[1].clone()],
        vec![Anf::from([0]),qs[1].clone()],vec![]];
    let circuits=[
        vec![G::H(0),G::H(1),G::CCX(0,1,2)],
        vec![G::H(0),G::H(1),G::CCX(0,1,2),G::H(2)],
        vec![G::H(0),G::T(0),G::H(0),G::CX(0,1),G::H(2)],
        vec![G::H(0),G::H(0),G::X(1)]
    ];
    let norm=|a:&[Root],x:u64,post:&Anf|->i128{
        (0..8u64).filter(|&z|!anf_value(post,z))
            .flat_map(|z|a[(8*x+z) as usize])
            .map(|v|i128::from(v)*i128::from(v)).sum()
    };
    let mut checks=0;let mut partitions=0;let mut hits=0;
    for ops in circuits{
        let mut raw=PathSum::new(3);raw.set_auto_reduce(false);
        for op in ops{op.apply(&mut raw,false);}
        let original=entries(&raw).unwrap();
        let (general,gr)=reduce(raw);assert!(!gr.limit);
        for q in &lists{
            let branches=first_failed_post(q).unwrap();
            let all=q.iter().try_fold(Anf::from([0]),|a,b|anf_product(&a,b)).unwrap();
            for z in 0..8u64{
                assert_eq!(branches.iter().filter(|b|!anf_value(b,z)).count(),usize::from(!anf_value(&all,z)));
            }
            for x in 0..8u64{
                let (prefix,pr)=reduce(fixed_input(general.clone(),x));assert!(!pr.limit);
                let mut sum=0;
                for branch in &branches{
                    let (out,s)=if let Some((t,_))=predicate_pivot(&prefix,branch){
                        hits+=1;let (out,r)=reduce(t);assert!(!r.limit);(out,r.scale2)
                    }else{(prefix.clone(),0)};
                    let got=norm(&entries(&out).unwrap(),x,branch).checked_shl(gr.scale2+pr.scale2+s).unwrap();
                    assert_eq!(got,norm(&original,x,branch));
                    sum+=got;checks+=1;
                }
                assert_eq!(sum,norm(&original,x,&all));partitions+=1;
            }
        }
    }
    assert!(hits>0);
    println!("HOARE_NATIVE_DISJOINT_PREDICATE checks={checks} partitions={partitions} pivots={hits}");
}


// Independent unnormalized Clifford+T gate recurrence. This reference
// never constructs PathSum, CNF or an RR checkpoint. H contributes its
// integer sign and branches; the common H normalization is omitted.
fn gate_reference(ops:&[QuantumOp],x:u64)->Vec<Root>{gate_reference_width(ops,x,3)}
fn gate_reference_width(ops:&[QuantumOp],x:u64,n:usize)->Vec<Root>{
    use QuantumOp as G;
    let mut a=vec![[0i64;32];1usize<<n];a[x as usize][0]=1;
    for g in ops{
        let mut b=vec![[0i64;32];1usize<<n];
        for (z,r) in a.iter().enumerate(){
            let mut add=|w:usize,phase:usize|{
                for (j,&v) in r.iter().enumerate(){
                    let k=(j+phase)%64;
                    b[w][k%32]+=if k<32{v}else{-v};
                }
            };
            match *g{
                G::H(q)=>{let w=z&!(1usize<<q);add(w,0);add(w|(1<<q),if z>>q&1==1{32}else{0});}
                G::X(q)=>add(z^(1<<q),0),
                G::CX(c,t)=>add(z^(((z>>c)&1)<<t),0),
                G::CCX(c,d,t)=>add(z^((((z>>c)&1)&((z>>d)&1))<<t),0),
                G::T(q)=>add(z,8*((z>>q)&1)),
                G::TDG(q)=>add(z,56*((z>>q)&1)),
                G::Z(q)=>add(z,32*((z>>q)&1)),
                G::S(q)=>add(z,16*((z>>q)&1)),
                G::SDG(q)=>add(z,48*((z>>q)&1)),
                _=>panic!("unsupported independent gate reference"),
            }
        }
        a=b;
    }
    a
}
#[test]
fn native_disjoint_gpmc_ablation(){
    use QuantumOp as G;
    let families=[
        ("ghz",vec![G::H(0),G::CX(0,1),G::CX(0,2)],G::X(1),
            vec![Anf::from([0,2]),Anf::from([0,4])],
            vec![Anf::from([0,1,2]),Anf::from([0,2,4]),Anf::from([0,1,4])]),
        ("and",vec![G::H(0),G::H(1),G::CCX(0,1,2)],G::H(2),
            vec![Anf::from([0,4])],
            vec![Anf::from([0,3,4]),Anf::from([0,4,5]),Anf::from([0,4,6])]),
    ];
    let dir=std::env::var_os("HOARE_PAPER_PROJECTED_DIR").map(std::path::PathBuf::from);
    let mut rows=String::new();let mut checks=0;let mut partitions=0;let mut hits=0;
    for (family,ops,mutation,pre,qs) in families{
        for mutant in [false,true]{
            let case=format!("{family}-{}",if mutant{"mutant"}else{"valid"});
            let mut ops=ops.clone();if mutant{ops.push(mutation.clone());}
            let t=std::time::Instant::now();
            let mut raw=PathSum::new(3);raw.set_auto_reduce(false);
            for op in &ops{op.apply(&mut raw,false);}
            let build=t.elapsed().as_nanos();
            let original=entries(&raw).unwrap();
            let legal:Vec<_>=(0..8u64).filter(|&x|pre.iter().all(|p|anf_value(p,x))).collect();
            let refs:BTreeMap<_,_>=legal.iter().map(|&x|(x,gate_reference(&ops,x))).collect();
            let norm=|a:&[Root],post:&Anf|->i128{
                a.iter().enumerate().filter(|(z,_)|!anf_value(post,*z as u64))
                    .flat_map(|(_,r)|*r).map(|v|i128::from(v)*i128::from(v)).sum()
            };
            let all=qs.iter().try_fold(Anf::from([0]),|a,b|anf_product(&a,b)).unwrap();
            for &x in &legal{
                assert_eq!(&original[(8*x) as usize..(8*x+8) as usize],refs[&x].as_slice());
            }
            let want_global=legal.iter().map(|x|norm(&refs[x],&all)).sum::<i128>();
            assert_eq!(want_global>0,mutant);
            let t=std::time::Instant::now();let (general,gr)=reduce(raw);
            let common=build+t.elapsed().as_nanos();assert!(!gr.limit);
            let mut emit=|route:&str,x:i64,j:usize,out:&PathSum,pred:&[Anf],post:&[Anf],
                scale:u32,prefix_ns:u128,prep:u128,hit:usize,want:i128|{
                let key=format!("disjoint-{case}-{route}-{x}-{j}");
                let t=std::time::Instant::now();
                let (c,sign,d)=native_dyadic_projection_variant(out,pred,post,32768,262144,true).unwrap();
                let enc=t.elapsed().as_nanos();
                if let Some(dir)=&dir{
                    let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                    for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                    std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                }
                rows.push_str(&format!("{key}\t{case}\t{route}\t{x}\t{j}\t{}\t{}\t{}\t{sign}\t{d}\t{scale}\t{common}\t{prefix_ns}\t{prep}\t{enc}\t{hit}\t{want}\n",h(out),c.vars,c.clauses.len()));
            };
            // Strong matched global projected-WMC baseline (same general RR).
            emit("global",-1,0,&general,&pre,&qs,gr.scale2,0,0,0,want_global);
            for &x in &legal{
                let t=std::time::Instant::now();
                let (prefix,pr)=reduce(fixed_input(general.clone(),x));
                let prefix_ns=t.elapsed().as_nanos();assert!(!pr.limit);
                let fixed:Vec<Anf>=(0..3).map(|i|if x>>i&1==1{Anf::from([1u64<<i])}
                    else{Anf::from([0,1u64<<i])}).collect();
                let want=norm(&refs[&x],&all);
                emit("input-only",x as i64,0,&prefix,&fixed,&qs,gr.scale2+pr.scale2,prefix_ns,0,0,want);
                for (route,reverse) in [("forward",false),("reverse",true)]{
                    let t=std::time::Instant::now();
                    let mut order=qs.clone();if reverse{order.reverse();}
                    let branches=first_failed_post(&order).unwrap();
                    let branch_ns=t.elapsed().as_nanos();
                    let mut sum=0;
                    for (j,b) in branches.iter().enumerate(){
                        let t=std::time::Instant::now();
                        let (out,s,hit)=if let Some((p,_))=predicate_pivot(&prefix,b){
                            let (out,r)=reduce(p);assert!(!r.limit);(out,r.scale2,1)
                        }else{(prefix.clone(),0,0)};
                        let prep=t.elapsed().as_nanos()+if j==0{branch_ns}else{0};
                        let scale=gr.scale2+pr.scale2+s;
                        let expected=norm(&refs[&x],b);
                        let got=entries(&out).unwrap();
                        assert_eq!(norm(&got[(8*x) as usize..(8*x+8) as usize],b).checked_shl(scale).unwrap(),expected);
                        sum+=expected;checks+=1;hits+=hit;
                        emit(route,x as i64,j,&out,&fixed,&[b.clone()],scale,if j==0{prefix_ns}else{0},prep,hit,expected);
                    }
                    assert_eq!(sum,want);partitions+=1;
                }
            }
        }
    }
    assert_eq!((checks,partitions),(72,24));
    if let Some(dir)=dir{std::fs::write(dir.join("disjoint-ablation.tsv"),rows).unwrap();}
    println!("HOARE_NATIVE_DISJOINT_ABLATION checks={checks} partitions={partitions} pivots={hits} independent_gate_oracle=true");
}


// A conservative, predeclared router: retain the global route for
// small residuals. A fixed-input probe is charged even if rejected.
fn structural_route(h0:usize,probe_h:usize,legal:usize)->bool{
    h0>12&&h0.saturating_sub(probe_h)>=4&&legal<=16
}
#[test]
fn native_router_boundary(){
    assert!(!structural_route(12,0,4));
    assert!(!structural_route(20,17,4));
    assert!(!structural_route(20,0,17));
    assert!(structural_route(20,16,4));
}
fn feynman_source_ops(src:&str)->(Vec<QuantumOp>,usize){
    use QuantumOp as G;
    let mut lines=src.lines().filter(|s|!s.trim().is_empty());
    assert_eq!(lines.next().unwrap(),"OPENQASM 2.0;");
    assert_eq!(lines.next().unwrap(),"include \"qelib1.inc\";");
    let n:usize=lines.next().unwrap().strip_prefix("qreg qubits[").unwrap().strip_suffix("];").unwrap().parse().unwrap();
    let mut ops=Vec::new();
    for line in lines{
        let (g,args)=line.strip_suffix(';').unwrap().split_once(' ').unwrap();
        let q:Vec<usize>=args.split(',').map(|a|a.trim().strip_prefix("qubits[").unwrap().strip_suffix(']').unwrap().parse().unwrap()).collect();
        assert!(q.iter().all(|&i|i<n));
        let op=match (g,q.as_slice()){
            ("h",[a])=>G::H(*a),("x",[a])=>G::X(*a),("z",[a])=>G::Z(*a),
            ("t",[a])=>G::T(*a),("tdg",[a])=>G::TDG(*a),("s",[a])=>G::S(*a),("sdg",[a])=>G::SDG(*a),
            ("cx",[a,b])=>G::CX(*a,*b),("ccx",[a,b,c])=>G::CCX(*a,*b,*c),
            _=>panic!("unsupported source gate {line}"),
        };ops.push(op);
    }
    (ops,n)
}
#[test]
fn native_feynman_router_pilot(){
    // Existing repository source fixtures, not newly generated circuits.
    // Research-defined P: all bits except q0,q1 zero; Q: top bit zero.
    // These are NOT claims about the original paper's specification.
    let sources=[
        ("qft4",include_str!("../../../benchmarks/Feynman/qft_4.qasm"),[21599390531584i128;4]),
        ("hwb6",include_str!("../../../benchmarks/Feynman/hwb6.qasm"),[0i128;4]),
        ("mod5",include_str!("../../../benchmarks/Feynman/mod5_4.qasm"),[16384i128,0,0,0]),
        ("barenco5",include_str!("../../../benchmarks/Feynman/barenco_tof_5.qasm"),[0i128;4]),
    ];
    let dir=std::env::var_os("HOARE_PAPER_PROJECTED_DIR").map(std::path::PathBuf::from);
    let mut rows=String::new();let mut plans=String::new();
    for (name,src,expected) in sources{
        let (ops,n)=feynman_source_ops(src);
        let (native,width)=parse_qasm_str(src).unwrap();
        assert_eq!((native,width),(ops.clone(),n));
        assert!(ops.iter().filter(|op|matches!(op,QuantumOp::H(_))).count()<=60);
        let mask=1u64<<(n-1);
        for x in 0..4u64{
            let a=gate_reference_width(&ops,x,n);
            let score=a.iter().enumerate().filter(|(z,_)|*z as u64&mask!=0)
                .flat_map(|(_,r)|*r).map(|v|i128::from(v)*i128::from(v)).sum::<i128>();
            assert_eq!(score,expected[x as usize],"{name} {x}");
        }
        let t=std::time::Instant::now();
        let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let build=t.elapsed().as_nanos();assert!(admitted(&raw));
        let t=std::time::Instant::now();let (general,gr)=reduce(raw);
        let common=build+t.elapsed().as_nanos();
        let pre:Vec<Anf>=(2..n).map(|i|Anf::from([0,1u64<<i])).collect();
        let post=vec![Anf::from([0,mask])];
        let mut emit=|route:&str,x:i64,out:&PathSum,pred:&[Anf],scale:u32,prefix_ns:u128,want:i128|{
            let key=format!("router-{name}-{route}-{x}");
            let t=std::time::Instant::now();
            let plan=native_dyadic_projection_variant(out,pred,&post,32768,262144,true);
            let enc=t.elapsed().as_nanos();
            let (status,v,c,sign,d)=if let Some((c,sign,d))=plan{
                if let Some(dir)=&dir{
                    let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                    for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                    std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                }
                ("READY",c.vars,c.clauses.len(),sign,d)
            }else{("UNSUPPORTED",0,0,0,0)};
            rows.push_str(&format!("{key}\t{name}\t{route}\t{x}\t{status}\t{n}\t{}\t{v}\t{c}\t{sign}\t{d}\t{scale}\t{common}\t{prefix_ns}\t{enc}\t{want}\n",h(out)));
        };
        emit("global",-1,&general,&pre,gr.scale2,0,expected.iter().sum());
        let mut first_h=0;let mut first_ns=0;
        for x in 0..4u64{
            let t=std::time::Instant::now();let (prefix,pr)=reduce(fixed_input(general.clone(),x));
            let ns=t.elapsed().as_nanos();
            if x==0{first_h=h(&prefix);first_ns=ns;}
            let fixed:Vec<Anf>=(0..n).map(|i|if x>>i&1==1{Anf::from([1u64<<i])}else{Anf::from([0,1u64<<i])}).collect();
            emit("input",x as i64,&prefix,&fixed,gr.scale2+pr.scale2,ns,expected[x as usize]);
        }
        let chosen=if structural_route(h(&general),first_h,4){"input"}else{"global"};
        let probe_ns=if h(&general)>12&&chosen=="global"{first_ns}else{0};
        plans.push_str(&format!("{name}\t{}\t{first_h}\t{chosen}\t{probe_ns}\n",h(&general)));
        println!("HOARE_FEYNMAN_ROUTER_PLAN name={name} n={n} gates={} general_h={} first_h={first_h} selected={chosen} probe_ns={probe_ns} limit={}",ops.len(),h(&general),gr.limit);
    }
    if let Some(dir)=dir{
        std::fs::write(dir.join("feynman-router.tsv"),rows).unwrap();
        std::fs::write(dir.join("feynman-router-plan.tsv"),plans).unwrap();
    }
}


// Exact bounded factor elimination over Z[zeta_8], a separate
// algebraic contraction route, NOT a WMC solver or dense statevector.
type Z8=[i128;4];
fn cyclo_one<const N:usize>()->[i128;N]{let mut r=[0;N];r[0]=1;r}
fn cyclo_add<const N:usize>(a:[i128;N],b:[i128;N])->Option<[i128;N]>{
    let mut c=[0i128;N];for i in 0..N{c[i]=a[i].checked_add(b[i])?;}Some(c)
}
fn cyclo_mul<const N:usize>(a:[i128;N],b:[i128;N])->Option<[i128;N]>{
    let mut c=[0i128;N];
    for i in 0..N{
        if a[i]==0{continue;}
        for j in 0..N{
        if b[j]==0{continue;}
        let p=a[i].checked_mul(b[j])?;
        let k=i+j;
        c[k%N]=if k<N{c[k%N].checked_add(p)?}else{c[k%N].checked_sub(p)?};
    }}Some(c)
}
#[test]
fn native_cyclo_checked_boundaries(){
    // Direct subtraction can succeed even when negating the product cannot.
    assert_eq!(cyclo_mul::<4>([-1,0,0,i128::MIN],[1,1,0,0]),
        Some([i128::MAX,-1,0,i128::MIN]));
    assert_eq!(cyclo_mul::<2>([0,i128::MIN],[0,1]),None);
    assert_eq!(cyclo_mul::<1>([i128::MIN],[-1]),None);
    assert_eq!(cyclo_mul::<2>([i128::MAX,1],[1,1]),None);
    assert_eq!(cyclo_mul::<1>([i128::MIN],[1]),Some([i128::MIN]));
    assert_eq!(cyclo_mul::<4>([i128::MIN,0,0,i128::MAX],[0;4]),Some([0;4]));
    let decode = |mut n:usize| -> [i128;4] {
        std::array::from_fn(|_|{let x=(n%3) as i128-1;n/=3;x})
    };
    let mut checks=0;
    for x in 0..81 {
        for y in 0..81 {
            let a=decode(x);let b=decode(y);
            let expected:[i128;4]=std::array::from_fn(|k|{
                let mut s=0;
                for i in 0..4 {for j in 0..4 {
                    if i+j==k{s+=a[i]*b[j];}
                    if i+j==k+4{s-=a[i]*b[j];}
                }}
                s
            });
            assert_eq!(cyclo_mul(a,b),Some(expected));
            checks+=1;
        }
    }
    assert_eq!(checks,6561);
    println!("HOARE_NATIVE_CYCLO_CHECKED cases=6561 boundary_cases=6 min_subtract=true overflow_reject=true");
}
#[derive(Clone)]
struct Factor<const N:usize>{scope:u64,table:Vec<[i128;N]>}
fn deposit8(mut i:usize,mut mask:u64)->u64{
    let mut a=0;while mask!=0{let b=mask&mask.wrapping_neg();mask^=b;if i&1!=0{a|=b;}i>>=1;}a
}
fn extract8(a:u64,mut mask:u64)->usize{
    let mut i=0;let mut bit=1;while mask!=0{let b=mask&mask.wrapping_neg();mask^=b;if a&b!=0{i|=bit;}bit<<=1;}i
}
fn factor<const N:usize>(scope:u64,mut f:impl FnMut(u64)->[i128;N])->Result<Factor<N>,&'static str>{
    if scope.count_ones()>12{return Err("WIDTH_LIMIT");}
    Ok(Factor{scope,table:(0..1usize<<scope.count_ones()).map(|i|f(deposit8(i,scope))).collect()})
}

// Plan scopes before allocating any dense factor tables. The output
// coordinates are boundary indices, never summed with hidden variables.
fn plan_factor8(mut scopes:Vec<u64>,hidden:usize,boundary:u64,mut work:usize)
    ->Result<(Vec<usize>,usize,usize),&'static str>{
    if hidden>60||boundary.count_ones()>12{return Err("WIDTH_LIMIT");}
    let mut peak=boundary.count_ones() as usize;
    for &scope in &scopes{
        let w=scope.count_ones() as usize;
        if w>12{return Err("WIDTH_LIMIT");}peak=peak.max(w);
    }
    if work>2_000_000{return Err("WORK_LIMIT");}
    let mut order=Vec::new();let mut live=(1u64<<hidden)-1;
    while live!=0{
        let (width,i,u)=(0..hidden).filter(|&i|live&(1u64<<i)!=0).map(|i|{
            let b=1u64<<i;let u=scopes.iter().filter(|&&f|f&b!=0).fold(b,|a,&f|a|f);
            (u.count_ones(),i,u)
        }).min().unwrap();
        if width>12{return Err("WIDTH_LIMIT");}peak=peak.max(width as usize);
        let b=1u64<<i;
        let count=scopes.iter().filter(|&&f|f&b!=0).count().max(1);
        work=work.checked_add((1usize<<width).checked_mul(count).ok_or("WORK_LIMIT")?).ok_or("WORK_LIMIT")?;
        if work>2_000_000{return Err("WORK_LIMIT");}
        scopes.retain(|f|*f&b==0);scopes.push(u&!b);order.push(i);live^=b;
    }
    assert!(scopes.iter().all(|f|f&!boundary==0));
    work=work.checked_add((1usize<<boundary.count_ones()).checked_mul(scopes.len().max(1)).ok_or("WORK_LIMIT")?).ok_or("WORK_LIMIT")?;
    if work>2_000_000{return Err("WORK_LIMIT");}
    Ok((order,peak,work))
}
enum FactorSpec8{Phase(u64,usize),Output(u64,Vec<u64>,Option<u64>,usize)}
struct BoundaryPlan8{degree:usize,specs:Vec<FactorSpec8>,order:Vec<usize>,free:u64,fixed:u64,peak:usize,work:usize}
fn prepare_cyclo_boundary(ps:&PathSum,fixed_mask:u64,degree:usize,deadline:std::time::Instant)
    ->Result<BoundaryPlan8,&'static str>{
    if ps.v.num_qubits>16{return Err("UNSUPPORTED");}
    prepare_cyclo_selected(ps,(1u64<<ps.v.num_qubits)-1,fixed_mask,degree,deadline)
}
fn prepare_cyclo_selected(ps:&PathSum,keep:u64,fixed_mask:u64,degree:usize,deadline:std::time::Instant)
    ->Result<BoundaryPlan8,&'static str>{
    if !matches!(degree,1|2|4|8|16|32){return Err("UNSUPPORTED_PHASE");}
    let n=ps.v.num_qubits;let hidden=h(ps);
    if hidden>60||n>16||hidden+n>63||!admitted(ps)||keep>>n!=0||fixed_mask&!keep!=0{return Err("UNSUPPORTED");}
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let free=(keep&!fixed_mask)<<hidden;
    let mut ids:Vec<_>=ps.v.path_vars.iter().copied().filter(|&i|i as usize>=n).collect();
    ids.sort_unstable();
    let positions:BTreeMap<_,_>=ids.iter().enumerate().map(|(j,&id)|(id,1u64<<j)).collect();
    let mask=|m:&[u32]|->Result<u64,&'static str>{
        m.iter().try_fold(0u64,|a,v|positions.get(v).map(|b|a|b).ok_or("UNFIXED_INPUT"))
    };
    let mut specs=Vec::new();let mut scopes=Vec::new();let mut initial_work=0usize;
    let mut charge=|scope:u64,per:usize|->Result<(),&'static str>{
        let w=scope.count_ones();
        if w>12{return Err("WIDTH_LIMIT");}
        initial_work=initial_work.checked_add((1usize<<w).checked_mul(per.max(1)).ok_or("WORK_LIMIT")?).ok_or("WORK_LIMIT")?;
        if initial_work>2_000_000{return Err("WORK_LIMIT");}
        scopes.push(scope);Ok(())
    };
    for (m,c) in &ps.p.terms{
        let den=c.constant.denom as i128;let num=(2*degree) as i128*c.constant.numer as i128;
        if den<=0||num%den!=0{return Err("UNSUPPORTED_PHASE");}
        let k=(num/den).rem_euclid((2*degree) as i128) as usize;if k==0{continue;}
        let scope=mask(m)?;charge(scope,1)?;specs.push(FactorSpec8::Phase(scope,k));
    }
    for (i,p) in ps.f.functions.iter().enumerate(){
        if keep>>i&1==0{continue;}
        let ms=p.iter().map(|m|mask(m)).collect::<Result<Vec<_>,_>>()?;
        let bit=if fixed_mask>>i&1==0{Some(1u64<<(hidden+i))}else{None};
        let scope=ms.iter().fold(bit.unwrap_or(0),|a,b|a|b);
        charge(scope,ms.len())?;specs.push(FactorSpec8::Output(scope,ms,bit,i));
    }
    let (order,peak,work)=plan_factor8(scopes,hidden,free,initial_work)?;
    // Charge worst-case dense coefficient multiplication relative to D8.
    let work=work.checked_mul((degree/4).max(1).pow(2)).ok_or("WORK_LIMIT")?;
    if work>2_000_000{return Err("WORK_LIMIT");}
    Ok(BoundaryPlan8{degree,specs,order,free,fixed:fixed_mask,peak,work})
}
fn execute_cyclo_boundary<const N:usize>(plan:&BoundaryPlan8,z:u64,deadline:std::time::Instant)
    ->Result<(Vec<[i128;N]>,usize,usize),&'static str>{
    if plan.degree!=N{return Err("UNSUPPORTED_PHASE");}
    if z&!plan.fixed!=0{return Err("UNSUPPORTED");}
    let BoundaryPlan8{specs,order,free,peak,work,..}=plan;
    let free=*free;
    // The work cap also upper-bounds the total number of allocated
    // table entries across this call (including discarded tables).
    let mut fs=Vec::<Factor<N>>::new();
    for spec in specs{
        if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let f=match spec{
            FactorSpec8::Phase(scope,k)=>factor::<N>(*scope,|a|{
                if a&*scope!=*scope{return cyclo_one::<N>();}
                let mut r=[0;N];r[*k%N]=if *k<N{1}else{-1};r
            })?,
            FactorSpec8::Output(scope,ms,bit,i)=>factor::<N>(*scope,|a|{
                let v=ms.iter().fold(false,|b,&m|b^(a&m==m));
                let want=bit.map_or(z>>*i&1==1,|b|a&b!=0);
                if v==want{cyclo_one::<N>()}else{[0;N]}
            })?,
        };fs.push(f);
    }
    for &i in order{
        if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let b=1u64<<i;
        let (bucket,rest):(Vec<_>,Vec<_>)=fs.into_iter().partition(|f|f.scope&b!=0);
        let scope=bucket.iter().fold(0u64,|a,f|a|f.scope)&!b;
        let count=1usize<<scope.count_ones();let mut table=Vec::with_capacity(count);
        for i in 0..count{
            if i%64==0&&std::time::Instant::now()>=deadline{return Err("DEADLINE");}
            let a=deposit8(i,scope);let mut sum=[0;N];
            for assignment in [a,a|b]{
                let mut v=cyclo_one::<N>();
                for f in &bucket{
                    v=cyclo_mul(v,f.table[extract8(assignment,f.scope)]).ok_or("OVERFLOW")?;
                    if v==[0;N]{break;}
                }
                sum=cyclo_add(sum,v).ok_or("OVERFLOW")?;
            }
            table.push(sum);
        }
        fs=rest;fs.push(Factor{scope,table});
    }
    let mut result=Vec::with_capacity(1usize<<free.count_ones());
    for i in 0..1usize<<free.count_ones(){
        if i%64==0&&std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let a=deposit8(i,free);let mut v=cyclo_one::<N>();
        for f in &fs{
            assert_eq!(f.scope&!free,0);
            v=cyclo_mul(v,f.table[extract8(a,f.scope)]).ok_or("OVERFLOW")?;
            if v==[0;N]{break;}
        }
        result.push(v);
    }
    Ok((result,*peak,*work))
}

// Determine the smallest supported power-of-two order from exact phase
// coefficients, including constant phase; no tolerance or value sampling.
fn minimum_cyclo_degree(ps:&PathSum)->Result<usize,&'static str>{
    if !admitted(ps){return Err("UNSUPPORTED");}
    let mut degree=1usize;
    for c in ps.p.terms.values(){
        let den=c.constant.denom as i128;
        if den<=0{return Err("UNSUPPORTED_PHASE");}
        let d=[1usize,2,4,8,16,32].into_iter().find(|&d|
            ((2*d) as i128*c.constant.numer as i128)%den==0).ok_or("UNSUPPORTED_PHASE")?;
        degree=degree.max(d);
    }
    Ok(degree)
}
type Z64=[i128;32];
fn execute_lifted<const N:usize>(plan:&BoundaryPlan8,z:u64,deadline:std::time::Instant)
    ->Result<(Vec<Z64>,usize,usize),&'static str>{
    let (a,w,c)=execute_cyclo_boundary::<N>(plan,z,deadline)?;
    let mut lifted=Vec::with_capacity(a.len());
    for v in a{
        let mut r=[0;32];
        for i in 0..N{r[i*(32/N)]=v[i];}
        lifted.push(r);
    }
    Ok((lifted,w,c))
}
fn execute_minimum_boundary(plan:&BoundaryPlan8,z:u64,deadline:std::time::Instant)
    ->Result<(Vec<Z64>,usize,usize),&'static str>{
    match plan.degree{
        1=>execute_lifted::<1>(plan,z,deadline),
        2=>execute_lifted::<2>(plan,z,deadline),
        4=>execute_lifted::<4>(plan,z,deadline),
        8=>execute_lifted::<8>(plan,z,deadline),
        16=>execute_lifted::<16>(plan,z,deadline),
        32=>execute_cyclo_boundary::<32>(plan,z,deadline),
        _=>Err("UNSUPPORTED_PHASE"),
    }
}

const Z8_ONE:Z8=[1,0,0,0];
fn prepare_boundary8(ps:&PathSum,fixed_mask:u64,deadline:std::time::Instant)->Result<BoundaryPlan8,&'static str>{
    prepare_cyclo_boundary(ps,fixed_mask,4,deadline)
}
fn execute_boundary8(plan:&BoundaryPlan8,z:u64,deadline:std::time::Instant)->Result<(Vec<Z8>,usize,usize),&'static str>{
    execute_cyclo_boundary::<4>(plan,z,deadline)
}
fn contract_boundary8(ps:&PathSum,fixed_mask:u64,z:u64,deadline:std::time::Instant)
    ->Result<(Vec<Z8>,usize,usize),&'static str>{
    let plan=prepare_boundary8(ps,fixed_mask,deadline)?;
    execute_boundary8(&plan,z,deadline)
}
fn contract_fibre8(ps:&PathSum,z:u64,deadline:std::time::Instant)->Result<(Z8,usize,usize),&'static str>{
    if ps.v.num_qubits>16{return Err("UNSUPPORTED");}
    let (a,w,c)=contract_boundary8(ps,(1u64<<ps.v.num_qubits)-1,z,deadline)?;
    assert_eq!(a.len(),1);Ok((a[0],w,c))
}
fn z8_norm(a:Z8)->i128{a.into_iter().map(|v|v*v).sum()}
#[test]
fn native_factor8_exact_reference(){
    use QuantumOp as G;
    let circuits=[
        vec![G::H(0),G::T(0),G::H(0),G::CX(0,1),G::H(2)],
        vec![G::H(0),G::H(1),G::CCX(0,1,2),G::H(2),G::TDG(2)],
        vec![G::H(0),G::Z(0),G::H(0)],
    ];
    let mut checks=0;let mut peak=0;
    for ops in circuits{
        let mut ps=PathSum::new(3);ps.set_auto_reduce(false);
        for g in &ops{g.apply(&mut ps,false);}
        for x in 0..8u64{
            let expected=gate_reference_width(&ops,x,3);
            let fixed=fixed_input(ps.clone(),x);
            for mask in 0..8u64{for z in 0..8u64{
                if z&!mask!=0{continue;}
                let (a,_,_)=contract_boundary8(&fixed,mask,z,std::time::Instant::now()+std::time::Duration::from_secs(5)).unwrap();
                for (i,r) in a.iter().enumerate(){
                    let output=z|deposit8(i,7&!mask);
                    let mut lifted=[0i64;32];for j in 0..4{lifted[8*j]=i64::try_from(r[j]).unwrap();}
                    assert_eq!(lifted,expected[output as usize]);
                }
            }}
            for z in 0..8u64{
                let (a,w,_)=contract_fibre8(&fixed,z,std::time::Instant::now()+std::time::Duration::from_secs(5)).unwrap();
                let mut lifted=[0i64;32];for i in 0..4{lifted[8*i]=i64::try_from(a[i]).unwrap();}
                assert_eq!(lifted,expected[z as usize]);checks+=1;peak=peak.max(w);
            }
        }
    }
    assert_eq!(checks,192);
    println!("HOARE_NATIVE_FACTOR8_REFERENCE checks={checks} peak_width={peak}");
}
#[test]
fn native_qft_factor8_pilot(){
    let src=include_str!("../../../benchmarks/Feynman/qft_4.qasm");
    let (ops,n)=feynman_source_ops(src);assert_eq!(n,5);
    let t=std::time::Instant::now();
    let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
    for g in &ops{g.apply(&mut raw,false);}
    let (general,gr)=reduce(raw);let common=t.elapsed();
    assert_eq!(h(&general),30);
    for conditioned in [false,true]{
        let start=std::time::Instant::now();
        let deadline=start+std::time::Duration::from_secs(30).saturating_sub(common);
        let mut exact=0;let mut positive=0;let mut peak=0;let mut work=0;let mut min_h=usize::MAX;
        let mut statuses=BTreeMap::<&str,usize>::new();
        for x in 0..4u64{
            if std::time::Instant::now()>=deadline{break;}
            let oracle=gate_reference_width(&ops,x,n);
            let (prefix,pr)=reduce(fixed_input(general.clone(),x));
            for z in 16..32u64{
                if std::time::Instant::now()>=deadline{break;}
                let (out,s)=if conditioned{
                    let (out,s,_,_,_)=condition_and_reduce(prefix.clone(),x,z,false);(out,s)
                }else{(prefix.clone(),0)};
                min_h=min_h.min(h(&out));
                match contract_fibre8(&out,z,deadline){
                    Ok((a,w,cost))=>{
                        let want=oracle[z as usize].iter().map(|&v|i128::from(v)*i128::from(v)).sum::<i128>();
                        let scale=gr.scale2+pr.scale2+s;
                        assert_eq!(z8_norm(a).checked_shl(scale).unwrap(),want,"{x} {z}");
                        exact+=1;positive+=usize::from(a!=[0;4]);peak=peak.max(w);work+=cost;
                        println!("HOARE_QFT_FACTOR8_FIBRE conditioned={conditioned} x={x} z={z} h={} width={w} work={cost} scale2={scale} nonzero={}",h(&out),a!=[0;4]);
                    }
                    Err(reason)=>{*statuses.entry(reason).or_default()+=1;}
                }
            }
        }
        let verdict=if positive>0{"REFUTED"}else if exact==64{"PROVED"}else{"UNKNOWN"};
        println!("HOARE_QFT_FACTOR8_SUMMARY conditioned={conditioned} exact={exact} positive={positive} verdict={verdict} min_h={min_h} max_width={peak} work={work} accounted_ns={} failures={statuses:?}",(common+start.elapsed()).as_nanos());
    }
    if let Some(dir)=std::env::var_os("HOARE_PAPER_PROJECTED_DIR"){
        std::fs::write(std::path::PathBuf::from(dir).join("qft-factor8-pilot.done"),"native bounded factor pilot executed\n").unwrap();
    }
}


#[test]
fn native_boundary_plan_caps(){
    assert_eq!(plan_factor8(vec![(1u64<<13)-1],13,0,8192).unwrap_err(),"WIDTH_LIMIT");
    assert_eq!(plan_factor8(vec![1],1,0,2_000_001).unwrap_err(),"WORK_LIMIT");
    assert_eq!(plan_factor8((1..13).map(|i|1|(1u64<<i)).collect(),1,((1u64<<13)-1)&!1,48).unwrap_err(),"WIDTH_LIMIT");
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    let _=ps.v.get_fresh_var();
    let fixed=fixed_input(ps,0);
    let (a,_,_)=contract_boundary8(&fixed,0,0,std::time::Instant::now()+std::time::Duration::from_secs(1)).unwrap();
    assert_eq!(a,vec![[2,0,0,0],[0;4]]);
    assert_eq!(contract_boundary8(&fixed,0,0,std::time::Instant::now()).unwrap_err(),"DEADLINE");
    println!("HOARE_NATIVE_BOUNDARY_CAPS width_work_free_deadline=true");
}

// Only nested masks are searched; actual execution uses the same immutable
// structural plan for all assignments to the additional fixed output bits.
const TILE_WORK_CAP:usize=2_000_000;
struct TileReceipt8{
    values:Vec<Option<Z8>>,fixed:u64,candidates:usize,rejected:usize,
    calls:usize,fallback_calls:usize,peak:usize,work:usize,
    failures:BTreeMap<&'static str,usize>,
}
fn tiled_boundary8(ps:&PathSum,sector:u64,value:u64,deadline:std::time::Instant)
    ->Result<TileReceipt8,&'static str>{
    tiled_boundary8_with(ps,sector,value,deadline,false,|plan,z,deadline|execute_boundary8(plan,z,deadline))
}
fn tiled_boundary8_with(ps:&PathSum,sector:u64,value:u64,deadline:std::time::Instant,fast:bool,
    mut execute:impl FnMut(&BoundaryPlan8,u64,std::time::Instant)->Result<(Vec<Z8>,usize,usize),&'static str>)
    ->Result<TileReceipt8,&'static str>{
    let n=ps.v.num_qubits;
    if n>16||sector>>n!=0||value&!sector!=0{return Err("UNSUPPORTED");}
    let all=(1u64<<n)-1;let free=all&!sector;
    if free.count_ones()>12{return Err("COVERAGE_LIMIT");}
    let mut best:Option<(usize,usize,u64,BoundaryPlan8)>=None;
    let mut fixed=sector;let mut candidates=0;let mut rejected=0;
    let mut last="NO_ADMITTED_PLAN";
    loop{
        if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        candidates+=1;
        match prepare_boundary8(ps,fixed,deadline){
            Ok(plan)=>{
                let calls=1usize<<(fixed&free).count_ones();
                let work=plan.work.checked_mul(calls).ok_or("WORK_LIMIT")?;
                if work<=TILE_WORK_CAP{
                    let key=(work,calls,fixed);
                    if best.as_ref().is_none_or(|b|key<(b.0,b.1,b.2)){
                        let cheap=fast&&fixed==sector&&(h(ps)==0||(plan.peak<=4&&work<=4096));
                        best=Some((work,calls,fixed,plan));
                        if cheap{break;}
                    }
                }else{rejected+=1;last="WORK_LIMIT";}
            }
            Err("DEADLINE")=>return Err("DEADLINE"),
            Err(reason)=>{rejected+=1;last=reason;}
        }
        if fixed==all{break;}
        let rest=all&!fixed;fixed|=rest&rest.wrapping_neg();
    }
    let (_,tiles,fixed,plan)=best.ok_or(last)?;
    let mut receipt=TileReceipt8{values:vec![None;1usize<<free.count_ones()],
        fixed,candidates,rejected,calls:0,fallback_calls:0,peak:0,work:0,failures:BTreeMap::new()};
    let added=fixed&free;let remaining=all&!fixed;
    for tile in 0..tiles{
        if std::time::Instant::now()>=deadline{*receipt.failures.entry("DEADLINE").or_default()+=1;break;}
        if receipt.work.saturating_add(plan.work)>TILE_WORK_CAP{*receipt.failures.entry("WORK_LIMIT").or_default()+=1;break;}
        let z=value|deposit8(tile,added);receipt.calls+=1;receipt.work+=plan.work;
        match execute(&plan,z,deadline){
            Ok((a,w,_))=>{
                receipt.peak=receipt.peak.max(w);
                for (i,r) in a.into_iter().enumerate(){
                    let output=z|deposit8(i,remaining);
                    let idx=extract8(output,free);
                    assert!(receipt.values[idx].replace(r).is_none(),"overlapping tile");
                }
            }
            Err(reason)=>{
                *receipt.failures.entry(reason).or_default()+=1;
                if reason=="DEADLINE"{break;}
            }
        }
    }
    // Only unresolved outputs may be retried. No partial tile is credited,
    // and the same deadline and aggregate estimated-work cap are retained.
    if fixed!=all&&receipt.values.iter().any(Option::is_none)&&std::time::Instant::now()<deadline{
        if let Ok(single)=prepare_boundary8(ps,all,deadline){
            for (i,r) in receipt.values.iter_mut().enumerate(){
                if r.is_some(){continue;}
                if std::time::Instant::now()>=deadline{*receipt.failures.entry("DEADLINE").or_default()+=1;break;}
                if receipt.work.saturating_add(single.work)>TILE_WORK_CAP{*receipt.failures.entry("WORK_LIMIT").or_default()+=1;break;}
                receipt.fallback_calls+=1;receipt.work+=single.work;
                match execute(&single,value|deposit8(i,free),deadline){
                    Ok((a,w,_))=>{assert_eq!(a.len(),1);*r=Some(a[0]);receipt.peak=receipt.peak.max(w);}
                    Err(reason)=>{*receipt.failures.entry(reason).or_default()+=1;if reason=="DEADLINE"{break;}}
                }
            }
        }
    }
    Ok(receipt)
}

#[test]
fn native_tiling8_failure_injection(){
    let mut ps=PathSum::new(3);ps.set_auto_reduce(false);
    for q in 0..3{QuantumOp::H(q).apply(&mut ps,false);}
    let fixed=fixed_input(ps,0);
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(5);
    let mut attempted=Vec::new();
    let r=tiled_boundary8_with(&fixed,4,4,deadline,false,|plan,z,d|{
        attempted.push((plan.fixed,z));
        if plan.fixed!=7{Err("INJECTED_TILE_FAILURE")}else{execute_boundary8(plan,z,d)}
    }).unwrap();
    assert_eq!(r.calls,1);assert_eq!(r.fallback_calls,4);
    assert_eq!(attempted,vec![(4,4),(7,4),(7,5),(7,6),(7,7)]);
    assert_eq!(r.values,vec![Some(Z8_ONE);4]);
    assert_eq!(r.failures.get("INJECTED_TILE_FAILURE"),Some(&1));
    let r=tiled_boundary8_with(&fixed,4,4,deadline,false,|plan,z,d|{
        if plan.fixed!=7||z==6{Err("INJECTED_FAILURE")}else{execute_boundary8(plan,z,d)}
    }).unwrap();
    assert_eq!(r.values,vec![Some(Z8_ONE),Some(Z8_ONE),None,Some(Z8_ONE)]);
    assert_eq!(r.fallback_calls,4);
    // A partial all-zero result is not a proof. A retained nonzero still refutes.
    let mut zero=PathSum::new(3);zero.set_auto_reduce(false);let zero=fixed_input(zero,0);
    let r=tiled_boundary8_with(&zero,4,4,deadline,false,|plan,z,d|{
        if plan.fixed!=7||z==6{Err("INJECTED_FAILURE")}else{execute_boundary8(plan,z,d)}
    }).unwrap();
    assert_eq!(r.values,vec![Some([0;4]),Some([0;4]),None,Some([0;4])]);
    println!("HOARE_NATIVE_TILING8_FAILURE recovered=4 partial_positive=3 partial_zero=3 unresolved=1");
}
#[test]
fn native_cyclo64_reference(){
    use quprs::{Rational,PhaseCoeff};
    let mut checks=0;
    for d in [2,4,8,16,32,64]{
        let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
        let a=ps.v.get_fresh_var();let b=ps.v.get_fresh_var();
        ps.f.functions[0]=Poly::from_iter([vec![a],vec![b]]);
        ps.f.functions[1]=Poly::from_iter([vec![a,b]]);
        ps.p.add_term(vec![a],PhaseCoeff::new_constant(Rational::new(1,d)));
        ps.p.add_term(vec![b],PhaseCoeff::new_constant(Rational::new(-1,d)));
        ps.p.add_term(vec![a,b],PhaseCoeff::new_constant(Rational::new(3,d)));
        let expected=entries(&ps).unwrap();
        let fixed=fixed_input(ps,0);
        let degree=minimum_cyclo_degree(&fixed).unwrap();assert_eq!(degree,d as usize/2);
        let deadline=std::time::Instant::now()+std::time::Duration::from_secs(5);
        for mask in 0..4u64{for z in 0..4u64{
            if z&!mask!=0{continue;}
            let plan=prepare_cyclo_boundary(&fixed,mask,32,deadline).unwrap();
            let (got,_,_)=execute_cyclo_boundary::<32>(&plan,z,deadline).unwrap();
            let min=prepare_cyclo_boundary(&fixed,mask,degree,deadline).unwrap();
            let (small,_,_)=execute_minimum_boundary(&min,z,deadline).unwrap();
            assert_eq!(small,got);
            for (i,r) in got.iter().enumerate(){
                let out=z|deposit8(i,3&!mask);
                assert_eq!(*r,expected[out as usize].map(i128::from));checks+=1;
            }
            assert!(matches!(execute_boundary8(&plan,z,deadline),Err("UNSUPPORTED_PHASE")));
        }}
        if d>8{assert!(matches!(prepare_boundary8(&fixed,0,deadline),Err("UNSUPPORTED_PHASE")));}
    }
    assert_eq!(checks,96);
    println!("HOARE_NATIVE_CYCLO64_REFERENCE vectors={checks} orders=6 basis_mismatch_rejected=true");
    let mut ps=PathSum::new(1);ps.set_auto_reduce(false);
    ps.p.add_term(vec![],PhaseCoeff::new_constant(Rational::new(1,3)));
    assert_eq!(minimum_cyclo_degree(&ps),Err("UNSUPPORTED_PHASE"));
    println!("HOARE_NATIVE_MINIMUM_BASIS vectors={checks} orders=6 unsupported_rejected=true");
}

#[test]
fn native_tiling8_width_control(){
    // A generated structural control, not a unitary circuit: all 13
    // output bits equal one hidden bit. Full boundary needs width 13.
    let n=13;let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
    let y=ps.v.get_fresh_var();
    for f in &mut ps.f.functions{*f=Poly::from_iter([vec![y]]);}
    let mask=1u64<<(n-1);let all=(1u64<<n)-1;
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(30);
    assert!(matches!(prepare_boundary8(&ps,mask,deadline),Err("WIDTH_LIMIT")));
    let r=tiled_boundary8(&ps,mask,mask,deadline).unwrap();
    assert!(r.fixed!=mask&&r.fixed!=all);
    assert!(r.rejected>0&&r.peak<=12&&r.work<=TILE_WORK_CAP);
    assert_eq!(r.values.len(),4096);
    for (i,v) in r.values.iter().enumerate(){assert_eq!(*v,Some(if i==4095{Z8_ONE}else{[0;4]}));}
    assert!(matches!(tiled_boundary8(&ps,mask,mask,std::time::Instant::now()),Err("DEADLINE")));
    println!("HOARE_NATIVE_TILING8_CONTROL exact=4096 full_rejected=true fixed={} calls={} peak={} work={} fallback_calls={}",r.fixed,r.calls,r.peak,r.work,r.fallback_calls);
    // Inject failure on only the first selected tile. The second tile
    // must remain credited; fallback must never recompute its outputs.
    let mut retried=Vec::new();
    let r=tiled_boundary8_with(&ps,mask,mask,deadline,false,|plan,z,d|{
        if plan.fixed!=all&&z==mask{return Err("INJECTED_FIRST_TILE");}
        if plan.fixed==all{retried.push(z);}
        execute_boundary8(plan,z,d)
    }).unwrap();
    assert_eq!(r.calls,2);assert_eq!(r.fallback_calls,2048);
    assert_eq!(retried.len(),2048);assert!(retried.iter().all(|z|z&1==0));
    assert!(r.work<=TILE_WORK_CAP);
    for (i,v) in r.values.iter().enumerate(){assert_eq!(*v,Some(if i==4095{Z8_ONE}else{[0;4]}));}
    println!("HOARE_NATIVE_TILING8_PARTIAL_RECOVERY retained=2048 recovered=2048 duplicate=0");

}

#[test]
fn native_feynman_boundary8_pilot(){
    let sources=[
        ("qft4",include_str!("../../../benchmarks/Feynman/qft_4.qasm")),
        ("hwb6",include_str!("../../../benchmarks/Feynman/hwb6.qasm")),
        ("mod5",include_str!("../../../benchmarks/Feynman/mod5_4.qasm")),
        ("barenco5",include_str!("../../../benchmarks/Feynman/barenco_tof_5.qasm")),
    ];
    for (name,src) in sources{
        let (ops,n)=feynman_source_ops(src);
        let mask=1u64<<(n-1);
        // Independent oracle is prepared outside both measured arms.
        let oracle:Vec<_>=(0..4u64).map(|x|gate_reference_width(&ops,x,n)).collect();
        let t=std::time::Instant::now();
        let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for g in &ops{g.apply(&mut raw,false);}
        let (general,gr)=reduce(raw);let common=t.elapsed();
        let mut receipts=BTreeMap::<(u64,u64),Z8>::new();let mut paired=0;
        for boundary in [false,true]{
            let start=std::time::Instant::now();
            let deadline=start+std::time::Duration::from_secs(30).saturating_sub(common);
            let mut exact=0;let mut positive=0;let mut peak=0;let mut work=0;let mut calls=0;let mut first_ns=None;
            let mut failures=BTreeMap::<&str,usize>::new();let mut kernel_ns=0u128;
            for x in 0..4u64{
                if std::time::Instant::now()>=deadline{break;}
                let (prefix,pr)=reduce(fixed_input(general.clone(),x));
                let scale=gr.scale2+pr.scale2;
                // One boundary contraction for all bad outputs or the
                // matched repeated-fibre baseline. Full diagnostics
                // continue after the first positive, record prefix cost.
                let queries=if boundary{vec![(mask,mask)]}else{(mask..2*mask).map(|z|(2*mask-1,z)).collect()};
                for (fixed,z) in queries{
                    if std::time::Instant::now()>=deadline{break;}
                    calls+=1;let t=std::time::Instant::now();
                    let got=contract_boundary8(&prefix,fixed,z,deadline);
                    kernel_ns+=t.elapsed().as_nanos();
                    match got{
                        Ok((a,w,cost))=>{
                            peak=peak.max(w);work+=cost;
                            for (i,r) in a.into_iter().enumerate(){
                                let out=z|deposit8(i,(2*mask-1)&!fixed);
                                let want=oracle[x as usize][out as usize].iter().map(|&v|i128::from(v)*i128::from(v)).sum::<i128>();
                                assert_eq!(z8_norm(r).checked_shl(scale).unwrap(),want,"{name} {x} {out}");
                                if boundary{
                                    if let Some(prev)=receipts.get(&(x,out)){assert_eq!(r,*prev);paired+=1;}
                                }else{receipts.insert((x,out),r);}
                                exact+=1;positive+=usize::from(r!=[0;4]);
                                if r!=[0;4]&&first_ns.is_none(){first_ns=Some((common+start.elapsed()).as_nanos());}
                            }
                        }
                        Err(reason)=>{*failures.entry(reason).or_default()+=1;}
                    }
                }
            }
            let planned=4*mask as usize;
            let verdict=if positive>0{"REFUTED"}else if exact==planned{"PROVED"}else{"UNKNOWN"};
            println!("HOARE_FEYNMAN_BOUNDARY8 name={name} boundary={boundary} exact={exact} planned={planned} positive={positive} verdict={verdict} calls={calls} h={} peak_width={peak} work={work} kernel_ns={kernel_ns} accounted_ns={} first_ns={first_ns:?} failures={failures:?}",h(&general),(common+start.elapsed()).as_nanos());
        }
        println!("HOARE_FEYNMAN_BOUNDARY8_PARITY name={name} paired={paired}");

        let start=std::time::Instant::now();
        let deadline=start+std::time::Duration::from_secs(30).saturating_sub(common);
        let mut exact=0;let mut positive=0;let mut parity=0;let mut calls=0;let mut fallback=0;
        let mut peak=0;let mut work=0;let mut candidates=0;let mut rejected=0;let mut kernel_ns=0u128;
        let mut masks=Vec::new();let mut failures=BTreeMap::<&str,usize>::new();
        for x in 0..4u64{
            if std::time::Instant::now()>=deadline{break;}
            let (prefix,pr)=reduce(fixed_input(general.clone(),x));let scale=gr.scale2+pr.scale2;
            let t=std::time::Instant::now();let result=tiled_boundary8(&prefix,mask,mask,deadline);
            kernel_ns+=t.elapsed().as_nanos();
            match result{
                Ok(r)=>{
                    calls+=r.calls;fallback+=r.fallback_calls;peak=peak.max(r.peak);work+=r.work;
                    candidates+=r.candidates;rejected+=r.rejected;masks.push(r.fixed);
                    for (k,v) in r.failures{*failures.entry(k).or_default()+=v;}
                    for (i,a) in r.values.into_iter().enumerate(){
                        let Some(a)=a else{continue;};let out=mask|i as u64;
                        let want=oracle[x as usize][out as usize].iter().map(|&v|i128::from(v)*i128::from(v)).sum::<i128>();
                        assert_eq!(z8_norm(a).checked_shl(scale).unwrap(),want);
                        if let Some(prev)=receipts.get(&(x,out)){assert_eq!(a,*prev);parity+=1;}
                        exact+=1;positive+=usize::from(a!=[0;4]);
                    }
                }
                Err(reason)=>{*failures.entry(reason).or_default()+=1;}
            }
        }
        let planned=4*mask as usize;
        let verdict=if positive>0{"REFUTED"}else if exact==planned{"PROVED"}else{"UNKNOWN"};
        println!("HOARE_FEYNMAN_TILING8 name={name} exact={exact} planned={planned} positive={positive} verdict={verdict} parity={parity} calls={calls} fallback={fallback} candidates={candidates} rejected={rejected} masks={masks:?} peak={peak} work={work} kernel_ns={kernel_ns} accounted_ns={} failures={failures:?}",(common+start.elapsed()).as_nanos());
        let start=std::time::Instant::now();
        let deadline=start+std::time::Duration::from_secs(30).saturating_sub(common);
        let mut exact=0;let mut positive=0;let mut parity=0;let mut calls=0;let mut fallback=0;
        let mut peak=0;let mut work=0;let mut candidates=0;let mut rejected=0;let mut kernel_ns=0u128;
        let mut masks=Vec::new();let mut failures=BTreeMap::<&str,usize>::new();
        for x in 0..4u64{
            if std::time::Instant::now()>=deadline{break;}
            let (prefix,pr)=reduce(fixed_input(general.clone(),x));let scale=gr.scale2+pr.scale2;
            let t=std::time::Instant::now();let result=tiled_boundary8_with(&prefix,mask,mask,deadline,true,|plan,z,d|execute_boundary8(plan,z,d));
            kernel_ns+=t.elapsed().as_nanos();
            match result{
                Ok(r)=>{
                    calls+=r.calls;fallback+=r.fallback_calls;peak=peak.max(r.peak);work+=r.work;
                    candidates+=r.candidates;rejected+=r.rejected;masks.push(r.fixed);
                    for (k,v) in r.failures{*failures.entry(k).or_default()+=v;}
                    for (i,a) in r.values.into_iter().enumerate(){
                        let Some(a)=a else{continue;};let out=mask|i as u64;
                        let want=oracle[x as usize][out as usize].iter().map(|&v|i128::from(v)*i128::from(v)).sum::<i128>();
                        assert_eq!(z8_norm(a).checked_shl(scale).unwrap(),want);
                        if let Some(prev)=receipts.get(&(x,out)){assert_eq!(a,*prev);parity+=1;}
                        exact+=1;positive+=usize::from(a!=[0;4]);
                    }
                }
                Err(reason)=>{*failures.entry(reason).or_default()+=1;}
            }
        }
        let planned=4*mask as usize;
        let verdict=if positive>0{"REFUTED"}else if exact==planned{"PROVED"}else{"UNKNOWN"};
        println!("HOARE_FEYNMAN_FAST_TILING8 name={name} exact={exact} planned={planned} positive={positive} verdict={verdict} parity={parity} calls={calls} fallback={fallback} candidates={candidates} rejected={rejected} masks={masks:?} peak={peak} work={work} kernel_ns={kernel_ns} accounted_ns={} failures={failures:?}",(common+start.elapsed()).as_nanos());

    }
}


#[test]
fn native_qwalk_cyclo64_pilot(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{return;};
    for name in ["vchain","noancilla"]{
        let src=std::fs::read_to_string(std::path::Path::new(&dir).join(format!("{name}.qasm"))).unwrap();
        let (ops,n,_)=source_ops(&src);assert_eq!(n,5);
        let (native,width)=parse_qasm_str(&src).unwrap();assert_eq!((native,width),(ops.clone(),n));
        let t=std::time::Instant::now();let deadline=t+std::time::Duration::from_secs(30);
        let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let zero=Poly::default();raw.p.substitute_var_with_poly(4,&zero);raw.f.substitute_var_with_poly(4,&zero);
        let (general,gr)=reduce(raw);
        let mut exact=0;let mut positive=0;let mut calls=0;let mut peak=0;let mut work=0;
        let mut failures=BTreeMap::<&str,usize>::new();
        for x in 0..16u64{
            if std::time::Instant::now()>=deadline{break;}
            let (prefix,pr)=reduce(fixed_input(general.clone(),x));assert!(!pr.limit);
            let got=prepare_cyclo_boundary(&prefix,16,32,deadline)
                .and_then(|p|{calls+=1;execute_cyclo_boundary::<32>(&p,16,deadline)});
            match got{
                Ok((a,w,cost))=>{
                    assert_eq!(a.len(),16);peak=peak.max(w);work+=cost;
                    let nonzero:Vec<_>=a.iter().enumerate().filter(|(_,r)|**r!=[0;32]).map(|(i,_)|16+i).collect();
                    if name=="vchain"{assert!(nonzero.is_empty());}
                    else{assert!(!nonzero.is_empty());if x==0{assert_eq!(nonzero,vec![28,31]);}}
                    exact+=a.len();positive+=nonzero.len();
                    println!("HOARE_QWALK_CYCLO64_INPUT name={name} x={x} h={} width={w} scale2={} nonzero={nonzero:?}",h(&prefix),gr.scale2+pr.scale2);
                }
                Err(reason)=>{*failures.entry(reason).or_default()+=1;}
            }
        }
        let verdict=if positive>0{"REFUTED"}else if exact==256{"PROVED"}else{"UNKNOWN"};
        println!("HOARE_QWALK_CYCLO64_SUMMARY name={name} exact={exact} positive={positive} verdict={verdict} calls={calls} width={peak} work={work} elapsed_ns={} failures={failures:?}",t.elapsed().as_nanos());
    }
}


// Matched D64 vs minimum-order kernels on exactly the same checkpoint.
// Oracle support is held out from planning. Full coefficient vectors
// are compared in a common Z[zeta64] basis, including complex phase.
#[test]
fn native_qwalk_minimum_basis_pilot(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{return;};
    for name in ["vchain","noancilla"]{
        let src=std::fs::read_to_string(std::path::Path::new(&dir).join(format!("{name}.qasm"))).unwrap();
        let (ops,n,_)=source_ops(&src);assert_eq!(n,5);
        let (native,width)=parse_qasm_str(&src).unwrap();assert_eq!((native,width),(ops.clone(),n));
        let t=std::time::Instant::now();
        let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let build_ns=t.elapsed().as_nanos();
        let t=std::time::Instant::now();
        let zero=Poly::default();raw.p.substitute_var_with_poly(4,&zero);raw.f.substitute_var_with_poly(4,&zero);
        let (general,gr)=reduce(raw);assert!(!gr.limit);
        let general_ns=t.elapsed().as_nanos();
        let common=build_ns+general_ns;
        let mut spent=[common;2];let mut prefix_ns=0u128;let mut plan_ns=[0u128;2];let mut exec_ns=[0u128;2];
        let mut works=[0usize;2];let mut exact=[0usize;2];let mut positives=[0usize;2];
        let mut degree_hist=BTreeMap::<usize,usize>::new();
        let mut failures=[BTreeMap::<&str,usize>::new(),BTreeMap::<&str,usize>::new()];
        let mut paired=0;let mut first=[None;2];
        let budget=30_000_000_000u128;
        for x in 0..16u64{
            if spent.iter().all(|&v|v>=budget){break;}
            let t=std::time::Instant::now();
            let (prefix,pr)=reduce(fixed_input(general.clone(),x));assert!(!pr.limit);
            let ns=t.elapsed().as_nanos();prefix_ns+=ns;
            let mut out:[Option<Vec<Z64>>;2]=[None,None];
            // Alternate execution order to reduce systematic warm-cache bias.
            for arm in [x as usize%2,1-x as usize%2]{
                if spent[arm]>=budget{continue;}
                spent[arm]+=ns;
                if spent[arm]>=budget{*failures[arm].entry("DEADLINE").or_default()+=1;continue;}
                let start=std::time::Instant::now();
                let deadline=start+std::time::Duration::from_nanos((budget-spent[arm]) as u64);
                let p=(||{
                    let d=if arm==0{32}else{minimum_cyclo_degree(&prefix)?};
                    if arm==1{*degree_hist.entry(2*d).or_default()+=1;}
                    prepare_cyclo_boundary(&prefix,16,d,deadline)
                })();
                plan_ns[arm]+=start.elapsed().as_nanos();
                let t=std::time::Instant::now();
                let result=p.and_then(|p|execute_minimum_boundary(&p,16,deadline));
                exec_ns[arm]+=t.elapsed().as_nanos();
                spent[arm]+=start.elapsed().as_nanos();
                match result{
                    Ok((a,_,w))=>{
                        assert_eq!(a.len(),16);works[arm]+=w;exact[arm]+=a.len();
                        let nonzero:Vec<_>=a.iter().enumerate().filter(|(_,r)|**r!=[0;32]).map(|(i,_)|16+i).collect();
                        if name=="vchain"{assert!(nonzero.is_empty());}
                        else{assert_eq!(nonzero.len(),2);if x==0{assert_eq!(nonzero,vec![28,31]);}}
                        if !nonzero.is_empty()&&first[arm].is_none(){first[arm]=Some(spent[arm]);}
                        positives[arm]+=nonzero.len();out[arm]=Some(a);
                    }
                    Err(reason)=>{*failures[arm].entry(reason).or_default()+=1;}
                }
            }
            if let [Some(a),Some(b)]=&out{assert_eq!(a,b);paired+=a.len();}
        }
        for arm in 0..2{
            let verdict=if positives[arm]>0{"REFUTED"}else if exact[arm]==256{"PROVED"}else{"UNKNOWN"};
            println!("HOARE_QWALK_MIN_BASIS name={name} arm={} exact={} positive={} verdict={verdict} work={} build_ns={build_ns} general_ns={general_ns} shared_prefix_ns={prefix_ns} plan_ns={} exec_ns={} accounted_ns={} first_ns={:?} failures={:?}",
                if arm==0{"d64"}else{"minimum"},exact[arm],positives[arm],works[arm],plan_ns[arm],exec_ns[arm],spent[arm],first[arm],failures[arm]);
        }
        println!("HOARE_QWALK_MIN_BASIS_PARITY name={name} paired={paired} orders={degree_hist:?}");
    }
}


// Explicit finite coverage state: the oracle is not an input to the verdict.
fn sector_verdict(values:&[Option<Z64>])->&'static str{
    if values.iter().flatten().any(|v|*v!=[0;32]){"REFUTED"}
    else if !values.is_empty()&&values.iter().all(Option::is_some){"PROVED"}
    else{"UNKNOWN"}
}
fn early_sector_minimum(ps:&PathSum,mask:u64,value:u64,deadline:std::time::Instant)
    ->Result<Vec<Z64>,&'static str>{
    let d=minimum_cyclo_degree(ps)?;
    let p=prepare_cyclo_boundary(ps,mask,d,deadline)?;
    execute_minimum_boundary(&p,value,deadline).map(|(a,_,_)|a)
}
#[test]
fn native_early_sector_coverage_controls(){
    let mut v=vec![None;4];
    assert_eq!(sector_verdict(&v),"UNKNOWN");
    v[0]=Some([0;32]);assert_eq!(sector_verdict(&v),"UNKNOWN");
    let mut a=[0;32];a[7]=1;v[2]=Some(a);assert_eq!(sector_verdict(&v),"REFUTED");
    v.fill(Some([0;32]));assert_eq!(sector_verdict(&v),"PROVED");
    assert_eq!(sector_verdict(&[]),"UNKNOWN");
    let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
    for _ in 0..4{QuantumOp::H(0).apply(&mut ps,false);}
    let h0=h(&ps);let (p,r,attempts,expired)=reduce_until(ps.clone(),std::time::Instant::now());
    assert!(expired);assert_eq!(attempts,0);assert_eq!(r.scale2,0);assert_eq!(h(&p),h0);
    let (p,r,_,expired)=reduce_until(ps.clone(),std::time::Instant::now()+std::time::Duration::from_secs(5));
    let (q,s)=reduce(ps);assert!(!expired);assert_eq!(r.scale2,s.scale2);assert_eq!(entries(&p),entries(&q));
    println!("HOARE_NATIVE_EARLY_COVERAGE partial_zero_unknown=true partial_positive_refuted=true full_zero_proved=true expired_unchanged=true");
}
#[test]
fn native_qwalk_early_witness(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{return;};
    for name in ["vchain","noancilla"]{
        let src=std::fs::read_to_string(std::path::Path::new(&dir).join(format!("{name}.qasm"))).unwrap();
        let (ops,n,_)=source_ops(&src);assert_eq!(n,5);
        let (native,width)=parse_qasm_str(&src).unwrap();assert_eq!((native,width),(ops.clone(),n));
        let t=std::time::Instant::now();
        let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let build=t.elapsed();assert!(admitted(&raw));
        let mut expected:BTreeMap<u64,Vec<Z64>>=BTreeMap::new();
        for arm in ["general-first","input-first","probe-then-general"]{
            let start=std::time::Instant::now();
            let deadline=start+std::time::Duration::from_secs(30).saturating_sub(build);
            let mut values=vec![None;256];
            let mut general_ns=0u128;let mut input_ns=0u128;let mut solve_ns=0u128;
            let mut attempts=0usize;let mut probe_ns=0u128;let mut calls=0usize;
            let mut failures=BTreeMap::<&str,usize>::new();
            let mut first=None;let mut paired=0;
            // Bounded first legal-input probe only; no oracle-driven input
            // choice, no inferred zero on rejected/incomplete work.
            let mut general=None;
            if arm=="probe-then-general"{
                let pstart=std::time::Instant::now();
                let pd=deadline.min(pstart+std::time::Duration::from_millis(500));
                let (p,r,a,expired)=reduce_until(fixed_input(raw.clone(),0),pd);attempts+=a;
                if !expired&&!r.limit{
                    calls+=1;
                    match early_sector_minimum(&p,16,16,pd){
                        Ok(v)=>{
                            assert_eq!(v.len(),16);
                            let nonzero=v.iter().any(|r|*r!=[0;32]);
                            for (i,a) in v.into_iter().enumerate(){values[i]=Some(a);}
                            if nonzero{first=Some((build+start.elapsed()).as_nanos());}
                        }
                        Err(e)=>{*failures.entry(e).or_default()+=1;}
                    }
                }else{*failures.entry(if expired{"PROBE_DEADLINE"}else{"RR_LIMIT"}).or_default()+=1;}
                probe_ns=pstart.elapsed().as_nanos();
            }
            if sector_verdict(&values)!="REFUTED"&&arm!="input-first"&&std::time::Instant::now()<deadline{
                let t=std::time::Instant::now();
                let mut p=raw.clone();let zero=Poly::default();
                p.p.substitute_var_with_poly(4,&zero);p.f.substitute_var_with_poly(4,&zero);
                let (p,r,a,expired)=reduce_until(p,deadline);attempts+=a;
                general_ns=t.elapsed().as_nanos();
                if !expired&&!r.limit{general=Some(p);}
                else{*failures.entry(if expired{"DEADLINE"}else{"RR_LIMIT"}).or_default()+=1;}
            }
            for x in 0..16u64{
                if sector_verdict(&values)=="REFUTED"||std::time::Instant::now()>=deadline{break;}
                let base=if arm=="input-first"{&raw}else if let Some(p)=general.as_ref(){p}else{break};
                let offset=x as usize*16;
                if values[offset..offset+16].iter().all(Option::is_some){continue;}
                let t=std::time::Instant::now();
                let (p,r,a,expired)=reduce_until(fixed_input(base.clone(),x),deadline);
                attempts+=a;input_ns+=t.elapsed().as_nanos();
                if expired||r.limit{*failures.entry(if expired{"DEADLINE"}else{"RR_LIMIT"}).or_default()+=1;continue;}
                let t=std::time::Instant::now();calls+=1;
                let result=early_sector_minimum(&p,16,16,deadline);
                solve_ns+=t.elapsed().as_nanos();
                match result{
                    Ok(v)=>{
                        assert_eq!(v.len(),16);
                        if arm=="general-first"{expected.insert(x,v.clone());}
                        else if let Some(w)=expected.get(&x){
                            // Rule order may change the common complex scale;
                            // only compare exact support across different RR routes.
                            for (a,b) in v.iter().zip(w){assert_eq!(*a==[0;32],*b==[0;32]);paired+=1;}
                        }
                        let nonzero=v.iter().any(|a|*a!=[0;32]);
                        for (i,a) in v.into_iter().enumerate(){values[offset+i]=Some(a);}
                        if nonzero{first=Some((build+start.elapsed()).as_nanos());}
                    }
                    Err(e)=>{*failures.entry(e).or_default()+=1;}
                }
            }
            // The bounded probe may finish before the general route.
            // Compare its support to the independently accepted reference
            // only after the route has stopped, never use it to choose x.
            let positive=values.iter().flatten().filter(|v|**v!=[0;32]).count();
            let exact=values.iter().flatten().count();
            if name=="vchain"{assert_eq!(positive,0);}
            else{for x in 0..16usize{
                let v=&values[16*x..16*x+16];
                if v.iter().all(Option::is_some){assert_eq!(v.iter().flatten().filter(|a|**a!=[0;32]).count(),2);}
            }}
            if name=="noancilla"&&values[..16].iter().all(Option::is_some){
                let support:Vec<_>=values[..16].iter().enumerate().filter(|(_,a)|a.as_ref().is_some_and(|v|*v!=[0;32])).map(|(i,_)|16+i).collect();
                assert_eq!(support,vec![28,31]);
            }
            let verdict=sector_verdict(&values);
            println!("HOARE_QWALK_EARLY name={name} arm={arm} exact={exact} positive={positive} verdict={verdict} calls={calls} attempts={attempts} build_ns={} general_ns={general_ns} input_ns={input_ns} probe_ns={probe_ns} solve_ns={solve_ns} first_ns={first:?} paired_support={paired} accounted_ns={} failures={failures:?}",build.as_nanos(),(build+start.elapsed()).as_nanos());
        }
    }
}


fn assert_rr_index_parity(a:&PathSum,b:&PathSum,ar:&Receipt,br:&Receipt,
    at:&[(u32,usize,Option<u32>)],bt:&[(u32,usize,Option<u32>)]){
    assert_eq!(at,bt);
    assert_eq!(a.p.terms,b.p.terms);
    assert_eq!(a.f.functions,b.f.functions);
    assert_eq!(a.v.path_vars,b.v.path_vars);
    assert_eq!((ar.scale2,ar.limit),(br.scale2,br.limit));
}

#[test]
fn native_hh_incident_matcher(){
    use quprs::{Rational,PhaseCoeff};
    let mut seed=20261126u64;
    let mut checks=0;let mut positives=0;
    let mut scan=HhScanMetrics::default();let mut indexed=HhScanMetrics::default();
    for trial in 0..1024{
        let mut ps=PathSum::new(2);ps.set_auto_reduce(false);
        let ids:Vec<u32>=(0..8).map(|_|ps.v.get_fresh_var()).collect();
        for _ in 0..24{
            seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            let y=ids[(seed>>32) as usize%8];
            let z=ids[(seed>>40) as usize%8];
            let mut m=vec![y,z];m.sort_unstable();m.dedup();
            let c=if trial%3==0{4}else{1+(seed>>48) as i64%7};
            ps.p.add_term(m,PhaseCoeff::new_constant(Rational::new(c as _,8)));
        }
        // Deterministic isolated internal HH positive and input-target negative.
        if trial%4==0{
            let y=ids[0];ps.p.terms.retain(|m,_|!m.contains(&y));
            let target=if trial%8==0{ids[7]}else{0};
            ps.p.add_term(vec![target.min(y),target.max(y)],PhaseCoeff::new_constant(Rational::HALF));
        }
        let mut incident:HhIncident<'_>=BTreeMap::new();
        for (m,c) in &ps.p.terms{for &y in m{incident.entry(y).or_default().push((m,c));indexed.incidences+=1;}}
        for &y in &ids{
            let a=hh_target(&ps,y);
            let b=hh_target_counted(ps.v.num_qubits,y,&ps.p.terms,&mut scan);
            let c=hh_target_counted(ps.v.num_qubits,y,incident.get(&y).into_iter().flatten().copied(),&mut indexed);
            assert_eq!(a,b);assert_eq!(a,c);checks+=1;positives+=usize::from(a.is_some());
        }
    }
    assert_eq!(checks,8192);assert!(positives>0);
    println!("HOARE_NATIVE_HH_INCIDENT checks={checks} positive={positives} scan_visits={} indexed_visits={} incidences={}",scan.visits,indexed.visits,indexed.incidences);
}

#[test]
fn native_indexed_rr_parity(){
    use QuantumOp as G;
    let mut seed=20261126u64;
    let mut attempts=0;let mut skipped=0;let mut accepted=0;
    for _ in 0..128{
        let mut ps=PathSum::new(3);ps.set_auto_reduce(false);
        for _ in 0..16{
            seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            let q=(seed>>32) as usize%3;
            let op=match (seed>>40)%6{
                0=>G::H(q),1=>G::T(q),2=>G::S(q),3=>G::TDG(q),
                4=>G::CX(q,(q+1)%3),_=>G::X(q),
            };op.apply(&mut ps,false);
        }
        for x in 0..8u64{
            let raw=fixed_input(ps.clone(),x);
            let deadline=std::time::Instant::now()+std::time::Duration::from_secs(5);
            let (a,ar,aa,_,ae,at)=reduce_indexed(raw.clone(),deadline,false);
            let (b,br,ba,bs,be,bt)=reduce_indexed(raw.clone(),deadline,true);
            assert!(!ae&&!be);assert_rr_index_parity(&a,&b,&ar,&br,&at,&bt);
            let (c,cr,ca,cs,ce,ct)=reduce_indexed_hh(raw,deadline,true,true,&mut HhScanMetrics::default());
            assert!(!ce);assert_rr_index_parity(&b,&c,&br,&cr,&bt,&ct);
            assert_eq!((ba,bs),(ca,cs));
            assert_eq!(aa,ba+bs);attempts+=aa;skipped+=bs;accepted+=at.len();
        }
    }
    assert!(skipped>0&&accepted>0);
    println!("HOARE_NATIVE_INDEXED_RR cases=1024 baseline_attempts={attempts} skipped={skipped} accepted={accepted} trace_exact=true");
}
#[test]
fn native_qwalk_indexed_rr(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{return;};
    for name in ["vchain","noancilla"]{
        let src=std::fs::read_to_string(std::path::Path::new(&dir).join(format!("{name}.qasm"))).unwrap();
        let (ops,n,_)=source_ops(&src);assert_eq!(n,5);
        let (native,width)=parse_qasm_str(&src).unwrap();assert_eq!((native,width),(ops.clone(),n));
        let t=std::time::Instant::now();let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let zero=Poly::default();raw.p.substitute_var_with_poly(4,&zero);raw.f.substitute_var_with_poly(4,&zero);
        let build=t.elapsed();
        let mut prior:Option<(PathSum,Receipt,Vec<(u32,usize,Option<u32>)>)>=None;
        let mut reference=BTreeMap::<u64,Vec<Z64>>::new();
        for indexed in [false,true]{
            let start=std::time::Instant::now();
            let deadline=start+std::time::Duration::from_secs(30).saturating_sub(build);
            let t=std::time::Instant::now();
            let (general,gr,mut attempts,mut skipped,expired,trace)=reduce_indexed(raw.clone(),deadline,indexed);
            let rr_ns=t.elapsed().as_nanos();
            assert!(!expired&&!gr.limit);
            if let Some((a,ar,at))=&prior{assert_rr_index_parity(a,&general,ar,&gr,at,&trace);}
            else{prior=Some((general.clone(),gr,trace));}
            let mut values=vec![None;256];let mut input_ns=0;let mut solve_ns=0;let mut paired=0;
            let mut failures=BTreeMap::<&str,usize>::new();let mut first=None;
            for x in 0..16u64{
                if std::time::Instant::now()>=deadline||sector_verdict(&values)=="REFUTED"{break;}
                let t=std::time::Instant::now();
                let (p,r,a,k,e,_)=reduce_indexed(fixed_input(general.clone(),x),deadline,indexed);
                attempts+=a;skipped+=k;input_ns+=t.elapsed().as_nanos();
                if e||r.limit{*failures.entry(if e{"DEADLINE"}else{"RR_LIMIT"}).or_default()+=1;continue;}
                let t=std::time::Instant::now();
                let result=early_sector_minimum(&p,16,16,deadline);solve_ns+=t.elapsed().as_nanos();
                match result{
                    Ok(v)=>{
                        assert_eq!(v.len(),16);
                        if indexed{if let Some(w)=reference.get(&x){assert_eq!(&v,w);paired+=16;}}
                        else{reference.insert(x,v.clone());}
                        if name=="vchain"{assert!(v.iter().all(|a|*a==[0;32]));}
                        else if x==0{
                            let support:Vec<_>=v.iter().enumerate().filter(|(_,a)|**a!=[0;32]).map(|(i,_)|16+i).collect();
                            assert_eq!(support,vec![28,31]);
                        }
                        let nonzero=v.iter().any(|a|*a!=[0;32]);
                        for (i,a) in v.into_iter().enumerate(){values[x as usize*16+i]=Some(a);}
                        if nonzero{first=Some((build+start.elapsed()).as_nanos());}
                    }
                    Err(e)=>{*failures.entry(e).or_default()+=1;}
                }
            }
            let exact=values.iter().flatten().count();let positive=values.iter().flatten().filter(|a|**a!=[0;32]).count();
            println!("HOARE_QWALK_INDEXED_RR name={name} indexed={indexed} exact={exact} positive={positive} verdict={} attempts={attempts} skipped={skipped} paired={paired} general_ns={rr_ns} input_ns={input_ns} solve_ns={solve_ns} first_ns={first:?} accounted_ns={} failures={failures:?}",sector_verdict(&values),(build+start.elapsed()).as_nanos());
        }
    }
}

#[test]
fn native_qwalk_hh_incident_rr(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{return;};
    for name in ["vchain","noancilla"]{
        let src=std::fs::read_to_string(std::path::Path::new(&dir).join(format!("{name}.qasm"))).unwrap();
        let (ops,n,_)=source_ops(&src);assert_eq!(n,5);
        let (native,width)=parse_qasm_str(&src).unwrap();assert_eq!((native,width),(ops.clone(),n));
        let t=std::time::Instant::now();let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let zero=Poly::default();raw.p.substitute_var_with_poly(4,&zero);raw.f.substitute_var_with_poly(4,&zero);
        let build=t.elapsed();
        let mut prior:Option<(PathSum,Receipt,Vec<(u32,usize,Option<u32>)>)>=None;
        let mut reference=BTreeMap::<u64,Vec<Z64>>::new();
        for (rep,hh_indexed) in [false,true,true,false].into_iter().enumerate(){
            let mut metrics=HhScanMetrics::default();
            let start=std::time::Instant::now();
            let deadline=start+std::time::Duration::from_secs(30).saturating_sub(build);
            let t=std::time::Instant::now();
            let (general,gr,mut attempts,mut skipped,expired,trace)=reduce_indexed_hh(raw.clone(),deadline,true,hh_indexed,&mut metrics);
            let rr_ns=t.elapsed().as_nanos();
            assert!(!expired&&!gr.limit);
            if let Some((a,ar,at))=&prior{assert_rr_index_parity(a,&general,ar,&gr,at,&trace);}
            else{prior=Some((general.clone(),gr,trace));}
            let mut values=vec![None;256];let mut input_ns=0;let mut solve_ns=0;let mut paired=0;
            let mut failures=BTreeMap::<&str,usize>::new();let mut first=None;
            for x in 0..16u64{
                if std::time::Instant::now()>=deadline||sector_verdict(&values)=="REFUTED"{break;}
                let t=std::time::Instant::now();
                let (p,r,a,k,e,_)=reduce_indexed_hh(fixed_input(general.clone(),x),deadline,true,hh_indexed,&mut metrics);
                attempts+=a;skipped+=k;input_ns+=t.elapsed().as_nanos();
                if e||r.limit{*failures.entry(if e{"DEADLINE"}else{"RR_LIMIT"}).or_default()+=1;continue;}
                let t=std::time::Instant::now();
                let result=early_sector_minimum(&p,16,16,deadline);solve_ns+=t.elapsed().as_nanos();
                match result{
                    Ok(v)=>{
                        assert_eq!(v.len(),16);
                        if rep!=0{if let Some(w)=reference.get(&x){assert_eq!(&v,w);paired+=16;}}
                        else{reference.insert(x,v.clone());}
                        if name=="vchain"{assert!(v.iter().all(|a|*a==[0;32]));}
                        else if x==0{
                            let support:Vec<_>=v.iter().enumerate().filter(|(_,a)|**a!=[0;32]).map(|(i,_)|16+i).collect();
                            assert_eq!(support,vec![28,31]);
                        }
                        let nonzero=v.iter().any(|a|*a!=[0;32]);
                        for (i,a) in v.into_iter().enumerate(){values[x as usize*16+i]=Some(a);}
                        if nonzero{first=Some((build+start.elapsed()).as_nanos());}
                    }
                    Err(e)=>{*failures.entry(e).or_default()+=1;}
                }
            }
            let exact=values.iter().flatten().count();let positive=values.iter().flatten().filter(|a|**a!=[0;32]).count();
            println!("HOARE_QWALK_HH_INCIDENT name={name} rep={rep} indexed={hh_indexed} exact={exact} positive={positive} verdict={} attempts={attempts} skipped={skipped} paired={paired} general_ns={rr_ns} input_ns={input_ns} solve_ns={solve_ns} first_ns={first:?} accounted_ns={} hh_calls={} hh_visits={} incidences={} failures={failures:?}",sector_verdict(&values),(build+start.elapsed()).as_nanos(),metrics.calls,metrics.visits,metrics.incidences);
        }
    }
}


// Staged sector dispatcher: both backends refer to exactly the same
// fixed-input residual. Emit CNF only when the factor result is absent.
// The Python consumer charges native preparation and live GPMC calls.
#[test]
fn native_hybrid_sector_export(){
    use QuantumOp as G;
    let dir=std::env::var_os("HOARE_PAPER_PROJECTED_DIR").map(std::path::PathBuf::from);
    let mut manifest=String::new();
    let mut cases:Vec<(&str,Vec<QuantumOp>,usize,Vec<u64>,Vec<bool>)>=Vec::new();
    for (name,src) in [
        ("qft4",include_str!("../../../benchmarks/Feynman/qft_4.qasm")),
        ("mod5",include_str!("../../../benchmarks/Feynman/mod5_4.qasm")),
        ("hwb6",include_str!("../../../benchmarks/Feynman/hwb6.qasm")),
        ("barenco5",include_str!("../../../benchmarks/Feynman/barenco_tof_5.qasm")),
    ]{
        let (ops,n)=feynman_source_ops(src);
        let (native,width)=parse_qasm_str(src).unwrap();
        assert_eq!((native,width),(ops.clone(),n));
        let mask=1u64<<(n-1);
        let expected=(0..4u64).map(|x|gate_reference_width(&ops,x,n).iter().enumerate()
            .any(|(z,r)|z as u64&mask!=0&&r.iter().any(|&v|v!=0))).collect();
        cases.push((name,ops,n,(0..4).collect(),expected));
    }
    // Real unitary controls. Wide output sector with no hidden variables
    // is intentionally rejected by the boundary coverage-width guard.
    cases.push(("wide14-zero",vec![G::H(0),G::H(1)],14,vec![0,1],vec![false,false]));
    cases.push(("wide14-positive",vec![G::H(0),G::X(13)],14,vec![0,1],vec![true,true]));
    // q12 controls fanout of H(q0) into q1..q11. For x=0 the
    // selected forbidden sector is zero. For x=4096 the retained
    // twelve outputs depend on the same hidden bit (bucket width13).
    let mut fan=vec![G::H(0)];
    for q in 1..12{fan.push(G::CCX(12,0,q));}
    cases.push(("mixed13",fan,13,vec![0,4096],vec![false,true]));
    let mut total=0;let mut factor=0;let mut exported=0;
    for (name,ops,n,inputs,expected) in cases{
        let t=std::time::Instant::now();
        let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
        for op in &ops{op.apply(&mut raw,false);}
        let (general,gr,_,_,expired,_)=reduce_indexed(raw,t+std::time::Duration::from_secs(30),true);
        assert!(!expired&&!gr.limit);let common=t.elapsed().as_nanos();
        let mask=1u64<<(n-1);
        let post=vec![Anf::from([0,mask])];
        let deadline=t+std::time::Duration::from_secs(30);
        for (ord,(&x,&want)) in inputs.iter().zip(&expected).enumerate(){
            let t=std::time::Instant::now();
            let (prefix,r,_,_,expired,_)=reduce_indexed(fixed_input(general.clone(),x),deadline,true);
            let prefix_ns=t.elapsed().as_nanos();
            let t=std::time::Instant::now();
            let result=if expired{Err("DEADLINE")}else if r.limit{Err("RR_LIMIT")}
                else{early_sector_minimum(&prefix,mask,mask,deadline)};
            let factor_ns=t.elapsed().as_nanos();
            let key=format!("hybrid-sector-{name}-{ord}");
            let mut mass="-".to_owned();let mut reason="-";let mut status="FACTOR_EXACT";
            let mut vars=0;let mut clauses=0;let mut sign=0;let mut d=0;let mut enc_ns=0;
            match result{
                Ok(v)=>{
                    assert_eq!(v.len(),mask as usize);
                    // Unnormalized coefficient-square sum in a common basis.
                    // The embedding preserves this sum; no physical leakage claim.
                    let m=v.iter().flatten().try_fold(0i128,|a,&b|a.checked_add(b.checked_mul(b)?)).unwrap();
                    assert_eq!(m!=0,want);mass=m.to_string();factor+=1;
                }
                Err(e)=>{
                    reason=e;status="UNSUPPORTED";
                    if !expired&&!r.limit&&std::time::Instant::now()<deadline{
                        let pre:Vec<Anf>=(0..n).map(|i|if x>>i&1==1{Anf::from([1u64<<i])}
                            else{Anf::from([0,1u64<<i])}).collect();
                        let t=std::time::Instant::now();
                        if let Some((c,l,den))=native_dyadic_projection_variant(&prefix,&pre,&post,32768,262144,true){
                            vars=c.vars;clauses=c.clauses.len();sign=l;d=den;
                            if let Some(dir)=&dir{
                                let mut text=format!("p cnf {vars} {clauses}\n");
                                for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                                std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                            }
                            status="WMC_READY";exported+=1;
                        }
                        enc_ns=t.elapsed().as_nanos();
                    }
                }
            }
            if name.starts_with("wide14"){assert_eq!(reason,"WIDTH_LIMIT");assert_eq!(status,"WMC_READY");}
            if name=="mixed13"{
                if ord==0{assert_eq!(status,"FACTOR_EXACT");}
                else{assert_eq!(reason,"WIDTH_LIMIT");assert_eq!(status,"WMC_READY");}
            }
            manifest.push_str(&format!("{key}\t{name}\t{ord}\t{x}\t{n}\t{}\t{status}\t{reason}\t{mass}\t{vars}\t{clauses}\t{sign}\t{d}\t{common}\t{prefix_ns}\t{factor_ns}\t{enc_ns}\t{want}\n",h(&prefix)));
            total+=1;
            println!("HOARE_NATIVE_HYBRID_SECTOR name={name} x={x} status={status} reason={reason} scale2={}",gr.scale2+r.scale2);
        }
    }
    assert_eq!(total,22);assert_eq!(factor,17);assert_eq!(exported,5);
    if let Some(dir)=&dir{std::fs::write(dir.join("hybrid-sector.tsv"),manifest).unwrap();}
    println!("HOARE_NATIVE_HYBRID_EXPORT sectors={total} factor={factor} wmc_ready={exported}");
}


fn online_hybrid_cases()->Vec<(&'static str,Vec<QuantumOp>,usize,Vec<u64>,Vec<bool>)>{
    use QuantumOp as G;
    let mut cases:Vec<(&'static str,Vec<QuantumOp>,usize,Vec<u64>,Vec<bool>)>=Vec::new();
    for (name,src) in [
        ("qft4",include_str!("../../../benchmarks/Feynman/qft_4.qasm")),
        ("mod5",include_str!("../../../benchmarks/Feynman/mod5_4.qasm")),
        ("hwb6",include_str!("../../../benchmarks/Feynman/hwb6.qasm")),
        ("barenco5",include_str!("../../../benchmarks/Feynman/barenco_tof_5.qasm")),
    ]{
        let (ops,n)=feynman_source_ops(src);
        let (native,width)=parse_qasm_str(src).unwrap();
        assert_eq!((native,width),(ops.clone(),n));
        let mask=1u64<<(n-1);
        let expected=(0..4u64).map(|x|gate_reference_width(&ops,x,n).iter().enumerate()
            .any(|(z,r)|z as u64&mask!=0&&r.iter().any(|&v|v!=0))).collect();
        cases.push((name,ops,n,(0..4).collect(),expected));
    }
    // Real unitary controls. Wide output sector with no hidden variables
    // is intentionally rejected by the boundary coverage-width guard.
    cases.push(("wide14-zero",vec![G::H(0),G::H(1)],14,vec![0,1],vec![false,false]));
    cases.push(("wide14-positive",vec![G::H(0),G::X(13)],14,vec![0,1],vec![true,true]));
    // q12 controls fanout of H(q0) into q1..q11. For x=0 the
    // selected forbidden sector is zero. For x=4096 the retained
    // twelve outputs depend on the same hidden bit (bucket width13).
    let mut fan=vec![G::H(0)];
    for q in 1..12{fan.push(G::CCX(12,0,q));}
    cases.push(("mixed13",fan,13,vec![0,4096],vec![false,true]));

    cases
}
fn online_gpmc_sector(ps:&PathSum,x:u64,mask:u64,key:&str,dir:&std::path::Path,
    solver:&std::path::Path,helper:&std::path::Path,deadline:std::time::Instant)
    ->Result<String,&'static str>{
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let n=ps.v.num_qubits;
    let pre:Vec<Anf>=(0..n).map(|i|if x>>i&1==1{Anf::from([1u64<<i])}
        else{Anf::from([0,1u64<<i])}).collect();
    let post=vec![Anf::from([0,mask])];
    let Some((c,sign,_))=native_dyadic_projection_variant(ps,&pre,&post,32768,262144,true)
        else{return Err("ENCODING_LIMIT");};
    let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
    for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
    let cnf=dir.join(format!("{key}.cnf"));
    std::fs::write(&cnf,text).unwrap();
    let remaining=deadline.saturating_duration_since(std::time::Instant::now());
    if remaining.is_zero(){return Err("DEADLINE");}
    // Python profiles and terminates its GPMC subprocess. The parent
    // checks the same absolute budget after completion; cleanup is
    // cooperative and may overrun it, never credited as on-time.
    let output=std::process::Command::new("python3").arg(helper).arg("--online-sector")
        .arg(solver).arg(&cnf).arg(sign.to_string()).arg((n+2*h(ps)).to_string())
        .arg(format!("{:.9}",remaining.as_secs_f64())).output().expect("online GPMC helper launch");
    assert!(output.status.success(),"online GPMC helper failure {}",String::from_utf8_lossy(&output.stderr));
    let stdout=String::from_utf8(output.stdout).unwrap();
    let rows:Vec<_>=stdout.lines().filter(|l|l.starts_with("ONLINE_GPMC_RESULT ")).collect();
    assert_eq!(rows.len(),1,"{stdout}");
    println!("HOARE_ONLINE_GPMC key={key} {}",stdout.trim().replace('\n'," "));
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let result=rows[0].strip_prefix("ONLINE_GPMC_RESULT ").unwrap();
    if let Some(v)=result.strip_prefix("EXACT "){
        assert!(!v.is_empty()&&v.bytes().all(|b|b.is_ascii_digit())&&(v=="0"||!v.starts_with('0')));
        Ok(v.to_owned())
    }else{
        match result{"TIMEOUT"=>Err("TIMEOUT"),"SIGNAL_KILL"=>Err("SIGNAL_KILL"),_=>panic!("invalid helper result {result}")}
    }
}

// Exact output-coordinate quotient on a fixed-input checkpoint.
// Group canonical Boolean ANFs modulo their constant coefficient.
// No distinct reachable full labels are merged: each representative
// is an original output coordinate, and every omitted bit is reconstructed.
struct OutputQuotient{
    keep:u64,fixed:u64,value:u64,rows:Vec<(Option<usize>,bool)>,impossible:bool,
}
fn output_quotient(ps:&PathSum,mask:u64,z:u64)->Result<OutputQuotient,&'static str>{
    let n=ps.v.num_qubits;
    if n==0||n>16||!admitted(ps)||mask>>n!=0||z&!mask!=0{return Err("UNSUPPORTED");}
    // Check ALL coordinates and phase terms, even omitted ones.
    if ps.f.functions.iter().flatten().chain(ps.p.terms.keys()).flatten().any(|&v|(v as usize)<n){
        return Err("UNFIXED_INPUT");
    }
    let mut q=OutputQuotient{keep:0,fixed:0,value:0,rows:Vec::new(),impossible:false};
    let mut groups=BTreeMap::<Vec<Vec<u32>>,(usize,bool)>::new();
    for (i,p) in ps.f.functions.iter().enumerate(){
        let c=p.contains(&vec![]);
        let mut key:Vec<_>=p.iter().filter(|m|!m.is_empty()).cloned().collect();
        key.sort_unstable();
        let assigned=mask>>i&1!=0;let target=z>>i&1!=0;
        if key.is_empty(){
            q.rows.push((None,c));
            if assigned&&target!=c{q.impossible=true;}
        }else{
            let (r,rc)=*groups.entry(key).or_insert((i,c));
            q.keep|=1u64<<r;
            let flip=c^rc;
            q.rows.push((Some(r),flip));
            if assigned{
                let bit=1u64<<r;let want=target^flip;
                if q.fixed&bit!=0&&(q.value&bit!=0)!=want{q.impossible=true;}
                q.fixed|=bit;
                if want{q.value|=bit;}else{q.value&=!bit;}
            }
        }
    }
    Ok(q)
}
fn quotient_label(q:&OutputQuotient,assignment:u64)->u64{
    q.rows.iter().enumerate().fold(0u64,|z,(i,(r,flip))|{
        let bit=r.is_some_and(|r|assignment>>r&1!=0)^*flip;
        z|(u64::from(bit)<<i)
    })
}
struct QuotientReceipt{values:BTreeMap<u64,Z64>,free:usize,width:usize,work:usize,impossible:bool}
fn quotient_sector(ps:&PathSum,mask:u64,z:u64,deadline:std::time::Instant)
    ->Result<QuotientReceipt,&'static str>{
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let degree=minimum_cyclo_degree(ps)?;
    let q=output_quotient(ps,mask,z)?;
    let free=q.keep&!q.fixed;
    if q.impossible{return Ok(QuotientReceipt{values:BTreeMap::new(),free:free.count_ones() as usize,width:0,work:0,impossible:true});}
    let p=prepare_cyclo_selected(ps,q.keep,q.fixed,degree,deadline)?;
    let (v,width,work)=execute_minimum_boundary(&p,q.value,deadline)?;
    assert_eq!(v.len(),1usize<<free.count_ones());
    let mut values=BTreeMap::new();
    for (i,a) in v.into_iter().enumerate(){
        let label=quotient_label(&q,q.value|deposit8(i,free));
        assert_eq!(label&mask,z);
        assert!(values.insert(label,a).is_none(),"quotient reconstruction not injective");
    }
    Ok(QuotientReceipt{values,free:free.count_ones() as usize,width,work,impossible:false})
}
#[test]
fn native_output_quotient_parity(){
    use quprs::{Rational,PhaseCoeff};
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(30);
    let mut seed=20261126u64;let mut checks=0usize;let mut queries=0;
    let mut contradictions=0;let mut compressed=0;
    for trial in 0..128{
        let mut ps=PathSum::new(3);ps.set_auto_reduce(false);
        let ids:Vec<_>=(0..3).map(|_|ps.v.get_fresh_var()).collect();
        // Include constants, complements, identical coordinates, and
        // nonlinear output ANFs with sparse phase coefficients.
        let p=Poly::from_iter([vec![ids[0]],vec![ids[1],ids[2]]]);
        let mut complement=p.clone();toggle(&mut complement,vec![]);
        ps.f.functions=match trial%4{
            0=>vec![p.clone(),p.clone(),complement.clone()],
            1=>vec![Poly::default(),Poly::from_iter([vec![]]),p.clone()],
            2=>vec![p.clone(),complement.clone(),Poly::from_iter([vec![ids[2]]])],
            _=>vec![p.clone(),Poly::from_iter([vec![ids[0]]]),Poly::from_iter([vec![ids[1]]])],
        };
        let d=[2,4,8,16,32,64][trial%6];
        for &y in &ids{
            seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new((1+(seed>>32)%7) as _,d)));
        }
        ps.p.add_term(vec![ids[0],ids[2]],PhaseCoeff::new_constant(Rational::new(1,d)));
        let fixed=fixed_input(ps,0);
        for mask in 0..8u64{for z in 0..8u64{
            if z&!mask!=0{continue;}
            let ordinary=early_sector_minimum(&fixed,mask,z,deadline).unwrap();
            let q=quotient_sector(&fixed,mask,z,deadline).unwrap();
            contradictions+=usize::from(q.impossible);
            compressed+=usize::from(q.free<(7&!mask).count_ones() as usize);
            for (i,a) in ordinary.iter().enumerate(){
                let label=z|deposit8(i,7&!mask);
                assert_eq!(*a,q.values.get(&label).copied().unwrap_or([0;32]));checks+=1;
            }
            queries+=1;
        }}
    }
    assert_eq!((queries,checks),(3456,8192));
    assert!(contradictions>0&&compressed>0);
    let ps=PathSum::new(2);
    assert!(matches!(output_quotient(&ps,0,0),Err("UNFIXED_INPUT")));
    println!("HOARE_NATIVE_OUTPUT_QUOTIENT queries={queries} vectors={checks} contradictions={contradictions} compressed={compressed} exact=true");
}


// Row-space basis chosen with fixed output rows first. This ensures
// every fixed constraint is either an original basis coordinate or
// a dependent equation involving only fixed basis coordinates.
// Nonconstant ANF monomials are independent formal GF(2) coordinates.
#[derive(Clone)]
struct AffineOutputBasis{keep:u64,fixed:u64,value:u64,rows:Vec<(u64,bool)>,impossible:bool}

// Independent certificate replay: transpose the original ANF coefficient
// matrix into monomial -> output incidence masks, rather than rerunning
// elimination or using its reconstruction/toggle routine. Checks the
// premises of AffineOutputQuotient.lean, not basis minimality.
// Research-only transpose of the original output ANF coefficient sets.
// Keep the existing OR accumulation and deadline policy, but expose the
// builder for independent membership and evaluation comparisons.
fn build_affine_incidence(functions:&[Poly],deadline:std::time::Instant)
    ->Result<(u64,BTreeMap<Vec<u32>,u64>),&'static str>{
    if functions.len()>16{return Err("UNSUPPORTED");}
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let mut incidence=BTreeMap::<Vec<u32>,u64>::new();
    let mut constants=0u64;
    for (i,poly) in functions.iter().enumerate(){
        for m in poly{
            if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
            if m.is_empty(){constants|=1u64<<i;}
            else{*incidence.entry(m.clone()).or_default()|=1u64<<i;}
        }
    }
    Ok((constants,incidence))
}

fn check_affine_output_certificate(ps:&PathSum,mask:u64,z:u64,q:&AffineOutputBasis,
    deadline:std::time::Instant)->Result<(),&'static str>{
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let n=ps.v.num_qubits;
    if n==0||n>16||!admitted(ps)||mask>>n!=0||z&!mask!=0{return Err("UNSUPPORTED");}
    if ps.f.functions.iter().flatten().chain(ps.p.terms.keys()).flatten().any(|&v|(v as usize)<n){
        return Err("UNFIXED_INPUT");
    }
    let domain=(1u64<<n)-1;
    if q.rows.len()!=n||q.keep&!domain!=0||q.fixed!=q.keep&mask||q.value!=z&q.fixed{
        return Err("CERTIFICATE_SHAPE");
    }
    let mut contradiction=false;
    for (i,&(rel,offset)) in q.rows.iter().enumerate(){
        let bit=1u64<<i;
        if rel&!q.keep!=0{return Err("CERTIFICATE_SUPPORT");}
        if q.keep&bit!=0&&(rel,offset)!=(bit,false){return Err("CERTIFICATE_REPRESENTATIVE");}
        if mask&bit!=0{
            if rel&!q.fixed!=0{return Err("CERTIFICATE_FIXED_SUPPORT");}
            let actual=((rel&q.value).count_ones()%2!=0)^offset;
            contradiction|=actual!=(z&bit!=0);
        }
    }
    if contradiction!=q.impossible{return Err("CERTIFICATE_CONTRADICTION");}
    let (constants,incidence)=build_affine_incidence(&ps.f.functions,deadline)?;
    for (i,&(rel,offset)) in q.rows.iter().enumerate(){
        let expected=(constants>>i&1)!=0;
        if (((rel&constants).count_ones()%2!=0)^offset)!=expected{
            return Err("CERTIFICATE_ROW_IDENTITY");
        }
        for &column in incidence.values(){
            if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
            if ((column&rel).count_ones()%2!=0)!=((column>>i&1)!=0){
                return Err("CERTIFICATE_ROW_IDENTITY");
            }
        }
    }
    Ok(())
}

fn affine_output_basis(ps:&PathSum,mask:u64,z:u64,deadline:std::time::Instant)
    ->Result<AffineOutputBasis,&'static str>{
    let n=ps.v.num_qubits;
    if n==0||n>16||!admitted(ps)||mask>>n!=0||z&!mask!=0{return Err("UNSUPPORTED");}
    if ps.f.functions.iter().flatten().chain(ps.p.terms.keys()).flatten().any(|&v|(v as usize)<n){
        return Err("UNFIXED_INPUT");
    }
    let mut q=AffineOutputBasis{keep:0,fixed:0,value:0,rows:vec![(0,false);n],impossible:false};
    let mut pivots=BTreeMap::<Vec<u32>,(std::collections::BTreeSet<Vec<u32>>,u64)>::new();
    let mut constants=0u64;
    for i in 0..n{if ps.f.functions[i].contains(&vec![]){constants|=1u64<<i;}}
    for i in (0..n).filter(|&i|mask>>i&1!=0).chain((0..n).filter(|&i|mask>>i&1==0)){
        if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let mut row:std::collections::BTreeSet<_>=ps.f.functions[i].iter().filter(|m|!m.is_empty()).cloned().collect();
        let mut relation=0u64;
        while let Some(p)=row.last().cloned(){
            if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
            if let Some((other,coeff))=pivots.get(&p){
                for m in other{if !row.insert(m.clone()){row.remove(m);}}
                relation^=*coeff;
            }else{
                let bit=1u64<<i;
                pivots.insert(p,(row,relation^bit));
                q.keep|=bit;relation=bit;
                if mask&bit!=0{q.fixed|=bit;q.value|=z&bit;}
                break;
            }
        }
        let offset=((constants>>i&1)^(u64::from((constants&relation).count_ones()%2!=0)))!=0;
        q.rows[i]=(relation,offset);
        if mask>>i&1!=0{
            if relation&!q.fixed!=0{return Err("CERTIFICATE_FIXED_SUPPORT");}
            let actual=((relation&q.value).count_ones()%2!=0)^offset;
            if actual!=(z>>i&1!=0){q.impossible=true;}
        }
    }
    check_affine_output_certificate(ps,mask,z,&q,deadline)?;
    Ok(q)
}
fn affine_label(q:&AffineOutputBasis,u:u64)->u64{
    q.rows.iter().enumerate().fold(0u64,|z,(i,(relation,offset))|{
        z|(u64::from(((relation&u).count_ones()%2!=0)^*offset)<<i)
    })
}
fn affine_quotient_sector(ps:&PathSum,mask:u64,z:u64,deadline:std::time::Instant)
    ->Result<QuotientReceipt,&'static str>{
    let degree=minimum_cyclo_degree(ps)?;
    let q=affine_output_basis(ps,mask,z,deadline)?;
    let free=q.keep&!q.fixed;
    if q.impossible{return Ok(QuotientReceipt{values:BTreeMap::new(),free:free.count_ones() as usize,width:0,work:0,impossible:true});}
    let p=prepare_cyclo_selected(ps,q.keep,q.fixed,degree,deadline)?;
    let (v,width,work)=execute_minimum_boundary(&p,q.value,deadline)?;
    assert_eq!(v.len(),1usize<<free.count_ones());
    let mut values=BTreeMap::new();
    for (i,a) in v.into_iter().enumerate(){
        let label=affine_label(&q,q.value|deposit8(i,free));
        assert_eq!(label&mask,z);
        assert!(values.insert(label,a).is_none());
    }
    Ok(QuotientReceipt{values,free:free.count_ones() as usize,width,work,impossible:false})
}
#[test]
fn native_affine_output_quotient_parity(){
    use quprs::{Rational,PhaseCoeff};
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(30);
    let mut checks=0;let mut queries=0;let mut strict=0;let mut contradictions=0;
    for trial in 0..96{
        let mut ps=PathSum::new(4);ps.set_auto_reduce(false);
        let ids:Vec<_>=(0..3).map(|_|ps.v.get_fresh_var()).collect();
        let a=Poly::from_iter([vec![ids[0]],vec![ids[1],ids[2]]]);
        let b=Poly::from_iter([vec![ids[1]],vec![ids[0],ids[2]]]);
        let mut c=a.clone();for m in &b{toggle(&mut c,m.clone());}
        let mut d=c.clone();toggle(&mut d,vec![]);
        ps.f.functions=match trial%3{
            0=>vec![a,b,c,d],
            1=>vec![c,a,b,Poly::default()],
            _=>vec![d,b,a,c],
        };
        let order=[2,4,8,16,32,64][trial%6];
        for (i,&y) in ids.iter().enumerate(){
            ps.p.add_term(vec![y],PhaseCoeff::new_constant(Rational::new((i+1) as _,order)));
        }
        let fixed=fixed_input(ps,0);
        for mask in 0..16u64{for z in 0..16u64{
            if z&!mask!=0{continue;}
            let ordinary=early_sector_minimum(&fixed,mask,z,deadline).unwrap();
            let simple=quotient_sector(&fixed,mask,z,deadline).unwrap();
            let q=affine_quotient_sector(&fixed,mask,z,deadline).unwrap();
            strict+=usize::from(q.free<simple.free);contradictions+=usize::from(q.impossible);
            for (i,a) in ordinary.iter().enumerate(){
                let label=z|deposit8(i,15&!mask);
                assert_eq!(*a,q.values.get(&label).copied().unwrap_or([0;32]));
                assert_eq!(*a,simple.values.get(&label).copied().unwrap_or([0;32]));checks+=1;
            }
            queries+=1;
        }}
    }
    assert_eq!((queries,checks),(7776,24576));assert!(strict>0&&contradictions>0);
    assert!(matches!(affine_output_basis(&PathSum::new(2),0,0,deadline),Err("UNFIXED_INPUT")));
    println!("HOARE_NATIVE_AFFINE_QUOTIENT queries={queries} vectors={checks} strict={strict} contradictions={contradictions} exact=true");
}


#[test]
fn native_affine_incidence_reference(){
    // All 16 assignments of four sparse variables; original row membership
    // and direct evaluation are independent of the transposed map.
    let ids=[17u32,131,4097,65537];
    let keys:Vec<Vec<u32>>=(0..16u32).map(|m|
        (0..4).filter(|&j|m>>j&1!=0).map(|j|ids[j]).collect()).collect();
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(10);
    let mut checks=0;
    for seed in 0..256u32{
        let mut rows=vec![Poly::default();16];
        for (i,row) in rows.iter_mut().enumerate(){
            for (j,m) in keys.iter().enumerate(){
                let v=seed.wrapping_mul(0x9e3779b9)
                    ^ (i as u32).wrapping_mul(0x85ebca6b)
                    ^ (j as u32).wrapping_mul(0xc2b2ae35);
                let present=match seed{
                    0=>false,
                    1=>i==j,
                    2=>j==0 && i%2==0,
                    _=>v.rotate_left(((i+j)%32) as u32)&1!=0,
                };
                if present{row.insert(m.clone());}
            }
        }
        let (constants,columns)=build_affine_incidence(&rows,deadline).unwrap();
        assert!(!columns.contains_key(&Vec::new()));
        if seed==1{
            assert_eq!(constants,1);
            assert_eq!(columns.len(),15);
            for j in 1..16{assert_eq!(columns.get(&keys[j]),Some(&(1u64<<j)));}
            for i in 0..16{assert_eq!(rows[i].len(),1);assert!(rows[i].contains(&keys[i]));}
        }
        if seed==2{assert_eq!(constants,0x5555);assert!(columns.is_empty());}
        for (j,m) in keys.iter().enumerate(){
            let expected=rows.iter().enumerate().fold(0u64,|w,(i,row)|
                w|(u64::from(row.contains(m))<<i));
            let got=if j==0{constants}else{columns.get(m).copied().unwrap_or(0)};
            assert_eq!(got,expected);
        }
        assert_eq!(columns.len(),keys.iter().skip(1).filter(|m|rows.iter().any(|r|r.contains(*m))).count());
        for a in 0..16u32{
            let active=|m:&Vec<u32>|m.iter().all(|v|{
                let j=ids.iter().position(|x|x==v).unwrap();
                a>>j&1!=0
            });
            let transposed=columns.iter().filter(|(m,_)|active(m)).fold(constants,|w,(_,c)|w^*c);
            for (i,row) in rows.iter().enumerate(){
                let expected=row.iter().filter(|m|active(m)).count()%2!=0;
                assert_eq!(transposed>>i&1!=0,expected);
                checks+=1;
            }
        }
    }
    assert_eq!(checks,65536);
    let empty=build_affine_incidence(&[],deadline).unwrap();
    assert_eq!(empty,(0,BTreeMap::new()));
    assert_eq!(build_affine_incidence(&[],std::time::Instant::now()),Err("DEADLINE"));
    println!("HOARE_NATIVE_AFFINE_INCIDENCE cases=256 checks=65536 sparse_ids=true constants=true empty=true deadline=true row_diversity=true one_hot=true");
}

#[test]
fn native_affine_word_parity_reference(){
    // Independent LSB iteration, including the maximum admitted width.
    // This is a finite intrinsic differential test, not a Rust proof.
    let mut checks=0usize;
    for a in 0..(1u64<<16){
        for r in [0xffffu64,0xaaaa,0x5555,a.rotate_left(7)&0xffff]{
            let mut expected=false;
            let mut support=true;
            for j in 0..16{
                let aj=(a>>j)&1!=0;
                let rj=(r>>j)&1!=0;
                expected^=aj&&rj;
                if rj&&!aj{support=false;}
            }
            assert_eq!((a&r).count_ones()%2!=0,expected);
            assert_eq!(r&!a==0,support);
            checks+=1;
        }
    }
    assert_eq!(checks,262144);
    assert_eq!((1u64<<63).count_ones(),1);
    assert_eq!(((1u64<<63)|1).count_ones()%2,0);
    assert_ne!((1u64<<63)&!0xffff,0);
    println!("HOARE_NATIVE_AFFINE_WORD_PARITY checks=262144 width=16 storage=64 high_bits=true");
}

#[test]
fn native_affine_certificate_replay(){
    let mut ps=PathSum::new(4);ps.set_auto_reduce(false);
    let x=ps.v.get_fresh_var();let y=ps.v.get_fresh_var();
    ps.f.functions=vec![
        Poly::from_iter([vec![x]]),
        Poly::from_iter([vec![y]]),
        Poly::from_iter([vec![x],vec![y]]),
        Poly::from_iter([vec![],vec![x],vec![y]])];
    let p=fixed_input(ps,0);
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(5);
    let mask=12u64;let z=4u64;
    // Hand-authored certificate, independent of the Gaussian producer.
    let q=AffineOutputBasis{keep:5,fixed:4,value:4,
        rows:vec![(1,false),(5,false),(4,false),(4,true)],impossible:false};
    check_affine_output_certificate(&p,mask,z,&q,deadline).unwrap();
    let generated=affine_output_basis(&p,mask,z,deadline).unwrap();
    check_affine_output_certificate(&p,mask,z,&generated,deadline).unwrap();
    let mut negative=0;
    macro_rules! reject{
        ($edit:expr,$err:literal)=>{{
            let mut bad=q.clone();($edit)(&mut bad);
            assert_eq!(check_affine_output_certificate(&p,mask,z,&bad,deadline),Err($err));
            negative+=1;
        }};
    }
    reject!(|b:&mut AffineOutputBasis|{b.rows.pop();},"CERTIFICATE_SHAPE");
    reject!(|b:&mut AffineOutputBasis|{b.keep|=16;},"CERTIFICATE_SHAPE");
    reject!(|b:&mut AffineOutputBasis|{b.fixed=0;},"CERTIFICATE_SHAPE");
    reject!(|b:&mut AffineOutputBasis|{b.value=0;},"CERTIFICATE_SHAPE");
    reject!(|b:&mut AffineOutputBasis|{b.rows[1].0|=2;},"CERTIFICATE_SUPPORT");
    reject!(|b:&mut AffineOutputBasis|{b.rows[0].1=true;},"CERTIFICATE_REPRESENTATIVE");
    reject!(|b:&mut AffineOutputBasis|{b.rows[3].0|=1;},"CERTIFICATE_FIXED_SUPPORT");
    reject!(|b:&mut AffineOutputBasis|{b.rows[1].1=true;},"CERTIFICATE_ROW_IDENTITY");
    reject!(|b:&mut AffineOutputBasis|{b.rows[1].0=1;},"CERTIFICATE_ROW_IDENTITY");
    reject!(|b:&mut AffineOutputBasis|{b.impossible=true;},"CERTIFICATE_CONTRADICTION");
    assert_eq!(check_affine_output_certificate(&p,mask,1,&q,deadline),Err("UNSUPPORTED"));
    assert_eq!(check_affine_output_certificate(&p,mask,z,&q,std::time::Instant::now()),Err("DEADLINE"));
    assert_eq!(check_affine_output_certificate(&PathSum::new(4),mask,z,&q,deadline),Err("UNFIXED_INPUT"));
    let mut inconsistent=q.clone();inconsistent.impossible=true;
    check_affine_output_certificate(&p,mask,12,&inconsistent,deadline).unwrap();
    // Rank zero: all outputs constants, including an impossible target.
    let mut constant=p.clone();constant.f.functions=vec![Poly::default();4];
    let zero=affine_output_basis(&constant,15,0,deadline).unwrap();
    assert_eq!(zero.keep,0);assert!(!zero.impossible);
    let impossible=affine_output_basis(&constant,15,1,deadline).unwrap();
    assert_eq!(impossible.keep,0);assert!(impossible.impossible);
    assert_eq!(negative,10);
    println!("HOARE_NATIVE_AFFINE_CERTIFICATE_REPLAY mutations=10 bad_query=true deadline=true unfixed=true rank_zero=true");
}

#[test]
fn native_affine_unitary_control(){
    use QuantumOp as G;
    // All 15 nonzero linear combinations of four independent path bits
    // appear as distinct output functions, no equal/complement reduction.
    let mut ps=PathSum::new(15);ps.set_auto_reduce(false);
    for q in 0..4{G::H(q).apply(&mut ps,false);}
    let mut target=4;
    for m in 1u32..16{
        if m.count_ones()==1{continue;}
        for i in 0..4{if m>>i&1!=0{G::CX(i,target).apply(&mut ps,false);}}
        target+=1;
    }
    assert_eq!(target,15);
    let p=fixed_input(ps,0);let deadline=std::time::Instant::now()+std::time::Duration::from_secs(5);
    let mask=1u64<<14;
    assert!(matches!(quotient_sector(&p,mask,mask,deadline),Err("WIDTH_LIMIT")));
    let a=affine_quotient_sector(&p,mask,mask,deadline).unwrap();
    assert_eq!(a.free,3);assert_eq!(a.values.len(),8);
    let mut expected=BTreeMap::new();
    for x in 0..16u64{
        if x.count_ones()%2==0{continue;}
        let mut z=x;let mut i=4;
        for m in 1u64..16{if m.count_ones()==1{continue;}z|=u64::from((x&m).count_ones()%2!=0)<<i;i+=1;}
        let mut v=[0;32];v[0]=1;expected.insert(z,v);
    }
    assert_eq!(a.values,expected);
    println!("HOARE_NATIVE_AFFINE_UNITARY rank=4 free=3 exact=8 simple_width_rejected=true width={} work={}",a.width,a.work);
}

#[test]
fn native_online_hybrid_sector(){
    let Some(solver)=std::env::var_os("HOARE_ONLINE_GPMC") else{return;};
    let solver=std::path::PathBuf::from(solver);
    let helper=std::path::PathBuf::from(std::env::var_os("HOARE_ONLINE_HELPER").unwrap());
    let dir=std::path::PathBuf::from(std::env::var_os("HOARE_ONLINE_DIR").unwrap());
    std::fs::create_dir_all(&dir).unwrap();
    let mut cases=0;let mut arms=0;
    for (name,ops,n,inputs,expected) in online_hybrid_cases(){
        let mask=1u64<<(n-1);
        // QFT WMC-only timeout cohort is already frozen; do not rerun
        // it in this small integration pilot.
        let routes:&[&str]=if name=="qft4"{&["factor-gpmc","tiling-gpmc","quotient-gpmc","affine-gpmc"]}
            else{&["factor-gpmc","tiling-gpmc","wmc-only","quotient-gpmc","affine-gpmc"]};
        for &route in routes{
            let start=std::time::Instant::now();
            let deadline=start+std::time::Duration::from_secs(30);
            let mut raw=PathSum::new(n);raw.set_auto_reduce(false);
            for op in &ops{op.apply(&mut raw,false);}
            let (general,gr,_,_,expired,_)=reduce_indexed(raw,deadline,true);
            assert!(!expired&&!gr.limit);
            let common=start.elapsed().as_nanos();
            let mut coverage=BTreeMap::<u64,String>::new();
            let mut factor=0;let mut tiles=0;let mut quotient=0;let mut qwidth=0;let mut qfree=0;let mut qwork=0;let mut qlabels=0;let mut qempty=0;let mut wmc=0;let mut wmc_attempts=0;
            let mut visited=0;let mut first=None;let mut failures=BTreeMap::<&str,usize>::new();
            let mut rejects=BTreeMap::<&str,usize>::new();
            for (ord,&x) in inputs.iter().enumerate(){
                if std::time::Instant::now()>=deadline{break;}
                visited+=1;
                let (p,r,_,_,expired,_)=reduce_indexed(fixed_input(general.clone(),x),deadline,true);
                if expired||r.limit{*failures.entry(if expired{"DEADLINE"}else{"RR_LIMIT"}).or_default()+=1;continue;}
                let mut result=None;
                if route=="quotient-gpmc"||route=="affine-gpmc"{
                    let qr=if route=="affine-gpmc"{affine_quotient_sector(&p,mask,mask,deadline)}else{quotient_sector(&p,mask,mask,deadline)};
                    match qr{
                        Ok(q)=>{
                            let v=q.values.values().flatten().try_fold(0i128,|s,&v|s.checked_add(v.checked_mul(v)?));
                            if let Some(v)=v{
                                result=Some(v.to_string());quotient+=1;qwidth=qwidth.max(q.width);qfree=qfree.max(q.free);qwork+=q.work;qlabels+=q.values.len();qempty+=usize::from(q.impossible);
                            }else{*rejects.entry("OVERFLOW").or_default()+=1;}
                        }
                        Err(e)=>{*rejects.entry(e).or_default()+=1;}
                    }
                }else if route!="wmc-only"{
                    match early_sector_minimum(&p,mask,mask,deadline){
                        Ok(a)=>{
                            assert_eq!(a.len(),mask as usize);
                            let v=a.iter().flatten().try_fold(0i128,|s,&v|s.checked_add(v.checked_mul(v)?));
                            if let Some(v)=v{result=Some(v.to_string());factor+=1;}
                            else{*rejects.entry("OVERFLOW").or_default()+=1;}
                        }
                        Err(e)=>{*rejects.entry(e).or_default()+=1;}
                    }
                }
                if result.is_none()&&route=="tiling-gpmc"&&std::time::Instant::now()<deadline{
                    // This pilot supports the already accepted D8 tiler,
                    // not a new generic D64 tiler.
                    match tiled_boundary8(&p,mask,mask,deadline){
                        Ok(t) if t.values.iter().all(Option::is_some)=>{
                            let v=t.values.iter().flatten().flatten().try_fold(0i128,|s,&v|s.checked_add(v.checked_mul(v)?));
                            if let Some(v)=v{result=Some(v.to_string());tiles+=1;}
                            else{*rejects.entry("TILE_OVERFLOW").or_default()+=1;}
                        }
                        Ok(_)=>{*rejects.entry("PARTIAL_TILE").or_default()+=1;}
                        Err(e)=>{*rejects.entry(e).or_default()+=1;}
                    }
                }
                if result.is_none()&&std::time::Instant::now()<deadline{
                    wmc_attempts+=1;let key=format!("online-{name}-{route}-{ord}");
                    match online_gpmc_sector(&p,x,mask,&key,&dir,&solver,&helper,deadline){
                        Ok(v)=>{result=Some(v);wmc+=1;}
                        Err(e)=>{*failures.entry(e).or_default()+=1;}
                    }
                }
                if std::time::Instant::now()>=deadline{
                    *failures.entry("DEADLINE").or_default()+=1;break;
                }
                if let Some(v)=result{
                    // Controls have known exact unnormalized residual
                    // coefficient-square sum (no RR normalization change).
                    if name.starts_with("wide14")||name=="mixed13"{
                        assert_eq!(gr.scale2+r.scale2,0);
                        assert_eq!(v,if name=="wide14-positive"||(name=="mixed13"&&x==4096){"2"}else{"0"});
                    }
                    let positive=v!="0";assert!(coverage.insert(x,v).is_none());
                    if positive{first=Some(x);break;}
                }
            }
            let verdict=if first.is_some(){"REFUTED"}else if coverage.len()==inputs.len(){"PROVED"}else{"UNKNOWN"};
            // Reference consulted only after actual stop.
            for (&x,v) in &coverage{let i=inputs.iter().position(|&z|z==x).unwrap();assert_eq!(v!="0",expected[i]);}
            let want=if expected.iter().any(|&v|v){"REFUTED"}else{"PROVED"};
            assert_eq!(verdict,want,"{name} {route}");
            assert_eq!(factor+tiles+quotient+wmc,coverage.len());
            if route=="factor-gpmc"&&name=="mixed13"{assert_eq!((factor,tiles,wmc),(1,0,1));}
            if route=="tiling-gpmc"&&name=="mixed13"{assert_eq!((factor,tiles,wmc),(1,1,0));}
            if name=="wide14-zero"&&route!="quotient-gpmc"&&route!="affine-gpmc"{assert_eq!((factor,tiles,wmc),(0,0,2));}
            if name=="wide14-positive"&&route!="quotient-gpmc"&&route!="affine-gpmc"{assert_eq!((factor,tiles,wmc),(0,0,1));assert_eq!(visited,1);}
            if (route=="quotient-gpmc"||route=="affine-gpmc")&&["wide14-zero","wide14-positive","mixed13"].contains(&name){assert_eq!(quotient,coverage.len());assert_eq!(wmc,0);}
            println!("HOARE_ONLINE_HYBRID name={name} route={route} verdict={verdict} exact={} planned={} visited={visited} factor={factor} tiles={tiles} wmc={wmc} wmc_attempts={wmc_attempts} quotient={quotient} qwidth={qwidth} qfree={qfree} qwork={qwork} qlabels={qlabels} qempty={qempty} common_ns={common} elapsed_ns={} first={first:?} rejects={rejects:?} failures={failures:?}",coverage.len(),inputs.len(),start.elapsed().as_nanos());
            arms+=1;
        }
        cases+=1;
    }
    assert_eq!((cases,arms),(7,34));
    println!("HOARE_ONLINE_HYBRID_COHORT cases={cases} arms={arms} duplicate=0");
}

#[test]
fn paper_qwalk_native_source_admission(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{
        println!("HOARE_PAPER_QWALK NOT_RUN no pinned fixture directory");return;
    };
    let export=std::env::var_os("HOARE_PAPER_PROJECTED_DIR").map(std::path::PathBuf::from);
    let mut rows=String::new();
    let mut single_rows=String::new();
    let mut sector_rows=String::new();
    for (name,gates,rx,expected_bad) in [("vchain",417,51,false),("noancilla",1305,183,true)]{
        let src=std::fs::read_to_string(std::path::Path::new(&dir).join(format!("{name}.qasm"))).unwrap();
        let (ops,n,rxc)=source_ops(&src);
        assert_eq!((ops.len(),n,rxc),(gates,5,rx));
        // Existing strict admission intentionally rejects multi-register
        // inputs, and the larger file also exceeds its gate budget.
        let strict=parse_qasm_str_source_pinned(&src);
        assert!(strict.is_err());
        let (native,width)=parse_qasm_str(&src).expect("native compatibility parse");
        assert_eq!(width,n);assert_eq!(native,ops);
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        let t=std::time::Instant::now();let mut built=0;
        for op in &native{
            op.apply(&mut ps,false);built+=1;
            if !admitted(&ps){break;}
        }
        let build_ns=t.elapsed().as_nanos();
        if built!=gates||!admitted(&ps){
            println!("HOARE_PAPER_QWALK name={name} status=BUILD_LIMIT built={built} terms={}",terms(&ps));continue;
        }
        let initial_h=h(&ps);assert_eq!(initial_h,rx*2);
        quotient_profile(&ps,name,false);
        if let Some(dir)=&export{export_projected(dir,name,"pure",&ps,initial_h,0,build_ns,0,expected_bad,&mut rows);}
        let max_id=ps.v.path_vars.iter().copied().max().unwrap();
        for specialize in [false,true]{
            let mut trial=ps.clone();
            if specialize{
                // Keep original input variable 4 in the domain; substitute
                // its precondition value into native phase and output only.
                let zero=FxHashSet::default();
                trial.f.substitute_var_with_poly(4,&zero);
                trial.p.substitute_var_with_poly(4,&zero);
            }
            let t=std::time::Instant::now();let (out,r)=reduce(trial);
            let rr_ns=t.elapsed().as_nanos();assert!(admitted(&out));
            quotient_profile(&out,name,specialize);
            assert_eq!(initial_h-h(&out),r.elim+2*r.hh+r.omega);
            if let Some(dir)=&export{
                export_projected(dir,name,if specialize{"hybrid-pre"}else{"hybrid"},&out,initial_h,r.scale2,build_ns,rr_ns,expected_bad,&mut rows);
                if specialize{export_projected(dir,name,"hybrid-pre-heap",&out,initial_h,r.scale2,build_ns,rr_ns,expected_bad,&mut rows);
                    export_single_fibres(dir,name,&out,r.scale2,build_ns,rr_ns,&mut single_rows);
                    // Keep old exporter callable, but freeze its prior measured baseline.
                    // Frozen source sector baseline; do not repeat the 64 queries.
                    let _ = &mut sector_rows; }
            }
            let mut bad=0usize;let mut checks=0usize;
            let status=if let Some(a)=entries(&out){
                for x in 0..16{for z in 16..32{
                    if a[x*32+z].iter().any(|&v|v!=0){bad+=1;}checks+=1;
                }}
                assert_eq!(bad>0,expected_bad);
                if bad==0{"PROJECTED_ZERO_REFERENCE"}else{"PROJECTED_NONZERO_REFERENCE"}
            }else if specialize&&out.f.functions[4].is_empty(){
                assert!(!expected_bad);"ALGEBRAIC_SUPPORT_ZERO"
            }else{"RESIDUAL_ORACLE_LIMIT"};
            println!("HOARE_PAPER_QWALK name={name} specialized={specialize} gates={gates} rx={rx} initial_h={initial_h} max_id={max_id} residual_h={} terms={} scale2={} elim={} hh={} omega={} rr_limit={} build_ns={build_ns} rr_ns={rr_ns} exact_entries={checks} nonzero_forbidden={bad} status={status} strict_source=BLOCKED compatibility_parse_equal=true",
                h(&out),terms(&out),r.scale2,r.elim,r.hh,r.omega,r.limit);
        }
    }
    if let Some(dir)=&export{std::fs::write(dir.join("paper-projected.tsv"),rows).unwrap();
        std::fs::write(dir.join("paper-single-fibre.tsv"),single_rows).unwrap();
        let _=sector_rows;}
}
