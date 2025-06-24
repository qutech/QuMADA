import contextlib
from typing import Sequence

from qcodes import Measurement
from qcodes.parameters import ParameterBase


class MeasurementAndPlot:
    def __init__(self, *, name: str):
        self.qcodes_measurement = Measurement(name=name)

    def register_parameter(
        self,
        parameter: ParameterBase,
        setpoints: Sequence[str | ParameterBase] | None = None,
        **kwargs):
        self.qcodes_measurement.register_parameter(parameter, setpoints, **kwargs)

    @contextlib.contextmanager
    def run(self):
        with self.qcodes_measurement.run() as qcodes_datasaver:
            yield DataSaverAndPlotter(self, qcodes_datasaver)


class DataSaverAndPlotter:
    def __init__(self, parent: MeasurementAndPlot, qcodes_datasaver):
        self._parent = parent
        self.qcodes_datasaver = qcodes_datasaver

    def add_result(self, *args):
        self.qcodes_datasaver.add_result(*args)

