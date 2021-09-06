#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any, List

from qtools.data.domain import DomainObject
from qtools.data.db import (api_url,
                            get_design_by_id,
                            get_device_by_id,
                            get_factory_by_id,
                            get_sample_by_id,
                            get_wafer_by_id,
                            save_or_update_design,
                            save_or_update_device,
                            save_or_update_factory,
                            save_or_update_sample,
                            save_or_update_wafer)


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
    w = Wafer.create("W14", "Testwafer 14", "20210827")
    f = Factory.create("Ftemp", "Temporary Factory")
    s = Sample.create("S5", "Testsample 5", w)
    d1 = Design.create("Design4", w, f, s, "", "DGrothe", [])
    d2 = Device.create("Device5", d1, s)
    l = Device.load_from_db("f3a4f564-d4e3-4953-b477-40b00dc81ccc")
    pass