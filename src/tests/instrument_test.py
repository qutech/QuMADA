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


# pylint: disable=missing-function-docstring
import pytest
from qcodes.instrument import Instrument, VisaInstrument
from qcodes.instrument_drivers.mock_instruments import DummyInstrument
from qcodes.parameters import Parameter

from qumada.instrument.instrument import is_instrument_class


@pytest.mark.parametrize(
    "cls,expected",
    [
        (Instrument, True),
        (DummyInstrument, True),
        (VisaInstrument, True),
        (Parameter, False),
    ],
)
def test_is_instrument(cls, expected: bool):
    assert is_instrument_class(cls) is expected


def test_mfli_driver():
    MFLI = pytest.importorskip("qumada.instrument.custom_drivers.ZI.MFLI")
    assert is_instrument_class(MFLI.MFLI)
