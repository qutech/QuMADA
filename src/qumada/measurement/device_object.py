from __future__ import annotations

import inspect
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from contextlib import suppress
from copy import deepcopy
from datetime import datetime
from functools import wraps
from typing import Any, Callable

import numpy as np
import qcodes as qc
from qcodes import Station
from qcodes.dataset import AbstractSweep, LinSweep
from qcodes.dataset.dond.do_nd_utils import ActionsT
from qcodes.parameters import Parameter, ParameterBase

from qumada.instrument.buffers.buffer import map_triggers
from qumada.instrument.mapping import map_terminals_gui
from qumada.measurement.scripts import Generic_1D_Sweep, Timetrace, Timetrace_buffered
from qumada.metadata import Metadata
from qumada.utils.ramp_parameter import ramp_or_set_parameter
from qumada.utils.utils import flatten_array

logger = logging.getLogger(__name__)


class Terminal_Exists_Exception(Exception):
    pass


class Parameter_Exists_Exception(Exception):
    pass


class QumadaDevice:
    def __init__(
        self,
        make_terminals_global=True,
        namespace=None,
        station: Station | None = None,
    ):
        self.namespace = namespace or globals()
        self.terminals = {}
        self.instrument_parameters = {}
        self.make_terminals_global = make_terminals_global
        self.station = station
        self.buffer_script_setup = {}

    def add_terminal(self, terminal_name: str, type: str | None = None, terminal_data: dict | None = {}):
        if terminal_name not in self.terminals.keys():
            self.__dict__[terminal_name.replace(" ", "_")] = self.terminals[terminal_name] = Terminal(
                terminal_name, self, type
            )
        else:
            raise Terminal_Exists_Exception(f"Terminal {terminal_name} already exists. Please remove it first!")
        if self.make_terminals_global:
            if terminal_name not in self.namespace.keys():
                # Adding to the global namespace
                self.namespace[terminal_name] = self.terminals[terminal_name.replace(" ", "_")]
                logger.warning(f"Added {terminal_name} to global namespace!")
            else:
                raise Terminal_Exists_Exception(
                    f"Terminal {terminal_name} already exists in global namespace. \
                        Please remove it first!"
                )

    def remove_terminal(self, terminal_name: str):
        if terminal_name in self.terminals.keys():
            del self.__dict__[terminal_name]
            del self.terminals[terminal_name]
            if terminal_name in self.namespace:
                del self.namespace[terminal_name]
        else:
            logger.warning(f"{terminal_name} does not exist and could not be deleted")

    def update_terminal_parameters(self):
        for terminal, mapping in self.instrument_parameters.items():
            for param in mapping.keys():
                self.terminals[terminal].update_terminal_parameter(param)

    def save_defaults(self):
        """
        Saves current values as default for all Terminals and their parameters
        """
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.save_default()

    def set_stored_values(self):
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.set_stored_value()

    def set_defaults(self):
        """
        Sets all Terminals and their parameters to their default values
        """
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.set_default()

    @staticmethod
    def create_from_dict(data: dict, station: Station | None = None, make_terminals_global=False, namespace=None):
        """
        Creates a QumadaDevice object from valid parameter dictionaries as used in Qumada measurement scripts.
        Be aware that the validity is not checked at the moment, so there might be unexpected exceptions!
        Parameter values are not set upon initialization for safety reason! They are stored in the _stored_values attribute.
        By default terminals are added to the namespace provided by the namespace argument.
        If you set namespace=globals() you can make the terminals available in global namespace.
        TODO: Remove make_terminals_global parameter and check if namespace is not None
        """
        device = QumadaDevice(station=station, make_terminals_global=make_terminals_global, namespace=namespace)
        for terminal_name, terminal_data in data.items():
            device.add_terminal(terminal_name, terminal_data=terminal_data)
            for parameter_name, properties in terminal_data.items():
                device.terminals[terminal_name].add_terminal_parameter(parameter_name, properties=properties)
        return device

    def load_from_dict(self, data: dict):
        """
        Adds terminals and corresponding parameters to an existing QumadaDevice.
        Values are not set automatically for safety reasons, they are stored in the _stored_value attribute.
        TODO: Check behaviour for existing terminals/parameters
        """
        device = self
        for terminal_name, terminal_data in data.items():
            try:
                device.add_terminal(terminal_name, terminal_data=terminal_data)
            except Terminal_Exists_Exception:
                pass
            for parameter_name, properties in terminal_data.items():
                try:
                    device.terminals[terminal_name].add_terminal_parameter(parameter_name, properties=properties)
                except Parameter_Exists_Exception:
                    device.terminals[terminal_name].terminal_parameters[parameter_name].properties = properties
                    device.terminals[terminal_name].terminal_parameters[parameter_name]._apply_properties()

        return device

    def save_to_dict(self, priorize_stored_value=False):
        """
        Returns a dict compatible with the qumada measurements scripts.
        Contains type, setpoints, delay, start, stop, num_points and value of the
        terminal parameters.
        For the value, by default the current value of the parameter is used (the parameter is called
        therefore). If the parameter is not callable (e.g. because no mapping was done so far), the
        _stored_value attribute is used.
        If priorize_stored_values is set to True, the _stored_value attribute will be used if available
        and the return value of the parameters callable only if _stored_value is not available (or None).
        None values will be always ignored, the value will not be set in this case.
        """
        return_dict = {}

        for terminal_name, terminal in self.terminals.items():
            return_dict[terminal_name] = {}
            for param_name, param in terminal.terminal_parameters.items():
                return_dict[terminal_name][param_name] = {}
                for attr_name in ["type", "setpoints", "delay", "start", "stop", "num_points", "break_conditions"]:
                    if hasattr(param, attr_name):
                        return_dict[terminal.name][param.name][attr_name] = getattr(param, attr_name)
                if priorize_stored_value:
                    if hasattr(param, "_stored_value") and getattr(param, "_stored_value") is not None:
                        return_dict[terminal.name][param.name]["value"] = getattr(param, "_stored_value")
                    elif callable(param):
                        try:
                            if param() is not None:
                                return_dict[terminal.name][param.name]["value"] = param()
                        except Exception as e:
                            logger.exception(e)
                    else:
                        logger.warning(f"Couldn't find value for {terminal_name} {param_name}")
                else:
                    try:
                        if param() is not None:
                            return_dict[terminal.name][param.name]["value"] = param()
                        else:
                            raise Exception(f"Calling {param} return None. Trying to use stored value")
                    except Exception as e:
                        logger.exception(e)
                        if hasattr(param, "_stored_value") and getattr(param, "_stored_value") is not None:
                            return_dict[terminal.name][param.name]["value"] = getattr(param, "_stored_value")
                        else:
                            logger.warning(f"Couldn't find value for {terminal_name} {param_name}")
        return return_dict

    def timetrace(
        self,
        duration: float,
        timestep: float = 1,
        name=None,
        metadata=None,
        station=None,
        buffered=False,
        buffer_settings: dict = {},
        priorize_stored_value=False,
    ):
        """ """
        if station is None:
            station = self.station
        if type(station) != Station:
            raise TypeError("No valid station assigned!")
        temp_buffer_settings = deepcopy(buffer_settings)
        if buffered == True:
            logger.warning("Temporarily modifying buffer settings to match function arguments.")
            temp_buffer_settings["sampling_rate"] = 1 / timestep
            temp_buffer_settings["duration"] = duration
            temp_buffer_settings["burst_duration"] = duration
            try:
                del temp_buffer_settings["num_points"]
                del temp_buffer_settings["num_bursts"]
            except KeyError as e:
                logger.warning(e)

            script = Timetrace_buffered()
        else:
            script = Timetrace()
        script.setup(
            self.save_to_dict(priorize_stored_value=priorize_stored_value),
            metadata=metadata,
            name=name,
            duration=duration,
            timestep=timestep,
            buffer_settings=temp_buffer_settings,
            **self.buffer_script_setup,
        )
        mapping = self.instrument_parameters
        map_terminals_gui(station.components, script.gate_parameters, mapping)
        map_triggers(station.components, script.properties, script.gate_parameters)
        data = script.run()
        return data


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


