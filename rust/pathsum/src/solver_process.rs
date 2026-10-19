//! POSIX solver subprocess lifecycle supervisor.
//!
//! stdout/stderr are redirected to private temporary files instead of pipes:
//! a detached descendant holding an inherited descriptor cannot stall cleanup
//! in a blocking reader thread. Disk growth is checked between polls and may
//! temporarily exceed the 1 MiB per-stream in-memory result limit.
use anyhow::{anyhow, Context, Result};
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const MAX_STREAM_BYTES: usize = 1024 * 1024;
const POLL_INTERVAL: Duration = Duration::from_millis(10);
static NEXT_CAPTURE_ID: AtomicU64 = AtomicU64::new(0);

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

/// Only this scope owns the temporary output file and removes its directory
/// entry on all return paths, including spawn, wait, deadline and parse errors.
struct CaptureFile {
    path: PathBuf,
    file: File,
}
impl CaptureFile {
    fn new(stream: &str) -> Result<Self> {
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let sequence = NEXT_CAPTURE_ID.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "quprs-solver-{}-{stamp}-{sequence}-{stream}.tmp",
            std::process::id()
        ));
        let mut options = OpenOptions::new();
        options.read(true).write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let file = options.open(&path).context("SolverProcessError: capture creation")?;
        Ok(Self { path, file })
    }

    fn exceeds_limit(&self) -> Result<bool> {
        Ok(self.file.metadata()?.len() > MAX_STREAM_BYTES as u64)
    }

    fn read_bounded(&mut self) -> Result<Vec<u8>> {
        self.file.seek(SeekFrom::Start(0))?;
        let mut bytes = Vec::new();
        (&mut self.file)
            .take((MAX_STREAM_BYTES + 1) as u64)
            .read_to_end(&mut bytes)?;
        if bytes.len() > MAX_STREAM_BYTES {
            return Err(anyhow!("SolverOutputLimit: stdout/stderr exceeded 1 MiB per stream"));
        }
        Ok(bytes)
    }
}
impl Drop for CaptureFile {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}

/// Kill the private POSIX process group even after a successful leader exit,
/// so members inheriting capture file handles are not left running.
fn terminate_tree(child: &mut Child) {
    #[cfg(unix)]
    {
        unsafe extern "C" {
            fn kill(pid: i32, sig: i32) -> i32;
        }
        if let Ok(group_id) = i32::try_from(child.id()) {
            unsafe { kill(-group_id, 9); }
        }
    }
    #[cfg(windows)]
    {
        let _ = Command::new("taskkill")
            .args(["/T", "/F", "/PID", &child.id().to_string()])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    let _ = child.kill();
    let _ = child.wait();
}

/// The deadline is for the external child, not in-process Reduction/CNF work.
pub(crate) fn run(command: &mut Command, deadline: Option<Instant>) -> Result<SolverOutput> {
    if deadline.is_some_and(|limit| Instant::now() >= limit) {
        return Err(anyhow!(SolverTimeout));
    }
    let mut stdout = CaptureFile::new("stdout")?;
    let mut stderr = CaptureFile::new("stderr")?;
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    command.stdin(Stdio::null())
        .stdout(Stdio::from(stdout.file.try_clone()?))
        .stderr(Stdio::from(stderr.file.try_clone()?));
    let mut child = command.spawn().context("SolverUnavailable: failed to spawn solver")?;

    // No pipe reader threads and no unbounded join(), including on failures.
    let outcome: Result<ExitStatus> = loop {
        match (stdout.exceeds_limit(), stderr.exceeds_limit()) {
            (Ok(a), Ok(b)) if a || b => {
                break Err(anyhow!("SolverOutputLimit: stdout/stderr exceeded 1 MiB per stream"));
            }
            (Err(error), _) | (_, Err(error)) => {
                break Err(error.context("SolverProcessError: capture metadata"));
            }
            _ => {}
        }
        if deadline.is_some_and(|limit| Instant::now() >= limit) {
            break Err(anyhow!(SolverTimeout));
        }
        match child.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(POLL_INTERVAL),
            Err(error) => break Err(error).context("SolverProcessError: wait failed"),
        }
    };
    // Cleanup is unconditional, including a successful parent process.
    terminate_tree(&mut child);
    let status = outcome?;
    if stdout.exceeds_limit()? || stderr.exceeds_limit()? {
        return Err(anyhow!("SolverOutputLimit: stdout/stderr exceeded 1 MiB per stream"));
    }
    Ok(SolverOutput {
        status,
        stdout: stdout.read_bounded()?,
        stderr: stderr.read_bounded()?,
    })
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
    fn descendants_inheriting_output_file_cannot_block_parent_exit() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "sleep 5 & echo ready; exit 0"]);
        let before = Instant::now();
        let output = run(&mut cmd, Some(before + Duration::from_secs(2)))
            .expect("file-backed capture cannot wait for descendant pipe EOF");
        assert!(output.status.success());
        assert!(output.stdout.starts_with(b"ready"));
        assert!(before.elapsed() < Duration::from_secs(3));
    }
}
