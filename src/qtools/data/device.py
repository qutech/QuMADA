#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any

from qtools.data.apiclasses import get_all, get_by_id, save
from qtools.data.db import (
    save_or_update_design,
    save_or_update_device,
    save_or_update_sample,
)
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

    def save_to_db(self):
        """Saves or updates the Sample object to the db."""
        response = save_or_update_sample(self.description,
                                         self.name,
                                         self.wafer.name,
                                         self.pid)
        self._handle_db_response(response)


@get_by_id
@get_all
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

    def save_to_db(self):
        """Saves or updates the Design object to the db."""
        response = save_or_update_design(",".join(self.allowedForMeasurementTypes),
                                         self.creator,
                                         self.factory.name,
                                         self.mask,
                                         self.name,
                                         self.sample.name,
                                         self.wafer.name,
                                         self.pid)
        self._handle_db_response(response)


@get_by_id
@get_all
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

    def save_to_db(self):
        """Saves or updates the Device object to the db."""
        response = save_or_update_device(self.name,
                                         self.design.name,
                                         self.sample.name)
        self._handle_db_response(response)
