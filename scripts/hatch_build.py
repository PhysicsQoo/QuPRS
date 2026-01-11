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
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
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

    def download_ganak(self, dest_path):
        """
        Downloads the pre-compiled static Ganak binary from GitHub Releases (ZIP format).
        Detects OS and Architecture to select the correct file.
        """
        import urllib.request
        import zipfile
        import stat
        import tempfile

        os_name = platform.system()
        machine = platform.machine().lower()

        # Map to Ganak release naming convention
        # ganak-linux-amd64.zip
        # ganak-linux-arm64.zip
        # ganak-mac-arm64.zip
        # ganak-mac-x86_64.zip
        
        target_os = ""
        target_arch = ""

        if os_name == "Linux":
            target_os = "linux"
            if machine in ["x86_64", "amd64"]:
                target_arch = "amd64"
            elif machine in ["aarch64", "arm64"]:
                target_arch = "arm64"
        elif os_name == "Darwin":
            target_os = "mac"
            if machine in ["x86_64", "amd64"]:
                target_arch = "x86_64"
            elif machine in ["arm64", "aarch64"]:
                target_arch = "arm64"
        
        if not target_os or not target_arch:
            print(f"--- [Hatch Hook] WARNING: Unsupported platform for Ganak download: {os_name} {machine}. Skipping. ---")
            return

        filename = f"ganak-{target_os}-{target_arch}.zip"
        url = f"https://github.com/meelgroup/ganak/releases/download/v2.5.2/{filename}"

        print(f"--- [Hatch Hook] Downloading Ganak ({filename}) from {url} ---")
        
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path = os.path.join(tmp_dir, filename)
                
                # Download ZIP
                with urllib.request.urlopen(url) as response, open(zip_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                # Extract ZIP
                print(f"--- [Hatch Hook] Extracting {filename} ---")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
                    
                # Find the binary in the extracted files
                # It might be in a subdirectory or just the file itself.
                # Usually it's named 'ganak' inside.
                found_bin = None
                for root, dirs, files in os.walk(tmp_dir):
                    if "ganak" in files:
                        found_bin = os.path.join(root, "ganak")
                        break
                
                if not found_bin:
                    raise FileNotFoundError(f"Could not find 'ganak' binary inside {filename}")

                # Move to destination
                print(f"--- [Hatch Hook] Installing Ganak to {dest_path} ---")
                if os.path.exists(dest_path):
                     os.remove(dest_path)
                shutil.move(found_bin, dest_path)

                # Make executable
                st = os.stat(dest_path)
                os.chmod(dest_path, st.st_mode | stat.S_IEXEC)
                print(f"--- [Hatch Hook] Successfully installed Ganak ---")

        except Exception as e:
            print(f"--- [Hatch Hook] ERROR downloading/installing Ganak: {e} ---")
            if os.path.exists(dest_path):
                os.remove(dest_path)

    def initialize(self, version, build_data):
        print("--- [Hatch Hook] Running custom build step ---")
        PROJECT_ROOT = self.root
        
        tools = [
            {"name": "gpmc", "dir": "GPMC"},
        ]
        
        target_dir = os.path.join(PROJECT_ROOT, "src", "QuPRS", "utils", "wmc_tools")
        os.makedirs(target_dir, exist_ok=True)

        # 1. Download Ganak (Static)
        ganak_dest = os.path.join(target_dir, "ganak")
        if not os.path.exists(ganak_dest):
             self.download_ganak(ganak_dest)
        else:
             print(f"--- [Hatch Hook] Binary ganak found at {ganak_dest}. Skipping download. ---")

        # 2. Build Tools from Source (GPMC)
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
                # GPMC: Build from source
                built_binary_path, _ = self.build_cmake_project(src_path, build_dir, tool["name"])
                
                print(f"--- [Hatch Hook] Installing {tool['name']} to {dest_path} ---")
                shutil.copy(built_binary_path, dest_path)
                
            except Exception as e:
                print(f"--- [Hatch Hook] ERROR building/installing {tool['name']}: {e} ---")
                raise e

        print("--- [Hatch Hook] Build complete ---")