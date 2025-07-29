import platform
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator


@contextmanager
def get_gpmc_path() -> Iterator[Path]:
    """
    Context manager to safely obtain the path to the packaged GPMC binary.

    This function determines the correct binary for the current operating system,
    locates it within the 'QuPRS.utils' package, and yields a valid file path.
    Raises:
        OSError: If the current OS is not supported.
        FileNotFoundError: If the binary is missing from the package.
    """
    os_name = platform.system()
    if os_name == "Linux":
        binary_name = "wmc_tools/gpmc.so"
    elif os_name == "Darwin":  # macOS
        binary_name = "wmc_tools/gpmc.dylib"
    # elif os_name == "Windows":
    #     # Reserved for future Windows support
    #     binary_name = "wmc_tools/gpmc.exe"
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

@contextmanager
def get_ganak_path() -> Iterator[Path]:
    """
    Context manager to safely obtain the path to the packaged GPMC binary.

    This function determines the correct binary for the current operating system,
    locates it within the 'QuPRS.utils' package, and yields a valid file path.
    Raises:
        OSError: If the current OS is not supported.
        FileNotFoundError: If the binary is missing from the package.
    """
    os_name = platform.system()
    if os_name == "Linux":
        binary_name = "wmc_tools/ganak.so"
    elif os_name == "Darwin":  # macOS
        binary_name = "wmc_tools/ganak.dylib"
    # elif os_name == "Windows":
    #     # Reserved for future Windows support
    #     binary_name = "wmc_tools/ganak.exe"
    else:
        raise OSError(f"Unsupported OS: ganak binary not available for {os_name}")

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
def WMC(tool_name="gpmc") -> Iterator[Path]:
    """
    Context manager to obtain the path to the GPMC or Ganak binary based on the tool name.
    Args:
        tool_name (str): The name of the tool, either "gpmc" or "ganak".
    Raises:
        ValueError: If the tool name is not supported.
    """
    if tool_name == "gpmc":
        return get_gpmc_path()
    elif tool_name == "ganak":
        return get_ganak_path()
    else:
        raise ValueError(f"Unsupported tool name: {tool_name}")

