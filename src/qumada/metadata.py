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

from datetime import datetime
from typing import Protocol


class Metadata(Protocol):
    """Protocol for a Metadata object. Defines the methods to handle specific metadata portions collected with QuMADA."""

    def add_terminal_mapping(self, mapping: str, name: str):
        """Adds metadata of the mapping between terminals and instrument parameters as a (JSON) string."""

    def add_script_to_metadata(self, script: str, language: str, name: str):
        """Adds metadata of the used measurement script."""

    def add_parameters_to_metadata(self, parameters: str, name: str):
        """Adds parameters and their settings to metadata."""

    def add_datetime_to_metadata(self, dt: datetime):
        """Adds datetime to metadata."""

    def add_data_to_metadata(self, location: str, datatype: str, name: str):
        """Adds metadata related to the measurement data to metadata."""


class BasicMetadata:
    """Example implementation of a MetadataHandler."""

    def __init__(self):
        self.metadata = {}

    def add_terminal_mapping(self, mapping: str, name: str = "mapping"):
        self.metadata[name] = mapping

    def add_script_to_metadata(self, script: str, language: str, name: str = "script"):
        self.metadata[name] = (language, script)

    def add_parameters_to_metadata(self, parameters: str, name: str = "parameters"):
        self.metadata[name] = parameters

    def add_datetime_to_metadata(self, dt: datetime):
        self.metadata["datetime"] = dt

    def add_data_to_metadata(self, location: str, datatype: str, name: str = "data"):
        self.metadata[name] = (datatype, location)
