#!/usr/bin/env python3
"""
Representations of domain objects (Devices).
"""

from dataclasses import dataclass, field
from typing import Any, List

from qtools.data.domain import DomainObject

# TODO: generalize nested creation of dataclasses
# https://stackoverflow.com/questions/51564841/creating-nested-dataclass-objects-in-python
# Maybe look at dacite: https://github.com/konradhalas/dacite/

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

    def __post_init__(self):
        self.wafer = Wafer(**self.wafer)


@dataclass
class Design(DomainObject):
    wafer: Wafer
    factory: Factory
    sample: Sample
    mask: str
    creator: str
    allowedMeasurementTypes: List[Any] = field(default_factory=list)

    def __post_init__(self):
        self.wafer = Wafer(**self.wafer)
        self.factory = Factory(**self.factory)
        self.sample = Sample(**self.sample)
        # TODO: MeasurementTypes

    

@dataclass
class Device(DomainObject):
    design: Design
    sample: Sample
    
    def __post_init__(self):
        self.design = Design(**self.design)
        self.sample = Sample(**self.sample)
    