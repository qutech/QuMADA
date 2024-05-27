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

from __future__ import annotations

import copy
import inspect
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from contextlib import suppress
from datetime import datetime
from functools import wraps
from typing import Any, Callable

import numpy as np
import qcodes as qc
from qcodes import Station
from qcodes.dataset import AbstractSweep, LinSweep
from qcodes.dataset.dond.do_nd_utils import ActionsT
from qcodes.parameters import Parameter, ParameterBase

from qumada.instrument.buffers import is_bufferable, is_triggerable
from qumada.metadata import Metadata
from qumada.utils.ramp_parameter import ramp_or_set_parameter
from qumada.utils.utils import flatten_array

logger = logging.getLogger(__name__)


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
        "demod0_aux_in_1",
        "demod0_aux_in_2",
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
                raise Exception("Gate {gate_name} is not a dictionary.")

    def _set_buffered_num_points(self) -> None:
        """
        Calculates number of datapoints when buffered measurements are performed and sets
        the buffered_num_points accordingly. Required to define QCoDeS datastructure.
        """

        if "burst_duration" in self.buffer_settings:
            self._burst_duration = float(self.buffer_settings["burst_duration"])

        if "duration" in self.buffer_settings:
            if "burst_duration" in self.buffer_settings:
                self._num_bursts = np.ceil(float(self.buffer_settings["duration"]) / self._burst_duration)
            elif "num_bursts" in self.buffer_settings:
                self._num_bursts = int(self.buffer_settings["num_bursts"])
                self._burst_duration = float(self.buffer_settings["duration"]) / self._num_bursts

        if "num_points" in self.buffer_settings:
            self.buffered_num_points = int(self.buffer_settings["num_points"])
            if "sampling_rate" in self.buffer_settings:
                self._burst_duration = float(self.buffered_num_points / self.buffer_settings["sampling_rate"])

        elif "sampling_rate" in self.buffer_settings:
            self._sampling_rate = float(self.buffer_settings["sampling_rate"])
            if self._burst_duration is not None:
                self.buffered_num_points = np.ceil(self._sampling_rate * self._burst_duration)
            elif all(k in self.buffer_settings for k in ("duration", "num_bursts")):
                self._burst_duration = float(self.buffer_settings["duration"] / self.buffer_settings["num_bursts"])

    def setup(
        self,
        parameters: dict,
        metadata: Metadata,
        *,
        add_script_to_metadata: bool = True,
        add_parameters_to_metadata: bool = True,
        buffer_settings: dict = {},
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

        E.g.: ``[param() for param in self.gettable_channels]`` will return a list
        of the current values of all gettable parameters.

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
        self.compensating_parameters: list[str] = []
        self.compensating_parameters_values: list[float] = []
        self.compensating_channels: list[str] = []
        self.compensating_leverarms: list[list[float]] = []
        self.compensated_parameters: list[list[str]] = []
        self.compensating_limits: list[list] = []
        self.abstract_parameters: list[str] = []
        self.abstract_setpoints: list[list] = []
        self.groups: dict[dict] = {}
        self.buffers: set = set()  # All buffers of gettable parameters
        self.trigger_ins: set = set()  # All trigger inputs that do not belong to buffers
        self.priorities: dict = {}
        self.loop: int = 0  # For usage with looped measurements

        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if gate == "abstract":
                    self.abstract_parameters.append()
                    self.abstract_setpoints.append(self.properties[gate][parameter]["setpoints"])

                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    self.static_parameters.append({"gate": gate, "parameter": parameter})
                    self.static_channels.append(channel)
                    if self.properties[gate][parameter]["type"].find("gettable") >= 0:
                        self.static_gettable_parameters.append({"gate": gate, "parameter": parameter})
                        self.static_gettable_channels.append(channel)
                if self.properties[gate][parameter]["type"].find("gettable") >= 0:
                    self.gettable_parameters.append({"gate": gate, "parameter": parameter})
                    self.gettable_channels.append(channel)
                    with suppress(KeyError):
                        for condition in self.properties[gate][parameter]["break_conditions"]:
                            self.break_conditions.append({"channel": channel, "break_condition": condition})
                if self.properties[gate][parameter]["type"].find("comp") >= 0:
                    self.compensating_parameters.append({"gate": gate, "parameter": parameter})
                    self.compensating_channels.append(channel)
                    try:
                        self.compensating_parameters_values.append(self.properties[gate][parameter]["value"])
                    except KeyError as e:
                        print(
                            f"No value assigned for compensating parameter \
                              {self.compensating_parameters[-1]}"
                        )
                        raise e
                    try:
                        leverarms = self.properties[gate][parameter]["leverarms"]
                        assert isinstance(leverarms, list)
                        self.compensating_leverarms.append(self.properties[gate][parameter]["leverarms"])
                    except KeyError as e:
                        print(f"No leverarm specified for parameters {self.compensating_parameters[-1]}!")
                        raise e
                    try:
                        comp_list = []
                        for entry in self.properties[gate][parameter]["compensated_gates"]:
                            assert isinstance(entry, dict)
                            comp_list.append({"gate": entry["terminal"], "parameter": entry["parameter"]})
                        self.compensated_parameters.append(comp_list)
                    except KeyError as e:
                        print(
                            f"The terminal to be compensated for with {self.compensating_parameters[-1]} \
                            is not properly specified! Make sure to define a dictionary with \
                            terminal and parameter as keys."
                        )
                        raise e
                    try:
                        limits = self.properties[gate][parameter]["limits"]
                        self.compensating_limits.append(limits)
                    except KeyError as e:
                        print(
                            f"No limits assigned to compensating parameter \
                              {self.compensating_parameters[-1]}!"
                        )
                        raise e

                elif self.properties[gate][parameter]["type"].find("dynamic") >= 0:
                    self.dynamic_parameters.append({"gate": gate, "parameter": parameter})
                    self.dynamic_channels.append(channel)
                    if self.properties[gate][parameter].get("_is_triggered", False) and self.buffered:
                        if "num_points" in self.properties[gate][parameter].keys():
                            try:
                                assert self.properties[gate][parameter]["num_points"] == self.buffered_num_points
                            except AssertionError:
                                logger.warning(
                                    f"Number of datapoints from buffer_settings\
                                    and gate_parameters do not match. Using \
                                    the value from the buffer settings: \
                                    {self.buffered_num_points}"
                                )
                        elif "setpoints" in self.properties[gate][parameter].keys():
                            try:
                                assert len(self.properties[gate][parameter]["setpoints"]) == self.buffered_num_points
                            except AssertionError:
                                logger.warning(
                                    f"Number of datapoints from buffer_settings\
                                    and gate_parameters do not match. Using \
                                    the value from the buffer settings: \
                                    {self.buffered_num_points}"
                                )

                        else:
                            logger.info(
                                "No num_points or setpoints given for\
                                         buffered measurement. The value from \
                                         buffer_settings is used"
                            )
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["start"],
                                    self.properties[gate][parameter]["stop"],
                                    int(self.buffered_num_points),
                                    delay=self.properties[gate][parameter].setdefault("delay", 0),
                                )
                            )
                        except KeyError:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["setpoints"][0],
                                    self.properties[gate][parameter]["setpoints"][-1],
                                    int(self.buffered_num_points),
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
                                    int(self.properties[gate][parameter]["num_points"]),
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

                    # Only executed for dynamic parameters!
                    if "group" in self.properties[gate][parameter].keys():
                        group = self.properties[gate][parameter]["group"]
                        if group not in self.groups.keys():
                            self.groups[group] = {"channels": [], "parameters": [], "priority": None}
                        self.groups[group]["channels"].append(channel)
                        self.groups[group]["parameters"].append({"gate": gate, "parameter": parameter})
                        if self.groups[group]["priority"] is None:
                            if "priority" in self.properties[gate][parameter].keys():
                                if self.groups[group]["priority"] in self.priorities.keys():
                                    raise Exception("Assigned the same priority to multiple groups")
                                elif self.groups[group]["priority"] is None:
                                    self.groups[group]["priority"] = int(self.properties[gate][parameter]["priority"])
                                    self.priorities[int(self.groups[group]["priority"])] = self.groups[group]
                                    self.dynamic_parameters[-1]["priority"] = int(self.groups[group]["priority"])
                            else:
                                try:
                                    prio = int(group)
                                    if prio not in self.priorities.keys():
                                        self.groups[group]["priority"] = prio
                                        self.priorities[prio] = self.groups[group]
                                        self.dynamic_parameters[-1]["priority"] = prio
                                except Exception:
                                    pass

        if self.buffered:
            self.buffers = {
                channel.root_instrument._qumada_buffer for channel in self.gettable_channels if is_bufferable(channel)
            }
            self.trigger_ins = {
                param.root_instrument._qumada_mapping for param in self.dynamic_channels if is_triggerable(param)
            }
        self.sort_by_priority()
        self._lists_created = True
        self._relabel_instruments()

    def sort_by_priority(self):
        combined_lists = list(zip(self.dynamic_parameters, self.dynamic_channels, self.dynamic_sweeps))
        combined_sorted = sorted(combined_lists, key=lambda x: (x[0].get("priority", float("inf"))))
        self.dynamic_parameters, self.dynamic_channels, self.dynamic_sweeps = map(list, zip(*combined_sorted))

    def initialize(self, dyn_ramp_to_val=False, inactive_dyn_channels: list | None = None) -> None:
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
        Relevant kwargs:
            dyn_ramp_to_val: Bool [False]: If true, dynamic parameters are
                    ramped to their value, before their sweep, else they are ramped
                    to their first setpoint.
            inactive_dyn_channels: List|None [None]: List of dynamic channels that are to be
                    treated as static for this initialization. They are always
                    ramped to their value instead of their sweeps starting point.
        """
        # TODO: Is there a more elegant way?
        # TODO: Put Sweep-Generation somewhere else?
        if inactive_dyn_channels is None:
            inactive_dyn_channels = []

        ramp_rate = self.settings.get("ramp_rate", 0.3)
        ramp_time = self.settings.get("ramp_time", 5)
        setpoint_intervall = self.settings.get("setpoint_intervall", 0.1)
        if not self._lists_created:
            self.generate_lists()
        # for item in self.compensated_parameters:
        #     if item not in self.dynamic_parameters:
        #         raise Exception(f"{item} is not in dynamic parameters and cannot be compensated!")
        self.dynamic_sweeps = []
        self.compensating_sweeps = []
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
                            try:
                                assert self.properties[gate][parameter]["num_points"] == self.buffered_num_points
                            except AssertionError:
                                logger.warning(
                                    f"Number of datapoints from buffer_settings\
                                    and gate_parameters do not match. Using \
                                    the value from the buffer settings: \
                                    {self.buffered_num_points}"
                                )
                                self.properties[gate][parameter]["num_points"] = self.buffered_num_points

                        elif "setpoints" in self.properties[gate][parameter].keys():
                            try:
                                assert len(self.properties[gate][parameter]["setpoints"]) == self.buffered_num_points
                            except AssertionError:
                                logger.warning(
                                    f"Number of datapoints from buffer_settings\
                                    and gate_parameters do not match. Using \
                                    the value from the buffer settings: \
                                    {self.buffered_num_points}"
                                )

                        else:
                            logger.info(
                                "No num_points or setpoints given for\
                                         buffered measurement. The value from \
                                         buffer_settings is used"
                            )
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["start"],
                                    self.properties[gate][parameter]["stop"],
                                    int(self.buffered_num_points),
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
                    else:
                        try:
                            self.dynamic_sweeps.append(
                                LinSweep(
                                    channel,
                                    self.properties[gate][parameter]["start"],
                                    self.properties[gate][parameter]["stop"],
                                    int(self.properties[gate][parameter]["num_points"]),
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
                    if dyn_ramp_to_val or channel in inactive_dyn_channels:
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
                    else:
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
        self.active_compensated_channels = []
        self.active_compensating_channels = []
        self.active_compensating_parameters = []
        inactive_dyn_params = []
        for ch in inactive_dyn_channels:
            inactive_dyn_params.append(self.dynamic_parameters[self.dynamic_channels.index(ch)])
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                # This iterates over all compensating parameters
                if self.properties[gate][parameter]["type"].find("comp") >= 0:
                    try:
                        i = self.compensating_parameters.index({"gate": gate, "parameter": parameter})
                        leverarms = self.compensating_leverarms[i]
                        comped_params = copy.deepcopy(
                            self.compensated_parameters[i]
                        )  # list of parameters compensated by the current parameter
                        comped_sweeps = []  # Sweeps that are compensated by current param
                        comped_leverarms = []  # Leverarms of the current param
                        comping_sweeps = []  # List to store only the sweeps for the current param
                        k = 0
                        for comped_param in comped_params.copy():
                            # Check if the parameter is actually ramped in this part of the measurement
                            if comped_param in inactive_dyn_params:
                                comped_params.remove(comped_param)
                            else:
                                # Get only the relevant list entries for the current parameter
                                try:
                                    comped_index = self.dynamic_parameters.index(comped_param)
                                except ValueError as e:
                                    logger.exception(
                                        "Watch out, there is an Exception incoming!"
                                        + "Did you try to compensate for a not dynamic parameter?"
                                    )
                                    raise e
                                comped_sweeps.append(self.dynamic_sweeps[comped_index])
                                comped_leverarms.append(leverarms[k])
                                self.active_compensated_channels.append(self.dynamic_channels[comped_index])
                            k += 1
                        compensating_param = self.compensating_parameters[i]
                        self.active_compensating_parameters.append(compensating_param)
                        if len(comped_params) > 0:
                            self.active_compensating_channels.append(channel)
                            for j in range(len(comped_params)):
                                # Here we create lists/sweeps only containing the difference required for compensation.
                                # Still has to be substracted from the set value in the measurement script as this can
                                # depend on the measurement script used (e.g. 1D vs 2D sweeps)
                                comping_setpoints = (
                                    -1
                                    * float(comped_leverarms[j])
                                    * (np.array(comped_sweeps[j].get_setpoints()) - comped_sweeps[j].get_setpoints()[0])
                                )
                                # This creates an inner list of required setpoint differences only
                                # for the param that is currently iterated over!
                                # The final self.compensating_sweeps list will contain list for each
                                # compensating parameters with one sweep per
                                # parameter that is compensated by this compensating parameters.
                                comping_sweeps.append(
                                    CustomSweep(
                                        channel,
                                        comping_setpoints,
                                        delay=self.properties[gate][parameter].setdefault("delay", 0),
                                    )
                                )
                            self.compensating_sweeps.append(comping_sweeps)
                            if (
                                any(
                                    [
                                        self.properties[param["gate"]][param["parameter"]].get("_is_triggered", False)
                                        for param in comped_params
                                    ]
                                )
                                and self.buffered
                            ):
                                self.properties[compensating_param["gate"]][compensating_param["parameter"]][
                                    "_is_triggered"
                                ] = True
                            # TODO: This part has to be moved into the measurement script,
                            # as the final setpoints for the comping params are now set at
                            # the measurement script. A helper method would be nice to have.
                            # if min(self.compensating_sweeps[-1].get_setpoints()) < min(*self.compensating_limits[i]) \
                            #  or max(self.compensating_sweeps[-1].get_setpoints()) > max(*self.compensating_limits[i]):
                            #     raise Exception(f"Value for compensating gate {compensating_param} exceeds limits!")
                        ramp_or_set_parameter(
                            channel,
                            self.properties[gate][parameter]["value"],
                            ramp_rate=ramp_rate,
                            ramp_time=ramp_time,
                            setpoint_intervall=setpoint_intervall,
                        )
                    except ValueError as e:
                        raise e

        if self.buffered:
            for gettable_param in list(set(self.gettable_channels) - set(self.static_gettable_channels)):
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
        TODO: Remove! Since initialize() does only create lists one, there is no advantage of using reset().
        """
        logger.warning(
            "The reset() method is deprecated and will be removed in a future release! \
                        It is recommended to replace all calls of reset() with initialize()"
        )
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

    def clean_up(self, additional_actions: list[Callable] | None = None, **kwargs) -> None:
        """
        Things to do after the measurement is complete. Cleans up subscribed paramteres for
        buffered measurements by default.
        TODO: Hook into measurement.run()

        Args:
            additional_actions (list[Callable], optional):
                List of functions to be called after the measurement is
                complete. Defaults to None.
        """
        for buffer in self.buffers:
            buffer.unsubscribe(buffer._subscribed_parameters)
        self.measurement_name = None
        if additional_actions:
            for action in additional_actions:
                action()

    def ready_buffers(self, **kwargs) -> None:
        """
        Setup all buffers registered in the measurement and start them.
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

        Args:
            **kwargs (dict):
                timestamps (bool): Set True if timestamp data is to be included
                    in the results. Not implemented yet.

        Returns:
            dict: Results, list with one tuple for each subscribed parameter.
            Tuple contains (parameter, measurement_data).

        """
        # TODO: Handle multiple bursts etc.
        data = {}
        results = []
        for buffer in self.buffers:
            buffer.stop()
            data[buffer] = buffer.read()
            for param in buffer._subscribed_parameters:
                results.append((param, flatten_array(data[buffer][param.name])))
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
