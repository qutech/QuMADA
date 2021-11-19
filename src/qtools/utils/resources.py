from __future__ import annotations

import importlib.resources as res
from pathlib import Path
from types import ModuleType


def import_resources(
    package: res.Package, ext: str = "*", recursive: bool = True
) -> list[res.Resource]:
    """
    Loads resource files from a given package and returns them as list of Path-objects.

    Args:
        package: Package to load the resources from.
        ext: File extension, eg. "*.json". Defaults to "*".
        recursive: Shall resources also load from subdirectories? Defaults to True.

    Returns:
        List of the resources' paths.
    """
    path: Path = res.files(package)
    if recursive:
        return list(path.rglob(ext))
    else:
        return list(path.glob(ext))
