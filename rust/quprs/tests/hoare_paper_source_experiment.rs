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
const Z8_ONE:Z8=[1,0,0,0];
fn z8_add(a:Z8,b:Z8)->Option<Z8>{
    let mut c=[0i128;4];for i in 0..4{c[i]=a[i].checked_add(b[i])?;}Some(c)
}
fn z8_mul(a:Z8,b:Z8)->Option<Z8>{
    let mut c=[0i128;4];
    for i in 0..4{for j in 0..4{
        if a[i]==0||b[j]==0{continue;}
        let p=a[i].checked_mul(b[j])?;
        let k=i+j;
        c[k%4]=if k<4{c[k%4].checked_add(p)?}else{c[k%4].checked_sub(p)?};
    }}Some(c)
}
#[derive(Clone)]
struct Factor8{scope:u64,table:Vec<Z8>}
fn deposit8(mut i:usize,mut mask:u64)->u64{
    let mut a=0;while mask!=0{let b=mask&mask.wrapping_neg();mask^=b;if i&1!=0{a|=b;}i>>=1;}a
}
fn extract8(a:u64,mut mask:u64)->usize{
    let mut i=0;let mut bit=1;while mask!=0{let b=mask&mask.wrapping_neg();mask^=b;if a&b!=0{i|=bit;}bit<<=1;}i
}
fn factor8(scope:u64,mut f:impl FnMut(u64)->Z8)->Result<Factor8,&'static str>{
    if scope.count_ones()>12{return Err("WIDTH_LIMIT");}
    Ok(Factor8{scope,table:(0..1usize<<scope.count_ones()).map(|i|f(deposit8(i,scope))).collect()})
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
enum FactorSpec8{Phase(u64,usize),Output(u64,Vec<u64>,Option<u64>,bool)}
fn contract_boundary8(ps:&PathSum,fixed_mask:u64,z:u64,deadline:std::time::Instant)
    ->Result<(Vec<Z8>,usize,usize),&'static str>{
    let n=ps.v.num_qubits;let hidden=h(ps);
    if hidden>60||n>16||hidden+n>63||!admitted(ps)||fixed_mask>>n!=0||z&!fixed_mask!=0{return Err("UNSUPPORTED");}
    if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
    let free=(((1u64<<n)-1)&!fixed_mask)<<hidden;
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
        let den=c.constant.denom as i128;let num=8i128*c.constant.numer as i128;
        if den<=0||num%den!=0{return Err("UNSUPPORTED_PHASE");}
        let k=(num/den).rem_euclid(8) as usize;if k==0{continue;}
        let scope=mask(m)?;charge(scope,1)?;specs.push(FactorSpec8::Phase(scope,k));
    }
    for (i,p) in ps.f.functions.iter().enumerate(){
        let ms=p.iter().map(|m|mask(m)).collect::<Result<Vec<_>,_>>()?;
        let bit=if fixed_mask>>i&1==0{Some(1u64<<(hidden+i))}else{None};
        let scope=ms.iter().fold(bit.unwrap_or(0),|a,b|a|b);
        charge(scope,ms.len())?;specs.push(FactorSpec8::Output(scope,ms,bit,z>>i&1==1));
    }
    let (order,peak,work)=plan_factor8(scopes,hidden,free,initial_work)?;
    // The work cap also upper-bounds the total number of allocated
    // table entries across this call (including discarded tables).
    let mut fs=Vec::<Factor8>::new();
    for spec in specs{
        if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let f=match spec{
            FactorSpec8::Phase(scope,k)=>factor8(scope,|a|{
                if a&scope!=scope{return Z8_ONE;}
                let mut r=[0;4];r[k%4]=if k<4{1}else{-1};r
            })?,
            FactorSpec8::Output(scope,ms,bit,value)=>factor8(scope,|a|{
                let v=ms.iter().fold(false,|b,&m|b^(a&m==m));
                let want=bit.map_or(value,|b|a&b!=0);
                if v==want{Z8_ONE}else{[0;4]}
            })?,
        };fs.push(f);
    }
    for i in order{
        if std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let b=1u64<<i;
        let (bucket,rest):(Vec<_>,Vec<_>)=fs.into_iter().partition(|f|f.scope&b!=0);
        let scope=bucket.iter().fold(0u64,|a,f|a|f.scope)&!b;
        let count=1usize<<scope.count_ones();let mut table=Vec::with_capacity(count);
        for i in 0..count{
            if i%64==0&&std::time::Instant::now()>=deadline{return Err("DEADLINE");}
            let a=deposit8(i,scope);let mut sum=[0;4];
            for assignment in [a,a|b]{
                let mut v=Z8_ONE;
                for f in &bucket{
                    v=z8_mul(v,f.table[extract8(assignment,f.scope)]).ok_or("OVERFLOW")?;
                    if v==[0;4]{break;}
                }
                sum=z8_add(sum,v).ok_or("OVERFLOW")?;
            }
            table.push(sum);
        }
        fs=rest;fs.push(Factor8{scope,table});
    }
    let mut result=Vec::with_capacity(1usize<<free.count_ones());
    for i in 0..1usize<<free.count_ones(){
        if i%64==0&&std::time::Instant::now()>=deadline{return Err("DEADLINE");}
        let a=deposit8(i,free);let mut v=Z8_ONE;
        for f in &fs{
            assert_eq!(f.scope&!free,0);
            v=z8_mul(v,f.table[extract8(a,f.scope)]).ok_or("OVERFLOW")?;
            if v==[0;4]{break;}
        }
        result.push(v);
    }
    Ok((result,peak,work))
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
    }
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
