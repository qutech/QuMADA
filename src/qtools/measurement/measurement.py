#!/usr/bin/env python3
"""
Measurement
"""

from typing import MutableSequence

from qcodes import Station

from qtools.data.measurement import EquipmentInstance


class QtoolsStation(Station):
    """Station object, inherits from qcodes Station."""


class VirtualGate():
    """Virtual Gate"""
    def __init__(self):
        self._functions = []

    @property
    def functions(self):
        """List of equipment Functions, the virtual gate shall have."""
        return self._functions

    @functions.setter
    def functions(self, functions: MutableSequence):
        self._functions = functions


class ExperimentHandler():
    """Experiment Handler"""
    def __init__(self, station: Station = None,
                 equipmentInstances: MutableSequence[EquipmentInstance] = None) -> None:
        if equipmentInstances is None:
            equipmentInstances = []

        if station:
            self._station = station
        else:
            self._station = Station()

        for instance in equipmentInstances:
            self._load_instrument(instance)

    def _load_instrument(self, instance: EquipmentInstance):
        pass
