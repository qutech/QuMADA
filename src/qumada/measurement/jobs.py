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


from __future__ import annotations

from qumada.measurement.measurement import MeasurementScript
from qumada.metadata import BasicMetadata, Metadata


class Job:
    def __init__(
        self,
        script: MeasurementScript,
        metadata: Metadata | None = None,
        parameters: dict | None = None,
    ):
        self._script: MeasurementScript = script
        self._metadata: Metadata = metadata or BasicMetadata()
        self._parameters: dict = parameters or {}
