// rust/pathsum/tests/test_wmc_tools.rs
use std::env;
use std::path::PathBuf;
use std::process::Command;

/// Get the absolute path of the expected tools directory.
fn get_tools_dir() -> PathBuf {
    // In integration tests, CARGO_MANIFEST_DIR points to rust/pathsum/
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent().unwrap() // Up to rust/
        .parent().unwrap() // Up to QuPRS root/
        .join("src")
        .join("QuPRS")
        .join("utils")
        .join("wmc_tools")
}

#[test]
fn test_gpmc_binary_exists_and_executable() {
    let tools_dir = get_tools_dir();
    let bin_name = if cfg!(windows) { "gpmc.exe" } else { "gpmc" };
    let gpmc_path = tools_dir.join(bin_name);

    // 1. Verify if the physical file exists in the source tree
    assert!(
        gpmc_path.exists(),
        "Integration test failed: GPMC binary not found. Expected path: {:?}",
        gpmc_path
    );

    // 2. Verify if the file is executable and can be invoked by the OS
    // We pass '--help' to check if the process starts and returns a result
    let output = Command::new(&gpmc_path)
        .arg("--help")
        .output()
        .expect("Failed to start GPMC process. Check file execution permissions.");

    // As long as the process starts (regardless of exit code), it is a valid executable
    assert!(
        output.status.success() || output.status.code().is_some(),
        "GPMC failed to execute properly"
    );
}

#[test]
fn test_ganak_binary_exists_and_executable() {
    let tools_dir = get_tools_dir();
    let bin_name = if cfg!(windows) { "ganak.exe" } else { "ganak" };
    let ganak_path = tools_dir.join(bin_name);

    // 1. Verify if the physical file exists in the source tree
    assert!(
        ganak_path.exists(),
        "Integration test failed: Ganak binary not found. Expected path: {:?}",
        ganak_path
    );

    // 2. Verify if the file is executable and can be invoked by the OS
    let output = Command::new(&ganak_path)
        .arg("--help")
        .output()
        .expect("Failed to start Ganak process. Check file execution permissions.");

    assert!(
        output.status.success() || output.status.code().is_some(),
        "Ganak failed to execute properly"
    );
}