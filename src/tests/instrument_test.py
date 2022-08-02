# pylint: disable=missing-function-docstring
import pytest
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.instrument.visa import VisaInstrument
from qcodes.tests.instrument_mocks import DummyInstrument

from qtools.instrument.custom_drivers.ZI.MFLI import MFLI
from qtools.instrument.instrument import is_instrument_class


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
    assert is_instrument_class(MFLI)
