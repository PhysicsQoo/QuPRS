//! Research-only Rust MPFR source-phase → complex CNF weight transport.
//!
//! Input: label, positive CNF variable, c_num, c_den, rad_num, rad_den,
//! precision bits (TSV). The angle is 2*pi*c + 2*rad in exact source units.
//! No source-angle float conversion. Output is decimal real/imag for native
//! GPMC/Ganak experiments. This is not a Solver arithmetic certificate.
use rug::{float::Constant, Float};
use std::{env, fs, io::{BufWriter, Write}};

fn fraction(numerator: &str, denominator: &str, bits: u32) -> Float {
    let mut n = Float::with_val(bits, Float::parse(numerator).expect("numerator"));
    let d = Float::with_val(bits, Float::parse(denominator).expect("denominator"));
    assert!(!d.is_zero(), "zero source denominator");
    n /= d;
    n
}

fn phase_weight(
    cn: &str, cd: &str, rn: &str, rd: &str, bits: u32,
) -> (Float, Float) {
    let mut angle = Float::with_val(bits, Constant::Pi);
    angle *= fraction(cn, cd, bits);
    angle *= 2;
    let mut radians = fraction(rn, rd, bits);
    radians *= 2;
    angle += radians;
    let mut re = angle.clone();
    re.cos_mut();
    angle.sin_mut();
    (re, angle)
}

fn main() {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 3, "usage: phase_weight_mpfr input.tsv output.tsv");
    let input = fs::read_to_string(&args[1]).expect("input TSV");
    let mut output = BufWriter::new(fs::File::create(&args[2]).expect("output TSV"));
    let mut n = 0;
    for row in input.lines() {
        let cols: Vec<_> = row.split('\t').collect();
        assert_eq!(cols.len(), 7, "invalid source-phase row");
        let bits: u32 = cols[6].parse().expect("precision");
        assert!(bits == 128 || bits == 256, "only bounded MPFR bits");
        let (real, imag) = phase_weight(cols[2],cols[3],cols[4],cols[5],bits);
        let digits = if bits == 128 { 45 } else { 85 };
        writeln!(output,"{}\t{}\t{}\t{}\t{}",
            cols[0], cols[1], bits,
            real.to_string_radix(10,Some(digits)),
            imag.to_string_radix(10,Some(digits))
        ).expect("output weight");
        n += 1;
    }
    output.flush().unwrap();
    assert_eq!(n, 16, "four source cases x two phase weights x two precisions");
    println!("NATIVE_RUST_MPFR_WEIGHT_PASS {n}");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sub_float_source_difference_survives_as_mpfr_phase() {
        let (a_re,a_im)=phase_weight(
            "0","1","1","100000000",256,
        );
        let (b_re,b_im)=phase_weight(
            "0","1","20000000000000000000001",
            "2000000000000000000000000000000",256,
        );
        assert!(a_re != b_re || a_im != b_im);
        let (re,im)=phase_weight("0","1","1","100000000",128);
        assert!(re > 0 && im > 0);
    }
}
