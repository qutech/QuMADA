#!/usr/bin/env python3
"""
Measurement
"""

from typing import MutableMapping, MutableSequence, Optional
from dataclasses import dataclass
from enum import Enum, auto

from qcodes.dataset.experiment_container import Experiment
from qcodes.utils.metadata import Metadatable
from qcodes import Station, Parameter
from qcodes.logger.logger import start_all_logging

from qtools.data.measurement import EquipmentInstance
import qtools.data.measurement as dm


class Station(Station):
    pass


class VirtualGate():
    def __init__(self):
        self._functions = []
    
    @property
    def functions(self):
        return self._functions

    @functions.setter
    def functions(self, functions: MutableSequence):
        self._functions = functions


class ExperimentHandler():
    def __init__(self, station: Station = None,
                 equipmentInstances: MutableSequence[EquipmentInstance] = None) -> None:
        if station:
            self._station = station
        else:
            self._station = Station()

        for instance in equipmentInstances:
            self._load_instrument(instance)

    def _load_instrument(self, instance: EquipmentInstance):
        pass