class Terminal(ABC):
    """
    Base class for Terminals scripts.

    The abstract functions "reset" has to be implemented.
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

    def __init__(self, name, parent: QumadaDevice | None = None, type: str | None = None):
        # Create function hooks for metadata
        # reverse order, so insert metadata is run second
        # self.run = create_hook(self.run, self._insert_metadata_into_db)
        # self.run = create_hook(self.run, self._add_data_to_metadata)
        # self.run = create_hook(self.run, self._add_current_datetime_to_metadata)

        self.properties: dict[Any, Any] = {}
        self.name = name
        self._parent = parent
        self.type = type
        self.terminal_parameters: dict[Any, dict[Any, Parameter | None] | Parameter | None] = {}

    def add_terminal_parameter(
        self, parameter_name: str, parameter: Parameter = None, properties: dict | None = None
    ) -> None:
        """
        Adds a gate parameter to self.terminal_parameters.

        Args:
            parameter_name (str): Name of the parameter. Has to be in MeasurementScript.PARAMETER_NAMES.
            terminal_name (str): Name of the parameter's gate. Set this, if you want to define the parameter
                             under a specific gate. Defaults to None.
            parameter (Parameter): Custom parameter. Set this, if you want to set a custom parameter. Defaults to None.
        """
        if parameter_name not in Terminal.PARAMETER_NAMES:
            raise NameError(f'parameter_name "{parameter_name}" not in MeasurementScript.PARAMETER_NAMES.')
        if parameter_name not in self.terminal_parameters.keys():
            self.__dict__[parameter_name] = self.terminal_parameters[parameter_name] = Terminal_Parameter(
                parameter_name, self, properties=properties
            )
            if self.name not in self._parent.instrument_parameters.keys():
                self._parent.instrument_parameters[self.name] = {}
            self._parent.instrument_parameters[self.name][parameter_name] = parameter
        else:
            raise Parameter_Exists_Exception(f"Parameter{parameter_name} already exists")

    def remove_terminal_parameter(self, parameter_name: str) -> None:
        """
        Adds a gate parameter to self.terminal_parameters.

        Args:
            parameter_name (str): Name of the parameter. Has to be in MeasurementScript.PARAMETER_NAMES.
            terminal_name (str): Name of the parameter's gate. Set this, if you want to define the parameter
                             under a specific gate. Defaults to None.
            parameter (Parameter): Custom parameter. Set this, if you want to set a custom parameter. Defaults to None.
        """
        if parameter_name in self.terminal_parameters.keys():
            del self.__dict__[parameter_name]
            del self.terminal_parameters[parameter_name]
        else:
            raise Exception(f"Parameter{parameter_name} does not exist!")

    def update_terminal_parameter(self, parameter_name: str, parameter: Parameter | None = None) -> None:
        self.terminal_parameters[parameter_name].instrument_parameter = self._parent.instrument_parameters[self.name][
            parameter_name
        ]

    def __call__(self, value=None):
        if "voltage" in self.terminal_parameters.keys():
            return self.voltage(value)
        else:
            raise TypeError


class Terminal_Parameter(ABC):
    def __init__(self, name: str, Terminal: Terminal, properties: dict = {}) -> None:
        self._parent = Terminal
        self._parent_device = Terminal._parent
        if properties is None:
            properties = {}
        self.properties: dict[Any, Any] = properties
        self.type = self.properties.get("type", None)
        self._stored_value = self.properties.get("value", None)  # For storing values for measurements
        self.setpoints = self.properties.get("setpoints", None)
        self.delay = self.properties.get("delay", 0)
        self.break_conditions = self.properties.get("break_conditions", [])
        self._value = None
        self.name = name
        self.limits = None
        self.rampable = False
        self.ramp_rate = self.properties.get("ramp_rate", 0.1)
        self.group = self.properties.get("group", None)
        self.default_value = None
        self.scaling = 1
        self._instrument_parameter = None
        self.locked = False

    def reset(self):
        pass

    def _apply_properties(self):
        """
        Make sure changes to the properties are passed on to the object attributes
        """
        self.type = self.properties.get("type", self.type)
        self._stored_value = self.properties.get("value", self._stored_value)  # For storing values for measurements
        self.setpoints = self.properties.get("setpoints", self.setpoints)
        self.delay = self.properties.get("delay", self.delay)
        self.ramp_rate = self.properties.get("ramp_rate", self.ramp_rate)
        self.group = self.properties.get("group", self.group)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.locked:
            raise Exception(f"Parameter {self.name} of Terminal {self._parent.name} is locked and cannot be set!")
            return
        if self.limits == None:
            if type(value) == float:
                self._value = self.scaling * value
                try:
                    self.instrument_parameter(self.scaling * value)
                except:
                    self._parent_device.update_terminal_parameters()
                    self.instrument_parameter(self.scaling * value)
            else:
                self._value = value
                # TODO: Replace Try/Except block, update_terminal_parameters() should be called by mapping function
                try:
                    self.instrument_parameter(value)
                except:
                    self._parent_device.update_terminal_parameters()
                    self.instrument_parameter(value)
        else:
            raise Exception("Limits are not yet implemented!")

    @value.getter
    def value(self):
        # TODO: Replace Try/Except block, update_terminal_parameters() should be called by mapping function
        try:
            return self.instrument_parameter()
        except:
            self._parent_device.update_terminal_parameters()
            return self.instrument_parameter()

    @property
    def instrument_parameter(self):
        return self._instrument_parameter

    @instrument_parameter.setter
    def instrument_parameter(self, param: Parameter):
        if isinstance(param, Parameter) or param == None:
            self._instrument_parameter = param
        else:
            raise TypeError(f"{param} is not a QCoDeS parameter!")

    def ramp(self, value, ramp_rate: float = 0.1, ramp_time: float = 5, setpoint_intervall: float = 0.01):
        ramp_or_set_parameter(
            self.instrument_parameter,
            value,
            ramp_rate=ramp_rate,
            ramp_time=ramp_time,
            setpoint_intervall=setpoint_intervall,
        )

    def measured_ramp(self, value, num_points=100, station=None, name=None, metadata=None, priorize_stored_value=False):
        if station is None:
            station = self._parent_device.station
        if type(station) != Station:
            raise TypeError("No valid station assigned!")
        if self.locked:
            raise Exception(f"{self.name} is locked!")
        script = Generic_1D_Sweep()
        for terminal_name, terminal in self._parent_device.terminals.items():
            for param_name, param in terminal.terminal_parameters.items():
                if param.type == "dynamic":
                    param.type = "static"
        self.type = "dynamic"
        self.setpoints = np.linspace(self(), value, num_points)
        script.setup(
            self._parent_device.save_to_dict(priorize_stored_value=priorize_stored_value),
            metadata=metadata,
            name=name,
        )
        mapping = self._parent_device.instrument_parameters
        map_terminals_gui(station.components, script.gate_parameters, mapping)
        data = script.run()
        return data

    def save_default(self):
        """
        Saves current value as default value.
        """
        try:
            self.default_value = self.value
        except Exception as e:
            logger.warning(f"{e} was raised when trying to save default value of {self.name}")
            pass

    def set_default(self):
        """
        Sets value to default value
        """
        if self.default_value is not None:
            try:
                self.value = self.default_value
            except NotImplementedError as e:
                logger.debug(f"{e} was raised and ignored")
        else:
            logger.warning(f"No default value set for parameter {self.name}")

    def set_stored_value(self):
        """
        Sets value to stored value from dict
        """
        if self._stored_value is not None:
            try:
                self.value = self._stored_value
            except NotImplementedError as e:
                logger.debug(f"{e} was raised and ignored")
        else:
            logger.warning(f"No stored value set for parameter {self.name}")

    def __call__(self, value=None):
        if value == None:
            return self.value
        else:
            self.value = value


# class Virtual_Terminal_Parameter(Terminal_Parameter):
