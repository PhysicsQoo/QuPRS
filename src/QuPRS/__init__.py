# __init__.py

from typing import Tuple, Union

try:
    from ._version import __version__, __version_tuple__, version, version_tuple
except ImportError:
    # Fallback for development mode or when setuptools_scm hasn't generated the file yet
    import warnings

    warnings.warn(
        "Version not found in _version.py, likely in development mode or during "
        "sdist build.",
        stacklevel=2,
    )
    __version__ = "0.0.0+unknown"
    __version_tuple__: Tuple[Union[int, str], ...] = (0, 0, 0, "unknown")
    version = __version__
    version_tuple = __version_tuple__

__all__ = [
    "__version__",
    "__version_tuple__",
    "version",
    "version_tuple",
]
