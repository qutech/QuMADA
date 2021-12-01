#!/usr/bin/env python3
"""
Measurement
"""
import numpy as np
from dataclasses import dataclass, field
from typing import MutableSequence, MutableMapping, Any, Union, Mapping, Sequence, Callable

from qcodes import Station
from qcodes.instrument import Parameter
from qcodes.utils.metadata import Metadatable
from qtools.data.measurement import EquipmentInstance, FunctionType
from qtools.instrument.mapping.base import _map_gate_to_instrument, filter_flatten_parameters
from qcodes.utils.dataset.doNd import LinSweep, AbstractSweep, ActionsT
from qcodes.instrument.parameter import _BaseParameter

class QtoolsStation(Station):
    """Station object, inherits from qcodes Station."""


class MeasurementScript():
    PARAMETER_NAMES: set[str] = {"voltage",
                                 "current",
                                 "current_compliance",
                                 "amplitude",
                                 "frequency",
                                 "output_enabled",
                                 "phase"}

    def __init__(self):
        self.properties: dict[Any, Any] = {}
        self.gate_parameters: dict[Any, Union[dict[Any, Union[Parameter, None]], Parameter, None]] = {}

    def add_gate_parameter(self,
                           parameter_name: str,
                           gate_name: str = None,
                           parameter: Parameter = None) -> None:
        """
        Adds a gate parameter to self.gate_parameters.

        Args:
            parameter_name (str): Name of the parameter. Has to be in MeasurementScript.PARAMETER_NAMES.
            gate_name (str): Name of the parameter's gate. Set this, if you want to define the parameter
                             under a specific gate. Defaults to None.
            parameter (Parameter): Custom parameter. Set this, if you want to set a custom parameter. Defaults to None.
        """
        if parameter_name not in MeasurementScript.PARAMETER_NAMES:
            raise NameError(f"parameter_name \"{parameter_name}\" not in MeasurementScript.PARAMETER_NAMES.")
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

    def setup(self,
              parameters: dict,
              metadata: dict) -> None:
        """
        Adds all gate_parameters that are defined in the parameters argument to
        the measurement. Allows to pass metadata dictionary to measurement.

        Args:
            parameters (dict): Dictionary containing parameters and their settings
            metadata (dict): Dictionary containing metadata that should be
                            available for the measurement.
        """
        self.metadata = metadata
        for gate, vals in parameters.items():
            self.properties[gate] = vals
            for parameter, properties in vals.items():
                self.add_gate_parameter(parameter, gate)

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
        self.gettable_parameters: list[str] = []
        self.gettable_channels: list[str] = []
        self.break_conditions: list[str] = []
        self.static_parameters: list[str] = []
        self.dynamic_parameters: list[str] = []
        self.dynamic_sweeps: list[str] = []
        
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    channel.set(self.properties[gate][parameter]["value"])
                    self.static_parameters.append({"gate":gate,
                                                   "parameter":parameter})

                if self.properties[gate][parameter]["type"].find("gettable") >= 0:
                    self.gettable_parameters.append({"gate":gate,
                                                     "parameter":parameter})
                    self.gettable_channels.append(channel)
                    try:
                        for condition in self.properties[gate][parameter]["break_conditions"]:
                            self.break_conditions.append({"channel": channel, "break_condition": condition})
                    except KeyError:
                        pass
                elif self.properties[gate][parameter]["type"].find("dynamic") >= 0:
                    #Handle different possibilities for starting points
                    try:
                        channel.set(self.properties[gate][parameter]["value"])
                    except KeyError:
                        try:
                            channel.set(self.properties[gate][parameter]["start"])
                        except KeyError:
                            channel.set(self.properties[gate][parameter]["setpoints"][0])
                    self.dynamic_parameters.append({"gate":gate,
                                                   "parameter":parameter})
                    #Generate sweeps from parameters
                    try:
                        self.dynamic_sweeps.append(LinSweep(channel,
                                                            self.properties[gate][parameter]["start"],
                                                            self.properties[gate][parameter]["stop"],
                                                            self.properties[gate][parameter]["num_points"],
                                                            self.properties[gate][parameter]["delay"]))
                    except KeyError:
                        self.dynamic_sweeps.append(CustomSweep(channel,
                                                               self.properties[gate][parameter]["setpoints"],
                                                               delay = self.properties[gate][parameter].setdefault("delay", 0)))
        self._relabel_instruments()

    def reset(self) -> None:
        """
        Resets all static/dynamic parameters to their value/start value.
        """
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    channel.set(self.properties[gate][parameter]["value"])
                elif self.properties[gate][parameter]["type"].find("dynamic") >= 0:
                    try:
                        channel.set(self.properties[gate][parameter]["value"])
                    except KeyError:
                        try:
                            channel.set(self.properties[gate][parameter]["start"])
                        except KeyError:
                            channel.set(self.properties[gate][parameter]["setpoints"][0])


    def _relabel_instruments(self) -> None:
        """
        Changes the labels of all instrument channels to the
        corresponding name defined in the measurement script.
        Has to be done after mapping!
        """
        for gate, parameters in self.gate_parameters.items():
            for key, parameter in parameters.items():
                parameter.label = f"{gate} {key}"


class VirtualGate():
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


class VirtualParameter():
    pass


@dataclass
class FunctionMapping():
    """Data structure, that holds the mapping of several instrument parameters
    that correspond to one specific FunctionType.
    """
    name: str
    function_type: FunctionType
    gate: VirtualGate
    parameters: MutableMapping[Any, Parameter] = field(default_factory=dict)


class ExperimentHandler():
    """Experiment Handler"""
    def __init__(self, station: Station = None,
                 equipmentInstances: MutableSequence[EquipmentInstance] = None) -> None:
        if equipmentInstances is None:
            equipmentInstances = []

        if station:
            self._station = station
        else:
            self._station = Station()

        for instance in equipmentInstances:
            self._load_instrument(instance)

    def _load_instrument(self, instance: EquipmentInstance):
        pass


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
        param: _BaseParameter,
        setpoints: np.ndarray,
        delay: float = 0,
        post_actions: ActionsT = ()

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
    def param(self) -> _BaseParameter:
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
