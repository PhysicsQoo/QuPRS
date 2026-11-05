//! Research-only stage measurement (Cargo feature qoo156-stage-probe).
//! Cross-process timestamps use Linux/macOS CLOCK_MONOTONIC. The trace write
//! happens AFTER the final stage event to keep I/O outside the measured span.
use std::ffi::OsString;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;

#[cfg(unix)]
fn monotonic_ns() -> u128 {
    let mut stamp: libc::timespec = unsafe { std::mem::zeroed() };
    if unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut stamp) } != 0 {
        return 0;
    }
    stamp.tv_sec as u128 * 1_000_000_000 + stamp.tv_nsec as u128
}
#[cfg(not(unix))]
fn monotonic_ns() -> u128 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
}
pub struct StageProbe {
    file: Option<PathBuf>,
    events: Vec<(&'static str, u128)>,
}
impl StageProbe {
    pub fn new(scope: &str) -> Self {
        let file = std::env::var_os("QUPRS_CLI_STAGE_PROFILE_FILE").map(|name| {
            let mut base: OsString = name;
            base.push(format!(".{scope}"));
            PathBuf::from(base)
        });
        let mut probe = Self { file, events: Vec::with_capacity(20) };
        probe.mark("entry");
        probe
    }
    pub fn mark(&mut self, event: &'static str) {
        if self.file.is_some() {
            self.events.push((event, monotonic_ns()));
        }
    }
}
impl Drop for StageProbe {
    fn drop(&mut self) {
        if let Some(path) = self.file.take() {
            if let Ok(mut output) = File::create(path) {
                for (name, stamp) in &self.events {
                    let _ = writeln!(output, "{name}\t{stamp}");
                }
            }
        }
    }
}
