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

from qtools_metadata.metadata import Metadata
from qtools.measurement.measurement import MeasurementScript


class Job:
    def __init__(
        self,
        metadata: Metadata | None = None,
        script: MeasurementScript | None = None,
        parameters: dict | None = None,
    ):
        self._metadata: Metadata = metadata or Metadata()
        self._script: MeasurementScript = script
        self._parameters: dict = parameters or {}
