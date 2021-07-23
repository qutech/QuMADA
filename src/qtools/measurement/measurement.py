#!/usr/bin/env python3
"""
Measurement
"""

from dataclasses import dataclass, field
from typing import Dict, MutableSequence, MutableMapping, Any, Set, Union

from qcodes import Station
from qcodes.instrument import Parameter
from qcodes.station import PARAMETER_ATTRIBUTES

from qtools.data.measurement import EquipmentInstance, FunctionType


class QtoolsStation(Station):
    """Station object, inherits from qcodes Station."""


class MeasurementScript():
    PARAMETER_NAMES: Set[str] = {"voltage",
                                 "current",
                                 "current_compliance",
                                 "amplitude",
                                 "frequency",
                                 "output_enabled"}

    def __init__(self):
        self.properties: Dict[Any, Any] = {}
        self.gate_parameters: Dict[Any, Union[Dict[Any, Parameter], Parameter]] = {}

    def add_gate_parameter(self,
                           parameter_name: str,
                           gate_name: str = None,
                           parameter: Parameter = None) -> None:
        """
        Adds a gate parameter to self.gate_parameters.

        Args:
            parameter_name (str): Name of the parameter. Has to be in MeasurementScript.PARAMETER_NAMES.
            gate_name (str): Name of the parameter's gate. Set this, if you want to define the parameter under a specific gate. Defaults to None.
            parameter (Parameter): Custom parameter. Set this, if you want to set a custom parameter. Defaults to None.
        """
        if parameter_name not in MeasurementScript.PARAMETER_NAMES:
            raise NameError(f"parameter_name \"{parameter_name}\" not in MeasurementScript.PARAMETER_NAMES.")
        if not gate_name:
            self.gate_parameters[parameter_name] = parameter
        else:
            self.gate_parameters.setdefault(gate_name, {})[parameter_name] = parameter


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
