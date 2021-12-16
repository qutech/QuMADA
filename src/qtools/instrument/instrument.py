import inspect

from qcodes.instrument.base import Instrument


def is_instrument(o):
    return inspect.isclass(o) and issubclass(o, Instrument)
