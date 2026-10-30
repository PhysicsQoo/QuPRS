// rust/pathsum/build.rs
use std::env;
use std::fs;
use std::io::{Cursor, Read};
#[path = "src/ganak_distribution.rs"]
mod ganak_distribution;
// The distribution validator is also compiled as part of the build script.
// Build-time Ganak validation reuses solver_process.rs, but it must never
// enable runtime QuPRS verification profiling. Supply a no-op recorder only
// in this build-script crate, which has a different crate root than pathsum.
mod diagnostics {
    pub(crate) fn span(_stage: &'static str) -> Option<()> { None }
    pub(crate) fn child_spawned() {}
}
#[path = "src/solver_process.rs"]
mod solver_process;
use std::path::{Path, PathBuf};

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    if env::var_os("CARGO_FEATURE_HIGH_PRECISION_GPMC").is_some() {
        // No additional Cargo crate or solver patch. Keep the native bridge
        // behind an opt-in feature until static wheel portability is proven.
        let output = PathBuf::from(env::var("OUT_DIR").unwrap());
        let input = manifest_dir.join("native/mpfr_weight_bridge.c");
        let obj = output.join("quprs_mpfr_bridge.o");
        let library = output.join("libquprs_exp_mpfr.a");
        let includes = pkg_config::probe_library("mpfr")
            .expect("The high-precision GPMC feature requires MPFR headers");
        // Homebrew stores GMP and MPFR in separate keg-only include dirs.
        // mpfr.h imports gmp.h; MPFR's own .pc include flags may omit GMP.
        let gmp_includes = pkg_config::probe_library("gmp")
            .expect("The high-precision GPMC feature requires GMP headers");
        let compiler = env::var("CC").unwrap_or_else(|_|"cc".to_string());
        let mut cc = std::process::Command::new(compiler);
        cc.args(["-std=c11","-O2","-fPIC","-c"]).arg(&input).arg("-o").arg(&obj);
        for path in includes.include_paths.iter().chain(gmp_includes.include_paths.iter()) {
            cc.arg(format!("-I{}",path.display()));
        }
        assert!(cc.status().expect("C compiler missing").success(),"MPFR C bridge build failed");
        let archiver = env::var("AR").unwrap_or_else(|_|"ar".to_string());
        assert!(std::process::Command::new(archiver).args(["rcs"])
            .arg(&library).arg(&obj).status().expect("archiver missing").success());
        println!("cargo:rustc-link-search=native={}",output.display());
        println!("cargo:rustc-link-lib=static=quprs_exp_mpfr");
        println!("cargo:rustc-link-lib=mpfr");
        println!("cargo:rustc-link-lib=gmp");
        println!("cargo:rerun-if-changed={}",input.display());
    }
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
    
    println!("cargo:rerun-if-changed=../../src/QuPRS/utils/ganak-release.txt");
    println!("cargo:rerun-if-changed=src/ganak_distribution.rs");
    // Always hash cached bytes; mere file existence is not release identity.
    let valid = fs::read(&ganak_dest).ok()
        .and_then(|b| ganak_distribution::validate(&b, &target_os, &target_arch).ok());
    if valid.is_none() {
        download_and_extract_ganak(&target_os, &target_arch, &ganak_dest);
    }
    println!("cargo:warning=Ganak {} sha256={}", ganak_distribution::VERSION,
        ganak_distribution::validate(&fs::read(&ganak_dest).unwrap(), &target_os, &target_arch).unwrap());

    // Inject environment variable for Rust code to use during development/testing
    println!("cargo:rustc-env=GANAK_BIN_PATH={}", ganak_dest.display());
    println!("cargo:rerun-if-changed={}", ganak_dest.display());

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
    // Collect include paths from pkg_config so we can forward them to cmake.
    // These libraries are required to compile GPMC from source.
    let mut extra_include_dirs: Vec<String> = Vec::new();
    if target_os != "windows" {
        // macOS Homebrew has keg-only libraries that NEED pkg-config to be found.
        // Linux (especially RHEL/CentOS based manylinux) might not ship with .pc files,
        // so we don't panic on Linux; CMake will just find them in /usr/include native paths.
        let gmp_res = pkg_config::probe_library("gmp");
        let mpfr_res = pkg_config::probe_library("mpfr");

        if target_os == "macos" {
            gmp_res.unwrap_or_else(|_| panic!(
                "\n\
                ╔════════════════════════════════════════════════════════╗\n\
                ║  Missing dependency: GMP (GNU Multiple Precision)      ║\n\
                ╠════════════════════════════════════════════════════════╣\n\
                ║  macOS (Homebrew):                                     ║\n\
                ║    brew install gmp                                    ║\n\
                ║                                                        ║\n\
                ║  After installing, retry: cargo build                  ║\n\
                ╚════════════════════════════════════════════════════════╝"
            ));
            mpfr_res.unwrap_or_else(|_| panic!(
                "\n\
                ╔════════════════════════════════════════════════════════╗\n\
                ║  Missing dependency: MPFR (Multiple Precision Float)   ║\n\
                ╠════════════════════════════════════════════════════════╣\n\
                ║  macOS (Homebrew):                                     ║\n\
                ║    brew install mpfr                                   ║\n\
                ║                                                        ║\n\
                ║  After installing, retry: cargo build                  ║\n\
                ╚════════════════════════════════════════════════════════╝"
            ));
        }

        // If pkg-config succeeded (either on macOS or Linux), collect the paths
        if let Ok(gmp) = pkg_config::probe_library("gmp") {
            for path in gmp.include_paths {
                extra_include_dirs.push(path.to_string_lossy().into_owned());
            }
        }
        if let Ok(mpfr) = pkg_config::probe_library("mpfr") {
            for path in mpfr.include_paths {
                extra_include_dirs.push(path.to_string_lossy().into_owned());
            }
        }
    }

