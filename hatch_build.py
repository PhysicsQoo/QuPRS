# hatch_build.py
import os
import platform
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """
        Custom build hook for cross-platform compilation of the GPMC binary.

        This hook ensures:
        - The GPMC source directory exists.
        - A clean build directory is created.
        - CMake is invoked with appropriate compiler and linker flags, especially for macOS.
        - The GPMC binary is built and copied to the Python package's utility directory.
        """
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, "GPMC")
        build_dir = os.path.join(gpmc_src_path, "build")

        # Ensure the GPMC source directory exists
        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError(
                "GPMC source directory not found. Did you forget to run 'git submodule update --init'?"
            )

        # 1. Create a clean build directory
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        # 2. Prepare CMake command-line arguments
        cmake_args = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]

        os_name = platform.system()
        if os_name == "Darwin":  # Darwin is the core name for macOS
            print("--- [Hatch Hook] Forcefully injecting compiler flags for macOS ---")
            brew_prefix = os.environ.get("HOMEBREW_PREFIX", "/opt/homebrew")

            # Compose all required -I (include) flags for the C++ compiler
            cxx_flags = (
                f"-I{brew_prefix}/opt/gmp/include "
                f"-I{brew_prefix}/opt/mpfr/include "
                f"-I{brew_prefix}/opt/zlib/include"
            )
            # Compose all required -L (library) flags for the linker
            ld_flags = (
                f"-L{brew_prefix}/opt/gmp/lib "
                f"-L{brew_prefix}/opt/mpfr/lib "
                f"-L{brew_prefix}/opt/zlib/lib"
            )

            # Forcefully inject flags using CMAKE_CXX_FLAGS and CMAKE_EXE_LINKER_FLAGS
            cmake_args.append(f"-DCMAKE_CXX_FLAGS={cxx_flags}")
            cmake_args.append(f"-DCMAKE_EXE_LINKER_FLAGS={ld_flags}")
            print(f"macOS CMAKE_CXX_FLAGS set to: {cxx_flags}")
            print(f"macOS CMAKE_EXE_LINKER_FLAGS set to: {ld_flags}")

        # Add the source path ('..') as the last argument
        cmake_args.append("..")

        # 3. Run cmake and make to build the binary
        try:
            print(f"Running command: {' '.join(cmake_args)} in {build_dir}")
            subprocess.check_call(cmake_args, cwd=build_dir)

            print(f"Running command: make in {build_dir}")
            subprocess.check_call(["make"], cwd=build_dir)
        except subprocess.CalledProcessError as e:
            print(f"!!! [Hatch Hook] GPMC compilation failed on {os_name}: {e}")
            raise

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name} ---")

        # 4. Copy the compiled binary to the package's utility directory
        binary_name = "gpmc.exe" if os_name == "Windows" else "gpmc"
        compiled_binary_path = os.path.join(build_dir, binary_name)
        target_dir = os.path.join(PROJECT_ROOT, "src", "QuPRS", "utils")
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, binary_name)

        if not os.path.exists(compiled_binary_path):
            raise FileNotFoundError(
                f"Build succeeded, but GPMC executable not found at: {compiled_binary_path}"
            )

        shutil.copy(compiled_binary_path, target_file)
        os.chmod(target_file, 0o755)

        print(f"--- [Hatch Hook] Copied '{binary_name}' to {target_file} ---")
