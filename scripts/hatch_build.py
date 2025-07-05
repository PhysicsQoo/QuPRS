# scripts/hatch_build.py
# This script defines a custom Hatch build hook for cross-platform compilation and integration of the GPMC binary.
# It compiles the GPMC source using CMake, renames the output binary according to the platform,
# and copies it into the package's utils directory for distribution.
import os
import platform
import shutil
import subprocess
from pathlib import Path 

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
            return "gpmc"

    def initialize(self, version, build_data):
        """
        Custom build step executed by Hatch during the build process.
        """
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        
        project_root = Path(self.root)
        gpmc_src_path = project_root / "GPMC"
        build_dir = project_root / "build_cpp" 

        if not gpmc_src_path.is_dir():
            raise FileNotFoundError("GPMC source directory not found.")

        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(exist_ok=True)

        cmake_args = [
            "cmake",
            "-S", str(gpmc_src_path),
            "-B", str(build_dir),
            "-DCMAKE_BUILD_TYPE=Release",
        ]
        
        os_name = platform.system()
        if os_name == "Darwin":
            brew_prefix = os.environ.get("HOMEBREW_PREFIX", "/opt/homebrew")
            cxx_flags = f"-I{brew_prefix}/opt/gmp/include -I{brew_prefix}/opt/mpfr/include -I{brew_prefix}/opt/zlib/include"
            ld_flags = f"-L{brew_prefix}/opt/gmp/lib -L{brew_prefix}/opt/mpfr/lib -L{brew_prefix}/opt/zlib/lib"
            cmake_args.extend([
                f"-DCMAKE_CXX_FLAGS={cxx_flags}",
                f"-DCMAKE_EXE_LINKER_FLAGS={ld_flags}",
            ])

        # Run CMake and Make to build the binary
        try:
            subprocess.check_call(cmake_args)
            subprocess.check_call(["make", "-C", str(build_dir)])
        except subprocess.CalledProcessError as e:
            raise e

        new_binary_name = self.get_gpmc_binary_name()
        original_binary_path = build_dir / "gpmc" 
        new_binary_path = build_dir / new_binary_name

        if not original_binary_path.exists():
             raise FileNotFoundError(f"GPMC binary not found at {original_binary_path}")
        
        shutil.move(original_binary_path, new_binary_path)

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name} ---")

        # Copy the compiled binary to the package's utils directory
        target_dir = project_root / "src" / "QuPRS" / "utils"
        target_dir.mkdir(exist_ok=True)
        target_file_path = target_dir / new_binary_name

        print(f"--- [Hatch Hook] Copying '{new_binary_path}' to '{target_file_path}' ---")
        shutil.copy(new_binary_path, target_file_path)

        relative_artifact_path = str(target_file_path.relative_to(project_root))
        build_data['artifacts'].append(relative_artifact_path)
        print(f"--- [Hatch Hook] Added artifact to build data: {relative_artifact_path} ---")
