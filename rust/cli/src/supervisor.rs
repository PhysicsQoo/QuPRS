//! CLI-only process isolation: whole-invocation deadline, atomic output,
//! bounded diagnostics, optional resource limits. No Rust pathsum hot-path changes.
use crate::args::Cli;
use anyhow::{bail, Context, Result};
use std::fs::{self, File};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::process::{Command, ExitStatus, Stdio};
use std::sync::mpsc;
#[cfg(unix)]
use std::sync::atomic::{AtomicI32, Ordering};
use std::thread;
use std::time::{Duration, Instant};

const OUTPUT_LIMIT: u64 = 16 * 1024 * 1024;
const WORKER_LAUNCH_WITNESS: &[u8] = b"QuPRS-supervisor-inherited-stdin-v1\n";

// POSIX signal handlers must not allocate, lock, print, or inspect the
// process tree. Record the signal and let the normal supervisor path perform
// bounded tree termination and reaping. No extra threads on the fast path.
#[cfg(unix)]
static INTERRUPTED_SIGNAL: AtomicI32 = AtomicI32::new(0);

#[cfg(unix)]
extern "C" fn record_supervisor_interrupt(signal: libc::c_int) {
    INTERRUPTED_SIGNAL.store(signal, Ordering::Relaxed);
}

#[cfg(unix)]
fn install_supervisor_signal_handlers() -> Result<()> {
    for signal in [libc::SIGINT, libc::SIGTERM] {
        let mut action: libc::sigaction = unsafe { std::mem::zeroed() };
        action.sa_sigaction = record_supervisor_interrupt as usize;
        unsafe {
            libc::sigemptyset(&mut action.sa_mask);
            if libc::sigaction(signal, &action, std::ptr::null_mut()) != 0 {
                return Err(io::Error::last_os_error())
                    .context("install CLI supervisor cancellation signal handler");
            }
        }
    }
    Ok(())
}

fn interrupted_signal() -> Option<i32> {
    #[cfg(unix)]
    {
        let signal = INTERRUPTED_SIGNAL.load(Ordering::Relaxed);
        if signal != 0 { return Some(signal); }
    }
    None
}

fn external_signal_status(signal: i32) -> i32 {
    128 + signal
}
pub const TIMEOUT_EXIT: i32 = 124;
pub const RESOURCE_EXIT: i32 = 125;

#[cfg(unix)]
use std::os::unix::process::CommandExt;


enum WorkerEvent {
    Exited(io::Result<ExitStatus>, Instant),
    CaptureFinished(&'static str, Instant),
    CaptureOverflow(&'static str),
    CaptureError(&'static str),
}

enum StopReason {
    Timeout,
    OutputLimit(&'static str),
    CaptureFailed(&'static str),
    WaitFailed(String),
    ExternalSignal(i32),
}

// An output EOF at (or after) deadline is not a successful completion even
// when the receiver's channel already has a queued event. This guard is part
// of the parent process, not native Path-sum or WMC computation.
fn eof_before_deadline(finished: Instant, deadline: Instant) -> bool {
    finished < deadline
}

// Parent-owned bounded spool: the worker cannot write to an unlimited
// tempfile. Each reader checks the byte count *before* committing chunks.
// Both pipes are drained concurrently to prevent stdout/stderr deadlock.
fn capture_bounded<R: Read>(
    mut source: R,
    mut destination: File,
    stream: &'static str,
    events: mpsc::Sender<WorkerEvent>,
) -> Result<File> {
    let mut written = 0_u64;
    let mut block = [0_u8; 8192];
    loop {
        let count = match source.read(&mut block) {
            Ok(count) => count,
            Err(error) => {
                let _ = events.send(WorkerEvent::CaptureError(stream));
                return Err(error).context(format!("read worker {stream}"));
            }
        };
        if count == 0 {
            // A reaped worker may have descendants that keep inherited
            // output pipes open. Report EOF explicitly; never block forever
            // in an unconditional reader join after the worker exits.
            let _ = events.send(WorkerEvent::CaptureFinished(stream, Instant::now()));
            return Ok(destination);
        }
        if written + count as u64 > OUTPUT_LIMIT {
            let _ = events.send(WorkerEvent::CaptureOverflow(stream));
            bail!("WorkerOutputLimitExceeded: {stream} exceeds {OUTPUT_LIMIT} bytes");
        }
        if let Err(error) = destination.write_all(&block[..count]) {
            let _ = events.send(WorkerEvent::CaptureError(stream));
            return Err(error).context(format!("spool worker {stream}"));
        }
        written += count as u64;
    }
}

// Linux re-parents descendants of a dead worker directly to this CLI
// supervisor, even when Ganak sets a distinct process group.
fn enable_child_subreaper() -> Result<()> {
    #[cfg(target_os = "linux")]
    if unsafe { libc::prctl(libc::PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) } != 0 {
        return Err(io::Error::last_os_error())
            .context("cannot safely supervise orphaned solver descendants");
    }
    Ok(())
}

// Called only after the direct worker has been reaped. On the fast path,
// waitpid reports ECHILD, avoiding any /proc scan or polling cost.
fn cleanup_adopted_children() -> Result<()> {
    #[cfg(target_os = "linux")]
    {
        let mut status = 0_i32;
        let mut pid = unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) };
        while pid > 0 {
            pid = unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) };
        }
        if pid == -1 {
            let err = io::Error::last_os_error();
            if err.raw_os_error() == Some(libc::ECHILD) { return Ok(()); }
            return Err(err).context("inspect adopted solver descendants");
        }

        // A waitpid return of 0 means an adopted process remains alive,
        // possibly SIGSTOP'ed. Kill detached process groups and reap.
        let own_group = unsafe { libc::getpgrp() };
        for _ in 0..100 {
            let descendants = descendant_pids(std::process::id());
            for child_pid in descendants.iter().rev().copied() {
                let pgid = unsafe { libc::getpgid(child_pid as i32) };
                if pgid > 0 && pgid != own_group {
                    unsafe { libc::kill(-pgid, libc::SIGKILL); }
                }
                unsafe { libc::kill(child_pid as i32, libc::SIGKILL); }
            }
            loop {
                let reaped = unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) };
                if reaped > 0 { continue; }
                if reaped == -1 {
                    let err = io::Error::last_os_error();
                    if err.raw_os_error() == Some(libc::ECHILD) { return Ok(()); }
                    return Err(err).context("reap adopted solver");
                }
                break;
            }
            thread::sleep(Duration::from_millis(10));
        }
        bail!("ResourceSupervisorError: adopted solver survived SIGKILL");
    }
    Ok(())
}

