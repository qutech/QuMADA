# -*- coding: utf-8 -*-
"""
Created on Tue Jan  3 15:20:07 2023

@author: till3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

import numpy as np
from jsonschema import validate
from pyvisa import VisaIOError
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import ManualParameter, Parameter
from qcodes.utils.metadata import Metadatable

from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qtools.instrument.buffer import Buffer, BufferException

#%%
class DummyDMMBuffer(Buffer):
    """Buffer for Dummy DMM"""

    AVAILABLE_TRIGGERS: list[str] = ["software"]

    def __init__(self, device: DummyDmm):
        self._device = device
        self._trigger: str | None = None
        self._subscribed_parameters: set[Parameter] = set()
        self._num_points: int | None = None

    def setup_buffer(self, settings: dict) -> None:
        """Sets instrument related settings for the buffer."""

        validate(settings, self.settings_schema)
        self.settings: dict = settings
        self._device.buffer_SR(settings.setdefault("sampling_rate", 512))
        #self._device.buffer_trig_mode("OFF")
        self._set_num_points() #Method defined below
        self.delay_data_points = 0 #Datapoints to delete at the beginning of dataset due to delay.
        self.delay = settings.get("delay", 0)
        if self.delay < 0:
            raise Exception("The Dummy Dac does not support negative delays.")
        else:
            self.delay_data_points = int(self.delay*self._device.buffer_SR())
            self.num_points = self.delay_data_points+ self.num_points
            self._device.buffer_n_points(self.num_points)
            #TODO: There has to be a more elegant way for the setter.
        self._device.buffer.ready_buffer()
    @property
    def num_points(self) -> int | None:
        return self._num_points
    
    @num_points.setter
    def num_points(self, num_points) -> None:
        if num_points > 16383:
            raise Exception("Dummy Dacs Buffer is to small for this measurement. Please reduce the number of data points or the delay")
        self._num_points = int(num_points)

    def _set_num_points(self) -> None:
        """
        Calculates number of datapoints and sets
        the num_points accordingly.
        Raises
        ------
        Exception
           Exception if number of points is overdefined.

        Returns
        -------
        None
        """
        if all(k in self.settings for k in ("sampling_rate", "burst_duration", "num_points")):
            raise Exception("You cannot define sampling_rate, burst_duration and num_points at the same time")
        elif self.settings.get("num_points", False):
            self.num_points = self.settings["num_points"]
        elif all(k in self.settings for k in ("sampling_rate", "burst_duration")):
                    self.num_points = int(
                        np.ceil(self.settings["sampling_rate"] * self.settings["burst_duration"])
                    )

    @property
    def trigger(self) -> str | None:
        return self._trigger

    @trigger.setter
    def trigger(self, trigger: str | None) -> None:
        if trigger is None:
            # TODO: standard value for Sample Rate
            self._device.buffer_SR(512)
            self._device.buffer_trig_mode("OFF")
        elif trigger == "external":
            self._device.buffer_SR("Trigger") 
            self._device.buffer_trig_mode("ON")
        else:
            raise BufferException(
                "SR830 does not support setting custom trigger inputs. Use 'external' and the input on the back of the unit."
            )
        self._trigger = trigger

    def force_trigger(self) -> None:
        self._device.start()

    def read_raw(self) -> dict:
        data = {}
        try:
            for parameter in self._subscribed_parameters:
                index = self._device.buffer.subscribed_params.index(parameter)
                data[parameter.name] = self._device.buffer.get()[index]
                data[parameter.name] = data[parameter.name][self.delay_data_points:self.num_points]
        except VisaIOError as ex:
            raise BufferException(
                "Could not read the buffer. Buffer has to be stopped before readout."
            ) from ex
        return data

    def read(self) -> dict:
        # TODO: Add timetrace if possible
        return self.read_raw()

    def subscribe(self, parameters: list[Parameter]) -> None:
        assert type(parameters) == list
        for parameter in parameters:
            self._device.buffer.subscribe(parameter)
            self._subscribed_parameters.add(parameter)

    def unsubscribe(self, parameters: list[Parameter]) -> None:
        assert type(parameters) == list
        for parameter in parameters:
            if parameter in self._device.buffer.subscribed_params:
                self._device.buffer.subscribed_params.remove(parameter)
                self._subscribed_parameters.remove(parameter)
            else: 
                print(f"{parameter} is not subscribed")

    def is_subscribed(self, parameter: Parameter) -> bool:
        return parameter in self._subscribed_parameters

    def start(self) -> None:
        self._device.start()

    def stop(self) -> None:
        ...
        
    def is_ready(self) -> bool:
        ...

    def is_finished(self) -> bool:
        return self._device.is_finished()
