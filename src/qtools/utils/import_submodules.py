from __future__ import annotations

import importlib
import pkgutil
from contextlib import suppress
from types import ModuleType


def import_submodules(
    package: str | ModuleType, recursive: bool = True
) -> dict[str, ModuleType]:
    """Import all submodules of a module, recursively, including subpackages"""
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        with suppress(ValueError, ImportError):
            results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results
