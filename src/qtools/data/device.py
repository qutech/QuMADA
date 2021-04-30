#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any, List

from qtools.data.domain import DomainObject


@dataclass
class Factory(DomainObject):
    """Represents the database entry of a factory."""
    description: str


@dataclass
class Wafer(DomainObject):
    """Represents the database entry of a wafer."""
    description: str
    productionDate: str


@dataclass
class Sample(DomainObject):
    """Represents the database entry of a sample."""
    description: str
    wafer: Wafer


@dataclass
class Design(DomainObject):
    """Represents the database entry of a design."""
    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedMeasurementTypes: List[Any] = field(default_factory=list)
    # TODO: MeasurementTypes


@dataclass
class Device(DomainObject):
    """Represents the database entry of a device."""
    design: Design
    sample: Sample
