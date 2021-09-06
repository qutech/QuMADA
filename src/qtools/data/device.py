#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any, List

from qtools.data.domain import DomainObject
from qtools.data.db import DBConnector


@dataclass
class Factory(DomainObject):
    """Represents the database entry of a factory."""
    description: str

    @classmethod
    def create(cls, name: str, description: str, **kwargs):
        kwargs["name"] = name
        kwargs["description"] = description
        return super(cls, cls).create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        data = get_factory_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        response = save_or_update_factory(self.description,
                                          self.name,
                                          self.pid)
        self._handle_db_response(response)


@dataclass
class Wafer(DomainObject):
    """Represents the database entry of a wafer."""
    description: str
    productionDate: str

    @classmethod
    def create(cls, name: str, description: str, productionDate: str, **kwargs):
        kwargs["name"] = name
        kwargs["description"] = description
        kwargs["productionDate"] = productionDate
        return super(cls, cls).create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        data = get_wafer_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        response = save_or_update_wafer(self.description,
                                        self.name,
                                        self.productionDate,
                                        self.pid)
        self._handle_db_response(response)


@dataclass
class Sample(DomainObject):
    """Represents the database entry of a sample."""
    description: str
    wafer: Wafer

    @classmethod
    def create(cls, name: str, description: str, wafer: Wafer, **kwargs):
        kwargs["name"] = name
        kwargs["description"] = description
        kwargs["wafer"] = wafer
        return super(cls, cls).create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        data = get_sample_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        response = save_or_update_sample(self.description,
                                         self.name,
                                         self.wafer.name,
                                         self.pid)
        self._handle_db_response(response)


@dataclass
class Design(DomainObject):
    """Represents the database entry of a design."""
    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedForMeasurementTypes: list[Any] = field(default_factory=list)
    # TODO: MeasurementTypes

    @classmethod
    def create(cls, name: str, wafer: Wafer, factory: Factory, sample: Sample, mask: str, creator: str, allowedForMeasurementTypes: List[Any], **kwargs):
        kwargs["name"] = name
        kwargs["wafer"] = wafer
        kwargs["factory"] = factory
        kwargs["sample"] = sample
        kwargs["mask"] = mask
        kwargs["creator"] = creator
        kwargs["allowedForMeasurementTypes"] = allowedForMeasurementTypes
        return super(cls, cls).create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        data = get_design_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        response = save_or_update_design(",".join(self.allowedMeasurementTypes),
                                         self.creator,
                                         self.factory.name,
                                         self.mask,
                                         self.name,
                                         self.sample.name,
                                         self.wafer.name,
                                         self.pid)
        self._handle_db_response(response)

@dataclass
class Device(DomainObject):
    """Represents the database entry of a device."""
    design: Design
    sample: Sample

    @classmethod
    def create(cls, name: str, design: Design, sample: Sample, **kwargs):
        kwargs["name"] = name
        kwargs["design"] = design
        kwargs["sample"] = sample
        return super(cls, cls).create(**kwargs)

    @classmethod
    def load_from_db(cls, pid: str):
        data = get_device_by_id(pid)
        return cls(**data)

    def save_to_db(self):
        response = save_or_update_device(self.name,
                                         self.design.name,
                                         self.sample.name)
        self._handle_db_response(response)

if __name__ == "__main__":
    db = DBConnector("http://134.61.7.48:9123/")
    factories = db.get_factories()
    f1 = db.get_factory_by_id("9471ed6c-24ac-443a-b89e-3073ef4cfc52")
    print(f1)
    print(factories)