"""
Representations of domain objects (Measurements).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from qtools.data.device import Device
from qtools.data.domain import DomainObject
from qtools.data.yaml import DomainYAMLObject


@dataclass
class TemplateParameter(DomainObject, DomainYAMLObject):
    """Represents the database entry of a template parameter."""

    yaml_tag = "!TemplateParameter"

    type: str

    @classmethod
    def create(cls, name: str, type: str, **kwargs) -> TemplateParameter:
        """Creates a TemplateParameter object."""
        kwargs.update({
            "name": name,
            "type": type,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateTemplateParameter")


@dataclass
class MeasurementSettingScript(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement setting script."""

    yaml_tag = "!MeasurementSettingScript"

    script: str
    language: str
    allowedParameters: list[TemplateParameter] = field(  # pylint: disable=invalid-name
        default_factory=list
    )
    # TODO: allowedParameters

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        script: str,
        language: str,
        allowedParameters: list[TemplateParameter],
        **kwargs
    ) -> MeasurementSettingScript:
        """Creates a MeasurementSettingScript object."""
        kwargs.update({
            "name": name,
            "script": script,
            "language": language,
            "allowedParameters": allowedParameters,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementSettingScript")


@dataclass
class MeasurementSettings(DomainObject, DomainYAMLObject):
    """Represents the database entry of the measurement settings."""

    yaml_tag = "!MeasurementSettings"

    script: MeasurementSettingScript

    @classmethod
    def create(
        cls, name: str, script: MeasurementSettingScript, **kwargs
    ) -> MeasurementSettings:
        """Creates a MeasurementSettings object."""
        kwargs.update({
            "name": name,
            "script": script,
        })
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[MeasurementSettings]:
        return super()._get_all(fn_name="measurementSettings")

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementSettings")


class FunctionType(Enum):
    """Possible equipment functions"""
    VOLTAGE_SOURCE = 0
    VOLTAGE_SOURCE_AC = 1
    VOLTAGE_SENSE = 2
    CURRENT_SOURCE = 3
    CURRENT_SENSE = 4
    CURRENT_SENSE_AC = 5


@dataclass
class EquipmentFunction(DomainObject, DomainYAMLObject):
    """Represents the database entry of a equipment function."""

    yaml_tag = "!EquipmentFunction"

    functionType: FunctionType  # pylint: disable=invalid-name

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls, name: str, functionType: FunctionType, **kwargs
    ) -> EquipmentFunction:
        """Creates an EquipmentFunction object."""
        kwargs.update({
            "name": name,
            "functionType": functionType,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateEquipmentFunction")


@dataclass
class Equipment(DomainObject, DomainYAMLObject):
    """Represents the database entry of an equipment."""

    yaml_tag = "!Equipment"

    description: str
    parameters: str
    functions: list[EquipmentFunction]
    # TODO: functions

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        parameters: str,
        functions: list[EquipmentFunction],
        **kwargs
    ) -> Equipment:
        """Creates an Equipment object."""
        kwargs.update({
            "name": name,
            "description": description,
            "parameters": parameters,
            "functions": functions,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateEquipment")


@dataclass
class EquipmentInstance(DomainObject, DomainYAMLObject):
    """Represents the database entry of an equipment instance."""

    yaml_tag = "!EquipmentInstance"

    type: Equipment
    parameter: str

    @classmethod
    def create(
        cls, name: str, type: Equipment, parameter: str, **kwargs
    ) -> EquipmentInstance:
        """Creates an EquipmentInstance object."""
        kwargs.update({
            "name": name,
            "type": type,
            "parameter": parameter,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateEquipmentInstance")


@dataclass
class MeasurementType(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement type."""

    yaml_tag = "!MeasurementType"

    model: str
    scriptTemplate: MeasurementSettingScript  # pylint: disable=invalid-name
    extractableParameters: str  # pylint: disable=invalid-name
    mapping: str
    equipments: list[Equipment] = field(default_factory=list)
    # TODO: equipments

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        model: str,
        scriptTemplate: MeasurementSettingScript,
        extractableParameters: str,
        mapping: str,
        equipments: list[Equipment],
        **kwargs
    ) -> MeasurementType:
        """Creates a MeasurementType object."""
        kwargs.update(
            {
                "name": name,
                "model": model,
                "scriptTemplate": scriptTemplate,
                "extractableParameters": extractableParameters,
                "mapping": mapping,
                "equipments": equipments,
            }
        )
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[MeasurementType]:
        return super()._get_all("measurementTypes")

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementType")


@dataclass
class Experiment(DomainObject, DomainYAMLObject):
    """Represents the database entry of an experiment."""

    yaml_tag = "!Experiment"

    description: str
    user: str
    group: str
    measurementType: MeasurementType  # pylint: disable=invalid-name
    softwareNoiseFilters: str  # pylint: disable=invalid-name
    equipmentInstances: list[EquipmentInstance] = field(  # pylint: disable=invalid-name
        default_factory=list
    )
    # TODO: equipmentInstances

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        user: str,
        group: str,
        measurementType: MeasurementType,
        softwareNoiseFilters: str | None = None,
        equipmentInstances: list[EquipmentInstance] | None = None,
        **kwargs
    ) -> Experiment:
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
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateExperiment")


@dataclass
class Measurement(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement."""

    yaml_tag = "!Measurement"

    device: Device
    experiment: Experiment
    settings: MeasurementSettings
    measurementParameters: str  # pylint: disable=invalid-name

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        device: Device,
        experiment: Experiment,
        settings: MeasurementSettings,
        measurementParameters: str,
        **kwargs
    ) -> Measurement:
        """Creates a Measurement object."""
        kwargs.update({
            "name": name,
            "device": device,
            "experiment": experiment,
            "settings": settings,
            "measurementParameters": measurementParameters,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurement")
