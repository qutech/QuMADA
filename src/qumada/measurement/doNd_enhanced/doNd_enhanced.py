# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Bertha Lab Setup
# - Daniel Grothe
# - Max Lennart Oberländer
# - Sionludi Lab
# - Till Huckemann


from __future__ import annotations

import logging
import operator
import sys
import time
import warnings
from collections.abc import Sequence
from functools import partial
from typing import Any, Callable, Optional, Union

import matplotlib.axes
import matplotlib.colorbar
import numpy as np
from qcodes import config
from qcodes.dataset.data_set_protocol import DataSetProtocol
from qcodes.dataset.descriptions.detect_shapes import detect_shape_of_measurement
from qcodes.dataset.descriptions.versioning.rundescribertypes import Shapes
from qcodes.dataset.dond.do_nd_utils import (
    _handle_plotting,
    _register_actions,
    _register_parameters,
    _set_write_period,
)

try:
    from qcodes.dataset.dond.do_nd_utils import _catch_interrupts
except ImportError:
    from qcodes.dataset.dond.do_nd_utils import catch_interrupts as _catch_interrupts

from qcodes.dataset.experiment_container import Experiment
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.threading import (  # SequentialParamsCaller,; ThreadPoolParamsCaller,
    process_params_meas,
)
from qcodes.parameters import ParameterBase
from tqdm.auto import tqdm

ActionsT = Sequence[Callable[[], None]]
BreakConditionT = Callable[[], bool]

ParamMeasT = Union[ParameterBase, Callable[[], None]]

AxesTuple = tuple[matplotlib.axes.Axes, matplotlib.colorbar.Colorbar]
AxesTupleList = tuple[list[matplotlib.axes.Axes], list[Optional[matplotlib.colorbar.Colorbar]]]
AxesTupleListWithDataSet = tuple[
    DataSetProtocol,
    list[matplotlib.axes.Axes],
    list[Optional[matplotlib.colorbar.Colorbar]],
]
MultiAxesTupleListWithDataSet = tuple[
    tuple[DataSetProtocol, ...],
    tuple[list[matplotlib.axes.Axes], ...],
    tuple[list[Optional[matplotlib.colorbar.Colorbar]], ...],
]

LOG = logging.getLogger(__name__)


