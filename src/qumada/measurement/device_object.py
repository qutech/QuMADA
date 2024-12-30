from __future__ import annotations

import inspect
import logging
from abc import ABC
from copy import deepcopy
from functools import wraps
from typing import Any

import numpy as np
from qcodes import Station
from qcodes.parameters import Parameter
from qcodes.validators.validators import Numbers

from qumada.instrument.buffers.buffer import map_triggers
from qumada.instrument.mapping import map_terminals_gui
from qumada.measurement.measurement import load_param_whitelist
from qumada.measurement.scripts import (
    Generic_1D_Hysteresis_buffered,
    Generic_1D_parallel_asymm_Sweep,
    Generic_1D_Sweep,
    Generic_1D_Sweep_buffered,
    Generic_2D_Sweep_buffered,
    Generic_nD_Sweep,
    Generic_Pulsed_Measurement,
    Generic_Pulsed_Repeated_Measurement,
    Timetrace,
    Timetrace_buffered,
)
from qumada.utils.ramp_parameter import ramp_or_set_parameter

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
        self.buffer_settings = {}
        self.buffer_script_setup = {}
        self.states = {}
        self.ramp: bool = True

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
                self.namespace[terminal_name.replace(" ", "_")] = self.terminals[terminal_name]
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

    def save_defaults(self, ramp=None, **kwargs):
        """
        Saves current values as default for all Terminals and their parameters
        """
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.save_default()

    def save_state(self, name: str):
        """
        Saves current state (inclung types, limits etc) as entry in the tuning dict with name as key.
        """
        self.states[name] = self.save_to_dict(priorize_stored_value=False)

    def set_state(self, name: str, ramp=None, **kwargs):
        if ramp is None:
            ramp = self.ramp
        self.load_from_dict(self.states[name])
        self.set_stored_values(ramp=ramp, **kwargs)

    def set_stored_values(self, ramp=None, **kwargs):
        if ramp is None:
            ramp = self.ramp
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.set_stored_value()

    def set_defaults(self, ramp=None, **kwargs):
        """
        Sets all Terminals and their parameters to their default values
        """
        if ramp is None:
            ramp = self.ramp
        for terminal in self.terminals.values():
            for param in terminal.terminal_parameters.values():
                param.set_default(ramp=ramp, **kwargs)

    def voltages(self):
        """
        Prints all paramters called voltage from all Terminals of the device.
        """

        for terminal in self.terminals.values():
            try:
                label = terminal.name
                voltage = terminal.voltage()
                print(f"{label} {voltage=}")
            except AttributeError:
                pass

    @staticmethod
    def create_from_dict(data: dict, station: Station | None = None, make_terminals_global=False, namespace=None):
        """
        Creates a QumadaDevice object from valid parameter dictionaries as used in Qumada measurement scripts.
        Be aware that the validity is not checked at the moment, so there might be unexpected exceptions!
        Parameter values are not set upon initialization for safety reason! They are stored in
        the _stored_values attribute.
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
                for attr_name in [
                    "type",
                    "setpoints",
                    "delay",
                    "start",
                    "stop",
                    "num_points",
                    "break_conditions",
                    "limits",
                    "group",
                    "leverarms",
                    "compensated_gates",
                ]:
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

    def mapping(self, instrument_parameters: None | dict = None):
        if instrument_parameters is None:
            instrument_parameters = self.instrument_parameters
        if not isinstance(self.station, Station):
            raise TypeError("No valid qcodes station found. Make sure you have set the station attribute correctly!")
        map_terminals_gui(self.station.components, self.instrument_parameters, instrument_parameters)
        self.update_terminal_parameters()

    def timetrace(
        self,
        duration: float,
        timestep: float = 1,
        name=None,
        metadata=None,
        station=None,
        buffered=False,
        buffer_settings: dict | None = None,
        priorize_stored_value=False,
    ):
        """ """
        if station is None:
            station = self.station
        if not isinstance(station, Station):
            raise TypeError("No valid station assigned!")
        if buffer_settings is None:
            buffer_settings = self.buffer_settings
        temp_buffer_settings = deepcopy(buffer_settings)
        if buffered is True:
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
        if buffered is True:
            map_triggers(station.components, script.properties, script.gate_parameters)
        data = script.run()
        return data

    def sweep_2D(
        self,
        slow_param: Parameter,
        fast_param: Parameter,
        slow_param_range: float,
        fast_param_range: float,
        slow_num_points: int = 50,
        fast_num_points: int = 100,
        name=None,
        metadata=None,
        station=None,
        buffered=False,
        buffer_settings: dict | None = None,
        priorize_stored_value=False,
        restore_state=True,
    ):
        """ """
        if station is None:
            station = self.station
        if not isinstance(station, Station):
            raise TypeError("No valid station assigned!")
        self.save_state("_temp_2D")
        try:
            for terminal in self.terminals.values():
                for parameter in terminal.terminal_parameters.values():
                    if parameter.type == "dynamic":
                        parameter.type = "static gettable"
            slow_param.type = "dynamic"
            slow_param.setpoints = np.linspace(
                slow_param.value - slow_param_range / 2.0, slow_param.value + slow_param_range / 2.0, slow_num_points
            )
            slow_param.group = 1
            fast_param.type = "dynamic"
            fast_param.group = 2
            fast_param.setpoints = np.linspace(
                fast_param.value - fast_param_range / 2.0, fast_param.value + fast_param_range / 2.0, fast_num_points
            )
            if buffer_settings is None:
                buffer_settings = self.buffer_settings
            temp_buffer_settings = deepcopy(buffer_settings)
            if buffered is True:
                if "num_points" in temp_buffer_settings.keys():
                    temp_buffer_settings["num_points"] = fast_num_points
                    logger.warning(
                        f"Temporarily changed buffer settings to match the \
                        number of points specified {fast_num_points=}"
                    )
                else:
                    logger.warning(
                        "Num_points not specified in buffer settings! fast_num_points value is \
                        ignored and buffer settings are used to specify measurement!"
                    )

                script = Generic_2D_Sweep_buffered()
            else:
                script = Generic_nD_Sweep()
            script.setup(
                self.save_to_dict(priorize_stored_value=priorize_stored_value),
                metadata=metadata,
                name=name,
                buffer_settings=temp_buffer_settings,
                **self.buffer_script_setup,
            )
            mapping = self.instrument_parameters
            map_terminals_gui(station.components, script.gate_parameters, mapping)
            if buffered is True:
                map_triggers(station.components, script.properties, script.gate_parameters)
            data = script.run()
        except Exception as e:
            print(self.states["_temp_2D"])
            self.set_state("_temp_2D")
            raise e
        finally:
            print(self.states["_temp_2D"])
            self.set_state("_temp_2D")
            del self.states["_temp_2D"]
        return data

    def sweep_parallel(
        self,
        params: list[Parameter],
        setpoints: list[list[float]] | None = None,
        target_values: list[float] | None = None,
        num_points: int = 100,
        name=None,
        metadata=None,
        station=None,
        priorize_stored_value=False,
        **kwargs,
    ):
        """
        Sweep multiple parameters in parallel.
        Provide either setpoints or target_values. Setpoints have to have the same length for all parameters.
        If no setpoints are provided, the target_values will be used to create the setpoints. Ramps will start from
        the current value of the parameters then.
        Gettable parameters and break conditions will be set according to their state in the device object.
        You can pass backsweep_after_break as a kwarg. If set to True, the sweep will continue in the opposite
        direction after a break condition is reached.
        """
        if station is None:
            station = self.station
        if not isinstance(station, Station):
            raise TypeError("No valid station assigned!")
        if setpoints is None and target_values is None:
            raise (Exception("Either setpoints or target_values have to be provided!"))
        if target_values is not None and setpoints is not None:
            raise (Exception("Either setpoints or target_values have to be provided, not both!"))
        if setpoints is None:
            assert len(params) == len(target_values)
            setpoints = [np.linspace(param(), target, num_points) for param, target in zip(params, target_values)]
        assert len(params) == len(setpoints)
        assert all([len(setpoint) == len(setpoints[0]) for setpoint in setpoints])

        for terminal in self.terminals.values():
            for parameter in terminal.terminal_parameters.values():
                if parameter not in params and parameter.type == "dynamic":
                    parameter.type = "static gettable"
                if parameter in params:
                    parameter.type = "dynamic"
                    parameter.setpoints = setpoints[params.index(parameter)]
        script = Generic_1D_parallel_asymm_Sweep()
        script.setup(
            self.save_to_dict(priorize_stored_value=priorize_stored_value), metadata=metadata, name=name, **kwargs
        )
        mapping = self.instrument_parameters
        map_terminals_gui(station.components, script.gate_parameters, mapping)
        data = script.run()
        return data

    def pulsed_measurement(
        self,
        params: list[Parameter],
        setpoints: list[list[float]],
        repetitions: int = 1,
        name=None,
        metadata=None,
        station=None,
        buffer_settings: dict | None = None,
        priorize_stored_value=False,
        **kwargs,
    ):
        if station is None:
            station = self.station
        if not isinstance(station, Station):
            raise TypeError("No valid station assigned!")
        assert len(params) == len(setpoints)
        assert all([len(setpoint) == len(setpoints[0]) for setpoint in setpoints])
        assert repetitions >= 1
        if buffer_settings is None:
            buffer_settings = self.buffer_settings
        temp_buffer_settings = deepcopy(buffer_settings)

        if "num_points" in temp_buffer_settings.keys():
            temp_buffer_settings["num_points"] = len(setpoints[0])
            logger.warning(
                "Temporarily changed buffer settings to match the \
                number of points specified in the setpoints"
            )
        else:
            raise Exception(
                "For this kind of measurement, you have to specify the number of points in the buffer settings!"
            )
        for terminal in self.terminals.values():
            for parameter in terminal.terminal_parameters.values():
                if parameter not in params and parameter.type == "dynamic":
                    parameter.type = "static gettable"
                if parameter in params:
                    parameter.type = "dynamic"
                    parameter.setpoints = setpoints[params.index(parameter)]
        if repetitions == 1:
            script = Generic_Pulsed_Measurement()
        elif repetitions > 1:
            script = Generic_Pulsed_Repeated_Measurement()
        script.setup(
            self.save_to_dict(priorize_stored_value=priorize_stored_value),
            metadata=metadata,
            measurement_name=name,  # achtung geändert!
            repetitions=repetitions,
            buffer_settings=temp_buffer_settings,
            **self.buffer_script_setup,
            **kwargs,
        )
        mapping = self.instrument_parameters
        map_terminals_gui(station.components, script.gate_parameters, mapping)
        map_triggers(station.components, script.properties, script.gate_parameters)
        data = script.run()
        return data


def create_hook(func, hook):
    """
    Decorator to hook a function onto an existing function.
    The hook function can use keyword-only arguments, which are omitted prior
    to execution of the main function.
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
    PARAMETER_NAMES: set[str] = load_param_whitelist()

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
        self._limits = self.properties.get("limits", None)
        self.leverarms = self.properties.get("leverarms", None)
        self.compensated_gates = self.properties.get("compensated_gates")
        self.rampable = False
        self.ramp_rate = self.properties.get("ramp_rate", 0.1)
        self.group = self.properties.get("group", None)
        self.default_value = None
        self.scaling = 1  # Only relevant for setting values. Not taken into account for measurements!
        self._instrument_parameter = None
        self.locked = False
        self._limit_validator = None

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
        self.leverarms = self.properties.get("leverarms", self.leverarms)
        self.compensated_gates = self.properties.get("compensated_gates")

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.locked is True:
            raise Exception(f"Parameter {self.name} of Terminal {self._parent.name} is locked and cannot be set!")
            return

        if isinstance(value, float):
            self._value = self.scaling * value
            try:
                self.instrument_parameter(self.scaling * value)
            except TypeError:
                self._parent_device.update_terminal_parameters()
                self.instrument_parameter(self.scaling * value)
        else:
            self._value = value
            # TODO: Replace Try/Except block, update_terminal_parameters() should be called by mapping function
            try:
                self.instrument_parameter(value)
            except TypeError:
                self._parent_device.update_terminal_parameters()
                self.instrument_parameter(value)

    @value.getter
    def value(self):
        # TODO: Replace Try/Except block, update_terminal_parameters() should be called by mapping function
        try:
            return self.instrument_parameter()
        except TypeError:
            self._parent_device.update_terminal_parameters()
            return self.instrument_parameter()

    @property
    def instrument_parameter(self):
        return self._instrument_parameter

    @instrument_parameter.setter
    def instrument_parameter(self, param: Parameter):
        if isinstance(param, Parameter) or param is None:
            self._instrument_parameter = param
            self._set_limits()
        else:
            raise TypeError(f"{param} is not a QCoDeS parameter!")

    @property
    def limits(self):
        return self._limits

    @limits.setter
    def limits(self, limits):
        if type(limits) in (list, tuple) and len(limits) == 2:
            self._limits = limits
            self._set_limits()
        else:
            raise ValueError("Limits has to be a list|tuple with two entries")

    def _set_limits(self):
        """
        Uses QCoDeS parameter's validators to limit values of parameters with
        number value to the values set in the limits attribute.
        Will replace last validator of corresponding parameter, if it was set
        by this method before! Won't remove validators that existed before
        initialization of the parameter. Make sure not to add validators
        manually to avoid problem (QCoDeS can only remove the last added
        validator, so it's not possible to just remove the correct one.')
        """
        if self.limits is None:
            return
        if len(self.limits) != 2:
            raise ValueError(f"Invalid limits provided for {self._parent.name} {self.name}")
        param = self.instrument_parameter
        if not isinstance(param, Parameter):
            logger.exception(
                f"Cannot set limits to {self._parent.name} {self.name} \
                             as no valid instrument parameter was assigned to it!"
            )
        else:
            try:
                if self._limit_validator in param.validators:
                    param.remove_validator()
            except AttributeError as e:
                logger.warning(e)
                pass
            self._limit_validator = Numbers(min_value=min(self.limits), max_value=max(self.limits))
            param.add_validator(self._limit_validator)

    def ramp(self, value, ramp_rate: float | None = None, ramp_time: float = 5, setpoint_intervall: float = 0.01):
        if ramp_rate is None:
            ramp_rate = self.ramp_rate
        ramp_or_set_parameter(
            self.instrument_parameter,
            value,
            ramp_rate=ramp_rate,
            ramp_time=ramp_time,
            setpoint_intervall=setpoint_intervall,
        )

    def measured_ramp(
        self,
        value,
        num_points=100,
        start=None,
        station=None,
        name=None,
        metadata=None,
        backsweep=False,
        buffered=False,
        buffer_settings: dict | None = None,
        priorize_stored_value=False,
    ):
        if station is None:
            station = self._parent_device.station
        if not isinstance(station, Station):
            raise TypeError("No valid station assigned!")
        if self.locked:
            raise Exception(f"{self.name} is locked!")

        for terminal_name, terminal in self._parent_device.terminals.items():
            for param_name, param in terminal.terminal_parameters.items():
                if param.type == "dynamic":
                    param.type = "static gettable"
        self.type = "dynamic"
        if start is None:
            start = self()
        if backsweep is True:
            if buffered is False:
                self.setpoints = [*np.linspace(start, value, num_points), *np.linspace(value, start, num_points)]
            else:
                self.setpoints = np.linspace(start, value, num_points)
        else:
            self.setpoints = np.linspace(start, value, num_points)
        temp_buffer_settings = deepcopy(self._parent_device.buffer_settings)
        temp_buffer_settings.update(buffer_settings or {})
        if buffered:
            if "num_points" in temp_buffer_settings.keys():
                temp_buffer_settings["num_points"] = num_points
                logger.warning(
                    f"Temporarily changed buffer settings to match the number of points specified {num_points=}"
                )
            else:
                logger.warning(
                    "Num_points not specified in buffer settings! fast_num_points value is \
                        ignored and buffer settings are used to specify measurement!"
                )
            if backsweep is True:
                script = Generic_1D_Hysteresis_buffered()
            else:
                script = Generic_1D_Sweep_buffered()
        else:
            script = Generic_1D_Sweep()
        script.setup(
            self._parent_device.save_to_dict(priorize_stored_value=priorize_stored_value),
            metadata=metadata,
            name=name,
            iterations=1,
            buffer_settings=temp_buffer_settings,
            **self._parent_device.buffer_script_setup,
        )
        mapping = self._parent_device.instrument_parameters
        map_terminals_gui(station.components, script.gate_parameters, mapping)
        if buffered is True:
            map_triggers(station.components, script.properties, script.gate_parameters)
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

    def set_default(self, ramp=True, **kwargs):
        """
        Sets value to default value
        """
        if self.default_value is not None:
            try:
                if ramp is True:
                    self.ramp(self.default_value, **kwargs)
                else:
                    self.value = self.default_value
            except NotImplementedError as e:
                logger.debug(f"{e} was raised and ignored")
        else:
            logger.warning(f"No default value set for parameter {self.name}")

    def set_stored_value(self, ramp=True, **kwargs):
        """
        Sets value to stored value from dict
        """
        if self._stored_value is not None:
            try:
                if ramp is True:
                    self.ramp(self._stored_value, **kwargs)
                else:
                    self.value = self._stored_value
            except NotImplementedError as e:
                logger.debug(f"{e} was raised and ignored")
        else:
            logger.warning(f"No stored value set for parameter {self.name}")

    def __call__(self, value=None, ramp=None):
        if value is None:
            return self.value
        else:
            if ramp is True:
                self.ramp(value)
            else:
                self.value = value


# class Virtual_Terminal_Parameter(Terminal_Parameter):
