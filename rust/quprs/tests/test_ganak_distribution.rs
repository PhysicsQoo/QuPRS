// The shared distribution module is included as a source module here. It
// refers to crate::solver_process, so the integration test needs the same
// companion module as the library and the build script.
// This integration test compiles solver_process.rs into its own crate.
// Match build.rs: the runtime timing hooks are intentionally no-ops here;
// the real opt-in recorder belongs only to the pathsum library crate.
// This file is a separate integration-test crate; the included source modules
// refer to the crate-local clock, just as they do in build.rs.
mod clock {
    pub use std::time::{Instant, Duration, SystemTime, UNIX_EPOCH};
}
mod diagnostics {
    pub(crate) fn span(_stage: &'static str) -> Option<()> { None }
    pub(crate) fn child_spawned() {}
}
#[path = "../src/solver_process.rs"]
mod solver_process;

#[path = "../src/ganak_distribution.rs"]
mod distribution;

#[test]
fn stale_or_tampered_binary_is_rejected() {
    assert!(distribution::validate(b"obsolete cached binary", "linux", "x86_64").is_err());
}

#[test]
fn target_headers_are_checked() {
    let mut elf = [0u8; 64];
    elf[..6].copy_from_slice(b"\x7fELF\x02\x01");
    elf[18] = 62;
    assert!(distribution::architecture(&elf, "linux", "x86_64"));
    assert!(!distribution::architecture(&elf, "linux", "aarch64"));
    assert!(!distribution::architecture(&elf, "macos", "x86_64"));
    assert!(distribution::asset("linux", "riscv64").is_err());
}

#[test]
fn packaged_binary_matches_the_pinned_release() {
    let path = std::path::Path::new(env!("GANAK_BIN_PATH"));
    let info = distribution::diagnostics(path, false).unwrap();
    assert!(info.contains("pinned=true"));
}

#[test]
fn native_clock_elapsed_and_deadline_contract() {
    // web_time re-exports std::time::Instant on native targets.
    let start: std::time::Instant = clock::Instant::now();
    let already_expired = start.checked_sub(clock::Duration::from_millis(1)).unwrap();
    assert!(clock::Instant::now() >= already_expired);
    let future = start.checked_add(clock::Duration::from_secs(1)).unwrap();
    assert!(future > start);
    std::thread::sleep(clock::Duration::from_millis(2));
    assert!(start.elapsed() >= clock::Duration::from_millis(1));
}

#[cfg(unix)]
#[test]
fn native_solver_deadline_kills_real_hanging_process() {
    let mut cmd = std::process::Command::new("sleep");
    cmd.arg("5");
    let start = clock::Instant::now();
    let err = solver_process::run(
        &mut cmd,
        Some(start.checked_add(clock::Duration::from_millis(120)).unwrap()),
    )
    .err()
    .expect("hanging child must expire and be reaped");
    assert!(err.to_string().contains("SolverTimeout"), "{err:#}");
    assert!(start.elapsed() < clock::Duration::from_secs(3));
}
