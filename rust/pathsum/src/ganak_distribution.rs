//! Shared build/runtime identity checks for the pinned upstream distribution.
use sha2::{Digest, Sha256};
use std::path::Path;

pub const VERSION: &str = "2.8.0";
pub const UPSTREAM_SHA: &str = "b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281";
pub const MANIFEST: &str = include_str!("../../../src/QuPRS/utils/ganak-release.txt");

pub fn asset(os: &str, arch: &str) -> Result<Vec<&'static str>, String> {
    MANIFEST.lines().filter(|line| !line.starts_with('#'))
        .map(|line| line.split_whitespace().collect::<Vec<_>>())
        .find(|fields| fields.len() == 5 && fields[0] == os && fields[1] == arch)
        .ok_or_else(|| format!("Unsupported Ganak platform: {os}/{arch}"))
}

pub fn fingerprint(bytes: &[u8]) -> String { format!("{:x}", Sha256::digest(bytes)) }

pub fn architecture(bytes: &[u8], os: &str, arch: &str) -> bool {
    match (os, arch) {
        ("linux", "x86_64") | ("linux", "aarch64") => {
            bytes.len() >= 20 && &bytes[..6] == b"\x7fELF\x02\x01"
                && u16::from_le_bytes([bytes[18], bytes[19]]) == if arch == "x86_64" {62} else {183}
        },
        ("macos", "x86_64") | ("macos", "aarch64") => {
            bytes.len() >= 8 && bytes[..4] == [0xcf, 0xfa, 0xed, 0xfe]
                && u32::from_le_bytes(bytes[4..8].try_into().unwrap()) == if arch == "x86_64" {0x01000007} else {0x0100000c}
        },
        ("windows", "x86_64") => {
            if bytes.len() < 64 || &bytes[..2] != b"MZ" { return false; }
            let offset = u32::from_le_bytes(bytes[60..64].try_into().unwrap()) as usize;
            bytes.get(offset..offset + 6).map(|h| h == b"PE\0\0\x64\x86").unwrap_or(false)
        },
        _ => false,
    }
}

pub fn validate(bytes: &[u8], os: &str, arch: &str) -> Result<String, String> {
    let fields = asset(os, arch)?;
    let hash = fingerprint(bytes);
    if hash != fields[4] { return Err(format!("Ganak SHA256 mismatch: expected {}, actual {hash}", fields[4])); }
    if !architecture(bytes, os, arch) { return Err(format!("Wrong Ganak architecture: {os}/{arch}")); }
    Ok(hash)
}

pub fn diagnostics(path: &Path, overridden: bool) -> Result<String, String> {
    use std::collections::HashMap;
    use std::sync::{Mutex, OnceLock};
    static CACHE: OnceLock<Mutex<HashMap<String, String>>> = OnceLock::new();
    let resolved = if path.components().count() == 1 && !path.is_file() {
        std::env::var_os("PATH").and_then(|paths| std::env::split_paths(&paths)
            .map(|dir| dir.join(path)).find(|candidate| candidate.is_file()))
    } else { None };
    let path = resolved.as_deref().unwrap_or(path);
    let overridden = overridden && option_env!("GANAK_BIN_PATH")
        .map(|packaged| std::fs::canonicalize(packaged).ok() != std::fs::canonicalize(path).ok())
        .unwrap_or(true);
    let metadata = std::fs::metadata(path).map_err(|e| e.to_string())?;
    #[cfg(unix)]
    let change_time = { use std::os::unix::fs::MetadataExt; (metadata.ctime(), metadata.ctime_nsec()) };
    #[cfg(not(unix))]
    let change_time = metadata.created();
    let key = format!("{}:{:?}:{:?}:{}:{overridden}", path.display(), metadata.modified(), change_time, metadata.len());
    let cache = CACHE.get_or_init(|| Mutex::new(HashMap::new()));
    if let Some(info) = cache.lock().unwrap().get(&key) { return Ok(info.clone()); }
    let info = uncached_diagnostics(path, overridden)?;
    cache.lock().unwrap().insert(key, info.clone());
    Ok(info)
}

fn uncached_diagnostics(path: &Path, overridden: bool) -> Result<String, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("Ganak {}: {e}", path.display()))?;
    let os = std::env::consts::OS;
    let arch = std::env::consts::ARCH;
    let hash = fingerprint(&bytes);
    if !architecture(&bytes, os, arch) { return Err(format!("Wrong Ganak architecture: {os}/{arch}, sha256={hash}")); }
    let pinned = validate(&bytes, os, arch).is_ok();
    if !overridden && !pinned { return Err(format!("Unverified packaged Ganak: sha256={hash}; rebuild QuPRS")); }
    let output = std::process::Command::new(path).arg("--version").output().map_err(|e| e.to_string())?;
    if !output.status.success() { return Err(format!("Ganak --version failed: {}", output.status)); }
    let version = String::from_utf8_lossy(&output.stdout).lines().find(|s| s.contains("Ganak SHA1:")).unwrap_or("Ganak version unknown").to_owned();
    if pinned && !version.contains(UPSTREAM_SHA) { return Err(format!("Ganak embedded version mismatch: {version}")); }
    if overridden && !pinned { eprintln!("Ganak override version mismatch: requested={VERSION} sha256={hash} {version}"); }
    Ok(format!("Ganak requested={VERSION} pinned={pinned} override={overridden} sha256={hash} {version}"))
}
