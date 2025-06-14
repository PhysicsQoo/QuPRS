from importlib import resources
from pathlib import Path


def WMC() -> Path:
    return resources.files(__name__).joinpath("gpmc")
