# pylint: disable=missing-function-docstring
import pytest
from qcodes.instrument import Instrument, VisaInstrument
from qcodes.parameters import Parameter
from qcodes.tests.instrument_mocks import DummyInstrument

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
    MFLI = pytest.importorskip("qtools.instrument.custom_drivers.ZI.MFLI")
    assert is_instrument_class(MFLI.MFLI)
