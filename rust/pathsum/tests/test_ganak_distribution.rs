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
