# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Till Huckeman

"""
Created on Tue Jan  3 15:20:07 2023

@author: till3
"""
from __future__ import annotations

import numpy as np
from jsonschema import validate
from qcodes.parameters import Parameter

from qtools.instrument.buffers.buffer import Buffer
from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm


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
        # self._device.buffer_trig_mode("OFF")
        self._set_num_points()  # Method defined below
        # Datapoints to delete at the beginning of dataset due to delay.
        self.delay_data_points = 0
        self.delay = settings.get("delay", 0)
        if self.delay < 0:
            raise BufferException("The Dummy Dac does not support negative delays.")
        else:
            self.delay_data_points = int(self.delay * self._device.buffer_SR())
            self.num_points = self.delay_data_points + self.num_points
            self._device.buffer_n_points(self.num_points)
        self._device.buffer.ready_buffer()

    @property
    def num_points(self) -> int | None:
        return self._num_points

    @num_points.setter
    def num_points(self, num_points) -> None:
        if num_points > 16383:
            raise BufferException(
                "Dummy Dacs Buffer is to small for this measurement. Please reduce the number of data points or the delay"
            )
        self._num_points = int(num_points)

    def _set_num_points(self) -> None:
        # TODO: Move to parent Buffer Class?
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
            raise BufferException("You cannot define sampling_rate, burst_duration and num_points at the same time")
        elif self.settings.get("num_points", False):
            self.num_points = self.settings["num_points"]
        elif all(k in self.settings for k in ("sampling_rate", "burst_duration")):
            self.num_points = int(np.ceil(self.settings["sampling_rate"] * self.settings["burst_duration"]))

    @property
    def trigger(self) -> str | None:
        return self._trigger

    @trigger.setter
    def trigger(self, trigger: str | None) -> None:
        if trigger == "software":
            self._trigger = trigger

    def force_trigger(self) -> None:
        self._device._force_trigger()

    def read_raw(self) -> dict:
        data = {}

        for parameter in self._subscribed_parameters:
            index = self._device.buffer.subscribed_params.index(parameter)
            data[parameter.name] = self._device.buffer.get()[index]
            data[parameter.name] = data[parameter.name][self.delay_data_points : self.num_points]
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
