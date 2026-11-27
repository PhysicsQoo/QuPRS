//! Research reader: reuse the production printed-count parser and midpoint classifier.
use anyhow::{ensure,Result};
use num_traits::{Signed,ToPrimitive,Zero};
use quprs::precision_count::{parse_stdout,observed_distance_verdict,PrintedVerdict};
fn main()->Result<()> {
    let a:Vec<_>=std::env::args().collect();
    ensure!(a.len()==3,"stdout-file normalization-twice-log2");
    let count=parse_stdout(&std::fs::read_to_string(&a[1])?)?;
    let k:i32=a[2].parse()?;
    let verdict=match observed_distance_verdict(&count,k,"1e-8")? {
        PrintedVerdict::NotEquivalent=>"not_equivalent",
        PrintedVerdict::Equivalent=>{
            let scale=count.real.abs()+count.imag.abs();
            if scale.is_zero() {"unknown"} else {
                match ((&count.real/&scale).to_f64(),(&count.imag/&scale).to_f64()) {
                    (Some(x),Some(y)) if x.is_finite()&&y.is_finite()=>{
                        if y.atan2(x).abs()<1e-8 {"equivalent"} else {"equivalent*"}
                    }
                    _=>"unknown",
                }
            }
        }
        _=>"unknown",
    };
    println!("{}\t{}\t{}\t{}",count.real,count.imag,verdict,count.format_name);
    Ok(())
}
