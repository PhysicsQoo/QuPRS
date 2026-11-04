//! CLI-only process isolation: whole-invocation deadline, atomic output,
//! bounded diagnostics, optional resource limits. No Rust pathsum hot-path changes.
use crate::args::Cli;
use anyhow::{bail, Context, Result};
use std::fs;
#[cfg(target_os = "linux")]
use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom};
use std::process::{Command, ExitStatus, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};

const OUTPUT_LIMIT: u64 = 16 * 1024 * 1024;
pub const TIMEOUT_EXIT: i32 = 124;
pub const RESOURCE_EXIT: i32 = 125;

#[cfg(unix)]
use std::os::unix::process::CommandExt;

pub fn supervise(cli: &Cli) -> Result<i32> {
    if cli.timeout == 0 { bail!("--timeout must be positive"); }
    if cli.max_memory_mib == Some(0) || cli.max_address_space_mib == Some(0) {
        bail!("resource limits must be positive MiB values");
    }
    let deadline = Instant::now()
        .checked_add(Duration::from_secs(cli.timeout))
        .context("requested timeout overflows the monotonic clock")?;

    // An explicit physical-memory cap is never silently downgraded to RLIMIT_AS.
    let cgroup = match cli.max_memory_mib {
        Some(mib) => Some(MemoryCgroup::new(mib)?),
        None => None,
    };
    let mut output = tempfile::tempfile().context("create private worker stdout")?;
    let mut diagnostics = tempfile::tempfile().context("create private worker stderr")?;
    let mut command = Command::new(std::env::current_exe()?);
    command.args(std::env::args_os().skip(1))
        .arg("--__quprs-worker")
        .stdin(Stdio::null())
        .stdout(Stdio::from(output.try_clone()?))
        .stderr(Stdio::from(diagnostics.try_clone()?));

    #[cfg(unix)]
    command.process_group(0);
    #[cfg(not(unix))]
    if cli.max_address_space_mib.is_some() {
        bail!("--max-address-space-mib requires a Unix host");
    }
    #[cfg(unix)]
    if let Some(mib) = cli.max_address_space_mib {
        install_address_space_limit(&mut command, mib)?;
    }
    // Join the bounded cgroup BEFORE exec, including dynamic-loader/startup
    // allocations. The cgroup.procs descriptor lives across Command::spawn
    // so its pre-exec async-signal-safe write cannot use a closed fd.
    #[cfg(target_os = "linux")]
    let join_file = cgroup.as_ref()
        .map(|group| group.install_pre_exec(&mut command)).transpose()?;
    let mut child = command.spawn().context("spawn isolated QuPRS CLI worker")?;
    #[cfg(target_os = "linux")]
    drop(join_file);
    let pid = child.id();
    // Wait for the real OS process-exit event. A dedicated parent-side thread
    // blocks in wait(), so there is no 20ms polling tail for millisecond jobs.
    // Only the CLI parent pays this fixed overhead, never rust/pathsum.
    let (tx, rx) = mpsc::sync_channel::<io::Result<ExitStatus>>(1);
    let waiter = thread::spawn(move || { let _ = tx.send(child.wait()); });
    let received = rx.recv_timeout(deadline.saturating_duration_since(Instant::now()));
    let exit = match received {
        Ok(Ok(status)) if Instant::now() < deadline => status,
        Ok(Ok(_)) => {
            // The child exited, but the parent cannot certify that it
            // completed before the strict monotonic request deadline.
            let _ = waiter.join();
            if cli.quiet { println!("Timeout"); }
            else { eprintln!("Timeout: whole CLI invocation exceeded --timeout"); }
            return Ok(TIMEOUT_EXIT);
        }
        Err(mpsc::RecvTimeoutError::Timeout) => {
            terminate_tree(pid, cgroup.as_ref());
            // Do not claim safety until the wait thread reaps the child.
            match rx.recv_timeout(Duration::from_secs(2)) {
                Ok(Ok(_)) => (),
                Ok(Err(error)) => return Err(error).context("reap canceled worker"),
                Err(_) => bail!("ResourceSupervisorError: worker was not reaped after timeout"),
            }
            let _ = waiter.join();
            if cli.quiet { println!("Timeout"); }
            else { eprintln!("Timeout: whole CLI invocation exceeded --timeout"); }
            return Ok(TIMEOUT_EXIT);
        }
        Ok(Err(error)) => return Err(error).context("wait for CLI worker"),
        Err(mpsc::RecvTimeoutError::Disconnected) => {
            bail!("ResourceSupervisorError: worker waiter disconnected")
        }
    };
    let _ = waiter.join();

    if cgroup.as_ref().is_some_and(MemoryCgroup::oom_killed) {
        eprintln!("MemoryLimitExceeded: cgroup memory.max was reached");
        return Ok(RESOURCE_EXIT);
    }
    if exit.success() {
        if output.metadata()?.len() > OUTPUT_LIMIT {
            eprintln!("WorkerOutputLimitExceeded: stdout exceeds 16 MiB");
            return Ok(RESOURCE_EXIT);
        }
        output.seek(SeekFrom::Start(0))?;
        io::copy(&mut output, &mut io::stdout().lock())?;
        diagnostics.seek(SeekFrom::Start(0))?;
        io::copy(&mut diagnostics, &mut io::stderr().lock())?;
        Ok(0)
    } else {
        diagnostics.seek(SeekFrom::Start(0))?;
        let mut message = String::new();
        diagnostics.take(OUTPUT_LIMIT).read_to_string(&mut message)?;
        if !message.is_empty() { eprint!("{message}"); }
        eprintln!("WorkerFailed: exit={exit}; no partial EQ/NEQ was emitted");
        Ok(exit.code().filter(|code| *code != 0).unwrap_or(RESOURCE_EXIT))
    }
}