def do1d_parallel(
    *param_meas: ParamMeasT,
    param_set: list[ParamMeasT],
    setpoints: np.array,
    delay: float,
    enter_actions: ActionsT = (),
    exit_actions: ActionsT = (),
    write_period: float | None = None,
    measurement_name: str = "",
    exp: Experiment | None = None,
    do_plot: bool | None = None,
    use_threads: bool | None = None,
    additional_setpoints: Sequence[ParamMeasT] = tuple(),
    show_progress: None | None = None,
    log_info: str | None = None,
    break_condition: BreakConditionT | None = None,
    backsweep_after_break: bool = False,
    wait_after_break: float = 0,
) -> AxesTupleListWithDataSet:
    """
    Performs a 1D scan of all ``param_set`` according to "setpoints" in parallel,
    measuring param_meas at each step. In case param_meas is
    an ArrayParameter this is effectively a 2d scan.

    Args:
        param_set: The QCoDeS parameter to sweep over
        setpoints: Array of setpoints for param_set
        delay: Delay after setting parameter before measurement is performed
        *param_meas: Parameter(s) to measure at each step or functions that
          will be called at each step. The function should take no arguments.
          The parameters and functions are called in the order they are
          supplied.
        enter_actions: A list of functions taking no arguments that will be
            called before the measurements start
        exit_actions: A list of functions taking no arguments that will be
            called after the measurements ends
        write_period: The time after which the data is actually written to the
            database.
        additional_setpoints: A list of setpoint parameters to be registered in
            the measurement but not scanned. Not supported right now.
        measurement_name: Name of the measurement. This will be passed down to
            the dataset produced by the measurement. If not given, a default
            value of 'results' is used for the dataset.
        exp: The experiment to use for this measurement.
        do_plot: should png and pdf versions of the images be saved after the
            run. If None the setting will be read from ``qcodesrc.json`
        use_threads: If True measurements from each instrument will be done on
            separate threads. If you are measuring from several instruments
            this may give a significant speedup.
        show_progress: should a progress bar be displayed during the
            measurement. If None the setting will be read from ``qcodesrc.json`
        log_info: Message that is logged during the measurement. If None a default
            message is used.
        backsweep_after_break: If true, after a break condition is fulfilled a
            reversed sweep starting from the measurement point at which the
            condition was fulfilled and stopping at the first setpoint of the
            measurement is performed.

    Returns:
        The QCoDeS dataset.
    """
    if do_plot is None:
        do_plot = config.dataset.dond_plot
    if show_progress is None:
        show_progress = config.dataset.dond_show_progress

    meas = Measurement(name=measurement_name, exp=exp)
    if log_info is not None:
        meas._extra_log_info = log_info
    else:
        meas._extra_log_info = "Using 'qcodes.utils.dataset.doNd.do1d'"

    all_setpoint_params = (param_set[0],) + tuple(s for s in additional_setpoints)

    measured_parameters = tuple(param for param in param_meas if isinstance(param, ParameterBase))
    measured_params = (*param_set[1:], *param_meas)
    setpoints_length = len(setpoints)
    if backsweep_after_break:
        setpoints_length *= 2
    try:
        loop_shape = tuple(1 for _ in additional_setpoints) + (setpoints_length,)
        shapes: Shapes = detect_shape_of_measurement(measured_params, loop_shape)
        print(loop_shape)
    except TypeError:
        LOG.exception(f"Could not detect shape of {measured_parameters} " f"falling back to unknown shape.")
        shapes = None

    _register_parameters(meas, all_setpoint_params, setpoints=None)
    _register_parameters(meas, measured_params, setpoints=all_setpoint_params, shapes=shapes)
    _set_write_period(meas, write_period)
    _register_actions(meas, enter_actions, exit_actions)

    original_delay = param_set[0].post_delay
    param_set[0].post_delay = delay

    if use_threads is None:
        use_threads = config.dataset.use_threads

    tracked_setpoints = list()
    # do1D enforces a simple relationship between measured parameters
    # and set parameters. For anything more complicated this should be
    # reimplemented from scratch

    with _catch_interrupts() as interrupted, meas.run() as datasaver:
        dataset = datasaver.dataset
        additional_setpoints_data = process_params_meas(additional_setpoints)

        # flush to prevent unflushed print's to visually interrupt tqdm bar
        # updates
        sys.stdout.flush()
        sys.stderr.flush()

        sweep_data = {}
        for channel in measured_params:
            sweep_data[channel]: list[float] = []

        for set_point in tqdm(setpoints, disable=not show_progress):
            for param in param_set:
                param.set(set_point)
            tracked_setpoints.append(set_point)
            time.sleep(delay)
            datasaver.add_result(
                (param_set[0], set_point),
                *process_params_meas(measured_params, use_threads=use_threads),
                *additional_setpoints_data,
            )

            for channel in measured_params:
                sweep_data[channel].append(channel.get())
            if callable(break_condition):
                if break_condition(sweep_data):
                    if backsweep_after_break:
                        tracked_setpoints.reverse()
                        time.sleep(wait_after_break)
                        for set_point in tqdm(tracked_setpoints, disable=not show_progress):
                            for param in param_set:
                                param.set(set_point)
                            datasaver.add_result(
                                (param_set[0], set_point),
                                *process_params_meas(measured_params, use_threads=use_threads),
                                *additional_setpoints_data,
                            )
                        break
                    else:
                        warnings.warn("Break condition was met.")
                        break

    param_set[0].post_delay = original_delay

    return _handle_plotting(dataset, do_plot, interrupted())


