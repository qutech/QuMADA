#!/usr/bin/env python3
"""
Representations of domain objects (Measurements).
"""

from enum import Enum
from dataclasses import dataclass, field

from qtools.data.device import Device
from qtools.data.domain import DomainObject


@dataclass
class TemplateParameter(DomainObject):
    """Represents the database entry of a template parameter."""
    type: str


@dataclass
class MeasurementSettingScript(DomainObject):
    """Represents the database entry of a measurement setting script."""
    script: str
    language: str
    allowedParameters: list[TemplateParameter] = field(default_factory=list)
    # TODO: allowedParameters


@dataclass
class MeasurementSetting(DomainObject):
    """Represents the database entry of a measurement setting."""
    script: MeasurementSettingScript


class FunctionType(Enum):
    """Possible equipment functions"""
    VOLTAGE_SOURCE = 0
    VOLTAGE_SOURCE_AC = 1
    VOLTAGE_SENSE = 2
    CURRENT_SOURCE = 3
    CURRENT_SENSE = 4
    CURRENT_SENSE_AC = 5


class VirtualParameter:
    pass


class VoltageSourceACParameter(VirtualParameter):
    def __init__(self, amplitude: Parameter, frequency: Parameter):
        self.amplitude = amplitude
        self.frequency = frequency
        self.time_constant = time_constant
        self.sensitivity


@dataclass
class EquipmentFunction(DomainObject):
    """Represents the database entry of a equipment function."""
    functionType: FunctionType


@dataclass
class Equipment(DomainObject):
    """Represents the database entry of an equipment."""
    description: str
    parameters: str
    functions: list[EquipmentFunction]
    # TODO: functions


@dataclass
class EquipmentInstance(DomainObject):
    """Represents the database entry of an equipment instance."""
    type: Equipment
    parameter: str


@dataclass
class MeasurementType(DomainObject):
    """Represents the database entry of a measurement type."""
    model: str
    scriptTemplate: MeasurementSettingScript
    extractableParameters: str
    mapping: str
    equipments: list[Equipment] = field(default_factory=list)
    # TODO: equipments


@dataclass
class Experiment(DomainObject):
    """Represents the database entry of an experiment."""
    description: str
    user: str
    group: str
    softwareNoiseFilters: str
    measurementType: MeasurementType
    equipmentInstances: list[EquipmentInstance] = field(default_factory=list)
    # TODO: equipmentInstances


@dataclass
class Measurement(DomainObject):
    """Represents the database entry of a measurement."""
    device: Device
    experiment: Experiment
    setting: MeasurementSetting
    measurementParameters: str
