from __future__ import annotations

import importlib
import pkgutil
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
        try:
            results[full_name] = importlib.import_module(full_name)
        except ImportError as e:
            pass
            # print(f"ImportError for {full_name}: {e}")
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results