def do1d_parallel_asym(
    *param_meas: ParamMeasT,
    param_set: list[ParamMeasT],
    setpoints: list[np.array],
    delay: float,
    enter_actions: ActionsT = (),
    exit_actions: ActionsT = (),
    write_period: float | None = None,
    measurement_name: str = "",
    exp: Experiment | None = None,
    do_plot: bool | None = None,
    use_threads: bool | None = None,
    additional_setpoints: Sequence[ParamMeasT] = tuple(),
    show_progress: None | None = None,
    log_info: str | None = None,
    break_condition: BreakConditionT | None = None,
    backsweep_after_break: bool = False,
    wait_after_break: float = 0,
) -> AxesTupleListWithDataSet:
    """
    Performs a 1D scan of all ``param_set`` according to "setpoints" in parallel,
    measuring param_meas at each step. In case param_meas is
    an ArrayParameter this is effectively a 2d scan.

    Args:
        param_set: The QCoDeS parameter to sweep over
        setpoints: Array of setpoints for param_set
        delay: Delay after setting parameter before measurement is performed
        *param_meas: Parameter(s) to measure at each step or functions that
          will be called at each step. The function should take no arguments.
          The parameters and functions are called in the order they are
          supplied.
        enter_actions: A list of functions taking no arguments that will be
            called before the measurements start
        exit_actions: A list of functions taking no arguments that will be
            called after the measurements ends
        write_period: The time after which the data is actually written to the
            database.
        additional_setpoints: A list of setpoint parameters to be registered in
            the measurement but not scanned. Not supported right now.
        measurement_name: Name of the measurement. This will be passed down to
            the dataset produced by the measurement. If not given, a default
            value of 'results' is used for the dataset.
        exp: The experiment to use for this measurement.
        do_plot: should png and pdf versions of the images be saved after the
            run. If None the setting will be read from ``qcodesrc.json`
        use_threads: If True measurements from each instrument will be done on
            separate threads. If you are measuring from several instruments
            this may give a significant speedup.
        show_progress: should a progress bar be displayed during the
            measurement. If None the setting will be read from ``qcodesrc.json`
        log_info: Message that is logged during the measurement. If None a default
            message is used.
        backsweep_after_break: If true, after a break condition is fulfilled a
            reversed sweep starting from the measurement point at which the
            condition was fulfilled and stopping at the first setpoint of the
            measurement is performed.

    Returns:
        The QCoDeS dataset.
    """
    if do_plot is None:
        do_plot = config.dataset.dond_plot
    if show_progress is None:
        show_progress = config.dataset.dond_show_progress

    meas = Measurement(name=measurement_name, exp=exp)
    if log_info is not None:
        meas._extra_log_info = log_info
    else:
        meas._extra_log_info = "Using 'qcodes.utils.dataset.doNd.do1d'"

    all_setpoint_params = (*param_set,) + tuple(s for s in additional_setpoints)
    all_setpoint_params = [
        *param_set,
    ] + [s for s in additional_setpoints]
    if len(all_setpoint_params) != len(setpoints):
        raise NotImplementedError("Setpoints list length does not match number of dynamic parameters")

    for entry in setpoints:
        if len(entry) != len(setpoints[0]):
            raise NotImplementedError(
                "Setpoints for different parameters have different length. This is not yet supported"
            )
    measured_parameters = tuple(param for param in param_meas if isinstance(param, ParameterBase))
    measured_params = param_meas
    setpoints_length = len(setpoints[0])
    if backsweep_after_break:
        setpoints_length *= 2
    try:
        loop_shape = tuple(1 for _ in additional_setpoints) + (setpoints_length,)
        shapes: Shapes = detect_shape_of_measurement(measured_params, loop_shape)
        print(loop_shape)
    except TypeError:
        LOG.exception(f"Could not detect shape of {measured_parameters} " f"falling back to unknown shape.")
        shapes = None

    _register_parameters(meas, [all_setpoint_params[0]], setpoints=None)
    _register_parameters(meas, all_setpoint_params[1:], setpoints=(all_setpoint_params[0],), shapes=shapes)
    print(f"Measured parameters: {measured_parameters}")
    _register_parameters(meas, measured_params, setpoints=(all_setpoint_params[0],), shapes=shapes)
    _set_write_period(meas, write_period)
    _register_actions(meas, enter_actions, exit_actions)

    original_delay = param_set[0].post_delay
    param_set[0].post_delay = delay

    if use_threads is None:
        use_threads = config.dataset.use_threads

    tracked_setpoints = list([] for _ in param_set)
    # do1D enforces a simple relationship between measured parameters
    # and set parameters. For anything more complicated this should be
    # reimplemented from scratch
    with _catch_interrupts() as interrupted, meas.run() as datasaver:
        dataset = datasaver.dataset
        additional_setpoints_data = process_params_meas(additional_setpoints)

        # flush to prevent unflushed print's to visually interrupt tqdm bar
        # updates
        sys.stdout.flush()
        sys.stderr.flush()

        for j in range(len(setpoints[0])):
            datasaver_list = []
            for i in range(len(param_set)):
                param_set[i].set(setpoints[i][j])
                tracked_setpoints[i].append(setpoints[i][j])
                time.sleep(delay)
                datasaver_list.append((param_set[i], setpoints[i][j]))
            datasaver.add_result(
                *datasaver_list,
                *process_params_meas(measured_params, use_threads=use_threads),
                *additional_setpoints_data,
            )
            if callable(break_condition):
                if break_condition():
                    if backsweep_after_break:
                        # tracked_setpoints.reverse()
                        # need nested reverse?
                        print('Break condition was met. Starting backsweep!')
                        tracked_setpoints = [setpoints[::-1] for setpoints in tracked_setpoints]
                        time.sleep(wait_after_break)
                        for j in range(len(tracked_setpoints[0])):
                            datasaver_backward_list = []
                            for i, param in enumerate(param_set):
                                # tqdm might not work anymore as intended; need j instead of object?
                                # for set_point in tqdm(tracked_setpoints, disable=not show_progress):
                                param.set(tracked_setpoints[i][j])
                                datasaver_backward_list.append((param_set[i], tracked_setpoints[i][j]))
                            datasaver.add_result(
                                *datasaver_backward_list,
                                *process_params_meas(measured_params, use_threads=use_threads),
                                *additional_setpoints_data,
                            )
                        break
                    else:
                        warnings.warn("Break condition was met.")
                        print('Break condition was met. This meassage pops up alone \
                               if there is some issue with warning.warn')
                        break

    param_set[0].post_delay = original_delay

    return _handle_plotting(dataset, do_plot, interrupted())


