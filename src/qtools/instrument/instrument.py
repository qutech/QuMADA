import inspect

from qcodes.instrument.base import Instrument


def is_instrument_class(o):
    """True, if class is of type Instrument or a subclass of Instrument"""
    return inspect.isclass(o) and issubclass(o, Instrument)
