# hatch_build.py (Revised v2)
import os
import shutil
import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        print("--- [Hatch Hook] Running custom build step: Compile GPMC binary ---")
        PROJECT_ROOT = self.root
        gpmc_src_path = os.path.join(PROJECT_ROOT, 'GPMC')

        if not os.path.isdir(gpmc_src_path):
            raise FileNotFoundError(
                "GPMC source directory not found. Did you forget to run 'git submodule update --init'?"
            )

        try:
            subprocess.check_call(['./build.sh', 'r'], cwd=gpmc_src_path)
            print("--- [Hatch Hook] GPMC compiled successfully ---")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"!!! [Hatch Hook] GPMC compilation failed: {e}")
            raise

        # --- This is the only modification ---
        # Look for the binary in the build subdirectory of GPMC
        compiled_binary_path = os.path.join(gpmc_src_path, 'build', 'gpmc')
        
        target_dir = os.path.join(PROJECT_ROOT, 'src', 'QuPRS', 'utils')
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, 'gpmc')
        
        # Check if the file exists before copying, to provide a clearer error message
        if not os.path.exists(compiled_binary_path):
            raise FileNotFoundError(
                f"Compilation succeeded, but GPMC binary not found at expected path: {compiled_binary_path}"
            )
            
        shutil.copy(compiled_binary_path, target_file)
        os.chmod(target_file, 0o755)
        
        print(f"--- [Hatch Hook] 'gpmc' binary copied to {target_file} ---")