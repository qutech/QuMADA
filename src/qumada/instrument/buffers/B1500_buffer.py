# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 17:26:21 2024

@author: mmw
"""

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

from __future__ import annotations

import logging

import numpy as np
from jsonschema import validate
from qcodes.parameters import Parameter

from qumada.instrument.buffers.buffer import Buffer, BufferException

from qcodes.instrument_drivers.Keysight.keysightb1500 import KeysightB1500
from qcodes.instrument_drivers.Keysight.keysightb1500 import constants

logger = logging.getLogger(__name__)


class B1500Buffer(Buffer):
    """Buffer for B1500"""

    AVAILABLE_TRIGGERS: list[str] = [
    ]

    TRIGGER_MODE_MAPPING: dict = {
    }

    # TODO: What happens in exact mode? Look up limitations...

    def __init__(self, B1500: KeysightB1500):
        
        self._subscribed_parameters: list[Parameter] = []
        self._trigger: str | None = None
        self._num_points: int | None = None
        self._num_bursts: int = 1
        self._burst_duration: float | None = None

    def setup_buffer(self, settings: dict) -> None:
        # validate settings
        validate(settings, self.settings_schema)
        self.settings: dict = settings
        self.enable_channels()
        logger.warning("All channels enabled!")

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, trigger: str | None) -> None:
        # TODO: Inform user about automatic changes of settings
        # TODO: This is done BEFORE the setup_buffer, so changes to trigger type will be overriden anyway?
        # print(f"Running trigger setter with: {trigger}")
        self._trigger = trigger

    def force_trigger(self) -> None:
        logger.exception("Cannot force trigger! Not implemented")
        
    @property
    def num_points(self) -> int | None:
        return self._num_points

    @num_points.setter
    def num_points(self, num_points) -> None:
        if num_points > 8388608:
            raise BufferException(
                "Buffer is to small for this measurement. \
                                  Please reduce the number of data points"
            )
        self._num_points = int(num_points)

    # TODO: Define setter for other settings (e.g. burst_duration, num_bursts etc)

    def _set_num_points(self) -> None:
        """
        Calculates all required settings for the MFLI and sets the values
        accordingly
        ------
        Exception
           Exception if number of points or number of burst is overdefined.

        Returns
        -------
        None
        """
        # TODO: Include ._daq.repetitions (averages over multiple bursts)

        if all(k in self.settings for k in ("sampling_rate", "burst_duration", "num_points")):
            raise BufferException("You cannot define sampling_rate, burst_duration and num_points at the same time")

        if all(k in self.settings for k in ("sampling_rate", "duration", "num_bursts", "num_points")):
            raise BufferException(
                "You cannot define sampling rate, duration and num_burst and num_points at the same time"
            )

        if all(k in self.settings for k in ("num_bursts", "duration", "burst_duration")):
            raise BufferException("You cannnot define duration, burst_duration and num_bursts at the same time")

        if "burst_duration" in self.settings:
            self._burst_duration = self.settings["burst_duration"]

        if "duration" in self.settings:
            if "burst_duration" in self.settings:
                self._num_bursts = np.ceil(self.settings["duration"] / self._burst_duration)
            elif "num_bursts" in self.settings:
                self._num_bursts = int(self.settings["num_bursts"])
                self._burst_duration = self.settings["duration"] / self._num_bursts
            else:
                logger.info(
                    "You have specified neither burst_duration nor num_bursts. \
                      Using duration as burst_duration!"
                )
                self._burst_duration = self.settings["duration"]

        if "num_points" in self.settings:
            self.num_points = int(self.settings["num_points"])
            if "sampling_rate" in self.settings:
                self._burst_duration = float(self.num_points / self.settings["sampling_rate"])

        elif "sampling_rate" in self.settings:
            self._sampling_rate = float(self.settings["sampling_rate"])
            if self._burst_duration is not None:
                self.num_points = int(np.ceil(self._sampling_rate * self._burst_duration))
            elif all(k in self.settings for k in ("duration", "num_bursts")):
                self._burst_duration = float(self.settings["duration"] / self.settings["num_bursts"])

        #self._daq.count(self._num_bursts)
        #self._daq.duration(self._burst_duration)
        #self._daq.grid.cols(self.num_points)

    def read(self) -> dict:
        data = self.read_raw()
        result_dict = {}
        for i in len(self._subscribed_parameters):
            result_dict[self._subscribed_parameters[i].name] = data[i]
            # if "timestamps" not in result_dict:
            #     result_dict["timestamps"] = data[key][0].time
        return result_dict

    def read_raw(self) -> dict:
        if self.data is not None:
            return self.data
        else:
            raise Exception("No data measured!")

    def subscribe(self, parameters: list[Parameter]) -> None:
        self.B1500.set_measurement_mode(
            mode=constants.MM.Mode.STAIRCASE_SWEEP,
            channels=[param.channels[0] for param in parameters])


    def unsubscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters.copy():
            try:
                self._subscribed_parameters.remove(parameter)
            except:
                logger.warning(f"{parameter} was not subscribed and cannot be removed")

    def is_subscribed(self, parameter: Parameter) -> bool:
        return parameter in self._subscribed_parameters

    def start(self) -> None:
        self.data=self.run_iv_staircase_sweep()

    def stop(self) -> None:
        logger.warning("Bad luck! There is no way to stop this measurement!")

    def is_ready(self) -> bool: ...

    def is_finished(self) -> bool:
        return True

