"""
Representations of domain objects (Devices).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qtools.data.domain import DomainObject
from qtools.data.yaml import DomainYAMLObject


@dataclass
class Factory(DomainObject, DomainYAMLObject):
    """Represents the database entry of a factory."""

    yaml_tag = "!Factory"

    description: str

    @classmethod
    def create(cls, name: str, description: str, **kwargs) -> Factory:
        """Creates a Factory object."""
        kwargs.update({
            "name": name,
            "description": description,
        })
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[Factory]:
        return super()._get_all(fn_name="factories")

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateFactory")


@dataclass
class Wafer(DomainObject, DomainYAMLObject):
    """Represents the database entry of a wafer."""

    yaml_tag = "!Wafer"

    description: str
    productionDate: str  # pylint: disable=invalid-name

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls, name: str, description: str, productionDate: str, **kwargs
    ) -> Wafer:
        """Creates a Wafer object."""
        kwargs.update({
            "name": name,
            "description": description,
            "productionDate": productionDate,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateWafer")


@dataclass
class Sample(DomainObject, DomainYAMLObject):
    """Represents the database entry of a sample."""

    yaml_tag = "!Sample"

    description: str
    wafer: Wafer

    @classmethod
    def create(cls, name: str, description: str, wafer: Wafer, **kwargs) -> Sample:
        """Creates a Sample object."""
        kwargs.update({
            "name": name,
            "description": description,
            "wafer": wafer,
        })
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[Sample]:
        return super()._get_all("samples")

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateSample")


@dataclass
class Design(DomainObject, DomainYAMLObject):
    """Represents the database entry of a design."""

    yaml_tag = "!Design"

    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedForMeasurementTypes: list[Any] = field(default_factory=list)  # pylint: disable=invalid-name
    # TODO: MeasurementTypes

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        wafer: Wafer,
        factory: Factory,
        sample: Sample,
        mask: str,
        creator: str,
        allowedForMeasurementTypes: list[Any],
        **kwargs
    ) -> Design:
        """Creates a Design object."""
        kwargs.update({
            "name": name,
            "wafer": wafer,
            "factory": factory,
            "sample": sample,
            "mask": mask,
            "creator": creator,
            "allowedForMeasurementTypes": allowedForMeasurementTypes,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateDesign")


@dataclass
class Device(DomainObject, DomainYAMLObject):
    """Represents the database entry of a device."""

    yaml_tag = "!Device"

    design: Design
    sample: Sample

    @classmethod
    def create(cls, name: str, design: Design, sample: Sample, **kwargs) -> Device:
        """Creates a Device object."""
        kwargs.update({
            "name": name,
            "design": design,
            "sample": sample,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateDevice")
