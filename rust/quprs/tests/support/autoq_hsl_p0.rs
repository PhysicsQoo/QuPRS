
// AQ-R4: narrow source-derived normalized singleton adapter. Reuse native
// PathSum, guarded_native_step, compact, and the existing exact CNF encoder.
// No alternative RR, no dense target construction in the solver.
#[derive(Clone,Copy)]
enum AqPattern { Fixed(u64), Except { offset:usize, width:usize, excluded:u64, outside:u64 } }
#[derive(Clone)]
struct AqTerm { pattern:AqPattern, signed:i64 }
#[derive(Clone)]
struct AqState { n:usize, k:usize, terms:Vec<AqTerm> }
fn aq_bits(s:&str)->Option<u64>{
    if s.is_empty()||s.len()>16{return None;}
    s.bytes().enumerate().try_fold(0u64,|v,(i,b)|match b{
        b'0'=>Some(v),b'1'=>Some(v|(1<<i)),_=>None})
}
fn aq_match(p:&AqPattern,z:u64)->bool{
    match *p{
        AqPattern::Fixed(v)=>z==v,
        AqPattern::Except{offset,width,excluded,outside}=>{
            let mask=((1u64<<width)-1)<<offset;
            z&!mask==outside && ((z&mask)>>offset)!=excluded
        }
    }
}
fn aq_parse(hsl:&str)->Option<AqState>{
    // Deliberate exact subset: named real integers or integer/(sqrt2^k),
    // one fixed ket, optionally one disjoint restricted summation.
    let mut lines=hsl.lines().map(str::trim).filter(|s|!s.is_empty());
    if lines.next()? != "Constants"{return None;}
    let mut cs=BTreeMap::<String,(i64,usize)>::new();
    let expr=loop{
        let l=lines.next()?;
        if l=="Extended Dirac"{break lines.next()?;}
        let (key,val)=l.split_once(":=")?;
        let key=key.trim();let val=val.trim();
        if key.is_empty()||!key.bytes().all(|b|b.is_ascii_alphanumeric()) {return None;}
        let (v,k)=if let Some((a,b))=val.split_once('/'){
            let b=b.trim().strip_prefix("(sqrt2 ^ ")?.strip_suffix(')')?;
            (a.trim().parse::<i64>().ok()?,b.parse::<usize>().ok()?)
        }else{(val.parse::<i64>().ok()?,0)};
        if v==0||v.unsigned_abs()>65535||k>32||cs.insert(key.to_owned(),(v,k)).is_some(){return None;}
    };
    if lines.next().is_some(){return None;}
    let expr=expr.strip_prefix('{')?.strip_suffix('}')?;
    let mut parts=expr.split(" + ");
    let (c,ket)=parts.next()?.split_once(' ')?;
    let (v,k)=*cs.get(c)?;
    let b=ket.strip_prefix('|')?.strip_suffix('>')?;
    let n=b.len();let fixed=aq_bits(b)?;
    let mut terms=vec![AqTerm{pattern:AqPattern::Fixed(fixed),signed:v}];
    if let Some(part)=parts.next(){
        let (c,rest)=part.split_once(" ∑ ")?;
        let (v2,k2)=*cs.get(c)?;
        if k2!=k{return None;}
        let (binding,ket)=rest.split_once(" |")?;
        let (decl,except)=binding.split_once(", ")?;
        let d=decl.strip_prefix('|')?;
        let (var,wd)=d.split_once("|=")?;
        if var.len()!=1||!var.as_bytes()[0].is_ascii_lowercase(){return None;}
        let width=wd.parse::<usize>().ok()?;
        let (var2,excluded)=except.split_once('≠')?;
        if var!=var2||width==0||width>=n||excluded.len()!=width{return None;}
        let ket=ket.strip_suffix('>')?;
        let (prefix,suffix)=ket.split_once(var)?;
        let offset=prefix.len();
        if offset+suffix.len()+width!=n{return None;}
        let prefix=if prefix.is_empty(){0}else{aq_bits(prefix)?};
        let suffix=if suffix.is_empty(){0}else{aq_bits(suffix)?};
        let pattern=AqPattern::Except{offset,width,excluded:aq_bits(excluded)?,outside:prefix|(suffix<<(offset+width))};
        if aq_match(&pattern,fixed){return None;} // disjoint support admission
        terms.push(AqTerm{pattern,signed:v2});
    }
    if parts.next().is_some(){return None;}
    let norm=terms.iter().try_fold(0i128,|sum,t|{
        let count=match t.pattern{AqPattern::Fixed(_)=>1,AqPattern::Except{width,..}=>(1i128<<width)-1};
        sum.checked_add(count.checked_mul(i128::from(t.signed).pow(2))?)
    })?;
    if norm!=(1i128<<k){return None;} // normalized, nonzero singleton
    Some(AqState{n,k,terms})
}

// Bounded outer-domain instantiation; coherent paths remain symbolic.
// Substitute only ket tokens and the disequality RHS, never coefficients.
fn aq_family(hsl:&str)->Option<(usize,Vec<AqState>)>{
    let Some((prefix,domain))=hsl.trim_end().rsplit_once(" : ")else{
        return Some((0,vec![aq_parse(hsl)?]));
    };
    let (var,w)=domain.strip_suffix('}')?.strip_prefix('|')?.split_once("|=")?;
    let w=w.parse::<usize>().ok()?;
    if var.len()!=1||!var.as_bytes()[0].is_ascii_lowercase()||w==0||w>4{return None;}
    let (header,expr)=prefix.rsplit_once('\n')?;
    if !expr.starts_with('{'){return None;}
    let mut rows=Vec::new();
    for x in 0..1u64<<w{
        let bits:String=(0..w).map(|i|if x>>i&1==1{'1'}else{'0'}).collect();
        let mut tokens=Vec::new();
        for token in expr.split_whitespace(){
            if token.contains("|=")&&token.starts_with(&format!("|{var}|")){return None;}
            if token.ends_with('>')&&token.contains('|'){
                let (left,ket)=token.split_once('|')?;
                tokens.push(format!("{left}|{}",ket.replace(var,&bits)));
            }else if let Some((lhs,rhs))=token.split_once('≠'){
                if lhs==var{return None;}
                tokens.push(if rhs==var{format!("{lhs}≠{bits}")}else{token.to_owned()});
            }else{tokens.push(token.to_owned());}
        }
        rows.push(aq_parse(&format!("{header}\n{}}}",tokens.join(" ")))?);
    }
    Some((w,rows))
}
// Sound, conservative support abstraction: every nonzero basis component
// agrees with the returned partial assignment. No amplitudes are enumerated.
fn aq_support_cube(b:&AqState)->Cube{
    let all=(1u64<<b.n)-1;
    let mut mask=all;let mut value=0;let mut first=true;
    for term in &b.terms{
        let (m,v)=match term.pattern{
            AqPattern::Fixed(v)=>(all,v),
            AqPattern::Except{offset,width,excluded,outside}=>{
                if width==1 {(all,outside|((excluded^1)<<offset))}
                else {(all&!(((1u64<<width)-1)<<offset),outside)}
            }
        };
        if first{mask=m;value=v;first=false;}
        else{mask &= m & !(value^v);}
    }
    Cube{mask,value:value&mask}
}
fn aq_fixed_input(a:&AqState)->Option<u64>{
    match a.terms.as_slice(){
        [AqTerm{pattern:AqPattern::Fixed(v),..}]=>Some(*v),
        _=>None
    }
}
fn aq_output_cube(s:&Symbolic,x:u64)->Cube{
    let input=Cube{mask:(1u64<<s.n)-1,value:x};
    let (mut mask,mut value)=(0u64,0u64);
    for (i,p) in s.output.iter().enumerate(){
        let t=specialize_bool(p,input);
        if t.is_empty(){mask|=1<<i;}
        else if t.len()==1&&t.contains(&0){mask|=1<<i;value|=1<<i;}
    }
    Cube{mask,value}
}
// No assumed label position, same-index pairing, or phase/ray oracle.
// Exclude a candidate only by a contradictory fixed output coordinate.
// When the remaining target is unique, ordinary overlap proves/refutes it;
// ambiguous or empty candidate sets are NOT_ADMITTED here, not false.
fn aq_discover_pairs(s:&Symbolic,aa:&[AqState],bb:&[AqState])->Option<Vec<usize>>{
    if aa.is_empty()||bb.is_empty()||aa.iter().chain(bb).any(|a|a.n!=s.n){return None;}
    if bb.len()==1{return Some(vec![0;aa.len()]);}
    let targets:Vec<_>=bb.iter().map(aq_support_cube).collect();
    let mut pairs=Vec::with_capacity(aa.len());
    for a in aa{
        let p=aq_output_cube(s,aq_fixed_input(a)?);
        let mut compatible=targets.iter().enumerate().filter(|(_,q)|
            (p.value^q.value)&p.mask&q.mask==0).map(|(i,_)|i);
        let j=compatible.next()?;
        if compatible.next().is_some(){return None;}
        pairs.push(j);
    }
    Some(pairs)
}

