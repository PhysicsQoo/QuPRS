# hatch_build.py
import os
import shutil
import subprocess
import platform
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """
        Custom build hook for cross-platform compilation of the GPMC binary.

        This hook is invoked by Hatch during the build process. It performs the following steps:
        1. Prepares the build environment and sets platform-specific environment variables.
        2. Configures and builds the GPMC binary using CMake and Make.
        3. Copies the resulting binary into the Python package's utils directory for distribution.

        Raises:
            FileNotFoundError: If the GPMC source directory or the compiled binary is missing.
            subprocess.CalledProcessError: If the build commands fail.
        """
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, 'GPMC')
        build_dir = os.path.join(gpmc_src_path, 'build')

        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError(
                "GPMC source directory not found. Did you forget to run 'git submodule update --init'?"
            )

        # 1. Prepare build environment variables
        build_env = os.environ.copy()
        os_name = platform.system()

        if os_name == "Darwin":  # Darwin is the core name for macOS
            print("--- [Hatch Hook] Configuring build environment for macOS ---")
            # On Apple Silicon, Homebrew is typically installed at /opt/homebrew.
            # On Intel Macs, it's usually /usr/local. We use the CI runner's Homebrew prefix if available.
            brew_prefix = build_env.get("HOMEBREW_PREFIX", "/opt/homebrew")
            
            # Set CPPFLAGS to specify header file search paths for the compiler
            cppflags = (
                f"-I{brew_prefix}/opt/gmp/include "
                f"-I{brew_prefix}/opt/mpfr/include "
                f"-I{brew_prefix}/opt/zlib/include"
            )
            # Set LDFLAGS to specify library search paths for the linker
            ldflags = (
                f"-L{brew_prefix}/opt/gmp/lib "
                f"-L{brew_prefix}/opt/mpfr/lib "
                f"-L{brew_prefix}/opt/zlib/lib"
            )
            
            build_env['CPPFLAGS'] = cppflags
            build_env['LDFLAGS'] = ldflags
            print(f"macOS CPPFLAGS set to: {cppflags}")
            print(f"macOS LDFLAGS set to: {ldflags}")

        # Remove any existing build directory to ensure a clean build
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        # 2. Prepare and run the cmake command to configure the build
        cmake_args = [
            'cmake',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            '..'
        ]
        
        print(f"Running command: {' '.join(cmake_args)} in {build_dir}")
        subprocess.check_call(cmake_args, cwd=build_dir, env=build_env)

        # 3. Run 'make' to compile the binary
        print(f"Running command: make in {build_dir}")
        subprocess.check_call(['make'], cwd=build_dir, env=build_env)

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name} ---")

        # 4. Copy the compiled binary to the package's utils directory
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