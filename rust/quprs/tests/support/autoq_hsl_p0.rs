
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
    if var.len()!=1||!var.as_bytes()[0].is_ascii_lowercase()||w==0||w>3{return None;}
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
fn aq_label_support(b:&AqState,w:usize,label:u64)->bool{
    let mask=(1u64<<w)-1;
    b.terms.iter().all(|t|match t.pattern{
        AqPattern::Fixed(v)=>v&mask==label,
        AqPattern::Except{offset,outside,..}=>offset>=w&&outside&mask==label,
    })
}
fn aq_label_preserved(s:&Symbolic,w:usize)->bool{
    s.output.iter().take(w).enumerate().all(|(i,p)|*p==Anf::from([1u64<<i]))
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
        let (native_ops,n)=quprs::qasm::parse_qasm_str(src).expect("native QASM parse");
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
        assert!(aq_label_preserved(&raw,w)&&aq_label_preserved(&residual,w));
        for (label,(a,b)) in aa.iter().zip(&bb).enumerate(){
        let x=match a.terms.as_slice(){[AqTerm{pattern:AqPattern::Fixed(v),..}]=>*v,_=>panic!("fixed input only")};
        assert!(aq_label_support(a,w,label as u64)&&aq_label_support(b,w,label as u64));
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
        println!("AQ_HSL_FAMILY_ADMISSION family={family} labels={} label_bits={w} raw_and_rr_preserved=true dense_oracle=true",aa.len());
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