#[cfg(unix)]
fn install_address_space_limit(command: &mut Command, mib: u64) -> Result<()> {
    let bytes = mib.checked_mul(1024 * 1024).context("RLIMIT_AS size overflow")?;
    let limit: libc::rlim_t = bytes.try_into().context("RLIMIT_AS size not representable")?;
    // Only async-signal-safe libc operations inside pre_exec.
    unsafe {
        command.pre_exec(move || {
            let value = libc::rlimit { rlim_cur: limit, rlim_max: limit };
            if libc::setrlimit(libc::RLIMIT_AS, &value) != 0 {
                return Err(io::Error::last_os_error());
            }
            Ok(())
        });
    }
    Ok(())
}

fn terminate_tree(pid: u32, group: Option<&MemoryCgroup>) {
    if let Some(group) = group {
        if group.kill_all().is_ok() {
            #[cfg(unix)]
            unsafe { libc::kill(pid as i32, libc::SIGKILL); }
            return;
        }
    }
    #[cfg(unix)]
    {
        for descendant in descendant_pids(pid).into_iter().rev() {
            unsafe { libc::kill(descendant as i32, libc::SIGKILL); }
        }
        unsafe {
            libc::kill(-(pid as i32), libc::SIGKILL);
            libc::kill(pid as i32, libc::SIGKILL);
        }
    }
    #[cfg(windows)]
    let _ = Command::new("taskkill").args([
        "/T", "/F", "/PID", &pid.to_string(),
    ]).status();
}

#[cfg(unix)]
fn descendant_pids(root: u32) -> Vec<u32> {
    let mut pairs = Vec::<(u32, u32)>::new();
    #[cfg(target_os = "linux")]
    if let Ok(entries) = fs::read_dir("/proc") {
        for e in entries.flatten() {
            let Some(pid) = e.file_name().to_string_lossy().parse::<u32>().ok() else { continue };
            let Ok(stat) = fs::read_to_string(format!("/proc/{pid}/stat")) else { continue };
            if let Some((_, tail)) = stat.rsplit_once(") ") {
                if let Some(ppid) = tail.split_whitespace().nth(1).and_then(|v| v.parse::<u32>().ok()) {
                    pairs.push((pid, ppid));
                }
            }
        }
    }
    if pairs.is_empty() {
        if let Ok(result) = Command::new("ps").args(["-axo", "pid=,ppid="]).output() {
            for line in String::from_utf8_lossy(&result.stdout).lines() {
                let mut words = line.split_whitespace();
                if let (Some(pid), Some(ppid)) = (
                    words.next().and_then(|v| v.parse::<u32>().ok()),
                    words.next().and_then(|v| v.parse::<u32>().ok()),
                ) { pairs.push((pid, ppid)); }
            }
        }
    }
    let mut descendants = vec![root];
    let mut cursor = 0usize;
    while cursor < descendants.len() {
        let parent = descendants[cursor];
        for &(pid, ppid) in &pairs {
            if ppid == parent && !descendants.contains(&pid) {
                descendants.push(pid);
            }
        }
        cursor += 1;
    }
    descendants.into_iter().skip(1).collect()
}

