import contextlib
import functools
import math
import warnings
from collections.abc import Sequence
from typing import Optional, Protocol, Union

import numpy as np
from qcodes import Measurement
from qcodes.dataset.data_set import DataSet
from qcodes.dataset.descriptions.rundescriber import RunDescriber
from qcodes.dataset.descriptions.param_spec import ParamSpecBase
from qcodes.parameters import ParameterBase

import matplotlib.pyplot as plt

import xarray as xr


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

        self._xarray_builder_error = None
        self._xarray_builder = None

    def _process_xarr(self, xarr, description: RunDescriber = None):
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

        if self._xarray_builder_error is None and self._xarray_builder is None:
            try:
                self._xarray_builder = XArrayBuilder(self.dataset.description)
            except Exception as e:
                warnings.warn(f"Could not build xarray dataset: {e}")
                self._xarray_builder_error = e
                raise # TODO: remove debug

        if self._xarray_builder_error is None and self._xarray_builder is not None:
            try:
                self._xarray_builder.add_result(*args)
            except Exception as e:
                warnings.warn(f"Could not add result to xarray dataset: {e}")
                self._xarray_builder_error = e
                raise # TODO: remove debug

        if self.plot_target is not None:
            if self._xarray_builder_error is None and self._xarray_builder is not None:
                xarr = self._xarray_builder.xarr
                self.plot_target(xarr)
                return

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


def _empty_variable_from_spec(param_spec: ParamSpecBase, shape: tuple, dims: Sequence[str]):
    if param_spec.type != 'numeric':
        warnings.warn(f"Unhandled parameter type: {param_spec.type!r}")

    assert len(shape) == len(dims)

    empty_data = np.full(shape=shape, fill_value=np.nan)
    attrs = {
        "long_name": param_spec.label,
        "standard_name": param_spec.name,
        "units": param_spec.unit,
    }
    return xr.Variable(
        dims=dims,
        data=empty_data,
        attrs=attrs,
    )


def _empty_xarray_from_description(description: RunDescriber):
    if description.interdeps.standalones:
        raise NotImplementedError("standalone parameters are not supported yet", description.interdeps.standalones)

    if description.interdeps.inferences:
        raise NotImplementedError("inferred parameters are not supported yet", description.interdeps.inferences)

    coords = {}
    data_vars = {}
    for measured, dependencies in description.interdeps.dependencies.items():

        shape = description.shapes[measured.name]
        measured_dims = []

        assert len(shape) == len(dependencies)
        for dep, size in zip(dependencies, shape):
            dim_name = dep.name
            if dim_name in coords:
                if len(coords[dim_name]) != size:
                    raise NotImplementedError("different sizes (and values)"
                                              "for the same parameter are not supported yet")
            else:
                coords[dim_name] = _empty_variable_from_spec(dep, (size,), (dim_name,))
            measured_dims.append(dim_name)

        measured_var = _empty_variable_from_spec(measured, shape, measured_dims)
        data_vars[measured.name] = measured_var

    xarr = xr.Dataset(data_vars=data_vars, coords=coords)
    return xarr

class XArrayBuilder:
    def __init__(self, description: RunDescriber):
        self.description = description
        self.xarr = _empty_xarray_from_description(description)

        self._counts = {name: 0 for name in self.xarr.keys()}
        self._index_values = {
            name: coord.values for name, coord in self.xarr.coords.items()
        }

    def add_result(self, *args):
        values = {parameter.full_name: value for parameter, value in args}
        if len(values) != len(args):
            raise ValueError("duplicate parameter names")

        for measure_param in self.xarr.keys():
            if measure_param not in values:
                continue
            count = self._counts[measure_param]

            measure_data = self.xarr[measure_param]
            measure_values = measure_data.values
            shape = measure_values.shape

            # this is faster than np.unravel_index
            idx = []
            remaining = count
            for dim in shape:
                dim_idx, remaining = divmod(remaining, dim)
                idx.append(dim_idx)
            idx = tuple(idx)
            measure_values[idx] = values[measure_param]

            to_update = {}
            for dim_idx, dim_var in zip(idx, measure_data.coords.values()):
                dim_name = dim_var.name
                new_val = values[dim_name]
                dim_values = self._index_values[dim_name]
                old_val = dim_values[dim_idx]
                if old_val != old_val:
                    # old value is nan
                    dim_values[dim_idx] = new_val
                    to_update[dim_name] = dim_values
            if to_update:
                measure_data.assign_coords(to_update)
            self._counts[measure_param] += 1

