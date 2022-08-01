# pylint: disable=missing-function-docstring
import pytest
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.instrument.visa import VisaInstrument
from qcodes.tests.instrument_mocks import DummyInstrument

from qtools.instrument.instrument import is_instrument_class


@pytest.fixture(name="instrument")
def fixture_instrument() -> Instrument:
    return DummyInstrument("instrument", ["v1", "v2"])


def test_is_instrument():
    assert is_instrument_class(Instrument)
    assert is_instrument_class(DummyInstrument)
    assert is_instrument_class(VisaInstrument)
    assert not is_instrument_class(Parameter)