// Linux cgroup v2 requires delegation. If unavailable, error before running
// the worker; never misreport a virtual-address cap as physical RSS isolation.
struct MemoryCgroup {
    path: std::path::PathBuf,
}
impl MemoryCgroup {
    #[cfg(target_os = "linux")]
    fn new(mib: u64) -> Result<Self> {
        let bytes = mib.checked_mul(1024 * 1024).context("memory.max overflow")?;
        let current = fs::read_to_string("/proc/self/cgroup")
            .context("find cgroup v2")?;
        let relative = current.lines().find_map(|x| x.strip_prefix("0::"))
            .context("cgroup v2 is unavailable")?
            .trim_start_matches('/');
        let parent = std::path::Path::new("/sys/fs/cgroup").join(relative);
        let path = parent.join(format!("quprs-cli-{}", std::process::id()));
        fs::create_dir(&path).context("no delegated writable memory cgroup; refused to run unbounded")?;
        let configured = (|| -> Result<()> {
            fs::write(path.join("memory.max"), bytes.to_string())
                .context("configure physical-memory limit")?;
            fs::write(path.join("memory.oom.group"), "1")
                .context("configure group OOM handling")?;
            Ok(())
        })();
        if let Err(err) = configured {
            let _ = fs::remove_dir(&path);
            return Err(err);
        }
        Ok(Self { path })
    }
    #[cfg(not(target_os = "linux"))]
    fn new(_: u64) -> Result<Self> {
        bail!("--max-memory-mib requires a delegated Linux cgroup v2")
    }

    #[cfg(target_os = "linux")]
    fn install_pre_exec(&self, command: &mut Command) -> Result<File> {
        use std::os::fd::AsRawFd;
        let writer = fs::OpenOptions::new().write(true)
            .open(self.path.join("cgroup.procs"))
            .context("open cgroup.procs for pre-exec worker admission")?;
        let fd = writer.as_raw_fd();
        // libc::getpid and libc::write are async-signal-safe. Do not allocate,
        // lock, format, spawn, or use Rust filesystem APIs in pre_exec.
        unsafe {
            command.pre_exec(move || {
                let mut buf = [0u8; 16];
                let mut value = libc::getpid() as u32;
                let mut first = buf.len();
                loop {
                    first -= 1;
                    buf[first] = b'0' + (value % 10) as u8;
                    value /= 10;
                    if value == 0 { break; }
                }
                let width = buf.len() - first;
                let count = libc::write(fd, buf[first..].as_ptr().cast(), width);
                if count != width as isize {
                    return Err(io::Error::last_os_error());
                }
                Ok(())
            });
        }
        Ok(writer)
    }

    fn kill_all(&self) -> Result<()> {
        #[cfg(target_os = "linux")]
        fs::write(self.path.join("cgroup.kill"), "1")
            .context("terminate worker cgroup")?;
        Ok(())
    }
    fn oom_killed(&self) -> bool {
        #[cfg(target_os = "linux")]
        if let Ok(data) = fs::read_to_string(self.path.join("memory.events")) {
            return data.lines().any(|line| line.split_once(' ')
                .is_some_and(|(key, value)| key == "oom_kill" && value.parse::<u64>().unwrap_or(0) > 0));
        }
        false
    }
}
impl Drop for MemoryCgroup {
    fn drop(&mut self) {
        let _ = self.kill_all();
        let _ = fs::remove_dir(&self.path);
    }
}

pub fn prepare_worker() -> Result<()> {
    // Test-only deterministic scheduling witness. Never compiled in release.
    // This proves the outer deadline starts BEFORE opening QASM files.
    #[cfg(debug_assertions)]
    if let Ok(ms) = std::env::var("QUPRS_CLI_TEST_HOLD_MS") {
        let millis: u64 = ms.parse().context("invalid test-only hold duration")?;
        thread::sleep(Duration::from_millis(millis.min(10_000)));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(unix)]
    #[test]
    fn terminating_shell_also_terminates_background_child() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "sleep 30 & wait"]).process_group(0);
        let mut child = cmd.spawn().unwrap();
        thread::sleep(Duration::from_millis(100));
        assert!(!descendant_pids(child.id()).is_empty());
        terminate_tree(child.id(), None);
        assert!(child.wait().is_ok());
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn timeout_kills_solver_like_separate_process_group() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "setsid sleep 30 & wait"]).process_group(0);
        let mut child = cmd.spawn().unwrap();
        thread::sleep(Duration::from_millis(150));
        let descendants = descendant_pids(child.id());
        assert!(!descendants.is_empty(), "must observe subprocess before kill");
        assert!(descendants.iter().any(|pid| unsafe {
            libc::getpgid(*pid as i32) != child.id() as i32
        }), "test must include a descendant outside the worker process group");
        terminate_tree(child.id(), None);
        child.wait().unwrap();
        // A killed child may remain briefly as a zombie until init reaps it.
        for pid in descendants {
            let mut exited = false;
            for _ in 0..50 {
                match fs::read_to_string(format!("/proc/{pid}/stat")) {
                    Err(_) => { exited = true; break; }
                    Ok(stat) => {
                        let state = stat.rsplit_once(") ").unwrap().1.chars().next().unwrap();
                        if state == 'Z' { exited = true; break; }
                    }
                }
                thread::sleep(Duration::from_millis(10));
            }
            assert!(exited, "separate-process-group descendant {pid} survived cancellation");
        }
    }
}