fn aq_pattern_lit(c:&mut Cnf,p:&AqPattern,z:&[Lit])->Lit{
    let eq=|c:&mut Cnf,bits:&[Lit],v:u64|->Lit{
        bits.iter().enumerate().fold(ONE,|a,(i,&l)|c.and(a,if v>>i&1!=0{l}else{-l}))
    };
    match *p{
        AqPattern::Fixed(v)=>eq(c,z,v),
        AqPattern::Except{offset,width,excluded,outside}=>{
            let lo=eq(c,&z[..offset],outside);
            let hi=eq(c,&z[offset+width..],outside>>(offset+width));
            let a=c.and(lo,hi);
            let b=eq(c,&z[offset..offset+width],excluded);
            c.and(a,-b)
        }
    }
}
fn aq_lt(c:&mut Cnf,bits:&[Lit],bound:u64)->Lit{
    if bound>=1u64<<bits.len(){return ONE;}
    let mut equal=ONE;let mut less=ZERO;
    for (i,&b) in bits.iter().enumerate().rev(){
        if bound>>i&1!=0{
            let new=c.and(equal,-b);less=c.or(less,new);
            equal=c.and(equal,b);
        }else{equal=c.and(equal,-b);}
    }
    less
}
fn aq_overlap(s:&Symbolic,x:u64,b:&AqState)->Option<(Cnf,[Lit;3],usize)>{
    if s.n!=b.n||s.h>32||s.n+s.h>63||b.terms.is_empty()||b.terms.len()>2{return None;}
    let selectors=usize::from(b.terms.len()==2);
    let mag=b.terms.iter().map(|t|t.signed.unsigned_abs()).max()?;
    let counter=(64-(mag-1).leading_zeros()) as usize;
    let primary=s.h+selectors+counter;
    let mut c=Cnf::new(primary);
    let bits:Vec<_>=(0..s.n).map(|i|if x>>i&1!=0{ONE}else{ZERO})
        .chain((0..s.h).map(|i|(i+2) as Lit)).collect();
    let z:Vec<_>=s.output.iter().map(|p|c.anf(p,&bits)).collect();
    let mult:Vec<_>=(0..counter).map(|i|(s.h+selectors+i+2) as Lit).collect();
    let selector=(s.h+2) as Lit;
    let mut valid=ZERO;let mut negative=ZERO;
    for (i,t) in b.terms.iter().enumerate(){
        let select=if selectors==0{ONE}else if i==0{-selector}else{selector};
        let p=aq_pattern_lit(&mut c,&t.pattern,&z);
        let guard=aq_lt(&mut c,&mult,t.signed.unsigned_abs());
        let both=c.and(p,guard);let active=c.and(select,both);
        valid=c.or(valid,active);
        if t.signed<0{negative=c.or(negative,active);}
    }
    c.enforce(valid);
    let mut acc=[ZERO,ZERO,negative]; // conjugation of real target sign
    for (&m,&k) in &s.phase{
        let lit=c.monomial(m,&bits);
        let w=std::array::from_fn(|i|if k>>i&1!=0{lit}else{ZERO});
        acc=c.add3(acc,w);
    }
    if c.vars>32768||c.clauses.len()>262144{return None;}
    Some((c,acc,primary))
}

// Research-only exact disjoint-class guard fusion. No change to the RR
// engine, target scale, or phase-bucket protocol. None = original fallback.
fn aq_overlap_fused(s:&Symbolic,x:u64,b:&AqState)->Option<(Cnf,[Lit;3],usize)>{
    if s.n!=b.n||s.h>32||s.n+s.h>63||b.terms.len()!=2{return None;}
    let [hi,lo]=b.terms.as_slice() else{return None;};
    let AqPattern::Fixed(fixed)=hi.pattern else{return None;};
    let AqPattern::Except{offset,width,excluded,outside}=lo.pattern else{return None;};
    if width==0||offset.checked_add(width)?>b.n||b.n>=64||hi.signed==0||lo.signed==0{return None;}
    let mask=((1u64<<width)-1)<<offset;
    if excluded>=1u64<<width||outside&mask!=0||outside>>b.n!=0||
       fixed!=(outside|(excluded<<offset)){return None;}
    let h=hi.signed.unsigned_abs();let l=lo.signed.unsigned_abs();
    let mag=h.max(l);
    let counter=(64-(mag-1).leading_zeros()) as usize;
    let primary=s.h+counter;
    let mut c=Cnf::new(primary);
    let bits:Vec<_>=(0..s.n).map(|i|if x>>i&1!=0{ONE}else{ZERO})
        .chain((0..s.h).map(|i|(i+2) as Lit)).collect();
    let z:Vec<_>=s.output.iter().map(|p|c.anf(p,&bits)).collect();
    let mult:Vec<_>=(0..counter).map(|i|(s.h+i+2) as Lit).collect();
    let eq=|c:&mut Cnf,bits:&[Lit],v:u64|->Lit{
        bits.iter().enumerate().fold(ONE,|a,(i,&bit)|c.and(a,if v>>i&1!=0{bit}else{-bit}))
    };
    let low_cube=eq(&mut c,&z[..offset],outside);
    let high_cube=eq(&mut c,&z[offset+width..],outside>>(offset+width));
    let cube=c.and(low_cube,high_cube);
    let e=eq(&mut c,&z[offset..offset+width],excluded);
    let hlt=aq_lt(&mut c,&mult,h);
    let llt=aq_lt(&mut c,&mult,l);
    let inside=if h>=l{let extra=c.and(e,hlt);c.or(llt,extra)}
        else{let extra=c.and(-e,llt);c.or(hlt,extra)};
    let valid=c.and(cube,inside);
    c.enforce(valid);
    // Sign is relevant only on valid assignments.
    let negative=match (hi.signed<0,lo.signed<0){
        (true,true)=>ONE,(true,false)=>e,(false,true)=>-e,(false,false)=>ZERO
    };
    let mut acc=[ZERO,ZERO,negative];
    for (&m,&k) in &s.phase{
        let lit=c.monomial(m,&bits);
        let w=std::array::from_fn(|i|if k>>i&1!=0{lit}else{ZERO});
        acc=c.add3(acc,w);
    }
    if c.vars>32768||c.clauses.len()>262144{return None;}
    Some((c,acc,primary))
}