def _interpret_breaks(break_conditions: list, **kwargs) -> Callable[[], bool] | None:
    """
    Translates break conditions and returns callable to check them.

    Parameters
    ----------
    break_conditions : List of dictionaries containing:
            "channel": Gettable parameter to check
            "break_condition": String specifying the break condition.
                    Syntax:
                        Parameter to check: only "val" supported so far.
                        Comparator: "<",">" or "=="
                        Value: float
                    The parts have to be separated by blanks.

    **kwargs : TYPE
        DESCRIPTION.

    Returns
    -------
    Callable
        Function, that returns a boolean, True if break conditions are fulfilled.

    """

    def eval_binary_expr(op1: Any, oper: str, op2: Any) -> bool:
        # evaluates the string "op1 [operator] op2
        # supports <, > and == as operators
        ops = {
            ">": operator.gt,
            "<": operator.lt,
            "==": operator.eq,
        }
        # Why convert explicitly to float?
        # op1, op2 = float(op1), float(op2)
        return ops[oper](op1, op2)

    def check_conditions(conditions: list[Callable[[], bool]]):
        for cond in conditions:
            if cond():
                return True
        return False

    conditions = []
    # Create break condition callables
    for cond in break_conditions:
        ops = cond["break_condition"].split(" ")
        if ops[0] != "val":
            raise NotImplementedError(
                'Only parameter values can be used for breaks in this version. Use "val" for the break condition.'
            )

        def f():
            return partial(eval_binary_expr, cond["channel"].get_latest(), ops[1], float(ops[2]))()

        conditions.append(f)
    return partial(check_conditions, conditions) if conditions else None


def _dev_interpret_breaks(break_conditions: list, sweep_values: dict, **kwargs) -> Callable[[], bool] | None:
    """
    Translates break conditions and returns callable to check them.

    Parameters
    ----------
    break_conditions : List of dictionaries containing:
            "channel": Gettable parameter to check
            "break_condition": String specifying the break condition.
                    Syntax:
                        Parameter to check: only "val" supported so far.
                        Comparator: "<",">" or "=="
                        Value: float
                    The parts have to be separated by blanks.

    **kwargs : TYPE
        DESCRIPTION.

    Returns
    -------
    Callable
        Function, that returns a boolean, True if break conditions are fulfilled.

    """

    def return_false():
        return False

    def eval_binary_expr(op1: Any, oper: str, op2: Any) -> bool:
        # evaluates the string "op1 [operator] op2
        # supports <, > and == as operators
        ops = {
            ">": operator.gt,
            "<": operator.lt,
            "==": operator.eq,
        }
        # Why convert explicitly to float?
        # op1, op2 = float(op1), float(op2)
        return ops[oper](op1, op2)

    def check_conditions(conditions: list[Callable[[], bool]]):
        for cond in conditions:
            if cond():
                return True
        return False

    conditions = []
    # Create break condition callables
    for cond in break_conditions:
        ops = cond["break_condition"].split(" ")
        data = sweep_values[cond["channel"]]
        if ops[0] == "val":

            def f():
                return partial(eval_binary_expr, data[-1], ops[1], float(ops[2]))()

        elif ops[0] == "grad":
            if int(ops[1]) >= len(data):
                f = return_false
            elif float(ops[1]) < len(data):
                if data[len(data) - 1] != 0:
                    dx = (data[len(data) - 1] - data[len(data) - 1 - int(ops[1])]) / data[len(data) - 1]

                    def f():
                        return partial(eval_binary_expr, dx, ops[2], float(ops[3]))()

                else:
                    f = return_false
        else:
            raise NotImplementedError("NOT IMPLEMENTED")
        conditions.append(f)
    return check_conditions(conditions) if conditions else None
