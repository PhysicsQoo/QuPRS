# hatch_build.py
import os
import shutil
import subprocess
import platform
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    """
    Custom Hatch build hook for compiling the GPMC binary during the build process.

    This hook performs the following steps:
      1. Ensures the GPMC source directory exists.
      2. Creates a clean build directory for each build.
      3. Runs CMake to configure the build system.
      4. Runs 'make' to compile the GPMC binary.
      5. Copies the compiled binary to the package's utils directory.
    """

    def initialize(self, version, build_data):
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, 'GPMC')
        build_dir = os.path.join(gpmc_src_path, 'build')

        # Step 1: Ensure the GPMC source directory exists
        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError(
                "GPMC source directory not found. Did you forget to run 'git submodule update --init'?"
            )

        # Step 2: Create a clean build directory for each build
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        # Step 3: Prepare and run the cmake command
        #         We no longer use build.sh; instead, we invoke cmake directly from Python
        cmake_args = [
            'cmake',
            '-DCMAKE_BUILD_TYPE=Release',
            # Key fix: Instruct newer cmake to be compatible with older settings
            # This resolves errors encountered on macOS
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            '..'  # Point to the parent source directory (GPMC/)
        ]
        
        print(f"Running command: {' '.join(cmake_args)} in {build_dir}")
        subprocess.check_call(cmake_args, cwd=build_dir)

        # Step 4: Run 'make' to compile the binary
        print(f"Running command: make in {build_dir}")
        subprocess.check_call(['make'], cwd=build_dir)

        print(f"--- [Hatch Hook] GPMC compiled successfully on {platform.system()} ---")

        # Step 5: Copy the compiled binary to the package's utils directory
        binary_name = 'gpmc.exe' if platform.system() == "Windows" else 'gpmc'
        compiled_binary_path = os.path.join(build_dir, binary_name)  # Look for the binary in the build directory
        target_dir = os.path.join(PROJECT_ROOT, 'src', 'QuPRS', 'utils')
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, binary_name)
        
        if not os.path.exists(compiled_binary_path):
            raise FileNotFoundError(
                f"Build succeeded, but the GPMC executable was not found at the expected path: {compiled_binary_path}"
            )
            
        shutil.copy(compiled_binary_path, target_file)
        os.chmod(target_file, 0o755)
        
        print(f"--- [Hatch Hook] Copied '{binary_name}' to {target_file} ---")