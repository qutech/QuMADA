#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any, List

from qtools.data.domain import DomainObject


@dataclass
class Factory(DomainObject):
    description: str


@dataclass
class Wafer(DomainObject):
    description: str
    productionDate: str


@dataclass
class Sample(DomainObject):
    description: str
    wafer: Wafer


@dataclass
class Design(DomainObject):
    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedMeasurementTypes: List[Any] = field(default_factory=list)
    # TODO: MeasurementTypes

    

@dataclass
class Device(DomainObject):
    design: Design
    sample: Sample
    