pub fn supervise(cli: &Cli) -> Result<i32> {
    if cli.timeout == 0 { bail!("--timeout must be positive"); }
    // Handle ordinary terminal/CI cancellation independently from worker
    // process group. SIGKILL is uncatchable; Linux additionally arms
    // PR_SET_PDEATHSIG on the worker before it may parse QASM.
    #[cfg(unix)]
    install_supervisor_signal_handlers()?;
    enable_child_subreaper()?;
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

    // Parent-owned invocation namespace for Rust WMC CNF and solver capture
    // files. A killed worker cannot run RAII Drop, so the supervisor owns
    // removal after the worker/descendants have been reaped.
    let worker_tempdir = tempfile::Builder::new()
        .prefix("quprs-cli-")
        .tempdir()
        .context("create private per-invocation solver temporary directory")?;
    let output = tempfile::tempfile().context("create private worker stdout")?;
    let diagnostics = tempfile::tempfile().context("create private worker stderr")?;
    let mut command = Command::new(std::env::current_exe()?);
    command.args(std::env::args_os().skip(1))
        .arg("--__quprs-worker")
        .env("QUPRS_CLI_SUPERVISOR_PID", std::process::id().to_string())
        // std::env::temp_dir() in Rust WMC/solver capture consults TMPDIR
        // on Linux and macOS. Never change the supervisor's TMPDIR globally.
        .env("TMPDIR", worker_tempdir.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

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
    // Join the cgroup before exec, so the loader/QASM are also bounded.
    #[cfg(target_os = "linux")]
    let join_file = cgroup.as_ref()
        .map(|group| group.install_pre_exec(&mut command)).transpose()?;
    // Linux worker death on abrupt supervisor loss (e.g. SIGKILL). This
    // guards the direct worker, not arbitrary daemonized solver grandchildren.
    #[cfg(target_os = "linux")]
    {
        let parent_pid = std::process::id() as libc::pid_t;
        unsafe {
            command.pre_exec(move || {
                if libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL, 0, 0, 0) != 0 {
                    return Err(io::Error::last_os_error());
                }
                if libc::getppid() != parent_pid {
                    return Err(io::Error::new(io::ErrorKind::NotConnected,
                        "CLI supervisor exited before worker admission"));
                }
                Ok(())
            });
        }
    }
    if let Some(signal) = interrupted_signal() {
        eprintln!("CancelledBySignal: signal {signal} before worker start");
        return Ok(external_signal_status(signal));
    }
    let mut child = command.spawn().context("spawn isolated QuPRS CLI worker")?;
    #[cfg(target_os = "linux")]
    drop(join_file);
    let pid = child.id();
    // The non-public worker mode must prove it has an inherited control pipe
    // and the expected live parent before it starts QASM parsing. This is
    // misuse resistance, not an adversarial same-user security boundary.
    let mut admission = child.stdin.take().context("worker admission pipe unavailable")?;
    if let Err(error) = admission.write_all(WORKER_LAUNCH_WITNESS) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error).context("write worker admission witness");
    }
    drop(admission);
    let stdout = child.stdout.take().context("worker stdout pipe unavailable")?;
    let stderr = child.stderr.take().context("worker stderr pipe unavailable")?;

    let (tx, rx) = mpsc::channel::<WorkerEvent>();
    let stdout_tx = tx.clone();
    let stdout_reader = thread::spawn(move || capture_bounded(
        stdout, output, "stdout", stdout_tx,
    ));
    let stderr_tx = tx.clone();
    let stderr_reader = thread::spawn(move || capture_bounded(
        stderr, diagnostics, "stderr", stderr_tx,
    ));
    // Event-driven process wait: do not introduce a periodic polling tail.
    let waiter = thread::spawn(move || {
        let status = child.wait();
        let _ = tx.send(WorkerEvent::Exited(status, Instant::now()));
    });
    let mut exit = None;
    let mut reaped = false;
    let mut stdout_finished = false;
    let mut stderr_finished = false;
    let mut interrupted = None;
    loop {
        if let Some(signal) = interrupted_signal() {
            interrupted = Some(StopReason::ExternalSignal(signal));
            break;
        }
        // Worker exit alone is not sufficient: an inherited stdout/stderr
        // descriptor can remain open in a detached descendant. EOF for both
        // captures is part of a successful bounded request.
        if exit.is_some() && stdout_finished && stderr_finished { break; }
        // A short receive cap wakes the supervisor on SIGINT/SIGTERM without
        // introducing a polling tail into completed requests. No extra
        // subprocess, signal thread, or computational hot-path instrumentation.
        let remaining = deadline.saturating_duration_since(Instant::now());
        match rx.recv_timeout(remaining.min(Duration::from_millis(50))) {
            Ok(WorkerEvent::Exited(Ok(status), finished)) => {
                reaped = true;
                if finished < deadline {
                    exit = Some(status);
                } else {
                    interrupted = Some(StopReason::Timeout);
                    break;
                }
            }
            Ok(WorkerEvent::Exited(Err(error), _)) => {
                reaped = true;
                interrupted = Some(StopReason::WaitFailed(error.to_string()));
                break;
            }
            Ok(WorkerEvent::CaptureFinished(stream, finished)) => {
                // A ready event queued after the deadline may still be
                // returned by recv_timeout(Duration::ZERO). Never release
                // a late successful result merely because both pipes closed.
                if !eof_before_deadline(finished, deadline) {
                    interrupted = Some(StopReason::Timeout);
                    break;
                }
                match stream {
                    "stdout" => stdout_finished = true,
                    "stderr" => stderr_finished = true,
                    _ => {
                        interrupted = Some(StopReason::CaptureFailed(stream));
                        break;
                    }
                }
            }
            Ok(WorkerEvent::CaptureOverflow(stream)) => {
                interrupted = Some(StopReason::OutputLimit(stream));
                break;
            }
            Ok(WorkerEvent::CaptureError(stream)) => {
                interrupted = Some(StopReason::CaptureFailed(stream));
                break;
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                if let Some(signal) = interrupted_signal() {
                    interrupted = Some(StopReason::ExternalSignal(signal));
                    break;
                }
                if Instant::now() >= deadline {
                    interrupted = Some(StopReason::Timeout);
                    break;
                }
                continue;
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                interrupted = Some(StopReason::WaitFailed(
                    "worker event channel disconnected".to_owned()
                ));
                break;
            }
        }
    }
    if interrupted.is_none() {
        if let Some(signal) = interrupted_signal() {
            interrupted = Some(StopReason::ExternalSignal(signal));
        }
    }
    if interrupted.is_some() {
        terminate_tree(pid, cgroup.as_ref());
        if !reaped {
            // Capture events may arrive before the waiter event. Never mistake
            // them for successful reaping or abandon a live worker.
            let reap_deadline = Instant::now() + Duration::from_secs(2);
            loop {
                match rx.recv_timeout(reap_deadline.saturating_duration_since(Instant::now())) {
                    Ok(WorkerEvent::Exited(Ok(_), _)) => break,
                    Ok(WorkerEvent::Exited(Err(error), _)) => {
                        return Err(error).context("reap canceled worker");
                    }
                    Ok(_) => continue,
                    Err(_) => bail!("ResourceSupervisorError: worker was not reaped after cancellation"),
                }
            }
        }
    }
    let _ = waiter.join();
    cleanup_adopted_children()?;

    // Collect kernel OOM evidence BEFORE removing the cgroup, then dispose of
    // both resource scopes BEFORE any success stdout may be published.
    // Cleanup failures are typed resource errors, never a scientific verdict.
    let oom_result = cgroup.as_ref().map(MemoryCgroup::oom_killed).transpose();
    let cgroup_cleanup = cgroup.as_ref().map(MemoryCgroup::cleanup).transpose();
    if let Err(error) = cgroup_cleanup {
        eprintln!("ResourceSupervisorCleanupError: cgroup: {error:#}");
        return Ok(RESOURCE_EXIT);
    }
    // Explicit retention is ONLY for ordinary failed solver requests.
    // Even with QUPRS_KEEP_FAILED_CNF=1, a kernel OOM or an unreadable
    // memory.events witness is a resource failure and MUST delete CNF.
    let preserve_failed_cnf = can_preserve_failed_cnf(
        interrupted.is_some(),
        exit.as_ref().is_some_and(|status| !status.success()),
        &oom_result,
        std::env::var("QUPRS_KEEP_FAILED_CNF").as_deref() == Ok("1"),
    );
    if let Err(error) = finalize_worker_tempdir(worker_tempdir, preserve_failed_cnf) {
        eprintln!("ResourceSupervisorCleanupError: worker temporary files: {error:#}");
        return Ok(RESOURCE_EXIT);
    }
    match oom_result {
        Ok(Some(true)) => {
            eprintln!("MemoryLimitExceeded: cgroup memory.max was reached");
            return Ok(RESOURCE_EXIT);
        }
        Ok(Some(false) | None) => {}
        Err(error) => {
            eprintln!("ResourceSupervisorError: cannot certify cgroup memory.events: {error:#}");
            return Ok(RESOURCE_EXIT);
        }
    }

    // On any failure, never join a reader whose pipe may still be held by
    // an uncontained descendant. The CLI main process exits after this
    // typed failure; no partial scientific output is committed.
    if let Some(reason) = interrupted {
        match reason {
            StopReason::Timeout => {
                if cli.quiet { println!("Timeout"); }
                else { eprintln!("Timeout: whole CLI invocation exceeded --timeout"); }
                return Ok(TIMEOUT_EXIT);
            }
            StopReason::OutputLimit(stream) => {
                eprintln!("WorkerOutputLimitExceeded: {stream} exceeds {OUTPUT_LIMIT} bytes");
            }
            StopReason::CaptureFailed(stream) => {
                eprintln!("WorkerOutputCaptureError: unable to capture {stream}");
            }
            StopReason::WaitFailed(message) => {
                eprintln!("ResourceSupervisorError: {message}");
            }
            StopReason::ExternalSignal(signal) => {
                eprintln!("CancelledBySignal: received signal {signal}; worker tree canceled");
                return Ok(external_signal_status(signal));
            }
        }
        return Ok(RESOURCE_EXIT);
    }

    // Both readers signaled EOF while the monotonic deadline was active;
    // joining now is bounded by in-memory cleanup, not a blocked pipe read.
    let stdout_result = stdout_reader.join()
        .map_err(|_| anyhow::anyhow!("WorkerOutputCaptureError: stdout reader panicked"))?;
    let stderr_result = stderr_reader.join()
        .map_err(|_| anyhow::anyhow!("WorkerOutputCaptureError: stderr reader panicked"))?;
    let mut output = match stdout_result {
        Ok(file) => file,
        Err(error) => {
            eprintln!("WorkerOutputCaptureError: {error:#}");
            return Ok(RESOURCE_EXIT);
        }
    };
    let mut diagnostics = match stderr_result {
        Ok(file) => file,
        Err(error) => {
            eprintln!("WorkerOutputCaptureError: {error:#}");
            return Ok(RESOURCE_EXIT);
        }
    };

    if let Some(signal) = interrupted_signal() {
        eprintln!("CancelledBySignal: signal {signal} before output commit");
        return Ok(external_signal_status(signal));
    }
    let exit = exit.context("worker exit status missing after successful event wait")?;
    if exit.success() {
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

// Preserve failed science data only when the worker failed normally AND
// kernel resource evidence proves that no OOM occurred. For a missing
// controller cap, None is a valid witness. Unreadable evidence fails closed.
fn can_preserve_failed_cnf(
    interrupted: bool,
    worker_failed: bool,
    oom_result: &Result<Option<bool>>,
    opt_in: bool,
) -> bool {
    opt_in && !interrupted && worker_failed
        && matches!(oom_result, Ok(None | Some(false)))
}

// The worker inherits TMPDIR only for the duration of this invocation.
// An opt-in ordinary failure may keep failed CNF files, but NOT other private
// solver captures. Every other artifact remains supervisor-owned and must be
// disposed of before the private directory can be retained.
fn finalize_worker_tempdir(dir: tempfile::TempDir, preserve_failed_cnf: bool) -> Result<()> {
    if preserve_failed_cnf {
        let mut has_cnf = false;
        for entry in fs::read_dir(dir.path())
            .context("inspect failed worker temporary directory")?
        {
            let entry = entry.context("read failed worker temporary entry")?;
            let kind = entry.file_type().context("inspect failed worker temporary entry type")?;
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if kind.is_file() && name.starts_with("temp_eqcheck_") && name.ends_with(".cnf") {
                has_cnf = true;
                continue;
            }
            // Use file_type rather than following symlinks when cleaning.
            // A cleanup error fails closed and TempDir's Drop still tries
            // to remove the remaining private directory.
            if kind.is_dir() {
                fs::remove_dir_all(entry.path())
                    .context("remove non-CNF failed worker temporary directory")?;
            } else {
                fs::remove_file(entry.path())
                    .context("remove non-CNF failed worker temporary artifact")?;
            }
        }
        if has_cnf {
            let retained = dir.keep();
            eprintln!("RetainedFailedSolverArtifacts: explicitly requested failed CNF at {}", retained.display());
            return Ok(());
        }
    }
    dir.close().context("remove supervisor-owned per-invocation temporary directory")
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
        let root = std::path::Path::new("/sys/fs/cgroup");
        let parent = root.join(relative).canonicalize()
            .context("resolve own cgroup-v2 path")?;
        anyhow::ensure!(parent.starts_with(root), "cgroup path escaped controller root");

        // cgroup-v2 domain controllers have a no-internal-process rule.
        // An ordinary CLI supervisor must run in a *leaf*, while its bounded
        // worker lives in a sibling under an EMPTY memory-delegated parent.
        // Searching ancestors is paid only when --max-memory-mib is requested.
        // Never silently interpret RLIMIT_AS as a physical-memory cap.
        let mut search = Some(parent.as_path());
        while let Some(candidate) = search {
            if !candidate.starts_with(root) { break; }
            let enabled = fs::read_to_string(candidate.join("cgroup.subtree_control"))
                .unwrap_or_default();
            let members = fs::read_to_string(candidate.join("cgroup.procs"))
                .unwrap_or_default();
            if enabled.split_whitespace().any(|x| x == "memory")
                && members.trim().is_empty()
            {
                let path = candidate.join(format!("quprs-cli-{}", std::process::id()));
                match fs::create_dir(&path) {
                    Ok(()) => {
                        let configured = (|| -> Result<()> {
                            fs::write(path.join("memory.max"), bytes.to_string())
                                .context("configure physical-memory limit")?;
                            fs::write(path.join("memory.oom.group"), "1")
                                .context("configure group OOM handling")?;
                            let readback = fs::read_to_string(path.join("memory.max"))
                                .context("read back physical-memory cap")?;
                            anyhow::ensure!(
                                readback.trim() == bytes.to_string(),
                                "memory.max readback did not equal requested cap"
                            );
                            Ok(())
                        })();
                        if let Err(error) = configured {
                            let _ = fs::remove_dir(&path);
                            return Err(error);
                        }
                        return Ok(Self { path });
                    }
                    Err(error) if error.kind() == io::ErrorKind::PermissionDenied => {
                        // This ancestor is not delegated to the current user.
                        // Keep looking only at actual cgroup ancestors.
                    }
                    Err(error) => {
                        return Err(error).context("create physical-memory worker cgroup");
                    }
                }
            }
            if candidate == root { break; }
            search = candidate.parent();
        }
        bail!("no delegated writable memory cgroup with memory controller active; refused to run unbounded")
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
    // Called on every complete or interrupted request before releasing any
    // scientific stdout, not just from Drop. This also handles a child that
    // daemonized within the CLI-owned cgroup after its direct worker exited.
    fn cleanup(&self) -> Result<()> {
        #[cfg(target_os = "linux")]
        {
            if !self.path.exists() { return Ok(()); }
            let deadline = Instant::now() + Duration::from_secs(1);
            loop {
                let data = fs::read_to_string(self.path.join("cgroup.events"))
                    .context("read cgroup.events before cleanup")?;
                if parse_cgroup_populated(&data)? {
                    self.kill_all().context("kill populated worker cgroup before cleanup")?;
                }
                match fs::remove_dir(&self.path) {
                    Ok(()) => return Ok(()),
                    Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(()),
                    Err(error) if Instant::now() >= deadline => {
                        return Err(error).context(format!(
                            "unable to remove worker cgroup {} after bounded cleanup", self.path.display()
                        ));
                    }
                    Err(_) => thread::sleep(Duration::from_millis(10)),
                }
            }
        }
        #[cfg(not(target_os = "linux"))]
        Ok(())
    }
    fn oom_killed(&self) -> Result<bool> {
        #[cfg(target_os = "linux")]
        {
            let data = fs::read_to_string(self.path.join("memory.events"))
                .context("read cgroup memory.events")?;
            return parse_oom_killed(&data);
        }
        #[cfg(not(target_os = "linux"))]
        Ok(false)
    }
}
// Missing or malformed kernel accounting is an explicit resource error.
#[cfg(target_os = "linux")]
fn parse_oom_killed(text: &str) -> Result<bool> {
    let mut count = None;
    for line in text.lines() {
        let mut parts = line.split_whitespace();
        if parts.next() == Some("oom_kill") {
            let value = parts.next().context("missing oom_kill counter")?;
            anyhow::ensure!(parts.next().is_none(), "malformed oom_kill counter");
            anyhow::ensure!(count.is_none(), "duplicate oom_kill counter");
            count = Some(value.parse::<u64>()
                .context("invalid oom_kill counter")?);
        }
    }
    Ok(count.context("memory.events missing oom_kill counter")? > 0)
}

#[cfg(target_os = "linux")]
fn parse_cgroup_populated(data: &str) -> Result<bool> {
    let mut populated = None;
    for line in data.lines() {
        let mut parts = line.split_whitespace();
        if parts.next() == Some("populated") {
            let value = parts.next().context("missing cgroup.events populated value")?;
            anyhow::ensure!(parts.next().is_none(), "malformed cgroup.events populated value");
            anyhow::ensure!(populated.is_none(), "duplicate cgroup.events populated value");
            populated = Some(match value {
                "0" => false,
                "1" => true,
                _ => bail!("invalid cgroup.events populated value"),
            });
        }
    }
    populated.context("cgroup.events missing populated field")
}

impl Drop for MemoryCgroup {
    fn drop(&mut self) {
        // Fallback only for early admission/spawn/worker-reap errors. On the
        // successful path cleanup() has already been checked before commit.
        if let Err(error) = self.cleanup() {
            eprintln!("ResourceSupervisorCleanupError: fallback cgroup cleanup failed: {error:#}");
        }
    }
}


pub fn authorize_worker_launch() -> Result<()> {
    // A hidden Clap option by itself must not bypass the outer timeout.
    // The parent provides a one-shot anonymous pipe and expected parent PID.
    let supervisor_pid: u32 = std::env::var("QUPRS_CLI_SUPERVISOR_PID")
        .context("InvalidWorkerLaunch: missing supervisor context")?
        .parse()
        .context("InvalidWorkerLaunch: malformed supervisor context")?;
    #[cfg(unix)]
    if unsafe { libc::getppid() } as u32 != supervisor_pid {
        bail!("InvalidWorkerLaunch: supervisor process is not the parent");
    }
    let mut witness = vec![0_u8; WORKER_LAUNCH_WITNESS.len()];
    io::stdin().read_exact(&mut witness)
        .context("InvalidWorkerLaunch: missing inherited supervisor pipe")?;
    if witness != WORKER_LAUNCH_WITNESS {
        bail!("InvalidWorkerLaunch: inherited supervisor pipe did not match");
    }
    Ok(())
}

pub fn prepare_worker() -> Result<()> {

    // Test-only witness written into the exact worker TMPDIR. A deterministic
    // hold/timeout or signal will kill the worker without running its Drop,
    // proving the parent removes both known Rust WMC temporary-name families.
    #[cfg(debug_assertions)]
    if let Ok(witness) = std::env::var("QUPRS_CLI_TEST_TEMP_MARKER") {
        let dir = std::env::temp_dir();
        fs::write(dir.join("temp_eqcheck_killed_worker.cnf"), b"test-sensitive-cnf")
            .context("write controlled CNF crash-remnant")?;
        fs::write(dir.join("quprs-solver_killed_worker.tmp"), b"test-sensitive-stdout")
            .context("write controlled solver-output crash-remnant")?;
        fs::write(witness, dir.as_os_str().to_string_lossy().as_bytes())
            .context("write parent-owned temporary directory witness")?;
    }

    // Debug-only process-liveness witnesses. These variables are not
    // compiled into the release CLI and do not affect production performance.
    #[cfg(debug_assertions)]
    if let Ok(path) = std::env::var("QUPRS_CLI_TEST_WORKER_PIDFILE") {
        fs::write(path, std::process::id().to_string())
            .context("write worker PID for parent-death-signal test")?;
    }

    #[cfg(all(debug_assertions, unix))]
    if let Ok(path) = std::env::var("QUPRS_CLI_TEST_DETACHED_PIDFILE") {
        let mut cmd = Command::new("sleep");
        cmd.arg("30").stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
        unsafe {
            cmd.pre_exec(|| {
                if libc::setsid() < 0 {
                    return Err(io::Error::last_os_error());
                }
                Ok(())
            });
        }
        let helper = cmd.spawn().context("spawn detached worker-session witness")?;
        fs::write(path, helper.id().to_string())
            .context("save detached helper PID")?;
        // Hold the worker alive so a parent can observe and kill even a
        // descendant in a separate process group before it becomes orphaned.
        thread::sleep(Duration::from_secs(6));
    }

    // Debug-only bounded I/O pressure. Large writes reach the parent capture
    // threads before any QASM parsing; never compiled into release binaries.
    #[cfg(debug_assertions)]
    if let Ok(stream) = std::env::var("QUPRS_CLI_TEST_FLOOD_STREAM") {
        let bytes = [b'X'; 8192];
        for _ in 0..(OUTPUT_LIMIT / 8192 + 2) {
            match stream.as_str() {
                "stdout" => io::stdout().write_all(&bytes)?,
                "stderr" => io::stderr().write_all(&bytes)?,
                _ => bail!("invalid debug-only flood stream"),
            }
        }
        bail!("QOO156_TEST_FLOOD_FINISHED");
    }
    // Debug-only pipe inheritance witness. The verification worker itself
    // completes normally, but a child retains stdout/stderr past the request
    // deadline. Its process group is canceled before any verdict is released.
    #[cfg(all(debug_assertions, unix))]
    if let Ok(secs) = std::env::var("QUPRS_CLI_TEST_INHERIT_OUTPUT_SECS") {
        let seconds: u64 = secs.parse().context("invalid inherited-pipe duration")?;
        anyhow::ensure!((1..=20).contains(&seconds), "inherited-pipe test duration out of range");
        let _child = Command::new("sleep").arg(seconds.to_string())
            .stdin(Stdio::null())
            .stdout(Stdio::inherit()).stderr(Stdio::inherit())
            .spawn().context("spawn inherited-pipe witness")?;
    }
    // Only debug builds: reproduce worker exit while an OS-detached helper
    // remains alive. This does not exist in the release executable.
    #[cfg(all(debug_assertions, target_os = "linux"))]
    if let Ok(path) = std::env::var("QUPRS_CLI_TEST_ORPHAN_PIDFILE") {
        let child = Command::new("setsid").args(["sleep", "30"])
            .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
            .spawn().context("launch detached orphan control")?;
        fs::write(path, child.id().to_string())
            .context("save orphan PID evidence")?;
        thread::sleep(Duration::from_millis(100));
        bail!("QOO156_TEST_INTENTIONAL_WORKER_EXIT");
    }
    // Test-only deterministic scheduling witness. Never compiled in release.
    // This proves the outer deadline starts BEFORE opening QASM files.
    #[cfg(debug_assertions)]
    if let Ok(ms) = std::env::var("QUPRS_CLI_TEST_HOLD_MS") {
        let millis: u64 = ms.parse().context("invalid test-only hold duration")?;
        thread::sleep(Duration::from_millis(millis.min(10_000)));
    }
    // Debug-only cgroup proof: force physical page commits inside the real
    // worker, after pre-exec admission but before reading QASM. The released
    // CLI cannot activate this test harness through environment variables.
    #[cfg(debug_assertions)]
    if let Ok(text) = std::env::var("QUPRS_CLI_TEST_ALLOC_MIB") {
        let mib: usize = text.parse().context("invalid test allocation MiB")?;
        anyhow::ensure!(mib <= 256, "test allocation exceeds safe pilot bound");
        let bytes = mib.checked_mul(1024 * 1024)
            .context("test allocation exceeds address space")?;
        let mut pages = vec![0u8; bytes];
        for index in (0..bytes).step_by(4096) {
            unsafe { std::ptr::write_volatile(pages.as_mut_ptr().add(index), 1); }
        }
        std::hint::black_box(&pages);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn failed_cnf_opt_in_never_overrides_cgroup_oom_or_unknown_resource_state() {
        let safe_no_cap: Result<Option<bool>> = Ok(None);
        let safe_no_oom: Result<Option<bool>> = Ok(Some(false));
        let real_oom: Result<Option<bool>> = Ok(Some(true));
        let unreadable: Result<Option<bool>> = Err(anyhow::anyhow!("unreadable memory.events"));
        assert!(can_preserve_failed_cnf(false, true, &safe_no_cap, true));
        assert!(can_preserve_failed_cnf(false, true, &safe_no_oom, true));
        for witness in [&real_oom, &unreadable] {
            assert!(!can_preserve_failed_cnf(false, true, witness, true),
                "OOM or unknown cgroup state must never preserve CNF");
        }
        assert!(!can_preserve_failed_cnf(true, true, &safe_no_cap, true),
            "timeout/SIGTERM must not preserve CNF");
        assert!(!can_preserve_failed_cnf(false, false, &safe_no_cap, true),
            "successful results must not preserve CNF");
        assert!(!can_preserve_failed_cnf(false, true, &safe_no_cap, false),
            "CNF retention must require explicit opt-in");
    }

    #[test]
    fn parent_owned_temporary_directory_reclaims_forced_worker_artifacts() {
        let dir = tempfile::Builder::new().prefix("qoo156-cleanup-").tempdir().unwrap();
        let path = dir.path().to_path_buf();
        fs::write(path.join("temp_eqcheck_forced.cnf"), b"secret-cnfdump").unwrap();
        fs::write(path.join("quprs-solver_forced.tmp"), b"secret-log").unwrap();
        finalize_worker_tempdir(dir, false).unwrap();
        assert!(!path.exists(), "forced-termination artifacts were not removed");
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn cgroup_cleanup_requires_strict_populated_witness() {
        assert!(!parse_cgroup_populated("populated 0\nfrozen 0\n").unwrap());
        assert!(parse_cgroup_populated("populated 1\nfrozen 0\n").unwrap());
        for malformed in ["", "frozen 0", "populated", "populated x",
                          "populated 2", "populated 0 garbage",
                          "populated 0\npopulated 1"] {
            assert!(parse_cgroup_populated(malformed).is_err(), "{malformed:?}");
        }
        let fake_root = tempfile::tempdir().unwrap();
        let fake_path = fake_root.path().join("worker");
        fs::create_dir(&fake_path).unwrap();
        let fake = MemoryCgroup { path: fake_path.clone() };
        assert!(fake.cleanup().is_err(), "unreadable cgroup.events failed open");
        std::mem::forget(fake); // fake directory isn't a kernel cgroup.
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn memory_oom_witness_must_be_readable_and_well_formed() {
        assert_eq!(parse_oom_killed("low 0\nhigh 0\noom 0\noom_kill 0\n").unwrap(), false);
        assert_eq!(parse_oom_killed("low 0\nhigh 0\noom 2\noom_kill 1\n").unwrap(), true);
        for malformed in ["", "oom 1", "oom_kill", "oom_kill xyz",
                          "oom_kill 0 extra", "oom_kill 0\noom_kill 1"] {
            assert!(parse_oom_killed(malformed).is_err(), "accepted {malformed:?}");
        }
        let missing = MemoryCgroup {
            path: std::env::temp_dir().join(format!(
                "qoo156-uncreated-memory-events-{}", std::process::id()
            )),
        };
        assert!(missing.oom_killed().is_err(), "unreadable cgroup events failed open");
        // Avoid Drop attempting cgroup.kill on an unrelated temp path.
        std::mem::forget(missing);
    }

    #[test]
    fn worker_and_pipe_completion_at_deadline_is_not_success() {
        let deadline = Instant::now();
        let earlier = deadline - Duration::from_nanos(1);
        let later = deadline + Duration::from_nanos(1);
        assert!(eof_before_deadline(earlier, deadline));
        assert!(!eof_before_deadline(deadline, deadline));
        assert!(!eof_before_deadline(later, deadline));
        // Check the production event payload still carries the timestamp.
        match WorkerEvent::CaptureFinished("stdout", later) {
            WorkerEvent::CaptureFinished(stream, finished) => {
                assert_eq!(stream, "stdout");
                assert!(!eof_before_deadline(finished, deadline));
            }
            _ => panic!("unexpected event"),
        }
    }

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
