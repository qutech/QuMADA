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


from typing import runtime_checkable

import pytest

from qtools.metadata import BasicMetadataHandler, MetadataHandler


def test_basic_metadata_handler():
    # Test that the basic metadata handler conforms to the MetadataHandler protocol.
    handler = BasicMetadataHandler()
    assert isinstance(handler, runtime_checkable(MetadataHandler))
