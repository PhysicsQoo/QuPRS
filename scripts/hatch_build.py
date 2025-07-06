# scripts/hatch_build.py
# This script defines a custom Hatch build hook for cross-platform compilation and integration of the GPMC binary.
# It compiles the GPMC source using CMake, renames the output binary according to the platform,
# and copies it into the package's utils directory for distribution.

import os
import platform
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface



class CustomBuildHook(BuildHookInterface):
    def get_gpmc_binary_name(self):
        """
        Returns the platform-specific binary name for GPMC.
        """
        os_name = platform.system()
        if os_name == "Linux":
            return "gpmc.so"
        elif os_name == "Darwin":  # macOS
            return "gpmc.dylib"
        elif os_name == "Windows":
            return "gpmc.exe"
        else:
            return "gpmc"  # Fallback for unknown platforms

    def initialize(self, version, build_data):
        """
        Custom build step executed by Hatch during the build process.
        Compiles the GPMC binary and copies it to the package's utils directory.
        """
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, "GPMC")
        build_dir = os.path.join(gpmc_src_path, "build")

        # Ensure the GPMC source directory exists
        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError("GPMC source directory not found.")

        # Clean up any previous build artifacts
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        # Prepare CMake arguments for cross-platform compatibility
        cmake_args = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        toolchain = os.environ.get("CMAKE_TOOLCHAIN_FILE")
        if toolchain:
            cmake_args.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain}")
        os_name = platform.system()
        if os_name == "Darwin":
            # On macOS, add Homebrew include and lib paths if available
            brew_prefix = os.environ.get("HOMEBREW_PREFIX", "/opt/homebrew")
            cxx_flags = f"-I{brew_prefix}/opt/gmp/include -I{brew_prefix}/opt/mpfr/include -I{brew_prefix}/opt/zlib/include"
            ld_flags = f"-L{brew_prefix}/opt/gmp/lib -L{brew_prefix}/opt/mpfr/lib -L{brew_prefix}/opt/zlib/lib"
            cmake_args.extend(
                [
                    f"-DCMAKE_CXX_FLAGS={cxx_flags}",
                    f"-DCMAKE_EXE_LINKER_FLAGS={ld_flags}",
                ]
            )
        cmake_args.append("..")

        # Run CMake and Make to build the binary
        try:
            subprocess.check_call(cmake_args, cwd=build_dir)
            subprocess.check_call(["make"], cwd=build_dir)
        except subprocess.CalledProcessError as e:
            raise e

        # Rename the binary according to the platform
        new_binary_name = self.get_gpmc_binary_name()
        original_binary_path = os.path.join(build_dir, "gpmc")
        new_binary_path = os.path.join(build_dir, new_binary_name)
        if os.path.exists(original_binary_path):
            shutil.move(original_binary_path, new_binary_path)
        elif not os.path.exists(new_binary_path):
            raise FileNotFoundError(
                f"GPMC binary not found after build at {original_binary_path}"
            )

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name} ---")

        # Copy the compiled binary to the package's utils directory
        target_dir = os.path.join(PROJECT_ROOT, "src", "QuPRS", "utils")
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, new_binary_name)

        print(f"--- [Hatch Hook] Copying '{new_binary_path}' to '{target_file}' ---")
        shutil.copy(new_binary_path, target_file)
        # Note: No need for chmod, as the file will be used directly in editable installs
