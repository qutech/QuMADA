# -*- coding: utf-8 -*-
"""
Created on Mon Nov 29 12:57:40 2021

@author: lab
"""

import logging
import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union
import operator

import matplotlib
import numpy as np
from tqdm.auto import tqdm

from qcodes import config
from qcodes.dataset.data_set_protocol import DataSetProtocol
from qcodes.dataset.descriptions.detect_shapes import detect_shape_of_measurement
from qcodes.dataset.descriptions.versioning.rundescribertypes import Shapes
from qcodes.dataset.experiment_container import Experiment
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.plotting import plot_dataset
from qcodes.instrument.parameter import _BaseParameter
from qcodes.utils.threading import process_params_meas
from qcodes.utils.dataset.doNd import (
        AbstractSweep, ParamMeasT, ActionsT, AxesTupleListWithDataSet, LinSweep, LOG,
        _register_parameters, _register_actions, _set_write_period, _catch_keyboard_interrupts, _handle_plotting
    )


@contextmanager
def _catch_keyboard_interrupts() -> Iterator[Callable[[], bool]]:
    interrupted = False

    def has_been_interrupted() -> bool:
        nonlocal interrupted
        return interrupted

    try:
        yield has_been_interrupted
    except KeyboardInterrupt:
        interrupted = True
    except Conditional_Break_Exception:
        interrupted = True


