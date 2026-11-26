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
                    export_sector_inputs(dir,name,&out,r.scale2,build_ns,rr_ns,&mut sector_rows); }
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
        std::fs::write(dir.join("paper-sector-inputs.tsv"),sector_rows).unwrap();}
}