    // --- Execute CMake ---
    println!("cargo:warning=Building GPMC from: {}", gpmc_src.display());
    
    // Provide a helpful hint for Linux users in case CMake fails due to missing headers
    if target_os == "linux" {
        println!("cargo:warning=---------------------------------------------------------");
        println!("cargo:warning=If the C++ build fails on Linux, you likely need to install system dependencies:");
        println!("cargo:warning=  Ubuntu/Debian: sudo apt install libgmp-dev libmpfr-dev zlib1g-dev libssl-dev cmake");
        println!("cargo:warning=  Fedora/RHEL:   sudo dnf install gmp-devel mpfr-devel zlib-devel openssl-devel cmake");
        println!("cargo:warning=  Or run:        sh scripts/install_linux_deps.sh");
        println!("cargo:warning=---------------------------------------------------------");
    }

    let mut config = cmake::Config::new(&gpmc_src);
    config
        .define("CMAKE_BUILD_TYPE", "Release")
        .define("CMAKE_CXX_STANDARD", "11");

    // Forward GMP/MPFR include paths to cmake so Homebrew keg-only headers are found
    if !extra_include_dirs.is_empty() {
        config.define(
            "CMAKE_CXX_FLAGS",
            extra_include_dirs
                .iter()
                .map(|d| format!("-I{}", d))
                .collect::<Vec<_>>()
                .join(" "),
        );
    }

    if target_os == "macos" {
        config.define("GPMC_STATIC_BUILD", "ON");
    }

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
    println!("cargo:rerun-if-changed={}", gpmc_dest.display());
}

/// Verify the official archive before extracting only its executable.
fn download_and_extract_ganak(target_os: &str, target_arch: &str, dest_path: &Path) {
    let fields = ganak_distribution::asset(target_os, target_arch).unwrap_or_else(|e| panic!("{e}"));
    let filename = fields[2];
    let url = format!("https://github.com/meelgroup/ganak/releases/download/release/v{}/{}",
        ganak_distribution::VERSION, filename);
    // A content-verified archive cache also supports reproducible offline rebuilds.
    let cache = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap()).join("../target/ganak-release-cache").join(filename);
    let bytes = match fs::read(&cache) {
        Ok(b) if ganak_distribution::fingerprint(&b) == fields[3] => b,
        _ => {
            println!("cargo:warning=Downloading Ganak from {url}");
            let b = reqwest::blocking::get(&url).expect("Ganak download failed")
                .error_for_status().expect("Ganak HTTP error")
                .bytes().expect("Failed to read Ganak archive").to_vec();
            assert_eq!(ganak_distribution::fingerprint(&b), fields[3], "Ganak archive SHA256 mismatch");
            fs::create_dir_all(cache.parent().unwrap()).unwrap();
            fs::write(&cache, &b).unwrap();
            b
        }
    };
    assert_eq!(ganak_distribution::fingerprint(&bytes), fields[3], "Ganak archive SHA256 mismatch");
    let mut executable = Vec::new();
    if filename.ends_with(".zip") {
        let mut archive = zip::ZipArchive::new(Cursor::new(bytes)).expect("Invalid Ganak ZIP");
        for i in 0..archive.len() {
            let mut entry = archive.by_index(i).unwrap();
            if Path::new(entry.name()).file_name().and_then(|s| s.to_str()) == Some("ganak.exe") {
                entry.read_to_end(&mut executable).unwrap();
                break;
            }
        }
    } else {
        // Unix release archives have a root-level ganak executable. Use the
        // platform tar rather than add another archive implementation.
        let archive_path = dest_path.with_extension("tar.gz");
        fs::write(&archive_path, bytes).unwrap();
        let output = std::process::Command::new("tar")
            .args(["-xOzf"]).arg(&archive_path).arg("ganak").output()
            .expect("tar is required to extract the Ganak Unix release");
        let _ = fs::remove_file(archive_path);
        assert!(output.status.success(), "Ganak tar extraction failed: {}", String::from_utf8_lossy(&output.stderr));
        executable = output.stdout;
    }
    ganak_distribution::validate(&executable, target_os, target_arch).unwrap_or_else(|e| panic!("{e}"));
    let temporary = dest_path.with_extension("installing");
    fs::write(&temporary, &executable).unwrap();
    #[cfg(unix)] {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&temporary, fs::Permissions::from_mode(0o755)).unwrap();
    }
    // Windows cannot replace an existing file with rename.
    if dest_path.exists() { fs::remove_file(dest_path).unwrap(); }
    fs::rename(temporary, dest_path).unwrap();
}
