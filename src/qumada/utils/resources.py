# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe


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
