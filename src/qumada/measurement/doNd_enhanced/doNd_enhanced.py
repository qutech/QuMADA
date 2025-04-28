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
from collections.abc import Sequence, Mapping
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
    BreakConditionInterrupt,
    _handle_plotting,
    _register_actions,
    _register_parameters,
    _set_write_period,
)
from qcodes.dataset.dond.do_nd import(
    TogetherSweep,
    AbstractSweep,
    cast,
    _parse_dond_arguments,
    ThreadPoolParamsCaller,
    SequentialParamsCaller,
    catch_interrupts,
    _Sweeper,
    _Measurements,
    ExitStack,
    
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
                        print("Break condition was met. Starting backsweep!")
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
                        raise BreakConditionInterrupt("Break condition was met.")

    param_set[0].post_delay = original_delay

    return _handle_plotting(dataset, do_plot, interrupted())

def dond_custom(
    *params: AbstractSweep | TogetherSweep | ParamMeasT | Sequence[ParamMeasT],
    write_period: float | None = None,
    measurement_name: str | Sequence[str] = "",
    exp: Experiment | Sequence[Experiment] | None = None,
    enter_actions: ActionsT = (),
    exit_actions: ActionsT = (),
    do_plot: bool | None = None,
    show_progress: bool | None = None,
    use_threads: bool | None = None,
    additional_setpoints: Sequence[ParameterBase] = tuple(),
    log_info: str | None = None,
    break_condition: BreakConditionT | None = None,
    backsweep_after_break: bool = False,
    wait_after_break: float = 0,
    dataset_dependencies: Mapping[str, Sequence[ParamMeasT]] | None = None,
    in_memory_cache: bool | None = None,
    squeeze: bool = True,
) -> AxesTupleListWithDataSet | MultiAxesTupleListWithDataSet:
    """
    Perform n-dimentional scan from slowest (first) to the fastest (last), to
    measure m measurement parameters. The dimensions should be specified
    as sweep objects, and after them the parameters to measure should be passed.

    Args:
        params: Instances of n sweep classes and m measurement parameters,
            e.g. if linear sweep is considered:

            .. code-block::

                LinSweep(param_set_1, start_1, stop_1, num_points_1, delay_1), ...,
                LinSweep(param_set_n, start_n, stop_n, num_points_n, delay_n),
                param_meas_1, param_meas_2, ..., param_meas_m

            If multiple DataSets creation is needed, measurement parameters should
            be grouped, so one dataset will be created for each group. e.g.:

            .. code-block::

                LinSweep(param_set_1, start_1, stop_1, num_points_1, delay_1), ...,
                LinSweep(param_set_n, start_n, stop_n, num_points_n, delay_n),
                [param_meas_1, param_meas_2], ..., [param_meas_m]

            If you want to sweep multiple parameters together.

            .. code-block::

                TogetherSweep(LinSweep(param_set_1, start_1, stop_1, num_points, delay_1),
                              LinSweep(param_set_2, start_2, stop_2, num_points, delay_2))
                param_meas_1, param_meas_2, ..., param_meas_m


        write_period: The time after which the data is actually written to the
            database.
        measurement_name: Name(s) of the measurement. This will be passed down to
            the dataset produced by the measurement. If not given, a default
            value of 'results' is used for the dataset. If more than one is
            given, each dataset will have an individual name.
        exp: The experiment to use for this measurement. If you create multiple
            measurements using groups you may also supply multiple experiments.
        enter_actions: A list of functions taking no arguments that will be
            called before the measurements start.
        exit_actions: A list of functions taking no arguments that will be
            called after the measurements ends.
        do_plot: should png and pdf versions of the images be saved and plots
            are shown after the run. If None the setting will be read from
            ``qcodesrc.json``
        show_progress: should a progress bar be displayed during the
            measurement. If None the setting will be read from ``qcodesrc.json``
        use_threads: If True, measurements from each instrument will be done on
            separate threads. If you are measuring from several instruments
            this may give a significant speedup.
        additional_setpoints: A list of setpoint parameters to be registered in
            the measurement but not scanned/swept-over.
        log_info: Message that is logged during the measurement. If None a default
            message is used.
        break_condition: Callable that takes no arguments. If returned True,
            measurement is interrupted.
        dataset_dependencies: Optionally describe that measured datasets only depend
            on a subset of the setpoint parameters. Given as a mapping from
            measurement names to Sequence of Parameters. Note that a dataset must
            depend on at least one parameter from each dimension but can depend
            on one or more parameters from a dimension sweeped with a TogetherSweep.
        in_memory_cache:
            Should a cache of the data be kept available in memory for faster
            plotting and exporting. Useful to disable if the data is very large
            in order to save on memory consumption.
            If ``None``, the value for this will be read from ``qcodesrc.json`` config file.
        squeeze: If True, will return a tuple of QCoDeS DataSet, Matplotlib axis,
            Matplotlib colorbar if only one group of measurements was performed
            and a tuple of tuples of these if more than one group of measurements
            was performed. If False, will always return a tuple where the first
            member is a tuple of QCoDeS DataSet(s) and the second member is a tuple
            of Matplotlib axis(es) and the third member is a tuple of Matplotlib
            colorbar(s).

    Returns:
        A tuple of QCoDeS DataSet, Matplotlib axis, Matplotlib colorbar. If
        more than one group of measurement parameters is supplied, the output
        will be a tuple of tuple(QCoDeS DataSet), tuple(Matplotlib axis),
        tuple(Matplotlib colorbar), in which each element of each sub-tuple
        belongs to one group, and the order of elements is the order of
        the supplied groups.

    """
    if do_plot is None:
        do_plot = cast(bool, config.dataset.dond_plot)
    if show_progress is None:
        show_progress = config.dataset.dond_show_progress
        
    tracked_set_events = []

    sweep_instances, params_meas = _parse_dond_arguments(*params)

    sweeper = _Sweeper(sweep_instances, additional_setpoints)

    measurements = _Measurements(
        sweeper,
        measurement_name,
        params_meas,
        enter_actions,
        exit_actions,
        exp,
        write_period,
        log_info,
        dataset_dependencies,
    )

    LOG.info(
        "Starting a doNd with scan with\n setpoints: %s,\n measuring: %s",
        sweeper.all_setpoint_params,
        measurements.measured_all,
    )
    LOG.debug(
        "dond has been grouped into the following datasets:\n%s",
        measurements.groups,
    )

    datasets = []
    plots_axes = []
    plots_colorbar = []
    if use_threads is None:
        use_threads = config.dataset.use_threads

    params_meas_caller = (
        ThreadPoolParamsCaller(*measurements.measured_all)
        if use_threads
        else SequentialParamsCaller(*measurements.measured_all)
    )

    datasavers = []
    interrupted: Callable[  # noqa E731
        [], KeyboardInterrupt | BreakConditionInterrupt | None
    ] = lambda: None
    try:
        with (
            catch_interrupts() as interrupted,
            ExitStack() as stack,
            params_meas_caller as call_params_meas,
        ):
            datasavers = [
                stack.enter_context(
                    group.measurement_cxt.run(in_memory_cache=in_memory_cache)
                )
                for group in measurements.groups
            ]
            additional_setpoints_data = process_params_meas(additional_setpoints)
            for set_events in tqdm(sweeper, disable=not show_progress):
                tracked_set_events.append(set_events)
                LOG.debug("Processing set events: %s", set_events)
                results: dict[ParameterBase, Any] = {}
                for set_event in set_events:
                    if set_event.should_set:
                        set_event.parameter(set_event.new_value)
                        for act in set_event.actions:
                            act()
                        time.sleep(set_event.delay)

                    if set_event.get_after_set:
                        results[set_event.parameter] = set_event.parameter()
                    else:
                        results[set_event.parameter] = set_event.new_value

                meas_value_pair = call_params_meas()
                for meas_param, value in meas_value_pair:
                    results[meas_param] = value

                for datasaver, group in zip(datasavers, measurements.groups):
                    filtered_results_list = [
                        (param, value)
                        for param, value in results.items()
                        if param in group.parameters
                    ]
                    datasaver.add_result(
                        *filtered_results_list,
                        *additional_setpoints_data,
                    )

                if callable(break_condition):
                    if break_condition():
                        if backsweep_after_break and sweeper.shape[0] >= 2*len(tracked_set_events):
                            #datasaver._points_expected += len(tracked_set_events)
                            tracked_set_events.reverse()
                            time.sleep(wait_after_break)
                            for set_events in tqdm(tracked_set_events, disable=not show_progress):
                                LOG.debug("Processing set events: %s", set_events)
                                results: dict[ParameterBase, Any] = {}
                                for set_event in set_events:
                                    if set_event.should_set:
                                        set_event.parameter(set_event.new_value)
                                        for act in set_event.actions:
                                            act()
                                        time.sleep(set_event.delay)

                                    if set_event.get_after_set:
                                        results[set_event.parameter] = set_event.parameter()
                                    else:
                                        results[set_event.parameter] = set_event.new_value

                                meas_value_pair = call_params_meas()
                                for meas_param, value in meas_value_pair:
                                    results[meas_param] = value

                                for datasaver, group in zip(datasavers, measurements.groups):
                                    filtered_results_list = [
                                        (param, value)
                                        for param, value in results.items()
                                        if param in group.parameters
                                    ]
                                    datasaver.add_result(
                                        *filtered_results_list,
                                        *additional_setpoints_data,
                                    )
                                    
                        raise BreakConditionInterrupt("Break condition was met.")
                        
    finally:
        for datasaver in datasavers:
            ds, plot_axis, plot_color = _handle_plotting(
                datasaver.dataset, do_plot, interrupted()
            )
            datasets.append(ds)
            plots_axes.append(plot_axis)
            plots_colorbar.append(plot_color)

    if len(measurements.groups) == 1 and squeeze is True:
        return datasets[0], plots_axes[0], plots_colorbar[0]
    else:
        return tuple(datasets), tuple(plots_axes), tuple(plots_colorbar)


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

    def f(cond, ops):
        return partial(eval_binary_expr, cond["channel"].get_latest(), ops[1], float(ops[2]))()

    def check_conditions(conditions: list[Callable[[], bool]]):
        for cond in conditions:
            if f(cond[0], cond[1]):
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
        conditions.append([cond, ops])

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