fn aq_rr_terminal(s:&Symbolic,x:u64,b:&AqState)->Option<bool>{
    if s.h!=0{return None;}
    let (z,_)=path(s,x,0);
    // A normalized single-path circuit output is a basis ray; a normalized
    // target equals it iff its support contains exactly that basis.
    Some(b.terms.len()==1&&matches!(b.terms[0].pattern,AqPattern::Fixed(v) if v==z))
}
fn aq_export(dir:&std::path::Path){
    let mut manifest=String::from("case\tvariant\tmode\tstatus\tprimary\tphase\tk\tbuild_ns\trr_ns\tencode_ns\texpected\n");
    for (family,pre,post,src) in AQ_SOURCES{
        for (suffix,bytes) in [("pre.hsl",pre),("post.hsl",post),("circuit.qasm",src)]{
            std::fs::write(dir.join(format!("aq-source-{family}-{suffix}")),bytes).unwrap();
        }
        let start=std::time::Instant::now();
        let (w,aa)=aq_family(pre).expect("pre admission");
        let (wb,bb)=aq_family(post).expect("post admission");
        assert_eq!(w,wb);assert_eq!(aa.len(),bb.len());
        let width=aa[0].n;
        assert!(aa.iter().chain(&bb).all(|a|a.n==width));
        let ops=factor_source_ops(src,width);
        let (native_ops,n)=quprs::qasm::parse_qasm_str_source_pinned(src).expect("source-pinned native QASM parse");
        assert_eq!((native_ops,n),(ops.clone(),width));
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        for g in &ops{g.apply(&mut ps,false);}
        let raw=compact(&ps,n).expect("raw native CPS");
        let h0=raw.h;let build_ns=start.elapsed().as_nanos();
        let t=std::time::Instant::now();
        let (reduced,frame,scale,steps)=native_rr_checkpoint(ps,n).expect("native checkpoint");
        assert_eq!(frame.compact(&reduced).unwrap(),Anf::from([0]));
        let residual=compact(&reduced,n).unwrap();
        let rr_ns=t.elapsed().as_nanos();
        let k0=h0.checked_sub(scale as usize).expect("scale");
        let discovery_start=std::time::Instant::now();
        let pairs=aq_discover_pairs(&raw,&aa,&bb).expect("unique raw StateSet candidates");
        assert_eq!(aq_discover_pairs(&residual,&aa,&bb).as_ref(),Some(&pairs));
        let discovery_ns=discovery_start.elapsed().as_nanos();
        // Actual source-derived StateSet: reverse post enumeration to catch
        // accidental zip/same-index assumptions; duplicate target -> ambiguity.
        if bb.len()>1{
            let mut reversed=bb.clone();reversed.reverse();
            let reverse_pairs=aq_discover_pairs(&raw,&aa,&reversed).unwrap();
            assert_eq!(reverse_pairs,pairs.iter().map(|j|bb.len()-1-*j).collect::<Vec<_>>());
            let mut ambiguous=bb.clone();ambiguous.push(bb[pairs[0]].clone());
            assert!(aq_discover_pairs(&raw,&aa,&ambiguous).is_none());
        }
        println!("AQ_HSL_AUTO_PAIR family={family} possible_pairs={} selected_pairs={} raw_residual_agree=true discovery_ns={discovery_ns} source_pinned=true",
            aa.len()*bb.len(),pairs.len());
        for (label,a) in aa.iter().enumerate(){
        let b=&bb[pairs[label]];
        let x=aq_fixed_input(a).expect("fixed input only");
        let name=if w==0{family.to_owned()}else{format!("{family}-label{label}")};
        // Separate dense gate oracle; not used to select route.
        let dense=dense_state(n,&ops,x);
        let (mut sum,mut norm)=(0i128,0i128);
        for (z,r) in dense.iter().enumerate(){
            assert_eq!(r[1..],[0,0,0]);
            let m=b.terms.iter().filter(|t|aq_match(&t.pattern,z as u64)).map(|t|i128::from(t.signed)).sum::<i128>();
            sum+=i128::from(r[0])*m;norm+=i128::from(r[0]).pow(2);
        }
        assert_eq!(norm,1i128<<h0);assert_eq!(sum.pow(2),1i128<<(h0+b.k));
        for variant in ["source","relative-mutant","global-sign"]{
            let mut target=b.clone();
            if variant=="relative-mutant"{
                if target.terms.len()==1{
                    let AqPattern::Fixed(v)=target.terms[0].pattern else{panic!("fixed post")};
                    target.terms[0].pattern=AqPattern::Fixed(v^1);
                }else{target.terms[0].signed=-target.terms[0].signed;}
            }else if variant=="global-sign"{for t in &mut target.terms{t.signed=-t.signed;}}
            // Sign mutations preserve the selected support cube. Recheck the
            // pairing against the entire mutated target family, not just this
            // target, so a StateSet refutation cannot miss an alternate match.
            if bb.len()>1{
                let mut targets=bb.clone();
                for t in &mut targets{
                    if variant=="relative-mutant"{
                        assert!(t.terms.len()>1,"multi-state basis mutants need separate pairing");
                        t.terms[0].signed=-t.terms[0].signed;
                    }else if variant=="global-sign"{for a in &mut t.terms{a.signed=-a.signed;}}
                }
                assert_eq!(aq_discover_pairs(&raw,&aa,&targets).as_ref(),Some(&pairs));
                assert_eq!(aq_discover_pairs(&residual,&aa,&targets).as_ref(),Some(&pairs));
            }
            let expected=variant!="relative-mutant";
            let rr=aq_rr_terminal(&residual,x,&target);
            if let Some(v)=rr{assert_eq!(v,expected);}
            for mode in ["rr","wmc","hybrid"]{
                let key=format!("aq-{name}-{variant}-{mode}");
                let time=std::time::Instant::now();
                let (status,primary,phase,k)=if mode=="rr"{
                    (match rr{Some(true)=>"PROVED",Some(false)=>"REFUTED",None=>"UNKNOWN"},0,String::new(),0)
                }else if mode=="hybrid"&&rr.is_some(){
                    (if rr.unwrap(){"PROVED"}else{"REFUTED"},0,String::new(),0)
                }else{
                    let (s,k)=if mode=="wmc"{(&raw,h0+target.k)}else{(&residual,k0+target.k)};
                    let (c,p,primary)=aq_overlap(s,x,&target).expect("overlap encoding");
                    let mut text=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                    for row in &c.clauses{for l in row{text.push_str(&format!("{l} "));}text.push_str("0\n");}
                    std::fs::write(dir.join(format!("{key}.cnf")),text).unwrap();
                    ("READY",primary,p.iter().map(ToString::to_string).collect::<Vec<_>>().join(","),k)
                };
                let enc_ns=time.elapsed().as_nanos();
                manifest.push_str(&format!("{name}\t{variant}\t{mode}\t{status}\t{primary}\t{phase}\t{k}\t{build_ns}\t{}\t{enc_ns}\t{expected}\n",if mode=="wmc"{0}else{rr_ns}));
            }
        }
        println!("AQ_HSL_NATIVE_EXPORT case={name} h0={h0} residual_h={} scale2={scale} rr_steps={steps}",residual.h);
        }
        println!("AQ_HSL_FAMILY_ADMISSION family={family} labels={} label_bits={w} auto_pair=true raw_residual_agree=true dense_oracle=true",aa.len());
    }
    std::fs::write(dir.join("aq-hsl-p0.tsv"),manifest).unwrap();
    println!("AQ_HSL_NATIVE_EXPORT_SUMMARY families=3 columns=10 variants=30 arms=90");
}

