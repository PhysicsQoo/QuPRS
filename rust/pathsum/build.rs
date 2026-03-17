// rust/pathsum/build.rs
use std::env;
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();
    let target_arch = env::var("CARGO_CFG_TARGET_ARCH").unwrap();

    // Define the target directory for the final binaries (corresponds to src/QuPRS/utils/wmc_tools)
    // Maturin will automatically package the src directory under the package root into the wheel
    let dest_tools_dir = manifest_dir
        .parent()
        .unwrap() // rust/
        .parent()
        .unwrap() // QuPRS/
        .join("src")
        .join("QuPRS")
        .join("utils")
        .join("wmc_tools");

    fs::create_dir_all(&dest_tools_dir).expect("Failed to create wmc_tools directory");

    // ==========================================
    // 1. Download and install Ganak
    // ==========================================
    let ganak_dest = dest_tools_dir.join(if target_os == "windows" {
        "ganak.exe"
    } else {
        "ganak"
    });
    
    if !ganak_dest.exists() {
        download_and_extract_ganak(&target_os, &target_arch, &ganak_dest);
    } else {
        println!(
            "cargo:warning=Ganak binary found at {}. Skipping download.",
            ganak_dest.display()
        );
    }
    
    // Inject environment variable for Rust code to use during development/testing
    println!("cargo:rustc-env=GANAK_BIN_PATH={}", ganak_dest.display());

    // ==========================================
    // 2. Compile GPMC
    // ==========================================
    let gpmc_src = manifest_dir
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("GPMC");
        
    if !gpmc_src.exists() {
        panic!(
            "FATAL: GPMC source directory not found at: {}",
            gpmc_src.display()
        );
    }

    println!(
        "cargo:rerun-if-changed={}/CMakeLists.txt",
        gpmc_src.display()
    );

    // --- Handle dependencies (GMP/MPFR) ---
    if target_os != "windows" {
        pkg_config::probe_library("gmp").expect("GMP library not found");
        pkg_config::probe_library("mpfr").expect("MPFR library not found");
    }

    // --- Execute CMake ---
    println!("cargo:warning=Building GPMC from: {}", gpmc_src.display());
    let mut config = cmake::Config::new(&gpmc_src);
    config
        .define("CMAKE_BUILD_TYPE", "Release")
        .define("CMAKE_CXX_STANDARD", "11");

    // If cross-compiling on macOS (e.g., x86_64 host compiling for aarch64 target)
    if target_os == "macos" {
        config.define(
            "CMAKE_OSX_ARCHITECTURES",
            if target_arch == "aarch64" {
                "arm64"
            } else {
                "x86_64"
            },
        );
    }

    let dst = config.build_target("all").build();

    // --- Locate and copy the compiled GPMC executable ---
    let bin_name = if target_os == "windows" {
        "gpmc.exe"
    } else {
        "gpmc"
    };
    let possible_paths = vec![
        dst.join("build").join(bin_name),
        dst.join("build").join("bin").join(bin_name),
        dst.join("build").join("Release").join(bin_name),
    ];

    let gpmc_bin_path = possible_paths
        .into_iter()
        .find(|p| p.exists())
        .unwrap_or_else(|| {
            panic!(
                "FATAL: GPMC binary not found! CMake output: {}",
                dst.display()
            )
        });

    let gpmc_dest = dest_tools_dir.join(bin_name);
    fs::copy(&gpmc_bin_path, &gpmc_dest)
        .expect("Failed to copy GPMC binary to target directory");
    println!(
        "cargo:warning=Successfully compiled and copied GPMC to {}",
        gpmc_dest.display()
    );

    // Inject environment variable for Rust code to use during development/testing
    println!("cargo:rustc-env=GPMC_BIN_PATH={}", gpmc_dest.display());
}

/// Downloads the corresponding Ganak ZIP for the target platform and extracts it
fn download_and_extract_ganak(target_os: &str, target_arch: &str, dest_path: &Path) {
    let os_str = match target_os {
        "linux" => "linux",
        "macos" => "mac",
        _ => {
            println!(
                "cargo:warning=Unsupported OS for Ganak download: {}. Skipping.",
                target_os
            );
            return;
        }
    };

    let arch_str = match target_arch {
        "x86_64" => {
            if os_str == "mac" {
                "x86_64"
            } else {
                "amd64"
            }
        }
        "aarch64" => "arm64",
        _ => {
            println!(
                "cargo:warning=Unsupported architecture for Ganak: {}. Skipping.",
                target_arch
            );
            return;
        }
    };

    let filename = format!("ganak-{}-{}.zip", os_str, arch_str);
    let url = format!(
        "https://github.com/meelgroup/ganak/releases/download/release/2.5.2/{}",
        filename
    );
    println!("cargo:warning=Downloading Ganak from {}", url);

    // Send HTTP GET request
    let response = reqwest::blocking::get(&url)
        .unwrap_or_else(|e| panic!("Failed to download Ganak: {}", e));
    let bytes = response.bytes().expect("Failed to read response bytes");

    // Extract ZIP
    let reader = Cursor::new(bytes);
    let mut zip = zip::ZipArchive::new(reader).expect("Failed to read Ganak ZIP archive");

    // Look for the file named ganak
    let mut found = false;
    for i in 0..zip.len() {
        let mut file = zip.by_index(i).unwrap();
        if file.name().ends_with("ganak") || file.name().ends_with("ganak.exe") {
            let mut out_file = fs::File::create(dest_path).unwrap();
            std::io::copy(&mut file, &mut out_file).unwrap();

            // Grant execution permissions (Unix)
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = fs::metadata(dest_path).unwrap().permissions();
                perms.set_mode(0o755);
                fs::set_permissions(dest_path, perms).unwrap();
            }
            found = true;
            break;
        }
    }

    if !found {
        panic!("Could not find 'ganak' binary inside downloaded zip.");
    }
    println!(
        "cargo:warning=Successfully installed Ganak to {}",
        dest_path.display()
    );
}
