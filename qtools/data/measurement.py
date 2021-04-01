#!/usr/bin/env python3
"""
Representations of domain objects (Measurements).
"""

from dataclasses import dataclass, field
from qtools.data.device import Device
from qtools.data.domain import DomainObject


@dataclass
class TemplateParameter(DomainObject):
    type: str


@dataclass
class MeasurementSettingScript(DomainObject):
    script: str
    language: str
    allowedParameters: list[TemplateParameter] = field(default_factory=list)
    # TODO: allowedParameters


@dataclass
class MeasurementSetting(DomainObject):
    script: MeasurementSettingScript


@dataclass
class EquipmentFunction(DomainObject):
    pass


@dataclass
class Equipment(DomainObject):
    description: str
    parameters: str
    functions: list[EquipmentFunction]
    # TODO: functions


@dataclass
class EquipmentInstance(DomainObject):
    type: Equipment
    parameter: str


@dataclass
class MeasurementType(DomainObject):
    model: str
    scriptTemplate: MeasurementSettingScript
    extractableParameters: str
    mapping: str
    equipments: list[Equipment] = field(default_factory=list)
    # TODO: equipments


@dataclass
class Experiment(DomainObject):
    description: str
    user: str
    group: str
    softwareNoiseFilters: str
    measurementType: MeasurementType
    equipmentInstances: list[EquipmentInstance] = field(default_factory=list)
    # TODO: equipmentInstances


@dataclass
class Measurement(DomainObject):
    device: Device
    experiment: Experiment
    setting: MeasurementSetting
    measurementParameters: str
