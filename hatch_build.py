# hatch_build.py
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
        Returns the platform-specific executable name for GPMC.
        Executables on Linux and macOS typically have no extension.
        """
        os_name = platform.system()
        if os_name == "Windows":
            return "gpmc.exe"
        # For Linux and macOS, the executable is just 'gpmc'
        return "gpmc"

    def initialize(self, version, build_data):
        """
        Custom build step executed by Hatch during the build process.
        Compiles the GPMC binary and copies it to the package's utils directory.
        """
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, "GPMC")
        build_dir = os.path.join(gpmc_src_path, "build")

        # The rest of the file remains unchanged, but I'll make one small change
        # to the binary renaming logic to be more robust.

        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError("GPMC source directory not found.")

        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        cmake_args = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=Release",
        ]
        os_name = platform.system()
        if os_name == "Darwin":
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

        try:
            subprocess.check_call(cmake_args, cwd=build_dir)
            subprocess.check_call(["make"], cwd=build_dir)
        except subprocess.CalledProcessError as e:
            raise e

        # CMake on Windows might already produce 'gpmc.exe'
        original_binary_name_unix = "gpmc"
        original_binary_name_windows = "gpmc.exe"
        
        # The final name we want for the binary
        new_binary_name = self.get_gpmc_binary_name()
        
        # Path to the final binary in the build directory
        new_binary_path = os.path.join(build_dir, new_binary_name)
        
        # Check for original names and rename if necessary
        original_binary_path_unix = os.path.join(build_dir, original_binary_name_unix)
        original_binary_path_windows = os.path.join(build_dir, "Release", original_binary_name_windows) # VS builds are often in a Release subdir

        # Default path
        binary_to_move = None
        if os.path.exists(original_binary_path_unix):
             binary_to_move = original_binary_path_unix
        elif os.path.exists(original_binary_path_windows):
             binary_to_move = original_binary_path_windows
        
        if binary_to_move and binary_to_move != new_binary_path:
            shutil.move(binary_to_move, new_binary_path)
        
        if not os.path.exists(new_binary_path):
            raise FileNotFoundError(
                f"GPMC binary not found after build at expected path '{new_binary_path}'"
            )

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name} ---")

        target_dir = os.path.join(PROJECT_ROOT, "src", "QuPRS", "utils")
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, new_binary_name)

        print(f"--- [Hatch Hook] Copying '{new_binary_path}' to '{target_file}' ---")
        shutil.copy(new_binary_path, target_file)
        build_data["artifacts"].append(target_file)