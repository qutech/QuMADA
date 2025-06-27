import contextlib
import functools
import warnings
from collections.abc import Sequence
from typing import Optional, Protocol, Union

from qcodes import Measurement
from qcodes.dataset.data_set import DataSet
from qcodes.parameters import ParameterBase


class MeasurementAndPlot:
    UPDATE_PERIOD = 0.01

    def __init__(self, *, script: "MeasurementScript", name: str, gui=None, **kwargs):
        self.qcodes_measurement = Measurement(name=name, **kwargs)
        self.qcodes_measurement.write_period = self.UPDATE_PERIOD
        self.gui = gui
        self.script = script
        self._shapes = None

    def register_parameter(
        self, parameter: ParameterBase, setpoints: Optional[Sequence[Union[str, ParameterBase]]] = None, **kwargs
    ):
        self.qcodes_measurement.register_parameter(parameter, setpoints, **kwargs)

    def set_shapes(self, shapes):
        self.qcodes_measurement.set_shapes(shapes=shapes)
        self._shapes = shapes

    @contextlib.contextmanager
    def run(self, **kwargs):
        if self.gui is not None:
            # here we could add some more arguments in the future
            plot_target = self.gui
        else:
            plot_target = None

        with self.qcodes_measurement.run(**kwargs) as qcodes_datasaver:
            yield DataSaverAndPlotter(self, qcodes_datasaver, plot_target=plot_target, shapes=self._shapes)


class DataSaverAndPlotter:
    def __init__(self, parent: MeasurementAndPlot, qcodes_datasaver, shapes, plot_target: callable):
        self._parent = parent
        self.qcodes_datasaver = qcodes_datasaver
        self.plot_target = plot_target
        self._shapes = shapes
        self._last_plot_call = None

    def _process_xarr(self, xarr):
        terminal_parameters = self._parent.script.terminal_parameters
        rename_dict = {
            parameter.full_name: parameter.label
            for parameters in terminal_parameters.values()
            for parameter in parameters.values()
            if parameter.full_name in xarr.variables
        }
        renamed = xarr.rename(rename_dict)
        return renamed

    def add_result(self, *args):
        self.qcodes_datasaver.add_result(*args)
        if self.plot_target is not None:
            # the following logic only generates a dataset and sends data to the plotter
            # if the QCoDeS internal _last_save_time attribute was updated.
            last_save_time = getattr(self.qcodes_datasaver, "_last_save_time", None)
            if last_save_time is None:
                warnings.warn(
                    "Current QCoDeS version is not compatible with efficient live plotting. "
                    "The plot is updated even if the data did not change.",
                    category=RuntimeWarning,
                )
                update_plot = True
            elif last_save_time != self._last_plot_call:
                update_plot = True
                self._last_plot_call = last_save_time
            else:
                update_plot = False

            if update_plot:
                xarr = self.dataset.to_xarray_dataset()
                processed = self._process_xarr(xarr)
                self.plot_target(processed)

    @property
    def dataset(self) -> DataSet:
        return self.qcodes_datasaver.dataset