def dond(
    *params: Union[AbstractSweep, ParamMeasT],
    write_period: Optional[float] = None,
    measurement_name: str = "",
    exp: Optional[Experiment] = None,
    enter_actions: ActionsT = (),
    exit_actions: ActionsT = (),
    do_plot: Optional[bool] = None,
    show_progress: Optional[bool] = None,
    use_threads: Optional[bool] = None,
    additional_setpoints: Sequence[ParamMeasT] = tuple(),
    log_info: Optional[str] = None,
    break_conditions = None,
) -> AxesTupleListWithDataSet:
    """
    Perform n-dimentional scan from slowest (first) to the fastest (last), to
    measure m measurement parameters. The dimensions should be specified
    as sweep objects, and after them the parameters to measure should be passed.

    Args:
        *params: Instances of n sweep classes and m measurement parameters,
            e.g. if linear sweep is considered:

            .. code-block::

                LinSweep(param_set_1, start_1, stop_1, num_points_1, delay_1), ...,
                LinSweep(param_set_n, start_n, stop_n, num_points_n, delay_n),
                param_meas_1, param_meas_2, ..., param_meas_m

        write_period: The time after which the data is actually written to the
            database.
        measurement_name: Name of the measurement. This will be passed down to
            the dataset produced by the measurement. If not given, a default
            value of 'results' is used for the dataset.
        exp: The experiment to use for this measurement.
        enter_actions: A list of functions taking no arguments that will be
            called before the measurements start.
        exit_actions: A list of functions taking no arguments that will be
            called after the measurements ends.
        do_plot: should png and pdf versions of the images be saved and plots
            are shown after the run. If None the setting will be read from
            ``qcodesrc.json``
        show_progress: should a progress bar be displayed during the
            measurement. If None the setting will be read from ``qcodesrc.json`
        use_threads: If True, measurements from each instrument will be done on
            separate threads. If you are measuring from several instruments
            this may give a significant speedup.
        additional_setpoints: A list of setpoint parameters to be registered in
            the measurement but not scanned/swept-over.
        log_info: Message that is logged during the measurement. If None a default
            message is used.
        break_conditions: List or tuple of break conditions
    """
    if do_plot is None:
        do_plot = config.dataset.dond_plot
    if show_progress is None:
        show_progress = config.dataset.dond_show_progress

    meas = Measurement(name=measurement_name, exp=exp)
    if log_info is not None:
        meas._extra_log_info = log_info
    else:
        meas._extra_log_info = "Using 'qcodes.utils.dataset.doNd.dond'"

    def _parse_dond_arguments(
        *params: Union[AbstractSweep, ParamMeasT]
    ) -> Tuple[List[AbstractSweep], List[ParamMeasT]]:
        """
        Parse supplied arguments into sweep objects and measurement parameters.
        """
        sweep_instances: List[AbstractSweep] = []
        params_meas: List[ParamMeasT] = []
        for par in params:
            if isinstance(par, AbstractSweep):
                sweep_instances.append(par)
            else:
                params_meas.append(par)
        return sweep_instances, params_meas

    def _make_nested_setpoints(sweeps: List[AbstractSweep]) -> np.ndarray:
        """Create the cartesian product of all the setpoint values."""
        if len(sweeps) == 0:
            return np.array([[]])  # 0d sweep (do0d)
        setpoint_values = [sweep.get_setpoints() for sweep in sweeps]
        setpoint_grids = np.meshgrid(*setpoint_values, indexing="ij")
        flat_setpoint_grids = [np.ravel(grid, order="C") for grid in setpoint_grids]
        return np.vstack(flat_setpoint_grids).T

    sweep_instances, params_meas = _parse_dond_arguments(*params)
    nested_setpoints = _make_nested_setpoints(sweep_instances)

    all_setpoint_params = tuple(sweep.param for sweep in sweep_instances) + tuple(
        s for s in additional_setpoints
    )

    measured_parameters = tuple(
        par for par in params_meas if isinstance(par, _BaseParameter)
    )

    try:
        loop_shape = tuple(1 for _ in additional_setpoints) + tuple(
            sweep.num_points for sweep in sweep_instances
        )
        shapes: Shapes = detect_shape_of_measurement(measured_parameters, loop_shape)
    except TypeError:
        LOG.exception(
            f"Could not detect shape of {measured_parameters} "
            f"falling back to unknown shape."
        )
        shapes = None

    _register_parameters(meas, all_setpoint_params)
    _register_parameters(
        meas, params_meas, setpoints=all_setpoint_params, shapes=shapes
    )
    _set_write_period(meas, write_period)
    _register_actions(meas, enter_actions, exit_actions)

    original_delays: Dict[_BaseParameter, float] = {}
    params_set: List[_BaseParameter] = []
    for sweep in sweep_instances:
        original_delays[sweep.param] = sweep.param.post_delay
        sweep.param.post_delay = sweep.delay
        params_set.append(sweep.param)

    try:
        with _catch_keyboard_interrupts() as interrupted, meas.run() as datasaver:
            dataset = datasaver.dataset
            additional_setpoints_data = process_params_meas(additional_setpoints)
            for setpoints in tqdm(nested_setpoints, disable=not show_progress):
                param_set_list = []
                param_value_pairs = zip(params_set[::-1], setpoints[::-1])
                for setpoint_param, setpoint in param_value_pairs:
                    setpoint_param(setpoint)
                    param_set_list.append((setpoint_param, setpoint))
                    if _handle_breaks(_interpret_breaks(break_conditions)) == True:
                        raise Conditional_Break_Exception("Break condition was met.")
                datasaver.add_result(
                    *param_set_list,
                    *process_params_meas(params_meas, use_threads=use_threads),
                    *additional_setpoints_data,
                )
    finally:
        for parameter, original_delay in original_delays.items():
            parameter.post_delay = original_delay

    return _handle_plotting(dataset, do_plot, interrupted())


def _interpret_breaks(break_conditions: list,
                      **kwargs
        ) -> list[bool]:
    """
    Translates and checks break conditions.

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
    list[bool]
        List of booleans, True if break condition is fulfilled.

    """    

    conditions = list()
    def eval_binary_expr(op1, oper, op2):
        ops = {
        '>' : operator.gt,
        '<' : operator.lt,
        '==' : operator.eq,
        }
        op1, op2 = float(op1), float(op2)
        return ops[oper](op1, op2)
    
    for cond in break_conditions:
        ops = cond["break_condition"].split(" ")
        if ops[0] == "val": 
            param = cond["channel"].get()
        else: 
            print("Only parameters values can be used for breaks in this version")
            conditions.append(False)
        try:
            conditions.append(eval_binary_expr(param, ops[1], ops[2]))
        except:
            print(f"Could not evaluate break condition: {cond}")
    return conditions

class Conditional_Break_Exception(Exception):
    pass    

def _handle_breaks(
        conditions: Union[tuple[bool], list[bool]],
        **kwargs
        ) -> bool: 
    """
    Handles break conditions and returns True if one of the conditions is fulfilled.
    """
    for cond in conditions:
        if cond == True: 
            #raise Conditional_Break_Exception
            return True
    return False

    