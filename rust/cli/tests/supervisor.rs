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
fn wait_for_canceled_cli(mut child: std::process::Child) -> std::process::Output {
    for _ in 0..100 {
        if child.try_wait().unwrap().is_some() {
            return child.wait_with_output().unwrap();
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    let _ = child.kill();
    let _ = child.wait();
    panic!("supervisor did not exit within 5s after cancellation");
}

#[cfg(unix)]
fn pid_is_gone_or_zombie(pid: u32) -> bool {
    #[cfg(target_os = "linux")]
    {
        let stat = std::fs::read_to_string(format!("/proc/{pid}/stat"));
        return match stat {
            Err(_) => true,
            Ok(data) => data.rsplit_once(") ").is_some_and(|(_, tail)| tail.starts_with('Z')),
        };
    }
    #[cfg(not(target_os = "linux"))]
    {
        let output = Command::new("ps").args(["-p", &pid.to_string(), "-o", "stat="])
            .output().unwrap();
        if !output.status.success() || output.stdout.is_empty() {
            return true;
        }
        String::from_utf8_lossy(&output.stdout).trim_start().starts_with('Z')
    }
}

#[cfg(unix)]
#[test]
fn supervisor_sigint_sigterm_cancels_worker_and_preserves_empty_science_stdout() {
    let file = fixture();
    for signal in [libc::SIGINT, libc::SIGTERM] {
        let child = Command::new(cli()).arg(file.path())
            .args(["--quiet", "--timeout", "20"])
            .env("QUPRS_CLI_TEST_HOLD_MS", "6000")
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn().unwrap();
        std::thread::sleep(Duration::from_millis(500));
        assert_eq!(unsafe { libc::kill(child.id() as i32, signal) }, 0);
        let output = wait_for_canceled_cli(child);
        assert_eq!(output.status.code(), Some(128 + signal),
            "signal cancellation was not typed: {output:?}");
        assert!(output.stdout.is_empty(), "partial science stdout escaped: {output:?}");
        assert!(String::from_utf8_lossy(&output.stderr).contains("CancelledBySignal"),
            "signal cancellation not reported: {output:?}");
    }
}

#[cfg(unix)]
#[test]
fn signal_cancellation_kills_worker_detached_process_group_helper() {
    let file = fixture();
    let pidfile = tempfile::NamedTempFile::new().unwrap();
    let child = Command::new(cli()).arg(file.path())
        .args(["--quiet", "--timeout", "20"])
        .env("QUPRS_CLI_TEST_DETACHED_PIDFILE", pidfile.path())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn().unwrap();
    let helper: u32 = (0..80).find_map(|_| {
        if let Ok(data) = fs::read_to_string(pidfile.path()) {
            if let Ok(pid) = data.trim().parse::<u32>() {
                return Some(pid);
            }
        }
        std::thread::sleep(Duration::from_millis(50));
        None
    }).expect("debug worker must write genuine detached PID before parent cancel");
    assert!(!pid_is_gone_or_zombie(helper), "detached helper was never alive");
    assert_eq!(unsafe { libc::kill(child.id() as i32, libc::SIGTERM) }, 0);
    let output = wait_for_canceled_cli(child);
    assert_eq!(output.status.code(), Some(143), "{output:?}");
    assert!(output.stdout.is_empty(), "{output:?}");
    for _ in 0..50 {
        if pid_is_gone_or_zombie(helper) { return; }
        std::thread::sleep(Duration::from_millis(40));
    }
    unsafe { libc::kill(helper as libc::pid_t, libc::SIGKILL); }
    panic!("detached helper pid {helper} survived supervisor SIGTERM cleanup");
}

#[cfg(target_os = "linux")]
#[test]
fn supervisor_sigkill_triggers_worker_parent_death_signal() {
    let file = fixture();
    let pidfile = tempfile::NamedTempFile::new().unwrap();
    let mut child = Command::new(cli()).arg(file.path())
        .args(["--quiet", "--timeout", "20"])
        .env("QUPRS_CLI_TEST_WORKER_PIDFILE", pidfile.path())
        .env("QUPRS_CLI_TEST_HOLD_MS", "6000")
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn().unwrap();
    let worker: u32 = (0..80).find_map(|_| {
        if let Ok(data) = fs::read_to_string(pidfile.path()) {
            if let Ok(pid) = data.trim().parse::<u32>() {
                return Some(pid);
            }
        }
        std::thread::sleep(Duration::from_millis(50));
        None
    }).expect("worker PID witness must be produced before supervisor SIGKILL");
    assert!(!pid_is_gone_or_zombie(worker), "worker must be alive before SIGKILL");
    assert_eq!(unsafe { libc::kill(child.id() as i32, libc::SIGKILL) }, 0);
    let _ = child.wait().unwrap();
    for _ in 0..80 {
        if pid_is_gone_or_zombie(worker) { return; }
        std::thread::sleep(Duration::from_millis(40));
    }
    unsafe { libc::kill(worker as libc::pid_t, libc::SIGKILL); }
    panic!("worker PID {worker} survived abrupt supervisor death");
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

#[test]
fn stdout_or_stderr_flood_never_publishes_scientific_output() {
    for stream in ["stdout", "stderr"] {
        let file = fixture();
        let result = Command::new(cli()).arg(file.path())
            .args(["--quiet", "--timeout", "10"])
            .env("QUPRS_CLI_TEST_FLOOD_STREAM", stream)
            .output().unwrap();
        assert_eq!(result.status.code(), Some(125),
            "expected a bounded output failure for {stream}: {:?}", result);
        assert!(result.stdout.is_empty(),
            "uncommitted worker output escaped on {stream}: {:?}", result);
        assert!(String::from_utf8_lossy(&result.stderr).contains("WorkerOutputLimitExceeded"),
            "bounded failure must be explicit for {stream}: {:?}", result);
    }
}

#[test]
fn direct_internal_worker_flag_is_refused_without_supervisor_context() {
    let file = fixture();
    let result = Command::new(cli()).arg(file.path())
        .args(["--__quprs-worker", "--quiet", "--timeout", "1"])
        .env_remove("QUPRS_CLI_SUPERVISOR_PID")
        .output().unwrap();
    assert!(!result.status.success(), "public bypass unexpectedly succeeded");
    assert!(result.stdout.is_empty(), "worker bypass leaked science output");
    assert!(String::from_utf8_lossy(&result.stderr).contains("InvalidWorkerLaunch"));
}

#[cfg(unix)]
#[test]
fn forged_supervisor_pid_without_inherited_pipe_is_refused() {
    let file = fixture();
    // A forged environment variable alone is not a valid launch witness.
    let result = Command::new(cli()).arg(file.path())
        .args(["--__quprs-worker", "--quiet"])
        .env("QUPRS_CLI_SUPERVISOR_PID", std::process::id().to_string())
        .output().unwrap();
    assert!(!result.status.success(), "worker accepted no control pipe");
    assert!(result.stdout.is_empty());
    assert!(String::from_utf8_lossy(&result.stderr).contains("InvalidWorkerLaunch"));
}

#[cfg(unix)]
#[test]
fn inherited_output_pipe_cannot_bypass_request_deadline_or_publish_success() {
    // The legitimate worker finishes a one-qubit circuit, while a spawned
    // child retains its output descriptors. Before CaptureFinished events,
    // the supervisor could block unboundedly when joining its readers.
    let file = fixture();
    let started = std::time::Instant::now();
    let result = Command::new(cli()).arg(file.path())
        .args(["--quiet", "--timeout", "1"])
        .env("QUPRS_CLI_TEST_INHERIT_OUTPUT_SECS", "9")
        .output().expect("bounded child-output-pipe witness");
    assert_eq!(result.status.code(), Some(124), "unexpected result: {:?}", result);
    assert_eq!(String::from_utf8_lossy(&result.stdout).trim(), "Timeout",
        "no partial scientific success may escape");
    assert!(started.elapsed() < Duration::from_secs(7),
        "timeout hung while readers waited for an inherited pipe: {:?}",
        started.elapsed());
}
