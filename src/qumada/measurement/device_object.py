from __future__ import annotations

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

from qumada.instrument.buffers.buffer import is_bufferable, is_triggerable
from qumada.metadata import Metadata
from qumada.utils.ramp_parameter import ramp_or_set_parameter
from qumada.utils.utils import flatten_array

logger = logging.getLogger(__name__)


def is_measurement_script(o):
    return inspect.isclass(o) and issubclass(o, MeasurementScript)


class QumadaDevice:
    def __init__(
        self,
        make_terminals_global=True,
        namespace=None,
    ):
        self.namespace = namespace or globals()
        self.terminals = {}
        self.instrument_parameters = {}
        self.make_terminals_global = make_terminals_global

    def add_terminal(self, terminal_name: str, type: str | None = None, terminal_data: dict | None = {}):
        if terminal_name not in self.terminals.keys():
            self.__dict__[terminal_name.replace(" ", "_")] = self.terminals[terminal_name] = Terminal(
                terminal_name, self, type
            )
        else:
            raise Exception(f"Terminal {terminal_name} already exists. Please remove it first!")
        if self.make_terminals_global:
            if terminal_name not in self.namespace.keys():
                # Adding to the global namespace
                self.namespace[terminal_name] = self.terminals[terminal_name]
                logger.warning(f"Added {terminal_name} to global namespace!")
            else:
                raise Exception(
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

    def set_defaults(self):
        """
        Sets all Terminals and their parameters to their default values
        """
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.set_default()

    @staticmethod
    def create_from_dict(data: dict, make_terminals_global=True, namespace=None):
        device = QumadaDevice(make_terminals_global=make_terminals_global, namespace=namespace)
        for terminal_name, terminal_data in data.items():
            device.add_terminal(terminal_name, terminal_data=terminal_data)
            for parameter_name, properties in terminal_data.items():
                device.terminals[terminal_name].add_terminal_parameter(parameter_name, properties=properties)
        return device

    def load_from_dict(self, data: dict):
        device = self
        for terminal_name, terminal_data in data.items():
            device.add_terminal(terminal_name, terminal_data=terminal_data)
            for parameter_name, properties in terminal_data.items():
                device.terminals[terminal_name].add_terminal_parameter(parameter_name, properties=properties)
        return device

    def save_to_dict(self, dictionary: dict): ...


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

    def __init__(self, name, parent: QtoolsDevice | None = None, type: str | None = None):
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
            raise Exception(f"Parameter{parameter_name} already exists")

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
        self.properties: Dict[Any, Any] = properties
        self.type = self.properties.get("type", None)
        self._stored_value = self.properties.get("value", None)  # For storing values for measurements
        self.setpoints = self.properties.get("setpoints", None)
        self.delay = self.properties.get("delay", 0)
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
                    self._parent._parent.update_terminal_parameters()
                    self.instrument_parameter(self.scaling * value)
            else:
                self._value = value
                # TODO: Replace Try/Except block, update_terminal_parameters() should be called by mapping function
                try:
                    self.instrument_parameter(value)
                except:
                    self._parent._parent.update_terminal_parameters()
                    self.instrument_parameter(value)
        else:
            raise Exception("Limits are not yet implemented!")

    @value.getter
    def value(self):
        # TODO: Replace Try/Except block, update_terminal_parameters() should be called by mapping function
        try:
            return self.instrument_parameter()
        except:
            self._parent._parent.update_terminal_parameters()
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

    def __call__(self, value=None):
        if value == None:
            return self.value
        else:
            self.value = value


# class Virtual_Terminal_Parameter(Terminal_Parameter):
