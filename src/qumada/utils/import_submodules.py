# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of qtools.
#
# qtools is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# qtools is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# qtools. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe


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
