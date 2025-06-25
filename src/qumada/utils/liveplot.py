import contextlib
import functools
from collections.abc import Sequence
from typing import Protocol

from qcodes import Measurement
from qcodes.parameters import ParameterBase
from qcodes.dataset.data_set import DataSet


class MeasurementAndPlot:
    def __init__(self, *, name: str, gui = None):
        self.qcodes_measurement = Measurement(name=name)
        self.gui = gui


    def register_parameter(
        self, parameter: ParameterBase, setpoints: Sequence[str | ParameterBase] | None = None, **kwargs
    ):
        self.qcodes_measurement.register_parameter(parameter, setpoints, **kwargs)

    @contextlib.contextmanager
    def run(self):
        if self.gui is not None:
            # here we could add some more arguments in the future
            plot_target = self.gui
        else:
            plot_target = None

        with self.qcodes_measurement.run() as qcodes_datasaver:
            yield DataSaverAndPlotter(self, qcodes_datasaver, plot_target)


class DataSaverAndPlotter:
    def __init__(self, parent: MeasurementAndPlot, qcodes_datasaver, plot_target: callable):
        self._parent = parent
        self.qcodes_datasaver = qcodes_datasaver
        self.plot_target = plot_target

    def add_result(self, *args):
        self.qcodes_datasaver.add_result(*args)
        if self.plot_target is not None:
            self.plot_target(self.dataset.to_xarray_dataset())

    @property
    def dataset(self) -> DataSet:
        return self.qcodes_datasaver.dataset
