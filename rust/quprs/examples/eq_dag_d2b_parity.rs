//! Parse frozen residuals into actual native PathSum; compare canonical bytes.
use anyhow::{ensure,Context,Result};
use quprs::{PathSum,PhaseCoeff,Rational,wmc::WmcManager};
use num_rational::BigRational;
use std::{fs,path::Path,time::Instant};
fn vars(s:&str)->Result<Vec<u32>> {
    let v=s.strip_prefix('[').and_then(|s|s.strip_suffix(']')).context("variable list")?;
    if v.trim().is_empty(){return Ok(vec![])}
    Ok(v.split(',').map(|s|s.trim().parse()).collect::<std::result::Result<_,_>>()?)
}
fn rad(s:&str)->Result<Option<BigRational>> {
    if s=="None"{return Ok(None)}
    let s=s.strip_prefix("Some(Ratio { numer: ").and_then(|s|s.strip_suffix(" })")).context("radian grammar")?;
    let (n,d)=s.split_once(", denom: ").context("radian denominator")?;
    Ok(Some(format!("{n}/{d}").parse()?))
}
fn load(path:&Path)->Result<PathSum> {
    let txt=fs::read_to_string(path)?;
    let n:usize=txt.lines().next().and_then(|l|l.strip_prefix("n\t")).context("n")?.parse()?;
    let mut ps=PathSum::new(n);
    ps.p.terms.clear();for f in &mut ps.f.functions{f.clear();}
    for l in txt.lines(){
        let a:Vec<_>=l.split('\t').collect();
        match a[0]{
            "vars"=>{ps.v.path_vars=vars(a[1])?.into_iter().collect();}
            "continuous"=>{ps.v.continuous_vars=vars(a[1])?.into_iter().collect();}
            "p"=>{ensure!(a.len()==6&&a[5]=="{}","unsupported source phase");
                let m=vars(a[1])?;let c=PhaseCoeff{constant:Rational::new(a[2].parse()?,a[3].parse()?),radians:rad(a[4])?,symbols:Default::default()};
                ensure!(ps.p.terms.insert(m,c).is_none(),"duplicate monomial");}
            "f"=>{let i:usize=a[1].parse()?;ensure!(ps.f.functions[i].insert(vars(a[2])?),"duplicate output term");}
            "n"|"h"|"output"|"rr_approximate"|"rr_tol_bits"=>{},
            _=>anyhow::bail!("unknown residual field"),
        }
    }
    Ok(ps)
}
fn main()->Result<()>{
    let args:Vec<_>=std::env::args().collect();ensure!(args.len()==4,"residual.tsv expected.cnf output.cnf");
    let ps=load(Path::new(&args[1]))?;
    let start=Instant::now();
    let (text,work,bits)=WmcManager::research_parity_cnf(&ps,1e-8,3_000_000)?;
    let elapsed=start.elapsed().as_secs_f64();
    fs::write(&args[3],&text)?;
    ensure!(text.as_bytes()==fs::read(&args[2])?.as_slice(),"E1e byte parity mismatch");
    println!("D2B_NATIVE_PASS terms={} work={work} bits={bits} seconds={elapsed:.9}",ps.p.terms.len());
    Ok(())
}
