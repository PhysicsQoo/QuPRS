# hatch_build.py
import os
import shutil
import subprocess
import platform
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """
        Custom Hatch build hook for cross-platform compilation of the GPMC binary.

        This hook performs the following steps:
        1. Ensures the GPMC source directory exists.
        2. Creates a clean build directory.
        3. Prepares and runs the CMake configuration, with special handling for macOS dependencies.
        4. Builds the GPMC binary using make.
        5. Copies the resulting binary to the package's utils directory.
        """

        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, 'GPMC')
        build_dir = os.path.join(gpmc_src_path, 'build')

        # Step 1: Ensure the GPMC source directory exists
        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError(
                "GPMC source directory not found. Did you forget to run 'git submodule update --init'?"
            )

        # Step 2: Create a clean build directory
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        # Step 3: Prepare CMake command arguments
        cmake_args = [
            'cmake',
            '-DCMAKE_BUILD_TYPE=Release',
            # For compatibility with older CMakeLists.txt files
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
        ]

        # Special handling for macOS: set CMAKE_PREFIX_PATH for Homebrew dependencies
        os_name = platform.system()
        if os_name == "Darwin":
            print("--- [Hatch Hook] Configuring CMAKE_PREFIX_PATH for macOS ---")
            brew_prefix = os.environ.get("HOMEBREW_PREFIX", "/opt/homebrew")
            # Join all Homebrew dependency paths with semicolons, as required by CMake
            cmake_prefix_path = (
                f"{brew_prefix}/opt/gmp;"
                f"{brew_prefix}/opt/mpfr;"
                f"{brew_prefix}/opt/zlib"
            )
            cmake_args.append(f'-DCMAKE_PREFIX_PATH={cmake_prefix_path}')
            print(f"macOS CMAKE_PREFIX_PATH set to: {cmake_prefix_path}")

        # Add the source directory ('..') as the final argument
        cmake_args.append('..')
        
        # Step 4: Run CMake and make to build the binary
        try:
            print(f"Running command: {' '.join(cmake_args)} in {build_dir}")
            subprocess.check_call(cmake_args, cwd=build_dir)

            print(f"Running command: make in {build_dir}")
            subprocess.check_call(['make'], cwd=build_dir)
        except subprocess.CalledProcessError as e:
            print(f"!!! [Hatch Hook] GPMC compilation failed on {os_name}: {e}")
            raise

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name} ---")

        # Step 5: Copy the compiled binary to the package's utils directory
        binary_name = 'gpmc.exe' if os_name == "Windows" else 'gpmc'
        compiled_binary_path = os.path.join(build_dir, binary_name)
        target_dir = os.path.join(PROJECT_ROOT, 'src', 'QuPRS', 'utils')
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, binary_name)
        
        if not os.path.exists(compiled_binary_path):
            raise FileNotFoundError(
                f"Build succeeded, but GPMC executable not found at: {compiled_binary_path}"
            )
            
        shutil.copy(compiled_binary_path, target_file)
        os.chmod(target_file, 0o755)
        
        print(f"--- [Hatch Hook] Copied '{binary_name}' to {target_file} ---")