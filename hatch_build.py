# hatch_build.py
import os
import shutil
import subprocess
import platform
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        print("--- [Hatch Hook] Running custom cross-platform build step for GPMC ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, 'GPMC')
        build_dir = os.path.join(gpmc_src_path, 'build')

        if not os.path.isdir(gpmc_src_path):
            # This check is still useful to ensure submodule is present
            raise FileNotFoundError(
                "GPMC source directory not found. Did you forget to run 'git submodule update --init'?"
            )

        # Create a clean build directory
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        # Prepare cmake command
        cmake_args = [
            'cmake',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
        ]
        os_name = platform.system()
        if os_name == "Darwin":
            brew_prefix = os.environ.get("HOMEBREW_PREFIX", "/opt/homebrew")
            cxx_flags = (
                f"-I{brew_prefix}/opt/gmp/include "
                f"-I{brew_prefix}/opt/mpfr/include "
                f"-I{brew_prefix}/opt/zlib/include"
            )
            ld_flags = (
                f"-L{brew_prefix}/opt/gmp/lib "
                f"-L{brew_prefix}/opt/mpfr/lib "
                f"-L{brew_prefix}/opt/zlib/lib"
            )
            cmake_args.append(f'-DCMAKE_CXX_FLAGS={cxx_flags}')
            cmake_args.append(f'-DCMAKE_EXE_LINKER_FLAGS={ld_flags}')
        
        cmake_args.append('..')

        # Run cmake and make
        try:
            print(f"Running cmake command in {build_dir}")
            subprocess.check_call(cmake_args, cwd=build_dir)
            print(f"Running make command in {build_dir}")
            subprocess.check_call(['make'], cwd=build_dir)
        except subprocess.CalledProcessError as e:
            print(f"!!! [Hatch Hook] GPMC compilation failed on {os_name}: {e}")
            raise

        print(f"--- [Hatch Hook] GPMC compiled successfully on {os_name}. Binary is at {build_dir} ---")