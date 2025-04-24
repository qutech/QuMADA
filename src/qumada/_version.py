# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe

# The idea is to get the current version from versioningit for editable installed qumada.
# For built packages, versioningit's onbuild functionality replaces __version__'s value
# with a fixed string.
#
# See
# - https://github.com/QCoDeS/Qcodes/blob/master/qcodes/_version.py
# - https://github.com/jwodder/versioningit/issues/8


def get_version() -> str:
    from pathlib import Path

    import versioningit

    import qumada

    qumada_path = Path(qumada.__file__).parent
    return versioningit.get_version(project_dir=qumada_path.parent.parent)


__version__ = get_version()
