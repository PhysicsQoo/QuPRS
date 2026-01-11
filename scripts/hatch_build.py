# scripts/hatch_build.py
# This script defines a custom Hatch build hook for cross-platform compilation of GPMC and Ganak.

import os
import platform
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    @staticmethod
    def _get_cmake_output_name(base_name):
        """
        Returns the platform-specific binary name produced by CMake.
        """
        os_name = platform.system()
        extension = ""
        if os_name == "Linux":
            extension = ".so"
        elif os_name == "Darwin":  # macOS
            extension = ".dylib"
        elif os_name == "Windows":
            extension = ".exe"
        
        return f"{base_name}{extension}"

    def build_cmake_project(self, src_path, build_dir, binary_base_name):
        """
        Builds a CMake project located at src_path.
        """
        os_name = platform.system()
        cmake_args = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=Release",
        ]
        
        # Cross-platform toolchain support
        toolchain = os.environ.get("CMAKE_TOOLCHAIN_FILE")
        if toolchain:
            cmake_args.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain}")

        if os_name == "Darwin":
            # On macOS, add Homebrew include and lib paths if available
            brew_prefix = os.environ.get("HOMEBREW_PREFIX", "/opt/homebrew")
            # Common paths for gmp, mpfr, zlib
            include_paths = [
                f"{brew_prefix}/opt/gmp/include",
                f"{brew_prefix}/opt/mpfr/include",
                f"{brew_prefix}/opt/zlib/include",
                f"{brew_prefix}/include"
            ]
            lib_paths = [
                f"{brew_prefix}/opt/gmp/lib",
                f"{brew_prefix}/opt/mpfr/lib",
                f"{brew_prefix}/opt/zlib/lib",
                f"{brew_prefix}/lib"
            ]
            
            cxx_flags = " ".join([f"-I{p}" for p in include_paths])
            ld_flags = " ".join([f"-L{p}" for p in lib_paths])
            
            cmake_args.extend(
                [
                    f"-DCMAKE_CXX_FLAGS={cxx_flags}",
                    f"-DCMAKE_EXE_LINKER_FLAGS={ld_flags}",
                ]
            )
            
        cmake_args.append("..")

        # Clean up build directory
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        print(f"--- [Hatch Hook] Configuring {binary_base_name} ---")
        subprocess.check_call(cmake_args, cwd=build_dir)
        
        print(f"--- [Hatch Hook] Building {binary_base_name} ---")
        subprocess.check_call(["cmake", "--build", "."], cwd=build_dir)

        # Locate and handle the binary
        binary_name = self._get_cmake_output_name(binary_base_name)
        
        # Location might vary (e.g. Release/ folder on Windows)
        possible_paths = [
            os.path.join(build_dir, binary_base_name), # Standard unix (may lack extension)
            os.path.join(build_dir, binary_name),      # With extension
            os.path.join(build_dir, "Release", binary_name), # Windows Release
            os.path.join(build_dir, "Debug", binary_name),   # Windows Debug
        ]
        
        found_binary = None
        for p in possible_paths:
            if os.path.exists(p):
                found_binary = p
                break
        
        if not found_binary:
             raise FileNotFoundError(f"Could not find built binary for {binary_base_name}")

        return found_binary, binary_name

    def initialize(self, version, build_data):
        print("--- [Hatch Hook] Running custom build step ---")
        PROJECT_ROOT = self.root
        
        tools = [
            {"name": "gpmc", "dir": "GPMC"},
            {"name": "ganak", "dir": "ganak"},
        ]
        
        target_dir = os.path.join(PROJECT_ROOT, "src", "QuPRS", "utils", "wmc_tools")
        os.makedirs(target_dir, exist_ok=True)

        for tool in tools:
            src_path = os.path.join(PROJECT_ROOT, tool["dir"])
            if not os.path.isdir(src_path) or not os.listdir(src_path):
                 print(f"--- [Hatch Hook] WARNING: {tool['dir']} directory missing or empty. Skipping build. Ensure git submodules are initialized. ---")
                 # We don't raise error to allow sdist creation even if submodules are missing locally, 
                 # but for wheel build it might be critical.
                 continue

            # Check if binary already exists (e.g. via cache)
            # We standardize the installed binary name (no extension)
            # binary_name is used for source lookups, but dest_name is just the tool name
            dest_name = tool["name"]
            dest_path = os.path.join(target_dir, dest_name)

            if os.path.exists(dest_path):
                print(f"--- [Hatch Hook] Binary {dest_name} found at {dest_path}. Skipping compilation. ---")
                continue

            build_dir = os.path.join(src_path, "build")
            
            try:
                built_binary_path, _ = self.build_cmake_project(src_path, build_dir, tool["name"])
                
                print(f"--- [Hatch Hook] Installing {tool['name']} to {dest_path} ---")
                shutil.copy(built_binary_path, dest_path)
                
            except Exception as e:
                print(f"--- [Hatch Hook] ERROR building {tool['name']}: {e} ---")
                raise e

        print("--- [Hatch Hook] Build complete ---")