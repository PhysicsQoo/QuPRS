# __init__.py

try:
    from ._version import * 
except ImportError:
    # Fallback for development mode or when setuptools_scm hasn't generated the file yet
    import warnings
    warnings.warn("Version not found in _version.py, likely in development mode or during sdist build.", stacklevel=2)
    __version__ = "0.0.0+unknown"
    __version_tuple__ = (0, 0, 0, "unknown")
    version = __version__
    version_tuple = __version_tuple__