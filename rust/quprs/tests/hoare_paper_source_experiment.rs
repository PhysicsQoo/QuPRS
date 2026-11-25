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
#[test]
fn paper_qwalk_native_source_admission(){
    let Some(dir)=std::env::var_os("HOARE_PAPER_QWALK_DIR") else{
        println!("HOARE_PAPER_QWALK NOT_RUN no pinned fixture directory");return;
    };
    let export=std::env::var_os("HOARE_PAPER_PROJECTED_DIR").map(std::path::PathBuf::from);
    let mut rows=String::new();
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
                if specialize{export_projected(dir,name,"hybrid-pre-heap",&out,initial_h,r.scale2,build_ns,rr_ns,expected_bad,&mut rows);}
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
    if let Some(dir)=&export{std::fs::write(dir.join("paper-projected.tsv"),rows).unwrap();}
}
