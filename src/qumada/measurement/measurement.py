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
# - Till Huckeman
# - Daniel Grothe
# - Jonas Mertens
# - Sionludi Lab


"""
Measurement
"""
from __future__ import annotations

import inspect
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from contextlib import suppress
from datetime import datetime
from functools import wraps
from typing import Any, Union

import numpy as np
import qcodes as qc
from qcodes import Station
from qcodes.dataset import AbstractSweep, LinSweep
from qcodes.dataset.dond.do_nd_utils import ActionsT
from qcodes.parameters import Parameter, ParameterBase

from qumada.instrument.buffers.buffer import is_bufferable, is_triggerable
from qumada.metadata import Metadata
from qumada.utils.ramp_parameter import ramp_or_set_parameter
from qumada.utils.utils import flatten_array


def is_measurement_script(o):
    return inspect.isclass(o) and issubclass(o, MeasurementScript)


class QtoolsStation(Station):
    """Station object, inherits from qcodes Station."""


def create_hook(func, hook):
    """
    Decorator to hook a function onto an existing function.
    The hook function can use keyword-only arguments, which are omitted prior to execution of the main function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        hook(*args, **kwargs)
        # remove arguments used in hook from kwargs
        sig = inspect.signature(hook)
        varkw = next(
            filter(
                lambda p: p.kind is inspect.Parameter.VAR_KEYWORD,
                sig.parameters.values(),
            )
        ).name
        unused_kwargs = sig.bind(*args, **kwargs).arguments.get(varkw) or {}
        return func(*args, **unused_kwargs)

    return wrapper


class MeasurementScript(ABC):
    """
    Base class for measurement scripts.

    The abstract function "run" has to be implemented.
    """

    # TODO: Put list elsewhere! Remove names that were added as workarounds (e.g. aux_voltage) as soon as possible
    PARAMETER_NAMES: set[str] = {
        "voltage",
        "voltage_x_component",
        "voltage_y_component",
        "voltage_offset",
        "current",
        "current_x_component",
        "current_y_component",
        "current_compliance",
        "amplitude",
        "frequency",
        "output_enabled",
        "time_constant",
        "phase",
        "count",
        "aux_voltage_1",
        "aux_voltage_2",
        "temperature",
        "test_parameter",
    }

    def __init__(self):
        # Create function hooks for metadata
        # reverse order, so insert metadata is run second
        self.run = create_hook(self.run, self._insert_metadata_into_db)
        self.run = create_hook(self.run, self._add_data_to_metadata)
        self.run = create_hook(self.run, self._add_current_datetime_to_metadata)

        self.properties: dict[Any, Any] = {}
        self.gate_parameters: dict[Any, dict[Any, Parameter | None] | Parameter | None] = {}
        self._buffered_num_points: int | None = None

    def add_gate_parameter(self, parameter_name: str, gate_name: str = None, parameter: Parameter = None) -> None:
        """
        Adds a gate parameter to self.gate_parameters.

        Args:
            parameter_name (str): Name of the parameter. Has to be in MeasurementScript.PARAMETER_NAMES.
            gate_name (str): Name of the parameter's gate. Set this, if you want to define the parameter
                             under a specific gate. Defaults to None.
            parameter (Parameter): Custom parameter. Set this, if you want to set a custom parameter. Defaults to None.
        """
        if parameter_name not in MeasurementScript.PARAMETER_NAMES:
            raise NameError(f'parameter_name "{parameter_name}" not in MeasurementScript.PARAMETER_NAMES.')
        if not gate_name:
            self.gate_parameters[parameter_name] = parameter
        else:
            # Create gate dict if not existing
            gate = self.gate_parameters.setdefault(gate_name, {})
            # Raise Exception, if gate "gate_name" was populated with a parameter (or smth. else) before
            if isinstance(gate, dict):
                gate[parameter_name] = parameter
            else:
                raise TypeError("Gate {gate_name} is not a dictionary.")

    def _set_buffered_num_points(self) -> None:
        """
        Calculates number of datapoints when buffered measurements are performed and sets
        the buffered_num_points accordingly. Required to define QCoDeS datastructure.

        Raises
        ------
        None

        Returns
        -------
        None
        """

        if "burst_duration" in self.buffer_settings:
            self._burst_duration = self.buffer_settings["burst_duration"]

        if "duration" in self.buffer_settings:
            if "burst_duration" in self.buffer_settings:
                self._num_bursts = np.ceil(self.buffer_settings["duration"] / self._burst_duration)
            elif "num_bursts" in self.buffer_settings:
                self._num_bursts = int(self.buffer_settings["num_bursts"])
                self._burst_duration = self.buffer_settings["duration"] / self._num_bursts

        if "num_points" in self.buffer_settings:
            self.buffered_num_points = int(self.buffer_settings["num_points"])
            if "sampling_rate" in self.buffer_settings:
                self._burst_duration = float(self.buffered_num_points / self.buffer_settings["sampling_rate"])

        elif "sampling_rate" in self.buffer_settings:
            self._sampling_rate = float(self.buffer_settings["sampling_rate"])
            if self._burst_duration is not None:
                self.buffered_num_points = int(np.ceil(self._sampling_rate * self._burst_duration))
            elif all(k in self.buffer_settings for k in ("duration", "num_bursts")):
                self._burst_duration = float(self.buffer_settings["duration"] / self.buffer_settings["num_bursts"])

    def setup(
        self,
        parameters: dict,
        metadata: Metadata,
        *,
        add_script_to_metadata: bool = True,
        add_parameters_to_metadata: bool = True,
        buffer_settings: dict = None,
        measurement_name: str | None = None,
        **settings: dict,
    ) -> None:
        """
        Adds all gate_parameters that are defined in the parameters argument to
        the measurement. Allows to pass metadata to measurement and update the
        metadata with the script.

        Args:
            parameters (dict): Dictionary containing parameters and their settings
            metadata (Metadata): Object containing/handling metadata that should be
                                        available for the measurement.
            add_script_to_metadata (bool): If True (default), adds this object's content
                                           to the metadata.
            add_parameters_to_metadata (bool): If True (default), add the parameters to
                                               the metadata.
            settings (dict): Settings regarding the measurement script. Kwargs:
                ramp_rate: Defines how fast parameters are ramped during
                initialization and reset.
                setpoint_intervalle: Defines how smooth parameters are ramped
                during initialization and reset.
        """
        if buffer_settings is None:
            buffer_settings = {}
        # TODO: Add settings to metadata
        self.metadata = metadata
        self.buffered = False
        self._lists_created = False
        self.measurement_name = measurement_name
        cls = type(self)
        try:
            self.buffer_settings.update(buffer_settings)
        except Exception:
            self.buffer_settings = buffer_settings
        self._set_buffered_num_points()

        try:
            self.settings.update(settings)
        except Exception:
            self.settings = settings

        # Add script and parameters to metadata
        if add_script_to_metadata:
            try:
                metadata.add_script_to_metadata(inspect.getsource(cls), language="python", name=cls.__name__)
            except OSError as err:
                print(f"Source of MeasurementScript could not be acquired: {err}")
            except Exception as ex:
                print(f"Script could not be added to metadata: {ex}")

        if add_parameters_to_metadata:
            try:
                metadata.add_parameters_to_metadata(json.dumps(parameters), name=f"{cls.__name__}Settings")
            except Exception as ex:
                print(f"Parameters could not be added to metadata: {ex}")

        # Add gate parameters
        for gate, vals in parameters.items():
            self.properties[gate] = vals
            for parameter, properties in vals.items():
                self.add_gate_parameter(parameter, gate)

    def generate_lists(self) -> None:
        """
        Creates lists containing the corresponding parameters for further use.
        
        The .channels list always contain the QCoDes parameters that can for
        example directly be called to get the corresponding values.
        E.g. 
            [param() for param in self.gettable_channels] 
        will return a list of the current values of all gettable parameters.
        
        The .parameters lists contain dictionaries with the keywords "gate" for the
        corresponding terminal name and "parameter" for the parameter name.
        This is usefull to get the keys for specific parameters from
        the gate_parameters.
        
        gettable and static lists both include static gettable parameters,
        the static_gettable lists only the ones that are both, static and 
        gettable. This is e.g. useful for logging static parameters that cannot
        be buffered and thus cause errors in buffered measurements.
                
        """
        self.gettable_parameters: list[str] = []
        self.gettable_channels: list[str] = []
        self.static_gettable_parameters: list[str] = []
        self.static_gettable_channels: list[str] = []
        self.break_conditions: list[str] = []
        self.static_parameters: list[str] = []
        self.static_channels: list[str] = []
        self.dynamic_parameters: list[str] = []
        self.dynamic_channels: list[str] = []
        self.dynamic_sweeps: list[str] = []
        self.groups: dict[dict] = {}
        self.buffers: set = set()  # All buffers of gettable parameters
        self.trigger_ins: set = set()  # All trigger inputs that do not belong to buffers
        self.priorities: dict = {}

        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    self.static_parameters.append(
                        {"gate": gate, "parameter": parameter})
                    self.static_channels.append(channel)
                    if self.properties[gate][parameter]["type"].find("gettable") >=0:
                        self.static_gettable_parameters.append(
                            {"gate": gate, "parameter": parameter})
                        self.static_gettable_channels.append(channel)
                if self.properties[gate][parameter]["type"].find("gettable") >= 0:
                    self.gettable_parameters.append(
                        {"gate": gate, "parameter": parameter})
                    self.gettable_channels.append(channel)
                    with suppress(KeyError):
                        self.break_conditions.extend(
                            {"channel": channel, "break_condition": condition}
                            for condition in self.properties[gate][parameter]["break_conditions"]
                        )
                elif self.properties[gate][parameter]["type"].find("dynamic") >= 0:
                    self.dynamic_parameters.append({"gate": gate, "parameter": parameter})
                    self.dynamic_channels.append(channel)
                    if self.properties[gate][parameter].get("_is_triggered", False) and self.buffered:
                        if "num_points" in self.properties[gate][parameter].keys():
                            assert self.properties[gate][parameter]["num_points"] == self.buffered_num_points
                        elif "setpoints" in self.properties[gate][parameter].keys():
                            assert len(self.properties[gate][parameter]["setpoints"]) == self.buffered_num_points
                        else:
                            pass
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                channel,
                self.properties[gate][parameter]["start"],
                self.properties[gate][parameter]["stop"],
                self.buffered_num_points,
                delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                        except KeyError:
                            self.dynamic_sweeps.append(
                                LinSweep(
                channel,
                self.properties[gate][parameter]["setpoints"][0],
                self.properties[gate][parameter]["setpoints"][-1],
                self.buffered_num_points,
                delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                    else:
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                channel,
                self.properties[gate][parameter]["start"],
                self.properties[gate][parameter]["stop"],
                self.properties[gate][parameter]["num_points"],
                delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                        except KeyError:
                            self.dynamic_sweeps.append(
                                CustomSweep(
                channel,
                self.properties[gate][parameter]["setpoints"],
                delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                if "group" in self.properties[gate][parameter].keys():
                    group = self.properties[gate][parameter]["group"]
                    if group not in self.groups.keys():
                        self.groups[group]={"channels":[], 
                                         "parameters": [],
                                         "priority": None}
                    self.groups[group]["channels"].append(channel)
                    self.groups[group]["parameters"].append(
                        {"gate": gate, "parameter": parameter})
                    if self.groups[group]["priority"] is None:
                        if "priority" in self.properties[gate][parameter].keys():
                            if self.groups[group]["priority"] in self.priorities.keys():
                                raise Exception("Assigned the same priority to multiple groups")
                            elif self.groups[group]["priority"] is None: 
                                self.groups[group]["priority"] = int(self.properties[gate][parameter]["priority"])
                                self.priorities[int(self.groups[group]["priority"])] = self.groups[group]
                        else:
                            try:
                                prio = int(group)
                                if prio not in self.priorities.keys():
                                    self.groups[group]["priority"] = prio
                                    self.priorities[prio] = self.groups[group]
                            except:
                                pass
                        
                        
        if self.buffered:
            self.buffers = {
                channel.root_instrument._qumada_buffer for channel in self.gettable_channels if is_bufferable(channel)
            }
            self.trigger_ins = {
                param.root_instrument._qumada_mapping for param in self.dynamic_channels if is_triggerable(param)
            }
        self._lists_created = True
        self._relabel_instruments()

    def initialize(self) -> None:
        """
        Sets all static/sweepable parameters to their value/start value.
        If parameters are both, static and dynamic, they will be set to the "value" property
        and not to the "start" property.
        Parameters that are marked "dynamic" and "gettable" will not be added
        to the "self.gettable_parameters" as they are recorded anyway and will
        cause issues with dond functions.
        Provides gettable_parameters, static_parameters and dynamic parameters to
        measurement class and generates AbstractSweeps from the measurement
        properties. Sweeps form a list that can be found in "dynamic_sweeps"
        TODO: Is there a more elegant way?
        TODO: Put Sweep-Generation somewhere else?
        """

        ramp_rate = self.settings.get("ramp_rate", 0.3)
        ramp_time = self.settings.get("ramp_time", 5)
        setpoint_intervall = self.settings.get("setpoint_intervall", 0.1)
        if not self._lists_created:
            self.generate_lists()
        self.dynamic_sweeps = []
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    ramp_or_set_parameter(
                        channel,
                        self.properties[gate][parameter]["value"],
                        ramp_rate=ramp_rate,
                        ramp_time=ramp_time,
                        setpoint_intervall=setpoint_intervall,
                    )
                elif self.properties[gate][parameter]["type"].find("dynamic") >= 0:
                    if self.properties[gate][parameter].get("_is_triggered", False) and self.buffered:
                        if "num_points" in self.properties[gate][parameter].keys():
                            assert self.properties[gate][parameter]["num_points"] == self.buffered_num_points
                        elif "setpoints" in self.properties[gate][parameter].keys():
                            assert len(self.properties[gate][parameter]["setpoints"]) == self.buffered_num_points
                        else:
                            pass
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["start"],
                                    self.properties[gate][parameter]["stop"],
                                    self.buffered_num_points,
                                    delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                        except KeyError:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["setpoints"][0],
                                    self.properties[gate][parameter]["setpoints"][-1],
                                    self.buffered_num_points,
                                    delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                    else:
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["start"],
                                    self.properties[gate][parameter]["stop"],
                                    self.properties[gate][parameter]["num_points"],
                                    delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                        except KeyError:
                            self.dynamic_sweeps.append(
                                CustomSweep(
                                    channel,
                                    self.properties[gate][parameter]["setpoints"],
                                    delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                    # Handle different possibilities for starting points
                    try:
                        ramp_or_set_parameter(
                            channel,
                            self.properties[gate][parameter]["value"],
                            ramp_rate=ramp_rate,
                            ramp_time=ramp_time,
                            setpoint_intervall=setpoint_intervall,
                        )
                    except KeyError:
                        try:
                            ramp_or_set_parameter(
                                channel,
                                self.properties[gate][parameter]["start"],
                                ramp_rate=ramp_rate,
                                ramp_time=ramp_time,
                                setpoint_intervall=setpoint_intervall,
                            )
                        except KeyError:
                            ramp_or_set_parameter(
                                channel,
                                self.properties[gate][parameter]["setpoints"][0],
                                ramp_rate=ramp_rate,
                                ramp_time=ramp_time,
                                setpoint_intervall=setpoint_intervall,
                            )
                    # Generate sweeps from parameters

        if self.buffered:
            for gettable_param in self.gettable_channels:
                if is_bufferable(gettable_param):
                    gettable_param.root_instrument._qumada_buffer.subscribe([gettable_param])
                else:
                    raise Exception(f"{gettable_param} is not bufferable.")

    @abstractmethod
    def run(self) -> list:
        """
        Runs the already setup measurement. you can call self.initialize in here.
        Abstract method.
        """
        return []

    def reset(self) -> None:
        """
        Resets all static/dynamic parameters to their value/start value.
        """
        ramp_rate = self.settings.get("ramp_rate", 0.3)
        setpoint_intervall = self.settings.get("setpoint_intervall", 0.1)
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    ramp_or_set_parameter(
                        channel,
                        self.properties[gate][parameter]["value"],
                        ramp_rate=ramp_rate,
                        setpoint_intervall=setpoint_intervall,
                    )
                elif self.properties[gate][parameter]["type"].find("dynamic") >= 0:
                    try:
                        ramp_or_set_parameter(
                            channel,
                            self.properties[gate][parameter]["value"],
                            ramp_rate=ramp_rate,
                            setpoint_intervall=setpoint_intervall,
                        )
                    except KeyError:
                        try:
                            ramp_or_set_parameter(
                                channel,
                                self.properties[gate][parameter]["start"],
                                ramp_rate=ramp_rate,
                                setpoint_intervall=setpoint_intervall,
                            )
                        except KeyError:
                            ramp_or_set_parameter(
                                channel,
                                self.properties[gate][parameter]["setpoints"][0],
                                ramp_rate=ramp_rate,
                                setpoint_intervall=setpoint_intervall,
                            )

    def ready_buffers(self, **kwargs) -> None:
        """
        Setup all buffers registered in the measurement and start them

        Parameters
        ----------
        **kwargs : None so far...

        Returns
        -------
        None
        """
        for buffer in self.buffers:
            buffer.setup_buffer(settings=self.buffer_settings)
            buffer.start()
        for trigger in self.trigger_ins:
            trigger.setup_trigger_in(trigger_settings=self.buffer_settings)

    def readout_buffers(self, **kwargs) -> dict:
        """
        Readout all buffer and return the results as list of tuples
        (parameters, values) as required by qcodes measurement context manager.

        Parameters
        ----------
        **kwargs :
            timestamps: Set True if timestamp data is to be included in the
                    results. Not implemented yet.
        Returns
        -------
        dict
            Results, list with one tuple for each subscribed parameter. Tuple
            contains (parameter, measurement_data).

        #TODO: Handle multiple bursts etc.
        """
        data = {}
        results = []
        for buffer in self.buffers:
            buffer.stop()
            data[buffer] = buffer.read()
            results.extend((param, flatten_array(data[buffer][param.name])) for param in buffer._subscribed_parameters)
        if kwargs.get("timestamps", False):
            results.append(flatten_array(data[list(data.keys())[0]]["timestamps"]))
        return results

    def _relabel_instruments(self) -> None:
        """
        Changes the labels of all instrument channels to the
        corresponding name defined in the measurement script.
        Has to be done after mapping!
        """
        for gate, parameters in self.gate_parameters.items():
            for key, parameter in parameters.items():
                parameter.label = f"{gate} {key}"

    def _add_current_datetime_to_metadata(self, *args, add_datetime_to_metadata: bool = True, **kwargs):
        if add_datetime_to_metadata:
            try:
                metadata = self.metadata
                metadata.add_datetime_to_metadata(datetime.now())
            except Exception as ex:
                print(f"Datetime could not be added to metadata: {ex}")

    def _add_data_to_metadata(self, *args, add_data_to_metadata: bool = True, **kwargs):
        # Add script and parameters to metadata
        if add_data_to_metadata:
            try:
                metadata = self.metadata
                cls = type(self)
                if not metadata.measurement.data:
                    metadata.measurement.data = []
                db_location = qc.config.core.db_location
                metadata.add_data_to_metadata(db_location, "sqlite3", f"{cls.__name__}Data")
            except Exception as ex:
                print(f"Data could not be added to metadata: {ex}")

    def _insert_metadata_into_db(self, *args, insert_metadata_into_db: bool = True, **kwargs):
        if insert_metadata_into_db:
            try:
                metadata = self.metadata
                metadata.save()
            except Exception as ex:
                print(f"Metadata could not inserted into database: {ex}")


class VirtualGate:
    """Virtual Gate"""

    def __init__(self):
        self._functions = []

    @property
    def functions(self):
        """List of equipment Functions, the virtual gate shall have."""
        return self._functions

    @functions.setter
    def functions(self, functions: MutableSequence):
        self._functions = functions


class CustomSweep(AbstractSweep):
    """
    Custom sweep from array of setpoints.

    Args:
        param: Qcodes parameter to sweep.
        setpoints: Array of setpoints.
        delay: Time in seconds between two consequtive sweep points
    """

    def __init__(
        self,
        param: ParameterBase,
        setpoints: np.ndarray,
        delay: float = 0,
        post_actions: ActionsT = (),
    ):
        self._param = param
        self._setpoints = setpoints
        self._num_points = len(setpoints)
        self._delay = delay
        self._post_actions = post_actions

    def get_setpoints(self) -> np.ndarray:
        """
        1D array of setpoints
        """
        return self._setpoints

    @property
    def param(self) -> ParameterBase:
        return self._param

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def num_points(self) -> int:
        return self._num_points

    @property
    def post_actions(self) -> ActionsT:
        return self._post_actions
