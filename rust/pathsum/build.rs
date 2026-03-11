use std::env;
use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();

    // 1. Correct the path to GPMC (two levels up from the manifest_dir)
    // Path: ../../GPMC
    let gpmc_src = manifest_dir
        .parent() // rust-test/
        .unwrap()
        .parent() // QuPRS/ (Root)
        .unwrap()
        .join("GPMC"); // Change to "gpmc" if the folder name is lowercase

    // Tell Cargo to rerun if the CMake file changes
    // Using display().to_string() to ensure the path is tracked correctly
    println!("cargo:rerun-if-changed={}/CMakeLists.txt", gpmc_src.display());

    // 2. Handle GMP/MPFR dependencies (Linux/macOS)
    if target_os != "windows" {
        pkg_config::probe_library("gmp").expect("GMP library not found");
        pkg_config::probe_library("mpfr").expect("MPFR library not found");
    }

    if !gpmc_src.exists() {
        panic!("FATAL: GPMC source directory not found at: {}. Current manifest: {}", 
               gpmc_src.display(), manifest_dir.display());
    }
   // 3. Compile GPMC using the cmake crate
    println!("cargo:warning=Building GPMC from: {}", gpmc_src.display());
    
    let dst = cmake::Config::new(&gpmc_src)
        .define("CMAKE_BUILD_TYPE", "Release")
        .define("CMAKE_CXX_STANDARD", "11")
        .build_target("all") // 
        .build();

    // 4. Locate the compiled executable
    let bin_name = if target_os == "windows" { "gpmc.exe" } else { "gpmc" };
    
    // Since we skipped install, the binary will be in the "build" folder
    let possible_paths = vec![
        dst.join("build").join(bin_name),
        dst.join("build").join("bin").join(bin_name),
        dst.join("build").join("Release").join(bin_name), // For Windows MSVC
    ];

    let gpmc_bin_path = possible_paths.into_iter().find(|p| p.exists())
        .unwrap_or_else(|| {
            panic!("FATAL: GPMC binary not found! CMake output path: {}", dst.display());
        });
    
    // 5. Inject the absolute path as an environment variable
    println!("cargo:rustc-env=GPMC_BIN_PATH={}", gpmc_bin_path.display());
}

#[test]
fn test_debug_path() {
    let path = env!("GPMC_BIN_PATH");
    println!("Current GPMC Path: {}", path);
}