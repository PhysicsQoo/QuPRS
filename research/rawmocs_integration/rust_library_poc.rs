//! R1 bounded release-pinned Rust library boundary, not a production adapter.
use anyhow::{ensure, Context, Result};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::Signed;
use quprs::{PathSum, PhaseCoeff, Rational, wmc::WmcManager};
use quprs::precision_count::{parse_rawmocs_stdout, parse_stdout};
use rawmocs_mpfr::{solve_text, solve_text_cancellable, CancellationToken, FailureKind, MpfrBinary, Precision, SolveOptions};
use std::{fs, path::Path, process::Command, time::Instant};

fn binary(v: MpfrBinary, bits: u32) -> Result<Q> {
    ensure!(v.precision_bits == bits && v.exponent2.unsigned_abs() <= 16384, "binary range");
    let n: BigInt = v.significand.parse()?;
    let shift = v.exponent2.unsigned_abs() as usize;
    Ok(if v.exponent2 >= 0 { Q::from_integer(n << shift) } else { Q::new(n, BigInt::from(1) << shift) })
}

fn close(a: &Q, b: &Q, eps: &Q) -> bool {
    (a-b).abs() <= *eps
}

fn compare(case: &str, cnf: &str, expected: Option<(bool, i32, i32)>, precision: Precision, root: &Path, gpmc: &Path) -> Result<()> {
    let digits = precision.digits();
    let opts = SolveOptions { precision, timeout_ms: Some(5000), ..Default::default() };
    let start = Instant::now();
    let native = solve_text(cnf, opts)?;
    let elapsed = start.elapsed().as_nanos();
    ensure!(native.precision == precision, "precision drift");
    // The CLI-shaped string is only a compatibility oracle for the existing
    // printed-count parser, not a transport: no process or file in solve_text.
    let status = if native.sat { "SATISFIABLE" } else { "UNSATISFIABLE" };
    let (sat, count) = parse_rawmocs_stdout(&format!("s {status}\nc r mpfr {} {}\n",native.real,native.imag))?;
    ensure!(sat == native.sat);
    let rb = binary(native.real_mpfr().binary(), precision.bits())?;
    let ib = binary(native.imag_mpfr().binary(), precision.bits())?;
    ensure!(close(&rb, &count.real, &count.real_half_unit), "real binary/decimal drift");
    ensure!(close(&ib, &count.imag, &count.imag_half_unit), "imag binary/decimal drift");
    if let Some((s,r,i)) = expected {
        ensure!(sat == s && rb == Q::from_integer(r.into()) && ib == Q::from_integer(i.into()), "independent exact fixture mismatch");
    }
    let stem = root.join(format!("{case}-{digits}"));
    let path = stem.with_extension("cnf");
    fs::write(&path, cnf)?;
    // Only the GPMC comparator uses a file and external executable.
    let output = Command::new("timeout").arg("10s").arg(gpmc).arg("-mode=1")
        .arg(format!("-prec={digits}")).arg(&path).output()?;
    fs::write(stem.with_extension("stdout"), &output.stdout)?;
    fs::write(stem.with_extension("stderr"), &output.stderr)?;
    ensure!(output.status.success(), "GPMC failed");
    let stdout = std::str::from_utf8(&output.stdout)?;
    let reported: Vec<_> = stdout.lines().filter_map(|l|l.strip_prefix("c o precision ")).collect();
    // GPMC may omit MPFR metadata only for an analytic UNSAT zero.
    let reference = parse_stdout(stdout)?;
    ensure!((reported.len()==1 && reported[0].trim().parse::<u32>()? == digits)
        || (case=="unsat" && reported.is_empty() && reference.real == Q::from_integer(0.into()) && reference.imag == Q::from_integer(0.into())), "GPMC precision mismatch");
    let statuses: Vec<_> = stdout.lines().filter(|l|l.starts_with("s ")).collect();
    ensure!(statuses == [format!("s {status}").as_str()], "GPMC SAT drift");
    let eps = Q::new(BigInt::from(1), BigInt::from(10).pow(digits-5));
    ensure!(close(&count.real,&reference.real,&eps) && close(&count.imag,&reference.imag,&eps), "same-CNF count mismatch");
    println!("R1_CASE {case} digits={digits} bits={} sat={sat} route={} native_wall_ns={elapsed} core_ns={} re={} im={}",precision.bits(),native.route.as_str(),native.solve_ns,native.real,native.imag);
    Ok(())
}

fn main() -> Result<()> {
    let root = std::env::var("R1_EVIDENCE").context("R1_EVIDENCE")?;
    let root = Path::new(&root);
    fs::create_dir_all(root)?;
    let gpmc = std::env::var("QUPRS_GPMC_PATH")?;
    let gpmc = Path::new(&gpmc);
    ensure!(gpmc.is_absolute() && gpmc.is_file(), "pinned GPMC required");
    let complex = "p cnf 1 0\nc t wmc\nc p weight 1 -2 3 0\nc p weight -1 1 -1 0\n";
    let zero = "p cnf 1 0\nc t wmc\nc p weight 1 1 0 0\nc p weight -1 -1 0 0\n";
    let unsat = "p cnf 1 2\nc t wmc\n1 0\n-1 0\n";
    let mut ps = PathSum::new(1);
    ps.p.add_term(vec![0], PhaseCoeff::new_constant(Rational::new(1,8)));
    let mut manager = WmcManager::new(&ps);
    manager.enable_precise_gpmc_weights(256);
    manager.encode_trace(&ps)?;
    let cnf = manager.try_to_dimacs_string("gpmc")?;
    ensure!(cnf == manager.try_to_dimacs_string("rawmocs")?, "CNF grammar drift");
    for p in [Precision::Digits30, Precision::Digits130] {
        compare("signed-complex", complex, Some((true,-1,2)), p, root, gpmc)?;
        compare("sat-zero", zero, Some((true,0,0)), p, root, gpmc)?;
        compare("unsat", unsat, Some((false,0,0)), p, root, gpmc)?;
        compare("quprs-phase-trace", &cnf, None, p, root, gpmc)?;
    }
    let opts = SolveOptions { timeout_ms: Some(5000), ..Default::default() };
    ensure!(solve_text("not a CNF\n",opts).unwrap_err().kind == FailureKind::InvalidInput, "malformed input category");
    let token = CancellationToken::new();
    token.cancel();
    ensure!(solve_text_cancellable(complex,opts,&token).unwrap_err().kind == FailureKind::Cancelled);
    let fresh = CancellationToken::new();
    ensure!(solve_text_cancellable(complex,opts,&fresh)?.sat, "reentry failed");
    println!("R1_DIRECT_LIBRARY_BOUNDARY_PASS cases=8 failures=2 reentry=1");
    Ok(())
}