const AQ_SOURCES:[(&str,&str,&str,&str);3]=[
    ("bv03",r####"Constants
c1 := 1
Extended Dirac
{c1 |0000>}
"####,r####"Constants
c1 := 1
Extended Dirac
{c1 |1011>}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[4];

h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
z qubits[3];
cx qubits[0], qubits[3];
cx qubits[2], qubits[3];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
"####),
    ("grover03",r####"Constants
c1 := 1
Extended Dirac
{c1 |00000>}
"####,r####"Constants
aH := 11 / (sqrt2 ^ 7)
aL := -1 / (sqrt2 ^ 7)
Extended Dirac
{aH |01001> + aL ∑ |i|=3, i≠010 |i01>}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[5];
x qubits[4];

h qubits[0];
h qubits[1];
h qubits[2];
h qubits[4];

x qubits[0];
x qubits[2];
ccx qubits[0], qubits[1], qubits[3];
cz qubits[3], qubits[2];
ccx qubits[0], qubits[1], qubits[3];
x qubits[0];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
x qubits[0];
x qubits[1];
x qubits[2];
ccx qubits[0], qubits[1], qubits[3];
cz qubits[3], qubits[2];
ccx qubits[0], qubits[1], qubits[3];
x qubits[0];
x qubits[1];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
x qubits[4];

x qubits[0];
x qubits[2];
ccx qubits[0], qubits[1], qubits[3];
cz qubits[3], qubits[2];
ccx qubits[0], qubits[1], qubits[3];
x qubits[0];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
x qubits[0];
x qubits[1];
x qubits[2];
ccx qubits[0], qubits[1], qubits[3];
cz qubits[3], qubits[2];
ccx qubits[0], qubits[1], qubits[3];
x qubits[0];
x qubits[1];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
x qubits[4];

h qubits[4];
"####),
    ("mogrover03",r####"Constants
c1 := 1
Extended Dirac
{c1 |s00000> : |s|=3}
"####,r####"Constants
aH := 11 / (sqrt2 ^ 7)
aL := -1 / (sqrt2 ^ 7)
Extended Dirac
{aH |ss01> + aL ∑ |i|=3, i≠s |si01> : |s|=3}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[8];
x qubits[7];

x qubits[0];
x qubits[1];
x qubits[2];
h qubits[3];
h qubits[4];
h qubits[5];
h qubits[7];

cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[3];
x qubits[4];
x qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
x qubits[3];
x qubits[4];
x qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[7];

cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cx qubits[0], qubits[3];
cx qubits[1], qubits[4];
cx qubits[2], qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[3];
x qubits[4];
x qubits[5];
ccx qubits[3], qubits[4], qubits[6];
cz qubits[6], qubits[5];
ccx qubits[3], qubits[4], qubits[6];
x qubits[3];
x qubits[4];
x qubits[5];
h qubits[3];
h qubits[4];
h qubits[5];
x qubits[7];

x qubits[0];
x qubits[1];
x qubits[2];
h qubits[7];
"####),
];


// Source-locked GHZall HSL template: complete basis input family and the
// complementary two-ket family with both relative signs. Scope is deliberately
// narrow; this is not a general HSL parser or a separate reduction engine.
fn aq_ghzall_admit(n:usize,pre:&str,post:&str)->bool{
    n>=2 && n<=16 &&
    pre.trim()==format!("Constants\nc1 := 1\nExtended Dirac\n{{c1 |ji> : |j|=1, |i|={}}}",n-1) &&
    post.trim()==format!("Constants\ncp := 1/sqrt2\ncn := -1/sqrt2\nExtended Dirac\n{{cp |0i> + cp |1i'> : |i|={}}} ∪\n{{cp |0i> + cn |1i'> : |i|={}}}",n-1,n-1)
}

// C1: specialize the single live path variable using the existing ANF and
// phase operations. The two outputs must be complementary on every input;
// the first coordinate orders the two paths. The common normalization is
// separately checked by the caller. No input/target enumeration.
#[derive(Debug,PartialEq,Eq)]
struct AqGhzWitness {
    tail: Vec<BTreeSet<u64>>,
    sign: BTreeMap<u64,u8>,
}
fn aq_ghz_witness(s:&Symbolic)->Option<AqGhzWitness>{
    if s.n<2 || s.n>16 || s.h!=1 || s.output.len()!=s.n{return None;}
    let y=1u64<<s.n;
    let lo=Cube{mask:y,value:0};
    let hi=Cube{mask:y,value:y};
    if !specialize_bool(&s.output[0],lo).is_empty() ||
        specialize_bool(&s.output[0],hi)!=Anf::from([0]) {return None;}
    let mut tail=Vec::new();
    for p in s.output.iter().skip(1){
        let a=specialize_bool(p,lo);
        let b=specialize_bool(p,hi);
        // Restrict this first extractor to affine target-index functions.
        if a.iter().any(|m|m.count_ones()>1){return None;}
        let mut complement=a.clone();
        if !complement.insert(0){complement.remove(&0);}
        if complement!=b{return None;}
        tail.push(a);
    }
    let p0=specialize_phase(&s.phase,lo);
    let mut delta=specialize_phase(&s.phase,hi);
    for (m,k) in p0{
        let v=(delta.get(&m).copied().unwrap_or(0)+8-k)%8;
        if v==0{delta.remove(&m);}else{delta.insert(m,v);}
    }
    // Relative phase must be exactly +1 or -1; input-dependent common
    // phase is irrelevant to ray equality. Coefficients 0/4 are sufficient.
    if delta.values().any(|&k|k!=4){return None;}
    Some(AqGhzWitness{tail,sign:delta})
}
fn aq_ghz_index(w:&AqGhzWitness,x:u64)->u64{
    w.tail.iter().enumerate().fold(0,|z,(i,p)|{
        let b=p.iter().fold(false,|b,m|b^(x&m==*m));
        z|((b as u64)<<(i+1))
    })
}
fn aq_ghz_negative(w:&AqGhzWitness,x:u64)->bool{
    w.sign.keys().fold(false,|b,m|b^(x&m==*m))
}
// C2: for a plus-only post family, a nonzero Boolean sign ANF provides
// a witness without enumerating input states. A minimum-degree monomial
// has no proper-subset term and evaluates to 1 on its own assignment.
fn aq_ghz_minus_input(w:&AqGhzWitness)->Option<u64>{
    let x=*w.sign.keys().min_by_key(|m|m.count_ones())?;
    assert!(aq_ghz_negative(w,x));
    Some(x)
}
#[test]
fn hoare_autoq_ghzall_symbolic_witness(){
    for (n,pre,post,src) in AQ_GHZALL_SOURCES{
        assert!(aq_ghzall_admit(n,pre,post));
        let t=std::time::Instant::now();
        let ops=factor_source_ops(src,n);
        let (parsed,width)=quprs::qasm::parse_qasm_str_source_pinned(src).expect("source-pinned GHZall parse");
        assert_eq!((parsed,width),(ops.clone(),n));
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        for g in &ops{g.apply(&mut ps,false);}
        let raw=compact(&ps,n).expect("native GHZall CPS");
        let h0=ops.iter().filter(|g|matches!(g,G::H(_))).count();
        assert_eq!(h0,1);assert_eq!(raw.h,1);
        let build_ns=t.elapsed().as_nanos();
        let t=std::time::Instant::now();
        let w=aq_ghz_witness(&raw).expect("symbolic whole-domain witness");
        let neg=aq_ghz_minus_input(&w).expect("plus-only post has counterexample");
        let structural_ns=t.elapsed().as_nanos();

        let (reduced,frame,scale,steps)=native_rr_checkpoint(ps,n).expect("native RR checkpoint");
        assert_eq!(scale,0);assert_eq!(frame.compact(&reduced).unwrap(),Anf::from([0]));
        let residual=compact(&reduced,n).unwrap();
        assert_eq!(aq_ghz_witness(&residual).as_ref(),Some(&w));

        // Separate dense exact gate oracle. Enumerate every target for each
        // input only here, never in the symbolic route. Removing the minus
        // branch is a genuine negative spec; flipping both signs is NOT.
        let total=1u64<<n;let mask=total-1;
        let mut matches=0u64;let mut plus_matches=0u64;
        let mut pairs=0u64;
        let t=std::time::Instant::now();
        for x in 0..total{
            let v=dense_state(n,&ops,x);
            assert!(v.iter().all(|r|r[1..]==[0,0,0]));
            assert_eq!(v.iter().map(|r|i128::from(r[0]).pow(2)).sum::<i128>(),2);
            let index=aq_ghz_index(&w,x);
            let minus=aq_ghz_negative(&w,x);
            let mut found=Vec::new();
            for i in 0..total/2{
                let a=i<<1;let b=mask^a;
                for s in [1i128,-1]{
                    pairs+=1;
                    let sum=i128::from(v[a as usize][0])+s*i128::from(v[b as usize][0]);
                    if sum.abs()==2{
                        found.push((a,s<0));
                        if s>0{plus_matches+=1;}
                    }
                }
            }
            assert_eq!(found,vec![(index,minus)]);
            matches+=1;
        }
        let dense_ns=t.elapsed().as_nanos();
        let v=dense_state(n,&ops,neg);
        assert!((0..total/2).all(|i|{
            let a=i<<1;let b=mask^a;
            (i128::from(v[a as usize][0])+i128::from(v[b as usize][0])).abs()!=2
        }));
        // Remove the last entangling gate from the actual source. A failed
        // structural admission is UNKNOWN/fallback, not itself REFUTED.
        let broken=&ops[..ops.len()-1];
        let s=native(n,broken).expect("negative source native");
        assert!(aq_ghz_witness(&s).is_none());
        let v=dense_state(n,broken,0);
        assert!((0..total/2).all(|i|{
            let a=i<<1;let b=mask^a;
            (i128::from(v[a as usize][0])+i128::from(v[b as usize][0])).abs()!=2 &&
            (i128::from(v[a as usize][0])-i128::from(v[b as usize][0])).abs()!=2
        }));
        assert_eq!(matches,total);assert_eq!(plus_matches,total/2);
        println!("AQ_GHZALL_SYMBOLIC n={n} full_pairs={pairs} symbolic_pairs=0 matched={matches} plus_matches={plus_matches} plus_only_refuted=true witness={neg} broken_unknown=true dense_oracle=true raw_residual_agree=true scale2={scale} rr_steps={steps} build_ns={build_ns} structural_ns={structural_ns} dense_oracle_ns={dense_ns}");
    }
}

// AutoQ pin 7eed39ad7ba5615a87c3f532a24f866e08967c12; original source bytes (pre, post, circuit).
const AQ_GHZALL_SOURCES:[(usize,&str,&str,&str);4]=[
    (3,r####"Constants
c1 := 1
Extended Dirac
{c1 |ji> : |j|=1, |i|=2}
"####,r####"Constants
cp := 1/sqrt2
cn := -1/sqrt2
Extended Dirac
{cp |0i> + cp |1i'> : |i|=2} ∪
{cp |0i> + cn |1i'> : |i|=2}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[3];

h qubits[0];
cx qubits[0], qubits[1];
cx qubits[1], qubits[2];
"####), // blobs 01a7d8579b1a6079fde76991cd3af5c4c7b3952c ba24ec21eef82940d34ca90822aedc3650293ac5 f1f040ec26312825a56db1f0ac735f81cad5dd9f
    (4,r####"Constants
c1 := 1
Extended Dirac
{c1 |ji> : |j|=1, |i|=3}
"####,r####"Constants
cp := 1/sqrt2
cn := -1/sqrt2
Extended Dirac
{cp |0i> + cp |1i'> : |i|=3} ∪
{cp |0i> + cn |1i'> : |i|=3}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[4];

h qubits[0];
cx qubits[0], qubits[1];
cx qubits[1], qubits[2];
cx qubits[2], qubits[3];
"####), // blobs f735cf6987e054b53d2682edb43abb00463182e9 b47769284fba9e93c8de087848c2b5188a418235 34b355874a3658e45307c44529473a93258e5bd3
    (5,r####"Constants
c1 := 1
Extended Dirac
{c1 |ji> : |j|=1, |i|=4}
"####,r####"Constants
cp := 1/sqrt2
cn := -1/sqrt2
Extended Dirac
{cp |0i> + cp |1i'> : |i|=4} ∪
{cp |0i> + cn |1i'> : |i|=4}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[5];

h qubits[0];
cx qubits[0], qubits[1];
cx qubits[1], qubits[2];
cx qubits[2], qubits[3];
cx qubits[3], qubits[4];
"####), // blobs b67b488134a71aabb55f8277d3e91c52f2fcd014 f4122a5fffab2806442e925a2d768f28ec26fa40 ad462048e1513e80d53c397d215ad1e2dafe6a3e
    (8,r####"Constants
c1 := 1
Extended Dirac
{c1 |ji> : |j|=1, |i|=7}
"####,r####"Constants
cp := 1/sqrt2
cn := -1/sqrt2
Extended Dirac
{cp |0i> + cp |1i'> : |i|=7} ∪
{cp |0i> + cn |1i'> : |i|=7}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[8];

h qubits[0];
cx qubits[0], qubits[1];
cx qubits[1], qubits[2];
cx qubits[2], qubits[3];
cx qubits[3], qubits[4];
cx qubits[4], qubits[5];
cx qubits[5], qubits[6];
cx qubits[6], qubits[7];
"####), // blobs a712713768d9605514ff30208785b5bfdbffad06 7a2693425da63470feca65ca62d93e9d19d3a461 f2c88eaf5779c0bd340a501514432290369fdf7f
];


// C3 reuse gate: original RR only. Fix the symbolic pre ancilla before
// applying gates while retaining input IDs (never summed integration vars).
fn aq_mobv_build(k:usize,ops:&[G],restricted:bool)->PathSum{
    let n=2*k+1;let mut ps=PathSum::new(n);
    ps.set_auto_reduce(false);
    if restricted{for f in ps.f.functions.iter_mut().skip(k){f.clear();}}
    for g in ops{g.apply(&mut ps,false);}
    ps
}
fn aq_mobv_rr(k:usize,ops:&[G],restricted:bool)->(usize,usize,u32,usize,&'static str,Option<u64>,u128){
    let n=2*k+1;let t=std::time::Instant::now();
    let ps=aq_mobv_build(k,ops,restricted);
    let h0=ops.iter().filter(|g|matches!(g,G::H(_))).count();
    let Some((p,frame,scale,steps))=native_rr_checkpoint(ps,n) else{
        return (h0,h0,0,0,"UNKNOWN",None,t.elapsed().as_nanos());
    };
    assert_eq!(frame.compact(&p).unwrap(),Anf::from([0]));
    let s=compact(&p,n).unwrap();
    if s.h!=0||scale as usize!=h0{
        return (h0,s.h,scale,steps,"UNKNOWN",None,t.elapsed().as_nanos());
    }
    let pre=Cube{mask:((1u64<<n)-1)^((1u64<<k)-1),value:0};
    // StateSet membership is existential in the post label: both output
    // blocks must be equal, not necessarily equal to the original input.
    // The original paper circuit's stronger identity-label relation is
    // checked independently by the dense oracle below.
    for i in k..=2*k{
        let mut diff=specialize_bool(&s.output[i],pre);
        let want=if i==2*k{Anf::from([0])}
            else{specialize_bool(&s.output[i-k],pre)};
        for m in want{if !diff.insert(m){diff.remove(&m);}}
        if let Some(&x)=diff.iter().min_by_key(|m|m.count_ones()){
            assert!(x<(1u64<<k));
            assert!(diff.iter().fold(false,|v,m|v^(x&m==*m)));
            return (h0,s.h,scale,steps,"REFUTED",Some(x),t.elapsed().as_nanos());
        }
    }
    (h0,s.h,scale,steps,"PROVED",None,t.elapsed().as_nanos())
}
#[test]
fn hoare_autoq_mobv_original_rr_reuse_gate(){
    for (k,pre,post,src) in AQ_MOBV_SOURCES{
        let n=2*k+1;
        assert_eq!(pre.trim(),format!("Constants\nc1 := 1\nExtended Dirac\n{{c1 |i{}> : |i|={k}}}","0".repeat(k+1)));
        assert_eq!(post.trim(),format!("Constants\nc1 := 1\nExtended Dirac\n{{c1 |ii1> : |i|={k}}}"));
        let ops=factor_source_ops(src,n);
        let parsed=quprs::qasm::parse_qasm_str_source_pinned(src);
        // The existing opt-in SourceTrust frontend is limited to 16 wires.
        // Preserve the 17-wire paper case as an explicit admission blocker;
        // do not silently bypass the contract with the narrow parser.
        if n>16{
            assert_eq!(parsed.unwrap_err(),"SourceTrust unsupported native lowering or register width");
            println!("AQ_MOBV_ADMISSION k={k} n={n} status=BLOCKED reason=source_width_cap skipped_arms=6");
            continue;
        }
        assert_eq!(parsed.expect("source-pinned MOBV parse"),(ops.clone(),n));
        let pre_cube=Cube{mask:((1u64<<n)-1)^((1u64<<k)-1),value:0};
        let raw=compact(&aq_mobv_build(k,&ops,false),n).unwrap();
        let restricted=compact(&aq_mobv_build(k,&ops,true),n).unwrap();
        assert_eq!(raw.h,restricted.h);
        assert_eq!(raw.output.iter().map(|p|specialize_bool(p,pre_cube)).collect::<Vec<_>>(),restricted.output);
        assert_eq!(specialize_phase(&raw.phase,pre_cube),restricted.phase);
        let mut no_z=ops.clone();
        let z=no_z.iter().position(|g|matches!(g,G::Z(_))).unwrap();no_z.remove(z);
        let mut no_ccx=ops.clone();
        let c=no_ccx.iter().position(|g|matches!(g,G::CCX(_,_,_))).unwrap();no_ccx.remove(c);
        for (variant,gates,expected) in [("source",&ops,"PROVED"),("missing-z",&no_z,"REFUTED"),("missing-ccx",&no_ccx,"REFUTED")]{
            for restricted in [false,true]{
                let (h0,h,scale,steps,verdict,witness,elapsed)=aq_mobv_rr(k,gates,restricted);
                assert!(verdict=="UNKNOWN"||verdict==expected);
                if let Some(x)=witness{
                    let v=dense_state(n,gates,x);
                    // Replay nonmembership against EVERY permitted post
                    // label, not just the label equal to the input.
                    assert!((0..1u64<<k).all(|j|v[(j|(j<<k)|(1u64<<(2*k))) as usize]==[0;4]));
                    assert_eq!(v.iter().filter(|a|**a!=[0;4]).count(),1);
                }
                println!("AQ_MOBV_RR k={k} n={n} variant={variant} restricted={restricted} h0={h0} residual_h={h} scale2={scale} rr_steps={steps} verdict={verdict} witness={witness:?} elapsed_ns={elapsed} source_pinned=true");
            }
        }
        let xs:Vec<u64>=if k<=5{(0..1u64<<k).collect()}else{vec![0,1,(1u64<<k)-1]};
        for &x in &xs{
            let v=dense_state(n,&ops,x);let z=x|(x<<k)|(1u64<<(2*k));
            assert!(v.iter().enumerate().all(|(i,a)|if i==z as usize{
                a[1..]==[0,0,0]&&i128::from(a[0]).abs()==1i128<<(k+1)
            }else{*a==[0;4]}));
        }
        println!("AQ_MOBV_ORACLE k={k} inputs={} restricted_raw_agree=true",xs.len());
    }
}

// AutoQ source pin 7eed39ad7ba5615a87c3f532a24f866e08967c12.
const AQ_MOBV_SOURCES:[(usize,&str,&str,&str);4]=[
    (3,r####"Constants
c1 := 1
Extended Dirac
{c1 |i0000> : |i|=3}
"####,r####"Constants
c1 := 1
Extended Dirac
{c1 |ii1> : |i|=3}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[7];

h qubits[6];
h qubits[5];
h qubits[4];
h qubits[3];
z qubits[6];
ccx qubits[0], qubits[3], qubits[6];
ccx qubits[1], qubits[4], qubits[6];
ccx qubits[2], qubits[5], qubits[6];
h qubits[6];
h qubits[5];
h qubits[4];
h qubits[3];
"####), // blobs dc3f455222fe91a8f297ee5834060cff4ddf0671 4d41e792b24a3859fe6b2d877480968ec864742a df5cab778713674b31590beb866ff8e497ed3273
    (4,r####"Constants
c1 := 1
Extended Dirac
{c1 |i00000> : |i|=4}
"####,r####"Constants
c1 := 1
Extended Dirac
{c1 |ii1> : |i|=4}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[9];

h qubits[8];
h qubits[7];
h qubits[6];
h qubits[5];
h qubits[4];
z qubits[8];
ccx qubits[0], qubits[4], qubits[8];
ccx qubits[1], qubits[5], qubits[8];
ccx qubits[2], qubits[6], qubits[8];
ccx qubits[3], qubits[7], qubits[8];
h qubits[8];
h qubits[7];
h qubits[6];
h qubits[5];
h qubits[4];
"####), // blobs 901a2b6196275d14b38eba0dd99d83fa05533201 2d356d0ddc17477d521c0f0067391cba12dab60f 9287d282a718d1799c46651215c4ff464ee44345
    (5,r####"Constants
c1 := 1
Extended Dirac
{c1 |i000000> : |i|=5}
"####,r####"Constants
c1 := 1
Extended Dirac
{c1 |ii1> : |i|=5}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[11];

h qubits[10];
h qubits[9];
h qubits[8];
h qubits[7];
h qubits[6];
h qubits[5];
z qubits[10];
ccx qubits[0], qubits[5], qubits[10];
ccx qubits[1], qubits[6], qubits[10];
ccx qubits[2], qubits[7], qubits[10];
ccx qubits[3], qubits[8], qubits[10];
ccx qubits[4], qubits[9], qubits[10];
h qubits[10];
h qubits[9];
h qubits[8];
h qubits[7];
h qubits[6];
h qubits[5];
"####), // blobs ca282570ca1f3a08c468560b54a63059ffaf982b 32fac194a4042a42a2871c5ad2c99674bf92dc19 23c716a443c317b72568e1ed0b640aaf33f2707e
    (8,r####"Constants
c1 := 1
Extended Dirac
{c1 |i000000000> : |i|=8}
"####,r####"Constants
c1 := 1
Extended Dirac
{c1 |ii1> : |i|=8}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[17];

h qubits[16];
h qubits[15];
h qubits[14];
h qubits[13];
h qubits[12];
h qubits[11];
h qubits[10];
h qubits[9];
h qubits[8];
z qubits[16];
ccx qubits[0], qubits[8], qubits[16];
ccx qubits[1], qubits[9], qubits[16];
ccx qubits[2], qubits[10], qubits[16];
ccx qubits[3], qubits[11], qubits[16];
ccx qubits[4], qubits[12], qubits[16];
ccx qubits[5], qubits[13], qubits[16];
ccx qubits[6], qubits[14], qubits[16];
ccx qubits[7], qubits[15], qubits[16];
h qubits[16];
h qubits[15];
h qubits[14];
h qubits[13];
h qubits[12];
h qubits[11];
h qubits[10];
h qubits[9];
h qubits[8];
"####), // blobs 840fce2b3accaec44a355b8058bd249bd7c56b03 b56988b6db8f18a1512d3cd6551823589588b7f3 9d720831156dafbb4f0636958bbd0432632dcaee
];


// C3 process-isolated whole-family runner. Test harness is only the transport;
// no oracle work, precomputed pairing, shared preparation or hidden fallback.
#[test]
fn hoare_autoq_c3_arm(){
    let Ok(case)=std::env::var("AQ_C3_CASE") else{return;};
    use std::io::Write;
    let mode=std::env::var("AQ_C3_MODE").unwrap();
    let file=std::path::PathBuf::from(std::env::var_os("AQ_C3_CNF").unwrap());
    let start=std::time::Instant::now();
    let cap=std::time::Duration::from_millis(std::env::var("AQ_C3_BUDGET_MS").unwrap().parse().unwrap());
    let deadline=start+cap;
    assert!(["rr","wmc","hybrid","hybrid-support","structural","hybrid-direct","structural-factor","raw-factor"].contains(&mode.as_str()));
    let mut queries=0usize;let mut pairs=0usize;let mut visited=0usize;
    let mut route="baseline";let mut rejected=false;
    let mut witness=None;
    let mut factor_work=0usize;let mut factor_hits=0usize;let mut factor_rejects=0usize;let mut direct_hits=0usize;
    let result=(||->Option<bool>{
        let ghz=case.starts_with("ghz");
        let plus=case.ends_with("-plus");let broken=case.ends_with("-broken");
        let (n,pre,post,src)=if ghz{
            let n:usize=case.strip_prefix("ghz")?.split('-').next()?.parse().ok()?;
            let &(_,a,b,c)=AQ_GHZALL_SOURCES.iter().find(|r|r.0==n)?;
            if !aq_ghzall_admit(n,a,b){return None;}
            (n,a,b,c)
        }else{
            let base=case.strip_suffix("-relative").unwrap_or(&case);
            let &(_,a,b,c)=AQ_SOURCES.iter().chain(AQ_C3_HELDOUT.iter()).find(|r|r.0==base)?;
            let (_,aa)=aq_family(a)?;(aa.first()?.n,a,b,c)
        };
        let build_start=std::time::Instant::now();
        println!("AQ_CPS_STAGE stage=build-start");std::io::stdout().flush().ok()?;
        let mut ops=factor_source_ops(src,n);
        if quprs::qasm::parse_qasm_str_source_pinned(src).ok()? != (ops.clone(),n){return None;}
        if broken{ops.pop()?;}
        let mut ps=PathSum::new(n);ps.set_auto_reduce(false);
        for g in &ops{g.apply(&mut ps,false);}
        let h0=ops.iter().filter(|g|matches!(g,G::H(_))).count();
        println!("AQ_CPS_STAGE stage=build-end ns={}",build_start.elapsed().as_nanos());std::io::stdout().flush().ok()?;
        let (s,k)=if mode=="wmc"||mode=="raw-factor"{(compact(&ps,n)?,h0)}else{
            println!("AQ_CPS_STAGE stage=rr-start");std::io::stdout().flush().ok()?;
            let rr_start=std::time::Instant::now();
            let (p,frame,scale,steps)=native_rr_checkpoint(ps,n)?;
            println!("AQ_CPS_STAGE stage=rr-end ns={} steps={steps}",rr_start.elapsed().as_nanos());std::io::stdout().flush().ok()?;
            if frame.compact(&p)?!=Anf::from([0]){return None;}
            (compact(&p,n)?,h0.checked_sub(scale as usize)?)
        };
        println!("AQ_CPS_RESIDUAL raw_h={h0} residual_h={} k={k} phase_terms={} output_terms={}",
            s.h,s.phase.len(),s.output.iter().map(|p|p.len()).sum::<usize>());
        if mode=="structural"||mode=="structural-factor"||mode=="raw-factor"{
            if ghz&&k==1{
                if let Some(w)=aq_ghz_witness(&s){
                    route="symbolic";
                    if plus{witness=aq_ghz_minus_input(&w);return Some(witness.is_none());}
                    return Some(true);
                }
            }
            rejected=true;route="fallback";
        }
        if std::time::Instant::now()>=deadline{return None;}
        // Strict baseline: original RR terminal check and existing exact
        // overlap encoder. Sound cube screening and early existential match.
        // No symbolic GHZ witness, dense oracle, or assumed label pairing.
        let (aa,bb)=if ghz{
            let total=1u64<<n;
            let aa=(0..total).map(|x|AqState{n,k:0,terms:vec![AqTerm{pattern:AqPattern::Fixed(x),signed:1}]}).collect::<Vec<_>>();
            let mut bb=Vec::new();
            for i in 0..total/2{
                for sign in [1,-1]{
                    if plus&&sign<0{continue;}
                    let a=i<<1;let b=(total-1)^a;
                    bb.push(AqState{n,k:1,terms:vec![AqTerm{pattern:AqPattern::Fixed(a),signed:1},AqTerm{pattern:AqPattern::Fixed(b),signed:sign}]});
                }
            }
            (aa,bb)
        }else{
            let post=if case.ends_with("-relative"){post.replace("aH := 11 /","aH := -11 /")}else{post.to_owned()};
            (aq_family(pre)?.1,aq_family(&post)?.1)
        };
        if mode=="rr"&&s.h!=0{return None;}
        let cubes:Vec<_>=bb.iter().map(aq_support_cube).collect();
        // Phase-blind exact support index: only two distinct fixed kets
        // and one live path, at the original 1/sqrt2 scale.
        let mut index=BTreeMap::<(u64,u64),Vec<usize>>::new();
        let indexed=["hybrid-support","hybrid-direct","structural-factor"].contains(&mode.as_str())&&s.h==1&&k==1&&bb.iter().enumerate().all(|(j,b)|{
            if let [a,b]=b.terms.as_slice(){
                if let (AqPattern::Fixed(u),AqPattern::Fixed(v))=(a.pattern,b.pattern){
                    if u!=v{index.entry((u.min(v),u.max(v))).or_default().push(j);return true;}
                }
            }
            false
        });
        if indexed{route="support-index";}
        for a in &aa{
            if std::time::Instant::now()>=deadline{return None;}
            let x=aq_fixed_input(a)?;
            visited+=1;
            let p=aq_output_cube(&s,x);
            let mut matched=false;let mut unknown=false;
            let hist=if mode=="hybrid-direct"&&s.h!=0{aq_direct_hist(&s,x,deadline)}else{None};
            let all;
            let selected=if indexed{
                let output=|y:u64|s.output.iter().enumerate().fold(0u64,|z,(i,p)|
                    z|(u64::from(eval(p,x|(y<<n)))<<i));
                let u=output(0);let v=output(1);
                if u!=v{
                    index.get(&(u.min(v),u.max(v))).map(Vec::as_slice).unwrap_or(&[])
                }else{
                    all=(0..bb.len()).collect::<Vec<_>>();&all
                }
            }else{all=(0..bb.len()).collect::<Vec<_>>();&all};
            for &j in selected{
                let b=&bb[j];let q=&cubes[j];
                if std::time::Instant::now()>=deadline{return None;}
                pairs+=1;
                if (p.value^q.value)&p.mask&q.mask!=0{continue;}
                let candidate=if (mode=="structural-factor"||mode=="raw-factor")&&s.h!=0{
                    let mut work=0;let v=aq_factor_ray(&s,x,b,k,&mut work,deadline);
                    factor_work+=work;if v.is_some(){factor_hits+=1;route="factor";}else{factor_rejects+=1;}v
                }else if let Some(hist)=&hist{let v=aq_hist_ray(hist,b,k);if v.is_some(){direct_hits+=1;route="direct";}v}else{None};
                let v=if candidate.is_some(){candidate}else if mode!="wmc"&&s.h==0{
                    aq_rr_terminal(&s,x,b)
                }else if mode=="rr"{None}else{
                    let encode_start=std::time::Instant::now();
                    let opt=std::env::var("AQ_CPS_FUSED").ok().as_deref()==Some("1");
                    let (encoded,fused)=if opt{
                        match aq_overlap_fused(&s,x,b){Some(v)=>(v,true),None=>(aq_overlap(&s,x,b)?,false)}
                    }else{(aq_overlap(&s,x,b)?,false)};
                    let (c,phase,primary)=encoded;
                    println!("AQ_CPS_ENCODING fused={fused} requested={opt} primary={primary} vars={} clauses={} encode_ns={}",
                        c.vars,c.clauses.len(),encode_start.elapsed().as_nanos());
                    let mut data=format!("p cnf {} {}\n",c.vars,c.clauses.len());
                    for row in &c.clauses{for l in row{data.push_str(&format!("{l} "));}data.push_str("0\n");}
                    std::fs::write(&file,data).ok()?;
                    let rem=deadline.saturating_duration_since(std::time::Instant::now());
                    if rem.is_zero(){return None;}
                    queries+=1;
                    println!("AQ_C3_QUERY {} {} {} {}",primary,k+b.k,phase.iter().map(ToString::to_string).collect::<Vec<_>>().join(","),rem.as_millis());
                    std::io::stdout().flush().ok()?;
                    let mut answer=String::new();
                    if std::io::stdin().read_line(&mut answer).ok()?==0{return None;}
                    match answer.trim(){"PROVED"=>Some(true),"REFUTED"=>Some(false),"UNKNOWN"=>None,_=>return None}
                };
                match v{Some(true)=>{matched=true;break;},Some(false)=>{},None=>{unknown=true;}}
            }
            if !matched{
                if unknown{return None;}
                witness=Some(x);return Some(false);
            }
        }
        Some(true)
    })();
    let verdict=if std::time::Instant::now()>=deadline{"UNKNOWN"}else{
        match result{Some(true)=>"PROVED",Some(false)=>"REFUTED",None=>"UNKNOWN"}
    };
    println!("AQ_C3_NATIVE case={case} mode={mode} verdict={verdict} route={route} rejected={rejected} queries={queries} pairs={pairs} visited={visited} witness={witness:?} factor_work={factor_work} factor_hits={factor_hits} factor_rejects={factor_rejects} direct_hits={direct_hits} native_ns={}",start.elapsed().as_nanos());
}

const AQ_C3_HELDOUT:[(&str,&str,&str,&str);2]=[
    ("grover04",r####"Constants
c1 := 1
Extended Dirac
{c1 |0000000>}
"####,r####"Constants
aH := 251 / (sqrt2 ^ 16)
aL := -13 / (sqrt2 ^ 16)
Extended Dirac
{aH |0101001> + aL ∑ |i|=4, i≠0101 |i001>}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[7];
x qubits[6];

h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
h qubits[6];

x qubits[0];
x qubits[2];
ccx qubits[0], qubits[1], qubits[4];
ccx qubits[4], qubits[2], qubits[5];
cz qubits[5], qubits[3];
ccx qubits[4], qubits[2], qubits[5];
ccx qubits[0], qubits[1], qubits[4];
x qubits[0];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
ccx qubits[0], qubits[1], qubits[4];
ccx qubits[4], qubits[2], qubits[5];
cz qubits[5], qubits[3];
ccx qubits[4], qubits[2], qubits[5];
ccx qubits[0], qubits[1], qubits[4];
x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
x qubits[6];

x qubits[0];
x qubits[2];
ccx qubits[0], qubits[1], qubits[4];
ccx qubits[4], qubits[2], qubits[5];
cz qubits[5], qubits[3];
ccx qubits[4], qubits[2], qubits[5];
ccx qubits[0], qubits[1], qubits[4];
x qubits[0];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
ccx qubits[0], qubits[1], qubits[4];
ccx qubits[4], qubits[2], qubits[5];
cz qubits[5], qubits[3];
ccx qubits[4], qubits[2], qubits[5];
ccx qubits[0], qubits[1], qubits[4];
x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
x qubits[6];

x qubits[0];
x qubits[2];
ccx qubits[0], qubits[1], qubits[4];
ccx qubits[4], qubits[2], qubits[5];
cz qubits[5], qubits[3];
ccx qubits[4], qubits[2], qubits[5];
ccx qubits[0], qubits[1], qubits[4];
x qubits[0];
x qubits[2];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
ccx qubits[0], qubits[1], qubits[4];
ccx qubits[4], qubits[2], qubits[5];
cz qubits[5], qubits[3];
ccx qubits[4], qubits[2], qubits[5];
ccx qubits[0], qubits[1], qubits[4];
x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[0];
h qubits[1];
h qubits[2];
h qubits[3];
x qubits[6];

h qubits[6];
"####), // blobs 3cb06685b906e4a7da6adab65bd6b472370fe800 c5a97b5c984fb0ea92bfaa624ee41fccf875ece6 2493f92a4ae9b335b30b86d5d17aa70902402b13
    ("mogrover04",r####"Constants
c1 := 1
Extended Dirac
{c1 |s0000000> : |s|=4}
"####,r####"Constants
aH := 251 / (sqrt2 ^ 16)
aL := -13 / (sqrt2 ^ 16)
Extended Dirac
{aH |ss001> + aL ∑ |i|=4, i≠s |si001> : |s|=4}
"####,r####"OPENQASM 2.0;
include "qelib1.inc";
qreg qubits[11];
x qubits[10];

x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
h qubits[10];

cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[10];

cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[10];

cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
cx qubits[0], qubits[4];
cx qubits[1], qubits[5];
cx qubits[2], qubits[6];
cx qubits[3], qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
ccx qubits[4], qubits[5], qubits[8];
ccx qubits[8], qubits[6], qubits[9];
cz qubits[9], qubits[7];
ccx qubits[8], qubits[6], qubits[9];
ccx qubits[4], qubits[5], qubits[8];
x qubits[4];
x qubits[5];
x qubits[6];
x qubits[7];
h qubits[4];
h qubits[5];
h qubits[6];
h qubits[7];
x qubits[10];

x qubits[0];
x qubits[1];
x qubits[2];
x qubits[3];
h qubits[10];
"####), // blobs 2b1c53ee628ef52edeeb09bf0dc70f1d601f968c 5e63ffba67c329e6fcb14693122c35cd0f004728 56e26972835eb604ee7ffd005ae0f10cdd081697
];


// Predicate-level exact sign partition, independent of RR. Fixed x
// specialization is reused from the existing native symbolic engine.
// The factors are integer weights in {-1,0,1}; no amplitude IR changes.
// Unsupported phase, factor width, work or time => no result/fallback.
struct AqSignFactor { mask:u64, values:Vec<i128> }
fn aq_deposit(mut x:usize,mut mask:u64)->u64{
    let mut a=0;
    while mask!=0{let b=mask&mask.wrapping_neg();if x&1!=0{a|=b;}x>>=1;mask^=b;}
    a
}
fn aq_gather(x:u64,mut mask:u64)->usize{
    let mut a=0;let mut i=0;
    while mask!=0{let b=mask&mask.wrapping_neg();if x&b!=0{a|=1usize<<i;}i+=1;mask^=b;}
    a
}
fn aq_factor_table(mask:u64,work:&mut usize,deadline:std::time::Instant,
                   mut f:impl FnMut(u64)->Option<i128>)->Option<AqSignFactor>{
    if mask.count_ones()>12||std::time::Instant::now()>=deadline{return None;}
    let len=1usize<<mask.count_ones();
    *work=work.checked_add(len)?;
    if *work>262144{return None;}
    let mut values=Vec::with_capacity(len);
    for i in 0..len{if i%256==0&&std::time::Instant::now()>=deadline{return None;}
        values.push(f(aq_deposit(i,mask))?);}
    Some(AqSignFactor{mask,values})
}
fn aq_sign_cube(s:&Symbolic,x:u64,mask:u64,z:u64,work:&mut usize,
                deadline:std::time::Instant)->Option<i128>{
    if s.h>32||s.n+s.h>63{return None;}
    let pre=Cube{mask:(1u64<<s.n)-1,value:x};
    let mut factors=Vec::new();
    // Ignore the input-dependent common phase; it multiplies every
    // overlap term by the same unit complex number.
    for (m,k) in specialize_phase(&s.phase,pre){
        if m==0{continue;}
        if k!=4{return None;}
        let m=m>>s.n;
        factors.push(aq_factor_table(m,work,deadline,|a|Some(if a&m==m{-1}else{1}))?);
    }
    for i in 0..s.n{
        if mask>>i&1==0{continue;}
        let p:Anf=specialize_bool(&s.output[i],pre).into_iter().map(|m|m>>s.n).collect();
        let scope=p.iter().fold(0u64,|v,m|v|m);
        let want=z>>i&1!=0;
        factors.push(aq_factor_table(scope,work,deadline,|a|Some(i128::from(eval(&p,a)==want)))?);
    }
    let mut remaining=(1u64<<s.h)-1;
    let mut scalar=1i128;
    while remaining!=0{
        if std::time::Instant::now()>=deadline{return None;}
        // Greedy induced width; no source name or known verdict routing.
        let v=(0..s.h).filter(|i|remaining>>i&1!=0).min_by_key(|i|{
            let bit=1u64<<i;
            factors.iter().filter(|f|f.mask&bit!=0).fold(0u64,|a,f|a|f.mask).count_ones()
        })?;
        let bit=1u64<<v;remaining^=bit;
        let mut local=Vec::new();let mut rest=Vec::new();
        for f in factors{if f.mask&bit!=0{local.push(f);}else{rest.push(f);}}
        if local.is_empty(){scalar=scalar.checked_mul(2)?;factors=rest;continue;}
        let union=local.iter().fold(0u64,|a,f|a|f.mask);
        if union.count_ones()>12{return None;}
        let scope=union^bit;
        let cost=(1usize<<union.count_ones()).checked_mul(local.len())?;
        *work=work.checked_add(cost)?;if *work>262144{return None;}
        let factor=aq_factor_table(scope,work,deadline,|a|{
            let product=|x:u64|local.iter().try_fold(1i128,|v,f|v.checked_mul(f.values[aq_gather(x,f.mask)]));
            product(a)?.checked_add(product(a|bit)?)
        })?;
        rest.push(factor);factors=rest;
    }
    factors.iter().try_fold(scalar,|a,f|if f.mask==0{a.checked_mul(f.values[0])}else{None})
}
fn aq_factor_ray(s:&Symbolic,x:u64,b:&AqState,k:usize,work:&mut usize,
                 deadline:std::time::Instant)->Option<bool>{
    let all=(1u64<<s.n)-1;let mut sum=0i128;
    let mut cache=BTreeMap::<(u64,u64),i128>::new();
    let mut cube=|mask:u64,z:u64|->Option<i128>{
        if let Some(&a)=cache.get(&(mask,z)){return Some(a);}
        let a=aq_sign_cube(s,x,mask,z,work,deadline)?;
        cache.insert((mask,z),a);Some(a)
    };
    for t in &b.terms{
        let a=match t.pattern{
            AqPattern::Fixed(z)=>cube(all,z)?,
            AqPattern::Except{offset,width,excluded,outside}=>{
                let m=((1u64<<width)-1)<<offset;
                cube(all^m,outside)?.checked_sub(cube(all,outside|(excluded<<offset))?)?
            }
        };
        sum=sum.checked_add(a.checked_mul(i128::from(t.signed))?)?;
    }
    Some(sum.checked_mul(sum)?==1i128.checked_shl((k+b.k).try_into().ok()?)?)
}
// Strong exact residual baseline: one path histogram per input, shared
// across every candidate target. Bounded work, no WMC, no dense gate oracle.
fn aq_direct_hist(s:&Symbolic,x:u64,deadline:std::time::Instant)->Option<BTreeMap<u64,Root>>{
    if s.h>16{return None;}
    let mut hist=BTreeMap::new();
    for y in 0..1u64<<s.h{
        if y%256==0&&std::time::Instant::now()>=deadline{return None;}
        let (z,p)=path(s,x,y);let a=hist.entry(z).or_insert([0;4]);
        *a=add(*a,root(p));
    }
    Some(hist)
}
fn aq_hist_ray(hist:&BTreeMap<u64,Root>,b:&AqState,k:usize)->Option<bool>{
    let mut a=[0i128;4];
    for (&z,v) in hist{
        for t in &b.terms{if aq_match(&t.pattern,z){
            for i in 0..4{a[i]=a[i].checked_add(i128::from(v[i]).checked_mul(i128::from(t.signed))?)?;}
        }}
    }
    let [a,b0,c,d]=a;
    let real=a*a+b0*b0+c*c+d*d;
    let radical=a*b0+b0*c+c*d-a*d;
    Some(radical==0&&real==1i128.checked_shl((k+b.k).try_into().ok()?)?)
}
