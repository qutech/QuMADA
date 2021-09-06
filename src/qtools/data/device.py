#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from sqlite3 import DatabaseError
from typing import Any, List

from qtools.data.domain import DomainObject
from qtools.data.db import (api_url,
                            save_or_update_design,
                            save_or_update_device,
                            save_or_update_factory,
                            save_or_update_sample,
                            save_or_update_wafer)


@dataclass
class Factory(DomainObject):
    """Represents the database entry of a factory."""
    description: str

    def save_to_db(self):
        response = save_or_update_factory(self.description, self.name)
        self._handle_db_response(response)


@dataclass
class Wafer(DomainObject):
    """Represents the database entry of a wafer."""
    description: str
    productionDate: str

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

    def save_to_db(self):
        response = save_or_update_sample(self.description,
                                         self.name,
                                         self.wafer)
        self._handle_db_response(response)


@dataclass
class Design(DomainObject):
    """Represents the database entry of a design."""
    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedMeasurementTypes: list[Any] = field(default_factory=list)
    # TODO: MeasurementTypes

    def save_to_db(self):
        response = save_or_update_design(self.allowedMeasurementTypes,
                                         self.creator,
                                         self.factory.name,
                                         self.mask,
                                         self.name,
                                         self.sample.name,
                                         self.wafer.name)
        self._handle_db_response(response)

@dataclass
class Device(DomainObject):
    """Represents the database entry of a device."""
    design: Design
    sample: Sample

    def save_to_db(self):
        response = save_or_update_device(self.name,
                                         self.design.name,
                                         self.sample.name)
        self._handle_db_response(response)
