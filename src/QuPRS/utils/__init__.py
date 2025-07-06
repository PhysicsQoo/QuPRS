import platform
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator


@contextmanager
def get_gpmc_path() -> Iterator[Path]:
    """
    Context manager to safely obtain the path to the packaged GPMC binary.

    Usage example:
        with get_gpmc_path() as gpmc_exe:
            subprocess.run([str(gpmc_exe), "--version"])

    This function determines the correct binary for the current operating system,
    locates it within the 'QuPRS.utils' package, and yields a valid file path.
    Raises:
        OSError: If the current OS is not supported.
        FileNotFoundError: If the binary is missing from the package.
    """
    os_name = platform.system()
    if os_name == "Linux":
        binary_name = "gpmc-linux"
    elif os_name == "Darwin":  # macOS
        binary_name = "gpmc-macos"
    elif os_name == "Windows":
        # Reserved for future Windows support
        binary_name = "gpmc.exe"
    else:
        raise OSError(f"Unsupported OS: GPMC binary not available for {os_name}")

    try:
        # 1. Locate the binary resource within the 'QuPRS.utils' submodule
        gpmc_resource = resources.files("QuPRS.utils").joinpath(binary_name)

        # 2. Use as_file to ensure we get a real file system path
        with resources.as_file(gpmc_resource) as path:
            # 3. Yield the valid path to the context block
            yield path

    except FileNotFoundError:
        raise FileNotFoundError(
            f"GPMC binary '{binary_name}' not found in package 'QuPRS.utils'. "
            "The package might be installed incorrectly or the binary was not included."
        )


# Alias for backward compatibility, if needed
WMC = get_gpmc_path
