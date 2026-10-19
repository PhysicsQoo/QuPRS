//! Bounded subprocess supervision for external weighted model counters.
//!
//! A separate process group/session keeps timeout cancellation from leaving
//! descendants behind. Both output pipes are drained concurrently; memory is
//! bounded even when a faulty solver produces unbounded diagnostics.
use anyhow::{anyhow, Context, Result};
use std::io::{self, Read};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

const MAX_STREAM_BYTES: usize = 1024 * 1024;
const POLL_INTERVAL: Duration = Duration::from_millis(10);
const PIPE_CLOSE_GRACE: Duration = Duration::from_millis(500);

/// Internal, typed deadline signal. Higher layers map this to the public
/// Timeout result without mistaking it for circuit inequivalence.
#[derive(Debug)]
pub(crate) struct SolverTimeout;
impl std::fmt::Display for SolverTimeout {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "SolverTimeout: subprocess deadline exceeded")
    }
}
impl std::error::Error for SolverTimeout {}

pub(crate) struct SolverOutput {
    pub status: ExitStatus,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

fn drain<R: Read>(mut pipe: R, exceeded: Arc<AtomicBool>) -> io::Result<Vec<u8>> {
    let mut kept = Vec::new();
    let mut buf = [0u8; 8192];
    loop {
        let n = pipe.read(&mut buf)?;
        if n == 0 {
            break;
        }
        let remaining = MAX_STREAM_BYTES.saturating_sub(kept.len());
        kept.extend_from_slice(&buf[..n.min(remaining)]);
        if n > remaining {
            exceeded.store(true, Ordering::Relaxed);
        }
    }
    Ok(kept)
}

fn terminate_tree(child: &mut Child) {
    #[cfg(unix)]
    {
        // CommandExt::process_group(0) places the child in a private group.
        // Kill the group rather than only its leader.
        unsafe extern "C" {
            fn kill(pid: i32, sig: i32) -> i32;
        }
        if let Ok(pgid) = i32::try_from(child.id()) {
            unsafe { kill(-pgid, 9); } // POSIX SIGKILL
        }
    }
    #[cfg(windows)]
    {
        // /T also terminates descendants; fall back to direct child.kill()
        // when taskkill is unavailable (such a failure is not silently ignored
        // by the strict descendant tests on supported runners).
        let _ = Command::new("taskkill")
            .args(["/T", "/F", "/PID", &child.id().to_string()])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    let _ = child.kill();
    let _ = child.wait();
}

pub(crate) fn run(command: &mut Command, deadline: Option<Instant>) -> Result<SolverOutput> {
    if deadline.is_some_and(|limit| Instant::now() >= limit) {
        return Err(anyhow!(SolverTimeout));
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    command.stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = command.spawn().context("SolverUnavailable: failed to spawn solver")?;
    let stdout = child.stdout.take().expect("stdout configured");
    let stderr = child.stderr.take().expect("stderr configured");
    let exceeded = Arc::new(AtomicBool::new(false));
    let out_limit = Arc::clone(&exceeded);
    let err_limit = Arc::clone(&exceeded);
    let out_handle = thread::spawn(move || drain(stdout, out_limit));
    let err_handle = thread::spawn(move || drain(stderr, err_limit));

    let status = loop {
        if exceeded.load(Ordering::Relaxed) {
            terminate_tree(&mut child);
            let _ = out_handle.join();
            let _ = err_handle.join();
            return Err(anyhow!("SolverOutputLimit: stdout/stderr exceeded 1 MiB per stream"));
        }
        if deadline.is_some_and(|limit| Instant::now() >= limit) {
            terminate_tree(&mut child);
            let _ = out_handle.join();
            let _ = err_handle.join();
            return Err(anyhow!(SolverTimeout));
        }
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => thread::sleep(POLL_INTERVAL),
            Err(error) => {
                terminate_tree(&mut child);
                let _ = out_handle.join();
                let _ = err_handle.join();
                return Err(error).context("SolverProcessError: wait failed");
            }
        }
    };

    // A child that exits but leaves grandchildren holding inherited stdout or
    // stderr open must not cause an unbounded join of the reader threads.
    let close_deadline = Instant::now() + PIPE_CLOSE_GRACE;
    while !out_handle.is_finished() || !err_handle.is_finished() {
        if Instant::now() >= close_deadline
            || deadline.is_some_and(|limit| Instant::now() >= limit)
        {
            terminate_tree(&mut child);
            let _ = out_handle.join();
            let _ = err_handle.join();
            return Err(anyhow!("SolverProcessError: output pipes not closed by descendants"));
        }
        thread::sleep(POLL_INTERVAL);
    }
    let stdout = out_handle.join()
        .map_err(|_| anyhow!("SolverProcessError: stdout reader panicked"))?
        .context("SolverProcessError: stdout read failed")?;
    let stderr = err_handle.join()
        .map_err(|_| anyhow!("SolverProcessError: stderr reader panicked"))?
        .context("SolverProcessError: stderr read failed")?;
    if exceeded.load(Ordering::Relaxed) {
        return Err(anyhow!("SolverOutputLimit: stdout/stderr exceeded 1 MiB per stream"));
    }
    Ok(SolverOutput { status, stdout, stderr })
}

#[cfg(test)]
#[cfg(unix)]
mod tests {
    use super::*;

    #[test]
    fn hanging_child_expires_and_is_reaped() {
        // Exercise a genuinely hung direct child; shell descendants and
        // inherited pipe handles are covered independently below. This keeps
        // process termination separate from shell execution details on Darwin.
        let mut cmd = Command::new("sleep");
        cmd.arg("5");
        let before = Instant::now();
        let err = run(&mut cmd, Some(before + Duration::from_millis(120)))
            .err().expect("hang must time out");
        assert!(err.to_string().contains("SolverTimeout"), "{err:#}");
        assert!(before.elapsed() < Duration::from_secs(3));
    }

    #[test]
    fn both_pipes_drain_and_failure_status_is_preserved() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "echo ok; echo failed >&2; exit 7"]);
        let result = run(&mut cmd, Some(Instant::now() + Duration::from_secs(2))).unwrap();
        assert_eq!(result.status.code(), Some(7));
        assert!(result.stdout.starts_with(b"ok"));
        assert!(result.stderr.starts_with(b"failed"));
    }

    #[test]
    fn oversized_stdout_stops_solver_early() {
        // Emit a definite 2 MiB payload through the pipe in a few writes.
        // A shell printf loop is CPU/scheduler dependent on macOS Intel and
        // can time out before ever producing the 1 MiB that this test asserts.
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "dd if=/dev/zero bs=8192 count=256 2>/dev/null; sleep 5"]);
        let err = run(&mut cmd, Some(Instant::now() + Duration::from_secs(3)))
            .err().expect("unbounded output must be rejected");
        assert!(err.to_string().contains("SolverOutputLimit"), "{err:#}");
    }

    fn still_executing(pid: u32) -> bool {
        // POSIX 'ps' works on both Darwin and Linux. A zombie is no longer
        // executing; its final reaping belongs to its adoptive parent.
        let result = Command::new("ps")
            .args(["-p", &pid.to_string(), "-o", "stat="])
            .output()
            .expect("ps must be available on supported POSIX runners");
        if !result.status.success() {
            return false;
        }
        let output = String::from_utf8_lossy(&result.stdout);
        let state = output.trim();
        !state.is_empty() && !state.starts_with('Z')
    }

    fn assert_all_stopped(pids: &[u32]) {
        let deadline = Instant::now() + Duration::from_secs(3);
        loop {
            let active: Vec<u32> = pids.iter().copied().filter(|p| still_executing(*p)).collect();
            if active.is_empty() {
                return;
            }
            if Instant::now() >= deadline {
                panic!("live solver descendants after process-group cancellation: {active:?}");
            }
            thread::sleep(Duration::from_millis(40));
        }
    }

    #[test]
    fn posix_timeout_kills_direct_child_and_grandchild() {
        use std::time::{SystemTime, UNIX_EPOCH};
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH).unwrap().as_nanos();
        let marker = std::env::temp_dir().join(format!(
            "quprs-process-tree-{}-{suffix}.pid", std::process::id()
        ));
        let mut cmd = Command::new("sh");
        // Both the direct solver and background process inherit the fresh
        // process group created by solver_process::run.
        cmd.args([
            "-c",
            "sleep 30 & echo \"$$ $!\" > \"$1\"; wait",
            "quprs-test",
            marker.to_str().expect("UTF-8 temporary directory"),
        ]);
        let begin = Instant::now();
        let result = run(&mut cmd, Some(begin + Duration::from_secs(3)));
        let err = result.err().expect("hung process tree must time out");
        assert!(err.downcast_ref::<SolverTimeout>().is_some(), "{err:#}");
        let pids: Vec<u32> = std::fs::read_to_string(&marker)
            .expect("solver must record its own PID and grandchild PID")
            .split_whitespace()
            .map(|x| x.parse().unwrap())
            .collect();
        let _ = std::fs::remove_file(&marker);
        assert_eq!(pids.len(), 2);
        assert_all_stopped(&pids);
    }

    #[test]
    fn descendants_holding_pipes_cannot_hang_parent() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "sleep 5 & exit 0"]);
        let before = Instant::now();
        let err = run(&mut cmd, Some(before + Duration::from_secs(2)))
            .err().expect("unclosed inherited pipes must be rejected");
        assert!(err.to_string().contains("SolverProcessError"), "{err:#}");
        assert!(before.elapsed() < Duration::from_secs(3));
    }
}
