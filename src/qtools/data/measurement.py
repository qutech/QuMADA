#!/usr/bin/env python3
"""
Representations of domain objects (Measurements).
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from qtools.data.db import (get_equipment_by_id,
                            get_equipment_function_by_id,
                            get_equipment_instance_by_id,
                            get_experiment_by_id,
                            get_measurement_by_id,
                            get_measurement_setting_by_id,
                            get_measurement_setting_script_by_id,
                            get_measurement_type_by_id,
                            get_template_parameter_by_id,
                            save_or_update_equipment,
                            save_or_update_equipment_function,
                            save_or_update_equipment_instance,
                            save_or_update_experiment,
                            save_or_update_measurement,
                            save_or_update_measurement_setting,
                            save_or_update_measurement_setting_script,
                            save_or_update_measurement_type,
                            save_or_update_template_parameter)

from qtools.data.device import Device
from qtools.data.domain import DomainObject


@dataclass
class TemplateParameter(DomainObject):
    """Represents the database entry of a template parameter."""
    type: str

    @classmethod
    def create(cls,
               name: str,
               type: str,
               **kwargs):
        """Creates a TemplateParameter object."""
        kwargs.update({
            "name": name,
            "type": type,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create a TemplateParameter object from an existing db entry."""
        data = get_template_parameter_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the TemplateParameter object to the db."""
        response = save_or_update_template_parameter(self.name,
                                                     self.type,
                                                     self.pid)
        self._handle_db_response(response)


@dataclass
class MeasurementSettingScript(DomainObject):
    """Represents the database entry of a measurement setting script."""
    script: str
    language: str
    allowedParameters: list[TemplateParameter] = field(default_factory=list)
    # TODO: allowedParameters

    @classmethod
    def create(cls,
               name: str,
               script: str,
               language: str,
               allowedParameters: list[TemplateParameter],
               **kwargs):
        """Creates a MeasurementSettingScript object."""
        kwargs.update({
            "name": name,
            "script": script,
            "language": language,
            "allowedParameters": allowedParameters,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create a MeasurementSettingScript object from an existing db entry."""
        data = get_measurement_setting_script_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the MeasurementSettingScript object to the db."""
        response = save_or_update_measurement_setting_script(self.name,
                                                             self.script,
                                                             self.language,
                                                             ",".join(self.allowedParameters),
                                                             self.pid)
        self._handle_db_response(response)


@dataclass
class MeasurementSettings(DomainObject):
    """Represents the database entry of the measurement settings."""
    script: MeasurementSettingScript

    @classmethod
    def create(cls,
               name: str,
               script: MeasurementSettingScript,
               **kwargs):
        """Creates a MeasurementSettings object."""
        kwargs.update({
            "name": name,
            "script": script,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create a MeasurementSettings object from an existing db entry."""
        data = get_measurement_setting_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the MeasurementSettings object to the db."""
        response = save_or_update_measurement_setting(self.name,
                                                      self.script.pid,
                                                      self.pid)
        self._handle_db_response(response)


class FunctionType(Enum):
    """Possible equipment functions"""
    VOLTAGE_SOURCE = 0
    VOLTAGE_SOURCE_AC = 1
    VOLTAGE_SENSE = 2
    CURRENT_SOURCE = 3
    CURRENT_SENSE = 4
    CURRENT_SENSE_AC = 5


@dataclass
class EquipmentFunction(DomainObject):
    """Represents the database entry of a equipment function."""
    functionType: FunctionType

    @classmethod
    def create(cls,
               name: str,
               functionType: FunctionType,
               **kwargs):
        """Creates an EquipmentFunction object."""
        kwargs.update({
            "name": name,
            "functionType": functionType,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create an EquipmentFunction object from an existing db entry."""
        data = get_equipment_function_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the EquipmentFunction object to the db."""
        response = save_or_update_equipment_function(self.name,
                                                     self.functionType.value,
                                                     self.pid)
        self._handle_db_response(response)


@dataclass
class Equipment(DomainObject):
    """Represents the database entry of an equipment."""
    description: str
    parameters: str
    functions: list[EquipmentFunction]
    # TODO: functions

    @classmethod
    def create(cls,
               name: str,
               description: str,
               parameters: str,
               functions: list[EquipmentFunction],
               **kwargs):
        """Creates an Equipment object."""
        kwargs.update({
            "name": name,
            "description": description,
            "parameters": parameters,
            "functions": functions,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create an Equipment object from an existing db entry."""
        data = get_equipment_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the Equipment object to the db."""
        response = save_or_update_equipment(self.name,
                                            self.description,
                                            self.parameters,
                                            ",".join(self.functions),
                                            self.pid)
        self._handle_db_response(response)


@dataclass
class EquipmentInstance(DomainObject):
    """Represents the database entry of an equipment instance."""
    type: Equipment
    parameter: str

    @classmethod
    def create(cls,
               name: str,
               type: Equipment,
               parameter: str,
               **kwargs):
        """Creates an EquipmentInstance object."""
        kwargs.update({
            "name": name,
            "type": type,
            "parameter": parameter,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create an EquipmentInstance object from an existing db entry."""
        data = get_equipment_instance_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the EquipmentInstance object to the db."""
        response = save_or_update_equipment_instance(self.name,
                                                     self.type.pid,
                                                     self.parameter,
                                                     self.pid)
        self._handle_db_response(response)


@dataclass
class MeasurementType(DomainObject):
    """Represents the database entry of a measurement type."""
    model: str
    scriptTemplate: MeasurementSettingScript
    extractableParameters: str
    mapping: str
    equipments: list[Equipment] = field(default_factory=list)
    # TODO: equipments

    @classmethod
    def create(cls,
               name: str,
               model: str,
               scriptTemplate: MeasurementSettingScript,
               exctractableParameters: str,
               mapping: str,
               equipments: list[Equipment],
               **kwargs):
        """Creates a MeasurementType object."""
        kwargs.update({
            "name": name,
            "model": model,
            "scriptTemplate": scriptTemplate,
            "exctractableParameters": exctractableParameters,
            "mapping": mapping,
            "equipments": equipments
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create a MeasurementType object from an existing db entry."""
        data = get_measurement_type_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the MeasurementType object to the db."""
        response = save_or_update_measurement_type(self.name,
                                                   self.model,
                                                   self.scriptTemplate.pid,
                                                   self.extractableParameters,
                                                   self.mapping,
                                                   ",".join(self.equipments),
                                                   self.pid)
        self._handle_db_response(response)


@dataclass
class Experiment(DomainObject):
    """Represents the database entry of an experiment."""
    description: str
    user: str
    group: str
    measurementType: MeasurementType
    softwareNoiseFilters: str
    equipmentInstances: list[EquipmentInstance] = field(default_factory=list)
    # TODO: equipmentInstances

    @classmethod
    def create(cls,
               name: str,
               description: str,
               user: str,
               group: str,
               measurementType: MeasurementType,
               softwareNoiseFilters: str | None = None,
               equipmentInstances: list[EquipmentInstance] | None = None,
               **kwargs):
        """Creates an Experiment object."""
        kwargs.update({
            "name": name,
            "description": description,
            "user": user,
            "group": group,
            "softwareNoiseFilters": softwareNoiseFilters,
            "measurementType": measurementType,
            "equipmentInstances": equipmentInstances
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create an Experiment object from an existing db entry."""
        data = get_experiment_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the Experiment object to the db."""
        response = save_or_update_experiment(self.description,
                                             self.name,
                                             self.user,
                                             self.group,
                                             self.softwareNoiseFilters,
                                             self.measurementType.name,
                                             ",".join(self.equipmentInstances),
                                             self.pid)
        self._handle_db_response(response)


@dataclass
class Measurement(DomainObject):
    """Represents the database entry of a measurement."""
    device: Device
    experiment: Experiment
    settings: MeasurementSettings
    measurementParameters: str

    @classmethod
    def create(cls,
               name: str,
               device: Device,
               experiment: Experiment,
               settings: MeasurementSettings,
               measurementParameters: str,
               **kwargs):
        """Creates a Measurement object."""
        kwargs.update({
            "name": name,
            "device": device,
            "experiment": experiment,
            "settings": settings,
            "measurementParameters": measurementParameters,
        })
        return super(cls, cls)._create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        """Create a Measurement object from an existing db entry."""
        data = get_measurement_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        """Saves or updates the Measurement object to the db."""
        response = save_or_update_measurement(self.name,
                                              self.device.name,
                                              self.experiment.name,
                                              self.settings.name,
                                              self.measurementParameters,
                                              self.pid)
        self._handle_db_response(response)
