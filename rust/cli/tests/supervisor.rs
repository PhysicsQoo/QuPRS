//! Scope and semantics of the experimental CLI outer supervisor.
//! The test-only hold runs only in debug builds and strictly before QASM I/O.
use std::{fs, process::Command, time::Duration};

fn cli() -> &'static str { env!("CARGO_BIN_EXE_QuPRS_cli") }

fn fixture() -> tempfile::NamedTempFile {
    use std::io::Write;
    let mut file = tempfile::NamedTempFile::new().unwrap();
    writeln!(file, "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\nh q[0];").unwrap();
    file
}
#[test]
fn dual_circuit_worker_returns_only_complete_equivalence() {
    let file = fixture();
    let result = Command::new(cli())
        .arg(file.path()).arg(file.path())
        .args(["--method", "reduction-rules", "--quiet", "--timeout", "20"])
        .output().unwrap();
    assert!(result.status.success(), "{:?}", result);
    assert!(String::from_utf8_lossy(&result.stdout).trim().contains("equivalent"),
        "{:?}", result);
}

#[test]
fn single_circuit_has_a_supervised_success_path() {
    let file = fixture();
    let result = Command::new(cli()).arg(file.path())
        .args(["--timeout", "20", "--quiet"]).output().unwrap();
    assert!(result.status.success(), "{:?}", result);
    assert!(String::from_utf8_lossy(&result.stdout).contains("Reduced PathSum State"));
}

#[test]
fn failed_worker_cannot_emit_a_partial_success_verdict() {
    let result = Command::new(cli()).arg("/path/not-found/qoo156.qasm")
        .args(["--quiet", "--timeout", "10"]).output().unwrap();
    assert!(!result.status.success());
    assert!(result.stdout.is_empty(), "partial output leaked: {:?}", result);
    assert!(String::from_utf8_lossy(&result.stderr).contains("WorkerFailed"));
}

#[test]
fn supervisor_timeout_includes_qasm_read_and_both_cli_modes() {
    for dual in [false, true] {
        let file = fixture();
        let mut cmd = Command::new(cli());
        cmd.arg(file.path());
        if dual { cmd.arg(file.path()); }
        let result = cmd.args(["--quiet", "--timeout", "1"])
            .env("QUPRS_CLI_TEST_HOLD_MS", "1800")
            .output().unwrap();
        assert_eq!(result.status.code(), Some(124), "{:?}", result);
        assert_eq!(String::from_utf8_lossy(&result.stdout).trim(), "Timeout");
    }
}

#[cfg(unix)]
#[test]
fn explicit_address_space_cap_does_not_fail_open() {
    let file = fixture();
    let result = Command::new(cli()).arg(file.path())
        .args(["--max-address-space-mib", "1", "--quiet", "--timeout", "10"])
        .output().unwrap();
    assert!(!result.status.success(), "worker ignored 1 MiB RLIMIT_AS");
    assert!(!String::from_utf8_lossy(&result.stdout).contains("EQUIVALENT"));
}

#[test]
fn resource_limits_reject_zero() {
    let file = fixture();
    for flag in ["--max-address-space-mib", "--max-memory-mib"] {
        let result = Command::new(cli()).arg(file.path())
            .args([flag, "0", "--quiet"]).output().unwrap();
        assert!(!result.status.success());
        assert!(result.stdout.is_empty());
    }
}

#[cfg(target_os = "linux")]
#[test]
fn physical_memory_cap_never_silently_falls_back_to_unlimited() {
    let file = fixture();
    let result = Command::new(cli()).arg(file.path())
        .args(["--max-memory-mib", "1", "--quiet", "--timeout", "10"])
        .output().unwrap();
    assert!(!result.status.success(),
        "1 MiB memory.max cannot complete a full Rust worker safely");
    assert!(!String::from_utf8_lossy(&result.stdout).contains("equivalent"));
}


#[cfg(target_os = "linux")]
#[test]
fn delegated_cgroup_physically_enforces_oom_or_records_not_admitted() {
    // A successful zero-permission test is NOT memory enforcement evidence.
    // Only the explicit OOM event + typed failure may claim admission.
    let source = fixture();
    let result = Command::new(cli()).arg(source.path())
        .args(["--max-memory-mib", "64", "--timeout", "15", "--quiet"])
        .env("QUPRS_CLI_TEST_ALLOC_MIB", "192")
        .output().expect("spawn real CLI with bounded 64 MiB cgroup");
    let stderr = String::from_utf8_lossy(&result.stderr);
    if stderr.contains("no delegated writable memory cgroup")
        || stderr.contains("memory cgroup delegation unavailable")
        || stderr.contains("cgroup v2 is unavailable")
        || stderr.contains("configure physical-memory limit")
        || stderr.contains("configure group OOM handling")
    {
        println!("QOO156_MEMORY_POSITIVE_NOT_ADMITTED: host lacks delegated writable cgroup v2");
        assert!(!result.status.success());
        assert!(result.stdout.is_empty(), "no fake successful verifier result");
        return;
    }
    assert_eq!(result.status.code(), Some(125),
        "cgroup resource failure must have typed exit 125, not a verdict: {stderr}");
    assert!(stderr.contains("MemoryLimitExceeded"),
        "no positive cgroup memory.events OOM witness: {stderr}");
    assert!(result.stdout.is_empty(), "a killed worker cannot emit partial EQ/NEQ");
    println!("QOO156_MEMORY_POSITIVE_ADMITTED: memory.max and memory.events verified");
}


#[cfg(target_os = "linux")]
#[test]
fn worker_exits_but_supervisor_reaps_separate_process_group_solver() {
    let source = fixture();
    let pid_file = tempfile::NamedTempFile::new().unwrap();
    let result = Command::new(cli()).arg(source.path())
        .args(["--quiet", "--timeout", "5"])
        .env("QUPRS_CLI_TEST_ORPHAN_PIDFILE", pid_file.path())
        .output().unwrap();
    assert!(!result.status.success(), "worker intentionally exits with failure");
    let pid: u32 = std::fs::read_to_string(pid_file.path())
        .unwrap().trim().parse().unwrap();
    for _ in 0..40 {
        let stat = std::fs::read_to_string(format!("/proc/{pid}/stat"));
        match stat {
            Err(_) => return,
            Ok(info) => {
                let state = info.rsplit_once(") ").unwrap().1.chars().next().unwrap();
                if state == 'Z' { return; }
            }
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    panic!("detached solver PID {pid} remained active after supervisor cleanup");
}
