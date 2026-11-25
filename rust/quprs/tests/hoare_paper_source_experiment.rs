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
