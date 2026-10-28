//! Independent high-precision MPFR evaluation of solver text, diagnostic only.
//! Guards only printf rounding, NOT underlying solver error/certification.
use rug::Float;
use std::{env, fs, io::{self, Write}};

const PREC: u32 = 512;

fn dec(input: &str) -> Float {
    Float::with_val(PREC, Float::parse(input).expect("decimal"))
}

fn half_print_unit(input: &str) -> Float {
    let (mantissa, power) = input.split_once('e').or_else(|| input.split_once('E'))
        .expect("scientific count");
    if dec(mantissa).is_zero() {
        // MPFR scientific printf emits a zero mantissa only for an exact zero.
        return Float::with_val(PREC, 0);
    }
    let after_dot = mantissa.split_once('.').map(|(_, x)| x.len()).unwrap_or(0);
    let exponent: i32 = power.parse().expect("count exponent");
    dec(&format!("5e{}", exponent - after_dot as i32 - 1))
}

fn status(re_s: &str, im_s: &str, epsilon_s: &str, log2_norm: u32) -> &'static str {
    let mut r = dec(re_s);
    let mut i = dec(im_s);
    r.abs_mut();
    i.abs_mut();
    let ur = half_print_unit(re_s);
    let ui = half_print_unit(im_s);

    let mut low_r = Float::with_val(PREC, &r - &ur);
    let mut low_i = Float::with_val(PREC, &i - &ui);
    if low_r < 0 { low_r = Float::with_val(PREC, 0); }
    if low_i < 0 { low_i = Float::with_val(PREC, 0); }
    let high_r = Float::with_val(PREC, &r + &ur);
    let high_i = Float::with_val(PREC, &i + &ui);

    let mut min2 = Float::with_val(PREC, &low_r * &low_r);
    min2 += Float::with_val(PREC, &low_i * &low_i);
    min2.sqrt_mut();
    let mut max2 = Float::with_val(PREC, &high_r * &high_r);
    max2 += Float::with_val(PREC, &high_i * &high_i);
    max2.sqrt_mut();

    for _ in 0..log2_norm {
        min2 /= 2;
        max2 /= 2;
    }
    let eps = dec(epsilon_s);
    let mut threshold = Float::with_val(PREC, 1);
    threshold -= Float::with_val(PREC, &eps * &eps);
    threshold.sqrt_mut();
    if min2 > 1 {
        "unknown_overshoot"
    } else if max2 < threshold {
        "not_equivalent_printed_only"
    } else if min2 >= threshold {
        "equivalent_printed_only"
    } else {
        "unknown_print_resolution"
    }
}

fn main() {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 3, "usage: precision_probe <input-tsv> <output-tsv>");
    let input = fs::read_to_string(&args[1]).expect("read input");
    let mut output = fs::File::create(&args[2]).expect("create output");
    let mut count = 0usize;
    for line in input.lines() {
        let p: Vec<_> = line.split('\t').collect();
        assert_eq!(p.len(), 5, "invalid record");
        let normalization: u32 = p[4].parse().expect("power-of-two normalization");
        let verdict = status(p[1], p[2], p[3], normalization);
        writeln!(output, "{}\t{}", p[0], verdict).expect("write output");
        count += 1;
    }
    assert_eq!(count, 144, "expected paired fixed-fixture matrix");
    io::stdout().flush().unwrap();
    println!("RUST_MPFR_PRINTED_COUNT_DISTANCE_PROBE_PASS {count}");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn tiny_projective_distance_not_erased_by_binary64() {
        assert_eq!(
            status("9.9999999999999994746875000000000000000117e-01",
                "0.0000000000000000000000000000000000000000e+00",
                "1e-8", 0),
            "not_equivalent_printed_only"
        );
        assert_eq!(
            status("1.00000000e+00", "0.00000000e+00", "1e-8", 0),
            "unknown_print_resolution"
        );
    }
}
