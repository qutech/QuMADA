#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any

from qtools.data.apiclasses import get_all, get_by_id, save
from qtools.data.domain import DomainObject


@get_by_id
@get_all(fn_name="factories")
@save(fn_name="saveOrUpdateFactory", field_names=["description", "name", "pid"])
@dataclass
class Factory(DomainObject):
    """Represents the database entry of a factory."""
    description: str

    @classmethod
    def create(cls, name: str, description: str, **kwargs):
        """Creates a Factory object."""
        kwargs.update({
            "name": name,
            "description": description,
        })
        return super(cls, cls)._create(**kwargs)


@get_by_id
@get_all
@save(fn_name="saveOrUpdateWafer")
@dataclass
class Wafer(DomainObject):
    """Represents the database entry of a wafer."""
    description: str
    productionDate: str  # pylint: disable=invalid-name

    @classmethod
    def create(cls,
               name: str,
               description: str,
               productionDate: str,
               **kwargs):  # pylint: disable=invalid-name
        """Creates a Wafer object."""
        kwargs.update({
            "name": name,
            "description": description,
            "productionDate": productionDate,
        })
        return super(cls, cls)._create(**kwargs)


@get_by_id
@get_all
@save(
    fn_name="saveOrUpdateSample", field_names=["description", "waferId", "name", "pid"]
)
@dataclass
class Sample(DomainObject):
    """Represents the database entry of a sample."""
    description: str
    wafer: Wafer

    @classmethod
    def create(cls, name: str, description: str, wafer: Wafer, **kwargs):
        """Creates a Sample object."""
        kwargs.update({
            "name": name,
            "description": description,
            "wafer": wafer,
        })
        return super(cls, cls)._create(**kwargs)

    @property
    def waferId(self):
        return self.wafer.pid


@get_by_id
@get_all
@save(
    fn_name="saveOrUpdateDesign",
    field_names=[
        "waferId",
        "factoryId",
        "sampleId",
        "mask",
        "creator",
        "allowedForMeasurementTypes",
        "name",
        "pid",
    ],
)
@dataclass
class Design(DomainObject):
    """Represents the database entry of a design."""
    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedForMeasurementTypes: list[Any] = field(default_factory=list)  # pylint: disable=invalid-name
    # TODO: MeasurementTypes

    @classmethod
    def create(cls,
               name: str,
               wafer: Wafer,
               factory: Factory,
               sample: Sample,
               mask: str,
               creator: str,
               allowedForMeasurementTypes: list[Any],
               **kwargs):  # pylint: disable=invalid-name
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
        return super(cls, cls)._create(**kwargs)

    @property
    def waferId(self):
        return self.wafer.pid

    @property
    def factoryId(self):
        return self.factory.pid

    @property
    def sampleId(self):
        return self.sample.pid


@get_by_id
@get_all
@save(fn_name="saveOrUpdateDevice", field_names=["designId", "sampleId", "name", "pid"])
@dataclass
class Device(DomainObject):
    """Represents the database entry of a device."""
    design: Design
    sample: Sample

    @classmethod
    def create(cls, name: str, design: Design, sample: Sample, **kwargs):
        """Creates a Device object."""
        kwargs.update({
            "name": name,
            "design": design,
            "sample": sample,
        })
        return super(cls, cls)._create(**kwargs)

    @property
    def designId(self):
        return self.design.pid

    @property
    def sampleId(self):
        return self.sample.pid
